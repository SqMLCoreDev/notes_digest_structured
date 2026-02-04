"""
app/services/mcp/mcp_server.py - MCP Server Implementation (Refactored)

Handles Claude MCP tool interactions and Elasticsearch query orchestration.
Enhanced with HL7 v2 Standard Segment Recognition and Query Pre-Analysis.
"""

import json
import io
import os
import re
import base64
import traceback
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime

# Set matplotlib cache directory for Lambda
os.environ['MPLCONFIGDIR'] = '/tmp/matplotlib'

try:
    import matplotlib
    matplotlib.use('Agg')  # Use non-interactive backend
    import matplotlib.pyplot as plt
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

from app.core.config import settings
from app.core.logging import get_logger
from app.core.exceptions import MCPException, OpenSearchError, ClaudeError
from app.services.clients.es_client import OpenSearchClient
from app.services.clients.claude_client import ClaudeClient, get_claude_client
from app.services.clients.pgvector_client import VectorStoreClient, get_vector_store_client
from app.services.rag.embeddings import get_embeddings_client

# Import prompts
try:
    from prompts import prompts, patient_note_templates, get_template_options_text
except ImportError:
    prompts = {}
    patient_note_templates = {}
    def get_template_options_text():
        return "No templates available"

logger = get_logger(__name__)


