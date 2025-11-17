# Amazon Bedrock AgentCore Memory

## What is Agentcore Memory
Memory is a critical component of intelligence. While Large Language Models (LLMs) have impressive capabilities, they lack persistent memory across conversations. Amazon Bedrock AgentCore Memory addresses this limitation by providing a managed service that enables AI agents to maintain context over time, remember important facts, and deliver consistent, personalized experiences.

## Key Capabilities
AgentCore Memory provides:

* Core Infrastructure: Serverless setup with built-in encryption and observability
* Event Storage: Raw event storage (conversation history/checkpointing) with branching support
* Strategy Management: Configurable extraction strategies (SEMANTIC, SUMMARY, USER_PREFERENCES, CUSTOM)
* Memory Records Extraction: Automatic extraction of facts, preferences, and summaries based on configured strategies
* Semantic Search: Vector-based retrieval of relevant memories using natural language queries

## How AgentCore Memory Works
![high_level_memory.png](images/high_level_memory.png)

### Short-Term Memory

Immediate conversation context and session-based information that provides continuity within a single interaction or closely related sessions.

### Long-Term Memory

Persistent information extracted and stored across multiple conversations, including facts, preferences, and summaries that enable personalized experiences over time.

## Memory Architecture

1. **Conversation Storage**: Complete conversations are saved in raw form for immediate access
2. **Strategy Processing**: Configured strategies automatically analyze conversations in the background
3. **Information Extraction**: Important data is extracted based on strategy types (typically takes ~1 minute)
4. **Organized Storage**: Extracted information is stored in structured namespaces for efficient retrieval
5. **Semantic Retrieval**: Natural language queries can retrieve relevant memories using vector similarity

## Memory Strategy Types

AgentCore Memory supports four strategy types:

- **Semantic Memory**: Stores factual information using vector embeddings for similarity search
- **Summary Memory**: Creates and maintains conversation summaries for context preservation
- **User Preference Memory**: Tracks user-specific preferences and settings
- **Custom Memory**: Allows customization of extraction and consolidation logic

## AgentCore Memory Integration
This workshop demonstrates two approaches for integrating AgentCore Memory with Strands Agents:

**Option 1: Using Strands Agents Hooks**

This approach leverages [Strands Agents hooks](https://strandsagents.com/latest/documentation/docs/user-guide/concepts/agents/hooks/) to give you fine-grained control over memory store and retrieval
operations. This is ideal if you need custom logic or specific behavior for your memory management, or want to learn exactly how the integration with AgentCore Memory works.

**Option 2: Using AgentCore Memory Session Manager**

This approach uses the [AgentCore Memory Session Manager](https://strandsagents.com/latest/documentation/docs/community/session-managers/agentcore-memory/), which is quick to set up and easy to use. It's automatic and transparent - developers don't need to manually manage memory operations. The session manager handles everything through Strands' lifecycle hooks. On the flip side, you will need to learn how Strands Agents and AgentCore Memory Session Manager work under the hood.

## Getting Started

- **Option 1**: See [option_1_agentcore_memory_with_strands_agents_hooks.ipynb](option_1_agentcore_memory_with_strands_agents_hooks.ipynb) for the hooks-based approach
- **Option 2**: See [option_2_agentcore_memory_with_strands_session_manager.ipynb](option_2_agentcore_memory_with_strands_session_manager.ipynb) for the session manager approach

Choose Option 1 for maximum flexibility or learning, or Option 2 for simplicity and convenience.
