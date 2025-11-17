import os
import boto3
from boto3.session import Session
import logging
import utils
from datetime import datetime, timedelta
from strands.tools.mcp import MCPClient
from mcp.client.streamable_http import streamablehttp_client
from strands.tools.mcp.mcp_client import MCPClient

from strands import Agent, tool
from strands_tools import retrieve, calculator

from bedrock_agentcore import BedrockAgentCoreApp
from bedrock_agentcore.memory import MemoryClient
from botocore.exceptions import ClientError
from bedrock_agentcore.memory.integrations.strands.session_manager import AgentCoreMemorySessionManager
from bedrock_agentcore.memory.integrations.strands.config import AgentCoreMemoryConfig, RetrievalConfig


# Set up logging specifically for Strands components
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
logger = logging.getLogger("agentcore-memory")

app = BedrockAgentCoreApp()
modelID="us.anthropic.claude-3-7-sonnet-20250219-v1:0"

# 4. Create Agent for General Mortgage Questions
#We will be creating an agent to answer general mortage questions providing it the **retrieve** tool to access the Knowledge Base created earlier.

@tool
def answer_general_mortgage_questions(query):
    # Create the General Mortgage Agent
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

# 7. Create Supervisor Agent

# Create the supervisor agent and provide all specialized agent tools. The the MCP tool exposed though the credit-check MCP server will be moved to AgentCore Gateway. 

# Global MCP client
token_response = utils.get_token(utils.get_ssm_parameter("/app/mortgageagent/agentcore/user_pool_id"), utils.get_ssm_parameter("/app/mortgageagent/agentcore/client_id"), utils.get_ssm_parameter("/app/mortgageagent/agentcore/client_secret"),utils.get_ssm_parameter("/app/mortgageagent/agentcore/scope"),'us-west-2')
token = token_response["access_token"]
MCP_SERVER_URL = utils.get_ssm_parameter("/app/mortgageagent/agentcore/gatewayURL")
mcp_client = MCPClient(lambda: streamablehttp_client(MCP_SERVER_URL, headers={"Authorization": f"Bearer {token}"}))

def create_supervisor_agent(query, session_manager):
    """
    Create a supervisor agent that coordinates between the specialized agents
    and integrates MCP tools through AgentCore Gateway
    """
    supervisor_system_prompt = """
    Your role is to provide a unified experience for all things related to mortgages. You are a supervisor who oversees answering
    customer questions related to general mortgages questions, queries about existing mortgages, and new loan applications.

    For general questions, use the answer_general_mortgage_questions tool.
    For questions on existing mortgage, use the answer_existing_mortgage_questions tool.
    For new loan applications, use the answer_new_loan_application_questions tool.
    If asked for a complicated calculation, use your code interpreter to be sure it's done accurately.
    You also have access to MCP tools that can perform additional function to get the credit score of existing customer by passing the customer id from the prompt.
    IMPORTANT: When using credit check tools, return ONLY the credit score value without additional analysis or explanations.
    Use these tools when appropriate for the customer's query.
    Synthesize the details from the response of the tools used into a comprehensive answer provided back to the customer.
    """

    # Base tools without MCP
    base_tools = [
        answer_general_mortgage_questions, 
        answer_existing_mortgage_questions,
        answer_new_loan_application_questions,
        calculator
    ]

    with mcp_client:
        try:
            mcp_tools = mcp_client.list_tools_sync()
            all_tools = base_tools + mcp_tools
            logger.info(f"Mortgage Assistant runtime - create_supervisor_agent() all_tools: {all_tools}")
            
            logger.info(f"Mortgage Assistant runtime - create_supervisor_agent() now create supervisor agent with all tools")
            agent = Agent(
                model=modelID,
                system_prompt=supervisor_system_prompt,
                tools=all_tools,
                session_manager=session_manager)
            logger.info(f"Mortgage Assistant runtime - create_supervisor_agent() supervisor agent with all tools created")
            return agent(query)
        except Exception as e:
            print(f"Error creating supervisor agent with MCP tools: {str(e)}")
            print("Creating supervisor agent without MCP tools")
            
            logger.info(f"Mortgage Assistant runtime - create_supervisor_agent() Failed to create supervisor with all tools: {str(e)}")
            logger.info(f"Mortgage Assistant runtime - create_supervisor_agent() now create supervisor agent with base tools only")
            all_tools = base_tools
            
            agent =  Agent(
                model=modelID,
                system_prompt=supervisor_system_prompt,
                tools=all_tools,
                session_manager=session_manager)
            logger.info(f"Mortgage Assistant runtime - create_supervisor_agent() supervisor agent with base tools only")
            return agent(query)

