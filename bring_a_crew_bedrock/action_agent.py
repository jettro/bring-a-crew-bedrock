import json
import re
from abc import ABC
from datetime import datetime

import boto3

from . import action_agent_log


def create_system_prompt(actions, agent_intro: str):
    def _extract_arguments(arguments):
        return ",".join([f" `{argument["name"]}`({argument["type"]})" for argument in arguments])
    actions_str = "\n".join([f" - `{action}`; for {value["description"]} with arguments {_extract_arguments(value["arguments"])}" for action, value in actions.items()])
    return f"""
{agent_intro}

You are an AI agent following the ReAct framework, where you **Think**, **Act**, and process **Observations** in response to a given **Question**.  During thinking you analyse the question, break it down into subquestions, and decide on the actions to take to answer the question. You then act by performing the actions you decided on. After each action, you pause to observe the results of the action. You then continue the cycle by thinking about the new observation and deciding on the next action to take. You continue this cycle until you have enough information to answer the original question.

The date for today is: {datetime.now().strftime("%Y-%m-%d")}

Arguments for an action are provided as a json document with the arguments as keys and the values as the values.

You will always follow this structured format:
Question: [User’s question]
Think: [Your reasoning about how to answer the question using available actions only]
Action: [action]: [arguments]
PAUSE

After receiving an **Observation**, you will continue the cycle using the new observation:
Observation: [Result from the previous action]
Think: [Decide on the next action to take.]
If further action is needed, you continue with the next action and wait for the new observation:
Action: [action]: [arguments]
PAUSE
Else, if the final answer is ready, you will return it:
Answer: [Use Final answer to write a friendly response with the answer to the question]

Rules:
1. Never answer a question directly; always go through the **Think → Action → PAUSE** cycle.
2. Never generate output after "PAUSE"
3. Observations will be provided as a response to an action; never generate your own output for an action.
4. These are the only available actions, and there arguments:
{actions_str}

Example Interactions:
- User Input:
What is the weight for a bulldog?
- Model Response:
Question: What is the weight for a bulldog?
Think: To solve this, I need to perform the dog_weight_for_breed action with the argument bulldog.
Action: dog_weight_for_breed: {{"name": "bulldog"}}
PAUSE

User Provides an Observation:
- Observation: a Bulldogs average weight is 40 lbs

Model Continues:
Observation: a Bulldogs average weight is 40 lbs
Think: Now that I have the result, I can provide the final answer.
Answer: The average weight for a Bulldog is 40 lbs.
""".strip()


class ActionAgent(ABC):
    def __init__(self, name: str, intro: str, actions=None):
        self.log = action_agent_log
        self.log.info("Initializing Agent")
        self.name = name
        self.intro = intro
        self.model = "eu.amazon.nova-lite-v1:0"
        self.client = boto3.client("bedrock-runtime", region_name="eu-west-1")

        # Initialize the messages with the system message
        self.memory = []
        self.system_prompt = create_system_prompt(actions, intro)

        # Initialize the known actions
        self.known_actions = {}
        if actions is not None:
            for action, value in actions.items():
                self.known_actions[action] = value["function"]

        self.max_turns = 10
        self.action_re = re.compile(r'^Action: (\w+): (.*)$')
        self.answer_re = re.compile(r'^Answer: (.*)$')

    def __handle_user_message(self, message):
        self.log.info(f"Received message: {message}")
        self.memory.append({"role": "user", "content": [{"text": message}]})
        result = self.__call_llm()
        self.memory.append({"role": "assistant", "content": [{"text": result}]})
        return result

    def perform_action(self, command):
        i = 0
        next_prompt = command
        while i < self.max_turns:
            i += 1
            result = self.__handle_user_message(next_prompt)

            # Check if there is an action to run or an answer to return
            actions = [self.action_re.match(a) for a in result.split('\n') if self.action_re.match(a)]
            if actions:
                next_prompt = self.__execute_action(actions)
            else:
                return self.__extract_answer(result)

    def __execute_action(self, actions):
        action, action_input = actions[0].groups()
        if action not in self.known_actions:
            self.log.error("Unknown action: %s: %s", action, action_input)
            raise Exception("Unknown action: {}: {}".format(action, action_input))

        self.log.info(" -- running %s %s", action, action_input)
        # Parse the JSON string into a dictionary
        action_args = json.loads(action_input)
        # Unpack the dictionary as keyword arguments
        observation = self.known_actions[action](**action_args)

        self.log.info("Observation: %s", observation)
        return f"Observation: {observation}"

    def __extract_answer(self, result):
        answers = [self.answer_re.match(answer) for answer in result.split('\n') if self.answer_re.match(answer)]
        if answers:
            # There is an answer to return
            self.log.info("Final answer: %s", answers[0].groups()[0])
            return answers[0].groups()[0]
        else:
            self.log.error("No action or answer found in: %s", result)
            raise Exception("No action or answer found in: {}".format(result))

    def __call_llm(self) -> str:
        bedrock_response  = self.client.converse(
            modelId=self.model,
            messages=self.memory,
            system = [{"text":  self.system_prompt}],
            inferenceConfig={"maxTokens": 512, "temperature": 0, "topP": 0.9, "stopSequences": ["PAUSE"]},
        )
        self.log.info(f"Response: {bedrock_response["output"]["message"]["content"]}")
        return bedrock_response["output"]["message"]["content"][0]["text"]
