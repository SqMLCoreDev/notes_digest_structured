"""
Rate Limiter for AWS Bedrock API calls
Ensures we don't exceed AWS rate limits when processing multiple notes concurrently
"""

import time
import threading
from typing import Optional
from collections import deque
from dataclasses import dataclass

from medical_notes.config.config import BEDROCK_RATE_LIMIT_RPS


@dataclass
class RateLimitConfig:
    requests_per_second: float
    burst_capacity: int = None  # Allow burst up to this many requests
    
    def __post_init__(self):
        if self.burst_capacity is None:
            self.burst_capacity = max(1, int(self.requests_per_second * 2))


class TokenBucketRateLimiter:
    """
    Token bucket rate limiter for controlling API request rates.
    Thread-safe implementation for concurrent usage.
    """
    
    def __init__(self, config: RateLimitConfig):
        self.config = config
        self.tokens = float(config.burst_capacity)
        self.last_refill = time.time()
        self.lock = threading.Lock()
        
        print(f"🚦 Rate limiter initialized: {config.requests_per_second} RPS, burst: {config.burst_capacity}")
    
    def acquire(self, tokens: int = 1, timeout: Optional[float] = None) -> bool:
        """
        Acquire tokens from the bucket.
        
        Args:
            tokens: Number of tokens to acquire (default: 1)
            timeout: Maximum time to wait for tokens (None = wait indefinitely)
            
        Returns:
            bool: True if tokens acquired, False if timeout exceeded
        """
        start_time = time.time()
        
        while True:
            with self.lock:
                self._refill_tokens()
                
                if self.tokens >= tokens:
                    self.tokens -= tokens
                    return True
            
            # Check timeout
            if timeout is not None and (time.time() - start_time) >= timeout:
                return False
            
            # Wait a bit before trying again
            time.sleep(0.01)  # 10ms
    
    def _refill_tokens(self):
        """Refill tokens based on elapsed time (called with lock held)."""
        now = time.time()
        elapsed = now - self.last_refill
        
        # Add tokens based on rate
        tokens_to_add = elapsed * self.config.requests_per_second
        self.tokens = min(self.config.burst_capacity, self.tokens + tokens_to_add)
        self.last_refill = now
    
    def get_available_tokens(self) -> float:
        """Get current number of available tokens."""
        with self.lock:
            self._refill_tokens()
            return self.tokens
    
    def get_wait_time(self, tokens: int = 1) -> float:
        """
        Get estimated wait time to acquire the specified number of tokens.
        
        Args:
            tokens: Number of tokens needed
            
        Returns:
            float: Estimated wait time in seconds
        """
        with self.lock:
            self._refill_tokens()
            
            if self.tokens >= tokens:
                return 0.0
            
            tokens_needed = tokens - self.tokens
            return tokens_needed / self.config.requests_per_second


class BedrockRateLimiter:
    """
    Specialized rate limiter for AWS Bedrock API calls.
    Manages different types of requests with appropriate limits.
    """
    
    def __init__(self, requests_per_second: float = BEDROCK_RATE_LIMIT_RPS):
        self.config = RateLimitConfig(requests_per_second=requests_per_second)
        self.limiter = TokenBucketRateLimiter(self.config)
        
        # Track statistics
        self.stats = {
            "total_requests": 0,
            "total_wait_time": 0.0,
            "max_wait_time": 0.0,
            "rate_limited_count": 0
        }
        self.stats_lock = threading.Lock()
    
    def acquire_for_request(self, timeout: Optional[float] = 30.0) -> bool:
        """
        Acquire permission to make a Bedrock API request.
        
        Args:
            timeout: Maximum time to wait for permission (default: 30 seconds)
            
        Returns:
            bool: True if permission granted, False if timeout
        """
        start_time = time.time()
        
        # Check if we need to wait
        wait_time = self.limiter.get_wait_time(1)
        if wait_time > 0:
            with self.stats_lock:
                self.stats["rate_limited_count"] += 1
            
            print(f"⏱️ Rate limiting: waiting {wait_time:.2f}s for Bedrock API slot")
        
        # Acquire token
        success = self.limiter.acquire(1, timeout)
        
        # Update statistics
        actual_wait_time = time.time() - start_time
        with self.stats_lock:
            self.stats["total_requests"] += 1
            self.stats["total_wait_time"] += actual_wait_time
            self.stats["max_wait_time"] = max(self.stats["max_wait_time"], actual_wait_time)
        
        if not success:
            print(f"⚠️ Rate limiter timeout after {timeout}s - request rejected")
        
        return success
    
    def get_stats(self) -> dict:
        """Get rate limiter statistics."""
        with self.stats_lock:
            stats = self.stats.copy()
            
        # Add computed metrics
        if stats["total_requests"] > 0:
            stats["avg_wait_time"] = stats["total_wait_time"] / stats["total_requests"]
            stats["rate_limited_percentage"] = (stats["rate_limited_count"] / stats["total_requests"]) * 100
        else:
            stats["avg_wait_time"] = 0.0
            stats["rate_limited_percentage"] = 0.0
        
        stats["current_available_tokens"] = self.limiter.get_available_tokens()
        stats["configured_rps"] = self.config.requests_per_second
        
        return stats
    
    def reset_stats(self):
        """Reset statistics counters."""
        with self.stats_lock:
            self.stats = {
                "total_requests": 0,
                "total_wait_time": 0.0,
                "max_wait_time": 0.0,
                "rate_limited_count": 0
            }


# Global rate limiter instance
_bedrock_rate_limiter: Optional[BedrockRateLimiter] = None
_limiter_lock = threading.Lock()


def get_bedrock_rate_limiter() -> BedrockRateLimiter:
    """Get the global Bedrock rate limiter instance (singleton pattern)."""
    global _bedrock_rate_limiter
    
    if _bedrock_rate_limiter is None:
        with _limiter_lock:
            if _bedrock_rate_limiter is None:
                _bedrock_rate_limiter = BedrockRateLimiter()
    
    return _bedrock_rate_limiter


def acquire_bedrock_request_slot(timeout: Optional[float] = 30.0) -> bool:
    """
    Convenience function to acquire a Bedrock API request slot.
    
    Args:
        timeout: Maximum time to wait for a slot
        
    Returns:
        bool: True if slot acquired, False if timeout
    """
    return get_bedrock_rate_limiter().acquire_for_request(timeout)