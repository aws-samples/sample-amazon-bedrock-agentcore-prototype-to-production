#!/usr/bin/env python3
"""
Multi-Agent Mortgage Assistant using LangGraph and Amazon Bedrock
Converted to AgentCore compatible format
"""

import os
import json
import boto3
import random
from typing import TypedDict, List, Annotated, Union
from datetime import datetime, timedelta
from textwrap import dedent

from langchain_aws import ChatBedrock, ChatBedrockConverse
from langchain.chat_models import init_chat_model
from langgraph.prebuilt import create_react_agent, ToolNode, tools_condition
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, AnyMessage, SystemMessage, ToolMessage
from langgraph.graph.message import add_messages
from langgraph.graph import MessagesState, StateGraph, START, END
from langchain.tools import tool
from langgraph.checkpoint.memory import InMemorySaver
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from langchain_aws.retrievers import AmazonKnowledgeBasesRetriever
from langchain.tools import Tool
# Import the swarm functionality
from langgraph_swarm import create_handoff_tool, create_swarm
import platform
import sys
import psutil


app = BedrockAgentCoreApp()

# Tool functions
@tool
def get_mortgage_details(customer_id: str) -> str:
    """
    Retrieves the mortgage status for a given customer ID. Returns an object containing 
    details like the account number, outstanding principal, interest rate, maturity date, 
    number of payments remaining, due date of next payment, and amount of next payment.
    """
    return {
        "account_number": customer_id,
        "outstanding_principal": 150599.25,
        "interest_rate": 8.5,
        "maturity_date": "2030-06-30",
        "original_issue_date": "2021-05-30",
        "payments_remaining": 72,
        "last_payment_date": str(datetime.today() - timedelta(days=14)).split(' ')[0],
        "next_payment_due": str(datetime.today() + timedelta(days=14)).split(' ')[0],
        "next_payment_amount": 1579.63
    }

@tool
def get_application_details(customer_id: str) -> str:
    """
    Retrieves the details about an application for a new mortgage. The function takes a customer ID, 
    but it is purely optional. Details include the application ID, application date, application status, 
    application type, application amount, application tentative rate, and application term in years.
    """
    return {
        "customer_id": customer_id,
        "application_id": "998776",
        "application_date": str(datetime.today() - timedelta(days=35)),
        "application_status": "IN_PROGRESS",
        "application_type": "NEW_MORTGAGE",
        "application_amount": 750000,
        "application_tentative_rate": 5.5,
        "application_term_years": 30,
        "application_rate_type": "fixed"
    }

@tool
def get_mortgage_rate_history(day_count: int = 30, type: str = "15-year-fixed"):
    """
    Retrieves the history of mortgage interest rates going back a given number of days, defaults to 30. 
    History is returned as a list of objects, where each object contains the date and the interest rate to 2 decimal places.
    """
    BASE_RATE = 6.00
    RATE_MIN_15 = 38
    RATE_MAX_15 = 48
    RATE_MIN_30 = RATE_MIN_15 + 80
    RATE_MAX_30 = RATE_MAX_15 + 80
    
    today = datetime.today()
    history_count = 0
    rate_history = []

    if type == "30-year-fixed":
        RATE_MIN = RATE_MIN_30
        RATE_MAX = RATE_MAX_30
    else:
        RATE_MIN = RATE_MIN_15
        RATE_MAX = RATE_MAX_15

    for i in range(int(day_count * 1.4)):
        if history_count >= day_count:
            break
        else:
            day = today - timedelta(days=i + 1)
            which_day_of_week = day.weekday()
            if which_day_of_week < 5:
                history_count += 1
                _date = str(day.strftime("%Y-%m-%d"))
                _rate = f"{BASE_RATE + ((random.randrange(RATE_MIN, RATE_MAX)) / 100):.2f}"
                rate_history.append({"date": _date, "rate": _rate})

    return rate_history

