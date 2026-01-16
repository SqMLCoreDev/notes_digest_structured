"""
Token Usage Tracker for Medical Notes Processing
Tracks token usage per section and calculates total cost per note
Pushes token usage to Elasticsearch index from configuration
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime
import os
import json
from pathlib import Path
import pandas as pd
from medical_notes.config.config import ES_INDEX_TOKEN_USAGE


# Claude model pricing on AWS Bedrock (as of 2025)
# https://aws.amazon.com/bedrock/pricing/
PRICING = {
    "claude-haiku-3-5": {
        "input_per_1k": 0.001,   # $0.001 per 1K input tokens ($1/million)
        "output_per_1k": 0.005,  # $0.005 per 1K output tokens ($5/million)
    },
    "claude-haiku-4-5": {
        "input_per_1k": 0.001,   # $0.001 per 1K input tokens ($1/million)
        "output_per_1k": 0.005,  # $0.005 per 1K output tokens ($5/million)
    },
    "claude-sonnet-3-5": {
        "input_per_1k": 0.006,   # $0.006 per 1K input tokens
        "output_per_1k": 0.03,  # $0.03 per 1K output tokens
    }
}




@dataclass
class SectionTokenUsage:
    """Token usage for a single section/API call"""
    section_name: str
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    timestamp: str = ""
    # TODO: Enable timing features later
    # start_time: Optional[datetime] = None
    # end_time: Optional[datetime] = None
    # duration_seconds: float = 0.0
    
    def calculate_cost(self, model: str = "claude-haiku-4-5") -> float:
        """Calculate cost for this section"""
        pricing = PRICING.get(model, PRICING["claude-haiku-4-5"])
        input_cost = (self.input_tokens / 1000) * pricing["input_per_1k"]
        output_cost = (self.output_tokens / 1000) * pricing["output_per_1k"]
        self.cost_usd = input_cost + output_cost
        return self.cost_usd
    
    # TODO: Enable timing features later
    # def set_timing(self, start_time: datetime, end_time: datetime) -> None:
    #     """Set timing information for this section"""
    #     self.start_time = start_time
    #     self.end_time = end_time
    #     if start_time and end_time:
    #         self.duration_seconds = (end_time - start_time).total_seconds()
    
    def to_dict(self) -> dict:
        return {
            "section_name": self.section_name,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.input_tokens + self.output_tokens,
            "cost_usd": round(self.cost_usd, 6)
            # TODO: Enable timing features later
            # "duration_seconds": round(self.duration_seconds, 3),
            # "start_time": self.start_time.isoformat() if self.start_time else None,
            # "end_time": self.end_time.isoformat() if self.end_time else None
        }


@dataclass
class TokenTracker:
    """Track token usage across all sections of a note processing job"""
    note_id: str = ""
    sections: List[SectionTokenUsage] = field(default_factory=list)
    model: str = "claude-haiku-4-5"
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    
    def add_usage(self, section_name: str, input_tokens: int, output_tokens: int, start_time: Optional[datetime] = None, end_time: Optional[datetime] = None) -> SectionTokenUsage:
        """Add token usage for a section with optional timing"""
        section = SectionTokenUsage(
            section_name=section_name,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            timestamp=datetime.now().isoformat()
        )
        section.calculate_cost(self.model)
        
        # TODO: Enable timing features later
        # Set timing if provided
        # if start_time and end_time:
        #     section.set_timing(start_time, end_time)
        
        self.sections.append(section)
        return section
    
    def get_total_input_tokens(self) -> int:
        """Get total input tokens across all sections"""
        return sum(s.input_tokens for s in self.sections)
    
    def get_total_output_tokens(self) -> int:
        """Get total output tokens across all sections"""
        return sum(s.output_tokens for s in self.sections)
    
    def get_total_tokens(self) -> int:
        """Get total tokens (input + output)"""
        return self.get_total_input_tokens() + self.get_total_output_tokens()
    
    def get_total_cost(self) -> float:
        """Get total cost in USD"""
        return sum(s.cost_usd for s in self.sections)
    
    # TODO: Enable timing features later
    # def get_total_duration_seconds(self) -> float:
    #     """Get total duration of all sections in seconds"""
    #     return sum(s.duration_seconds for s in self.sections if s.duration_seconds > 0)
    
    def set_end_time(self) -> None:
        """Mark the end of processing"""
        self.end_time = datetime.now()
    
    def get_processing_duration_seconds(self) -> float:
        """Get processing duration in seconds"""
        end = self.end_time or datetime.now()
        return (end - self.start_time).total_seconds()
    
    def get_processing_duration_formatted(self) -> str:
        """Get processing duration as formatted string (mm:ss)"""
        duration = self.get_processing_duration_seconds()
        minutes = int(duration // 60)
        seconds = duration % 60
        return f"{minutes}m {seconds:.1f}s"
    
    def get_section_breakdown(self) -> List[dict]:
        """Get breakdown by section"""
        return [s.to_dict() for s in self.sections]
    
    def get_summary(self) -> dict:
        """Get complete token usage summary"""
        return {
            "note_id": self.note_id,
            "model": self.model,
            "processing_duration_seconds": round(self.get_processing_duration_seconds(), 2),
            "processing_duration_formatted": self.get_processing_duration_formatted(),
            # TODO: Enable timing features later
            # "sections_total_duration_seconds": round(self.get_total_duration_seconds(), 2),
            "total_input_tokens": self.get_total_input_tokens(),
            "total_output_tokens": self.get_total_output_tokens(),
            "total_tokens": self.get_total_tokens(),
            "total_cost_usd": round(self.get_total_cost(), 6),
            "section_count": len(self.sections),
            "sections": self.get_section_breakdown()
        }
    
    def print_summary(self) -> str:
        """Generate a printable summary string"""
        lines = [
            "\n" + "=" * 60,
            "TOKEN USAGE SUMMARY",
            "=" * 60,
            f"Note ID: {self.note_id}",
            f"Model: {self.model}",
            f"Processing Time: {self.get_processing_duration_formatted()}",
            # TODO: Enable timing features later
            # f"Sections Total Time: {self.get_total_duration_seconds():.2f}s",
            "-" * 60,
            "SECTION BREAKDOWN:",
        ]
        
        for section in self.sections:
            # TODO: Enable timing features later
            # duration_str = f" ({section.duration_seconds:.2f}s)" if section.duration_seconds > 0 else ""
            lines.append(
                f"  • {section.section_name}: "
                f"{section.input_tokens:,} in / {section.output_tokens:,} out = "
                f"{section.input_tokens + section.output_tokens:,} tokens "
                f"(${section.cost_usd:.6f})"
                # TODO: Enable timing features later
                # f"(${section.cost_usd:.6f}){duration_str}"
            )
        
        lines.extend([
            "-" * 60,
            "TOTALS:",
            f"  • Input Tokens:  {self.get_total_input_tokens():,}",
            f"  • Output Tokens: {self.get_total_output_tokens():,}",
            f"  • Total Tokens:  {self.get_total_tokens():,}",
            f"  • Total Cost:    ${self.get_total_cost():.6f} USD",
            f"  • Duration:      {self.get_processing_duration_formatted()}",
            # TODO: Enable timing features later
            # f"  • Sections Time: {self.get_total_duration_seconds():.2f}s",
            "=" * 60,
        ])
        
        return "\n".join(lines)
    
    def push_to_elasticsearch(self) -> bool:
        """
        Push token usage to Elasticsearch index from configuration.
        Enhanced with comprehensive timestamp tracking including:
        - processedAtEpoch: When token usage was recorded/indexed
        - processingTimeStartEpoch: When note processing began
        - processingTimeEndEpoch: When note processing completed
        Creates one document per section with common fields.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            from medical_notes.repository.elastic_search import df_to_es_load
            # Import timestamp utilities
            from medical_notes.utils.timestamp_utils import TimestampManager, get_current_processing_tracker
            
            # Set end time if not already set
            if not self.end_time:
                self.set_end_time()
            
            # Format datetime to MM/dd/yyyy HH:mm:ss
            def format_datetime(dt_obj):
                if dt_obj:
                    return dt_obj.strftime("%m/%d/%Y %H:%M:%S")
                return None
            
            # Convert datetime to epoch (milliseconds since Unix epoch)
            def datetime_to_epoch(dt_obj):
                if dt_obj:
                    return int(dt_obj.timestamp() * 1000)
                return None
            
            now = datetime.now()
            
            # Enhanced timestamp tracking using ProcessingTracker
            tracker = get_current_processing_tracker()
            
            # Get enhanced timestamps from tracker or generate fallback timestamps
            if tracker:
                timestamps = tracker.get_timestamps()
                processed_at_epoch = timestamps.get('processed_at', TimestampManager.current_epoch_ms())
                processing_start_epoch = timestamps.get('processing_start', datetime_to_epoch(self.start_time))
                processing_end_epoch = timestamps.get('processing_end', datetime_to_epoch(self.end_time))
                print(f"    ✓ Using ProcessingTracker timestamps for token usage (note {self.note_id})")
            else:
                # Fallback: use existing datetime objects and current time
                processed_at_epoch = TimestampManager.current_epoch_ms()
                processing_start_epoch = datetime_to_epoch(self.start_time) or TimestampManager.current_epoch_ms()
                processing_end_epoch = datetime_to_epoch(self.end_time) or TimestampManager.current_epoch_ms()
                print(f"    ⚠️ ProcessingTracker not found for token usage, using fallback timestamps (note {self.note_id})")
            
            # Validate timestamp format
            if not TimestampManager.validate_epoch_timestamp(processed_at_epoch):
                print(f"    ⚠️ Invalid processedAtEpoch timestamp, using current time")
                processed_at_epoch = TimestampManager.current_epoch_ms()
            
            if not TimestampManager.validate_epoch_timestamp(processing_start_epoch):
                print(f"    ⚠️ Invalid processingTimeStartEpoch timestamp, using current time")
                processing_start_epoch = TimestampManager.current_epoch_ms()
                
            if not TimestampManager.validate_epoch_timestamp(processing_end_epoch):
                print(f"    ⚠️ Invalid processingTimeEndEpoch timestamp, using current time")
                processing_end_epoch = TimestampManager.current_epoch_ms()
            
            print(f"\n  [Token Usage Timestamp Tracking] Enhanced timestamp fields:")
            print(f"    • processedAtEpoch: {processed_at_epoch}")
            print(f"    • processingTimeStartEpoch: {processing_start_epoch}")
            print(f"    • processingTimeEndEpoch: {processing_end_epoch}")
            
            # Common fields for all section documents (enhanced with new timestamp fields)
            common_fields = {
                "documentId": self.note_id,
                "model": self.model,
                "processedAt": format_datetime(now),
                "processedAtEpoch": processed_at_epoch,  # Enhanced timestamp field
                "processingTimeStart": format_datetime(self.start_time),
                "processingTimeStartEpoch": processing_start_epoch,  # Enhanced timestamp field
                "processingTimeEnd": format_datetime(self.end_time),
                "processingTimeEndEpoch": processing_end_epoch,  # Enhanced timestamp field
                "processingTimeDurationSeconds": round(self.get_processing_duration_seconds(), 2),
                "processingTimeDurationFormatted": self.get_processing_duration_formatted(),
                # TODO: Enable timing features later
                # "sectionsTotalDurationSeconds": round(self.get_total_duration_seconds(), 2),
                "totalsInputTokens": self.get_total_input_tokens(),
                "totalsOutputTokens": self.get_total_output_tokens(),
                "totalsTotalTokens": self.get_total_tokens(),
                "totalsCostUSD": round(self.get_total_cost(), 6)
            }
            
            # Create one document per section
            documents = []
            for section in self.sections:
                doc = {
                    **common_fields,
                    "sectionName": section.section_name,
                    "sectionInputTokens": section.input_tokens,
                    "sectionOutputTokens": section.output_tokens,
                    "sectionTotalTokens": section.input_tokens + section.output_tokens,
                    "sectionCostUSD": round(section.cost_usd, 6)
                    # TODO: Enable timing features later
                    # "sectionDurationSeconds": round(section.duration_seconds, 3),
                    # "sectionStartTime": format_datetime(section.start_time) if section.start_time else None,
                    # "sectionEndTime": format_datetime(section.end_time) if section.end_time else None,
                    # "sectionStartTimeEpoch": datetime_to_epoch(section.start_time) if section.start_time else None,
                    # "sectionEndTimeEpoch": datetime_to_epoch(section.end_time) if section.end_time else None
                }
                documents.append(doc)
            
            if documents:
                # Convert to DataFrame and push to ES
                df = pd.DataFrame(documents)
                df_to_es_load(df, ES_INDEX_TOKEN_USAGE)
                print(f"📊 Token usage for noteId '{self.note_id}' pushed to ES index '{ES_INDEX_TOKEN_USAGE}' ({len(documents)} sections)")
                return True
            else:
                print(f"⚠️ No sections to push for noteId '{self.note_id}'")
                return False
                
        except Exception as e:
            print(f"❌ Error pushing token usage to ES: {str(e)}")
            return False