def get_memory_id_from_ssm():
    param_name = "/app/mortgage_assistant/agentcore/memory_id"
    ssm = boto3.client("ssm")
    try:
        response = ssm.get_parameter(Name=param_name)
        memory_id = response["Parameter"]["Value"]
        logger.info(f"Mortgage Assistant runtime - get_memory_id_from_ssm memory_id: {memory_id}")
        return memory_id
    except ClientError as e:
        raise Exception(f"Could not retrieve memory_id from SSM: {e}")

def get_kb_id_from_ssm():
    param_name = '/app/mortgage_assistant/agentcore/kb_id'
    ssm = boto3.client("ssm")
    try:
        response = ssm.get_parameter(Name=param_name)
        kb_id = response["Parameter"]["Value"]
        logger.info(f"Mortgage Assistant runtime - get_kb_id_from_ssm kb_id: {kb_id}")
        return kb_id
    except ClientError as e:
        raise Exception(f"Could not retrieve kb_id from SSM: {e}")
        
############################
memory_id = None
memory_client = None
user_id_global = None
session_id_globl = None

kb_id = get_kb_id_from_ssm()
logger.info(f"Mortgage Assistant runtime - KnowledgeBase ID: {kb_id}")
# Set knowledge base ID as environment variable so that Strands retrieve tool can use it
os.environ["KNOWLEDGE_BASE_ID"] = kb_id
logger.info("Mortgage Assistant runtime - package level done")

@app.entrypoint
def invoke(payload, context):
    """Process user input and return a response"""
    global memory_id
    global memory_client
    global user_id_global
    global session_id_globl
    global kb_id

    user_message = payload.get("prompt")
    
    user_id = payload.get("user_id")
    if not user_id:
        raise Exception("Payload user_id is not set")
    user_id_global = user_id
        
    session_id = context.session_id
    if not session_id:
        raise Exception("Context session_id is not set")
    session_id_globl = session_id
    
    boto_session = Session()
    region = boto_session.region_name

    logger.info(f"Mortgage Assistant runtime - app.entrypoint invoke() method. region: {region}")
    logger.info(f"Mortgage Assistant runtime - user_message: {user_message}")
    logger.info(f"Mortgage Assistant runtime - user_id: {user_id}")
    logger.info(f"Mortgage Assistant runtime - session_id: {session_id}")

    if memory_id is None:
        memory_id = get_memory_id_from_ssm()
        logger.info(f"Mortgage Assistant runtime - memory_id: {memory_id}")

    if memory_client is None:
        memory_client=MemoryClient(region_name=region)
        logger.info(f"Mortgage Assistant runtime - memory_client is created.")
    
    config = AgentCoreMemoryConfig(
        memory_id=memory_id,
        session_id=session_id_globl,
        actor_id=user_id_global,
        retrieval_config={
            "mortgage_assistant/{actorId}/preferences": RetrievalConfig(
                top_k=5,
                relevance_score=0.7
            ),
            "mortgage_assistant/{actorId}/facts": RetrievalConfig(
                top_k=5,
                relevance_score=0.7
            ),
            "mortgage_assistant/{actorId}/{sessionId}": RetrievalConfig(
                top_k=5,
                relevance_score=0.7
            )
        }
    )
    session_manager = AgentCoreMemorySessionManager(config, region_name=region)

    logger.info(f"Mortgage Assistant runtime - creating supervisor_agent")
    result = create_supervisor_agent(user_message, session_manager)
    return {"result": result.message}

if __name__ == "__main__":
    app.run()
