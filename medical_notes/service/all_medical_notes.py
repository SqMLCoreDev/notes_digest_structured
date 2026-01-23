"""
Enhanced Medical Notes Generator - Single Template Processing
Each note type processed with a single comprehensive template
With token usage tracking
"""

import os
import json
import boto3
import re
import time
import random
from datetime import datetime
from typing import Dict, List, Optional, Any, Union, Tuple
import pandas as pd
from dotenv import load_dotenv
from botocore.exceptions import ClientError
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

from medical_notes.service.token_tracker import add_token_usage, extract_token_usage_from_response
from medical_notes.utils.invoke_claude import invoke_claude

load_dotenv()

class MedicalNotesGenerator:
    """
    Medical note generator using single comprehensive templates per note type.
    """
    
    def __init__(
        self,
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
        aws_region: str = "us-east-1"
    ):
        """Initialize the Medical Notes Generator."""
        from botocore.config import Config

        # Configure timeout settings
        config = Config(
            read_timeout=300,  # 5 minutes read timeout
            connect_timeout=60,  # 1 minute connect timeout
            retries={
                'max_attempts': 5,
                'mode': 'adaptive'  # Adaptive retry mode for better handling
            }
        )

        self.bedrock = boto3.Session(
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS"),
            region_name=os.getenv("AWS_REGION", "us-east-1")
        ).client("bedrock-runtime", config=config)

        self.max_tokens = 30000  # Claude 4.5 Haiku max output limit on Bedrock
        self.print_lock = threading.Lock()  # Thread-safe printing
    
    def invoke_bedrock(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 30000,
        temperature: float = 0,
        base_delay: int = 0,
        max_retries: int = 5,
        section_name: str = "unknown"
    ) -> str:
        """
        Wrapper for the invoke_claude function to maintain compatibility with token tracking.
        """
        return invoke_claude(system_prompt, user_prompt, max_tokens, temperature, section_name)
    
    def _convert_dataframe_to_dict(self, df: pd.DataFrame) -> Dict[str, str]:
        """Convert pandas DataFrame to dictionary format."""
        text_col = None
        for col in df.columns:
            if any(keyword in col.lower() for keyword in ['text', 'note', 'content', 'narrative', 'rawdata']):
                text_col = col
                break
        
        if text_col is None:
            text_col = df.columns[0]
        
        id_col = None
        for col in df.columns:
            if col.lower() in ['id', 'record_id', 'note_id', 'identifier', 'visit_id', 'noteid']:
                id_col = col
                break
        
        if id_col:
            records_dict = {
                str(row[id_col]): str(row[text_col])
                for _, row in df.iterrows()
            }
        else:
            records_dict = {
                f"record_{idx}": str(row[text_col])
                for idx, row in df.iterrows()
            }
        
        return records_dict
    
    def _thread_safe_print(self, message: str):
        """Thread-safe printing method."""
        with self.print_lock:
            print(message)
    
    def _process_note_type_template(self, note_type: str, full_text: str) -> Tuple[str, Optional[str], Optional[str]]:
        """
        Process the specific note type template.
        
        Returns:
            Tuple of (template_name, result_text, error_message)
        """
        try:
            from medical_notes.prompts.all_prompts import get_note_template
            
            self._thread_safe_print(f"Loading template for {note_type}...")
            template_config = get_note_template(note_type, full_text)

            self._thread_safe_print(f"Generating complete note for {note_type}...")
            processed_note_text = self.invoke_bedrock(
                template_config["system_prompt"],
                template_config["prompt"],
                max_tokens=self.max_tokens,
                temperature=0,
                section_name=f"template_{note_type}"
            )

            self._thread_safe_print(f"\u2713 {note_type.capitalize()} generated successfully")
            return f"template_{note_type}", processed_note_text, None
            
        except Exception as e:
            error_msg = f"Error processing {note_type} template: {str(e)}"
            self._thread_safe_print(f"ERROR: {error_msg}")
            return f"template_{note_type}", None, error_msg
    
    def _process_soap_template(self, full_text: str) -> Tuple[str, Optional[str], Optional[str]]:
        """
        Process the SOAP note template.
        
        Returns:
            Tuple of (template_name, result_text, error_message)
        """
        try:
            from medical_notes.prompts.all_prompts import get_note_template
            
            self._thread_safe_print("Processing SOAP note...")
            soap_template_config = get_note_template("soap", full_text)

            soap_note_text = self.invoke_bedrock(
                soap_template_config["system_prompt"],
                soap_template_config["prompt"],
                max_tokens=self.max_tokens,
                temperature=0,
                section_name="template_soap"
            )

            self._thread_safe_print(f"\u2713 SOAP note generated successfully")
            return "soap", soap_note_text, None
            
        except Exception as e:
            error_msg = f"Error processing SOAP template: {str(e)}"
            self._thread_safe_print(f"ERROR: {error_msg}")
            return "soap", None, error_msg
    
    def _process_notes_digest_template(self, full_text: str) -> Tuple[str, Optional[str], Optional[str]]:
        """
        Process the Notes Digest template.
        
        Returns:
            Tuple of (template_name, result_text, error_message)
        """
        try:
            from medical_notes.prompts.all_prompts import get_note_template
            
            self._thread_safe_print("Processing Notes Digest template...")
            notes_digest_template_config = get_note_template("notes_digest", full_text)

            notes_digest_text = self.invoke_bedrock(
                notes_digest_template_config["system_prompt"],
                notes_digest_template_config["prompt"],
                max_tokens=self.max_tokens,
                temperature=0,
                section_name="template_notes_digest"
            )

            self._thread_safe_print(f"\u2713 Notes Digest generated successfully")
            
            # Validate and clean the LLM response to extract valid JSON
            try:
                import json
                import re
                
                # Clean the response - remove markdown code blocks if present
                cleaned_response = notes_digest_text.strip()
                
                # Remove markdown code blocks (```json ... ``` or ``` ... ```)
                if cleaned_response.startswith('```'):
                    # Find the first { and last }
                    start_idx = cleaned_response.find('{')
                    end_idx = cleaned_response.rfind('}')
                    if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                        cleaned_response = cleaned_response[start_idx:end_idx + 1]
                        self._thread_safe_print(f"    ✓ Removed markdown code blocks from LLM response")
                
                # Try to parse the cleaned response
                json.loads(cleaned_response)
                self._thread_safe_print(f"    ✓ Notes digest is valid JSON format")
                notes_digest_data = cleaned_response
                
            except json.JSONDecodeError as e:
                self._thread_safe_print(f"    ⚠️ Notes digest is not valid JSON: {str(e)}")
                self._thread_safe_print(f"    ⚠️ LLM returned: {notes_digest_text[:200]}...")
                
                # Try to extract JSON from the response using regex as fallback
                try:
                    # Look for JSON pattern starting with { and ending with }
                    json_match = re.search(r'\{.*\}', notes_digest_text, re.DOTALL)
                    if json_match:
                        potential_json = json_match.group(0)
                        json.loads(potential_json)  # Validate it's proper JSON
                        notes_digest_data = potential_json
                        self._thread_safe_print(f"    ✓ Extracted valid JSON using regex fallback")
                    else:
                        self._thread_safe_print(f"    ⚠️ Could not extract valid JSON, using raw response")
                        notes_digest_data = notes_digest_text
                except:
                    self._thread_safe_print(f"    ⚠️ Regex extraction failed, using raw response")
                    notes_digest_data = notes_digest_text
            
            return "notes_digest", notes_digest_data, None
            
        except Exception as e:
            error_msg = f"Error processing Notes Digest template: {str(e)}"
            self._thread_safe_print(f"ERROR: {error_msg}")
            return "notes_digest", None, error_msg

    def process_medical_records(
        self,
        text_records: Union[Dict[str, str], pd.DataFrame],
        note_type: str = "soap"
    ) -> tuple[Optional[Dict[str, Any]], Optional[str]]:
        """
        Main processing pipeline using templates per note type with parallel processing.

        Args:
            text_records: Medical records as dict or DataFrame
            note_type: Type of medical note

        Returns:
            Tuple of (result_dict, error_message)
        """
        if isinstance(text_records, pd.DataFrame):
            text_records = self._convert_dataframe_to_dict(text_records)

        # Get full text
        full_text = "\n\n".join([
            f"{'='*80}\nRECORD ID: {record_id}\n{'='*80}\n{text}"
            for record_id, text in text_records.items()
        ])

        print(f"\n{'='*80}")
        print(f"Processing {len(text_records)} medical record(s)")
        print(f"Note Type: {note_type.upper().replace('_', ' ')}")
        print(f"Processing templates in parallel...")
        print(f"{'='*80}\n")

        try:
            # Process all templates in parallel using ThreadPoolExecutor
            with ThreadPoolExecutor(max_workers=3) as executor:
                # Submit all three tasks
                future_to_template = {
                    executor.submit(self._process_note_type_template, note_type, full_text): f"template_{note_type}",
                    executor.submit(self._process_soap_template, full_text): "soap",
                    executor.submit(self._process_notes_digest_template, full_text): "notes_digest"
                }
                
                # Collect results as they complete
                results = {}
                errors = []
                
                for future in as_completed(future_to_template):
                    template_name, result_text, error_msg = future.result()
                    
                    if error_msg:
                        errors.append(error_msg)
                    else:
                        results[template_name] = result_text
            
            # Check if we have any critical errors
            if len(errors) == 3:  # All templates failed
                error_msg = f"All template processing failed: {'; '.join(errors)}"
                print(f"ERROR: {error_msg}\n")
                return None, error_msg
            
            # Build result dictionary with available results
            result = {}
            
            # Map results to expected keys
            if f"template_{note_type}" in results:
                result['processed_data'] = results[f"template_{note_type}"]
            
            if "soap" in results:
                result['soap_data'] = results["soap"]
            
            if "notes_digest" in results:
                result['notes_digest'] = results["notes_digest"]
            
            # Report any partial failures
            if errors:
                self._thread_safe_print(f"⚠️ Some templates failed: {'; '.join(errors)}")
            
            print(f"SUCCESS: Processing completed successfully")
            print(f"Processed templates: {list(result.keys())}")
            print(f"{'='*80}\n")

            return result, None

        except Exception as e:
            error_msg = f"Medical data extraction failed: {str(e)}"
            print(f"ERROR: {error_msg}\n")
            return None, error_msg