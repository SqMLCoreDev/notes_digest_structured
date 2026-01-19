"""
Example: How to use PostgreSQL cache with existing chatbot_messages table

This shows how to switch from Redis to your existing PostgreSQL table
for conversation history without changing any other code.
"""

# STEP 1: Install dependency
# pip install asyncpg>=0.29.0

# STEP 2: In your chat_service.py, change the import:
# FROM:
# from app.services.cache_service import CacheService, get_cache_service

# TO:
# from app.services.cache_service_postgres import CacheService, get_cache_service

# STEP 3: That's it! The rest works exactly the same.

# Example usage in your API:
"""
async def chat_endpoint(request: QueryRequest):
    # This will now use your existing chatbot_messages table
    # conversation_id from request.chatsession_id will be used to query
    # role='assistant' rows for conversation history
    
    chat_service = get_chat_service()
    response = await chat_service.process_query(request)
    return response
"""

# What happens internally:
"""
1. When historyenabled=True and chatsession_id="123":
   - Queries: SELECT query, response, created_at, id 
             FROM chatbot_messages 
             WHERE conversation_id = '123' 
               AND role = 'assistant' 
               AND deleted_at IS NULL 
             ORDER BY id ASC 
             LIMIT 30

2. Returns conversation history in the same format as before:
   [
     {
       'query': 'User question',
       'response': 'Assistant response', 
       'timestamp': '2025-12-11T04:01:13',
       'used_indices': []
     },
     ...
   ]

3. The add() and clear() methods are no-ops since your table
   is populated by another process.
"""

# Benefits:
"""
✅ Uses your existing chatbot_messages table
✅ No schema changes needed
✅ Same API as Redis cache
✅ Filters for role='assistant' automatically
✅ Orders by id for chronological conversation
✅ Limits to 30 most recent conversations
✅ Handles deleted_at IS NULL filtering
✅ No Redis dependency needed
"""