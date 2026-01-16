"""Device tracker platform for Keenetic routers."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from homeassistant.components.device_tracker import ScannerEntity, SourceType
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import (
    ATTR_CONNECTION_TYPE,
    CONNECTION_TYPE_WIRELESS,
    DOMAIN,
    SIGNAL_DEVICE_NEW,
    SIGNAL_DEVICE_UPDATE,
)

if TYPE_CHECKING:
    from . import KeeneticConfigEntry
    from .router import KeeneticDeviceInfo, KeeneticRouterCoordinator

_LOGGER = logging.getLogger(__name__)

DEFAULT_DEVICE_NAME = "Unknown device"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: KeeneticConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up device tracker for Keenetic component."""
    coordinator = entry.runtime_data
    tracked: set[str] = set()

    @callback
    def update_router() -> None:
        """Update the values of the router."""
        add_entities(coordinator, async_add_entities, tracked)

    coordinator.async_on_close(
        async_dispatcher_connect(hass, SIGNAL_DEVICE_NEW, update_router)
    )

    update_router()


@callback
def add_entities(
    coordinator: KeeneticRouterCoordinator,
    async_add_entities: AddConfigEntryEntitiesCallback,
    tracked: set[str],
) -> None:
    """Add new tracker entities from the router."""
    new_tracked = []

    for mac, device in coordinator.devices.items():
        if mac in tracked:
            continue

        new_tracked.append(KeeneticDeviceTracker(coordinator, device))
        tracked.add(mac)

    if new_tracked:
        _LOGGER.debug("Adding %d new device tracker entities", len(new_tracked))
        async_add_entities(new_tracked)


class KeeneticDeviceTracker(ScannerEntity):
    """Representation of a Keenetic device tracker."""

    _attr_should_poll = False
    _attr_source_type = SourceType.ROUTER

    def __init__(
        self,
        coordinator: KeeneticRouterCoordinator,
        device: KeeneticDeviceInfo,
    ) -> None:
        """Initialize a Keenetic device tracker."""
        self._coordinator = coordinator
        self._device = device
        self._attr_unique_id = device.mac
        self._attr_name = device.name or DEFAULT_DEVICE_NAME

    @property
    def is_connected(self) -> bool:
        """Return true if the device is connected to the network."""
        return self._device.is_connected

    @property
    def hostname(self) -> str | None:
        """Return the hostname of device."""
        return self._device.hostname

    @property
    def ip_address(self) -> str | None:
        """Return the primary ip address of the device."""
        return self._device.ip_address

    @property
    def mac_address(self) -> str:
        """Return the mac address of the device."""
        return self._device.mac

    @property
    def icon(self) -> str:
        """Return device icon."""
        if not self._device.is_connected:
            return "mdi:lan-disconnect"
        if self._device.connection_type == CONNECTION_TYPE_WIRELESS:
            return "mdi:wifi"
        return "mdi:lan-connect"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        return self._device.extra_attributes

    @callback
    def async_on_demand_update(self) -> None:
        """Update state."""
        if self._device.mac in self._coordinator.devices:
            self._device = self._coordinator.devices[self._device.mac]
            self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        """Register state update callback."""
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                SIGNAL_DEVICE_UPDATE,
                self.async_on_demand_update,
            )
        )