def extract_token_usage_from_response(response_body: dict) -> tuple:
    """
    Extract token usage from Bedrock response body.
    
    Args:
        response_body: Parsed JSON response from Bedrock
        
    Returns:
        tuple: (input_tokens, output_tokens)
    """
    usage = response_body.get('usage', {})
    input_tokens = usage.get('input_tokens', 0)
    output_tokens = usage.get('output_tokens', 0)
    return input_tokens, output_tokens


# Global tracker instance for the current processing job
_current_tracker: Optional[TokenTracker] = None


def init_tracker(note_id: str, model: str = "claude-haiku-4-5") -> TokenTracker:
    """Initialize a new token tracker for a note processing job"""
    global _current_tracker
    _current_tracker = TokenTracker(note_id=note_id, model=model)
    return _current_tracker


def get_current_tracker() -> Optional[TokenTracker]:
    """Get the current token tracker"""
    global _current_tracker
    return _current_tracker


def add_token_usage(section_name: str, input_tokens: int, output_tokens: int, start_time: Optional[datetime] = None, end_time: Optional[datetime] = None) -> Optional[SectionTokenUsage]:
    """Add token usage to the current tracker with optional timing"""
    global _current_tracker
    if _current_tracker:
        # TODO: Enable timing features later - for now ignore timing parameters
        return _current_tracker.add_usage(section_name, input_tokens, output_tokens)
    return None


def get_and_clear_tracker() -> Optional[TokenTracker]:
    """Get the current tracker and clear the global reference"""
    global _current_tracker
    tracker = _current_tracker
    _current_tracker = None
    return tracker

