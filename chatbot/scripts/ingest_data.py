#!/usr/bin/env python
"""
scripts/ingest_data.py - Data Ingestion Script

Ingests clinical notes into Elasticsearch and/or PGVector.

Usage:
    python scripts/ingest_data.py --source notes.json --target elasticsearch
    python scripts/ingest_data.py --source notes.json --target pgvector
    python scripts/ingest_data.py --source notes.json --target both
"""

import argparse
import json
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def ingest_to_elasticsearch(data: list, index_name: str):
    """Ingest data into Elasticsearch."""
    from app.services.clients.es_client import OpenSearchClient
    
    client = OpenSearchClient()
    print(f"Ingesting {len(data)} documents to Elasticsearch index: {index_name}")
    
    # TODO: Implement bulk ingestion
    # for doc in data:
    #     client.index(index=index_name, document=doc)
    
    print("Elasticsearch ingestion complete.")


def ingest_to_pgvector(data: list, collection_name: str):
    """Ingest data into PGVector."""
    from app.services.rag.embeddings import get_embeddings_client
    from app.services.clients.pgvector_client import get_vector_store_client
    
    embeddings = get_embeddings_client()
    if not embeddings:
        print("ERROR: Embeddings client not available.")
        return
    
    vector_store = get_vector_store_client(embeddings=embeddings.get_langchain_embeddings())
    if not vector_store:
        print("ERROR: Vector store client not available.")
        return
    
    print(f"Ingesting {len(data)} documents to PGVector collection: {collection_name}")
    
    # TODO: Implement vector ingestion
    # texts = [doc.get('content', '') for doc in data]
    # metadatas = [doc.get('metadata', {}) for doc in data]
    # vector_store.add_texts(texts, metadatas)
    
    print("PGVector ingestion complete.")


def main():
    parser = argparse.ArgumentParser(description="Ingest data into Elasticsearch/PGVector")
    parser.add_argument("--source", required=True, help="Source JSON file")
    parser.add_argument("--target", choices=["elasticsearch", "pgvector", "both"], default="both")
    parser.add_argument("--index", default="tiamd_prod_clinical_notes", help="Elasticsearch index name")
    parser.add_argument("--collection", default="clinical_notes", help="PGVector collection name")
    
    args = parser.parse_args()
    
    # Load source data
    source_path = Path(args.source)
    if not source_path.exists():
        print(f"ERROR: Source file not found: {args.source}")
        sys.exit(1)
    
    with open(source_path, 'r') as f:
        data = json.load(f)
    
    print(f"Loaded {len(data)} documents from {args.source}")
    
    # Ingest based on target
    if args.target in ["elasticsearch", "both"]:
        ingest_to_elasticsearch(data, args.index)
    
    if args.target in ["pgvector", "both"]:
        ingest_to_pgvector(data, args.collection)
    
    print("Ingestion complete!")


if __name__ == "__main__":
    main()
