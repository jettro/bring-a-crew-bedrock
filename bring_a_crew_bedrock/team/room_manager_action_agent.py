import logging

from dotenv import load_dotenv

from bring_a_crew_bedrock import action_agent_log
from bring_a_crew_bedrock.action_agent import ActionAgent
from bring_a_crew_bedrock.setup_logging import setup_logging


def check_available_room(req_date: str, timeslot: str, number_of_people: int):
    # This is a placeholder for the actual implementation
    return f"Room with more then {number_of_people} seats is available on {req_date} for {timeslot}. You can book it."


def book_room(req_date: str, timeslot: str, number_of_people: int):
    room_id = f"max_{str(number_of_people)}_people"
    # This is a placeholder for the actual implementation
    return f"Room with more then {number_of_people} seats is booked on {req_date} for {timeslot} with id {room_id}."


def create_agent():
    return  ActionAgent(
        name="room_manager",
        intro="This agent checks the availability of rooms and books them.",
        actions={
            "check_available_room": {
                "description": "Find an available room with more then requested seats for the asked time and day. Rooms are only available to book for morning or afternoon.",
                "function": check_available_room,
                "arguments": [
                    {"name": "req_date", "type": "str"},
                    {"name": "timeslot", "type": "str"},
                    {"name": "number_of_people", "type": "int"}
                ]
            },
            "book_room": {
                "description": "Book a room with more then requested seats for the asked time and day. Rooms are only available to book for morning or afternoon. Return the room id.",
                "function": book_room,
                "arguments": [
                    {"name": "req_date", "type": "str"},
                    {"name": "timeslot", "type": "str"},
                    {"name": "number_of_people", "type": "int"}
                ]
            }
        }
    )

if __name__ == "__main__":
    _ = load_dotenv()
    setup_logging()
    main_log = logging.getLogger("main")
    main_log.setLevel(logging.INFO)
    action_agent_log.setLevel(logging.DEBUG)

    # This is a placeholder for the actual implementation
    action_agent_log.debug("Starting the room_manager agent")
    room_manager = create_agent()
    response = room_manager.perform_action(
        "Check for an available room for 6 people tuesday morning the 26th of February.")

    main_log.info("Response: %s", response)

