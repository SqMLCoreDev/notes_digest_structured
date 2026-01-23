"""
app/services/clients/es_client.py - OpenSearch/Elasticsearch Client (Async)

Handles all OpenSearch connections and query execution with async support.
"""

import httpx
import urllib3
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.core.logging import get_logger
from app.core.exceptions import OpenSearchError, AuthenticationError

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = get_logger(__name__)


class OpenSearchClient:
    """
    Async OpenSearch/Elasticsearch client for executing queries.
    Provides a clean interface for all ES operations with proper concurrency.
    """
    
    def __init__(
        self,
        url: Optional[str] = None,
        auth: Optional[str] = None
    ):
        """
        Initialize OpenSearch client.
        
        Args:
            url: OpenSearch URL (uses settings if not provided)
            auth: Base64 encoded auth string (uses settings if not provided)
        """
        self.url = url or settings.ES_URL
        self.auth = auth or settings.es_auth
        
        if not self.url:
            raise OpenSearchError(
                message="Elasticsearch URL not configured",
                details={"setting": "ES_URL"}
            )
        
        self.headers = {
            "Content-Type": "application/json"
        }
        
        if self.auth:
            self.headers["Authorization"] = f"Basic {self.auth}"
        
        self.used_indices: set = set()
        
        # Create async client with connection pooling
        self._client = httpx.AsyncClient(
            headers=self.headers,
            verify=False,
            timeout=30.0
        )
    
    async def close(self):
        """Close the async client connection."""
        await self._client.aclose()
    
    async def test_connection(self) -> Dict[str, Any]:
        """
        Test OpenSearch connection.
        
        Returns:
            Dict with connection status and cluster info
        """
        try:
            response = await self._client.get(
                f"{self.url}/_cluster/health",
                timeout=5.0
            )
            
            if response.status_code == 401:
                raise AuthenticationError(
                    message="OpenSearch authentication failed",
                    details={"url": self.url}
                )
            
            response.raise_for_status()
            health = response.json()
            
            return {
                'status': 'healthy',
                'cluster_status': health.get('status', 'unknown'),
                'cluster_name': health.get('cluster_name', 'unknown'),
                'number_of_nodes': health.get('number_of_nodes', 0)
            }
            
        except AuthenticationError:
            raise
        except httpx.RequestError as e:
            return {
                'status': 'unreachable',
                'error': str(e)
            }
    
    async def search(
        self,
        index: str,
        query: Dict[str, Any],
        size: int = 10,
        sort: Optional[List] = None,
        fields: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Execute a search query.
        
        Args:
            index: Index to search
            query: Elasticsearch query DSL
            size: Number of results
            sort: Sort specification
            fields: Fields to return
            
        Returns:
            Search results
        """
        self.used_indices.add(index)
        
        body = {
            "query": query,
            "size": min(size, 1000)  # Cap at 1000
        }
        
        if sort:
            body['sort'] = sort
        
        if fields:
            body['_source'] = fields
        
        logger.debug(f"Searching {index}, size={size}")
        
        try:
            response = await self._client.post(
                f"{self.url}/{index}/_search",
                json=body
            )
            
            await self._check_response(response, "search")
            
            result = response.json()
            hits = result.get('hits', {}).get('hits', [])
            total = result.get('hits', {}).get('total', {})
            total_count = total.get('value', 0) if isinstance(total, dict) else total
            
            return {
                'success': True,
                'total_documents': total_count,
                'returned_documents': len(hits),
                'documents': [hit['_source'] for hit in hits]
            }
            
        except OpenSearchError:
            raise
        except Exception as e:
            raise OpenSearchError(
                message=f"Search failed: {str(e)}",
                details={"index": index}
            )
    
    async def aggregate(
        self,
        index: str,
        aggs: Dict[str, Any],
        query: Optional[Dict] = None,
        size: int = 0
    ) -> Dict[str, Any]:
        """
        Execute an aggregation query.
        
        Args:
            index: Index to aggregate
            aggs: Aggregation specification
            query: Optional filter query
            size: Number of documents to return (0 for aggs only)
            
        Returns:
            Aggregation results
        """
        self.used_indices.add(index)
        
        body = {
            "query": query or {"match_all": {}},
            "aggs": aggs,
            "size": size
        }
        
        logger.debug(f"Aggregating {index}, aggs={list(aggs.keys())}")
        
        try:
            response = await self._client.post(
                f"{self.url}/{index}/_search",
                json=body
            )
            
            await self._check_response(response, "aggregate")
            
            result = response.json()
            total = result.get('hits', {}).get('total', {})
            total_count = total.get('value', 0) if isinstance(total, dict) else total
            
            return {
                'success': True,
                'total_documents': total_count,
                'aggregations': result.get('aggregations', {})
            }
            
        except OpenSearchError:
            raise
        except Exception as e:
            raise OpenSearchError(
                message=f"Aggregation failed: {str(e)}",
                details={"index": index}
            )
    
    async def count(
        self,
        index: str,
        query: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Execute a count query.
        
        Args:
            index: Index to count
            query: Optional filter query
            
        Returns:
            Count result
        """
        self.used_indices.add(index)
        
        body = {"query": query or {"match_all": {}}}
        
        logger.debug(f"Counting {index}")
        
        try:
            response = await self._client.post(
                f"{self.url}/{index}/_count",
                json=body
            )
            
            await self._check_response(response, "count")
            
            result = response.json()
            
            return {
                'success': True,
                'count': result.get('count', 0)
            }
            
        except OpenSearchError:
            raise
        except Exception as e:
            raise OpenSearchError(
                message=f"Count failed: {str(e)}",
                details={"index": index}
            )
    
    async def get_mapping(self, index: str) -> Dict[str, Any]:
        """
        Get index mapping.
        
        Args:
            index: Index name
            
        Returns:
            Index mapping
        """
        try:
            response = await self._client.get(
                f"{self.url}/{index}/_mapping",
                timeout=10.0
            )
            
            await self._check_response(response, "mapping")
            
            return response.json()
            
        except OpenSearchError:
            raise
        except Exception as e:
            raise OpenSearchError(
                message=f"Failed to get mapping: {str(e)}",
                details={"index": index}
            )
    
    async def get_index_schemas(self, indices: List[str]) -> Dict[str, Dict]:
        """
        Get field mappings (schema) for multiple indices.
        
        Args:
            indices: List of index names
            
        Returns:
            Dict of index schemas with field types and document counts
        """
        schemas = {}
        
        for index in indices:
            try:
                # Get mapping
                mapping = await self.get_mapping(index)
                
                # Get count
                count_result = await self.count(index)
                doc_count = count_result.get('count', 0)
                
                # Extract field information
                properties = mapping.get(index, {}).get('mappings', {}).get('properties', {})
                
                fields = {}
                for field_name, field_info in properties.items():
                    field_type = field_info.get('type', 'unknown')
                    fields[field_name] = {
                        'type': field_type,
                        'format': field_info.get('format', None)
                    }
                
                schemas[index] = {
                    'document_count': doc_count,
                    'fields': fields,
                    'field_count': len(fields),
                    'sample_fields': list(fields.keys())[:20]
                }
                
                logger.info(f"Schema for {index}: {doc_count:,} docs, {len(fields)} fields")
                
            except Exception as e:
                logger.error(f"Failed to get schema for {index}: {e}")
                schemas[index] = {'error': str(e)}
        
        return schemas
    
    async def _check_response(self, response: httpx.Response, operation: str) -> None:
        """Check response for errors."""
        if response.status_code == 401:
            raise AuthenticationError(
                message=f"OpenSearch authentication failed during {operation}",
                details={"url": self.url, "status_code": 401}
            )
        
        if response.status_code >= 400:
            raise OpenSearchError(
                message=f"OpenSearch {operation} failed",
                details={
                    "status_code": response.status_code,
                    "response": response.text[:500]
                }
            )
    
    def reset_used_indices(self) -> None:
        """Reset the tracking of used indices."""
        self.used_indices = set()
    
    def get_used_indices(self) -> List[str]:
        """Get list of indices used since last reset."""
        return list(self.used_indices)
