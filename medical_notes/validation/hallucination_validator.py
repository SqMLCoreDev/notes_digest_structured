"""
Hallucination Validator - Hallucination Score Calculation

Measures how much of the generated content is not supported by the source note
using LLM-as-judge approach.
"""

import os
import json
import re
from typing import Dict, Any
from botocore.config import Config
import boto3
from medical_notes.service.rate_limiter import acquire_bedrock_request_slot
from medical_notes.service.token_tracker import add_token_usage, extract_token_usage_from_response


def check_hallucination_score(source_note: str, generated_output: str) -> Dict[str, Any]:
    """
    Calculate hallucination score - measures unsupported content in generated output.
    
    Lower score = more hallucinations (bad)
    Higher score = fewer hallucinations (good)
    
    Args:
        source_note: Original source medical note text
        generated_output: AI-generated output to validate
    
    Returns:
        dict with 'passed' (bool), 'score' (float), 'hallucination_rate' (float), and 'issues' (list)
    """
    system_prompt = """You are a clinical validation expert specializing in detecting hallucinations in medical notes.

Your task is to identify any content in the generated output that is NOT supported by the source note.

Hallucinations include:
1. Information present in generated output but absent from source
2. Contradictory information (generated says X, source says Y)
3. Inferred information not explicitly stated in source
4. Fabricated details (medications, diagnoses, findings not in source)

Respond ONLY with a JSON object in this exact format:
{
  "hallucination_rate": 0.0-1.0,
  "score": 0.0-1.0,
  "hallucinated_sentences": ["sentence1", "sentence2", ...],
  "issues": ["issue1", "issue2", ...]
}

Where:
- hallucination_rate: Proportion of generated content that is hallucinated (0.0 = no hallucinations, 1.0 = all hallucinated)
- score: 1.0 - hallucination_rate (higher is better)
- hallucinated_sentences: List of sentences or phrases that are hallucinated
- issues: List of specific hallucination issues found

If no hallucinations found, hallucination_rate should be 0.0, score should be 1.0, and arrays should be empty."""

    user_prompt = f"""SOURCE NOTE:
{source_note}

GENERATED OUTPUT:
{generated_output}

Identify all hallucinations in the generated output. Return JSON only."""

    try:
        if not acquire_bedrock_request_slot(timeout=60.0):
            return {
                "passed": False,
                "score": 0.0,
                "hallucination_rate": 1.0,
                "issues": ["Rate limit timeout: Could not acquire Bedrock API slot for hallucination check"]
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
                "hallucination_rate": 1.0,
                "issues": ["Empty response from Bedrock for hallucination check"]
            }
        
        result = json.loads(response_body)
        
        if 'content' not in result or len(result['content']) == 0:
            return {
                "passed": False,
                "score": 0.0,
                "hallucination_rate": 1.0,
                "issues": ["No content in Bedrock response for hallucination check"]
            }
        
        # Extract and track token usage
        input_tokens, output_tokens = extract_token_usage_from_response(result)
        add_token_usage("validation_hallucination", input_tokens, output_tokens)
        
        response_text = result['content'][0].get('text', '').strip()
        
        # Parse JSON response
        try:
            # Extract JSON from response (handle markdown code blocks)
            json_match = re.search(r'\{[^{}]*"hallucination_rate"[^{}]*\}', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
            else:
                json_str = response_text
            
            validation_result = json.loads(json_str)
            
            hallucination_rate = float(validation_result.get("hallucination_rate", 1.0))
            score = float(validation_result.get("score", 1.0 - hallucination_rate))
            hallucinated_sentences = validation_result.get("hallucinated_sentences", [])
            issues = validation_result.get("issues", [])
            
            # Add hallucinated sentences to issues if present
            if hallucinated_sentences:
                issues.extend([f"Hallucinated: {sent}" for sent in hallucinated_sentences[:5]])
            
            # Determine if passed (threshold: hallucination_rate < 0.2, score > 0.8)
            passed = hallucination_rate < 0.2 and score >= 0.8
            
            if not passed:
                if not issues:
                    issues.append(f"High hallucination rate ({hallucination_rate:.3f}, threshold: 0.2)")
            
            return {
                "passed": passed,
                "score": round(score, 3),
                "hallucination_rate": round(hallucination_rate, 3),
                "hallucinated_sentences": hallucinated_sentences[:10],  # Limit to first 10
                "issues": issues
            }
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            return {
                "passed": False,
                "score": 0.0,
                "hallucination_rate": 1.0,
                "hallucinated_sentences": [],
                "issues": [f"Failed to parse hallucination validation response: {str(e)}"]
            }
    
    except Exception as e:
        return {
            "passed": False,
            "score": 0.0,
            "hallucination_rate": 1.0,
            "hallucinated_sentences": [],
            "issues": [f"Error during hallucination check: {str(e)}"]
        }
