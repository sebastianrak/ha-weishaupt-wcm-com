"""Weishaupt WCM-COM: lokale Anbindung über parameter.json."""

from __future__ import annotations

from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.httpx_client import get_async_client

from .api import WcmClient
from .const import CONF_CIRCUITS, CONF_GENERATORS, CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
from .coordinator import WcmConfigEntry, WcmCoordinator, bind_points
from .entity import hub_device_info

PLATFORMS = [
    Platform.BINARY_SENSOR,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
]


async def async_setup_entry(hass: HomeAssistant, entry: WcmConfigEntry) -> bool:
    client = WcmClient(
        get_async_client(hass),
        entry.data[CONF_HOST],
        entry.data.get(CONF_USERNAME),
        entry.data.get(CONF_PASSWORD),
    )
    generators = [busk for busk, _ in entry.data.get(CONF_GENERATORS, [])]
    circuits = [busk for busk, _ in entry.data.get(CONF_CIRCUITS, [])]
    coordinator = WcmCoordinator(
        hass,
        entry,
        client,
        bind_points(generators, circuits),
        entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
    )
    await coordinator.async_config_entry_first_refresh()
    if not coordinator.data:
        raise ConfigEntryNotReady("WCM-COM hat beim ersten Abruf keine Werte geliefert")

    # Das WCM-COM als übergeordnetes Gerät anlegen; Kessel und Heizkreis hängen daran.
    hub = dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id, **hub_device_info(coordinator)
    )
    coordinator.hub_device_id = hub.id

    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_reload))
    return True


async def _async_reload(hass: HomeAssistant, entry: WcmConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: WcmConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
