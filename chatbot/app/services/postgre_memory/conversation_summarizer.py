"""
Conversation Summarizer Service

Automatically summarizes conversations when they exceed the message limit.
Maintains context while keeping memory usage manageable.
"""

from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
import json

from app.core.config import settings
from app.core.logging import get_logger
from app.services.clients.claude_client import ClaudeClient

logger = get_logger(__name__)


class ConversationSummarizer:
    """
    Service to summarize long conversations automatically.
    
    Strategy:
    1. When conversation > 30 messages, summarize older messages
    2. Keep recent 10 messages for immediate context
    3. Create summary of older 20+ messages
    4. Store summary as special message in PostgreSQL
    """
    
    def __init__(self):
        self.claude_client = ClaudeClient()
        self.max_messages = 30
        self.keep_recent = 10
        self.summary_prompt = """
Please create a concise summary of this conversation history. Focus on:
1. Key topics discussed
2. Important decisions or conclusions
3. Relevant context for future messages
4. User preferences or requirements mentioned

Keep the summary under 500 words and maintain the conversational context.

Conversation to summarize:
{conversation_history}

Summary:"""
    
    async def should_summarize(self, messages: List[Dict[str, Any]]) -> bool:
        """
        Check if conversation should be summarized.
        
        Args:
            messages: List of conversation messages
            
        Returns:
            bool: True if summarization is needed
        """
        # Count actual Q&A pairs (not individual messages)
        qa_pairs = self._count_qa_pairs(messages)
        return qa_pairs > self.max_messages
    
    def _count_qa_pairs(self, messages: List[Dict[str, Any]]) -> int:
        """Count question-answer pairs in the conversation."""
        # Each message in our format represents a Q&A pair
        return len([msg for msg in messages if msg.get('query') and msg.get('response')])
    
    async def summarize_conversation(
        self, 
        messages: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Summarize a long conversation.
        
        Args:
            messages: Full conversation history
            
        Returns:
            Tuple of (recent_messages, summary_entry)
        """
        if len(messages) <= self.max_messages:
            return messages, None
        
        # Split messages: older (to summarize) + recent (to keep)
        messages_to_summarize = messages[:-self.keep_recent]
        recent_messages = messages[-self.keep_recent:]
        
        logger.info(f"Summarizing {len(messages_to_summarize)} messages, keeping {len(recent_messages)} recent")
        
        # Create conversation text for summarization
        conversation_text = self._format_conversation_for_summary(messages_to_summarize)
        
        # Generate summary using Claude
        try:
            summary_text = await self._generate_summary(conversation_text)
            
            # Create summary entry
            summary_entry = {
                'query': '[CONVERSATION SUMMARY]',
                'response': summary_text,
                'used_indices': [],
                'timestamp': datetime.utcnow().isoformat(),
                'message_count': len(messages_to_summarize),
                'is_summary': True
            }
            
            # Return summary + recent messages
            summarized_conversation = [summary_entry] + recent_messages
            
            logger.info(f"Created summary of {len(messages_to_summarize)} messages")
            return summarized_conversation, summary_entry
            
        except Exception as e:
            logger.error(f"Failed to generate summary: {e}")
            # Fallback: just keep recent messages
            return recent_messages, None
    
    def _format_conversation_for_summary(self, messages: List[Dict[str, Any]]) -> str:
        """Format conversation messages for summarization."""
        conversation_parts = []
        
        for i, msg in enumerate(messages, 1):
            query = msg.get('query', '').strip()
            response = msg.get('response', '').strip()
            timestamp = msg.get('timestamp', '')
            
            if query and response:
                conversation_parts.append(f"""
Message {i} ({timestamp}):
User: {query}
Assistant: {response}
""")
        
        return "\n".join(conversation_parts)
    
    async def _generate_summary(self, conversation_text: str) -> str:
        """Generate summary using Claude."""
        try:
            prompt = self.summary_prompt.format(conversation_history=conversation_text)
            
            response = await self.claude_client.generate_response(
                prompt=prompt,
                max_tokens=1000,  # Limit summary length
                temperature=0.3   # More focused, less creative
            )
            
            return response.strip()
            
        except Exception as e:
            logger.error(f"Claude summarization error: {e}")
            # Fallback summary
            return f"[Auto-generated summary of previous conversation covering multiple topics and {len(conversation_text.split('Message'))} exchanges]"
    
    def is_summary_message(self, message: Dict[str, Any]) -> bool:
        """Check if a message is a conversation summary."""
        return message.get('is_summary', False) or message.get('query') == '[CONVERSATION SUMMARY]'
    
    def get_effective_context_length(self, messages: List[Dict[str, Any]]) -> int:
        """
        Calculate effective context length considering summaries.
        
        A summary represents multiple messages, so we count it differently.
        """
        total_length = 0
        
        for msg in messages:
            if self.is_summary_message(msg):
                # Summary represents multiple messages
                total_length += msg.get('message_count', 10)
            else:
                # Regular message
                total_length += 1
        
        return total_length


# Singleton instance
_summarizer: Optional[ConversationSummarizer] = None


def get_conversation_summarizer() -> ConversationSummarizer:
    """Get the conversation summarizer singleton."""
    global _summarizer
    if _summarizer is None:
        _summarizer = ConversationSummarizer()
    return _summarizer