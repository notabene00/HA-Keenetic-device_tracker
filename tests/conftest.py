"""Fixtures for Keenetic integration tests."""
from __future__ import annotations

import sys
from collections.abc import Generator
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Mock homeassistant modules before any imports
mock_ha = MagicMock()
sys.modules["homeassistant"] = mock_ha
sys.modules["homeassistant.config_entries"] = MagicMock()
sys.modules["homeassistant.const"] = MagicMock()
sys.modules["homeassistant.core"] = MagicMock()
sys.modules["homeassistant.exceptions"] = MagicMock()
sys.modules["homeassistant.helpers"] = MagicMock()
sys.modules["homeassistant.helpers.config_validation"] = MagicMock()
sys.modules["homeassistant.helpers.dispatcher"] = MagicMock()
sys.modules["homeassistant.helpers.entity_platform"] = MagicMock()
sys.modules["homeassistant.helpers.event"] = MagicMock()
sys.modules["homeassistant.util"] = MagicMock()
sys.modules["homeassistant.util.dt"] = MagicMock()
sys.modules["homeassistant.components"] = MagicMock()
sys.modules["homeassistant.components.device_tracker"] = MagicMock()
sys.modules["voluptuous"] = MagicMock()

# Add custom_components to path for imports
CUSTOM_COMPONENTS_PATH = str(Path(__file__).parent.parent / "custom_components")
if CUSTOM_COMPONENTS_PATH not in sys.path:
    sys.path.insert(0, CUSTOM_COMPONENTS_PATH)


@pytest.fixture
def mock_httpx_client() -> Generator[MagicMock, None, None]:
    """Create a mock httpx AsyncClient."""
    with patch("httpx.AsyncClient") as mock_client:
        mock_instance = MagicMock()
        mock_instance.get = AsyncMock()
        mock_instance.post = AsyncMock()
        mock_instance.aclose = AsyncMock()
        mock_client.return_value = mock_instance
        yield mock_instance