@tool
def get_mortgage_app_doc_status(customer_id: str):
    """
    Retrieves the list of required documents for a mortgage application in process, 
    along with their respective statuses (COMPLETED or MISSING).
    """
    return [
        {
            "type": "proof_of_income",
            "status": "COMPLETED"
        },
        {
            "type": "employment_information",
            "status": "MISSING"
        },
        {
            "type": "proof_of_assets",
            "status": "COMPLETED"
        },
        {
            "type": "credit_information",
            "status": "COMPLETED"
        }
    ]



def setup_knowledge_base():
    """Setup knowledge base retriever tool"""

    try:
        ssm = boto3.client("ssm")


        param = ssm.get_parameter(Name="/app/mortgage_assistant/agentcore/kb_id")
        KB_ID = param["Parameter"]["Value"]
        if not KB_ID:
            print("Please run the 01_Prerequisite/01_create_knowledgebase.ipynb notebook first to create and store the KB_ID")
            return None
        print(f"Knowledge base id: {KB_ID}")
        retriever = AmazonKnowledgeBasesRetriever(
            knowledge_base_id=KB_ID,
            retrieval_config={
                "vectorSearchConfiguration": {
                    "numberOfResults": 4
                }
            }
        )
        
        retriever_tool = Tool(
            name="amazon_knowledge_base",
            description="Use this knowledge base to answer general questions about mortgages, like how to refinance, or the difference between 15-year and 30-year mortgages.",
            func=lambda query: "\n\n".join([doc.page_content for doc in retriever.invoke(query)])
        )
        
        print("Knowledge base retriever tool setup successfully")
        return retriever_tool
        
    except Exception as e:
        print(f"Failed to setup knowledge base: {e}")
        return None

