import json
import logging
import traceback

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def check_availability(date: str, person: str):
    logger.info("check_availability: date=%s, person=%s", date, person)
    if person.lower() == "alice":
        return f"{person} is not available in the week starting with {date}, Charlie will replace her until further notice."
    elif person.lower() == "bob":
        return f"{person} is available in the week starting with {date} on Monday, Tuesday, and Thursday."
    elif person.lower() == "charlie":
        return f"{person} is not available in the week starting with {date} on Monday in the morning, Tuesday, Thursday, and Friday in the morning."
    else:
        return f"{person} is unknown to the system."


def book_person(date: str, timeslot: str, person: str):
    logger.info("book_person: date=%s, timeslot=%s, person=%s", date, timeslot, person)
    return f"{person} is booked for a meeting on {date} at {timeslot}."



def lambda_handler(event, context):

    api_path = event['apiPath']
    action_group = event['actionGroup']

    try:
        logger.info(f"Calling function with API path: {api_path}")

        logger.info(f"Received event: \n{json.dumps(event, indent=2)}")

        # Extract parameters
        parameters = event.get('parameters', [])

        has_error = False
        if api_path == '/check_availability':
            # Extract parameters for check_availability
            start_date = next((param['value'] for param in parameters if param['name'] == 'start_date'), None)
            person = next((param['value'] for param in parameters if param['name'] == 'person'), None)
            function_response = check_availability(start_date, person)
        elif api_path == '/book_person':
            # Extract parameters for book_person
            date = next((param['value'] for param in parameters if param['name'] == 'date'), None)
            timeslot = next((param['value'] for param in parameters if param['name'] == 'timeslot'), None)
            person = next((param['value'] for param in parameters if param['name'] == 'person'), None)
            function_response = f"{person} is booked for a meeting on {date} at {timeslot}."
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