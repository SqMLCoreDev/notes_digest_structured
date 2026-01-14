import os
import json
import boto3
import random
import time
from botocore.config import Config
from medical_notes.service.token_tracker import add_token_usage, extract_token_usage_from_response
from medical_notes.service.rate_limiter import acquire_bedrock_request_slot

def invoke_claude(system_prompt: str, user_prompt: str, max_tokens: int = 30000, temperature: float = 0.1, section_name: str = "unknown"):
    """
    Invoke the Claude model via AWS Bedrock with token tracking and rate limiting.

    Args:
        system_prompt (str): The system prompt for the model.
        user_prompt (str): The user prompt for the model.
        max_tokens (int): Maximum tokens for the response.
        temperature (float): Sampling temperature for the model.
        section_name (str): Name of the section for token tracking.

    Returns:
        str: The response from the Claude model.
    """
    # TODO: Enable timing features later
    # from datetime import datetime
    # Record start time
    # start_time = datetime.now()
    
    # Acquire rate limit slot before making request
    if not acquire_bedrock_request_slot(timeout=60.0):
        raise RuntimeError(f"Rate limit timeout: Could not acquire Bedrock API slot for {section_name}")
    
    config = Config(
        read_timeout=300,  # 5 minutes read timeout
        connect_timeout=60,  # 1 minute connect timeout
        retries={
            'max_attempts': 5,
            'mode': 'adaptive'  # Adaptive retry mode for better handling
        }
    )

    bedrock = boto3.Session(
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        region_name=os.getenv("AWS_REGION", "us-east-1")
    ).client("bedrock-runtime", config=config)

    payload = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": max_tokens,
        "temperature": temperature,
        "messages": [
            {
                "role": "user",
                "content": f"{system_prompt}\n\n{user_prompt}"
            }
        ]
    }

    try:
        model_id = os.getenv("CLAUDE_HAIKU_4_5", "us.anthropic.claude-haiku-4-5-20251001-v1:0")
        response = bedrock.invoke_model(
            modelId=model_id,
            body=json.dumps(payload)
        )

        response_body = response['body'].read()
        if not response_body:
            raise ValueError("Empty response from Bedrock")

        result = json.loads(response_body)

        if 'content' not in result or len(result['content']) == 0:
            raise ValueError("No content in Bedrock response")

        # TODO: Enable timing features later
        # Record end time
        # end_time = datetime.now()
        # duration = (end_time - start_time).total_seconds()

        # Extract and track token usage (without timing for now)
        input_tokens, output_tokens = extract_token_usage_from_response(result)
        add_token_usage(section_name, input_tokens, output_tokens)
        
        print(f"  📊 Token usage ({section_name}): {input_tokens:,} in / {output_tokens:,} out")
        # TODO: Enable timing features later
        # print(f"  📊 Token usage ({section_name}): {input_tokens:,} in / {output_tokens:,} out ({duration:.2f}s)")

        return result['content'][0].get('text', '').strip()

    except Exception as e:
        # TODO: Enable timing features later
        # Record end time even on error
        # end_time = datetime.now()
        # duration = (end_time - start_time).total_seconds()
        # print(f"  ❌ Error in {section_name} after {duration:.2f}s: {e}")
        print(f"Error invoking Claude model: {e}")
        raise