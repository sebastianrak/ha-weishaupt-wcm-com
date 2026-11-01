"""Datenpunkte, abgeleitet aus den Seitenskripten der WCM-COM-Weboberfläche.

Quelle je Gruppe:
- Wärmeerzeuger:  Form_WTC_G_Prozesswerte.js / Form_WTC_G_Fachmann.js (Modul 10)
- Heizkreis:      Form_Heizkreis_Prozesswerte.js / _Benutzer.js / _Fachmann.js /
                  _Konfiguration.js (Modul 6, Mischerwerte Modul 12)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from .const import MT_FS, MT_MS, MT_WG


class Scope(StrEnum):
    GENERATOR = "generator"
    CIRCUIT = "circuit"


class Kind(StrEnum):
    SENSOR = "sensor"
    ENUM = "enum"
    BINARY = "binary"
    SELECT = "select"
    NUMBER = "number"
    INTERNAL = "internal"


@dataclass(frozen=True, kw_only=True)
class DataPoint:
    key: str  # zugleich translation_key
    scope: Scope
    module: int
    info: int
    kind: Kind
    factor: float = 1.0
    unit: str | None = None
    device_class: str | None = None
    state_class: str | None = None
    diagnostic: bool = False
    config: bool = False
    optional: bool = False  # nur anlegen, wenn beim ersten Abruf ein Wert kommt
    slow: bool = False  # nur jede SLOW_POLL_EVERY-te Abfrage lesen
    enabled_default: bool = True
    icon: str | None = None
    options: dict[int, str] = field(default_factory=dict)
    min_value: float | None = None
    max_value: float | None = None
    step: float | None = None


TEMP = "temperature"
DURATION = "duration"
MEAS = "measurement"
TOTAL_INC = "total_increasing"
C = "°C"
K = "K"
H = "h"
MIN = "min"
PCT = "%"

# Rohwert -> Optionsschlüssel (Texte in translations/*.json)
MODE_HK = {
    1: "standby",
    3: "normal",
    4: "setback",
    5: "summer",
    11: "program_1",
    12: "program_2",
    13: "program_3",
    255: "central",
}
MODE_WW = {1: "standby", 3: "normal", 4: "setback", 11: "dhw_program", 255: "central"}

G, HK = Scope.GENERATOR, Scope.CIRCUIT

DATAPOINTS: tuple[DataPoint, ...] = (
    # ---------------- Wärmeerzeuger: Prozesswerte ----------------
    DataPoint(key="aussentemperatur", scope=G, module=MT_WG, info=12, kind=Kind.SENSOR, factor=0.1, unit=C, device_class=TEMP, state_class=MEAS),
    DataPoint(key="gedaempfte_aussentemperatur", scope=G, module=MT_WG, info=2572, kind=Kind.SENSOR, factor=0.1, unit=C, device_class=TEMP, state_class=MEAS),
    DataPoint(key="waermeanforderung", scope=G, module=MT_WG, info=2, kind=Kind.SENSOR, factor=0.1, unit=C, device_class=TEMP, state_class=MEAS),
    DataPoint(key="vorlauftemperatur", scope=G, module=MT_WG, info=3101, kind=Kind.SENSOR, factor=0.1, unit=C, device_class=TEMP, state_class=MEAS),
    DataPoint(key="kesseltemperatur", scope=G, module=MT_WG, info=13, kind=Kind.SENSOR, factor=0.1, unit=C, device_class=TEMP, state_class=MEAS),
    DataPoint(key="abgastemperatur", scope=G, module=MT_WG, info=325, kind=Kind.SENSOR, factor=0.1, unit=C, device_class=TEMP, state_class=MEAS),
    DataPoint(key="warmwassertemperatur", scope=G, module=MT_WG, info=14, kind=Kind.SENSOR, factor=0.1, unit=C, device_class=TEMP, state_class=MEAS),
    DataPoint(key="pufferfuehler", scope=G, module=MT_WG, info=118, kind=Kind.SENSOR, factor=0.1, unit=C, device_class=TEMP, state_class=MEAS, optional=True),
    DataPoint(key="laststellung", scope=G, module=MT_WG, info=138, kind=Kind.SENSOR, unit=PCT, state_class=MEAS, icon="mdi:fire"),
    DataPoint(key="betriebsphase", scope=G, module=MT_WG, info=373, kind=Kind.SENSOR, icon="mdi:state-machine"),
    DataPoint(key="fehlercode", scope=G, module=MT_WG, info=1, kind=Kind.SENSOR, diagnostic=True, icon="mdi:alert-circle-outline"),
    DataPoint(key="brennerstarts", scope=G, module=MT_WG, info=3158, kind=Kind.SENSOR, factor=1000, state_class=TOTAL_INC, icon="mdi:counter"),
    DataPoint(key="betriebsstunden", scope=G, module=MT_WG, info=3159, kind=Kind.SENSOR, factor=100, unit=H, device_class=DURATION, state_class=TOTAL_INC),
    DataPoint(key="zeit_seit_wartung", scope=G, module=MT_WG, info=700, kind=Kind.SENSOR, factor=10, unit=H, device_class=DURATION, diagnostic=True),
    # Binärwerte
    DataPoint(key="flamme", scope=G, module=MT_WG, info=81, kind=Kind.BINARY, icon="mdi:fire"),
    DataPoint(key="gasventil_1", scope=G, module=MT_WG, info=1497, kind=Kind.BINARY, diagnostic=True),
    DataPoint(key="gasventil_2", scope=G, module=MT_WG, info=1498, kind=Kind.BINARY, diagnostic=True),
    DataPoint(key="kesselpumpe", scope=G, module=MT_WG, info=466, kind=Kind.BINARY, device_class="running"),
    DataPoint(key="heizbetrieb", scope=G, module=MT_WG, info=82, kind=Kind.BINARY, device_class="running", icon="mdi:radiator"),
    DataPoint(key="warmwasserbetrieb", scope=G, module=MT_WG, info=83, kind=Kind.BINARY, device_class="running", icon="mdi:water-boiler"),
    # ---------------- Wärmeerzeuger: Fachmann (nur lesen) ----------------
    DataPoint(key="p18_sonderniveau", scope=G, module=MT_WG, info=3102, kind=Kind.SENSOR, unit=C, device_class=TEMP, diagnostic=True, slow=True, optional=True),
    DataPoint(key="p20_aussenfuehler_korrektur", scope=G, module=MT_WG, info=3103, kind=Kind.SENSOR, unit=K, diagnostic=True, slow=True, optional=True),
    DataPoint(key="p23_anlagenfrostschutz", scope=G, module=MT_WG, info=2560, kind=Kind.SENSOR, factor=0.1, unit=C, device_class=TEMP, diagnostic=True, slow=True, optional=True),
    DataPoint(key="p30_min_vl_soll", scope=G, module=MT_WG, info=31, kind=Kind.SENSOR, factor=0.1, unit=C, device_class=TEMP, diagnostic=True, slow=True, optional=True),
    DataPoint(key="p31_max_vl_soll", scope=G, module=MT_WG, info=39, kind=Kind.SENSOR, factor=0.1, unit=C, device_class=TEMP, diagnostic=True, slow=True, optional=True),
    DataPoint(key="p32_schaltdifferenz", scope=G, module=MT_WG, info=34, kind=Kind.SENSOR, factor=0.1, unit=K, diagnostic=True, slow=True, optional=True),
    DataPoint(key="p34_taktsperre", scope=G, module=MT_WG, info=323, kind=Kind.SENSOR, unit=MIN, device_class=DURATION, diagnostic=True, slow=True, optional=True),
    DataPoint(key="p37_max_leistung_heizung", scope=G, module=MT_WG, info=319, kind=Kind.SENSOR, factor=0.1, unit=PCT, diagnostic=True, slow=True, optional=True),
    DataPoint(key="p38_max_leistung_ww", scope=G, module=MT_WG, info=345, kind=Kind.SENSOR, factor=0.1, unit=PCT, diagnostic=True, slow=True, optional=True),
    DataPoint(key="p52_max_ladezeit_ww", scope=G, module=MT_WG, info=384, kind=Kind.SENSOR, unit=MIN, device_class=DURATION, diagnostic=True, slow=True, optional=True),
    # ---------------- Heizkreis: Prozesswerte ----------------
    DataPoint(key="gemischte_aussentemperatur", scope=HK, module=MT_FS, info=2586, kind=Kind.SENSOR, factor=0.1, unit=C, device_class=TEMP, state_class=MEAS, optional=True),
    DataPoint(key="raumtemperatur", scope=HK, module=MT_FS, info=17, kind=Kind.SENSOR, factor=0.1, unit=C, device_class=TEMP, state_class=MEAS, optional=True),
    DataPoint(key="vorlaufsoll_hk", scope=HK, module=MT_FS, info=4, kind=Kind.SENSOR, factor=0.1, unit=C, device_class=TEMP, state_class=MEAS, optional=True),
    DataPoint(key="vorlaufsoll_system", scope=HK, module=MT_FS, info=2, kind=Kind.SENSOR, factor=0.1, unit=C, device_class=TEMP, state_class=MEAS, optional=True),
    DataPoint(key="vorlauftemperatur_hk", scope=HK, module=MT_MS, info=15, kind=Kind.SENSOR, factor=0.1, unit=C, device_class=TEMP, state_class=MEAS, optional=True),
    DataPoint(key="warmwassertemperatur_hk", scope=HK, module=MT_MS, info=14, kind=Kind.SENSOR, factor=0.1, unit=C, device_class=TEMP, state_class=MEAS, optional=True),
    DataPoint(key="zirkulationstemperatur", scope=HK, module=MT_MS, info=1257, kind=Kind.SENSOR, factor=0.1, unit=C, device_class=TEMP, state_class=MEAS, optional=True),
    # ---------------- Heizkreis: Benutzer (einstellbar) ----------------
    DataPoint(key="betriebsart", scope=HK, module=MT_FS, info=274, kind=Kind.SELECT, options=MODE_HK, icon="mdi:radiator"),
    DataPoint(key="normal_raumtemperatur", scope=HK, module=MT_FS, info=5, kind=Kind.NUMBER, factor=0.1, unit=C, device_class=TEMP, min_value=10, max_value=35, step=0.5, optional=True),
    DataPoint(key="absenk_raumtemperatur", scope=HK, module=MT_FS, info=8, kind=Kind.NUMBER, factor=0.1, unit=C, device_class=TEMP, min_value=10, max_value=35, step=0.5, optional=True),
    DataPoint(key="normal_vl_soll", scope=HK, module=MT_FS, info=297, kind=Kind.NUMBER, factor=0.1, unit=C, device_class=TEMP, min_value=8, max_value=85, step=1, config=True, optional=True),
    DataPoint(key="absenk_vl_soll", scope=HK, module=MT_FS, info=298, kind=Kind.NUMBER, factor=0.1, unit=C, device_class=TEMP, min_value=8, max_value=85, step=1, config=True, optional=True),
    DataPoint(key="steilheit", scope=HK, module=MT_FS, info=270, kind=Kind.NUMBER, factor=0.1, min_value=2.5, max_value=40, step=0.5, config=True, optional=True, icon="mdi:chart-line"),
    DataPoint(key="raumfrosttemperatur", scope=HK, module=MT_FS, info=2580, kind=Kind.NUMBER, factor=0.1, unit=C, device_class=TEMP, min_value=4, max_value=35, step=0.5, config=True, optional=True),
    DataPoint(key="sommer_winter_umschaltung", scope=HK, module=MT_FS, info=278, kind=Kind.NUMBER, factor=0.1, unit=C, device_class=TEMP, min_value=8, max_value=30, step=1, config=True, optional=True),
    DataPoint(key="ww_normal_soll", scope=HK, module=MT_FS, info=19, kind=Kind.NUMBER, factor=0.1, unit=C, device_class=TEMP, min_value=8, max_value=80, step=1, optional=True, icon="mdi:water-thermometer"),
    DataPoint(key="ww_absenk_soll", scope=HK, module=MT_FS, info=650, kind=Kind.NUMBER, factor=0.1, unit=C, device_class=TEMP, min_value=8, max_value=80, step=1, optional=True, icon="mdi:water-thermometer-outline"),
    DataPoint(key="ww_vorverlegung", scope=HK, module=MT_FS, info=2418, kind=Kind.NUMBER, unit=MIN, device_class=DURATION, min_value=5, max_value=270, step=5, config=True, optional=True),
    # ---------------- Heizkreis: Fachmann/Konfiguration (nur lesen) ----------------
    DataPoint(key="regelvariante", scope=HK, module=MT_FS, info=321, kind=Kind.ENUM, diagnostic=True, slow=True, optional=True, options={0: "constant_flow", 1: "weather", 2: "weather_room", 3: "room"}),
    DataPoint(key="hk_typ", scope=HK, module=MT_FS, info=2419, kind=Kind.ENUM, diagnostic=True, slow=True, optional=True, options={0: "floor_warming", 1: "floor_heating", 2: "radiator_60", 3: "radiator_75", 4: "convector", 5: "universal"}),
    DataPoint(key="reduziertbetrieb", scope=HK, module=MT_FS, info=306, kind=Kind.ENUM, diagnostic=True, slow=True, optional=True, options={0: "frost", 1: "setback"}),
    DataPoint(key="frostheizgrenze", scope=HK, module=MT_FS, info=702, kind=Kind.SENSOR, factor=0.1, unit=C, device_class=TEMP, diagnostic=True, slow=True, optional=True),
    DataPoint(key="raumthermostat", scope=HK, module=MT_FS, info=2588, kind=Kind.ENUM, diagnostic=True, slow=True, optional=True, options={0: "off", 1: "day_on", 2: "1k", 3: "2k", 4: "3k"}),
    # ---------------- Heizkreis: interne Statuswerte ----------------
    DataPoint(key="status_104", scope=HK, module=MT_FS, info=104, kind=Kind.INTERNAL, optional=True),
    DataPoint(key="status_2585", scope=HK, module=MT_FS, info=2585, kind=Kind.INTERNAL, optional=True),
)
