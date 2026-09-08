# Imports

import os
from dotenv import load_dotenv
from openai.types.responses.response_input_param import McpApprovalResponse, ResponseInputParam

from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import (
    PromptAgentDefinition,
    MicrosoftFabricPreviewTool,
    FabricDataAgentToolParameters,
    ToolProjectConnection,
    MCPTool,
)

# Load environment variables
load_dotenv('parameters.env')

# Configure foundry project endpoint and Azure OpenAI model
endpoint = os.getenv("endpoint")
gpt_4o_model = os.getenv('gpt-4o-model')

#Configure fabric connection
fabric_connection_name = os.getenv('fabric_connection_name')

#Knowledgebase details
server_label=os.getenv("server_label")
server_url=os.getenv("server_url")
project_connection_id=os.getenv("project_connection_id")

# Initialize the AI Project client
with (
    DefaultAzureCredential() as credential,
    AIProjectClient(endpoint=endpoint, credential=credential, allow_preview=True) as project_client,
    project_client.get_openai_client() as openai_client,
):
    # Define MCP tool for knowledge retrieval
    mcp_tool = MCPTool(
        server_label=server_label,
        server_url=server_url,
        project_connection_id = project_connection_id,
        require_approval="never",
    )


    # Create Reward Campaign Agent
    reward_campaign_agent = project_client.agents.create_version(
        agent_name="Rewards-Campaign-Agent",
        definition=PromptAgentDefinition(
            model=gpt_4o_model,
            instructions="""Apply personalized discounts to customers based on their loyalty information and explain the applicable Black Friday promotional tiers using the provided knowledge sources.
            ________________________________________
            Response Behavior
            •	Generate responses only from the retrieved knowledge and tool outputs. Do not assume or invent any values.
            •	When a customer name is included, respond in a friendly first-person tone and include celebratory emojis such as 🎉, 😊, or 🛍️.
            •	When the internal team asks about discount tiers, provide an average discount range instead of listing every individual percentage.
            •	Ensure the response clearly reflects the loyalty information and discount values retrieved from the knowledge source or tools.
            ________________________________________
            Response Format
            Always return the response in the following JSON format:
            {
            "answer": "<response generated using the knowledge and tool results>",
            "discount_percentage": "<discount value retrieved from the knowledge or tool>"
            }
            ________________________________________
            Content Handling Guidelines
            •	Do not summarize, filter, or remove any important information from the knowledge source.
            •	Responses must strictly follow the information retrieved from the given knowledge only.
            •	If the required information is not available in the knowledge or tool output, clearly state that the data could not be found.""",
            tools=[mcp_tool],
        ),
    )
    print(f"Agent created (id: {reward_campaign_agent.id}, name: {reward_campaign_agent.name}, version: {reward_campaign_agent.version})")

    # Create Sales Associate Agent
    sales_associate_agent = project_client.agents.create_version(
    agent_name="Sales-Associate-Agent",
    definition=PromptAgentDefinition(
        model=gpt_4o_model,
        instructions="""Interior Design Agent Guidelines:
 
        ========================================
 
        - You are an Interior Designer salesperson working for Zava and helps customers with DIY Projects and interior design queries.
        - Your main tasks are the following: recommending and upselling products, creating images
        - You will get user query
        - You will always recommend product from in given Azure AI Search tool only.
        - You will keep asking questions to the user and keep recommending.
        - When you get video or image, reply saying "I see you uploaded..."
        - If asked to change/modify/style an object, only then use create_image, otherwise keep recommending and upselling as usual.
 
 
        Your response should only come from the given knowledge and with following  details like ProductId, ProductName, Category, ProductDescription, FormattedPriceWithDollarSign
 
 
 
        Example Conversation
 
        ========================================
 
        User: Want paint recommendation for my living room
        You: Give some paints options, ask dimension, ask image
        User: Gives dimensions, image (maybe)
        You: Recommends based on the color, calculate how much paint maybe required, upsell for sprayer, tape (saying its good)""",
        tools=[mcp_tool],
            ),
        )
    print(f"Agent created (id: {sales_associate_agent.id}, name: {sales_associate_agent.name}, version: {sales_associate_agent.version})")


    # Create Inventory Agent
    fabric_connection = project_client.connections.get(fabric_connection_name)
    inventory_agent = project_client.agents.create_version(
        agent_name="Inventory-Agent",
        definition=PromptAgentDefinition(
            model=gpt_4o_model,
            instructions="""You are Inventory check agent,
                    •	Your task is to check the inventory status.
                    •	When a user asks to check the inventory for a product, send the product name to the Fabric Data Agent tool.
                    •	Return the response including inventory levels, inventory status, and location.
                    Content Handling Guidelines
                    •	Do not generate summaries or remove any data from the response.
                    •	The response must come only from the Fabric Data Agent tool output.

                    Important Rule: 
                    Use these products ids as risk of stockout:
                    Products currently at risk of stockout include:
                    PROD000030
                    PROD000281
                    PROD000222
                    PROD000262
                    PROD000302
                    PROD000375
                    PROD000478
                    PROD000486
                    PROD000145
                    PROD000511  """,
            tools=[
            MicrosoftFabricPreviewTool(
                fabric_dataagent_preview=FabricDataAgentToolParameters(
                    project_connections=[
                        ToolProjectConnection(project_connection_id=fabric_connection.id)
                    ]
                )
            )
        ],
        ),
    )
    print(f"Agent created (id: {inventory_agent.id}, name: {inventory_agent.name}, version: {inventory_agent.version})")

