"""
app/services/clients/pgvector_client.py - PGVector Client for RAG

Handles vector store operations using PostgreSQL with pgvector extension.
Provides similarity search and context retrieval for RAG queries.
"""

import re
import asyncio
from typing import Any, Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor

from app.core.config import settings
from app.core.logging import get_logger
from app.core.exceptions import ConfigurationError

logger = get_logger(__name__)

# Thread pool for running sync vector store calls
_vector_executor = ThreadPoolExecutor(max_workers=5)

# Try to import langchain-postgres
try:
    from langchain_postgres import PGVector
    PGVECTOR_AVAILABLE = True
except ImportError:
    PGVECTOR_AVAILABLE = False
    PGVector = None


class VectorStoreClient:
    """
    Client for vector store operations using PGVector.
    Provides similarity search and metadata filtering for RAG.
    """
    
    def __init__(self, embeddings=None):
        """
        Initialize vector store client.
        
        Args:
            embeddings: LangChain embeddings object (BedrockEmbeddings)
        """
        if not PGVECTOR_AVAILABLE:
            raise ConfigurationError(
                message="langchain-postgres not installed. Install with: pip install langchain-postgres",
                details={"package": "langchain-postgres"}
            )
        
        if not settings.POSTGRES_CONNECTION:
            raise ConfigurationError(
                message="POSTGRES_CONNECTION not configured",
                details={"required": "POSTGRES_CONNECTION environment variable"}
            )
        
        if embeddings is None:
            raise ConfigurationError(
                message="Embeddings object required for vector store",
                details={"hint": "Pass BedrockEmbeddings or similar"}
            )
        
        self.collection_name = settings.COLLECTION_NAME
        self.connection = settings.POSTGRES_CONNECTION
        
        try:
            self.vector_store = PGVector(
                embeddings=embeddings,
                collection_name=self.collection_name,
                connection=self.connection,
                use_jsonb=True
            )
            logger.info(f"✅ Vector store initialized with collection: {self.collection_name}")
            
        except Exception as e:
            raise ConfigurationError(
                message=f"Failed to initialize vector store: {str(e)}",
                details={"collection": self.collection_name}
            )
    
    def similarity_search_sync(
        self, 
        query: str, 
        k: int = 2, 
        filter: Optional[Dict] = None
    ) -> List[Any]:
        """
        Perform similarity search (synchronous).
        
        Args:
            query: Query text
            k: Number of results to return
            filter: Optional metadata filter
            
        Returns:
            List of matching documents
        """
        return self.vector_store.similarity_search(
            query=query,
            k=k,
            filter=filter
        )
    
    async def similarity_search(
        self, 
        query: str, 
        k: int = 2, 
        filter: Optional[Dict] = None
    ) -> List[Any]:
        """
        Perform similarity search (async).
        
        Args:
            query: Query text
            k: Number of results to return
            filter: Optional metadata filter
            
        Returns:
            List of matching documents
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            _vector_executor,
            lambda: self.similarity_search_sync(query, k, filter)
        )
    
    async def retrieve_context(
        self, 
        query: str, 
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Retrieve context for RAG query.
        
        Args:
            query: User's query
            metadata: Optional metadata filters (MRN, noteId, etc.)
            
        Returns:
            Dict with success status and retrieved content
        """
        try:
            # Perform similarity search
            retrieved_docs = await self.similarity_search(
                query=query,
                k=2,
                filter=metadata
            )
            
            # Serialize the documents
            serialized = "\n\n".join(
                f"Source: {doc.metadata}\nContent: {doc.page_content}"
                for doc in retrieved_docs
            )
            
            return {
                'success': True,
                'serialized_content': serialized,
                'document_count': len(retrieved_docs),
                'documents': [
                    {
                        'metadata': doc.metadata,
                        'content': doc.page_content
                    } for doc in retrieved_docs
                ]
            }
            
        except Exception as e:
            logger.error(f"Error retrieving context: {e}")
            return {
                'success': False,
                'error': f'Error retrieving context: {str(e)}'
            }
    
    @staticmethod
    def extract_metadata_from_question(question: str) -> Optional[Dict]:
        """
        Extract metadata from user question for filtering.
        
        Args:
            question: User's question text
            
        Returns:
            Dict with extracted metadata or None
        """
        metadata = {}
        
        # Extract MRN numbers
        mrn_match = re.search(r"\bmrn\s*[:=]?\s*(\d+)", question, re.IGNORECASE)
        if mrn_match:
            metadata["patientMRN"] = mrn_match.group(1).zfill(6)
        
        # Extract note IDs
        note_match = re.search(r"\bnote(?:id|_id)?\s*[:=]?\s*(\d+)", question, re.IGNORECASE)
        if note_match:
            metadata["noteId"] = note_match.group(1)
        
        # Extract dates
        date_match = re.search(r"\b\d{2}-\d{2}-\d{4}\b", question)
        if date_match:
            metadata["serviceDate"] = date_match.group(0)
        
        # Extract patient names - multiple patterns
        patient_name = None
        
        # Pattern 1: "for [Name]" or "for patient [Name]"
        name_match1 = re.search(r"\bfor\s+(?:patient\s+)?([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)", question)
        if name_match1:
            patient_name = name_match1.group(1)
        
        # Pattern 2: "notes for [Name]" or "data for [Name]"
        name_match2 = re.search(r"\b(?:notes?|data|records?)\s+for\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)", question)
        if name_match2:
            patient_name = name_match2.group(1)
        
        # Pattern 3: "[Name]'s notes" or "[Name]'s data"
        name_match3 = re.search(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)'s\s+(?:notes?|data|records?)", question)
        if name_match3:
            patient_name = name_match3.group(1)
        
        # Pattern 4: "patient [Name]" anywhere in the question
        name_match4 = re.search(r"\bpatient\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)", question)
        if name_match4:
            patient_name = name_match4.group(1)
        
        # Pattern 5: Just a name at the end (like "documentation for Maria")
        name_match5 = re.search(r"\bfor\s+([A-Z][a-z]+)$", question)
        if name_match5:
            patient_name = name_match5.group(1)
        
        if patient_name:
            # Parse name into first and last
            name_parts = patient_name.strip().split()
            if len(name_parts) == 1:
                metadata["patientFirstName"] = name_parts[0]
            elif len(name_parts) == 2:
                metadata["patientFirstName"] = name_parts[0]
                metadata["patientLastName"] = name_parts[1]
            elif len(name_parts) > 2:
                metadata["patientFirstName"] = name_parts[0]
                metadata["patientLastName"] = " ".join(name_parts[1:])
        
        return metadata if metadata else None


# Singleton instance
_vector_store_client: Optional[VectorStoreClient] = None


def get_vector_store_client(embeddings=None) -> Optional[VectorStoreClient]:
    """
    Get the vector store client singleton.
    
    Args:
        embeddings: LangChain embeddings object (required on first call)
        
    Returns:
        VectorStoreClient instance or None if not configured
    """
    global _vector_store_client
    
    if not PGVECTOR_AVAILABLE:
        logger.warning("⚠️ PGVector not available. Install with: pip install langchain-postgres")
        return None
    
    if not settings.POSTGRES_CONNECTION:
        logger.warning("⚠️ POSTGRES_CONNECTION not configured. Vector store disabled.")
        return None
    
    if _vector_store_client is None:
        if embeddings is None:
            logger.warning("⚠️ Embeddings required to initialize vector store")
            return None
        
        try:
            _vector_store_client = VectorStoreClient(embeddings=embeddings)
        except Exception as e:
            logger.warning(f"⚠️ Failed to initialize vector store: {e}")
            return None
    
    return _vector_store_client
