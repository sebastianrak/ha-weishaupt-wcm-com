"""Sensoren."""

from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import WcmConfigEntry, WcmCoordinator
from .datapoints import Kind
from .entity import WcmEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: WcmConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    entities: list[SensorEntity] = []
    for bound in coordinator.points:
        if not coordinator.is_present(bound):
            continue
        if bound.point.kind is Kind.SENSOR:
            entities.append(WcmSensor(coordinator, bound))
        elif bound.point.kind is Kind.ENUM:
            entities.append(WcmEnumSensor(coordinator, bound))
    async_add_entities(entities)


class WcmSensor(WcmEntity, SensorEntity):
    def __init__(self, coordinator: WcmCoordinator, bound) -> None:
        super().__init__(coordinator, bound)
        point = bound.point
        self._attr_native_unit_of_measurement = point.unit
        if point.device_class:
            self._attr_device_class = SensorDeviceClass(point.device_class)
        if point.state_class:
            self._attr_state_class = SensorStateClass(point.state_class)
        # Ganzzahlige Werte (auch Stunden/Minuten) ohne Nachkommastellen anzeigen
        self._attr_suggested_display_precision = 1 if point.factor < 1 else 0

    @property
    def native_value(self) -> float | int | None:
        return self.scaled


class WcmEnumSensor(WcmEntity, SensorEntity):
    _attr_device_class = SensorDeviceClass.ENUM

    def __init__(self, coordinator: WcmCoordinator, bound) -> None:
        super().__init__(coordinator, bound)
        self._attr_options = list(bound.point.options.values())

    @property
    def native_value(self) -> str | None:
        raw = self.raw
        if raw is None:
            return None
        return self.bound.point.options.get(raw)
