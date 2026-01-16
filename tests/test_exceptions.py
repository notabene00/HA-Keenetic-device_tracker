"""Tests for Keenetic exceptions."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Add custom_components to path for imports
CUSTOM_COMPONENTS_PATH = str(Path(__file__).parent.parent / "custom_components")
if CUSTOM_COMPONENTS_PATH not in sys.path:
    sys.path.insert(0, CUSTOM_COMPONENTS_PATH)

from keenetic.exceptions import (
    KeeneticAuthenticationError,
    KeeneticConnectionError,
    KeeneticError,
    KeeneticResponseError,
    KeeneticTimeoutError,
)


class TestExceptions:
    """Tests for custom exceptions."""

    def test_base_exception(self) -> None:
        """Test base KeeneticError."""
        error = KeeneticError("Test error")
        assert str(error) == "Test error"
        assert isinstance(error, Exception)

    def test_connection_error(self) -> None:
        """Test KeeneticConnectionError."""
        error = KeeneticConnectionError("Connection failed")
        assert str(error) == "Connection failed"
        assert isinstance(error, KeeneticError)

    def test_authentication_error(self) -> None:
        """Test KeeneticAuthenticationError."""
        error = KeeneticAuthenticationError("Auth failed")
        assert str(error) == "Auth failed"
        assert isinstance(error, KeeneticError)

    def test_timeout_error(self) -> None:
        """Test KeeneticTimeoutError."""
        error = KeeneticTimeoutError("Request timed out")
        assert str(error) == "Request timed out"
        assert isinstance(error, KeeneticError)

    def test_response_error(self) -> None:
        """Test KeeneticResponseError."""
        error = KeeneticResponseError("Invalid response")
        assert str(error) == "Invalid response"
        assert isinstance(error, KeeneticError)

    def test_exception_hierarchy(self) -> None:
        """Test that all exceptions inherit from KeeneticError."""
        exceptions = [
            KeeneticConnectionError("test"),
            KeeneticAuthenticationError("test"),
            KeeneticTimeoutError("test"),
            KeeneticResponseError("test"),
        ]

        for exc in exceptions:
            assert isinstance(exc, KeeneticError)

    def test_exception_can_be_caught_by_base(self) -> None:
        """Test that specific exceptions can be caught by base class."""
        with pytest.raises(KeeneticError):
            raise KeeneticConnectionError("test")

        with pytest.raises(KeeneticError):
            raise KeeneticAuthenticationError("test")

        with pytest.raises(KeeneticError):
            raise KeeneticTimeoutError("test")

        with pytest.raises(KeeneticError):
            raise KeeneticResponseError("test")
