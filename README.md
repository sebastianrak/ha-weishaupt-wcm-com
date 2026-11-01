# Weishaupt WCM-COM für Home Assistant

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz/docs/faq/custom_repositories/)
[![Validate](https://github.com/sebastianrak/ha-weishaupt-wcm-com/actions/workflows/validate.yml/badge.svg)](https://github.com/sebastianrak/ha-weishaupt-wcm-com/actions/workflows/validate.yml)
[![Tests](https://github.com/sebastianrak/ha-weishaupt-wcm-com/actions/workflows/tests.yml/badge.svg)](https://github.com/sebastianrak/ha-weishaupt-wcm-com/actions/workflows/tests.yml)

Lokale Anbindung von Weishaupt-Heizungen über das Kommunikationsmodul **WCM-COM 1.0 home**. Die Integration liest Kessel und Heizkreise über die `parameter.json`-Schnittstelle des Moduls aus und kann die Werte setzen, die auch die Weboberfläche auf der Seite „Benutzer“ anbietet. Ohne Cloud, ohne zusätzliche Hardware.

> **Hinweis:** Dies ist kein Produkt der Max Weishaupt SE und wird von Weishaupt weder unterstützt noch geprüft. Das Protokoll ist nicht offiziell dokumentiert; es wurde aus der Weboberfläche des Moduls abgeleitet. Schreibzugriffe wirken direkt auf die Heizung. Nutzung auf eigene Gefahr – insbesondere bei Warmwassertemperaturen (Legionellenschutz).

*English summary below.*

## Funktionen

- Einrichtung komplett über die Oberfläche, mit Bus-Scan: Wärmeerzeuger und Heizkreise werden automatisch erkannt.
- **Wärmeerzeuger (WTC-G / WTC-O):** Außen-, gedämpfte Außen-, Vorlauf-, Kessel-, Abgas- und Warmwassertemperatur, Wärmeanforderung, Laststellung, Betriebsphase, Fehlercode, Flamme, Gasventile, Kesselpumpe, Heiz-/Warmwasserbetrieb, Störung, Brennerstarts, Betriebsstunden, Zeit seit Wartung. Fachmann-Parameter (P18–P52) nur lesend als Diagnose.
- **Heizkreis (WCM-FS):** Betriebsart (Auswahl), Normal-/Absenk-Raumtemperatur, Warmwasser-Sollwerte, Normal-/Absenk-Vorlaufsoll, Steilheit, Raumfrost, Sommer/Winter-Umschaltung, Vorverlegung (einstellbar); Ist- und Sollwerte, Regelvariante, Heizkreis-Typ (lesend).
- Werte, die das eigene Gerät nicht liefert (z. B. fehlender Raumfühler), werden nicht angelegt.
- Robust gegen die Eigenheiten des Moduls: alle Zugriffe nacheinander, Wiederholung bei „server is busy“, Nullbytes und abgeschnittenem JSON, kurze Aussetzer werden überbrückt.
- Schalter **„Abfrage pausieren“**: Das WCM-COM erlaubt nur einen angemeldeten Client. Solange Home Assistant abfragt, ist die Weboberfläche gesperrt. Pausieren gibt sie frei (Schreiben ist dann gesperrt).
- Deutsch und Englisch.

## Voraussetzungen

- Weishaupt WCM-COM 1.0 home im lokalen Netz (eBUS-Anbindung an den Wärmeerzeuger)
- Home Assistant 2026.10 oder neuer (automatisierte Tests laufen gegen 2026.10.4)
- Bei aktivierter Benutzerverwaltung am WCM-COM: Benutzername und Passwort (Digest-Anmeldung)

Entwickelt an einer Anlage mit WTC-G und einem Heizkreis-Regler WCM-FS (Softwarestand 327). Rückmeldungen zu anderen Anlagen sind willkommen.

## Installation

### HACS (empfohlen)

1. HACS → ⋮ → *Benutzerdefinierte Repositories* → `https://github.com/sebastianrak/ha-weishaupt-wcm-com`, Kategorie *Integration*.
2. „Weishaupt WCM-COM“ installieren und Home Assistant neu starten.

### Manuell

Ordner `custom_components/weishaupt_wcm` nach `<config>/custom_components/weishaupt_wcm` kopieren und Home Assistant neu starten.

## Einrichtung

1. Vorher in der Weboberfläche des WCM-COM abmelden und den Browser-Tab schließen.
2. *Einstellungen → Geräte & Dienste → Integration hinzufügen → Weishaupt WCM-COM*.
3. IP-Adresse, ggf. Benutzername und Passwort eingeben. Die Integration führt einen Bus-Scan aus und legt je Gerät ein Gerät in Home Assistant an.

Unter *Konfigurieren* lässt sich das Abfrageintervall ändern (Standard 60 s, 30–3600 s). Fachmann-Parameter werden nur bei jeder zehnten Abfrage gelesen.

## Dashboard-Beispiel

Eine Karte nur mit Standardkarten liegt unter [`examples/dashboard-karte.yaml`](examples/dashboard-karte.yaml). Die Entitäts-IDs hängen von der Systemsprache ab (Deutsch: `sensor.warmeerzeuger_…`, `select.heizkreis_2_…`; Englisch: `sensor.heat_generator_…`, `select.heating_circuit_2_…`).

Ob die Auswahl als „Betriebsart“ oder „Betriebsart Warmwasser“ erscheint, ergibt sich aus dem Regler selbst (Infonummer 104, Bit 0x40), genau wie in der Weboberfläche.

## Wie es funktioniert

Die Weboberfläche des WCM-COM schickt JSON-Telegramme per `POST /parameter.json`:

```json
{"prot":"coco","telegramm":[[10,0,1,12,0,0,0,0]]}
```

Aufbau: `[Modultyp, Buskennung, Befehl, Infonummer, Index, Protokoll, LowByte, HighByte]`, Befehl 1 = lesen, 2 = schreiben. Details, Modultypen und alle verwendeten Infonummern stehen in [`docs/protokoll.md`](docs/protokoll.md).

## Logo

Home Assistant (geprüft mit 2026.10) zeigt Logos eigener Integrationen aus dem Ordner `custom_components/weishaupt_wcm/brand/` an (`icon.png` 256×256, optional `icon@2x.png` 512×512, `logo.png`, `dark_icon.png`, `dark_logo.png`). Das Repository enthält bewusst kein Herstellerlogo; das Weishaupt-Logo ist eine Marke der Max Weishaupt SE.

## Danksagung

Ohne die Vorarbeit anderer wäre das nicht entstanden:

- [ThomasKeller/HomeAssistant-Weishaupt](https://github.com/ThomasKeller/HomeAssistant-Weishaupt) – robuste Behandlung der „busy“-Antworten, Datenlogger
- [B-o-r-i-s-M/Weishaupt-WTC-OB-ebusd-Home-Assistant](https://github.com/B-o-r-i-s-M/Weishaupt-WTC-OB-ebusd-Home-Assistant) – Parametertabellen, eBUS-Protokoll
- [lairsdragon/nodered-weishaupt](https://github.com/lairsdragon/nodered-weishaupt) und [blog.weinreich.org](https://blog.weinreich.org/posts/2018/2018-12-27_weisshaupt_heizungssteurung/) – erste Lese- und Schreibtelegramme

## Lizenz

MIT, siehe [LICENSE](LICENSE).

---

## English summary

Local Home Assistant integration for Weishaupt heating systems with the **WCM-COM 1.0 home** communication module. It discovers the heat generator and heating circuits via a bus scan, exposes process values as sensors and binary sensors, and lets you set the values the module's own web interface offers on its "user" page (operating mode, room and hot water setpoints, heating curve, …). No cloud, no extra hardware.

Install via HACS (custom repository `https://github.com/sebastianrak/ha-weishaupt-wcm-com`, category *Integration*) or copy `custom_components/weishaupt_wcm` manually, restart, then add *Weishaupt WCM-COM* under *Settings → Devices & services*. Log out of the WCM-COM web interface first: the module accepts only one client at a time. Use the *Pause polling* switch to free the web interface temporarily.

Not affiliated with or endorsed by Max Weishaupt SE. The protocol is undocumented; writing values affects your heating system directly. Use at your own risk.
