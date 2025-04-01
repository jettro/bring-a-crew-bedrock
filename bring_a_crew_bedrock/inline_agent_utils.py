import json
import os
from datetime import datetime

from rich.console import Console
from rich.markdown import Markdown
from termcolor import colored


def load_json_file(file_path) -> str:
    """Load a JSON file and return its content as a string."""
    with open(file_path, "r") as file:
        data = json.load(file)
    return json.dumps(data, indent=2)


def invoke_inline_agent_helper(client, request_params, trace_level="core"):
    _time_before_call = datetime.now()

    _agent_resp = client.invoke_inline_agent(
        **request_params
    )

    if request_params["enableTrace"]:
        if trace_level == "all":
            print(f"invokeAgent API response object: {_agent_resp}")
        else:
            print(
                f"invokeAgent API request ID: {_agent_resp['ResponseMetadata']['RequestId']}"
            )
            session_id = request_params["sessionId"]
            print(f"invokeAgent API session ID: {session_id}")

    # Return error message if invoke was unsuccessful
    if _agent_resp["ResponseMetadata"]["HTTPStatusCode"] != 200:
        _error_message = f"API Response was not 200: {_agent_resp}"
        if request_params["enableTrace"] and trace_level == "all":
            print(_error_message)
        return _error_message

    _total_in_tokens = 0
    _total_out_tokens = 0
    _total_llm_calls = 0
    _orch_step = 0
    _sub_step = 0
    _trace_truncation_lenght = 300
    _time_before_orchestration = datetime.now()

    _agent_answer = ""
    _event_stream = _agent_resp["completion"]

    try:
        for _event in _event_stream:
            _sub_agent_alias_id = None

            if "chunk" in _event:
                _data = _event["chunk"]["bytes"]
                _agent_answer = _data.decode("utf8")

            if "trace" in _event and request_params["enableTrace"]:
                if "failureTrace" in _event["trace"]["trace"]:
                    print(
                        colored(
                            f"Agent error: {_event['trace']['trace']['failureTrace']['failureReason']}",
                            "red",
                        )
                    )

                if "orchestrationTrace" in _event["trace"]["trace"]:
                    _orch = _event["trace"]["trace"]["orchestrationTrace"]

                    if trace_level in ["core", "outline"]:
                        if "rationale" in _orch:
                            _rationale = _orch["rationale"]
                            print(colored(f"{_rationale['text']}", "blue"))

                        if "invocationInput" in _orch:
                            # NOTE: when agent determines invocations should happen in parallel
                            # the trace objects for invocation input still come back one at a time.
                            _input = _orch["invocationInput"]
                            print(_input)

                            if "actionGroupInvocationInput" in _input:
                                if 'function' in _input['actionGroupInvocationInput']:
                                    tool = _input['actionGroupInvocationInput']['function']
                                elif 'apiPath' in _input['actionGroupInvocationInput']:
                                    tool = _input['actionGroupInvocationInput']['apiPath']
                                else:
                                    tool = 'undefined'
                                if trace_level == "outline":
                                    print(
                                        colored(
                                            f"Using tool: {tool}",
                                            "magenta",
                                        )
                                    )
                                else:
                                    print(
                                        colored(
                                            f"Using tool: {tool} with these inputs:",
                                            "magenta",
                                        )
                                    )
                                    # TODO made a change here to print the inputs
                                    if "parameters" not in _input["actionGroupInvocationInput"]:
                                        print(
                                            colored(
                                                f"  No parameters provided.\n",
                                                "magenta",
                                            )
                                        )
                                    else:
                                        if (
                                            len(
                                                _input["actionGroupInvocationInput"][
                                                    "parameters"
                                                ]
                                            )
                                            == 1
                                        ) and (
                                            _input["actionGroupInvocationInput"][
                                                "parameters"
                                            ][0]["name"]
                                            == "input_text"
                                        ):
                                            print(
                                                colored(
                                                    f"{_input['actionGroupInvocationInput']['parameters'][0]['value']}",
                                                    "magenta",
                                                )
                                            )
                                        else:
                                            print(
                                                colored(
                                                    f"{_input['actionGroupInvocationInput']['parameters']}\n",
                                                    "magenta",
                                                )
                                            )

                            elif "codeInterpreterInvocationInput" in _input:
                                if trace_level == "outline":
                                    print(
                                        colored(
                                            f"Using code interpreter", "magenta"
                                        )
                                    )
                                else:
                                    console = Console()
                                    _gen_code = _input[
                                        "codeInterpreterInvocationInput"
                                    ]["code"]
                                    _code = f"```python\n{_gen_code}\n```"

                                    console.print(
                                        Markdown(f"**Generated code**\n{_code}")
                                    )

                        if "observation" in _orch:
                            if trace_level == "core":
                                _output = _orch["observation"]
                                if "actionGroupInvocationOutput" in _output:
                                    print(
                                        colored(
                                            f"--tool outputs:\n{_output['actionGroupInvocationOutput']['text'][0:_trace_truncation_lenght]}...\n",
                                            "magenta",
                                        )
                                    )

                                if "agentCollaboratorInvocationOutput" in _output:
                                    _collab_name = _output[
                                        "agentCollaboratorInvocationOutput"
                                    ]["agentCollaboratorName"]
                                    _collab_output_text = _output[
                                        "agentCollaboratorInvocationOutput"
                                    ]["output"]["text"][0:_trace_truncation_lenght]
                                    print(
                                        colored(
                                            f"\n----sub-agent {_collab_name} output text:\n{_collab_output_text}...\n",
                                            "magenta",
                                        )
                                    )

                                if "finalResponse" in _output:
                                    print(
                                        colored(
                                            f"Final response:\n{_output['finalResponse']['text'][0:_trace_truncation_lenght]}...",
                                            "cyan",
                                        )
                                    )


                    if "modelInvocationOutput" in _orch:
                        _orch_step += 1
                        _sub_step = 0
                        print(colored(f"---- Step {_orch_step} ----", "green"))

                        _llm_usage = _orch["modelInvocationOutput"]["metadata"][
                            "usage"
                        ]
                        _in_tokens = _llm_usage["inputTokens"]
                        _total_in_tokens += _in_tokens

                        _out_tokens = _llm_usage["outputTokens"]
                        _total_out_tokens += _out_tokens

                        _total_llm_calls += 1
                        _orch_duration = (
                            datetime.now() - _time_before_orchestration
                        )

                        print(
                            colored(
                                f"Took {_orch_duration.total_seconds():,.1f}s, using {_in_tokens+_out_tokens} tokens (in: {_in_tokens}, out: {_out_tokens}) to complete prior action, observe, orchestrate.",
                                "yellow",
                            )
                        )

                        # restart the clock for next step/sub-step
                        _time_before_orchestration = datetime.now()

                elif "preProcessingTrace" in _event["trace"]["trace"]:
                    _pre = _event["trace"]["trace"]["preProcessingTrace"]
                    if "modelInvocationOutput" in _pre:
                        _llm_usage = _pre["modelInvocationOutput"]["metadata"][
                            "usage"
                        ]
                        _in_tokens = _llm_usage["inputTokens"]
                        _total_in_tokens += _in_tokens

                        _out_tokens = _llm_usage["outputTokens"]
                        _total_out_tokens += _out_tokens

                        _total_llm_calls += 1

                        print(
                            colored(
                                "Pre-processing trace, agent came up with an initial plan.",
                                "yellow",
                            )
                        )
                        print(
                            colored(
                                f"Used LLM tokens, in: {_in_tokens}, out: {_out_tokens}",
                                "yellow",
                            )
                        )

                elif "postProcessingTrace" in _event["trace"]["trace"]:
                    _post = _event["trace"]["trace"]["postProcessingTrace"]
                    if "modelInvocationOutput" in _post:
                        _llm_usage = _post["modelInvocationOutput"]["metadata"][
                            "usage"
                        ]
                        _in_tokens = _llm_usage["inputTokens"]
                        _total_in_tokens += _in_tokens

                        _out_tokens = _llm_usage["outputTokens"]
                        _total_out_tokens += _out_tokens

                        _total_llm_calls += 1
                        print(colored("Agent post-processing complete.", "yellow"))
                        print(
                            colored(
                                f"Used LLM tokens, in: {_in_tokens}, out: {_out_tokens}",
                                "yellow",
                            )
                        )

                if trace_level == "all":
                    print(json.dumps(_event["trace"], indent=2))

            if "files" in _event.keys() and request_params["enableTrace"]:
                console = Console()
                files_event = _event["files"]
                console.print(Markdown("**Files**"))

                files_list = files_event["files"]
                for this_file in files_list:
                    print(f"{this_file['name']} ({this_file['type']})")
                    file_bytes = this_file["bytes"]

                    # save bytes to file, given the name of file and the bytes
                    file_name = os.path.join("output", this_file["name"])
                    with open(file_name, "wb") as f:
                        f.write(file_bytes)

        if request_params["enableTrace"]:
            duration = datetime.now() - _time_before_call

            if trace_level in ["core", "outline"]:
                print(
                    colored(
                        f"Agent made a total of {_total_llm_calls} LLM calls, "
                        + f"using {_total_in_tokens+_total_out_tokens} tokens "
                        + f"(in: {_total_in_tokens}, out: {_total_out_tokens})"
                        + f", and took {duration.total_seconds():,.1f} total seconds",
                        "yellow",
                    )
                )

            if trace_level == "all":
                print(f"Returning agent answer as: {_agent_answer}")

        return _agent_answer

    except Exception as e:
        print(f"Caught exception while processing input to invokeAgent:\n")
        input_text = request_params["inputText"]
        print(f"  for input text:\n{input_text}\n")
        print(
            f"  request ID: {_agent_resp['ResponseMetadata']['RequestId']}, retries: {_agent_resp['ResponseMetadata']['RetryAttempts']}\n"
        )
        print(f"Error: {e}")
        raise Exception("Unexpected exception: ", e)