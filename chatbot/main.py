"""
main.py - AWS Lambda Entry Point

Provides Lambda handler function using Mangum adapter.
Supports both API Gateway HTTP events and direct Lambda invocations.
"""

import json
import asyncio
import traceback
from datetime import datetime

# Import Mangum for Lambda support
try:
    from mangum import Mangum
    MANGUM_AVAILABLE = True
except ImportError:
    MANGUM_AVAILABLE = False

from app.main import app
from app.core.config import settings
from app.core.logging import setup_logging, get_logger
from app.services.mcp.mcp_server import get_mcp_server

# Configure logging for Lambda
setup_logging(level="INFO", json_format=True)
logger = get_logger(__name__)

# Initialize Mangum handler
if MANGUM_AVAILABLE:
    mangum_handler = Mangum(app, lifespan="off")


def lambda_handler(event, context):
    """
    AWS Lambda handler function.
    
    Supports:
    - API Gateway HTTP events (via Mangum)
    - Direct Lambda invocations
    
    Args:
        event: Lambda event (API Gateway or direct)
        context: Lambda context object
        
    Returns:
        API Gateway response or direct invocation response
    """
    logger.info(f"Lambda invoked: {context.function_name}")
    logger.info(f"Request ID: {context.aws_request_id}")
    
    # Check if this is a direct Lambda invocation
    if 'httpMethod' not in event and 'requestContext' not in event:
        return _handle_direct_invocation(event, context)
    
    # Otherwise, use Mangum for HTTP events
    if MANGUM_AVAILABLE:
        logger.info("HTTP invocation - using Mangum")
        return mangum_handler(event, context)
    else:
        logger.error("Mangum not installed")
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'error': 'Mangum dependency missing'
            })
        }


def _handle_direct_invocation(event, context):
    """
    Handle direct Lambda invocation (not through API Gateway).
    
    Args:
        event: Direct invocation event
        context: Lambda context
        
    Returns:
        JSON response
    """
    logger.info("Direct Lambda invocation detected")
    
    # Run the async handler
    return asyncio.get_event_loop().run_until_complete(
        _async_direct_handler(event, context)
    )


async def _async_direct_handler(event, context):
    """
    Async handler for direct Lambda invocations.
    
    Args:
        event: Direct invocation event
        context: Lambda context
        
    Returns:
        JSON response
    """
    try:
        # Extract parameters
        department = event.get('department', 'claims')
        user = event.get('user', 'test-user')
        query = event.get('chatquery', 'What is the total count of records?')
        history = event.get('historyenabled', False)
        session_id = event.get('chatsession_id', None)
        
        logger.info(f"Direct invocation: dept={department}, user={user}")
        
        # Validate
        if history and not session_id:
            raise ValueError('chatsession_id is required when historyenabled=true')
        
        # Get services
        mcp_server = get_mcp_server()
        es_client = mcp_server.es_client
        
        # Get allowed indices (async call)
        query_body = {
            "bool": {
                "must": [
                    {"match": {"departmentName": department}},
                    {"match": {"users": user}}
                ]
            }
        }
        
        result = await es_client.search(
            index=settings.MAPPING_INDEX,
            query=query_body,
            size=10
        )
        
        if not result.get('success') or not result.get('documents'):
            raise Exception(f"Access denied for {user}@{department}")
        
        allowed_indices = result['documents'][0].get('datasets', [])
        
        # Query with Claude (async, on-demand schemas)
        response_text, used_indices, base64_image = await mcp_server.query_with_claude(
            question=query,
            indices=allowed_indices,
            schemas=None,  # On-demand schema fetching
            conversation_history=[]
        )
        
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'user': user,
                'sessionId': session_id or "",
                'query': query,
                'chatResponse': response_text,
                'chartbase64Image': base64_image,
                'responseTime': datetime.utcnow().isoformat()
            })
        }
        
    except Exception as e:
        logger.error(f"Direct invocation error: {e}")
        logger.error(traceback.format_exc())
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'success': False,
                'error': str(e),
                'invocation_type': 'direct'
            })
        }


# For local testing
if __name__ == "__main__":
    # Simulate a direct invocation
    test_event = {
        "department": "test",
        "user": "test-user",
        "chatquery": "What is the total count?",
        "historyenabled": False
    }
    
    class MockContext:
        function_name = "local-test"
        aws_request_id = "test-123"
    
    result = lambda_handler(test_event, MockContext())
    print(json.dumps(result, indent=2))
