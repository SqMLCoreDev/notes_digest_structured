# Datasets Package - Index-Specific Prompts

"""
Datasets package containing prompts for each Elasticsearch index.
Each index prompt is in a separate file for maintainability.
"""

from prompts.datasets.processed_notes import PROCESSED_NOTES_PROMPT
from prompts.datasets.processed_notes_json import PROCESSED_NOTES_JSON_PROMPT
from prompts.datasets.processed_notes_json_nested import PROCESSED_NOTES_JSON_NESTED_PROMPT
from prompts.datasets.prod_clinical_notes import PROD_CLINICAL_NOTES_PROMPT
from prompts.datasets.clinical_notes import CLINICAL_NOTES_PROMPT
from prompts.datasets.processed_notes_nonprod import PROCESSED_NOTES_NONPROD_PROMPT

# Combine all prompts into a single dictionary
prompts = {
    # Production processed notes
    "tiamd_prod_processed_notes": PROCESSED_NOTES_PROMPT,
    "tiamd_prod_processed_notes_json": PROCESSED_NOTES_JSON_PROMPT,
    "tiamd_prod_processed_notes_json_nested": PROCESSED_NOTES_JSON_NESTED_PROMPT,
    
    # Clinical notes (raw)
    "tiamd_prod_clinical_notes": PROD_CLINICAL_NOTES_PROMPT,
    "tiamd_clinical_notes": CLINICAL_NOTES_PROMPT,
    
    # Non-production processed notes
    "tiamd_processed_notes": PROCESSED_NOTES_NONPROD_PROMPT,
}

__all__ = [
    'prompts',
    'PROCESSED_NOTES_PROMPT',
    'PROCESSED_NOTES_JSON_PROMPT',
    'PROCESSED_NOTES_JSON_NESTED_PROMPT',
    'PROD_CLINICAL_NOTES_PROMPT',
    'CLINICAL_NOTES_PROMPT',
    'PROCESSED_NOTES_NONPROD_PROMPT',
]
