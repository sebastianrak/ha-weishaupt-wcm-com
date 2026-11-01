"""Tests von Einrichtung, Entitäten, Schreiben und Pause (WCM-COM simuliert)."""

from unittest.mock import patch

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import entity_registry as er
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.weishaupt_wcm.api import ScanResult, WcmAuthError, WcmBusyError
from custom_components.weishaupt_wcm.const import DOMAIN

VALUES = {
    (10, 0, 12): 40, (10, 0, 14): 540, (10, 0, 2): 410, (10, 0, 13): 400, (10, 0, 3101): 400,
    (10, 0, 325): 370, (10, 0, 2572): 85, (10, 0, 1): 0, (10, 0, 81): 1, (10, 0, 138): 37,
    (10, 0, 3158): 50, (10, 0, 3159): 191, (10, 0, 700): 284, (10, 0, 466): 0, (10, 0, 82): 1,
    (10, 0, 83): 0, (10, 0, 373): 0, (10, 0, 1497): 1, (10, 0, 1498): 0,
    (10, 0, 118): None, (10, 0, 3103): -2, (10, 0, 31): 250, (10, 0, 39): 750,
    (6, 1, 274): 11, (6, 1, 5): 210, (6, 1, 8): 170, (6, 1, 104): 0x40, (6, 1, 2585): 1,
    (6, 1, 17): None, (6, 1, 19): 550, (6, 1, 650): 400, (6, 1, 270): 120, (6, 1, 321): 1,
    (6, 1, 2586): 60, (6, 1, 4): 210, (6, 1, 2): 405,
}

DATA = {
    "host": "192.168.1.50",
    "username": "wcm",
    "password": "x",
    "generators": [[0, 61491]],
    "circuits": [[1, 327]],
}


class FakeClient:
    def __init__(self) -> None:
        self.values = dict(VALUES)
        self.writes: list = []
        self.busy_next = 0
        self.read_calls = 0
        self.scan_error: Exception | None = None

    async def scan(self) -> ScanResult:
        if self.scan_error:
            raise self.scan_error
        return ScanResult(generators=[(0, 61491)], circuits=[(1, 327)])

    async def read(self, keys):
        self.read_calls += 1
        if self.busy_next:
            self.busy_next -= 1
            raise WcmBusyError("server is busy")
        return {k: self.values[k] for k in keys if k in self.values}

    async def write(self, key, raw) -> None:
        self.writes.append((key, raw))
        self.values[key] = raw


@pytest.fixture
def fake():
    client = FakeClient()
    with (
        patch("custom_components.weishaupt_wcm.WcmClient", return_value=client),
        patch("custom_components.weishaupt_wcm.config_flow.WcmClient", return_value=client),
        patch("custom_components.weishaupt_wcm.coordinator.WRITE_READBACK_DELAY", 0),
    ):
        yield client


async def _setup(hass: HomeAssistant) -> MockConfigEntry:
    entry = MockConfigEntry(domain=DOMAIN, unique_id="192.168.1.50", data=DATA)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


def _state(hass: HomeAssistant, entity_id: str) -> str:
    state = hass.states.get(entity_id)
    assert state is not None, entity_id
    return state.state


async def test_config_flow(hass: HomeAssistant, fake) -> None:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    assert result["type"] is FlowResultType.FORM
    with patch("custom_components.weishaupt_wcm.async_setup_entry", return_value=True):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"host": "192.168.1.50", "username": "wcm", "password": "x"}
        )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"]["generators"] == [[0, 61491]]
    assert result["data"]["circuits"] == [[1, 327]]


async def test_config_flow_wrong_password(hass: HomeAssistant, fake) -> None:
    fake.scan_error = WcmAuthError("HTTP 401")
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"host": "192.168.1.50", "username": "wcm", "password": "falsch"}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}


