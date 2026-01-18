"""Config flow for Keenetic integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_USERNAME
from homeassistant.helpers import config_validation as cv

from .const import (
    CONF_USE_SSL,
    CONF_VERIFY_SSL,
    DEFAULT_HOST,
    DEFAULT_PORT,
    DEFAULT_SSL_PORT,
    DEFAULT_USE_SSL,
    DEFAULT_USERNAME,
    DEFAULT_VERIFY_SSL,
    DOMAIN,
)
from .exceptions import (
    KeeneticAuthenticationError,
    KeeneticConnectionError,
    KeeneticError,
    KeeneticTimeoutError,
)
from .keenetic import KeeneticRouter

_LOGGER = logging.getLogger(__name__)

RESULT_AUTH_FAILED = "auth_failed"
RESULT_CANNOT_CONNECT = "cannot_connect"
RESULT_TIMEOUT = "timeout"
RESULT_UNKNOWN = "unknown"


class KeeneticConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Keenetic."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._config_data: dict[str, Any] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._config_data = user_input

            host = user_input[CONF_HOST]
            use_ssl = user_input.get(CONF_USE_SSL, DEFAULT_USE_SSL)

            await self.async_set_unique_id(host)
            self._abort_if_unique_id_configured()

            result, error = await self._async_test_connection(user_input)

            if result:
                return self.async_create_entry(
                    title=f"Keenetic ({host})",
                    data=user_input,
                )

            errors["base"] = error or RESULT_UNKNOWN

        data_schema = vol.Schema(
            {
                vol.Required(
                    CONF_HOST,
                    default=self._config_data.get(CONF_HOST, DEFAULT_HOST),
                ): cv.string,
                vol.Required(
                    CONF_USERNAME,
                    default=self._config_data.get(CONF_USERNAME, DEFAULT_USERNAME),
                ): cv.string,
                vol.Required(CONF_PASSWORD): cv.string,
                vol.Optional(
                    CONF_PORT,
                    description={"suggested_value": self._config_data.get(CONF_PORT)},
                ): cv.port,
                vol.Optional(
                    CONF_USE_SSL,
                    default=self._config_data.get(CONF_USE_SSL, DEFAULT_USE_SSL),
                ): cv.boolean,
                vol.Optional(
                    CONF_VERIFY_SSL,
                    default=self._config_data.get(CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL),
                ): cv.boolean,
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
        )

    async def _async_test_connection(
        self, user_input: dict[str, Any]
    ) -> tuple[bool, str | None]:
        """Test connection to the router."""
        host = user_input[CONF_HOST]
        port = user_input.get(CONF_PORT)
        username = user_input[CONF_USERNAME]
        password = user_input[CONF_PASSWORD]
        use_ssl = user_input.get(CONF_USE_SSL, DEFAULT_USE_SSL)
        verify_ssl = user_input.get(CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL)

        router = KeeneticRouter(
            host=host,
            port=port,
            username=username,
            password=password,
            use_ssl=use_ssl,
            verify_ssl=verify_ssl,
        )

        try:
            await router.connect()
            if router.is_connected:
                _LOGGER.info("Successfully connected to Keenetic router at %s", host)
                return True, None
            return False, RESULT_AUTH_FAILED

        except KeeneticAuthenticationError as err:
            _LOGGER.warning("Authentication failed for %s: %s", host, err)
            return False, RESULT_AUTH_FAILED

        except KeeneticTimeoutError as err:
            _LOGGER.warning("Connection timeout for %s: %s", host, err)
            return False, RESULT_TIMEOUT

        except KeeneticConnectionError as err:
            _LOGGER.warning("Cannot connect to %s: %s", host, err)
            return False, RESULT_CANNOT_CONNECT

        except KeeneticError as err:
            _LOGGER.error("Unexpected error connecting to %s: %s", host, err)
            return False, RESULT_UNKNOWN

        except Exception as err:
            _LOGGER.exception("Unknown error connecting to %s: %s", host, err)
            return False, RESULT_UNKNOWN

        finally:
            await router.close()
