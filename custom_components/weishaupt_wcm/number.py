"""Einstellbare Sollwerte (Seite 'Benutzer' des Heizkreises)."""

from __future__ import annotations

from homeassistant.components.number import NumberDeviceClass, NumberEntity, NumberMode
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .api import WcmError
from .const import DOMAIN
from .coordinator import BoundPoint, WcmConfigEntry, WcmCoordinator
from .datapoints import Kind
from .entity import WcmEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: WcmConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(
        WcmNumber(coordinator, bound)
        for bound in coordinator.points
        if bound.point.kind is Kind.NUMBER and coordinator.is_present(bound)
    )


class WcmNumber(WcmEntity, NumberEntity):
    _attr_mode = NumberMode.BOX

    def __init__(self, coordinator: WcmCoordinator, bound: BoundPoint) -> None:
        super().__init__(coordinator, bound)
        point = bound.point
        self._attr_native_min_value = point.min_value
        self._attr_native_max_value = point.max_value
        self._attr_native_step = point.step
        self._attr_native_unit_of_measurement = point.unit
        if point.device_class:
            self._attr_device_class = NumberDeviceClass(point.device_class)

    @property
    def available(self) -> bool:
        return super().available and not self.coordinator.paused and self.raw is not None

    @property
    def native_value(self) -> float | int | None:
        return self.scaled

    async def async_set_native_value(self, value: float) -> None:
        point = self.bound.point
        if not point.min_value <= value <= point.max_value:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="out_of_range",
                translation_placeholders={
                    "value": str(value),
                    "min": str(point.min_value),
                    "max": str(point.max_value),
                },
            )
        # Auf die Schrittweite der Weboberfläche runden, dann in den Rohwert wandeln
        value = round(round(value / point.step) * point.step, 3)
        raw = int(round(value / point.factor))
        try:
            await self.coordinator.async_write(self.bound, raw)
        except WcmError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="write_failed",
                translation_placeholders={"error": str(err)},
            ) from err
