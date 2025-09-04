#!/usr/bin/env python3
"""
Mortgage Assistant Agent using LangGraph and Amazon Bedrock
Converted from Jupyter notebook to standalone Python script
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
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, AnyMessage, SystemMessage
from langgraph.graph.message import add_messages
from langgraph.graph import MessagesState, StateGraph, START, END
from langchain.tools import tool
from langfuse import get_client
from langfuse.langchain import CallbackHandler
from bedrock_agentcore.runtime import BedrockAgentCoreApp

app = BedrockAgentCoreApp()


class AgentState(MessagesState):
    pass


@tool
def get_mortgage_details(customer_id: str) -> str:
    """
    Retrieves the details about an application for a new mortgage.
    The function takes a customer ID, but it is purely optional. The function
    implementation can retrieve it from session state instead. Details include
    the application ID, application date, application status, application type,
    application amount, mortgage interest, and application term in years
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


def create_customer_id():
    """
    Creates customer ID
    """
    return "123456"


def create_loan_application(customer_id, name, age, annual_income, annual_expense):
    """Creates a new loan application using the details provided. The details include the name,
    age, customer_id, annual_income and annual_expense
    """
    print(f"creating loan application for customer: {customer_id}...")
    print(f"customer name: {name}")
    print(f"customer age: {age}")
    print(f"customer annual income: {annual_income}")
    print(f"customer annual expense: {annual_expense}")
    return {
        "customer_id": customer_id,
        "customer_name": name,
        "age": age,
        "annual_income": annual_income,
        "annual_expense": annual_expense,
        "application_date": datetime.now().strftime("%Y-%m-%d"),
        "message": "Loan application successfully created"
    }


def get_mortgage_app_doc_status(customer_id):
    """Retrieves the list of required documents for a mortgage application in process, 
    along with their respective statuses (COMPLETED or MISSING). 
    The function takes a customer ID, but it is purely optional. The function
    implementation can retrieve it from session state instead.
    This function returns a list of objects, where each object represents 
    a required document type. 
    The required document types for a mortgage application are: proof of income, employment information, 
    proof of assets, and credit information. Each object in the returned list contains the type of the 
    required document and its corresponding status.
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


def create_mortgage_agent():
    """Create and return the mortgage agent"""
    
    # Set up AWS profile if needed (uncomment if running locally)
    # os.environ['AWS_PROFILE'] = 'your-profile-name'
    
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
    
    # Define the system prompt
    system = """
    You are a mortgage bot for creating, managing, and completing an application for a new mortgage. you greet the customer before your answer.
You first ask customers for their customer id. If they don't have any then you use the tool to create a new customer id and tell the user that you have created a new customer id and show it to them.
Next, you ask for their name, age, annual income and annual expense. Ask one question at a time. If they cant answer any of the questions then its fine, you just move forward. 
Once you have all the information use the tool to create a new loan application for this customer. 
After creating the loan application give the customer their newly created customer id if they didn't provide one initially.
never make up information that you are unable to retrieve from your available actions. 
do not engage with users about topics other than an existing mortgage. leave those other topics for other experts to handle. for example, do not respond to general questions about mortgages. However, respond to the greeting by another greeting
    """
    
    # Create the agent
    existing_mortgage_agent = create_react_agent(
        model=model,
        tools=[get_mortgage_details, create_customer_id, create_loan_application, get_mortgage_app_doc_status],
        prompt=dedent(system)
    )
    
    return existing_mortgage_agent


existing_mortgage_agent = create_mortgage_agent()


def convert_langgraph_to_agentcore(messages):
    """Convert LangGraph messages to AgentCore compatible format"""
    converted_messages = []
    
    for message in messages:
        if hasattr(message, 'content') and hasattr(message, 'type'):
            # Extract basic message info
            msg_data = {
                'type': message.type,  # 'human' or 'ai'
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
def invoke(payload,context):
    print("received payload: ", payload)
    message = payload.get("prompt","no prompt")
    print("received message: ", message)
    actor = payload.get("actor_id", "user")
    response = existing_mortgage_agent.invoke({"messages": message})
    converted_messages = convert_langgraph_to_agentcore(response["messages"])

    return {
        "messages": converted_messages
    }
    
    return response
if __name__ == "__main__":
    app.run()
