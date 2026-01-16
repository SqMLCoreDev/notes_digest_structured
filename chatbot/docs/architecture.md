# Architecture

## System Overview

```
                     ┌─────────────────────────────────────────┐
                     │           Load Balancer / API Gateway   │
                     └────────────────────┬────────────────────┘
                                          │
                     ┌────────────────────▼────────────────────┐
                     │           FastAPI Application           │
                     │              (app/main.py)              │
                     └────────────────────┬────────────────────┘
                                          │
         ┌────────────────┬───────────────┼───────────────┬────────────────┐
         │                │               │               │                │
         ▼                ▼               ▼               ▼                ▼
  ┌─────────────┐  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
  │    Redis    │  │ MCP Server  │ │    Chat     │ │   Health    │ │   Cache     │
  │   (Cache)   │  │ Orchestrator│ │   Service   │ │   Service   │ │   Service   │
  └─────────────┘  └──────┬──────┘ └─────────────┘ └─────────────┘ └─────────────┘
                          │
         ┌────────────────┼────────────────┐
         │                │                │
         ▼                ▼                ▼
  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
  │   Claude    │  │Elasticsearch│  │  PGVector   │
  │  (Bedrock)  │  │ (OpenSearch)│  │ (RAG Store) │
  └─────────────┘  └─────────────┘  └─────────────┘
```

## Components

### app/services/clients/
External service clients:
- **claude_client.py** - AWS Bedrock Claude integration
- **es_client.py** - Elasticsearch/OpenSearch client
- **pgvector_client.py** - PostgreSQL vector store

### app/services/mcp/
Tool orchestration:
- **mcp_server.py** - Main MCP server, Claude tool handling

### app/services/rag/
RAG components:
- **embeddings.py** - Amazon Titan embeddings generation

### prompts/
Prompt management:
- **templates/** - Clinical note format templates
- **datasets/** - Index-specific prompts

## Data Flow

1. User sends query via `/v1/chat`
2. Chat service validates user access
3. MCP Server receives query
4. Claude analyzes query, requests tools
5. Tools query Elasticsearch/PGVector
6. Results returned to Claude
7. Claude generates response
8. Response cached and returned
