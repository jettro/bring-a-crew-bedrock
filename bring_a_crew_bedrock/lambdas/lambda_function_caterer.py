import json
import logging
import random
import traceback

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def check_lunch_options() -> list[str]:
    return ["Pizza", "Sushi", "Burger", "Sandwich", "Salad", "Broodje kroket"]


def order_lunch(date: str, room_id: str, number_of_people: int, lunch_option: str) -> str:
    if lunch_option and lunch_option in check_lunch_options():
        logger.info(f"Ordering lunch option for {lunch_option}")
    else:
        if lunch_option:
            logger.info(f"Provided lunch option {lunch_option} is not available")
            return f"This lunch cannot be ordered. Provided lunch option {lunch_option} is not available. Please order one of the following options for lunch: {', '.join(check_lunch_options())}"
        else:
            logger.info(f"No lunch option provided")
            lunch_option = random.choice(check_lunch_options())
    return f"Lunch order is received. {lunch_option} will be served in room {room_id} for {number_of_people} people on {date}"



def lambda_handler(event, context):

    api_path = event['apiPath']
    action_group = event['actionGroup']

    try:
        logger.info(f"Calling function with API path: {api_path}")

        logger.info(f"Received event: \n{json.dumps(event, indent=2)}")

        # Extract parameters
        parameters = event.get('parameters', [])

        has_error = False
        if api_path == '/check_lunch_options':
            lunch_options = check_lunch_options()
            logger.info(f"Available lunch options: {lunch_options}")
            function_response = f"Available lunch options are: {' '.join(lunch_options)}"
        elif api_path == '/order_lunch':
            date = next((param['value'] for param in parameters if param['name'] == 'date'), None)
            room_id = next((param['value'] for param in parameters if param['name'] == 'room_id'), None)
            number_of_people = next((param['value'] for param in parameters if param['name'] == 'number_of_people'), None)
            lunch_option = next((param['value'] for param in parameters if param['name'] == 'lunch_option'), None)

            function_response = order_lunch(date, room_id, number_of_people, lunch_option)
        else:
            logger.error(f"Unknown API path: {api_path}")
            raise ValueError(f"Unknown API path: {api_path}")

        response_body = {
            "application/json": {
                "body": function_response
            }
        }

        logger.info(f"Current availability result : {function_response}")

        action_response = {
            'actionGroup': action_group,
            'apiPath': api_path,
            'httpMethod': event.get('httpMethod', 'POST'),
            'httpStatusCode': 200,
            'responseBody': response_body
        }

        final_response = {'response': action_response}
        logger.info(f"Returning successful response: \n{json.dumps(final_response, indent=2)}")
        return final_response

    except Exception as e:
        logger.error(f"Exception occurred: {str(e)}")
        logger.error(f"Stack trace: {traceback.format_exc()}")

        error_body = {
            'status': 'error',
            'message': str(e)
        }

        response_body = {
            'application/json': {
                'body': json.dumps(error_body)
            }
        }

        action_response = {
            'actionGroup': action_group,
            'apiPath': api_path,
            'httpMethod': event.get('httpMethod', 'POST'),
            'httpStatusCode': 400,
            'responseBody': response_body
        }

        error_response = {'response': action_response}
        logger.info(f"Returning error response: \n{json.dumps(error_response, indent=2)}")
        return error_response