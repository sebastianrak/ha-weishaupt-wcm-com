"""Schalter zum Pausieren der Abfrage.

Das WCM-COM erlaubt nur einen angemeldeten Client. Solange Home Assistant
abfragt, lässt die Weboberfläche keine Anmeldung zu. Mit diesem Schalter
pausiert die Abfrage, die letzten Werte bleiben stehen, Schreiben ist gesperrt.
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import WcmConfigEntry, WcmCoordinator
from .entity import hub_device_info


async def async_setup_entry(
    hass: HomeAssistant,
    entry: WcmConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    async_add_entities([WcmPauseSwitch(entry.runtime_data)])


class WcmPauseSwitch(CoordinatorEntity[WcmCoordinator], SwitchEntity):
    _attr_has_entity_name = True
    _attr_translation_key = "pause"
    _attr_icon = "mdi:pause-circle-outline"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: WcmCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_pause"
        self._attr_device_info = hub_device_info(coordinator)

    @property
    def available(self) -> bool:
        return True

    @property
    def is_on(self) -> bool:
        return self.coordinator.paused

    async def async_turn_on(self, **kwargs: Any) -> None:
        self.coordinator.paused = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        self.coordinator.paused = False
        self.async_write_ha_state()
        await self.coordinator.async_request_refresh()
