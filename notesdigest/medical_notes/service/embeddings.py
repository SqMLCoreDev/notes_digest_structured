"""
Medical Notes Embeddings Service
Generates and stores vector embeddings for clinical notes using AWS Bedrock and PostgreSQL
"""

import time
import logging
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
import os
import boto3
from langchain_aws import BedrockEmbeddings, ChatBedrockConverse
from langchain_postgres import PGVector
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter, MarkdownHeaderTextSplitter
from elasticsearch import Elasticsearch
from elasticsearch.helpers import scan

# Import configuration
from medical_notes.config.config import (
    ES_URL, ES_USER, ES_PASSWORD, ES_INDEX_CLINICAL_NOTES,
    POSTGRES_CONNECTION, VECTOR_DB_COLLECTION_NAME, EMBEDDINGS_MODEL,
    EMBEDDINGS_CHUNK_SIZE, EMBEDDINGS_CHUNK_OVERLAP, EMBEDDINGS_MAX_RETRIES, EMBEDDINGS_RETRY_DELAY,
    AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION, CLAUDE_HAIKU_4_5
)

# Set up logging
logger = logging.getLogger(__name__)

HEADING_WISE_CHRONOLOGICAL_PROMPT = """
You are a clinical documentation engine. Extract information exactly as documented, without interpretation or inference.

INPUT:
Patient records across multiple encounters (notes, labs, imaging, vitals, medications).

OUTPUT:
HEADING-WISE clinical summary.
Under EACH heading, organize all content in strict chronological order (earliest → latest).

CORE RULES:
- Extract ONLY what is explicitly documented
- NO assumptions, interpretation, or summarization beyond wording in the record
- Use hyphen (-) bullets only
- Dates must be MM-DD-YYYY
- Times must be HH:MM (24-hour format)
- If information is not documented, explicitly state so
- Include data from ALL encounters and ALL dates
- Use markdown for every headings

================================================================

HEADING-WISE CHRONOLOGICAL SUMMARY

Patient Demographics:
- Name: [Name]
- Age: [Age]
- Sex: [Sex]
- DOB: [MM-DD-YYYY]
- MRN: [MRN]
- Allergies: [All allergies from ANY source or "NKDA"]

----------------------------------------------------------------

Patient Status:
- List ALL dates in chronological order

ADMISSION DAY FORMAT:
- [MM-DD-YYYY]: [Name], a [Age]-year-old [Sex] with significant past medical history of [PMH list] presented to the [Location] with [Complaints].
  Include overall status, major events, procedures, complications, transfers, and level-of-care changes documented for that day.

FOLLOW-UP DAY FORMAT:
- [MM-DD-YYYY]: Current status, symptom changes, procedures, events, and location/level-of-care changes.

If no documentation for a date:
- [MM-DD-YYYY]: No new symptoms or status changes documented

----------------------------------------------------------------

Vitals:
- For EACH documented date:
  - [MM-DD-YYYY]: Temperature, BP, HR, RR, SpO2 (include min/max if documented)
- If none for a date:
  - No vitals documented

----------------------------------------------------------------

Medication Updates:
- List ALL dates chronologically

ADMISSION:
- [MM-DD-YYYY]:
  - Continued: [Medication] [dose] [route] [frequency]
  (ALL medications including PRN must be listed as Continued on admission; NO specialty attribution)

FOLLOW-UP:
- [MM-DD-YYYY]:
  - Continued: [Medication] [dose] [route] [frequency]
  - Started: [Medication] [dose] [route] [frequency] | [Specialty/Department]
  - Stopped: [Medication] | [Specialty/Department] | [reason if documented]
  - Dosage Changed: [Medication] from [old dose] to [new dose] [route] [frequency] | [Specialty/Department]

MEDICATION RULES:
- Do NOT mark a medication as Started if it appears earlier in the record
- Planned or ordered dose increases/decreases count as Dosage Changed
- Started / Stopped / Dosage Changed REQUIRE specialty attribution
- If specialty not documented, use "Not specified"
- Continued medications must NOT include specialty
- If no medication changes on a date:
  - [MM-DD-YYYY]: No medication changes documented

----------------------------------------------------------------

Lab Updates:
- List chronologically by date

LAB RULES:
- ONLY abnormal labs marked (H) or (L)
- Exclude ALL normal labs entirely
- Include timestamp HH:MM when available
- Include reference ranges ONLY for abnormal values
- Plain text only (NO tables)

FORMAT:
- [MM-DD-YYYY]:
  - [HH:MM] - [Lab]: [Value] [units] (H/L) (Reference range: [range])
  OR
  - [Lab]: [Value] [units] (H/L) (Reference range: [range])

If none:
- No abnormal labs documented

----------------------------------------------------------------

Imaging Updates:
- List chronologically by study date

IMAGING RULES:
- IMPRESSION ONLY
- NO measurements, NO technique details, NO multi-paragraph findings
- Collapse each study into 1–2 concise impression sentences

FORMAT:
- [MM-DD-YYYY]:
  - [Study Type]: [Impression only]

If none:
- No imaging studies documented

----------------------------------------------------------------

Procedures:
- List chronologically
- Include procedures explicitly documented in notes or operative history

FORMAT:
- [MM-DD-YYYY]: [Procedure name]

If none:
- No procedures documented

----------------------------------------------------------------

Assessment & Plan:
- Organized by DATE, then SPECIALTY
- Chronological order

FORMAT:
- [MM-DD-YYYY]:

[Specialty] - [Provider Name, Credentials]:
Concise (2–3 lines) DAY-SPECIFIC summary of new diagnoses, diagnosis changes, procedures, medication changes, test orders, and specialty interventions.

ASSESSMENT & PLAN RULES:
- Provider name REQUIRED
- Use full name when available
- If provider not documented: "Provider not specified"
- If specialty note contains no plan:
  - Explicitly state: "No new assessments or management plans documented"
- General services (ED, Internal Medicine, Hospitalist): max 1–2 lines
- Exclude unchanged, historical, or background information

----------------------------------------------------------------

Signature Information:
- Extract ALL signatures from entire record

FORMAT:
- Electronically Signed By: [Name, credentials] at [MM/DD/YYYY HH:MM AM/PM]
- Cosigned By: [Name, credentials] at [MM/DD/YYYY HH:MM AM/PM] (if applicable)
- Additional Signatories: [List if present]

================================================================

DATA:
{note}
"""


