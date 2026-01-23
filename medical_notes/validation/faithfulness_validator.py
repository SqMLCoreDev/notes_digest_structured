"""
Faithfulness Validator - LLM-as-Judge Validation

Checks if generated output is faithful to the source note using AWS Bedrock Claude.
"""

import os
import json
import re
from typing import Dict, Any
from botocore.config import Config
import boto3
from medical_notes.service.rate_limiter import acquire_bedrock_request_slot
from medical_notes.service.token_tracker import add_token_usage, extract_token_usage_from_response


def check_faithfulness(source_note: str, generated_output: str) -> Dict[str, Any]:
    """
    Check if generated output is faithful to the source note using LLM-as-judge.
    
    Args:
        source_note: Original source medical note text
        generated_output: AI-generated output to validate
    
    Returns:
        dict with 'passed' (bool), 'score' (float), and 'issues' (list)
    """
    system_prompt = """You are a clinical validation expert. Your task is to evaluate whether an AI-generated medical note summary is faithful to the original source note.

Evaluate faithfulness by checking:
1. No hallucination: Generated content must be supported by source material
2. No omission of critical information: Important clinical details from source must be present
3. No contradiction: Generated content must not contradict source material
4. Accurate representation: Key facts, medications, diagnoses, and findings must match

Respond ONLY with a JSON object in this exact format:
{
  "faithful": true/false,
  "score": 0.0-1.0,
  "issues": ["issue1", "issue2", ...]
}

If faithful=true, issues should be an empty array."""

    user_prompt = f"""SOURCE NOTE:
{source_note}

GENERATED OUTPUT:
{generated_output}

Evaluate the faithfulness of the generated output to the source note. Return JSON only."""

    try:
        if not acquire_bedrock_request_slot(timeout=60.0):
            return {
                "passed": False,
                "score": 0.0,
                "issues": ["Rate limit timeout: Could not acquire Bedrock API slot for faithfulness check"]
            }
        
        config = Config(
            read_timeout=300,
            connect_timeout=60,
            retries={
                'max_attempts': 5,
                'mode': 'adaptive'
            }
        )
        
        bedrock = boto3.Session(
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS"),
            region_name=os.getenv("AWS_REGION", "us-east-1")
        ).client("bedrock-runtime", config=config)
        
        payload = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 2000,
            "temperature": 0.1,
            "messages": [
                {
                    "role": "user",
                    "content": f"{system_prompt}\n\n{user_prompt}"
                }
            ]
        }
        
        model_id = os.getenv("CLAUDE_HAIKU_4_5", "us.anthropic.claude-haiku-4-5-20251001-v1:0")
        response = bedrock.invoke_model(
            modelId=model_id,
            body=json.dumps(payload)
        )
        
        response_body = response['body'].read()
        if not response_body:
            return {
                "passed": False,
                "score": 0.0,
                "issues": ["Empty response from Bedrock for faithfulness check"]
            }
        
        result = json.loads(response_body)
        
        if 'content' not in result or len(result['content']) == 0:
            return {
                "passed": False,
                "score": 0.0,
                "issues": ["No content in Bedrock response for faithfulness check"]
            }
        
        # Extract and track token usage
        input_tokens, output_tokens = extract_token_usage_from_response(result)
        add_token_usage("validation_faithfulness", input_tokens, output_tokens)
        
        response_text = result['content'][0].get('text', '').strip()
        
        # Parse JSON response
        try:
            # Extract JSON from response (handle markdown code blocks)
            json_match = re.search(r'\{[^{}]*"faithful"[^{}]*\}', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
            else:
                json_str = response_text
            
            validation_result = json.loads(json_str)
            
            return {
                "passed": validation_result.get("faithful", False),
                "score": float(validation_result.get("score", 0.0)),
                "issues": validation_result.get("issues", [])
            }
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            return {
                "passed": False,
                "score": 0.0,
                "issues": [f"Failed to parse faithfulness validation response: {str(e)}"]
            }
    
    except Exception as e:
        return {
            "passed": False,
            "score": 0.0,
            "issues": [f"Error during faithfulness check: {str(e)}"]
        }
