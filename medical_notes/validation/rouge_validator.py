"""
ROUGE Validator - ROUGE Score Calculation

Calculates ROUGE-1, ROUGE-2, and ROUGE-L scores for evaluating
overlap between generated output and source note.
"""

from typing import Dict, Any, List
from collections import Counter


def check_rouge_scores(source_note: str, generated_output: str) -> Dict[str, Any]:
    """
    Calculate ROUGE scores (ROUGE-1, ROUGE-2, ROUGE-L) between source and generated output.
    
    Args:
        source_note: Original source medical note text
        generated_output: AI-generated output to validate
    
    Returns:
        dict with 'passed' (bool), 'score' (float), 'rouge_scores' (dict), and 'issues' (list)
    """
    issues = []
    
    # Tokenize both texts
    source_tokens = _tokenize(source_note)
    generated_tokens = _tokenize(generated_output)
    
    if not source_tokens or not generated_tokens:
        return {
            "passed": False,
            "score": 0.0,
            "rouge_scores": {
                "rouge_1": 0.0,
                "rouge_2": 0.0,
                "rouge_l": 0.0
            },
            "issues": ["Empty source or generated text for ROUGE calculation"]
        }
    
    # Calculate ROUGE-1 (unigram overlap)
    rouge_1 = _calculate_rouge_n(source_tokens, generated_tokens, n=1)
    
    # Calculate ROUGE-2 (bigram overlap)
    rouge_2 = _calculate_rouge_n(source_tokens, generated_tokens, n=2)
    
    # Calculate ROUGE-L (longest common subsequence)
    rouge_l = _calculate_rouge_l(source_tokens, generated_tokens)
    
    # Overall ROUGE score (weighted average)
    overall_rouge = (rouge_1 * 0.4 + rouge_2 * 0.3 + rouge_l * 0.3)
    
    # Determine if passed (threshold: 0.3 for medical notes)
    passed = overall_rouge >= 0.3
    
    if not passed:
        issues.append(f"ROUGE score below threshold (score: {overall_rouge:.3f}, threshold: 0.3)")
    
    if rouge_1 < 0.2:
        issues.append(f"Low ROUGE-1 score ({rouge_1:.3f}) - poor unigram overlap")
    
    if rouge_2 < 0.15:
        issues.append(f"Low ROUGE-2 score ({rouge_2:.3f}) - poor bigram overlap")
    
    return {
        "passed": passed,
        "score": round(overall_rouge, 3),
        "rouge_scores": {
            "rouge_1": round(rouge_1, 3),
            "rouge_2": round(rouge_2, 3),
            "rouge_l": round(rouge_l, 3)
        },
        "issues": issues
    }


def _tokenize(text: str) -> List[str]:
    """
    Tokenize text into words (simple whitespace-based tokenization).
    
    Args:
        text: Text to tokenize
    
    Returns:
        List of tokens (lowercased)
    """
    if not text:
        return []
    
    # Simple tokenization: split on whitespace and punctuation
    import re
    tokens = re.findall(r'\b\w+\b', text.lower())
    return tokens


def _calculate_rouge_n(reference_tokens: List[str], candidate_tokens: List[str], n: int) -> float:
    """
    Calculate ROUGE-N score (n-gram overlap).
    
    Args:
        reference_tokens: Reference text tokens
        candidate_tokens: Candidate text tokens
        n: N-gram size (1 for unigrams, 2 for bigrams, etc.)
    
    Returns:
        ROUGE-N score (0.0-1.0)
    """
    if n == 1:
        reference_ngrams = Counter(reference_tokens)
        candidate_ngrams = Counter(candidate_tokens)
    else:
        reference_ngrams = Counter(_get_ngrams(reference_tokens, n))
        candidate_ngrams = Counter(_get_ngrams(candidate_tokens, n))
    
    if not reference_ngrams:
        return 0.0
    
    # Calculate overlap
    overlap = sum((reference_ngrams & candidate_ngrams).values())
    total_reference = sum(reference_ngrams.values())
    
    if total_reference == 0:
        return 0.0
    
    return overlap / total_reference


def _get_ngrams(tokens: List[str], n: int) -> List[tuple]:
    """
    Generate n-grams from tokens.
    
    Args:
        tokens: List of tokens
        n: N-gram size
    
    Returns:
        List of n-gram tuples
    """
    if len(tokens) < n:
        return []
    
    return [tuple(tokens[i:i+n]) for i in range(len(tokens) - n + 1)]


def _calculate_rouge_l(reference_tokens: List[str], candidate_tokens: List[str]) -> float:
    """
    Calculate ROUGE-L score (longest common subsequence).
    
    Args:
        reference_tokens: Reference text tokens
        candidate_tokens: Candidate text tokens
    
    Returns:
        ROUGE-L score (0.0-1.0)
    """
    if not reference_tokens or not candidate_tokens:
        return 0.0
    
    # Calculate LCS length
    lcs_length = _lcs_length(reference_tokens, candidate_tokens)
    
    if lcs_length == 0:
        return 0.0
    
    # ROUGE-L = LCS / max(len(reference), len(candidate))
    # Using F-measure: 2 * LCS / (len(reference) + len(candidate))
    precision = lcs_length / len(candidate_tokens) if candidate_tokens else 0.0
    recall = lcs_length / len(reference_tokens) if reference_tokens else 0.0
    
    if precision + recall == 0:
        return 0.0
    
    f_score = 2 * precision * recall / (precision + recall)
    return f_score


def _lcs_length(seq1: List[str], seq2: List[str]) -> int:
    """
    Calculate the length of the longest common subsequence.
    
    Args:
        seq1: First sequence
        seq2: Second sequence
    
    Returns:
        Length of LCS
    """
    m, n = len(seq1), len(seq2)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if seq1[i-1] == seq2[j-1]:
                dp[i][j] = dp[i-1][j-1] + 1
            else:
                dp[i][j] = max(dp[i-1][j], dp[i][j-1])
    
    return dp[m][n]
