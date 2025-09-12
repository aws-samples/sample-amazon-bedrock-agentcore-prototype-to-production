
# Mortgage assistant - AgentCore runtime integration

## What you will learn

* Use Amazon Bedrock AgentCore Python SDK to transform your agent code into AgentCore standardised protocols
* Configure and launch your Strands agent application onto AgentCore runtime. Invoke the agent through the runtime.


## Architecture diagram

The Strands agent which was built in the [Strands-mortgage-assistant](../../Strands-mortgage-assistant/) is now launched on the AgentCore runtime. The architecture will look as below

<img src="../../images/agentcore-runtime.png" alt="agentcore-runtime.png"/>

# Steps to run

 * We have provided the Strands based mortgage assistant transformed to Amazon Bedrock AgentCore-compatible service [mortgage_agent_runtime.py](./mortgage_agent_runtime.py). Examine the code changes.

## How Strands Agent is Wrapped for AgentCore Runtime

The transformation from a standalone Strands agent to an AgentCore runtime-compatible service requires **only 5 lines of code**:

```python
# 1. Import AgentCore - Brings in the runtime wrapper framework
from bedrock_agentcore import BedrockAgentCoreApp

# 2. Create app instance - Initializes the AgentCore runtime container
app = BedrockAgentCoreApp()

# 3. Add entrypoint decorator - Marks this function as the runtime entry point
@app.entrypoint
# 4. Create invoke function - Handles incoming requests and calls your existing agent
def invoke(payload):
    user_message = payload.get("prompt", "default message")
    result = supervisor_agent(user_message)  # Your existing Strands agent unchanged
    return {"result": result.message}

# 5. Run the app - Starts the AgentCore runtime server
if __name__ == "__main__":
    app.run()
```

**That's it!** Your existing Strands agent logic remains completely unchanged. The AgentCore wrapper handles all the runtime protocol, payload parsing, and response formatting automatically.

* Run the [agentcore_runtime.ipynb](./agentcore_runtime.ipynb) notebook which packages and deploys the agent application on to the runtime. You will also invoke the agent from this notebook and look at the response.

## Related AWS Documentation

- [Host agent or tools with Amazon Bedrock AgentCore Runtime](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/agents-tools-runtime.html) - Learn how to host agents using AgentCore Runtime
- [Getting started with Amazon Bedrock AgentCore Runtime](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-getting-started.html) - Getting started guide for AgentCore Runtime
- [Strands Agents - AWS Prescriptive Guidance](https://docs.aws.amazon.com/prescriptive-guidance/latest/agentic-ai-frameworks/strands-agents.html) - Learn about Strands Agents framework
- [Troubleshoot AgentCore Runtime](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-troubleshooting.html) - Solutions to common runtime issues




