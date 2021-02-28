"""Support for scanning a network."""
import logging

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.components.device_tracker import (DOMAIN, PLATFORM_SCHEMA,
                                                     DeviceScanner)
from homeassistant.const import (CONF_HOST, CONF_PASSWORD, CONF_PORT,
                                 CONF_USERNAME)

from .keenetic import Router

_LOGGER = logging.getLogger(__name__)


PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Optional(CONF_USERNAME, default="admin"): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
        vol.Optional(CONF_PORT, default=80): cv.port,
        vol.Optional(CONF_HOST, default="192.168.1.1"): cv.string,
    }
)


def get_scanner(hass, config):
    """Validate the configuration and return a Keenetic scanner."""
    config = config[DOMAIN]
    router = Router(
        username=config[CONF_USERNAME],
        password=config[CONF_PASSWORD],
        host=config[CONF_HOST],
        port=config[CONF_PORT],
    )
    return Keenetic(router)


class Keenetic(DeviceScanner):
    """This class scans for devices."""

    def __init__(self, router):
        """Initialize the scanner."""
        self.last_results = []
        self.router = router
        _LOGGER.debug("Scanner initialized")

    def scan_devices(self):
        """Scan for new devices and return a list with found device IDs."""
        self._update_info()
        _LOGGER.debug("Keenetic last update results %s", self.last_results)
        return [device.mac for device in self.last_results]

    def get_device_name(self, target_mac):
        """Return the name of the given device or None if we don't know."""
        return next(
            (
                device.name or device.hostname
                for device in self.last_results
                if device.mac == target_mac
            ),
            None,
        )

    def get_extra_attributes(self, target_mac):
        """Return extra attributes of the given device."""
        device = next(
            (device for device in self.last_results if device.mac == target_mac),
            None,
        )
        if device:
            keys = device.__dict__.keys()
            info = {
                "mac": device.mac,
                "registered": device.registered,
                "ip": device.ip,
                "access": device.access,
                "uptime": device.uptime,
                "hostname": device.hostname,
            }
            if "ssid" in keys: # wireless
                info.update({"ssid": device.ssid, "rssi": device.rssi})
            elif "port" in keys: # wired
                info.update({"port": device.port, "speed": device.speed, "duplex": device.duplex})
            return info
        return {}

    def _update_info(self):
        """Scan the network for devices.

        Returns boolean if scanning successful.
        """
        if self.router.is_authenticated:
            self.last_results = self.router.connected_devices
            return True
        return False
