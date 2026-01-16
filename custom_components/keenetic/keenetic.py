"""Keenetic router API client with async support."""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from hashlib import md5, sha256
from typing import Any

import httpx

from .const import (
    API_AUTH,
    API_HOTSPOT,
    ATTR_ACCESS,
    ATTR_CONNECTION_TYPE,
    ATTR_DUPLEX,
    ATTR_HOSTNAME,
    ATTR_IP,
    ATTR_MAC,
    ATTR_PORT,
    ATTR_REGISTERED,
    ATTR_RSSI,
    ATTR_SPEED,
    ATTR_SSID,
    ATTR_UPTIME,
    CONNECTION_TIMEOUT,
    CONNECTION_TYPE_WIRED,
    CONNECTION_TYPE_WIRELESS,
    DEFAULT_HOST,
    DEFAULT_PORT,
    DEFAULT_SSL_PORT,
    DEFAULT_USERNAME,
    DEFAULT_USE_SSL,
    DEFAULT_VERIFY_SSL,
    MAX_RETRY_ATTEMPTS,
    REQUEST_TIMEOUT,
    RETRY_BASE_DELAY,
    RETRY_MAX_DELAY,
)
from .exceptions import (
    KeeneticAuthenticationError,
    KeeneticConnectionError,
    KeeneticError,
    KeeneticResponseError,
    KeeneticTimeoutError,
)

_LOGGER = logging.getLogger(__name__)


