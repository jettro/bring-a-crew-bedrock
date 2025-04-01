import json
import logging
import traceback

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def check_available_room(req_date: str, timeslot: str, number_of_people: int):
    # This is a placeholder for the actual implementation
    return f"Room with more then {number_of_people} seats is available on {req_date} for {timeslot}. You can book it."


def book_room(req_date: str, timeslot: str, number_of_people: int):
    room_id = f"max_{str(number_of_people)}_people"
    # This is a placeholder for the actual implementation
    return f"Room with more then {number_of_people} seats is booked on {req_date} for {timeslot} with id {room_id}."



def lambda_handler(event, context):

    api_path = event['apiPath']
    action_group = event['actionGroup']

    try:
        logger.info(f"Calling function with API path: {api_path}")

        logger.info(f"Received event: \n{json.dumps(event, indent=2)}")

        # Extract parameters
        parameters = event.get('parameters', [])

        has_error = False
        if api_path == '/check_availability_room':
            # Extract parameters for check_availability_room
            req_date = next((param['value'] for param in parameters if param['name'] == 'req_date'), None)
            timeslot = next((param['value'] for param in parameters if param['name'] == 'timeslot'), None)
            number_of_people = next((param['value'] for param in parameters if param['name'] == 'number_of_people'), None)
            function_response = check_available_room(req_date, timeslot, number_of_people)
        elif api_path == '/book_room':
            # Extract parameters for book_room
            req_date = next((param['value'] for param in parameters if param['name'] == 'req_date'), None)
            timeslot = next((param['value'] for param in parameters if param['name'] == 'timeslot'), None)
            number_of_people = next((param['value'] for param in parameters if param['name'] == 'number_of_people'), None)

            function_response = book_room(req_date, timeslot, number_of_people)
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