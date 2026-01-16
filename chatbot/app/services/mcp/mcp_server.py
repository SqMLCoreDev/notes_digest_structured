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
        Analyze user query to detect data type, template, and identifier.
        Deterministic parsing using regex and keyword matching.
        
        Args:
            question: User's query string
            conversation_history: Previous conversation exchanges
            
        Returns:
            Dict with detected specifications
        """
        analysis = {
            'data_type': None,
            'template': None,
            'identifier': None,
            'identifier_type': None,
            'execution_path': None
        }
        
        query_lower = question.lower()
        
        # Detect Data Type
        raw_keywords = ['raw', 'raw data', 'original', 'unprocessed', 
                        'tiamd_prod_clinical_notes', 'tiamd_clinical_notes']
        processed_keywords = ['processed', 'structured', 'parsed', 'formatted',
                              'tiamd_prod_processed_notes', 'tiamd_processed_notes']
        
        if any(kw in query_lower for kw in raw_keywords):
            analysis['data_type'] = 'raw'
        elif any(kw in query_lower for kw in processed_keywords):
            analysis['data_type'] = 'processed'
        elif 'same' in query_lower and conversation_history:
            for conv in reversed(conversation_history):
                answer = conv.get('answer', '').lower()
                if any(kw in answer for kw in raw_keywords):
                    analysis['data_type'] = 'raw'
                    break
                elif any(kw in answer for kw in processed_keywords):
                    analysis['data_type'] = 'processed'
                    break
        
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
        
        # Determine Execution Path
        if analysis['data_type'] and analysis['template']:
            analysis['execution_path'] = 'A'
        elif analysis['data_type'] and not analysis['template']:
            analysis['execution_path'] = 'B'
        elif not analysis['data_type'] and analysis['template']:
            analysis['execution_path'] = 'C'
        else:
            analysis['execution_path'] = 'D'
        
        logger.debug(f"Query analysis: path={analysis['execution_path']}, "
                     f"data_type={analysis['data_type']}, template={analysis['template']}")
        
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
                return await self.es_client.search(
                    index=index,
                    query=tool_input.get('query', {"match_all": {}}),
                    size=tool_input.get('size', 10),
                    sort=tool_input.get('sort'),
                    fields=tool_input.get('fields')
                )
            
            elif tool_name == 'elasticsearch_aggregate':
                return await self.es_client.aggregate(
                    index=index,
                    aggs=tool_input.get('aggs', {}),
                    query=tool_input.get('query'),
                    size=tool_input.get('size', 0)
                )
            
            elif tool_name == 'elasticsearch_count':
                return await self.es_client.count(
                    index=index,
                    query=tool_input.get('query')
                )
            
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
            elif tool_name == 'extract_metadata_from_question':
                # Track RAG tool usage
                self._tool_types_used.add('RAG')
                logger.info(f"🔍 RAG TOOL: Extracting metadata from question")
                
                question = tool_input.get('question', '')
                metadata = VectorStoreClient.extract_metadata_from_question(question)
                
                return {
                    'success': True,
                    'metadata': metadata
                }
            
            elif tool_name == 'retrieve_context':
                # Track RAG tool usage
                self._tool_types_used.add('RAG')
                logger.info(f"📋 RAG TOOL: Retrieving context from vector store")
                
                query = tool_input.get('query', '')
                metadata = tool_input.get('metadata', None)
                
                if not self.vector_store:
                    return {
                        'success': False,
                        'error': 'Vector store not configured. Please set POSTGRES_CONNECTION in environment.'
                    }
                
                return await self.vector_store.retrieve_context(query, metadata)
            
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
        
        # RAG routing guidance - always included since PGVector is installed
        rag_routing_text = """
**🚨 CRITICAL: TOOL ROUTING DECISION 🚨**

You have access to TWO types of tools. Choose ONE type per question:

🔍 **RAG TOOLS** (for raw patient data - USE THESE FOR PATIENT QUERIES):
- Use for: "get notes", "show records", "find data", "raw data", MRN numbers, patient names, noteId
- Tools: `extract_metadata_from_question` → `retrieve_context`
- Example: "Get notes for MRN 123456" → Use RAG tools
- Example: "Show raw data for patient John Doe" → Use RAG tools

📊 **ELASTICSEARCH TOOLS** (for analytics ONLY):
- Use for: "how many", "count", "total", "average", "statistics", "trends"
- Tools: `elasticsearch_search`, `elasticsearch_aggregate`, `elasticsearch_count`
- Example: "How many patients?" → Use Elasticsearch tools

**NEVER MIX TOOL TYPES** - Choose ONE system per question.
**FOR RAW PATIENT DATA: ALWAYS USE RAG TOOLS, NOT ELASTICSEARCH**
"""
        
        system_prompt = f"""You are an expert healthcare data analyst with access to healthcare data via Elasticsearch.

