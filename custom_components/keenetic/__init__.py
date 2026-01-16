"""The Keenetic device tracker integration."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STOP, Platform
from homeassistant.core import Event, HomeAssistant

from .const import DOMAIN, VERSION
from .router import KeeneticRouterCoordinator

if TYPE_CHECKING:
    pass

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.DEVICE_TRACKER]

type KeeneticConfigEntry = ConfigEntry[KeeneticRouterCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: KeeneticConfigEntry) -> bool:
    """Set up Keenetic from a config entry."""
    _LOGGER.debug("Setting up Keenetic integration v%s", VERSION)

    coordinator = KeeneticRouterCoordinator(hass, entry)
    await coordinator.setup()

    async def async_close_connection(event: Event) -> None:
        """Close Keenetic connection on HA Stop."""
        await coordinator.close()

    entry.async_on_unload(
        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, async_close_connection)
    )

    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    _LOGGER.info("Keenetic integration setup complete for %s", coordinator.host)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: KeeneticConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.debug("Unloading Keenetic integration")

    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        coordinator = entry.runtime_data
        await coordinator.close()

    return unload_ok
