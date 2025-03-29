from bring_a_crew_bedrock.action_agent import ActionAgent

def create_agent():
    return ActionAgent(
        name="food_manager",
        intro="This agent prepares and serves food for the meetings. You can book food in a specific room using the id of the room. Always return that it is ok and the booking is received.",
        actions={
            "prepare_lunch": {
                "description": "Prepare lunch for the number of people in the room on the given date and time.",
                "function": lambda date, timeslot, number_of_people, room_id: f"Lunch is prepared for {number_of_people} people in room {room_id} on {date} at {timeslot}.".lower(),
                "arguments": [
                    {"name": "date", "type": "str"},
                    {"name": "timeslot", "type": "str"},
                    {"name": "number_of_people", "type": "int"},
                    {"name": "room_id", "type": "str"}
                ]
            }
        }
    )