def create_mortgage_agent():
    """
    Creates the mortgage agent, which is a multi-agent assistant that can handle
    both existing mortgage and mortgage application assistants.
    """

    # Configure the model
    agent_foundation_model = [
        'us.anthropic.claude-3-5-haiku-20241022-v1:0'
    ]

    bedrock_client = boto3.client('bedrock-runtime')

    model = init_chat_model(
        agent_foundation_model[0],
        model_provider="bedrock_converse",
        temperature=0.7,
        client=bedrock_client
    )

    retriever_tool = setup_knowledge_base() 
    # Memory for multi-agent conversations
    memory = InMemorySaver()
    # Create handoff tools for agent switching
    transfer_to_existing_assistant = create_handoff_tool(
        agent_name="existing_mortgage_agent",
        description="Transfer user to the existing mortgage agent to provide information about current mortgage  details including outstanding principal, interest rates, maturity dates, payment schedules, and upcoming payment information. Use this when the user is asking about their existing mortgage account, payment details, or loan status. "
    )
    
    
    transfer_to_application_assistant = create_handoff_tool(
        agent_name="mortgage_application_agent",
        description="Transfer user to the mortgage application agent to provide assistance with new mortgage applications, document status tracking, application details, and historical mortgage rate information. Use this when the user is asking about applying for a new mortgage, checking application status, or needs information about current mortgage rates."
    )
    
    transfer_to_general_mortgage_agent = create_handoff_tool(
        agent_name="general_mortgage_agent",
        description="Transfer user to the general mortgage agent to use knowledge base to answer general questions about mortgages, like how to refinnance, or the difference between 15-year and 30-year mortgages."
    
    )


    # Create the agents
    general_mortgage_system = """
# General Assistant System Prompt

You are the main routing assistant for a mortgage service system. Your primary role is to understand customer needs and direct them to the appropriate specialist.

## System Information
- Current Date: {current_date}
- System Version: 1.0.0
- Available Services: Existing Mortgage Management, New Applications, General Mortgage Information
- Operating Hours: 24/7 Automated Service

## Your Role
- Greet customers and understand their needs
- Route customers to appropriate specialist agents
- Provide general guidance about available services
- Handle initial inquiries and triage

## Available Specialists
1. **Existing Mortgage Agent** - For customers with questions about their current mortgage accounts
2. **Mortgage Application Agent** - For customers applying for new mortgages or checking application status

## Guidelines
1. **Always greet customers warmly** and ask how you can help
2. **Listen carefully** to understand their specific needs
3. **Route appropriately** based on their inquiry type
4. **Provide brief explanations** of what each specialist can help with
5. **Be helpful and professional** throughout the interaction

## Routing Logic
- **Existing mortgage questions** → Transfer to existing_mortgage_agent
  - Account balances, payment schedules, loan details
  - Interest rates on current loans, maturity dates
  - Payment history and upcoming payments

- **New mortgage applications** → Transfer to mortgage_application_agent
  - Application status and requirements
  - Document submission and tracking
  - Current mortgage rates and application process

## Communication Style
- Friendly and welcoming
- Clear and concise
- Professional yet approachable
- Efficient in routing while being helpful

## What You Should Not Do
- Don't try to handle specialized mortgage questions yourself
- Don't make up information about mortgage details
- Don't provide specific financial advice

Your success is measured by how well you understand customer needs and connect them with the right specialist. 

Remember: Never make up information. Always use your available tools. If a query falls outside your scope, transfer directly to another relevant agent without asking for confirmation, just explain why you are transferring. When you receive the handoff from previous agent, read the context before you respond

## When Receiving Handoffs
When you receive a handoff from another agent:
1. **Acknowledge the transfer** and greet the customer
2. **Review the conversation context** to understand what the customer needs
3. **Continue the conversation** by addressing their specific requests
4. **Use your tools** to provide the requested information
5. **Be proactive** - don't just say you can help, actually help by using your available tools

If the customer asked for multiple things and you were transferred to handle specific parts, make sure to address those parts immediately using your available tools.
"""
    existing_mortgage_system = """
# Existing Mortgage Agent System Prompt

You are a specialized mortgage assistant focused on helping customers with their existing mortgage accounts.

## Your Role
- Provide information about current mortgage details
- Help customers understand their payment schedules
- Retrieve account balances and loan status
- Answer questions about interest rates and maturity dates

## Guidelines
1. **Always greet customers warmly** when starting a new session
2. **Use available tools** to retrieve information rather than asking customers for data you can access
3. **Stay focused** on existing mortgage topics only
4. **Be proactive** in retrieving relevant information
5. **Provide clear, accurate information** about mortgage details

## What You Can Help With
- Outstanding principal balance
- Interest rates and payment history
- Maturity dates and remaining payments
- Next payment due dates and amounts
- Account status and details

## What You Should Not Handle
- New mortgage applications (transfer to mortgage application agent)
- General mortgage advice (stay focused on account-specific information)
- Non-mortgage related inquiries

## Communication Style
- Professional yet friendly
- Clear and concise explanations
- Proactive in offering relevant information
- Patient and helpful

Remember: Never make up information. Always use your available tools to retrieve accurate, current data. If a query falls outside your scope, transfer directly to another relevant agent without asking for confirmation, just explain why you are transferring. When you receive the handoff from previous agent, read the context before you respond

## When Receiving Handoffs
When you receive a handoff from another agent:
1. **Acknowledge the transfer** and greet the customer
2. **Review the conversation context** to understand what the customer needs
3. **Continue the conversation** by addressing their specific requests
4. **Use your tools** to provide the requested information
5. **Be proactive** - don't just say you can help, actually help by using your available tools

If the customer asked for multiple things and you were transferred to handle specific parts, make sure to address those parts immediately using your available tools.
"""

    mortgage_application_system = """
# Mortgage Application Agent System Prompt

You are a specialized mortgage assistant focused on helping customers with new mortgage applications and related processes.

## Your Role
- Assist with new mortgage application processes
- Track document submission status
- Provide current mortgage rate information
- Help customers understand application requirements

## Guidelines
1. **Greet customers warmly** before providing assistance
2. **Use available tools** to retrieve current information
3. **Focus on application-related topics** only
4. **Be thorough** in explaining document requirements
5. **Provide accurate, up-to-date information** about rates and processes

## What You Can Help With
- New mortgage application details and status
- Required document tracking (proof of income, employment info, assets, credit info)
- Document submission status (completed vs missing)
- Historical mortgage rate information
- Application timelines and next steps

## What You Should Not Handle
- Existing mortgage account details (transfer to existing mortgage agent)
- General financial advice unrelated to mortgage applications
- Non-mortgage related inquiries

## Communication Style
- Professional and supportive
- Clear explanations of complex processes
- Encouraging and patient
- Detail-oriented when explaining requirements

## Document Types You Track
- Proof of income
- Employment information
- Proof of assets
- Credit information

Remember: Always use your available tools to get the most current information. Never make assumptions about document status or application details.  If a query falls outside your scope, transfer directly to another relevant agent without asking for confirmation, just explain why you are transferring.

## When Receiving Handoffs
When you receive a handoff from another agent:
1. **Acknowledge the transfer** and greet the customer
2. **Review the conversation context** to understand what the customer needs
3. **Continue the conversation** by addressing their specific requests
4. **Use your tools** to provide the requested information
5. **Be proactive** - don't just say you can help, actually help by using your available tools

If the customer asked for multiple things and you were transferred to handle specific parts, make sure to address those parts immediately using your available tools.
"""
    # Format system prompt with current system info
    system_info = get_system_info()
    formatted_general_system = general_mortgage_system.format(
        current_date=system_info["current_date"]
    )
    
    general_mortgage_agent = create_react_agent(
        model=model,
        tools=[retriever_tool,transfer_to_existing_assistant,transfer_to_application_assistant],
        prompt=dedent(formatted_general_system),
        name="general_mortgage_agent")
    
    # Define the Agent
    existing_mortgage_agent = create_react_agent(
        model=model,
        tools=[get_mortgage_details,transfer_to_application_assistant, transfer_to_general_mortgage_agent],
        prompt=dedent(existing_mortgage_system),
        name="existing_mortgage_agent"
    )
    
    # Define the Agent
    mortgage_application_agent = create_react_agent(
        model=model,
        tools=[get_application_details,get_mortgage_rate_history,get_mortgage_app_doc_status,
               transfer_to_existing_assistant,transfer_to_general_mortgage_agent],
        prompt=dedent(mortgage_application_system),
        name="mortgage_application_agent")

    # Create the multi-agent graph
    multi_agent_graph = create_swarm([existing_mortgage_agent,mortgage_application_agent,
                                      general_mortgage_agent],default_active_agent="general_mortgage_agent")
    # Compile the graph to make it invokable
    return multi_agent_graph.compile(checkpointer=memory)

