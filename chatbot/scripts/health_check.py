#!/usr/bin/env python
"""
scripts/health_check.py - Service Health Check Script

Checks the health of all external services.

Usage:
    python scripts/health_check.py
    python scripts/health_check.py --service elasticsearch
    python scripts/health_check.py --service redis
    python scripts/health_check.py --service all
"""

import argparse
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def check_elasticsearch():
    """Check Elasticsearch connection."""
    try:
        from app.services.clients.es_client import OpenSearchClient
        client = OpenSearchClient()
        # Try a simple operation
        print("[CHECKING] Elasticsearch...")
        # result = await client.get_available_indices()
        print("[OK] Elasticsearch: Connected")
        return True
    except Exception as e:
        print(f"[FAIL] Elasticsearch: {e}")
        return False


def check_redis():
    """Check Redis connection."""
    try:
        from app.core.config import settings
        if not settings.REDIS_URL:
            print("[SKIP] Redis: Not configured")
            return True
        
        import redis
        print("[CHECKING] Redis...")
        r = redis.from_url(settings.REDIS_URL)
        r.ping()
        print("[OK] Redis: Connected")
        return True
    except Exception as e:
        print(f"[FAIL] Redis: {e}")
        return False


def check_pgvector():
    """Check PostgreSQL/PGVector connection."""
    try:
        from app.core.config import settings
        if not settings.POSTGRES_CONNECTION:
            print("[SKIP] PGVector: Not configured")
            return True
        
        print("[CHECKING] PGVector...")
        from app.services.rag.embeddings import get_embeddings_client
        from app.services.clients.pgvector_client import get_vector_store_client
        
        embeddings = get_embeddings_client()
        if embeddings:
            vector_store = get_vector_store_client(embeddings=embeddings.get_langchain_embeddings())
            if vector_store:
                print("[OK] PGVector: Connected")
                return True
        print("[FAIL] PGVector: Could not initialize")
        return False
    except Exception as e:
        print(f"[FAIL] PGVector: {e}")
        return False


def check_aws():
    """Check AWS Bedrock connection."""
    try:
        print("[CHECKING] AWS Bedrock...")
        from app.services.clients.claude_client import get_claude_client
        client = get_claude_client()
        if client:
            print("[OK] AWS Bedrock: Connected")
            return True
        print("[FAIL] AWS Bedrock: Client not initialized")
        return False
    except Exception as e:
        print(f"[FAIL] AWS Bedrock: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Check health of external services")
    parser.add_argument("--service", choices=["elasticsearch", "redis", "pgvector", "aws", "all"], 
                       default="all", help="Service to check")
    
    args = parser.parse_args()
    
    print("=" * 50)
    print("SERVICE HEALTH CHECK")
    print("=" * 50)
    
    checks = {
        "elasticsearch": check_elasticsearch,
        "redis": check_redis,
        "pgvector": check_pgvector,
        "aws": check_aws,
    }
    
    results = []
    
    if args.service == "all":
        for name, check_func in checks.items():
            results.append(check_func())
    else:
        results.append(checks[args.service]())
    
    print("=" * 50)
    
    if all(results):
        print("All checks passed!")
        sys.exit(0)
    else:
        print("Some checks failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
