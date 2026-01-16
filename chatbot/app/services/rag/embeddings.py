"""
app/services/rag/embeddings.py - Amazon Titan Embeddings

Handles embeddings generation using AWS Bedrock and Amazon Titan.
"""

import asyncio
from typing import List, Optional
from concurrent.futures import ThreadPoolExecutor

from app.core.config import settings
from app.core.logging import get_logger
from app.core.exceptions import ConfigurationError

logger = get_logger(__name__)

# Thread pool for running boto3 sync calls
_embeddings_executor = ThreadPoolExecutor(max_workers=5)

# Try to import langchain-aws
try:
    from langchain_aws import BedrockEmbeddings
    LANGCHAIN_AWS_AVAILABLE = True
except ImportError:
    LANGCHAIN_AWS_AVAILABLE = False
    BedrockEmbeddings = None


class EmbeddingsClient:
    """
    Client for generating embeddings using Amazon Titan via AWS Bedrock.
    Provides async wrapper around langchain BedrockEmbeddings.
    """
    
    def __init__(self):
        """Initialize embeddings client with AWS Bedrock."""
        if not LANGCHAIN_AWS_AVAILABLE:
            raise ConfigurationError(
                message="langchain-aws not installed. Install with: pip install langchain-aws",
                details={"package": "langchain-aws"}
            )
        
        self.model_id = settings.EMBEDDINGS_MODEL
        self.region = settings.AWS_REGION
        
        try:
            # Initialize BedrockEmbeddings
            if settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY:
                import boto3
                bedrock_client = boto3.client(
                    'bedrock-runtime',
                    region_name=self.region,
                    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
                )
                self.embeddings = BedrockEmbeddings(
                    client=bedrock_client,
                    model_id=self.model_id
                )
            else:
                self.embeddings = BedrockEmbeddings(
                    region_name=self.region,
                    model_id=self.model_id
                )
            
            logger.info(f"Initialized embeddings client with model {self.model_id}")
            
        except Exception as e:
            raise ConfigurationError(
                message=f"Failed to initialize embeddings client: {str(e)}",
                details={"model": self.model_id, "region": self.region}
            )
    
    def embed_query_sync(self, text: str) -> List[float]:
        """
        Generate embeddings for a query (synchronous).
        
        Args:
            text: Text to embed
            
        Returns:
            List of embedding values
        """
        return self.embeddings.embed_query(text)
    
    async def embed_query(self, text: str) -> List[float]:
        """
        Generate embeddings for a query (async).
        
        Args:
            text: Text to embed
            
        Returns:
            List of embedding values
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            _embeddings_executor,
            self.embed_query_sync,
            text
        )
    
    def embed_documents_sync(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple documents (synchronous).
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
        """
        return self.embeddings.embed_documents(texts)
    
    async def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple documents (async).
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            _embeddings_executor,
            self.embed_documents_sync,
            texts
        )
    
    def get_langchain_embeddings(self):
        """
        Get the underlying LangChain embeddings object.
        Useful for direct integration with vector stores.
        
        Returns:
            BedrockEmbeddings instance
        """
        return self.embeddings


# Singleton instance
_embeddings_client: Optional[EmbeddingsClient] = None


def get_embeddings_client() -> Optional[EmbeddingsClient]:
    """
    Get the embeddings client singleton.
    Returns None if langchain-aws is not available.
    """
    global _embeddings_client
    
    if not LANGCHAIN_AWS_AVAILABLE:
        logger.warning("langchain-aws not available, embeddings client disabled")
        return None
    
    if _embeddings_client is None:
        try:
            _embeddings_client = EmbeddingsClient()
        except Exception as e:
            logger.warning(f"Failed to initialize embeddings client: {e}")
            return None
    
    return _embeddings_client
