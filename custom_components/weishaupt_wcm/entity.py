"""Gemeinsame Basis für alle Entitäten."""

from __future__ import annotations

from homeassistant.const import EntityCategory
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_CIRCUITS, CONF_GENERATORS, DOMAIN, MANUFACTURER, SW_WTC_G, SW_WTC_O
from .coordinator import BoundPoint, WcmCoordinator
from .datapoints import Scope


def hub_device_info(coordinator: WcmCoordinator) -> DeviceInfo:
    entry = coordinator.config_entry
    return DeviceInfo(
        identifiers={(DOMAIN, f"{entry.entry_id}_wcm")},
        name="WCM-COM",
        manufacturer=MANUFACTURER,
        model="WCM-COM 1.0 home",
        configuration_url=f"http://{entry.data['host']}",
    )


def _sw(coordinator: WcmCoordinator, conf_key: str, busk: int) -> int | None:
    for b, sw in coordinator.config_entry.data.get(conf_key, []):
        if b == busk:
            return sw
    return None


def device_info_for(coordinator: WcmCoordinator, bound: BoundPoint) -> DeviceInfo:
    info = _device_info(coordinator, bound)
    if coordinator.hub_device_id:
        info["via_device_id"] = coordinator.hub_device_id
    return info


def _device_info(coordinator: WcmCoordinator, bound: BoundPoint) -> DeviceInfo:
    entry = coordinator.config_entry
    # Die Weboberfläche zählt ab 1: Buskennung 1 = "Heizkreis 2"
    number = str(bound.busk + 1)
    if bound.point.scope is Scope.GENERATOR:
        sw = _sw(coordinator, CONF_GENERATORS, bound.busk)
        model = "WTC-G" if sw in SW_WTC_G else "WTC-O" if sw in SW_WTC_O else None
        return DeviceInfo(
            identifiers={(DOMAIN, f"{entry.entry_id}_{bound.device_id}")},
            translation_key="generator" if bound.busk == 0 else "generator_n",
            translation_placeholders={"number": number},
            manufacturer=MANUFACTURER,
            model=model,
            sw_version=str(sw) if sw is not None else None,
        )
    sw = _sw(coordinator, CONF_CIRCUITS, bound.busk)
    return DeviceInfo(
        identifiers={(DOMAIN, f"{entry.entry_id}_{bound.device_id}")},
        translation_key="circuit",
        translation_placeholders={"number": number},
        manufacturer=MANUFACTURER,
        model="WCM-FS",
        sw_version=str(sw) if sw is not None else None,
    )


class WcmEntity(CoordinatorEntity[WcmCoordinator]):
    """Entität für genau einen Datenpunkt."""

    _attr_has_entity_name = True
    _unrecorded_attributes = frozenset({"infonummer", "rohwert"})

    def __init__(self, coordinator: WcmCoordinator, bound: BoundPoint) -> None:
        super().__init__(coordinator)
        self.bound = bound
        point = bound.point
        self._attr_unique_id = (
            f"{coordinator.config_entry.entry_id}_{bound.device_id}_{point.key}"
        )
        self._attr_translation_key = point.key
        self._attr_device_info = device_info_for(coordinator, bound)
        if point.icon:
            self._attr_icon = point.icon
        if point.diagnostic:
            self._attr_entity_category = EntityCategory.DIAGNOSTIC
        elif point.config:
            self._attr_entity_category = EntityCategory.CONFIG
        self._attr_entity_registry_enabled_default = point.enabled_default

    @property
    def raw(self) -> int | None:
        return self.coordinator.value(self.bound.key)

    @property
    def scaled(self) -> float | int | None:
        raw = self.raw
        if raw is None:
            return None
        factor = self.bound.point.factor
        if factor == 1:
            return raw
        value = raw * factor
        return round(value, 1) if factor < 1 else int(round(value))

    @property
    def extra_state_attributes(self) -> dict[str, int | None]:
        return {"infonummer": self.bound.point.info, "rohwert": self.raw}
