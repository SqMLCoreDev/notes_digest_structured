# Pytest Configuration

"""
Pytest fixtures and configuration for tests.
"""

import pytest
import asyncio
from typing import Generator, AsyncGenerator

# Configure async test support
@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def sample_query() -> str:
    """Sample query for testing."""
    return "What is the total count of records?"


@pytest.fixture
def sample_mrn() -> str:
    """Sample MRN for testing."""
    return "123456"


@pytest.fixture
def sample_patient_name() -> str:
    """Sample patient name for testing."""
    return "John Doe"


# Add more fixtures as needed for:
# - Mock Elasticsearch client
# - Mock Claude client
# - Test user credentials
# - Sample conversation history
