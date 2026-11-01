"""Konstanten für die Weishaupt-WCM-COM-Integration."""

from __future__ import annotations

DOMAIN = "weishaupt_wcm"

CONF_SCAN_INTERVAL = "scan_interval"
CONF_GENERATORS = "generators"  # Liste [Buskennung, Softwarenummer]
CONF_CIRCUITS = "circuits"  # Liste [Buskennung, Softwarenummer]

DEFAULT_SCAN_INTERVAL = 60
MIN_SCAN_INTERVAL = 30
MAX_SCAN_INTERVAL = 3600

# Langsame Werte (Fachmann-/Konfigurationsparameter) nur jede n-te Abfrage lesen
SLOW_POLL_EVERY = 10

# Modultypen laut Weboberfläche (webApp.js, TEL_MTYPE_*)
MT_DIRECT = 0
MT_FS = 6  # Fernbedienung / Bedieneinheit (Heizkreis)
MT_WG = 10  # Wärmeerzeuger WTC-G / WTC-O
MT_MS = 12  # Mischer

# Bus-Scan-Infonummern (Menu_Waermeerzeuger.js / Menu_Heizkreise.js)
INFO_SCAN_GENERATORS = 4985
INFO_SCAN_CIRCUITS = 4986

# Softwarenummern laut Menu_Waermeerzeuger.js
SW_WTC_G = {61492, 61491, 61489, 61488}
SW_WTC_O = {61493, 61490}

MANUFACTURER = "Weishaupt"
