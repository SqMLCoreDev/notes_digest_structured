"""
G-Eval Validator - G-Eval Score Calculation

Uses LLM-as-judge with chain-of-thought reasoning to evaluate
the quality of generated medical notes.
"""

import os
import json
import re
from typing import Dict, Any
from botocore.config import Config
import boto3
from medical_notes.service.rate_limiter import acquire_bedrock_request_slot
from medical_notes.service.token_tracker import add_token_usage, extract_token_usage_from_response


def check_geval_score(source_note: str, generated_output: str, note_type: str) -> Dict[str, Any]:
    """
    Calculate G-Eval score using LLM-as-judge with chain-of-thought reasoning.
    
    G-Eval evaluates:
    1. Relevance: How relevant is the generated content to the source?
    2. Coherence: How well-structured and coherent is the output?
    3. Consistency: How consistent is the information?
    4. Completeness: How complete is the information?
    
    Args:
        source_note: Original source medical note text
        generated_output: AI-generated output to validate
        note_type: Type of note (for context)
    
    Returns:
        dict with 'passed' (bool), 'score' (float), 'geval_scores' (dict), and 'issues' (list)
    """
    system_prompt = """You are a clinical validation expert using G-Eval methodology to evaluate medical notes.

G-Eval uses chain-of-thought reasoning to evaluate text quality across multiple dimensions.

Evaluate the generated output on these dimensions:
1. RELEVANCE (0-5): How relevant is the generated content to the source note? Does it capture key clinical information?
2. COHERENCE (0-5): How well-structured and coherent is the output? Is it logically organized?
3. CONSISTENCY (0-5): How consistent is the information? Are there contradictions?
4. COMPLETENESS (0-5): How complete is the information? Are critical details included?

For each dimension, provide:
- A score (0-5, where 5 is best)
- Brief reasoning

Respond ONLY with a JSON object in this exact format:
{
  "relevance": {"score": 0-5, "reasoning": "..."},
  "coherence": {"score": 0-5, "reasoning": "..."},
  "consistency": {"score": 0-5, "reasoning": "..."},
  "completeness": {"score": 0-5, "reasoning": "..."},
  "overall_score": 0.0-1.0,
  "issues": ["issue1", "issue2", ...]
}

Where overall_score is the average of the four dimension scores normalized to 0-1."""

    user_prompt = f"""SOURCE NOTE:
{source_note}

GENERATED OUTPUT:
{generated_output}

NOTE TYPE: {note_type}

Evaluate the generated output using G-Eval methodology. Return JSON only."""

    try:
        if not acquire_bedrock_request_slot(timeout=60.0):
            return {
                "passed": False,
                "score": 0.0,
                "geval_scores": {
                    "relevance": 0.0,
                    "coherence": 0.0,
                    "consistency": 0.0,
                    "completeness": 0.0
                },
                "issues": ["Rate limit timeout: Could not acquire Bedrock API slot for G-Eval check"]
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
                "geval_scores": {
                    "relevance": 0.0,
                    "coherence": 0.0,
                    "consistency": 0.0,
                    "completeness": 0.0
                },
                "issues": ["Empty response from Bedrock for G-Eval check"]
            }
        
        result = json.loads(response_body)
        
        if 'content' not in result or len(result['content']) == 0:
            return {
                "passed": False,
                "score": 0.0,
                "geval_scores": {
                    "relevance": 0.0,
                    "coherence": 0.0,
                    "consistency": 0.0,
                    "completeness": 0.0
                },
                "issues": ["No content in Bedrock response for G-Eval check"]
            }
        
        # Extract and track token usage
        input_tokens, output_tokens = extract_token_usage_from_response(result)
        add_token_usage("validation_geval", input_tokens, output_tokens)
        
        response_text = result['content'][0].get('text', '').strip()
        
        # Parse JSON response
        try:
            # Extract JSON from response (handle markdown code blocks)
            json_match = re.search(r'\{[^{}]*"overall_score"[^{}]*\}', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
            else:
                json_str = response_text
            
            validation_result = json.loads(json_str)
            
            # Extract dimension scores
            relevance = validation_result.get("relevance", {})
            coherence = validation_result.get("coherence", {})
            consistency = validation_result.get("consistency", {})
            completeness = validation_result.get("completeness", {})
            
            relevance_score = float(relevance.get("score", 0)) / 5.0 if isinstance(relevance, dict) else 0.0
            coherence_score = float(coherence.get("score", 0)) / 5.0 if isinstance(coherence, dict) else 0.0
            consistency_score = float(consistency.get("score", 0)) / 5.0 if isinstance(consistency, dict) else 0.0
            completeness_score = float(completeness.get("score", 0)) / 5.0 if isinstance(completeness, dict) else 0.0
            
            # Get overall score (use provided or calculate)
            overall_score = float(validation_result.get("overall_score", 0.0))
            if overall_score == 0.0:
                # Calculate average if not provided
                overall_score = (relevance_score + coherence_score + consistency_score + completeness_score) / 4.0
            
            issues = validation_result.get("issues", [])
            
            # Add dimension-specific issues if scores are low
            if relevance_score < 0.6:
                issues.append(f"Low relevance score ({relevance_score:.3f})")
            if coherence_score < 0.6:
                issues.append(f"Low coherence score ({coherence_score:.3f})")
            if consistency_score < 0.6:
                issues.append(f"Low consistency score ({consistency_score:.3f})")
            if completeness_score < 0.6:
                issues.append(f"Low completeness score ({completeness_score:.3f})")
            
            # Determine if passed (threshold: overall_score >= 0.7)
            passed = overall_score >= 0.7
            
            if not passed and not issues:
                issues.append(f"G-Eval score below threshold (score: {overall_score:.3f}, threshold: 0.7)")
            
            return {
                "passed": passed,
                "score": round(overall_score, 3),
                "geval_scores": {
                    "relevance": round(relevance_score, 3),
                    "coherence": round(coherence_score, 3),
                    "consistency": round(consistency_score, 3),
                    "completeness": round(completeness_score, 3),
                    "relevance_reasoning": relevance.get("reasoning", "") if isinstance(relevance, dict) else "",
                    "coherence_reasoning": coherence.get("reasoning", "") if isinstance(coherence, dict) else "",
                    "consistency_reasoning": consistency.get("reasoning", "") if isinstance(consistency, dict) else "",
                    "completeness_reasoning": completeness.get("reasoning", "") if isinstance(completeness, dict) else ""
                },
                "issues": issues
            }
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            return {
                "passed": False,
                "score": 0.0,
                "geval_scores": {
                    "relevance": 0.0,
                    "coherence": 0.0,
                    "consistency": 0.0,
                    "completeness": 0.0
                },
                "issues": [f"Failed to parse G-Eval validation response: {str(e)}"]
            }
    
    except Exception as e:
        return {
            "passed": False,
            "score": 0.0,
            "geval_scores": {
                "relevance": 0.0,
                "coherence": 0.0,
                "consistency": 0.0,
                "completeness": 0.0
            },
            "issues": [f"Error during G-Eval check: {str(e)}"]
        }
