#!/usr/bin/env python3
"""
Test script for validation endpoint
"""

import requests
import json

def test_validation():
    """Test the validation endpoint with sample data"""
    
    url = "http://localhost:8000/validate"
    
    payload = {
        "source_note": "Patient is a 45-year-old male presenting with chest pain. Blood pressure 140/90. Prescribed aspirin 81mg daily.",
        "generated_output": """PROGRESS NOTE

PATIENT INFORMATION
- Name: Patient
- Age: 45
- Sex: Male

SUBJECTIVE
Patient presents with chest pain.

OBJECTIVE
Blood pressure: 140/90

ASSESSMENT
Chest pain, rule out cardiac event

PLAN
Aspirin 81mg daily""",
        "note_type": "progress_note",
        "note_id": "test_001",
        "store_to_es": True
    }
    
    print("Testing Validation Endpoint...")
    print("=" * 50)
    
    try:
        response = requests.post(url, json=payload, timeout=300)
        response.raise_for_status()
        
        result = response.json()
        
        print("\n✅ Validation Result:")
        print(f"Decision: {result['decision']}")
        print(f"Overall Score: {result['score']}")
        print(f"Validation ID: {result.get('validation_id', 'N/A')}")
        print(f"Timestamp: {result['timestamp']}")
        
        print("\n📊 Individual Scores:")
        scores = result['scores']
        print(f"  - Faithfulness: {scores['faithfulness']}")
        print(f"  - Template: {scores['template']}")
        print(f"  - Medical Facts: {scores['medical_facts']}")
        print(f"  - ROUGE: {scores['rouge']}")
        print(f"  - Hallucination: {scores['hallucination']}")
        print(f"  - G-Eval: {scores['geval']}")
        
        if result.get('rouge_scores'):
            print("\n📈 ROUGE Scores:")
            rouge = result['rouge_scores']
            print(f"  - ROUGE-1: {rouge['rouge_1']}")
            print(f"  - ROUGE-2: {rouge['rouge_2']}")
            print(f"  - ROUGE-L: {rouge['rouge_l']}")
        
        if result.get('hallucination_rate') is not None:
            print(f"\n🚨 Hallucination Rate: {result['hallucination_rate']}")
            if result.get('hallucinated_sentences'):
                print(f"  Hallucinated Sentences: {len(result['hallucinated_sentences'])}")
        
        if result.get('geval_scores'):
            print("\n🎯 G-Eval Scores:")
            geval = result['geval_scores']
            print(f"  - Relevance: {geval['relevance']}")
            print(f"  - Coherence: {geval['coherence']}")
            print(f"  - Consistency: {geval['consistency']}")
            print(f"  - Completeness: {geval['completeness']}")
        
        print("\n⚠️  Issues Found:")
        issues = result['issues']
        for category, issue_list in issues.items():
            if issue_list:
                print(f"  {category.upper()}:")
                for issue in issue_list[:3]:  # Show first 3 issues
                    print(f"    - {issue}")
        
        print("\n" + "=" * 50)
        print(f"\nFull JSON Response:\n{json.dumps(result, indent=2)}")
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Error: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response: {e.response.text}")


def get_validation_history(note_id: str):
    """Get validation history for a note"""
    
    url = f"http://localhost:8000/validate/{note_id}"
    
    print(f"\n📜 Validation History for note_id: {note_id}")
    print("=" * 50)
    
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        
        print(f"Total Validations: {result['count']}")
        
        for i, validation in enumerate(result['validations'], 1):
            print(f"\nValidation {i}:")
            print(f"  ID: {validation['validation_id']}")
            print(f"  Timestamp: {validation['timestamp']}")
            print(f"  Decision: {validation['decision']}")
            print(f"  Score: {validation['score']}")
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Error: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response: {e.response.text}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        # Get validation history
        note_id = sys.argv[1]
        get_validation_history(note_id)
    else:
        # Run validation test
        test_validation()
