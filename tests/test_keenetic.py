"""Tests for Keenetic router API client."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

# Add custom_components to path for imports
CUSTOM_COMPONENTS_PATH = str(Path(__file__).parent.parent / "custom_components")
if CUSTOM_COMPONENTS_PATH not in sys.path:
    sys.path.insert(0, CUSTOM_COMPONENTS_PATH)

from keenetic.const import (
    CONNECTION_TYPE_WIRED,
    CONNECTION_TYPE_WIRELESS,
)
from keenetic.exceptions import (
    KeeneticAuthenticationError,
    KeeneticConnectionError,
    KeeneticResponseError,
    KeeneticTimeoutError,
)
from keenetic.keenetic import ConnectedDevice, KeeneticRouter


class TestConnectedDevice:
    """Tests for ConnectedDevice dataclass."""

    def test_from_dict_wireless(self) -> None:
        """Test creating wireless device from dict."""
        data = {
            "mac": "AA:BB:CC:DD:EE:FF",
            "name": "Test Phone",
            "hostname": "test-phone",
            "ip": "192.168.1.100",
            "active": True,
            "registered": True,
            "access": "permit",
            "uptime": 3600,
            "ssid": "MyWiFi",
            "rssi": -45,
        }
        device = ConnectedDevice.from_dict(data)

        assert device.mac == "AA:BB:CC:DD:EE:FF"
        assert device.name == "Test Phone"
        assert device.hostname == "test-phone"
        assert device.ip == "192.168.1.100"
        assert device.active is True
        assert device.registered is True
        assert device.ssid == "MyWiFi"
        assert device.rssi == -45
        assert device.connection_type == CONNECTION_TYPE_WIRELESS

    def test_from_dict_wired(self) -> None:
        """Test creating wired device from dict."""
        data = {
            "mac": "AA:BB:CC:DD:EE:FF",
            "name": "Desktop",
            "ip": "192.168.1.101",
            "active": True,
            "port": 1,
            "speed": 1000,
            "duplex": "full",
        }
        device = ConnectedDevice.from_dict(data)

        assert device.mac == "AA:BB:CC:DD:EE:FF"
        assert device.port == 1
        assert device.speed == 1000
        assert device.duplex == "full"
        assert device.connection_type == CONNECTION_TYPE_WIRED

    def test_from_dict_with_dashes(self) -> None:
        """Test that keys with dashes are normalized."""
        data = {
            "mac": "AA:BB:CC:DD:EE:FF",
            "some-key": "value",
            "active": True,
        }
        device = ConnectedDevice.from_dict(data)
        assert device._raw_data.get("some_key") == "value"

    def test_display_name_priority(self) -> None:
        """Test display name returns best available name."""
        device1 = ConnectedDevice.from_dict({
            "mac": "AA:BB:CC:DD:EE:FF",
            "name": "Custom Name",
            "hostname": "hostname",
        })
        assert device1.display_name == "Custom Name"

        device2 = ConnectedDevice.from_dict({
            "mac": "AA:BB:CC:DD:EE:FF",
            "hostname": "hostname",
        })
        assert device2.display_name == "hostname"

        device3 = ConnectedDevice.from_dict({
            "mac": "AA:BB:CC:DD:EE:FF",
        })
        assert device3.display_name == "AA:BB:CC:DD:EE:FF"

    def test_get_extra_attributes_wireless(self) -> None:
        """Test extra attributes for wireless device."""
        device = ConnectedDevice.from_dict({
            "mac": "AA:BB:CC:DD:EE:FF",
            "ip": "192.168.1.100",
            "ssid": "MyWiFi",
            "rssi": -50,
            "active": True,
        })
        attrs = device.get_extra_attributes()

        assert attrs["mac"] == "AA:BB:CC:DD:EE:FF"
        assert attrs["ip"] == "192.168.1.100"
        assert attrs["ssid"] == "MyWiFi"
        assert attrs["rssi"] == -50
        assert attrs["connection_type"] == CONNECTION_TYPE_WIRELESS
        assert "port" not in attrs

    def test_get_extra_attributes_wired(self) -> None:
        """Test extra attributes for wired device."""
        device = ConnectedDevice.from_dict({
            "mac": "AA:BB:CC:DD:EE:FF",
            "ip": "192.168.1.100",
            "port": 1,
            "speed": 1000,
            "active": True,
        })
        attrs = device.get_extra_attributes()

        assert attrs["port"] == 1
        assert attrs["speed"] == 1000
        assert attrs["connection_type"] == CONNECTION_TYPE_WIRED
        assert "ssid" not in attrs


class TestKeeneticRouter:
    """Tests for KeeneticRouter class."""

    def test_init_http(self) -> None:
        """Test initialization with HTTP."""
        router = KeeneticRouter(
            host="192.168.1.1",
            port=80,
            username="admin",
            password="secret",
            use_ssl=False,
        )
        assert router._endpoint == "http://192.168.1.1:80"
        assert router.host == "192.168.1.1"

    def test_init_https(self) -> None:
        """Test initialization with HTTPS."""
        router = KeeneticRouter(
            host="192.168.1.1",
            username="admin",
            password="secret",
            use_ssl=True,
        )
        assert router._endpoint == "https://192.168.1.1:443"

    def test_init_default_port(self) -> None:
        """Test default port selection."""
        router_http = KeeneticRouter(host="192.168.1.1", use_ssl=False)
        assert router_http._port == 80

        router_https = KeeneticRouter(host="192.168.1.1", use_ssl=True)
        assert router_https._port == 443

    @pytest.mark.asyncio
    async def test_connect_success(self, mock_httpx_client: MagicMock) -> None:
        """Test successful connection."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_httpx_client.get = AsyncMock(return_value=mock_response)

        with patch("httpx.AsyncClient", return_value=mock_httpx_client):
            router = KeeneticRouter(
                host="192.168.1.1",
                username="admin",
                password="secret",
            )
            await router.connect()

            assert router.is_connected is True

    @pytest.mark.asyncio
    async def test_connect_with_auth(self, mock_httpx_client: MagicMock) -> None:
        """Test connection requiring authentication."""
        auth_response = MagicMock()
        auth_response.status_code = 401
        auth_response.headers = {
            "X-NDM-Realm": "test-realm",
            "X-NDM-Challenge": "test-challenge",
        }

        success_response = MagicMock()
        success_response.status_code = 200

        mock_httpx_client.get = AsyncMock(return_value=auth_response)
        mock_httpx_client.post = AsyncMock(return_value=success_response)

        with patch("httpx.AsyncClient", return_value=mock_httpx_client):
            router = KeeneticRouter(
                host="192.168.1.1",
                username="admin",
                password="secret",
            )
            await router.connect()

            assert router.is_connected is True
            mock_httpx_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_connect_auth_failed(self, mock_httpx_client: MagicMock) -> None:
        """Test connection with failed authentication."""
        auth_response = MagicMock()
        auth_response.status_code = 401
        auth_response.headers = {
            "X-NDM-Realm": "test-realm",
            "X-NDM-Challenge": "test-challenge",
        }

        failed_response = MagicMock()
        failed_response.status_code = 401

        mock_httpx_client.get = AsyncMock(return_value=auth_response)
        mock_httpx_client.post = AsyncMock(return_value=failed_response)

        with patch("httpx.AsyncClient", return_value=mock_httpx_client):
            router = KeeneticRouter(
                host="192.168.1.1",
                username="admin",
                password="wrong",
            )

            with pytest.raises(KeeneticAuthenticationError):
                await router.connect()

    @pytest.mark.asyncio
    async def test_connect_timeout(self, mock_httpx_client: MagicMock) -> None:
        """Test connection timeout."""
        mock_httpx_client.get = AsyncMock(
            side_effect=httpx.TimeoutException("Timeout")
        )

        with patch("httpx.AsyncClient", return_value=mock_httpx_client):
            router = KeeneticRouter(host="192.168.1.1")

            with pytest.raises(KeeneticTimeoutError):
                await router.connect()

    @pytest.mark.asyncio
    async def test_connect_error(self, mock_httpx_client: MagicMock) -> None:
        """Test connection error."""
        mock_httpx_client.get = AsyncMock(
            side_effect=httpx.ConnectError("Connection refused")
        )

        with patch("httpx.AsyncClient", return_value=mock_httpx_client):
            router = KeeneticRouter(host="192.168.1.1")

            with pytest.raises(KeeneticConnectionError):
                await router.connect()

    @pytest.mark.asyncio
    async def test_get_connected_devices(self, mock_httpx_client: MagicMock) -> None:
        """Test getting connected devices."""
        auth_response = MagicMock()
        auth_response.status_code = 200

        devices_response = MagicMock()
        devices_response.is_success = True
        devices_response.json.return_value = {
            "host": [
                {
                    "mac": "AA:BB:CC:DD:EE:01",
                    "name": "Device1",
                    "ip": "192.168.1.100",
                    "active": True,
                },
                {
                    "mac": "AA:BB:CC:DD:EE:02",
                    "name": "Device2",
                    "ip": "192.168.1.101",
                    "active": True,
                },
                {
                    "mac": "AA:BB:CC:DD:EE:03",
                    "name": "Inactive",
                    "ip": "192.168.1.102",
                    "active": False,
                },
            ]
        }

        mock_httpx_client.get = AsyncMock(
            side_effect=[auth_response, devices_response]
        )

        with patch("httpx.AsyncClient", return_value=mock_httpx_client):
            router = KeeneticRouter(host="192.168.1.1")
            await router.connect()
            devices = await router.get_connected_devices()

            assert len(devices) == 2
            assert devices[0].mac == "AA:BB:CC:DD:EE:01"
            assert devices[1].mac == "AA:BB:CC:DD:EE:02"

    @pytest.mark.asyncio
    async def test_get_connected_devices_invalid_response(
        self, mock_httpx_client: MagicMock
    ) -> None:
        """Test handling invalid response format."""
        auth_response = MagicMock()
        auth_response.status_code = 200

        devices_response = MagicMock()
        devices_response.is_success = True
        devices_response.json.return_value = {"invalid": "data"}

        mock_httpx_client.get = AsyncMock(
            side_effect=[auth_response, devices_response]
        )

        with patch("httpx.AsyncClient", return_value=mock_httpx_client):
            router = KeeneticRouter(host="192.168.1.1")
            await router.connect()
            devices = await router.get_connected_devices()

            assert devices == []

    @pytest.mark.asyncio
    async def test_close(self, mock_httpx_client: MagicMock) -> None:
        """Test closing connection."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_httpx_client.get = AsyncMock(return_value=mock_response)

        with patch("httpx.AsyncClient", return_value=mock_httpx_client):
            router = KeeneticRouter(host="192.168.1.1")
            await router.connect()
            assert router.is_connected is True

            await router.close()
            assert router.is_connected is False
            mock_httpx_client.aclose.assert_called_once()

    @pytest.mark.asyncio
    async def test_context_manager(self, mock_httpx_client: MagicMock) -> None:
        """Test async context manager."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_httpx_client.get = AsyncMock(return_value=mock_response)

        with patch("httpx.AsyncClient", return_value=mock_httpx_client):
            async with KeeneticRouter(host="192.168.1.1") as router:
                assert router.is_connected is True

            mock_httpx_client.aclose.assert_called_once()

    @pytest.mark.asyncio
    async def test_retry_on_timeout(self, mock_httpx_client: MagicMock) -> None:
        """Test retry mechanism on timeout."""
        auth_response = MagicMock()
        auth_response.status_code = 200

        success_response = MagicMock()
        success_response.is_success = True
        success_response.json.return_value = {"host": []}

        mock_httpx_client.get = AsyncMock(
            side_effect=[
                auth_response,
                httpx.TimeoutException("Timeout"),
                success_response,
            ]
        )

        with patch("httpx.AsyncClient", return_value=mock_httpx_client):
            with patch("asyncio.sleep", new_callable=AsyncMock):
                router = KeeneticRouter(host="192.168.1.1")
                await router.connect()
                devices = await router.get_connected_devices()

                assert devices == []
                assert mock_httpx_client.get.call_count == 3

    @pytest.mark.asyncio
    async def test_reauth_on_401(self, mock_httpx_client: MagicMock) -> None:
        """Test re-authentication on 401 response."""
        auth_response = MagicMock()
        auth_response.status_code = 200

        expired_response = MagicMock()
        expired_response.status_code = 401

        success_response = MagicMock()
        success_response.is_success = True
        success_response.json.return_value = {"host": []}

        mock_httpx_client.get = AsyncMock(
            side_effect=[
                auth_response,
                expired_response,
                auth_response,
                success_response,
            ]
        )

        with patch("httpx.AsyncClient", return_value=mock_httpx_client):
            router = KeeneticRouter(host="192.168.1.1")
            await router.connect()
            devices = await router.get_connected_devices()

            assert devices == []
