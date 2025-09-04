import os
import io
import time
import boto3
import logging
import botocore
import json
from textwrap import dedent
import sys
from datetime import datetime, timedelta
from strands.tools.mcp import MCPClient
from mcp.client.streamable_http import streamablehttp_client

from strands import Agent, tool
from strands_tools import retrieve, calculator

# agentcore imports
from bedrock_agentcore import BedrockAgentCoreApp
from bedrock_agentcore.tools.code_interpreter_client import code_session

# Set up logging specifically for Strands components
loggers = [
  'strands',
  'strands.agent',
  'strands.tools',
  'strands.models',
  'strands.bedrock'
]
for logger_name in loggers:
  logger = logging.getLogger(logger_name)
  logger.setLevel(logging.INFO)
  # Add console handler if not already present
  if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

app = BedrockAgentCoreApp()

session = boto3.Session()
region = session.region_name
print(f"current region: {region}")

modelID="us.anthropic.claude-3-5-haiku-20241022-v1:0"

# get the kb id from AWS SSM
def setup_knowledge_base():
    try:
        ssm = boto3.client("ssm")
        param = ssm.get_parameter(Name="/app/mortgage_assistant/agentcore/kb_id")
        KB_ID = param["Parameter"]["Value"]
        if not KB_ID:
            print("Please run the 01_Prerequisite/01_create_knowledgebase.ipynb notebook first to create and store the KB_ID")
            return None
        print(f"Knowledge base id: {KB_ID}")
        return KB_ID
    except Exception as e:
        print(f"Error retrieving KB_ID from SSM: {e}")
        return None

# 4. Create Agent for General Mortgage Questions
#We will be creating an agent to answer general mortgage questions providing it the **retrieve** tool to access the Knowledge Base created earlier.

@tool
def answer_general_mortgage_questions(query):
    # Create the General Mortgage Agent
    #retrieve KB
    KB_ID = setup_knowledge_base()

    if not KB_ID:
        return "Knowledge base is unavailable."
    
    os.environ['KNOWLEDGE_BASE_ID'] = KB_ID
    general_mortgage_agent = Agent(
        model=modelID,
        tools=[
           retrieve
        ],
        system_prompt="""
        You are a mortgage bot, and can answer questions about mortgage refinancing and tradeoffs of mortgage types. Greet the customer first.

        IMPORTANT: Always use the retrieve tool to search the knowledge base before answering any mortgage-related questions.

        You can:
        1. Provide general information about mortgages
        2. Handle conversations about general mortgage questions, like high level concepts of refinancing or tradeoffs of 15-year vs 30-year terms.
        3. Offer guidance on the mortgage refinancing and tradeoffs of mortgage types.
        4. Access a knowledge base of mortgage information using the retrieve tool
        5. Only answer from the knowledge base and not from your general knowledge. If you dont have the answer from Knowledge base, say "I dont know"

        When helping users:
        - ALWAYS call the retrieve tool first to search for relevant information
        - Provide clear explanations based on retrieved information
        - Use plain language to explain complex financial terms
        - Offer balanced advice considering both pros and cons
        - Be informative without making specific financial recommendations

        Remember that you're providing general mortgage information, not financial advice.
        Always clarify that users should consult with a financial advisor for personalized advice.
        """
    )
    return str(general_mortgage_agent(query))

# 5. Create Agent for Existing Mortgage Questions

#Create the Agent for managing existing mortgages, for example you can ask when is your next payment due, etc.
   
@tool
def get_mortgage_details(customer_id):
    # TODO: Implement real business logic to retrieve mortgage status
    return {
        "account_number": customer_id,
        "outstanding_principal": 150000.0,
        "interest_rate": 4.5,
        "maturity_date": "2030-06-30",
        "payments_remaining": 72,
        "last_payment_date": "2024-06-01",
        "next_payment_due": "2024-07-01",
        "next_payment_amount": 1250.0
    }


@tool
def answer_existing_mortgage_questions(query):
    # Create the Existing Mortgage Agent
    existing_mortgage_agent = Agent(
        model=modelID,
        tools=[
           get_mortgage_details
        ],
        system_prompt="""
        You are an Existing Mortgage Assistant that helps customers with their current mortgages.

        You can:
        1. Provide information about a customer's existing mortgage
        2. Check mortgage status including balance and payment information
        3. Evaluate refinancing eligibility
        4. Calculate payoff timelines with extra payments
        5. Answer questions about mortgage terms and conditions

        When helping users:
        - Always verify the customer ID before providing information
        - Provide clear explanations of mortgage details
        - Format financial data in a readable way
        - Explain payment schedules and upcoming due dates
        - Offer guidance on refinancing options when appropriate
        - Use the knowledge base for detailed information when needed

        Remember that you're dealing with sensitive financial information, so maintain a professional tone
        and ensure accuracy in all responses.
        """
    )
    return str(existing_mortgage_agent(query))

