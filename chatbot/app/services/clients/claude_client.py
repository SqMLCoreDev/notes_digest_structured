"""
app/services/clients/claude_client.py - Claude/Bedrock Client (Async)

Handles all interactions with AWS Bedrock and Claude AI with async support.
"""

import json
import os
import asyncio
from typing import Any, Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor
import boto3
from botocore.exceptions import ClientError

from app.core.config import settings
from app.core.logging import get_logger
from app.core.exceptions import ClaudeError, ConfigurationError

# Set matplotlib cache directory for Lambda
os.environ['MPLCONFIGDIR'] = '/tmp/matplotlib'

logger = get_logger(__name__)

# Thread pool for running boto3 sync calls
_executor = ThreadPoolExecutor(max_workers=10)


class ClaudeClient:
    """
    Async client for interacting with Claude AI via AWS Bedrock.
    Uses thread pool executor to make boto3 calls non-blocking.
    """
    
    def __init__(self):
        """Initialize Claude client with AWS Bedrock."""
        self.region = settings.AWS_REGION
        self.model_id = settings.model_id
        self.max_tokens = settings.MAX_TOKENS
        
        # Initialize Bedrock client
        try:
            if settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY:
                self.client = boto3.client(
                    'bedrock-runtime',
                    region_name=self.region,
                    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
                )
            else:
                self.client = boto3.client('bedrock-runtime', region_name=self.region)
                
            logger.info(f"Initialized Claude client with model {self.model_id}")
            
        except Exception as e:
            raise ConfigurationError(
                message=f"Failed to initialize Bedrock client: {str(e)}",
                details={"region": self.region}
            )
    
    def _invoke_sync(
        self,
        system_prompt: str,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict]] = None,
        temperature: float = 0
    ) -> Dict[str, Any]:
        """
        Synchronous invoke method (called in thread pool).
        """
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": self.max_tokens,
            "system": system_prompt,
            "messages": messages,
            "temperature": temperature
        }
        
        if tools:
            request_body["tools"] = tools
        
        response = self.client.invoke_model(
            modelId=self.model_id,
            body=json.dumps(request_body)
        )
        
        response_bytes = response['body'].read()
        return json.loads(response_bytes)
    
    async def invoke(
        self,
        system_prompt: str,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict]] = None,
        temperature: float = 0
    ) -> Dict[str, Any]:
        """
        Async invoke Claude model using thread pool.
        
        Args:
            system_prompt: System instructions
            messages: Conversation messages
            tools: Optional tool definitions
            temperature: Model temperature (0 for deterministic)
            
        Returns:
            Model response
        """
        try:
            logger.debug(f"Invoking {self.model_id} in {self.region}")
            
            # Run sync boto3 call in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            response_body = await loop.run_in_executor(
                _executor,
                self._invoke_sync,
                system_prompt,
                messages,
                tools,
                temperature
            )
            
            return response_body
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            error_message = e.response.get('Error', {}).get('Message', '')
            
            raise ClaudeError(
                message=f"Bedrock API error: {error_code}",
                details={
                    "code": error_code,
                    "message": error_message,
                    "model": self.model_id
                }
            )
            
        except json.JSONDecodeError as e:
            raise ClaudeError(
                message="Failed to parse model response",
                details={"error": str(e)}
            )
            
        except Exception as e:
            raise ClaudeError(
                message=f"Model invocation failed: {str(e)}",
                details={"model": self.model_id}
            )
    
    def extract_text_response(self, response: Dict[str, Any]) -> str:
        """
        Extract text response from model output.
        
        Args:
            response: Model response
            
        Returns:
            Text content
        """
        content = response.get('content', [])
        text_blocks = [
            block.get('text', '')
            for block in content
            if block.get('type') == 'text'
        ]
        return '\n\n'.join(text_blocks).strip()
    
    def extract_tool_calls(self, response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract tool calls from model output.
        
        Args:
            response: Model response
            
        Returns:
            List of tool call objects
        """
        content = response.get('content', [])
        return [
            block for block in content
            if block.get('type') == 'tool_use'
        ]
    
    def has_tool_calls(self, response: Dict[str, Any]) -> bool:
        """Check if response contains tool calls."""
        return len(self.extract_tool_calls(response)) > 0


# Singleton instance
_claude_client: Optional[ClaudeClient] = None


def get_claude_client() -> ClaudeClient:
    """Get the Claude client singleton."""
    global _claude_client
    if _claude_client is None:
        _claude_client = ClaudeClient()
    return _claude_client