mortgage_agent = create_mortgage_agent()

def convert_langgraph_to_agentcore(messages):
    """Convert LangGraph messages to AgentCore compatible format"""
    converted_messages = []
    
    for message in messages:
        if hasattr(message, 'content') and hasattr(message, 'type'):
            # Extract basic message info
            msg_data = {
                'type': message.type,
                'content': message.content,
                'id': getattr(message, 'id', None)
            }
            
            # Add metadata if available
            if hasattr(message, 'response_metadata') and message.response_metadata:
                msg_data['metadata'] = message.response_metadata
                
            # Add usage info if available
            if hasattr(message, 'usage_metadata') and message.usage_metadata:
                msg_data['usage'] = message.usage_metadata
                
            converted_messages.append(msg_data)
    
    return converted_messages



@app.entrypoint
def invoke(payload, context):
    print("received payload: ", payload)
    message = payload.get("prompt", "no prompt")
    print("received message: ", message)
    actor = payload.get("actor_id", "user")
    session_id = payload.get("session_id", random.randint(1,10000))
    

    
    response = mortgage_agent.invoke(
        {"messages": message},
        config={"configurable": {"thread_id": session_id}}
    )
    
    converted_messages = convert_langgraph_to_agentcore(response["messages"])
    
    return {
        "messages": converted_messages,
        "active_agent": response.get("active_agent", "existing_mortgage_agent")
    }

if __name__ == "__main__":
    app.run()