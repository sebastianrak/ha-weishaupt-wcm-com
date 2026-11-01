"""Binärsensoren."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import BoundPoint, WcmConfigEntry, WcmCoordinator
from .datapoints import Kind
from .entity import WcmEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: WcmConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    entities: list[BinarySensorEntity] = []
    for bound in coordinator.points:
        if not coordinator.is_present(bound):
            continue
        if bound.point.kind is Kind.BINARY:
            entities.append(WcmBinarySensor(coordinator, bound))
        elif bound.point.key == "fehlercode":
            entities.append(WcmFaultSensor(coordinator, bound))
    async_add_entities(entities)


class WcmBinarySensor(WcmEntity, BinarySensorEntity):
    def __init__(self, coordinator: WcmCoordinator, bound: BoundPoint) -> None:
        super().__init__(coordinator, bound)
        if bound.point.device_class:
            self._attr_device_class = BinarySensorDeviceClass(bound.point.device_class)

    @property
    def is_on(self) -> bool | None:
        raw = self.raw
        return None if raw is None else raw != 0


class WcmFaultSensor(WcmEntity, BinarySensorEntity):
    """Störung = Fehlercode ungleich 0."""

    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    def __init__(self, coordinator: WcmCoordinator, bound: BoundPoint) -> None:
        super().__init__(coordinator, bound)
        self._attr_unique_id = f"{self._attr_unique_id}_stoerung"
        self._attr_translation_key = "stoerung"
        self._attr_icon = None
        self._attr_entity_category = None

    @property
    def is_on(self) -> bool | None:
        raw = self.raw
        return None if raw is None else raw != 0