class EmbeddingsServiceError(Exception):
    """Custom exception for embeddings service errors"""
    pass


class EmbeddingsService:
    """Service for generating and storing medical note embeddings"""
    
    def __init__(self):
        """Initialize the embeddings service with configuration"""
        self.es_client = None
        self.llm = None
        self.embeddings_model = None
        self.vector_store = None
        self.text_splitter = None
        self.markdown_splitter = None
        self._initialize_components()
    
    def _initialize_components(self):
        """Initialize Elasticsearch, LLM, embeddings model, and vector store"""
        try:
            # Initialize Elasticsearch client
            self.es_client = Elasticsearch(
                ES_URL,
                http_auth=(ES_USER, ES_PASSWORD),
                scheme="https",
                port=443,
                verify_certs=False
            )
            
            # Set AWS credentials in environment for good measure
            os.environ['AWS_ACCESS_KEY_ID'] = AWS_ACCESS_KEY_ID
            os.environ['AWS_SECRET_ACCESS_KEY'] = AWS_SECRET_ACCESS_KEY
            os.environ['AWS_REGION'] = AWS_REGION
            
            # Create an explicit Bedrock Runtime client - This is the most robust way in Docker
            bedrock_client = boto3.client(
                service_name="bedrock-runtime",
                region_name=AWS_REGION,
                aws_access_key_id=AWS_ACCESS_KEY_ID,
                aws_secret_access_key=AWS_SECRET_ACCESS_KEY
            )
            
            # Initialize LLM for summarization
            # Using 'model' because this version of ChatBedrockConverse expects it
            # Using explicit client to avoid region/credential lookup issues
            self.llm = ChatBedrockConverse(
                model=CLAUDE_HAIKU_4_5,
                client=bedrock_client
            )
            
            # Initialize embeddings model
            # BedrockEmbeddings uses 'model_id' and explicit client
            self.embeddings_model = BedrockEmbeddings(
                model_id=EMBEDDINGS_MODEL,
                client=bedrock_client
            )
            
            # Initialize text splitters
            self.text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=EMBEDDINGS_CHUNK_SIZE,
                chunk_overlap=EMBEDDINGS_CHUNK_OVERLAP,
                add_start_index=True
            )
            
            headers_to_split_on = [
                ("##", "Section"),
                ("###", "Subsection"),
            ]
            self.markdown_splitter = MarkdownHeaderTextSplitter(headers_to_split_on)
            
            # Initialize vector store
            self.vector_store = PGVector(
                embeddings=self.embeddings_model,
                collection_name=VECTOR_DB_COLLECTION_NAME,
                connection=POSTGRES_CONNECTION,
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
    
    def prepare_documents_for_embedding(self, note_data: Dict[str, Any], summarized_content: str) -> List[Document]:
        """
        Prepare LangChain documents with metadata for embedding using Markdown header splitting
        
        Args:
            note_data: Note data from Elasticsearch
            summarized_content: Summary text generated by LLM
            
        Returns:
            List of LangChain Document objects
        """
        # Extract metadata
        note_metadata = {
            "serviceDate": note_data.get("serviceDate"),
            "patientID": note_data.get("patientID"),
            "patientMRN": note_data.get("patientMRN"),
            "noteId": note_data.get("noteId"),
            "fin": note_data.get("fin"),
            "csn": note_data.get("csn"),
            "processed_at": datetime.now().isoformat()
        }
        
        # Prepare patient header for each chunk
        header_lines = []
        if note_data.get("patientID"):
            header_lines.append(f"Patient Name: {note_data.get('patientID')}")
        if note_data.get("patientMRN"):
            header_lines.append(f"Patient MRN: {note_data.get('patientMRN')}")
        patient_header = "\n".join(header_lines)
        
        # Split summarized content by Markdown headers
        md_header_splits = self.markdown_splitter.split_text(summarized_content)
        
        # Filter splits to only those with sections or subsections
        md_header_splits = [
            doc for doc in md_header_splits
            if doc.metadata.get("Section") or doc.metadata.get("Subsection")
        ]
        
        documents = []
        for chunk in md_header_splits:
            section = chunk.metadata.pop("Section", None)
            subsection = chunk.metadata.pop("Subsection", None)
            
            heading = ""
            if section:
                heading += f"## {section}\n"
            if subsection:
                heading += f"### {subsection}\n"
                
            # Combine header, heading, and original chunk content
            page_content = heading + chunk.page_content
            if patient_header:
                page_content = f"{patient_header}\n\n{page_content}"
                
            doc = Document(
                page_content=page_content,
                metadata=note_metadata
            )
            documents.append(doc)
        
        logger.info(f"Prepared {len(documents)} document chunks for embedding from LLM summary")
        return documents
    
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
            
            # Step 3: Call LLM to generate structured summary
            # Using ChatBedrockConverse as per verified pattern
            logger.info(f"Note {note_id}: Generating LLM summary for embeddings")
            raw_note = note_data.get("rawdata", "")
            prompt_content = HEADING_WISE_CHRONOLOGICAL_PROMPT.format(note=raw_note)
            
            llm_response = self.llm.invoke(prompt_content)
            summarized_content = llm_response.content
            
            if not summarized_content:
                raise EmbeddingsServiceError("LLM returned empty summary for embeddings")
            
            # Step 4: Prepare documents for embedding using the summary
            documents = self.prepare_documents_for_embedding(note_data, summarized_content)
            
            # Step 5: Generate and store embeddings
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