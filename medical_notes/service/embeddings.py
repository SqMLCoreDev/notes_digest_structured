"""
Medical Notes Embeddings Service
Generates and stores vector embeddings for clinical notes using AWS Bedrock and PostgreSQL
"""

import time
import logging
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime

from langchain_aws import BedrockEmbeddings
from langchain_postgres import PGVector
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from elasticsearch import Elasticsearch
from elasticsearch.helpers import scan

# Import configuration
from medical_notes.config.config import (
    ES_URL, ES_USER, ES_PASSWORD, ES_INDEX_CLINICAL_NOTES,
    VECTOR_DB_CONNECTION, VECTOR_DB_COLLECTION_NAME, EMBEDDINGS_MODEL_ID,
    EMBEDDINGS_CHUNK_SIZE, EMBEDDINGS_CHUNK_OVERLAP, EMBEDDINGS_MAX_RETRIES, EMBEDDINGS_RETRY_DELAY,
    AWS_ACCESS_KEY, AWS_SECRET_ACCESS, AWS_REGION
)

# Set up logging
logger = logging.getLogger(__name__)


class EmbeddingsServiceError(Exception):
    """Custom exception for embeddings service errors"""
    pass


class EmbeddingsService:
    """Service for generating and storing medical note embeddings"""
    
    def __init__(self):
        """Initialize the embeddings service with configuration"""
        self.es_client = None
        self.embeddings_model = None
        self.vector_store = None
        self.text_splitter = None
        self._initialize_components()
    
    def _initialize_components(self):
        """Initialize Elasticsearch, embeddings model, and vector store"""
        try:
            # Initialize Elasticsearch client
            self.es_client = Elasticsearch(
                ES_URL,
                http_auth=(ES_USER, ES_PASSWORD),
                scheme="https",
                port=443,
                verify_certs=False
            )
            
            # Initialize embeddings model
            self.embeddings_model = BedrockEmbeddings(
                model_id=EMBEDDINGS_MODEL_ID,
                region_name=AWS_REGION
            )
            
            # Initialize text splitter
            self.text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=EMBEDDINGS_CHUNK_SIZE,
                chunk_overlap=EMBEDDINGS_CHUNK_OVERLAP,
                add_start_index=True
            )
            
            # Initialize vector store
            self.vector_store = PGVector(
                embeddings=self.embeddings_model,
                collection_name=VECTOR_DB_COLLECTION_NAME,
                connection=VECTOR_DB_CONNECTION,
                use_jsonb=True,
            )
            
            logger.info("Embeddings service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize embeddings service: {str(e)}")
            raise EmbeddingsServiceError(f"Initialization failed: {str(e)}")
    
    def fetch_note_from_elasticsearch(self, note_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch note data from Elasticsearch by note ID
        
        Args:
            note_id: The unique identifier of the clinical note
            
        Returns:
            Dict containing note data or None if not found
            
        Raises:
            EmbeddingsServiceError: If ES query fails
        """
        try:
            logger.info(f"Fetching note {note_id} from Elasticsearch")
            
            # Search for the note by noteId
            query = {
                "query": {
                    "term": {"noteId": note_id}
                }
            }
            
            response = self.es_client.search(
                index=ES_INDEX_CLINICAL_NOTES,
                body=query,
                size=1
            )
            
            if response['hits']['total']['value'] == 0:
                logger.warning(f"Note {note_id} not found in Elasticsearch")
                return None
            
            note_data = response['hits']['hits'][0]['_source']
            logger.info(f"Successfully fetched note {note_id}")
            return note_data
            
        except Exception as e:
            logger.error(f"Error fetching note {note_id} from Elasticsearch: {str(e)}")
            raise EmbeddingsServiceError(f"Failed to fetch note from Elasticsearch: {str(e)}")
    
    def validate_note_data(self, note_data: Dict[str, Any], note_id: str) -> None:
        """
        Validate that note data contains required fields
        
        Args:
            note_data: Note data from Elasticsearch
            note_id: Note ID for error messages
            
        Raises:
            EmbeddingsServiceError: If validation fails
        """
        if not note_data:
            raise EmbeddingsServiceError(f"Note {note_id}: No data provided")
        
        rawdata = note_data.get("rawdata", "")
        if not rawdata or not rawdata.strip():
            raise EmbeddingsServiceError(f"Note {note_id}: rawdata field is empty or missing")
        
        logger.info(f"Note {note_id}: Validation passed, rawdata length: {len(rawdata)} characters")
    
    def prepare_documents_for_embedding(self, note_data: Dict[str, Any]) -> List[Document]:
        """
        Prepare LangChain documents with metadata for embedding
        
        Args:
            note_data: Note data from Elasticsearch
            
        Returns:
            List of LangChain Document objects
        """
        # Extract content and metadata
        page_content = note_data.get("rawdata", "")
        metadata = {
            "noteId": note_data.get("noteId"),
            "locationname": note_data.get("locationname"),
            "noteType": note_data.get("noteType"),
            "serviceDate": note_data.get("serviceDate"),
            "patientID": note_data.get("patientID"),
            "status": note_data.get("status"),
            "patientMRN": note_data.get("patientMRN"),
            "processed_at": datetime.now().isoformat()
        }
        
        # Create initial document
        document = Document(page_content=page_content, metadata=metadata)
        
        # Split into chunks
        chunks = self.text_splitter.split_documents([document])
        
        # Enhance each chunk with metadata prefix
        enhanced_chunks = []
        for i, chunk in enumerate(chunks):
            # Create metadata info string
            metadata_info = " | ".join([f"{k}: {v}" for k, v in metadata.items() if v is not None])
            
            # Prepend metadata to content
            enhanced_content = f"{metadata_info}\n{chunk.page_content}"
            
            # Update content
            chunk.page_content = enhanced_content
            enhanced_chunks.append(chunk)
        
        logger.info(f"Prepared {len(enhanced_chunks)} document chunks for embedding")
        return enhanced_chunks
    
    def generate_and_store_embeddings(self, documents: List[Document], note_id: str) -> int:
        """
        Generate embeddings and store in vector database with retry logic
        
        Args:
            documents: List of LangChain documents to embed
            note_id: Note ID for logging
            
        Returns:
            Number of documents successfully processed
            
        Raises:
            EmbeddingsServiceError: If embedding generation or storage fails
        """
        retry_count = 0
        last_error = None
        
        while retry_count < EMBEDDINGS_MAX_RETRIES:
            try:
                logger.info(f"Note {note_id}: Generating embeddings (attempt {retry_count + 1}/{EMBEDDINGS_MAX_RETRIES})")
                
                # Add documents to vector store (this generates embeddings and stores them)
                self.vector_store.add_documents(documents)
                
                logger.info(f"Note {note_id}: Successfully stored {len(documents)} document chunks with embeddings")
                return len(documents)
                
            except Exception as e:
                retry_count += 1
                last_error = e
                logger.warning(f"Note {note_id}: Embedding attempt {retry_count} failed: {str(e)}")
                
                if retry_count < EMBEDDINGS_MAX_RETRIES:
                    delay = EMBEDDINGS_RETRY_DELAY * (2 ** (retry_count - 1))  # Exponential backoff
                    logger.info(f"Note {note_id}: Retrying in {delay} seconds...")
                    time.sleep(delay)
        
        # All retries failed
        error_msg = f"Failed to generate embeddings after {EMBEDDINGS_MAX_RETRIES} attempts. Last error: {str(last_error)}"
        logger.error(f"Note {note_id}: {error_msg}")
        raise EmbeddingsServiceError(error_msg)
    
    def process_note_embeddings(self, note_id: str) -> Dict[str, Any]:
        """
        Main method to process embeddings for a clinical note
        
        Args:
            note_id: The unique identifier of the clinical note to process
            
        Returns:
            Dict with processing results and statistics
            
        Raises:
            EmbeddingsServiceError: If any step in the process fails
        """
        start_time = time.time()
        
        try:
            logger.info(f"Starting embeddings processing for note {note_id}")
            
            # Step 1: Fetch note from Elasticsearch
            note_data = self.fetch_note_from_elasticsearch(note_id)
            if not note_data:
                raise EmbeddingsServiceError(f"Note {note_id} not found")
            
            # Step 2: Validate note data
            self.validate_note_data(note_data, note_id)
            
            # Step 3: Prepare documents for embedding
            documents = self.prepare_documents_for_embedding(note_data)
            
            # Step 4: Generate and store embeddings
            chunks_processed = self.generate_and_store_embeddings(documents, note_id)
            
            # Calculate processing time
            processing_time = time.time() - start_time
            
            result = {
                "success": True,
                "note_id": note_id,
                "chunks_processed": chunks_processed,
                "processing_time_seconds": round(processing_time, 2),
                "note_type": note_data.get("noteType"),
                "patient_mrn": note_data.get("patientMRN"),
                "service_date": note_data.get("serviceDate"),
                "rawdata_length": len(note_data.get("rawdata", "")),
                "processed_at": datetime.now().isoformat()
            }
            
            logger.info(f"Successfully completed embeddings processing for note {note_id}: "
                       f"{chunks_processed} chunks in {processing_time:.2f} seconds")
            
            return result
            
        except EmbeddingsServiceError:
            # Re-raise our custom errors
            raise
        except Exception as e:
            # Wrap unexpected errors
            error_msg = f"Unexpected error processing embeddings for note {note_id}: {str(e)}"
            logger.error(error_msg)
            raise EmbeddingsServiceError(error_msg)


# Global service instance
_embeddings_service = None


def get_embeddings_service() -> EmbeddingsService:
    """Get or create the global embeddings service instance"""
    global _embeddings_service
    if _embeddings_service is None:
        _embeddings_service = EmbeddingsService()
    return _embeddings_service


def process_note_embeddings(note_id: str) -> Dict[str, Any]:
    """
    Convenience function to process embeddings for a clinical note
    
    Args:
        note_id: The unique identifier of the clinical note to process
        
    Returns:
        Dict with processing results and statistics
        
    Raises:
        EmbeddingsServiceError: If processing fails
    """
    service = get_embeddings_service()
    return service.process_note_embeddings(note_id)


if __name__ == "__main__":
    # Example usage
    import sys
    
    if len(sys.argv) > 1:
        note_id = sys.argv[1]
        try:
            result = process_note_embeddings(note_id)
            print(f"✅ Success: {result}")
        except EmbeddingsServiceError as e:
            print(f"❌ Error: {e}")
            sys.exit(1)
    else:
        print("Usage: python embeddings.py <note_id>")
        print("Example: python embeddings.py 12345")