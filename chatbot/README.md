# MCP Chatbot API

A production-grade Model Context Protocol (MCP) API for OpenSearch data querying with Claude AI.

## Features

- **Async Architecture** - Non-blocking concurrent request handling
- **Redis Caching** - Production-ready session management with TTL
- **On-Demand Schemas** - Claude fetches schemas only when needed
- **Smart Query Routing** - Deterministic PATH A/B/C/D logic for raw/processed data

## Architecture

```
app/
├── main.py                 # FastAPI app factory
├── schema.py               # Pydantic models
├── api/v1/endpoints/       # Query & health endpoints
├── core/                   # Config, logging, exceptions
└── services/
    ├── chat_service.py     # Query orchestration
    ├── cache_service.py    # Redis/memory caching
    └── mcp/
        ├── mcp_server.py   # MCP server (async)
        ├── es_client.py    # OpenSearch client (httpx async)
        └── claude_client.py # Bedrock client (async)
```

## Quick Start

### Docker Compose (Recommended)

```bash
# Copy and configure environment
cp .env.example .env
# Edit .env with your credentials

# Start API + Redis together
docker-compose up --build
```

Both services start together:
- API: http://localhost:8000
- Redis: localhost:6379

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Start Redis (required for production mode)
docker run -d -p 6379:6379 redis:7-alpine

# Run with hot-reload
uvicorn app.main:app --reload --port 8000
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/query` | POST | Main MCP query endpoint |
| `/health` | GET | Basic health check |
| `/health/ready` | GET | Readiness with dependencies |
| `/mcp` | GET | Swagger UI documentation |

### Query Example

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{
    "department": "YourDept",
    "user": "your-username",
    "chatquery": "Show me raw notes for patient John Doe in SOAP format",
    "historyenabled": true,
    "chatsession_id": "session-123"
  }'
```

## Configuration

See `.env.example` for all options.

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENSEARCH_URL` | OpenSearch cluster URL | Required |
| `REDIS_URL` | Redis connection URL | `redis://redis:6379/0` |
| `CACHE_TTL_SECONDS` | Session expiry time | 3600 (1 hour) |
| `MODEL` | Claude model name | `CLAUDE_HAIKU_4_5` |
| `AWS_REGION` | AWS region for Bedrock | `us-east-1` |

## AWS Lambda Deployment

```python
# Entry point: main.py
# Handler: main.lambda_handler
```

Supports both API Gateway (via Mangum) and direct Lambda invocations.

## Session & History

- Sessions isolated by `chatsession_id`
- History stored in Redis with TTL
- Set `historyenabled: false` to start new conversation

## License

Proprietary - Internal Use Only
