"""Keenetic router coordinator for Home Assistant."""
from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_USERNAME
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.util import dt as dt_util

from .const import (
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
    CONF_USE_SSL,
    CONF_VERIFY_SSL,
    CONNECTION_TYPE_WIRED,
    CONNECTION_TYPE_WIRELESS,
    DEFAULT_CONSIDER_HOME,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_USE_SSL,
    DEFAULT_VERIFY_SSL,
    DOMAIN,
    SIGNAL_DEVICE_NEW,
    SIGNAL_DEVICE_UPDATE,
)
from .exceptions import KeeneticError
from .keenetic import ConnectedDevice, KeeneticRouter

if TYPE_CHECKING:
    from . import KeeneticConfigEntry

_LOGGER = logging.getLogger(__name__)


@dataclass
class KeeneticDeviceInfo:
    """Representation of a Keenetic device info."""

    mac: str
    name: str | None = None
    hostname: str | None = None
    ip_address: str | None = None
    connection_type: str = CONNECTION_TYPE_WIRED
    ssid: str | None = None
    rssi: int | None = None
    port: int | None = None
    speed: int | None = None
    duplex: str | None = None
    registered: bool = False
    access: str | None = None
    uptime: int | None = None
    last_activity: datetime | None = None
    _is_connected: bool = False

    @property
    def is_connected(self) -> bool:
        """Return connected status."""
        return self._is_connected

    @property
    def extra_attributes(self) -> dict[str, Any]:
        """Return extra attributes for the entity."""
        attrs: dict[str, Any] = {
            ATTR_MAC: self.mac,
            ATTR_IP: self.ip_address,
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

    def update(
        self,
        device: ConnectedDevice | None = None,
        consider_home: int = DEFAULT_CONSIDER_HOME,
    ) -> None:
        """Update device info from router data."""
        utc_now = dt_util.utcnow()

        if device:
            if not self.name:
                self.name = device.name or device.hostname or self.mac.replace(":", "_")
            self.hostname = device.hostname
            self.ip_address = device.ip
            self.registered = device.registered
            self.access = device.access
            self.uptime = device.uptime
            self.ssid = device.ssid
            self.rssi = device.rssi
            self.port = device.port
            self.speed = device.speed
            self.duplex = device.duplex
            self.connection_type = device.connection_type
            self.last_activity = utc_now
            self._is_connected = True
        elif self._is_connected:
            self._is_connected = (
                self.last_activity is not None
                and (utc_now - self.last_activity).total_seconds() < consider_home
            )
            if not self._is_connected:
                self.ip_address = None


class KeeneticRouterCoordinator:
    """Coordinator for Keenetic router data updates."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        self.hass = hass
        self._entry = entry

        self._devices: dict[str, KeeneticDeviceInfo] = {}
        self._connect_error: bool = False
        self._on_close: list[Callable[[], None]] = []

        self._router: KeeneticRouter | None = None
        self._scan_interval = timedelta(seconds=DEFAULT_SCAN_INTERVAL)
        self._consider_home = DEFAULT_CONSIDER_HOME

    @property
    def host(self) -> str:
        """Return router host."""
        return self._entry.data[CONF_HOST]

    @property
    def devices(self) -> dict[str, KeeneticDeviceInfo]:
        """Return tracked devices."""
        return self._devices

    async def setup(self) -> None:
        """Set up the router coordinator."""
        _LOGGER.debug("Setting up Keenetic router coordinator for %s", self.host)

        self._router = KeeneticRouter(
            host=self._entry.data[CONF_HOST],
            port=self._entry.data.get(CONF_PORT),
            username=self._entry.data[CONF_USERNAME],
            password=self._entry.data[CONF_PASSWORD],
            use_ssl=self._entry.data.get(CONF_USE_SSL, DEFAULT_USE_SSL),
            verify_ssl=self._entry.data.get(CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL),
        )

        try:
            await self._router.connect()
        except KeeneticError as err:
            _LOGGER.error("Failed to connect to Keenetic router at %s: %s", self.host, err)
            raise ConfigEntryNotReady(
                f"Failed to connect to Keenetic router: {err}"
            ) from err

        if not self._router.is_connected:
            raise ConfigEntryNotReady("Failed to authenticate with Keenetic router")

        _LOGGER.info("Successfully connected to Keenetic router at %s", self.host)

        await self.update_devices()

        self.async_on_close(
            async_track_time_interval(
                self.hass,
                self._async_update_all,
                self._scan_interval,
            )
        )

    async def _async_update_all(self, now: datetime | None = None) -> None:
        """Update all data from the router."""
        await self.update_devices()

    async def update_devices(self) -> None:
        """Update device tracker data from the router."""
        if self._router is None:
            _LOGGER.error("Router not initialized")
            return

        _LOGGER.debug("Updating devices from Keenetic router at %s", self.host)
        new_device = False

        try:
            router_devices = await self._router.get_connected_devices()
        except KeeneticError as err:
            if not self._connect_error:
                self._connect_error = True
                _LOGGER.error(
                    "Error getting devices from Keenetic router at %s: %s",
                    self.host,
                    err,
                )
            return

        if self._connect_error:
            self._connect_error = False
            _LOGGER.info("Reconnected to Keenetic router at %s", self.host)

        router_devices_by_mac = {d.mac: d for d in router_devices}

        for mac, device_info in self._devices.items():
            router_device = router_devices_by_mac.pop(mac, None)
            device_info.update(router_device, self._consider_home)

        for mac, router_device in router_devices_by_mac.items():
            new_device = True
            device_info = KeeneticDeviceInfo(mac=mac)
            device_info.update(router_device, self._consider_home)
            self._devices[mac] = device_info
            _LOGGER.debug("New device discovered: %s (%s)", device_info.name, mac)

        async_dispatcher_send(self.hass, SIGNAL_DEVICE_UPDATE)
        if new_device:
            async_dispatcher_send(self.hass, SIGNAL_DEVICE_NEW)

    async def close(self) -> None:
        """Close the router connection."""
        if self._router is not None:
            _LOGGER.debug("Closing Keenetic router connection")
            await self._router.close()
            self._router = None

        for func in self._on_close:
            func()
        self._on_close.clear()

    @callback
    def async_on_close(self, func: CALLBACK_TYPE) -> None:
        """Add a function to call when coordinator is closed."""
        self._on_close.append(func)