@dataclass
class ConnectedDevice:
    """Representation of a device connected to the router."""

    mac: str
    name: str | None = None
    hostname: str | None = None
    ip: str | None = None
    active: bool = False
    registered: bool = False
    access: str | None = None
    uptime: int | None = None
    ssid: str | None = None
    rssi: int | None = None
    port: int | None = None
    speed: int | None = None
    duplex: str | None = None
    _raw_data: dict[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ConnectedDevice:
        """Create ConnectedDevice from API response dictionary."""
        normalized = {
            key.replace("-", "_"): value for key, value in data.items()
        }
        return cls(
            mac=normalized.get("mac", ""),
            name=normalized.get("name"),
            hostname=normalized.get("hostname"),
            ip=normalized.get("ip"),
            active=normalized.get("active", False),
            registered=normalized.get("registered", False),
            access=normalized.get("access"),
            uptime=normalized.get("uptime"),
            ssid=normalized.get("ssid"),
            rssi=normalized.get("rssi"),
            port=normalized.get("port"),
            speed=normalized.get("speed"),
            duplex=normalized.get("duplex"),
            _raw_data=normalized,
        )

    @property
    def connection_type(self) -> str:
        """Return connection type (wireless or wired)."""
        if self.ssid is not None:
            return CONNECTION_TYPE_WIRELESS
        if self.port is not None:
            return CONNECTION_TYPE_WIRED
        return CONNECTION_TYPE_WIRED

    @property
    def display_name(self) -> str:
        """Return the best available name for the device."""
        return self.name or self.hostname or self.mac

    def get_extra_attributes(self) -> dict[str, Any]:
        """Return extra attributes for Home Assistant entity."""
        attrs: dict[str, Any] = {
            ATTR_MAC: self.mac,
            ATTR_IP: self.ip,
            ATTR_HOSTNAME: self.hostname,
            ATTR_REGISTERED: self.registered,
            ATTR_ACCESS: self.access,
            ATTR_UPTIME: self.uptime,
            ATTR_CONNECTION_TYPE: self.connection_type,
        }
        if self.connection_type == CONNECTION_TYPE_WIRELESS:
            attrs[ATTR_SSID] = self.ssid
            attrs[ATTR_RSSI] = self.rssi
        else:
            attrs[ATTR_PORT] = self.port
            attrs[ATTR_SPEED] = self.speed
            attrs[ATTR_DUPLEX] = self.duplex
        return {k: v for k, v in attrs.items() if v is not None}


class KeeneticRouter:
    """Async client for Keenetic router API."""

    def __init__(
        self,
        host: str = DEFAULT_HOST,
        port: int | None = None,
        username: str = DEFAULT_USERNAME,
        password: str = "",
        use_ssl: bool = DEFAULT_USE_SSL,
        verify_ssl: bool = DEFAULT_VERIFY_SSL,
    ) -> None:
        """Initialize the router client."""
        self._host = host
        self._port = port or (DEFAULT_SSL_PORT if use_ssl else DEFAULT_PORT)
        self._username = username
        self._password = password
        self._use_ssl = use_ssl
        self._verify_ssl = verify_ssl

        protocol = "https" if use_ssl else "http"
        self._endpoint = f"{protocol}://{host}:{self._port}"

        self._client: httpx.AsyncClient | None = None
        self._authenticated = False

    @property
    def host(self) -> str:
        """Return router host."""
        return self._host

    @property
    def is_connected(self) -> bool:
        """Return True if client is connected and authenticated."""
        return self._client is not None and self._authenticated

    async def __aenter__(self) -> KeeneticRouter:
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.close()

    async def connect(self) -> None:
        """Connect to the router and authenticate."""
        if self._client is not None:
            return

        _LOGGER.debug("Connecting to Keenetic router at %s", self._endpoint)

        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(REQUEST_TIMEOUT, connect=CONNECTION_TIMEOUT),
            verify=self._verify_ssl,
        )

        try:
            await self._authenticate()
        except Exception:
            await self.close()
            raise

    async def close(self) -> None:
        """Close the connection."""
        if self._client is not None:
            _LOGGER.debug("Closing connection to Keenetic router at %s", self._endpoint)
            await self._client.aclose()
            self._client = None
            self._authenticated = False

    async def _authenticate(self) -> None:
        """Authenticate with the router."""
        if self._client is None:
            raise KeeneticConnectionError("Client not initialized")

        _LOGGER.debug("Authenticating with Keenetic router")

        try:
            response = await self._client.get(f"{self._endpoint}{API_AUTH}")

            if response.status_code == 200:
                _LOGGER.debug("Already authenticated")
                self._authenticated = True
                return

            if response.status_code != 401:
                raise KeeneticAuthenticationError(
                    f"Unexpected auth response: {response.status_code}"
                )

            realm = response.headers.get("X-NDM-Realm")
            challenge = response.headers.get("X-NDM-Challenge")

            if not realm or not challenge:
                raise KeeneticAuthenticationError(
                    "Missing authentication headers from router"
                )

            password_hash = md5(
                f"{self._username}:{realm}:{self._password}".encode("utf-8")
            ).hexdigest()
            final_hash = sha256(
                f"{challenge}{password_hash}".encode("utf-8")
            ).hexdigest()

            auth_response = await self._client.post(
                f"{self._endpoint}{API_AUTH}",
                json={"login": self._username, "password": final_hash},
            )

            if auth_response.status_code != 200:
                raise KeeneticAuthenticationError(
                    f"Authentication failed with status {auth_response.status_code}"
                )

            _LOGGER.info("Successfully authenticated with Keenetic router at %s", self._host)
            self._authenticated = True

        except httpx.TimeoutException as err:
            raise KeeneticTimeoutError(
                f"Timeout during authentication: {err}"
            ) from err
        except httpx.RequestError as err:
            raise KeeneticConnectionError(
                f"Connection error during authentication: {err}"
            ) from err

    async def _request_with_retry(
        self,
        method: str,
        url: str,
        **kwargs: Any,
    ) -> httpx.Response:
        """Make HTTP request with exponential backoff retry."""
        if self._client is None:
            raise KeeneticConnectionError("Client not connected")

        last_error: Exception | None = None

        for attempt in range(MAX_RETRY_ATTEMPTS):
            try:
                if method.upper() == "GET":
                    response = await self._client.get(url, **kwargs)
                else:
                    response = await self._client.post(url, **kwargs)

                if response.status_code == 401:
                    _LOGGER.debug("Session expired, re-authenticating (attempt %d)", attempt + 1)
                    self._authenticated = False
                    await self._authenticate()
                    continue

                return response

            except httpx.TimeoutException as err:
                last_error = KeeneticTimeoutError(f"Request timeout: {err}")
                _LOGGER.warning(
                    "Request timeout (attempt %d/%d): %s",
                    attempt + 1,
                    MAX_RETRY_ATTEMPTS,
                    err,
                )
            except httpx.RequestError as err:
                last_error = KeeneticConnectionError(f"Request error: {err}")
                _LOGGER.warning(
                    "Request error (attempt %d/%d): %s",
                    attempt + 1,
                    MAX_RETRY_ATTEMPTS,
                    err,
                )

            if attempt < MAX_RETRY_ATTEMPTS - 1:
                delay = min(
                    RETRY_BASE_DELAY * (2 ** attempt),
                    RETRY_MAX_DELAY,
                )
                _LOGGER.debug("Retrying in %.1f seconds", delay)
                await asyncio.sleep(delay)

        raise last_error or KeeneticError("Request failed after all retries")

    async def get_connected_devices(self) -> list[ConnectedDevice]:
        """Get list of connected devices from the router."""
        if not self._authenticated:
            await self._authenticate()

        _LOGGER.debug("Fetching connected devices from %s", self._host)

        try:
            response = await self._request_with_retry(
                "GET",
                f"{self._endpoint}{API_HOTSPOT}",
            )

            if not response.is_success:
                raise KeeneticResponseError(
                    f"Failed to get devices: HTTP {response.status_code}"
                )

            data = response.json()
            hosts = data.get("host", [])

            devices = [
                ConnectedDevice.from_dict(host)
                for host in hosts
                if host.get("active", False)
            ]

            _LOGGER.debug("Found %d active devices", len(devices))
            return devices

        except (KeyError, ValueError) as err:
            raise KeeneticResponseError(f"Invalid response format: {err}") from err

    async def test_connection(self) -> bool:
        """Test connection to the router."""
        try:
            await self.connect()
            return self._authenticated
        except KeeneticError as err:
            _LOGGER.error("Connection test failed: %s", err)
            return False


# Backward compatibility alias
Router = KeeneticRouter