{rag_routing_text}

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
        
        # Determine index based on data type
        index_to_use = None
        if query_analysis.get('data_type') == 'raw':
            for idx in ['tiamd_prod_clinical_notes', 'tiamd_clinical_notes']:
                if idx in indices:
                    index_to_use = idx
                    break
        elif query_analysis.get('data_type') == 'processed':
            for idx in ['tiamd_prod_processed_notes', 'tiamd_processed_notes']:
                if idx in indices:
                    index_to_use = idx
                    break
        
        template_name = "note"
        if query_analysis.get('template') in patient_note_templates:
            template_name = patient_note_templates[query_analysis['template']]['name']
        
        context = f"""
{'='*70}
QUERY ANALYSIS RESULTS (CRITICAL - READ THIS FIRST)
{'='*70}
Pre-Parsed Detection from User Query:

Execution Path: PATH {query_analysis['execution_path']}
Data Type: {query_analysis.get('data_type') or 'NOT SPECIFIED'}
Template: {query_analysis.get('template') or 'NOT SPECIFIED'}
Identifier Type: {query_analysis.get('identifier_type') or 'NOT SPECIFIED'}
Identifier Value: {query_analysis.get('identifier') or 'NOT SPECIFIED'}

"""
        
        if query_analysis['execution_path'] == 'A':
            context += f"""
PATH A DETECTED: Both data type AND template specified
YOUR IMMEDIATE ACTIONS (NO QUESTIONS ALLOWED):

1. Query Index: {index_to_use}
2. Search For: {query_analysis.get('identifier_type')} = "{query_analysis.get('identifier')}"
3. Format With: {query_analysis.get('template')} ({template_name})
4. Present Result: Formatted clinical note

CRITICAL - DO NOT ASK:
- "Which data source would you like?" (User already specified: {query_analysis.get('data_type')})
- "Which template format would you like?" (User already specified: {template_name})

EXAMPLE RESPONSE START:
"Here is the {query_analysis.get('data_type')} clinical note for {query_analysis.get('identifier')} formatted as a {template_name}:"
[Then provide the formatted note following the template structure]
"""
        elif query_analysis['execution_path'] == 'B':
            context += f"""
PATH B DETECTED: Only data type specified (no template)
YOUR ACTIONS IN ORDER:

1. Query Index: {index_to_use} (DO NOT ASK - data type already specified)
2. Search For: {query_analysis.get('identifier_type')} = "{query_analysis.get('identifier')}"
3. AFTER retrieving data, ask: "Which template format would you like?"
4. Wait for user's template selection
5. Format and present the note

CRITICAL - DO NOT ASK:
- "Which data source would you like?" (User already specified: {query_analysis.get('data_type')})

DO ASK (after querying):
- "I found the note data. Which template format would you like me to use?"
"""
        elif query_analysis['execution_path'] == 'C':
            context += f"""
PATH C DETECTED: Only template specified (no data type)
YOUR ACTIONS IN ORDER:

1. Ask user: "Which data source would you like: (1) Raw Data or (2) Processed Data?"
2. Wait for user's data type selection
3. Query the selected index
4. Format With: {query_analysis.get('template')} ({template_name}) (DO NOT ASK - already specified)
5. Present formatted note

CRITICAL - DO NOT ASK:
- "Which template format would you like?" (User already specified: {template_name})

DO ASK (before querying):
- "Which data source would you like: (1) Raw Data or (2) Processed Data?"
"""
        elif query_analysis['execution_path'] == 'D':
            context += f"""
PATH D DETECTED: Neither data type nor template specified
YOUR ACTIONS IN ORDER:

1. Ask user: "Which data source would you like: (1) Raw Data or (2) Processed Data?"
2. Wait for user's data type selection
3. Query the selected index
4. Ask user: "Which template format would you like?"
5. Wait for user's template selection
6. Format and present the note

YOU MUST ASK BOTH QUESTIONS (user didn't specify either):
- First ask about data source
- Then ask about template format
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
                "description": "Search Elasticsearch indices for matching documents.",
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
                "description": "Perform aggregations on Elasticsearch data.",
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
                "description": "Count documents in an index.",
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
            # RAG Tools for raw patient data retrieval
            {
                "name": "extract_metadata_from_question",
                "description": "🔍 RAG TOOL: Extract metadata from questions about specific patient data. Use ONLY for raw data questions that mention patient identifiers (MRN, noteId, patient names). This is the FIRST step for retrieving patient records, clinical notes, or medical documentation.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "question": {
                            "type": "string",
                            "description": "The user's question to extract metadata from"
                        }
                    },
                    "required": ["question"]
                }
            },
            {
                "name": "retrieve_context",
                "description": "📋 RAG TOOL: Retrieve actual patient data from vector store. Use ONLY after extract_metadata_from_question for raw data questions. This tool returns the actual clinical content, patient records, and medical documentation.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The query to search for relevant context"
                        },
                        "metadata": {
                            "type": "object",
                            "description": "Optional metadata filters to apply during search (e.g., patient MRN, note ID, date filters)"
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