# 6. Create Agent for New Loan Applications

# Now we'll create an agent to handle new mortgage loan applications.
@tool
def get_mortgage_app_doc_status(customer_id: str = None):
    """Retrieves the list of required documents for a mortgage application"""
    return [
        {"type": "proof_of_income", "status": "COMPLETED"},
        {"type": "employment_information", "status": "MISSING"},
        {"type": "proof_of_assets", "status": "COMPLETED"},
        {"type": "credit_information", "status": "COMPLETED"}
    ]

@tool
def get_application_details(customer_id: str = None):
    """Retrieves details about a mortgage application"""
    return {
        "customer_id": customer_id or "123456",
        "application_id": "998776",
        "application_date": str(datetime.today() - timedelta(days=35)),
        "application_status": "IN_PROGRESS",
        "application_type": "NEW_MORTGAGE",
        "name": "Mithil"
    }

@tool
def create_customer_id():
    """Creates a new customer ID"""
    return "123456"

@tool
def create_loan_application(customer_id: str, name: str, age: int, annual_income: int, annual_expense: int):
    """Creates a new loan application"""
    print(f"Creating loan application for customer: {customer_id}")
    print(f"Customer name: {name}")
    print(f"Customer age: {age}")
    print(f"Customer annual income: {annual_income}")
    print(f"Customer annual expense: {annual_expense}")
    return f"Loan application created successfully for {name} (ID: {customer_id})"

@tool
def answer_new_loan_application_questions(query):
    """Tool that handles new loan application questions using a specialized agent"""
    # Create the New Loan Application Agent
    new_loan_application_agent = Agent(
        model=modelID,
        tools=[
            get_mortgage_app_doc_status, 
            get_application_details, 
            create_customer_id, 
            create_loan_application
        ],
        system_prompt="""You are a mortgage application agent that helps customers with new mortgage applications.
        
        Instructions:
        - Greet customers warmly before answering
        - First ask for their customer ID, if they don't have one, create a new one
        - Ask for name, age, annual income, and annual expense one question at a time
        - Once you have all information, create the loan application
        - Only discuss mortgage applications, not general mortgage topics
        - Never make up information you cannot retrieve from tools"""
    )
    
    return str(new_loan_application_agent(query))


# 7. Create Code Interpreter Tool for Dynamic Mortgage Analysis

@tool
def compare_fortnightly_vs_monthly_payments(loan_amount: float, interest_rate: float, 
                                          loan_term_years: int = 30) -> str:
    """
    Get requirements for fortnightly vs monthly payment analysis. This will prompt you to 
    generate Python code for the specific loan parameters.
    
    Args:
        loan_amount: Principal loan amount in dollars
        interest_rate: Annual interest rate as percentage (e.g., 6.5 for 6.5%)
        loan_term_years: Loan term in years (default 30)
    
    Returns:
        Requirements for generating Python code to compare payment frequencies
    """
    
    requirements = f"""

## Task
Generate executable Python code to analyze and compare fortnightly versus monthly mortgage payment strategies.

## Input Parameters
<loan_details>
- Principal loan amount: Loan Parameters:
- Principal: ${loan_amount:,.2f}
- Interest Rate:
- Interest rate: {interest_rate}%
- Loan term: #{loan_term_years} years
</loan_details>

## Technical Requirements
Your code must:
1. Use standard Python libraries only (no external dependencies like numpy/pandas)
2. Implement the standard mortgage formula: M = P * [r(1+r)^n] / [(1+r)^n - 1] where:
   - M = payment amount
   - P = principal loan amount
   - r = interest rate per payment period
   - n = total number of payments

## Calculation Requirements
The code should:
- Calculate standard monthly payments (12 payments per year)
- Calculate fortnightly payments (26 payments per year, typically half the monthly payment)
- Implement an amortization loop to determine the exact payoff time for fortnightly payments
- Calculate total interest paid under both payment methods
- Determine the time and interest savings achieved with fortnightly payments

## Output Requirements
The code should produce:
1. Properly formatted currency values (with commas and dollar signs)
2. A detailed breakdown of all calculations
3. A clear recommendation with specific dollar amounts saved
4. Explanation of why one payment method is advantageous over the other

## Execution
After generating the complete, accurate, and executable code, use the execute_python_code function to run it and display the results.

Focus exclusively on comparing fortnightly versus monthly payment strategies for this mortgage scenario.
    """
    
    return requirements

