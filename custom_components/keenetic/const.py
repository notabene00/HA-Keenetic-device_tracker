"""Constants for Keenetic integration."""
from typing import Final

DOMAIN: Final = "keenetic"
VERSION: Final = "2.0.0"

# Configuration
CONF_USE_SSL: Final = "use_ssl"
CONF_VERIFY_SSL: Final = "verify_ssl"

# Defaults
DEFAULT_HOST: Final = "192.168.1.1"
DEFAULT_PORT: Final = 80
DEFAULT_SSL_PORT: Final = 443
DEFAULT_USERNAME: Final = "admin"
DEFAULT_USE_SSL: Final = False
DEFAULT_VERIFY_SSL: Final = False
DEFAULT_SCAN_INTERVAL: Final = 30
DEFAULT_CONSIDER_HOME: Final = 180

# Retry settings
MAX_RETRY_ATTEMPTS: Final = 3
RETRY_BASE_DELAY: Final = 1.0
RETRY_MAX_DELAY: Final = 10.0

# API endpoints
API_AUTH: Final = "/auth"
API_HOTSPOT: Final = "/rci/show/ip/hotspot"

# Timeouts (seconds)
REQUEST_TIMEOUT: Final = 10.0
CONNECTION_TIMEOUT: Final = 5.0

# Signals
SIGNAL_DEVICE_NEW: Final = f"{DOMAIN}_device_new"
SIGNAL_DEVICE_UPDATE: Final = f"{DOMAIN}_device_update"

# Device attributes
ATTR_MAC: Final = "mac"
ATTR_IP: Final = "ip"
ATTR_HOSTNAME: Final = "hostname"
ATTR_REGISTERED: Final = "registered"
ATTR_ACCESS: Final = "access"
ATTR_UPTIME: Final = "uptime"
ATTR_SSID: Final = "ssid"
ATTR_RSSI: Final = "rssi"
ATTR_PORT: Final = "port"
ATTR_SPEED: Final = "speed"
ATTR_DUPLEX: Final = "duplex"
ATTR_CONNECTION_TYPE: Final = "connection_type"

# Connection types
CONNECTION_TYPE_WIRELESS: Final = "wireless"
CONNECTION_TYPE_WIRED: Final = "wired"
