"""
Pytest configuration for RiskPilot AI backend tests.
Configures anyio backend for all async tests.
"""
import pytest


# Configure anyio to run all @pytest.mark.anyio tests with asyncio backend
def pytest_configure(config):
    config.addinivalue_line(
        "markers", "anyio: mark a test as an async test using anyio"
    )
