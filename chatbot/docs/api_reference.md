# API Reference

## Endpoints

### Root
**GET /**

Returns API information.

**Response:**
```json
{
  "name": "MCP Chatbot API",
  "version": "1.0.0",
  "docs": "/mcp",
  "health": "/health"
}
```

---

### Health Check
**GET /health**

Returns basic health status.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-01-10T10:00:00Z"
}
```

---

### Detailed Health
**GET /health/detailed**

Returns detailed health of all services.

**Response:**
```json
{
  "status": "healthy",
  "services": {
    "elasticsearch": {"status": "healthy", "latency_ms": 45},
    "redis": {"status": "healthy"},
    "mcp_server": {"status": "ready"}
  }
}
```

---

### Chat Query
**POST /v1/chat**

Send a natural language query.

**Request Body:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| department | string | Yes | User's department |
| user | string | Yes | Username |
| chatquery | string | Yes | The query |
| historyenabled | boolean | No | Enable conversation history |
| chatsession_id | string | Conditional | Required if historyenabled=true |

**Example Request:**
```json
{
  "department": "claims",
  "user": "john.doe",
  "chatquery": "Show me notes for patient MRN 123456",
  "historyenabled": true,
  "chatsession_id": "session-abc-123"
}
```

**Response:**
```json
{
  "user": "john.doe",
  "sessionId": "session-abc-123",
  "query": "Show me notes for patient MRN 123456",
  "chatResponse": "Here are the notes for patient...",
  "chartbase64Image": null,
  "responseTime": "2025-01-10T10:00:00Z"
}
```

---

## Error Responses

All errors follow this format:

```json
{
  "detail": {
    "error": "Error type",
    "message": "Human readable message",
    "code": "ERROR_CODE"
  }
}
```

| Status Code | Description |
|-------------|-------------|
| 400 | Bad Request - Invalid input |
| 401 | Unauthorized - Invalid credentials |
| 403 | Forbidden - Access denied |
| 500 | Internal Server Error |
