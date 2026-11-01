"""Config Flow: Host und Zugang eingeben, Bus-Scan ausführen."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import callback
from homeassistant.helpers.httpx_client import get_async_client
from homeassistant.helpers.selector import TextSelector, TextSelectorConfig, TextSelectorType
import voluptuous as vol

from .api import WcmAuthError, WcmClient, WcmError
from .const import (
    CONF_CIRCUITS,
    CONF_GENERATORS,
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)


class WcmConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            await self.async_set_unique_id(host)
            self._abort_if_unique_id_configured()
            client = WcmClient(
                get_async_client(self.hass),
                host,
                user_input.get(CONF_USERNAME) or None,
                user_input.get(CONF_PASSWORD) or None,
            )
            try:
                scan = await client.scan()
            except WcmAuthError:
                errors["base"] = "invalid_auth"
            except WcmError as err:
                _LOGGER.warning("WCM-COM %s nicht erreichbar: %s", host, err)
                errors["base"] = "cannot_connect"
            else:
                if not scan.generators and not scan.circuits:
                    errors["base"] = "no_devices"
                else:
                    return self.async_create_entry(
                        title=f"WCM-COM ({host})",
                        data={
                            CONF_HOST: host,
                            CONF_USERNAME: user_input.get(CONF_USERNAME) or "",
                            CONF_PASSWORD: user_input.get(CONF_PASSWORD) or "",
                            CONF_GENERATORS: [list(p) for p in scan.generators],
                            CONF_CIRCUITS: [list(p) for p in scan.circuits],
                        },
                    )

        schema = vol.Schema(
            {
                vol.Required(CONF_HOST): str,
                vol.Optional(CONF_USERNAME, default=""): str,
                vol.Optional(CONF_PASSWORD, default=""): TextSelector(
                    TextSelectorConfig(type=TextSelectorType.PASSWORD)
                ),
            }
        )
        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(schema, user_input or {}),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry) -> OptionsFlow:
        return WcmOptionsFlow()


class WcmOptionsFlow(OptionsFlow):
    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data=user_input)
        current = self.config_entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_SCAN_INTERVAL, default=current): vol.All(
                        vol.Coerce(int), vol.Range(min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL)
                    )
                }
            ),
        )