@tool
def execute_python_code(code: str, description: str = "Python code execution") -> str:
    """
    Execute Python code in secure sandbox environment for mortgage calculations.
    
    Args:
        code: Python code to execute
        description: Description of what the code does
    
    Returns:
        Results of the code execution including output and any generated files
    """
    
    print(f"\\nExecuting: {description}")
    print(f"Code length: {len(code)} characters")
    
    try:
        with code_session(region) as code_client:
            response = code_client.invoke("executeCode", {
                "code": code,
                "language": "python",
                "clearContext": False
            })
        
        for event in response["stream"]:
            return json.dumps(event["result"])
            
    except Exception as e:
        return json.dumps({
            "isError": True,
            "content": [{"type": "text", "text": f"Error executing code: {str(e)}"}]
        })

# 8. Create Supervisor Agent

# Create the supervisor agent and provide all specialized agent tools. The the MCP tool exposed though the credit-check MCP server will be moved to AgentCore Gateway. 

def create_supervisor_agent():
    """
    Create a supervisor agent that coordinates between the specialized agents
    and integrates MCP tools through AgentCore Gateway
    
    Returns:
        Agent: The supervisor agent

    TODO: integrate agentcore gateway
    """
   
    # Define supervisor system prompt
    supervisor_system_prompt = """
    # Mortgage Assistant Supervisor

## Role and Responsibilities
You are a specialized Mortgage Assistant Supervisor responsible for providing a comprehensive customer service experience for all mortgages related inquiries. Your primary function is to route customer questions to the appropriate specialized tools and synthesize responses into clear, helpful answers.

## Available Tools and When to Use Them

<tools>
1. **answer_general_mortgage_questions**
   - Use for: General mortgage information, concepts, terminology, and any questions not covered by other specialized tools
   - Example queries: "How do mortgage rates work?", "What is LVR?", "What documents do I need for a mortgage?"

2. **answer_existing_mortgage_questions**
   - Use for: Any inquiries about a customer's current mortgage
   - Example queries: "What's my current interest rate?", "How much do I still owe?", "Can I make extra repayments?"

3. **answer_new_loan_application_questions**
   - Use for: Questions about applying for a new mortgage
   - Example queries: "How do I apply for a mortgage?", "Am I eligible for a home loan?", "What rates can I get as a first-time buyer?"

4. **Payment Comparison Tools** (For fortnightly vs monthly payment comparisons ONLY)
   - When a customer specifically asks about comparing fortnightly vs monthly payments, follow this exact sequence:
     a. Use **compare_fortnightly_vs_monthly_payments** to gather detailed requirements
     b. **IMPORTANT**: After receiving the requirements, YOU must generate Python code that fulfills those requirements using the customer's specific loan parameters
     c. Use **execute_python_code** to run your generated Python code in the secure sandbox
   - The requirements will specify exactly what calculations, visualizations, and outputs are needed
   - Generate complete, executable Python code that implements the mortgage formula and creates the required comparisons
   - Only use for: "Fortnightly vs monthly payments", "Payment frequency comparison", "Interest savings from fortnightly payments"
</tools>

## Process Guidelines
1. Identify the nature of the customer's query
2. Select the appropriate tool based on the query type
3. Use ONLY ONE tool per response unless specifically handling a fortnightly vs monthly payment comparison
4. For payment comparison requests, follow the three-step process exactly as outlined
5. Synthesize the information from the tool's response into a comprehensive, customer-friendly answer
6. Never mention the tools by name in your response to the customer

## Important Restrictions
- Do NOT use the payment comparison tools for any calculations other than fortnightly vs monthly payment comparisons
- Always generate Python code dynamically based on the specific customer scenario
- Do not attempt to perform complex calculations without using the appropriate tools

## Code Generation Instructions
When handling payment comparison requests:
1. After calling **compare_fortnightly_vs_monthly_payments**, you will receive detailed requirements
2. **YOU must write the Python code** that implements those requirements using the customer's loan parameters
3. Your generated code should be complete, executable, and include all required calculations and visualizations
4. Then call **execute_python_code** with your generated code to run it in the sandbox
5. Present the results to the customer in a clear, helpful format

When responding to customers, maintain a helpful, knowledgeable, and professional tone while providing accurate information about mortgages.
 """
    
    # Combine custom tools with MCP tools
    all_tools = [
        answer_general_mortgage_questions, 
        answer_existing_mortgage_questions,
        answer_new_loan_application_questions,
        compare_fortnightly_vs_monthly_payments,
        execute_python_code,
        calculator
    ]
    
    # Create the supervisor agent
    supervisor = Agent(
        model=modelID,
        system_prompt=supervisor_system_prompt,
        tools=all_tools
    )
    
    return supervisor



supervisor_agent = create_supervisor_agent()

'''
prompt = "why do so many people choose a 30-year mortgage??"

print(supervisor_agent(prompt))

'''

@app.entrypoint
def invoke(payload):
    """Process user input and return a response"""
    user_message = payload.get("prompt", "why do so many people choose a 30-year mortgage??")
    result = supervisor_agent(user_message)
    return {"result": result.message}

if __name__ == "__main__":
    app.run()
