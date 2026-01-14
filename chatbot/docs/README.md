# MCP Chatbot API Documentation

## Overview

MCP (Model Context Protocol) Chatbot API is a FastAPI-based backend that enables natural language querying of Elasticsearch data using Claude AI.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your settings

# Run locally
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## API Endpoints

### Health Check
- `GET /health` - Basic health status
- `GET /health/detailed` - Detailed service health

### Chat
- `POST /v1/chat` - Send a chat query

```json
{
  "department": "claims",
  "user": "username",
  "chatquery": "What is the total count of records?",
  "historyenabled": false,
  "chatsession_id": "optional-session-id"
}
```

### Documentation
- `GET /mcp` - OpenAPI/Swagger UI
- `GET /redoc` - ReDoc documentation

## Project Structure

```
├── app/
│   ├── api/              # API endpoints
│   ├── core/             # Config, logging, exceptions
│   ├── services/         # Business logic
│   │   ├── clients/      # External service clients
│   │   ├── mcp/          # MCP server orchestration
│   │   └── rag/          # RAG components
│   └── main.py           # FastAPI app
├── prompts/
│   ├── templates/        # Note format templates
│   └── datasets/         # Index-specific prompts
├── tests/                # Unit tests
├── scripts/              # Utility scripts
└── docs/                 # Documentation
```

## Configuration

See `.env.example` for all configuration options:
- `AWS_REGION` - AWS region for Bedrock
- `OPENSEARCH_HOST` - Elasticsearch/OpenSearch URL
- `REDIS_URL` - Redis URL for caching
- `POSTGRES_CONNECTION` - PGVector connection string

## Additional Documentation

- [API Reference](./api_reference.md)
- [Architecture](./architecture.md)
- [Deployment](./deployment.md)
