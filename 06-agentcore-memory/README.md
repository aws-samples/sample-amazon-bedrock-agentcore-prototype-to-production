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

## Getting Started
Learn how to configure AgentCore Memory for the Mortgage Assistant, the multi-agent application built in Strands in [agentcore_memory.ipynb](agentcore_memory.ipynb).