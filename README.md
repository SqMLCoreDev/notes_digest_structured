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

## Recent Improvements

### 🧠 Intelligent Data Source Routing

The chatbot now features **deterministic data source routing** that automatically chooses between RAG (vector search) and Elasticsearch based on user intent:

**🔍 RAG-Only Mode** - Triggered by keywords:
- `"raw data"`, `"original notes"`, `"unprocessed"`, `"embeddings"`
- **Action**: Uses ONLY RAG tools (`extract_metadata_from_question` → `retrieve_context`)
- **Benefit**: Direct access to clinical content via vector similarity search

**📊 Elasticsearch-Only Mode** - Triggered by keywords:
- `"how many"`, `"count"`, `"total"`, `"statistics"`, `"analytics"`
- **Action**: Uses ONLY Elasticsearch tools for aggregations and counts
- **Benefit**: Fast structured data analytics

**🎯 Auto-Routing Mode** - For general queries:
- **Strategy**: Try Elasticsearch first (faster), RAG as fallback if needed
- **Benefit**: Optimal performance with comprehensive coverage

**Key Benefits**:
- ✅ No more mixed data sources in single responses
- ✅ Respects explicit user data source preferences
- ✅ Automatic routing for optimal performance
- ✅ Enhanced logging shows which tools retrieved data

### 🏗️ Three-Tier Caching System

Robust caching architecture with automatic failover ensures the chatbot always works:

```
Tier 1: Redis (Fast, Shared) → Tier 2: PostgreSQL (Persistent) → Tier 3: In-Memory (Fallback)
```

**Tier 1 - Redis Cache**:
- ⚡ Microsecond-fast access
- 🔄 Shared across multiple app instances
- 💾 Persistent across app restarts
- ⏰ Automatic TTL expiration

**Tier 2 - PostgreSQL Cache**:
- 🗄️ Read existing conversations from database
- 📖 UI team handles all writes (read-only for chatbot)
- 📝 Automatic conversation summarization when >30 messages
- 🔍 Historical conversation retrieval

**Tier 3 - In-Memory Cache**:
- 🛡️ Always available (no external dependencies)
- 🚀 Local fallback when Redis/PostgreSQL fail
- 📊 Built-in performance monitoring
- 💪 Ensures zero downtime

**Key Benefits**:
- ✅ **Zero Downtime**: Chatbot works even when Redis/PostgreSQL fail
- ✅ **Automatic Failover**: Seamless tier switching
- ✅ **Performance Monitoring**: Hit rates and tier usage statistics
- ✅ **Graceful Degradation**: Optimal performance regardless of service availability

### 🔧 Enhanced Conversation Management

**Optional Conversation ID**:
- `chatsession_id` is **optional** when `historyenabled: false` (new conversations)
- `chatsession_id` is **required** when `historyenabled: true` (loading history)
- Maps to PostgreSQL `conversation_id` for persistence

**Conversation History**:
- Automatic summarization for conversations >30 messages
- In-memory summarization (no database writes)
- Smart context management without interfering with UI team operations

## Services Overview

### Chatbot Service (`/chatbot/*`)

**Purpose**: Natural language querying of clinical/business data with conversation history

**Key Features**:
- **Intelligent Data Source Routing**: Deterministic routing between RAG and Elasticsearch based on user intent
- **Three-Tier Caching System**: Redis → PostgreSQL → In-Memory with automatic failover
- Model Context Protocol (MCP) implementation for Claude AI
- On-demand schema fetching (Claude requests schemas only when needed)
- Smart query routing with PATH A/B/C/D logic for raw/processed data
- RAG support with PGVector embeddings and vector similarity search
- User access control via Elasticsearch mapping
- Conversation history with automatic summarization
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

# Redis Cache (Three-Tier System)
REDIS_URL=redis://redis:6379/0
CACHE_TTL_SECONDS=3600
MAX_RESPONSES_PER_SESSION=30

# PostgreSQL (Conversation History & Vector Store)
POSTGRES_CONNECTION=postgresql+psycopg://user:pass@host:5432/db
COLLECTION_NAME=medical_notes_embeddings

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

### Chatbot Query Examples

```bash
# RAG-only query (raw data)
curl -X POST "http://localhost:8000/chatbot/query" \
  -H "Content-Type: application/json" \
  -d '{
    "department": "TiaMD",
    "user": "doctor123",
    "chatquery": "give demographics for jennifer grant from raw data",
    "historyenabled": false
  }'

# Analytics query (Elasticsearch-only)
curl -X POST "http://localhost:8000/chatbot/query" \
  -H "Content-Type: application/json" \
  -d '{
    "department": "TiaMD", 
    "user": "doctor123",
    "chatquery": "how many patients were seen last month?",
    "historyenabled": false
  }'

# General query with conversation history
curl -X POST "http://localhost:8000/chatbot/query" \
  -H "Content-Type: application/json" \
  -d '{
    "department": "TiaMD",
    "user": "doctor123", 
    "chatquery": "tell me more about that patient",
    "historyenabled": true,
    "chatsession_id": "session-456"
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
1. **Request Validation**: User submits query with optional conversation ID
2. **Access Control**: System validates user access against Elasticsearch mapping  
3. **Data Source Routing**: Intelligent routing based on user intent:
   - RAG-only for "raw data" requests
   - Elasticsearch-only for analytics queries
   - Auto-routing for general queries
4. **Cache Lookup**: Three-tier cache check (Redis → PostgreSQL → In-Memory)
5. **MCP Processing**: Claude AI uses appropriate tools based on routing decision
6. **Response Generation**: Natural language response with optional visualizations
7. **Cache Update**: Response saved to all available cache tiers
8. **Logging**: Comprehensive logging shows which data sources were used

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

- **Health Endpoints**: `/health` for each service with detailed component status
- **Cache Monitoring**: Three-tier cache hit rates and performance statistics
- **Data Source Tracking**: Logs show which tools (RAG vs Elasticsearch) retrieved data
- **Metrics**: Token usage tracking, processing times, error rates
- **Logging**: Structured JSON logging with correlation IDs and data source indicators
- **Status Tracking**: Real-time job status for concurrent processing

## Security Features

- Environment-based configuration (no hardcoded secrets)
- User access control via Elasticsearch mapping
- Rate limiting for external API calls
- Input validation with Pydantic models
- CORS configuration for web clients
- AWS IAM integration for Bedrock access

## Performance Optimizations

- **Intelligent Data Routing**: Prevents mixing data sources for optimal performance
- **Three-Tier Caching**: Redis → PostgreSQL → In-Memory with automatic failover
- **Async Architecture**: Non-blocking I/O for concurrent request handling
- **Conversation Summarization**: Automatic context management for long conversations
- **Concurrent Job Processing**: Configurable workers for notes processing
- **Rate Limiting**: Prevents API throttling with smart backoff
- **Connection Pooling**: Optimized database and Redis connections
- **Lazy Loading**: On-demand schema fetching and model initialization

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