"""
Production Cache Service - 3-Tier Architecture
Redis (Fast) + PostgreSQL (Persistent) + In-Memory (Fallback)

Strategy for Multiple Sessions:
1. Redis: Primary cache (fast, shared across instances)
2. PostgreSQL: Persistent storage (existing conversations)
3. In-Memory: Fallback only (when Redis is down)

Performance Tiers:
- Tier 1: Redis (⚡ fastest, shared)
- Tier 2: PostgreSQL (🔄 warm-up, persistent)
- Tier 3: In-Memory (🆘 fallback only)
"""

from typing import Any, Dict, List, Optional, Set
from datetime import datetime
import json

from app.core.config import settings
from app.core.logg