async def test_entities(hass: HomeAssistant, fake) -> None:
    entry = await _setup(hass)
    ids = [e.entity_id for e in er.async_entries_for_config_entry(er.async_get(hass), entry.entry_id)]

    assert _state(hass, "sensor.heat_generator_outdoor_temperature") == "4.0"
    assert _state(hass, "sensor.heat_generator_hot_water_temperature") == "54.0"
    assert _state(hass, "sensor.heat_generator_burner_starts") == "50000"
    assert _state(hass, "sensor.heat_generator_burner_operating_hours") == "19100"
    assert _state(hass, "sensor.heat_generator_p20_outdoor_sensor_correction") == "-2"
    assert _state(hass, "sensor.heat_generator_load") == "37"
    assert _state(hass, "binary_sensor.heat_generator_flame") == "on"
    assert _state(hass, "binary_sensor.heat_generator_fault") == "off"
    assert _state(hass, "sensor.heating_circuit_2_control_mode") == "weather"
    # Bit 0x40 in Infonummer 104 bei Buskennung 1 -> Warmwasser-Betriebsart
    assert _state(hass, "select.heating_circuit_2_hot_water_operating_mode") == "dhw_program"
    assert _state(hass, "number.heating_circuit_2_normal_room_temperature") == "21.0"
    assert _state(hass, "number.heating_circuit_2_hot_water_normal_setpoint") == "55.0"
    # Optionale Werte ohne Inhalt werden nicht angelegt, interne Werte nie
    assert hass.states.get("sensor.heat_generator_buffer_sensor") is None
    assert hass.states.get("sensor.heating_circuit_2_room_temperature") is None
    assert not any("status" in i for i in ids)


async def test_german_names(hass: HomeAssistant, fake) -> None:
    hass.config.language = "de"
    await _setup(hass)
    state = hass.states.get("sensor.warmeerzeuger_aussentemperatur")
    assert state is not None
    assert state.attributes["friendly_name"] == "Wärmeerzeuger Außentemperatur"
    assert hass.states.get("select.heizkreis_2_betriebsart_warmwasser") is not None


async def test_write_number_and_select(hass: HomeAssistant, fake) -> None:
    await _setup(hass)
    await hass.services.async_call(
        "number", "set_value",
        {"entity_id": "number.heating_circuit_2_normal_room_temperature", "value": 21.4},
        blocking=True,
    )
    assert fake.writes[-1] == ((6, 1, 5), 215)  # auf 0,5 °C gerundet
    assert _state(hass, "number.heating_circuit_2_normal_room_temperature") == "21.5"

    await hass.services.async_call(
        "select", "select_option",
        {"entity_id": "select.heating_circuit_2_hot_water_operating_mode", "option": "setback"},
        blocking=True,
    )
    assert fake.writes[-1] == ((6, 1, 274), 4)
    await hass.async_block_till_done()
    assert _state(hass, "select.heating_circuit_2_hot_water_operating_mode") == "setback"

    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            "number", "set_value",
            {"entity_id": "number.heating_circuit_2_normal_room_temperature", "value": 40},
            blocking=True,
        )
    assert fake.writes[-1] == ((6, 1, 274), 4)


async def test_pause_and_busy(hass: HomeAssistant, fake) -> None:
    entry = await _setup(hass)
    coordinator = entry.runtime_data

    await hass.services.async_call("switch", "turn_on", {"entity_id": "switch.wcm_com_pause_polling"}, blocking=True)
    assert coordinator.paused
    calls = fake.read_calls
    await coordinator.async_refresh()
    assert fake.read_calls == calls
    assert _state(hass, "select.heating_circuit_2_hot_water_operating_mode") == "unavailable"
    assert _state(hass, "sensor.heat_generator_outdoor_temperature") == "4.0"

    await hass.services.async_call("switch", "turn_off", {"entity_id": "switch.wcm_com_pause_polling"}, blocking=True)
    await hass.async_block_till_done()
    assert _state(hass, "select.heating_circuit_2_hot_water_operating_mode") == "dhw_program"

    # Ein einzelnes 'busy' wird überbrückt
    fake.busy_next = 1
    await coordinator.async_refresh()
    await hass.async_block_till_done()
    assert coordinator.last_update_success
    assert _state(hass, "sensor.heat_generator_outdoor_temperature") == "4.0"

    # Dauerhaft belegt -> nicht verfügbar, danach wieder da
    fake.busy_next = 5
    for _ in range(3):
        await coordinator.async_refresh()
    await hass.async_block_till_done()
    assert _state(hass, "sensor.heat_generator_outdoor_temperature") == "unavailable"
    fake.busy_next = 0
    await coordinator.async_refresh()
    await hass.async_block_till_done()
    assert _state(hass, "sensor.heat_generator_outdoor_temperature") == "4.0"


async def test_unload(hass: HomeAssistant, fake) -> None:
    entry = await _setup(hass)
    assert await hass.config_entries.async_unload(entry.entry_id)