class MCPServer:
    """
    MCP Server for Elasticsearch integration with Claude.
    Provides tools for querying, aggregating, and analyzing ES data.
    """
    
    def __init__(
        self,
        es_client: Optional[OpenSearchClient] = None,
        claude_client: Optional[ClaudeClient] = None,
        vector_store: Optional[VectorStoreClient] = None
    ):
        """
        Initialize MCP Server.
        
        Args:
            es_client: OpenSearch client (creates default if not provided)
            claude_client: Claude client (creates default if not provided)
            vector_store: Vector store client for RAG (optional)
        """
        self.es_client = es_client or OpenSearchClient()
        self.claude_client = claude_client or get_claude_client()
        self.vector_store = vector_store
        
        # Track tool types used for debugging
        self._tool_types_used = set()
    
    def analyze_user_query(
        self,
        question: str,
        conversation_history: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """
        Analyze user query to detect template and identifier.
        Deterministic parsing using regex and keyword matching.
        
        Args:
            question: User's query string
            conversation_history: Previous conversation exchanges
            
        Returns:
            Dict with detected specifications
        """
        analysis = {
            'template': None,
            'identifier': None,
            'identifier_type': None
        }
        
        query_lower = question.lower()
        
        # Detect Template
        template_keywords = {
            'soap': 'soap_note',
            'neurology consult': 'neurology_consult',
            'neurology consultation': 'neurology_consult',
            'neurology progress note': 'neurology_progress',
            'neurology progress': 'neurology_progress',
            'comprehensive': 'comprehensive_consult',
            'resident': 'resident_attestation',
            'resident attestation': 'resident_attestation',
            'attestation': 'resident_attestation',
            'day by day': 'day_by_day_summary',
            'day-by-day': 'day_by_day_summary',
            'daily summary': 'day_by_day_summary'
        }
        
        sorted_keywords = sorted(template_keywords.keys(), key=len, reverse=True)
        for keyword in sorted_keywords:
            if keyword in query_lower:
                analysis['template'] = template_keywords[keyword]
                break
        
        # Check for template numbers
        if not analysis['template']:
            number_match = re.search(r'\b([1-7])\b', question)
            if number_match and any(w in query_lower for w in ['template', 'format', 'option', 'number', 'select']):
                template_num = int(number_match.group(1))
                template_keys = list(patient_note_templates.keys())
                if 0 < template_num <= len(template_keys):
                    analysis['template'] = template_keys[template_num - 1]
        
        # Detect Identifier
        if re.search(r'\bnoteid\b|\bnote\s*id\b|\bnote_id\b', query_lower):
            analysis['identifier_type'] = 'noteid'
            match = re.search(r'(?:noteid|note\s*id|note_id)\s*[:=]?\s*["\']?(\w+)["\']?', query_lower)
            if match:
                analysis['identifier'] = match.group(1)
        elif re.search(r'\bmrn\b', query_lower):
            analysis['identifier_type'] = 'mrn'
            match = re.search(r'mrn\s*[:=]?\s*["\']?(\w+)["\']?', query_lower)
            if match:
                analysis['identifier'] = match.group(1)
        else:
            # Check for patient name
            name_match = re.search(r'(?:for|patient|notes?\s+for)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)', question)
            if not name_match:
                name_match = re.search(r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)['']s", question)
            if not name_match:
                name_match = re.search(r'\b([A-Z][a-z]+\s+[A-Z][a-z]+)\b', question)
            
            if name_match:
                analysis['identifier_type'] = 'name'
                analysis['identifier'] = name_match.group(1)
        
        logger.debug(f"Query analysis: template={analysis['template']}, identifier={analysis['identifier']}")
        
        return analysis
    
    async def execute_tool(self, tool_name: str, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute Elasticsearch operations based on MCP tool calls (async).
        
        Args:
            tool_name: Name of the tool to execute
            tool_input: Parameters for the tool
            
        Returns:
            Dict containing tool execution results
        """
        index = tool_input.get('index')
        
        try:
            if tool_name == 'get_index_schema':
                # On-demand schema fetching
                logger.info(f"Fetching schema for index: {index}")
                schemas = await self.es_client.get_index_schemas([index])
                return {
                    'success': True,
                    'index': index,
                    'schema': schemas.get(index, {})
                }
            
            elif tool_name == 'elasticsearch_search':
                # Track Elasticsearch tool usage
                self._tool_types_used.add('ELASTICSEARCH')
                logger.info(f"🔍 ELASTICSEARCH TOOL: Searching index {index}")
                
                result = await self.es_client.search(
                    index=index,
                    query=tool_input.get('query', {"match_all": {}}),
                    size=tool_input.get('size', 10),
                    sort=tool_input.get('sort'),
                    fields=tool_input.get('fields')
                )
                
                # Enhanced logging for Elasticsearch results
                if result.get('success'):
                    hit_count = len(result.get('documents', []))  # Fixed: ES client returns 'documents', not 'hits'
                    total_hits = result.get('total_documents', 0)  # Fixed: ES client returns 'total_documents', not 'total'
                    if hit_count > 0:
                        logger.info(f"✅ ELASTICSEARCH TOOL: Found {hit_count} documents (total: {total_hits}) in {index}")
                        # Log first document preview for debugging
                        first_doc = result.get('documents', [{}])[0]  # Fixed: 'documents' not 'hits'
                        preview_fields = {k: str(v)[:50] + "..." if len(str(v)) > 50 else v 
                                        for k, v in list(first_doc.items())[:3]}
                        logger.info(f"📄 ELASTICSEARCH PREVIEW: {preview_fields}")
                    else:
                        logger.warning(f"⚠️ ELASTICSEARCH TOOL: No documents found in {index}")
                        # INJECT MANDATORY FALLBACK INSTRUCTION
                        result['system_instruction'] = "ELASTICSEARCH FOUND 0 RESULTS. FALLBACK REQUIRED: You MUST now use the 'extract_metadata_from_question' tool to search via RAG. Do not answer 'Not Found' yet."
                else:
                    error_msg = result.get('error', 'Unknown error')
                    logger.error(f"❌ ELASTICSEARCH TOOL: Search failed - {error_msg}")
                
                return result
            
            elif tool_name == 'elasticsearch_aggregate':
                # Track Elasticsearch tool usage
                self._tool_types_used.add('ELASTICSEARCH')
                logger.info(f"📊 ELASTICSEARCH TOOL: Aggregating data in {index}")
                
                result = await self.es_client.aggregate(
                    index=index,
                    aggs=tool_input.get('aggs', {}),
                    query=tool_input.get('query'),
                    size=tool_input.get('size', 0)
                )
                
                # Enhanced logging for aggregation results
                if result.get('success'):
                    agg_keys = list(result.get('aggregations', {}).keys())
                    logger.info(f"✅ ELASTICSEARCH TOOL: Aggregation completed with keys: {agg_keys}")
                else:
                    error_msg = result.get('error', 'Unknown error')
                    logger.error(f"❌ ELASTICSEARCH TOOL: Aggregation failed - {error_msg}")
                
                return result
            
            elif tool_name == 'elasticsearch_count':
                # Track Elasticsearch tool usage
                self._tool_types_used.add('ELASTICSEARCH')
                logger.info(f"🔢 ELASTICSEARCH TOOL: Counting documents in {index}")
                
                result = await self.es_client.count(
                    index=index,
                    query=tool_input.get('query')
                )
                
                # Enhanced logging for count results
                if result.get('success'):
                    count = result.get('count', 0)
                    logger.info(f"✅ ELASTICSEARCH TOOL: Found {count} documents in {index}")
                else:
                    error_msg = result.get('error', 'Unknown error')
                    logger.error(f"❌ ELASTICSEARCH TOOL: Count failed - {error_msg}")
                
                return result
            
            elif tool_name == 'elasticsearch_multi_search':
                # Handle multi-search
                searches = tool_input.get('searches', [])
                results = []
                for search in searches:
                    result = await self.es_client.search(
                        index=search.get('index'),
                        query=search.get('body', {}).get('query', {"match_all": {}}),
                        size=search.get('body', {}).get('size', 10)
                    )
                    results.append(result)
                return {'success': True, 'responses': results}
            
            # RAG Tools
            elif tool_name == 'retrieve_context':
                # Track RAG tool usage
                self._tool_types_used.add('RAG')
                logger.info(f"📋 RAG TOOL: Retrieving context from vector store")
                
                query = tool_input.get('query', '')
                metadata = tool_input.get('metadata', None)
                
                # Validation: Ensure metadata is a dictionary
                if isinstance(metadata, str):
                    logger.warning(f"⚠️ RAG TOOL: Received string metadata '{metadata}', ignoring.")
                    metadata = None
                
                if metadata and not isinstance(metadata, dict):
                    logger.warning(f"⚠️ RAG TOOL: Invalid metadata type {type(metadata)}, ignoring.")
                    metadata = None
                
                if not self.vector_store:
                    logger.error(f"❌ RAG TOOL: Vector store not configured")
                    return {
                        'success': False,
                        'error': 'Vector store not configured. Please set POSTGRES_CONNECTION in environment.'
                    }
                
                result = await self.vector_store.retrieve_context(query, metadata)
                
                # Enhanced logging for RAG results
                if result.get('success'):
                    doc_count = result.get('document_count', 0)
                    if doc_count > 0:
                        logger.info(f"✅ RAG TOOL: Found {doc_count} documents in vector store")
                        # Log first few words of content for debugging
                        content = result.get('serialized_content', '')
                        preview = content[:100] + "..." if len(content) > 100 else content
                        logger.info(f"📄 RAG CONTENT PREVIEW: {preview}")
                    else:
                        logger.warning(f"⚠️ RAG TOOL: No documents found in vector store")
                else:
                    error_msg = result.get('error', 'Unknown error')
                    logger.error(f"❌ RAG TOOL: Failed to retrieve context - {error_msg}")
                
                return result
            
            else:
                return {'success': False, 'error': f'Unknown tool: {tool_name}'}
        
        except OpenSearchError as e:
            logger.error(f"Tool execution error: {e}")
            return {'success': False, 'error': str(e), 'tool': tool_name}
        except Exception as e:
            logger.error(f"Unexpected tool error: {e}")
            return {'success': False, 'error': str(e), 'tool': tool_name}
    
    async def query_with_claude(
        self,
        question: str,
        indices: List[str],
        schemas: Optional[Dict[str, Dict]] = None,
        conversation_history: Optional[List[Dict]] = None
    ) -> Tuple[str, List[str], Optional[str]]:
        """
        Query data using Claude with MCP tools (async).
        
        Schemas are now optional - Claude will fetch them on-demand
        using the get_index_schema tool when needed.
        
        Args:
            question: User's question
            indices: Available indices
            schemas: Optional pre-fetched schemas (for backward compatibility)
            conversation_history: Previous conversation
            
        Returns:
            Tuple of (response, used_indices, base64_image)
        """
        # Reset index tracking
        self.es_client.reset_used_indices()
        
        # Reset tool type tracking
        self._tool_types_used.clear()
        
        # Analyze query
        query_analysis = self.analyze_user_query(question, conversation_history)
        
        # Build system prompt
        system_prompt = self._build_system_prompt(indices, schemas, query_analysis)
        
        # Build messages
        messages = []
        
        if conversation_history:
            logger.debug(f"Including {len(conversation_history)} previous exchanges")
            for conv in conversation_history:
                messages.append({"role": "user", "content": conv.get("question", "")})
                messages.append({"role": "assistant", "content": conv.get("answer", "")})
        
        messages.append({"role": "user", "content": question})
        
        # Build tools
        tools = self._build_mcp_tools(indices)
        
        # Conversation loop
        max_iterations = 10
        
        for iteration in range(max_iterations):
            logger.debug(f"Iteration {iteration + 1}")
            
            try:
                response = await self.claude_client.invoke(
                    system_prompt=system_prompt,
                    messages=messages,
                    tools=tools,
                    temperature=0
                )
                
                content = response.get('content', [])
                
                if not self.claude_client.has_tool_calls(response):
                    # Final answer
                    final_answer = self.claude_client.extract_text_response(response)
                    
                    if not final_answer:
                        return "I couldn't generate a response.", self.es_client.get_used_indices(), None
                    
                    # Log data sources used
                    self._log_data_sources_used()
                    
                    # Generate chart
                    base64_image = await self._generate_chart(question, final_answer)
                    
                    return final_answer, self.es_client.get_used_indices(), base64_image
                
                # Execute tool calls
                tool_calls = self.claude_client.extract_tool_calls(response)
                logger.debug(f"Executing {len(tool_calls)} tool(s)")
                
                tool_results = []
                for tool_call in tool_calls:
                    tool_name = tool_call.get('name')
                    tool_input = tool_call.get('input', {})
                    tool_id = tool_call.get('id')
                    
                    result = await self.execute_tool(tool_name, tool_input)
                    
                    try:
                        result_json = json.dumps(result, default=str)
                    except Exception:
                        result_json = json.dumps({"error": "Failed to serialize result"})
                    
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_id,
                        "content": result_json
                    })
                
                # Continue conversation
                messages.append({"role": "assistant", "content": content})
                messages.append({"role": "user", "content": tool_results})
                
            except ClaudeError as e:
                logger.error(f"Claude error: {e}")
                return f"Error: {str(e)}", self.es_client.get_used_indices(), None
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                return f"Error: {str(e)}", self.es_client.get_used_indices(), None
        
        return (
            "Maximum iterations reached. Please simplify your question.",
            self.es_client.get_used_indices(),
            None
        )
    
    def _log_data_sources_used(self):
        """Log which data sources were used in the query."""
        if not self._tool_types_used:
            logger.info("📋 DATA SOURCES: No tools were used (direct response)")
            return
        
        sources_used = list(self._tool_types_used)
        if len(sources_used) == 1:
            logger.info(f"📋 DATA SOURCES: Used {sources_used[0]} only ✅")
        else:
            logger.warning(f"⚠️ DATA SOURCES: Mixed sources used - {', '.join(sources_used)} (should use only one!)")
    
    async def _generate_chart(self, question: str, answer: str) -> Optional[str]:
        """Generate chart visualization from Q&A (async)."""
        if not MATPLOTLIB_AVAILABLE:
            return None
        
        try:
            # Generate chart code
            prompt = f"""Generate matplotlib Python code to visualize data from this Q&A.

Q: {question}
A: {answer}

Requirements:
- Extract numbers/categories from the answer
- Create appropriate chart (bar/line/pie/scatter)
- Save to 'img_buffer' using: plt.savefig(img_buffer, format='png', bbox_inches='tight', dpi=100)
- Use plt.close() after saving
- If no visualizable data, return: "# No chart needed"

Return ONLY executable Python code (no markdown, no explanations)."""

            response = await self.claude_client.invoke(
                system_prompt="You are a Python chart generation expert.",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2
            )
            
            code_text = self.claude_client.extract_text_response(response)
            
            # Extract code from markdown blocks
            if '```python' in code_text:
                code_text = code_text.split('```python')[1].split('```')[0].strip()
            elif '```' in code_text:
                code_text = code_text.split('```')[1].split('```')[0].strip()
            
            if "No chart needed" in code_text or not code_text:
                return None
            
            # Execute chart code
            try:
                import numpy as np
            except ImportError:
                np = None
            
            img_buffer = io.BytesIO()
            exec_globals = {
                '__builtins__': __builtins__,
                'plt': plt,
                'matplotlib': matplotlib,
                'np': np,
                'img_buffer': img_buffer
            }
            
            exec(code_text, exec_globals)
            
            img_bytes = img_buffer.getvalue()
            img_buffer.close()
            
            if img_bytes:
                return base64.b64encode(img_bytes).decode('utf-8')
            
            return None
            
        except Exception as e:
            logger.warning(f"Chart generation failed: {e}")
            return None
    
    def _build_system_prompt(
        self,
        indices: List[str],
        schemas: Optional[Dict[str, Dict]] = None,
        query_analysis: Optional[Dict[str, Any]] = None
    ) -> str:
        """Build system prompt with schema and analysis context."""
        
        # Build template options
        template_options_text = get_template_options_text()
        
        # Build template definitions
        template_definitions = ""
        for key, template in patient_note_templates.items():
            template_definitions += f"\n---\n### Template: {template['name']} (key: {key})\n"
            template_definitions += f"**Description:** {template['description']}\n"
            if 'format_instructions' in template:
                template_definitions += f"\n**Format Instructions:**\n{template['format_instructions']}\n"
        
        # Build schema text - handle None schemas (on-demand mode)
        if schemas:
            schema_text = "**Available Elasticsearch Indices (schemas pre-loaded):**\n\n"
            for index in indices:
                schema = schemas.get(index, {})
                
                if 'error' in schema:
                    schema_text += f"- **{index}**: Error loading schema - {schema['error']}\n"
                    continue
                
                schema_text += f"- **{index}**\n"
                schema_text += f"  - Documents: {schema.get('document_count', 0):,}\n"
                schema_text += f"  - Fields ({schema.get('field_count', 0)}): {', '.join(schema.get('sample_fields', [])[:15])}\n"
                
                fields = schema.get('fields', {})
                if fields:
                    important_fields = {k: v for k, v in list(fields.items())[:10]}
                    schema_text += f"  - Field types: {json.dumps(important_fields, indent=4)}\n"
                
                schema_text += "\n"
        else:
            # On-demand mode - Claude must fetch schemas when needed
            schema_text = f"""**Available Elasticsearch Indices:** {', '.join(indices)}

**IMPORTANT - ON-DEMAND SCHEMA MODE:**
- Schemas are NOT pre-loaded to save time on general queries
- If you need to query data from Elasticsearch, use the `get_index_schema` tool FIRST to get field information
- For general questions (templates, help, capabilities), answer directly WITHOUT fetching schemas
- Only fetch schema when you actually need to query ES data
"""
        
        # Build dataset prompts
        dataset_prompts_text = ""
        for dataset in indices:
            if dataset in prompts:
                dataset_prompts_text += f"\n{'-'*70}\n"
                dataset_prompts_text += prompts[dataset]
        
        # Build selection guidance
        selection_guidance = ""
        if len(indices) > 1:
            selection_guidance = f"""
You are a deterministic index-routing model.
Select the most appropriate index from: {', '.join(indices)}
"""
        elif len(indices) == 1:
            selection_guidance = f"Use index: {indices[0]}"
        
        # Build analysis context
        analysis_context = ""
        if query_analysis and query_analysis.get('execution_path'):
            analysis_context = self._build_analysis_context(query_analysis, indices)
        
        # Smart data source routing with explicit user intent detection
        smart_routing_text = """
** CLINICAL QA AGENT & DETERMINISTIC DATA SOURCE ROUTING **

** ROUTING LOGIC **

**1. CHECK FOR EXPLICIT RAG TRIGGERS**
   - Triggers: "rag", "embeddings", "vector search".
   - IF FOUND: Use `retrieve_context` tool immediately.

**2. CHECK FOR EXPLICIT ANALYTICS TRIGGERS**
   - Triggers: "how many", "count", "total", "average", "statistics", "trends".
   - IF FOUND: Use `elasticsearch_aggregate` or `elasticsearch_count`.

**3. DEFAULT: ALL OTHER QUESTIONS (Medications, Summaries, Patient Details, etc.)**
   - **STEP A: Try Elasticsearch (`elasticsearch_search`)**
     - You MUST start here for all standard questions.
     - Search relevant indices for structured data.
   
   - **STEP B: Evaluate Elasticsearch Results**
     - Did it return 0 documents?
     - Did it return an error?
     - Is the result "less" than expected or "not proper" (missing details)?
   
   - **STEP C: Fallback to RAG (`retrieve_context`)**
     - YOU MUST USE RAG IF:
       - Elasticsearch returned 0 results or an error.
       - Elasticsearch content was insufficient to fully answer the question.
     - When fallback is needed, use `retrieve_context` adhering to the rules below.

** RAG-SPECIFIC INSTRUCTIONS (Active ONLY when using retrieve_context) **
   *These rules apply to the retrieve_context tool usage, whether triggered explicitly (Step 1) or via fallback (Step 3).*

Your task is to answer the user question using retrieved clinical context.

** Identifier rules (STRICT): **
- The ONLY fields allowed as metadata filters are:
  - serviceDate (MM-DD-YYYY only)
  - patientMRN
  - noteId
  - fin
  - csn
- Use a metadata filter ONLY if the identifier is explicitly stated in the user question
  AND the value exactly matches the stored format.
- Do NOT infer, normalize, or reformat identifiers.
- Do NOT use patient names as metadata filters.
- If no allowed identifier is explicitly present, do NOT apply any metadata filter.

** RAG Process: **
1. Read the user question.
2. Decide whether any allowed identifier is explicitly present and exact.
3. Build a metadata filter using ONLY those identifiers (or leave it empty).
4. Call the `retrieve_context` tool with the original user question and the metadata filter (or null if empty).
5. Answer ONLY using the retrieved context.

** Clinical Rules: **
- Never guess or invent metadata.
- Never answer from prior knowledge.
- If the information is not found in retrieved context, say so.
- If the question contains only a patient name, still call the retrieval tool using semantic search with metadata = null.
- Do not use markdown, headings (##), bold (**), or any special formatting in the final answer.
- Do not add, infer, summarize, or restate any information that is not explicitly present in the retrieved context.

"""
        
        system_prompt = f"""You are an expert healthcare data analyst with access to healthcare data via Elasticsearch and RAG tools.

{smart_routing_text}

{schema_text}

{analysis_context}

**CRITICAL: Query Optimization Rules:**
- Get index mappings before querying to understand field types
- Use specific queries when searching by ID
- Avoid multi-index searches when unnecessary
- Use size=1 when retrieving by unique ID
- ALWAYS use .keyword sub-field for aggregations and sorting on text fields (e.g., use 'patientID.keyword' instead of 'patientID')

{selection_guidance}

{dataset_prompts_text}

**Template Definitions:**
{template_definitions}
"""
        
        return system_prompt
    
    def _build_analysis_context(
        self,
        query_analysis: Dict[str, Any],
        indices: List[str]
    ) -> str:
        """Build query analysis context for system prompt."""
        
        template_name = "note"
        if query_analysis.get('template') in patient_note_templates:
            template_name = patient_note_templates[query_analysis['template']]['name']
        
        context = f"""
{'='*70}
QUERY ANALYSIS RESULTS (CRITICAL - READ THIS FIRST)
{'='*70}
Pre-Parsed Detection from User Query:

Template: {query_analysis.get('template') or 'NOT SPECIFIED'}
Identifier Type: {query_analysis.get('identifier_type') or 'NOT SPECIFIED'}
Identifier Value: {query_analysis.get('identifier') or 'NOT SPECIFIED'}

"""
        
        # Build smart routing context based on user intent
        context += f"""
ROUTING ANALYSIS:
- Identifier: {query_analysis.get('identifier_type')} = "{query_analysis.get('identifier')}"
- Template: {template_name if query_analysis.get('template') else 'Natural format'}

ROUTING STRATEGY:
1.  Check if user explicitly requested RAG/raw data
2.  Check if user asked for analytics/counts  
3.  Default to Elasticsearch-first for general queries

EXECUTION RULES:
- If RAG requested: Use RAG tools only.
- If analytics requested: Use Elasticsearch tools only.
- If general query:
  1. Start with Elasticsearch - try ALL available indices:
     a. First try tiamd_prod_processed_notes (structured/processed data)
     b. If no results or wrong patient, try tiamd_prod_clinical_notes (raw clinical data)
     c. You MUST try BOTH indices before moving to the next step
  2. Only after trying BOTH Elasticsearch indices with 0 results OR wrong patient:
     **YOU MUST EXECUTE THE RAG TOOL (`extract_metadata_from_question`).**
  3. Do not say "Not Found" until you have tried: BOTH ES indices AND RAG.
  4. Final Answer: You may CONSOLIDATE information from both sources IF AND ONLY IF they refer to the SAME patient/ID.
- Never mention data source types to user
"""
        
        return context
    
    def _build_mcp_tools(self, indices: List[str]) -> List[Dict]:
        """Build MCP tool definitions."""
        
        return [
            {
                "name": "get_index_schema",
                "description": "Get the schema (field mappings and document count) for an Elasticsearch index. Use this BEFORE querying to understand field names and types. For general questions that don't need ES data, skip this tool entirely.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "index": {
                            "type": "string", 
                            "enum": indices,
                            "description": "The index to get schema for"
                        }
                    },
                    "required": ["index"]
                }
            },
            {
                "name": "elasticsearch_search",
                "description": " ELASTICSEARCH TOOL: Search structured data in Elasticsearch indices. Use for general patient queries, demographics, processed notes, and when RAG tools are not explicitly requested. DO NOT use when user specifically asks for 'raw data' or 'original notes'.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "index": {"type": "string", "enum": indices},
                        "query": {"type": "object"},
                        "size": {"type": "integer", "default": 10},
                        "sort": {"type": "array"},
                        "fields": {"type": "array"}
                    },
                    "required": ["index", "query"]
                }
            },
            {
                "name": "elasticsearch_aggregate",
                "description": " ELASTICSEARCH TOOL: Perform analytics and aggregations (counts, averages, statistics). Use ONLY for analytics queries like 'how many', 'count', 'total', 'average', 'statistics'. DO NOT use for individual patient data retrieval.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "index": {"type": "string", "enum": indices},
                        "aggs": {"type": "object"},
                        "query": {"type": "object"},
                        "size": {"type": "integer", "default": 0}
                    },
                    "required": ["index", "aggs"]
                }
            },
            {
                "name": "elasticsearch_count",
                "description": " ELASTICSEARCH TOOL: Count documents for analytics. Use ONLY for counting queries like 'how many patients', 'total notes', etc. DO NOT use for individual patient data retrieval.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "index": {"type": "string", "enum": indices},
                        "query": {"type": "object"}
                    },
                    "required": ["index"]
                }
            },
            {
                "name": "elasticsearch_multi_search",
                "description": "Execute multiple searches across indices.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "searches": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "index": {"type": "string", "enum": indices},
                                    "body": {"type": "object"}
                                },
                                "required": ["index", "body"]
                            }
                        }
                    },
                    "required": ["searches"]
                }
            },
            # Unified RAG Tool
            {
                "name": "retrieve_context",
                "description": "Retrieve raw patient records and notes from the vector store. This is a clinical QA tool. Use it to answer questions about a patient's medical history, status, or specific notes. Use semantic search on the query and apply metadata filters ONLY for exact matches of serviceDate, patientMRN, noteId, fin, or csn found in the question.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "the original user question to search for in vector space"
                        },
                        "metadata": {
                            "type": "object",
                            "nullable": True,
                            "description": "Optional strict metadata filters: { 'serviceDate': 'MM-DD-YYYY', 'patientMRN': '...', 'noteId': '...', 'fin': '...', 'csn': '...' }. DO NOT pass the string 'None' or 'null' - use actual null value or omit the key."
                        }
                    },
                    "required": ["query"]
                }
            }
        ]


# Factory function
def get_mcp_server(vector_store: Optional[VectorStoreClient] = None) -> MCPServer:
    """
    Get MCP server instance with vector store for RAG.
    
    Args:
        vector_store: Optional vector store client. Will be auto-initialized
                      if POSTGRES_CONNECTION is configured.
    """
    # Initialize vector store (required for RAG)
    if vector_store is None:
        embeddings_client = get_embeddings_client()
        if embeddings_client:
            embeddings = embeddings_client.get_langchain_embeddings()
            vector_store = get_vector_store_client(embeddings=embeddings)
            if vector_store:
                logger.info("✅ MCP Server initialized with vector store for RAG")
            else:
                logger.error("❌ Failed to initialize vector store - check POSTGRES_CONNECTION")
        else:
            logger.error("❌ Failed to initialize embeddings client - check AWS credentials")
    
    return MCPServer(vector_store=vector_store)
