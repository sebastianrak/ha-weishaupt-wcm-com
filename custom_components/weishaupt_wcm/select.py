"""Auswahl: Betriebsart des Heizkreises bzw. des Warmwassers."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .api import WcmError
from .const import DOMAIN, MT_FS
from .coordinator import BoundPoint, WcmConfigEntry, WcmCoordinator
from .datapoints import MODE_WW, Kind
from .entity import WcmEntity

# Form_Heizkreis_Benutzer.js: Ist in Infonummer 104 Bit 0x40 gesetzt und die
# Buskennung nicht 0, steht Infonummer 274 für die Warmwasser-Betriebsart.
FLAG_WW_MODE = 0x40


def _is_ww_mode(coordinator: WcmCoordinator, bound: BoundPoint) -> bool:
    flags = coordinator.value((MT_FS, bound.busk, 104))
    return flags is not None and bool(flags & FLAG_WW_MODE) and bound.busk != 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: WcmConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(
        WcmModeSelect(coordinator, bound, _is_ww_mode(coordinator, bound))
        for bound in coordinator.points
        if bound.point.kind is Kind.SELECT and coordinator.is_present(bound)
    )


class WcmModeSelect(WcmEntity, SelectEntity):
    def __init__(self, coordinator: WcmCoordinator, bound: BoundPoint, ww: bool) -> None:
        super().__init__(coordinator, bound)
        self._map = MODE_WW if ww else bound.point.options
        if ww:
            self._attr_translation_key = "betriebsart_warmwasser"
            self._attr_icon = "mdi:water-boiler"
        self._attr_options = list(self._map.values())

    @property
    def available(self) -> bool:
        return super().available and not self.coordinator.paused and self.raw is not None

    @property
    def current_option(self) -> str | None:
        raw = self.raw
        return None if raw is None else self._map.get(raw)

    async def async_select_option(self, option: str) -> None:
        raw = next((k for k, v in self._map.items() if v == option), None)
        if raw is None:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="invalid_option",
                translation_placeholders={"option": option},
            )
        try:
            await self.coordinator.async_write(self.bound, raw)
        except WcmError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="write_failed",
                translation_placeholders={"error": str(err)},
            ) from err
