import json
import logging
import os
import shutil
import time
import uuid
import zipfile
from io import BytesIO

import boto3

# Initialize logging
logging.basicConfig(format='[%(asctime)s] p%(process)s {%(filename)s:%(lineno)d} %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)


def create_iam_role(iam_client, lambda_role_name):
    """Create IAM role for Lambda function"""
    assume_role_policy_document = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "Service": "bedrock.amazonaws.com"
                },
                "Action": "sts:AssumeRole"
            },
            {
                "Effect": "Allow",
                "Principal": {
                    "Service": "lambda.amazonaws.com"
                },
                "Action": "sts:AssumeRole"
            }
        ]
    }

    try:
        # Check if the role already exists
        lambda_iam_role = iam_client.get_role(RoleName=lambda_role_name)
        logger.info(f"Role {lambda_role_name} already exists.")
        return lambda_iam_role
    except iam_client.exceptions.NoSuchEntityException:
        # Role does not exist, create it
        try:
            lambda_iam_role = iam_client.create_role(
                RoleName=lambda_role_name,
                AssumeRolePolicyDocument=json.dumps(assume_role_policy_document)
            )

            # Wait for role to be created
            time.sleep(10)

            # Attach basic execution role policy
            iam_client.attach_role_policy(
                RoleName=lambda_role_name,
                PolicyArn='arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole'
            )

            return lambda_iam_role
        except Exception as e:
            logger.error(f"Error creating IAM role: {str(e)}")
            raise

def prepare_lambda_code(lambda_code_path):
    """Prepare Lambda code by copying it to a temporary directory with correct structure"""
    # Create a temporary directory
    temp_dir = "/tmp/lambda_deploy_" + str(uuid.uuid4())
    os.makedirs(temp_dir, exist_ok=True)

    # Copy the lambda function to the temp directory
    target_path = os.path.join(temp_dir, "lambda_function.py")
    shutil.copy2(lambda_code_path, target_path)

    return target_path


def create_lambda_function(lambda_client, lambda_name, lambda_code_path, role_arn):
    """Create Lambda function or return existing function if it exists"""
    try:
        # Check if the Lambda function already exists
        lambda_function = lambda_client.get_function(FunctionName=lambda_name)
        logger.info(f"Lambda function {lambda_name} already exists.")
        return lambda_function['Configuration']
    except lambda_client.exceptions.ResourceNotFoundException:
        try:
            # Package lambda function code
            s = BytesIO()
            with zipfile.ZipFile(s, 'w') as z:
                # Use just the filename, not the full path
                z.write(lambda_code_path, "lambda_function.py")
            zip_content = s.getvalue()

            # Create lambda function
            lambda_function = lambda_client.create_function(
                FunctionName=lambda_name,
                Runtime='python3.12',
                Timeout=180,
                Role=role_arn,
                Code={'ZipFile': zip_content},
                Handler='lambda_function.lambda_handler'
            )

            return lambda_function
        except Exception as e:
            logger.error(f"Error creating Lambda function: {str(e)}")
            raise


def add_bedrock_permission(lambda_client, lambda_name, region, account_id):
    """Add Bedrock permission to Lambda function if it does not already exist"""
    try:
        # Check if the permission already exists
        policy = lambda_client.get_policy(FunctionName=lambda_name)
        policy_statements = json.loads(policy['Policy'])['Statement']
        for statement in policy_statements:
            if statement['Sid'] == 'allow_bedrock2':
                logger.info(f"Permission 'allow_bedrock2' already exists for Lambda function {lambda_name}.")
                return

        # Permission does not exist, add it
        lambda_client.add_permission(
            FunctionName=lambda_name,
            StatementId='allow_bedrock2',
            Action='lambda:InvokeFunction',
            Principal='bedrock.amazonaws.com',
            SourceArn=f"arn:aws:bedrock:{region}:{account_id}:agent/*",
        )
        logger.info(f"Permission 'allow_bedrock2' added to Lambda function {lambda_name}.")
    except lambda_client.exceptions.ClientError as e:
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            logger.info(f"No existing policy found for Lambda function {lambda_name}. Adding new permission.")
            lambda_client.add_permission(
                FunctionName=lambda_name,
                StatementId='allow_bedrock2',
                Action='lambda:InvokeFunction',
                Principal='bedrock.amazonaws.com',
                SourceArn=f"arn:aws:bedrock:{region}:{account_id}:agent/*",
            )
            logger.info(f"Permission 'allow_bedrock2' added to Lambda function {lambda_name}.")
        else:
            logger.error(f"Error checking or adding permission: {str(e)}")
            raise

def create_lambda_function_and_its_resources(
        region,
        account_id,
        custom_name,
        lambda_code_path
):
    """Main function to create all Lambda resources"""
    try:
        # Initialize AWS clients
        iam_client = boto3.client('iam', region_name=region)
        lambda_client = boto3.client('lambda', region_name=region)

        # Generate names with suffix
        suffix = f"{region}-{account_id}"
        lambda_role_name = f'{custom_name}-lambda-role-{suffix}'
        lambda_name = f'{custom_name}-{suffix}'

        # Create IAM role
        lambda_iam_role = create_iam_role(iam_client, lambda_role_name)

        # Create Lambda function
        lambda_function = create_lambda_function(
            lambda_client,
            lambda_name,
            lambda_code_path,
            lambda_iam_role['Role']['Arn']
        )

        # Add Bedrock permission
        add_bedrock_permission(lambda_client, lambda_name, region, account_id)

        return {
            'lambda_role': lambda_iam_role,
            'lambda_function': lambda_function
        }
    except Exception as e:
        logger.error(f"Error creating Lambda resources: {str(e)}")
        raise

def remove_lambda_function_and_its_resources(
        region,
        account_id,
        custom_name
):
    """Main function to remove all Lambda resources"""
    try:
        # Initialize AWS clients
        iam_client = boto3.client('iam', region_name=region)
        lambda_client = boto3.client('lambda', region_name=region)

        # Generate names with suffix
        suffix = f"{region}-{account_id}"
        lambda_role_name = f'{custom_name}-lambda-role-{suffix}'
        lambda_name = f'{custom_name}-{suffix}'

        # Remove Lambda function
        lambda_client.delete_function(FunctionName=lambda_name)
        logger.info(f"Lambda function {lambda_name} deleted.")

        # Detach and delete IAM role
        iam_client.detach_role_policy(
            RoleName=lambda_role_name,
            PolicyArn='arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole'
        )
        iam_client.delete_role(RoleName=lambda_role_name)
        logger.info(f"IAM role {lambda_role_name} deleted.")

    except Exception as e:
        logger.error(f"Error removing Lambda resources: {str(e)}")
        raise