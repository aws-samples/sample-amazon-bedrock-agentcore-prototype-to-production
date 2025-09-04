import json

def lambda_handler(event, context):
    toolName = context.client_context.custom['bedrockAgentCoreToolName']
    print(context.client_context)
    print(event)
    print(f"Original toolName: , {toolName}")
    delimiter = "___"
    if delimiter in toolName:
        toolName = toolName[toolName.index(delimiter) + len(delimiter):]
    print(f"Converted toolName: , {toolName}")
    if toolName == 'get_credit_score_tool':
        return {'statusCode': 200, 'body': "Credit score for the customer is 80"}
    else:
        return {'statusCode': 200, 'body': "Unknown tool name. Try with a valid tool"}
