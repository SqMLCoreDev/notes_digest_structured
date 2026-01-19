# Notes Engine - Unified Medical Data Processing Platform

A production-grade platform combining intelligent chatbot querying and medical notes processing with AI-powered analysis.

## Overview

This workspace contains a **unified Notes Engine** that integrates two powerful microservices:

- **Chatbot Service**: Natural language querying of clinical data using Claude AI via Model Context Protocol (MCP)
- **NotesDigest Service**: Concurrent medical notes processing, extraction, and summarization with embeddings

Both services are orchestrated through a unified FastAPI gateway with combined Swagger documentation and shared infrastructure.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    UNIFIED GATEWAY (main.py)                    │
│                    FastAPI @ :8000/docs                         │
└──────────────────────┬──────────────────────────────────────────┘
                       │
        ┌──────────────┴──────────────┐
        │                             │
        ▼                             ▼
┌──────────────────────┐    ┌──────────────────────┐
│  CHATBOT SERVICE     │    │ NOTESDIGEST SERVICE  │
│  /chatbot/*          │    │ /notesdigest/*       │
│  (Query Interface)   │    │ (Processing Engine)  │
└──────────────────────┘    └──────────────────────┘
        │                             │
        ▼                             ▼
    ┌────────────────────────────────────────────────┐
    │         ELASTICSEARCH CLUSTER                  │
    │  - Clinical Notes (source data)               │
    │  - Processed Notes (structured output)        │
    │  - Notes Digest (summaries)                   │
    │  - User Access Control                        │
    └────────────────────────────────────────────────┘
        │
        ▼
    ┌────────────────────────────────────────────────┐
    │         AWS BEDROCK (Claude AI)                │
    │  - Natural language understanding             │
    │  - Medical note extraction & summarization    │
    │  - MCP tool orchestration                     │
    └────────────────────────────────────────────────┘
```

## Technology Stack

- **Framework**: FastAPI 0.109+, Uvicorn ASGI server
- **Language**: Python 3.11+
- **AI/ML**: AWS Bedrock (Claude models), Amazon Titan Embeddings
- **Data**: Elasticsearch 7.17+, PostgreSQL with PGVector
- **Caching**: Redis 7 with TTL support
- **Async**: asyncio, httpx for non-blocking I/O
- **Deployment**: Docker, Docker Compose, AWS Lambda support
- **Testing**: pytest with async support and property-based testing

## Quick Start

### 1. Environment Setup

```bash
# Copy and configure environment variables
cp .env.example .env
# Edit .env with your AWS credentials and service endpoints
```

### 2. Docker Compose (Recommended)

```bash
# Start entire stack (API + Redis)
docker-compose up --build

# Services available at:
# - API: http://localhost:8000
# - Swagger UI: http://localhost:8000/docs
# - Redis: localhost:6379
```

### 3. Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run unified gateway
uvicorn main:app --reload --port 8000

# Or run services individually:
# Chatbot only: cd chatbot && uvicorn app.main:app --reload
# NotesDigest only: cd notesdigest && uvicorn medical_notes.service.app:app --reload
```

## Services Overview

### Chatbot Service (`/chatbot/*`)

**Purpose**: Natural language querying of clinical/business data with conversation history

**Key Features**:
- Model Context Protocol (MCP) implementation for Claude AI
- On-demand schema fetching (Claude requests schemas only when needed)
- Smart query routing with PATH A/B/C/D logic for raw/processed data
- Redis-based session caching with TTL
- RAG support with PGVector embeddings
- User access control via Elasticsearch mapping
- Async architecture for concurrent requests
- AWS Lambda deployment ready

**Endpoints**:
- `POST /chatbot/v1/chat` - Submit natural language queries
- `GET /chatbot/health` - Service health check
- `GET /chatbot/v1/schemas/{index}` - Fetch index schemas

### NotesDigest Service (`/notesdigest/*`)

**Purpose**: Medical notes processing and digestion with concurrent job management

**Key Features**:
- Concurrent processing of multiple notes with configurable workers
- Historical context integration (N previous visits)
- Structured data extraction (note type, patient MRN, SOAP format)
- Vector embeddings generation via Amazon Titan
- Rate limiting for Bedrock API calls
- Token usage tracking for cost monitoring
- External API integration with tracking
- Comprehensive error handling and job status tracking

**Endpoints**:
- `POST /notesdigest/process` - Process single note
- `POST /notesdigest/process/batch` - Process multiple notes concurrently
- `GET /notesdigest/status/{job_id}` - Check job status
- `GET /notesdigest/health` - Service health check

## Project Structure

```
├── main.py                     # Unified FastAPI gateway
├── docker-compose.yml          # Orchestration for API + Redis
├── Dockerfile                  # Multi-stage production build
├── requirements.txt            # Unified dependencies
├── .env.example               # Environment template
│
├── chatbot/                   # Chatbot Service
│   ├── app/
│   │   ├── main.py           # FastAPI app factory
│   │   ├── schema.py         # Pydantic models
│   │   ├── api/v1/endpoints/ # REST endpoints
│   │   ├── core/             # Config, logging, exceptions
│   │   └── services/         # Business logic
│   │       ├── chat_service.py    # Query orchestration
│   │       ├── cache_service.py   # Redis caching
│   │       ├── mcp/              # MCP protocol implementation
│   │       ├── clients/          # AWS Bedrock, Elasticsearch
│   │       └── rag/              # Embeddings & vector search
│   ├── prompts/              # AI prompt templates
│   ├── tests/                # Test suite
│   └── scripts/              # Utilities
│
└── notesdigest/              # NotesDigest Service
    ├── main.py               # CLI entry point
    └── medical_notes/
        ├── config/           # Configuration management
        ├── service/          # Core processing logic
        │   ├── app.py                    # FastAPI app
        │   ├── medical_notes_processor.py # Note processing
        │   ├── concurrent_job_manager.py  # Job queue management
        │   └── rate_limiter.py           # API rate limiting
        ├── repository/       # Data access layer
        ├── routes/           # API endpoints
        ├── utils/            # Helper utilities
        └── prompts/          # AI prompts for extraction
```

## Configuration

### Key Environment Variables

```bash
# AWS Configuration
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_REGION=us-east-1

# Claude Models
CLAUDE_HAIKU_4_5=us.anthropic.claude-haiku-4-5-20251001-v1:0
CLAUDE_SONNET_3_5=us.anthropic.claude-3-5-sonnet-20241022-v2:0
MODEL=CLAUDE_HAIKU_4_5
MAX_TOKENS=100000

# Elasticsearch
ES_URL=https://your-elasticsearch-cluster:9200
ES_USER=elastic
ES_PASSWORD=your_password
ES_INDEX_CLINICAL_NOTES=tiamd_clinical_notes
ES_INDEX_PROCESSED_NOTES=tiamd_processed_notes

# Redis Cache
REDIS_URL=redis://redis:6379/0
CACHE_TTL_SECONDS=3600

# Processing Configuration
MAX_CONCURRENT_NOTES=10
MAX_QUEUE_SIZE=100
NOTE_PROCESSING_TIMEOUT=1800
BEDROCK_RATE_LIMIT_RPS=30

# Embeddings
POSTGRES_CONNECTION=postgresql+psycopg://user:pass@host:5432/db
EMBEDDINGS_MODEL=amazon.titan-embed-text-v2:0
```

## Usage Examples

### Chatbot Queries

```bash
# Natural language query
curl -X POST "http://localhost:8000/chatbot/v1/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Show me all patients with diabetes from last month",
    "user_id": "doctor123",
    "session_id": "session_456"
  }'
```

### Notes Processing

```bash
# Process single note
curl -X POST "http://localhost:8000/notesdigest/process" \
  -H "Content-Type: application/json" \
  -d '{
    "note_id": "note_12345"
  }'

# Process multiple notes concurrently
curl -X POST "http://localhost:8000/notesdigest/process/batch" \
  -H "Content-Type: application/json" \
  -d '{
    "note_ids": ["note_1", "note_2", "note_3"]
  }'

# Check job status
curl "http://localhost:8000/notesdigest/status/job_789"
```

### CLI Usage (NotesDigest)

```bash
# Process single note
python notesdigest/main.py --note-id 123

# Process multiple notes concurrently
python notesdigest/main.py --note-ids 1 2 3 4 5 --concurrent

# System status
python notesdigest/main.py --action status

# Health check
python notesdigest/main.py --action health
```

## Data Flow

### Chatbot Query Flow
1. User submits natural language query via REST API
2. Chat service validates user access against Elasticsearch mapping
3. MCP Server processes query and communicates with Claude via Bedrock
4. Claude analyzes query and requests tools (schema fetching, data querying)
5. Tools query Elasticsearch for relevant data
6. Claude synthesizes results into natural language response
7. Response cached in Redis for session continuity
8. Final response returned with optional visualizations

### NotesDigest Processing Flow
1. User submits note processing request
2. Concurrent job manager queues the job
3. Worker fetches raw note from Elasticsearch
4. Claude extracts note type and patient MRN
5. System fetches historical context (N previous visits)
6. Claude processes combined current + historical data
7. Structured data extracted (SOAP format, digest, embeddings)
8. Results stored in processed notes and digest indices
9. External API notification with tracking
10. Job status updated and returned to user

## Deployment Options

### Development
```bash
# Local development with hot reload
uvicorn main:app --reload --port 8000
```

### Docker
```bash
# Production-ready containers
docker-compose up --build
```

### AWS Lambda
```bash
# Deploy chatbot as Lambda function
# Handler: chatbot/main.py:lambda_handler
# Runtime: Python 3.11
# Timeout: 900s (15 minutes)
```

## Monitoring & Health Checks

- **Health Endpoints**: `/health` for each service
- **Metrics**: Token usage tracking, processing times, error rates
- **Logging**: Structured JSON logging with correlation IDs
- **Status Tracking**: Real-time job status for concurrent processing

## Security Features

- Environment-based configuration (no hardcoded secrets)
- User access control via Elasticsearch mapping
- Rate limiting for external API calls
- Input validation with Pydantic models
- CORS configuration for web clients
- AWS IAM integration for Bedrock access

## Performance Optimizations

- Async architecture for non-blocking I/O
- Redis caching for session management
- Concurrent job processing with configurable workers
- Rate limiting to prevent API throttling
- Connection pooling for database operations
- Lazy loading of AI models and schemas

## Testing

```bash
# Run test suite
pytest chatbot/tests/ -v
pytest notesdigest/tests/ -v

# Run with coverage
pytest --cov=chatbot/app chatbot/tests/
pytest --cov=notesdigest/medical_notes notesdigest/tests/
```

## Contributing

1. Copy `.env.example` to `.env` and configure your environment
2. Install dependencies: `pip install -r requirements.txt`
3. Run tests: `pytest`
4. Start development server: `uvicorn main:app --reload`
5. Access Swagger UI: http://localhost:8000/docs

## License

This project is proprietary software for medical data processing and analysis.