# Implementation Guide: PostgreSQL + Memory Cache (No Redis)

## Overview

This implementation removes all Redis dependencies and uses a hybrid approach:
- **PostgreSQL**: Read existing conversations from `chatbot_messages` table
- **In-Memory**: Store new conversation responses during current session
- **No Redis**: Completely eliminated Redis dependency

## Files Created/Modified

### New Files:
1. `app/services/postgres_cache_backend_improved.py` - PostgreSQL backend with Q&A pairing
2. `app/services/cache_service_hybrid.py` - Main hybrid cache service
3. `app/services/cache_service_clean.py` - Clean interface without Redis

### Files to Replace:
- Replace `app/services/cache_service.py` with `app/services/cache_service_clean.py`

## Implementation Steps

### Step 1: Install Dependencies
```bash
pip install asyncpg>=0.29.0
```

### Step 2: Replace Cache Service
```bash
# Backup original
mv chatbot/app/services/cache_service.py chatbot/app/services/cache_service_original.py

# Use clean version
cp chatbot/app/services/cache_service_clean.py chatbot/app/services/cache_service.py
```

### Step 3: Update Environment (Optional)
```bash
# Remove Redis configuration from .env
# REDIS_URL=redis://redis:6379/0  # Remove this line

# PostgreSQL connection is already configured
# POSTGRES_CONNECTION=postgresql+psycopg://...
```

### Step 4: Update Docker Compose (Optional)
Remove Redis service from `docker-compose.yml`:
```yaml
# Remove this entire section:
# redis:
#   image: redis:7-alpine
#   container_name: chatbot-redis
#   ports:
#     - "6379:6379"
```

## How It Works

### Conversation History Flow:

1. **User requests with `historyenabled=true` and `chatsession_id="123"`**

2. **get_responses("123") is called:**
   ```python
   # Try PostgreSQL first
   postgres_responses = await postgres_backend.get("123")
   if postgres_responses:
       return postgres_responses  # Existing conversation found
   
   # Fallback to memory
   memory_responses = await memory_cache.get("123")
   return memory_responses  # New conversation or current session
   ```

3. **PostgreSQL Query (if conversation exists):**
   ```sql
   SELECT role, query, response, created_at, id, parent_id
   FROM chatbot_messages
   WHERE conversation_id = '123' 
     AND deleted_at IS NULL
     AND role IN ('user', 'assistant')
   ORDER BY id ASC
   ```

4. **Q&A Pairing Logic:**
   - Processes messages sequentially
   - Pairs user questions with assistant responses
   - Handles orphaned messages gracefully
   - Returns last 30 complete Q&A pairs

5. **New responses saved to memory:**
   ```python
   await memory_cache.add("123", {
       'query': 'User question',
       'response': 'AI response',
       'used_indices': ['index1'],
       'timestamp': '2025-01-19T...'
   })
   ```

### Data Flow Examples:

#### Scenario 1: Existing Conversation
```
Request: chatsession_id="1", historyenabled=true
→ PostgreSQL: Found 5 Q&A pairs from chatbot_messages
→ Return: 5 complete conversation pairs
→ New response: Saved to memory cache
```

#### Scenario 2: New Conversation
```
Request: chatsession_id="999", historyenabled=true  
→ PostgreSQL: No data found for conversation_id="999"
→ Memory: No data found (new session)
→ Return: Empty history (new conversation)
→ New response: Saved to memory cache
```

#### Scenario 3: Continuing Session
```
Request: chatsession_id="999", historyenabled=true (2nd request)
→ PostgreSQL: Still no data
→ Memory: Found 1 Q&A pair from previous request
→ Return: 1 conversation pair
→ New response: Saved to memory cache (now 2 pairs)
```

## Benefits

### ✅ Advantages:
- **No Redis dependency** - Eliminates infrastructure complexity
- **Uses existing data** - Leverages your `chatbot_messages` table
- **Proper Q&A pairing** - Ensures complete conversations
- **Handles edge cases** - Orphaned questions/responses
- **Memory fallback** - New conversations work immediately
- **Same API** - Drop-in replacement for existing code
- **Better ordering** - Chronological conversation flow
- **30 complete pairs** - Not 30 individual messages

### 🔧 Technical Details:
- **Connection pooling** - Efficient PostgreSQL connections (2-10 pool)
- **Async operations** - Non-blocking database queries
- **Error handling** - Graceful fallbacks on database errors
- **Memory management** - Bounded in-memory cache (30 entries max)
- **Statistics** - Combined stats from both backends

## Configuration

### Required Settings:
```python
# In config.py - already exists
POSTGRES_CONNECTION = "postgresql+psycopg://user:pass@host:5432/db"
```

### Optional Settings:
```python
# These can be removed from config.py
# REDIS_URL = ...  # Not needed anymore
# CACHE_TYPE = ...  # Not needed anymore
```

## Testing

### Test Existing Conversations:
```bash
# Test with existing conversation_id from your database
curl -X POST "http://localhost:8000/chatbot/v1/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "department": "TiaMD",
    "user": "TiaMD", 
    "chatquery": "What about recent patients?",
    "historyenabled": true,
    "chatsession_id": "1"
  }'
```

### Test New Conversations:
```bash
# Test with new conversation_id
curl -X POST "http://localhost:8000/chatbot/v1/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "department": "TiaMD",
    "user": "TiaMD",
    "chatquery": "Hello, this is a new conversation",
    "historyenabled": true,
    "chatsession_id": "new_session_123"
  }'
```

### Check Cache Stats:
```bash
curl "http://localhost:8000/chatbot/health/detailed"
# Look for cache statistics in the response
```

## Migration Notes

### From Redis to Hybrid:
1. **No data migration needed** - Existing conversations are in PostgreSQL
2. **Redis data is lost** - But it's replaced by PostgreSQL data
3. **New conversations** - Start fresh in memory cache
4. **Same functionality** - All features work the same way

### Rollback Plan:
1. Keep `cache_service_original.py` as backup
2. Restore original file if needed
3. Restart Redis service if rolling back

This implementation provides a cleaner, simpler architecture while maintaining all the conversation history functionality you need.