# WCM-COM-Protokoll

Abgeleitet aus den Skripten der Weboberfläche des WCM-COM (`/CARD/Websites/script/webApp.js` und die Seitenskripte `Form_*.js`). Nicht offiziell dokumentiert; Angaben ohne Gewähr.

## Anfrage

`POST http://<wcm-com>/parameter.json`, Body als Text:

```json
{"prot":"coco","telegramm":[[10,0,1,12,0,0,0,0],[6,1,1,274,0,0,0,0]]}
```

Ist am Modul die Benutzerverwaltung aktiv, ist HTTP-Digest-Anmeldung nötig.

## Telegramm

| Position | Bedeutung |
|---|---|
| 0 | Modultyp |
| 1 | Buskennung |
| 2 | Befehl: 1 lesen, 2 schreiben, 255 Fehler |
| 3 | Infonummer |
| 4 | Index |
| 5 | Protokoll (0 Standard, 1 generisch) |
| 6 | Low-Byte |
| 7 | High-Byte |

Werte sind vorzeichenbehaftete 16-Bit-Zahlen (`High * 256 + Low`), skaliert je Infonummer. `0x8000` und `-1000` (vom Heizkreisregler) bedeuten „Fühler nicht vorhanden“. Die Antwort enthält dieselben Telegramme mit eingesetzten Werten; nicht vorhandene Adressen fehlen. Bei vielen nicht vorhandenen Adressen in einer Anfrage kann die Antwort komplett leer sein.

Schreiben: dasselbe Telegramm mit Befehl 2 und dem Rohwert in Byte 6/7.

## Modultypen

| Typ | Gerät |
|---|---|
| 0 | direkt (WCM-COM selbst, Bus-Scan) |
| 3 | Kessel / WCM-SOL |
| 6 | Fernbedienung WCM-FS / Bedieneinheit (Heizkreis) |
| 7 | Ein-/Ausgangsmodul |
| 9 | WCM-KA (Kaskade) |
| 10 | Wärmeerzeuger WTC-G / WTC-O |
| 12 | Mischer |

## Bus-Scan

| Infonummer (Modul 0) | Inhalt |
|---|---|
| 4983 | WCM-SOL vorhanden (Softwarenummer 342) |
| 4984 | WCM-KA vorhanden (Softwarenummer 266) |
| 4985 | Wärmeerzeuger: `[…, Anzahl, Busk1, SW1, Busk2, SW2, …]` |
| 4986 | Heizkreise: `[…, Anzahl, Busk1, SW1, …]` |

Die Weboberfläche zählt Heizkreise ab 1: Buskennung 1 = „Heizkreis 2“. Softwarenummern 61488/61489/61491/61492 = WTC-G, 61490/61493 = WTC-O.

## Wärmeerzeuger (Modul 10)

| Infonummer | Bedeutung | Faktor |
|---|---|---|
| 1 | Fehlercode | 1 |
| 2 | Wärmeanforderung | 0,1 °C |
| 12 | Außentemperatur | 0,1 °C |
| 13 | Kesseltemperatur | 0,1 °C |
| 14 | Warmwassertemperatur | 0,1 °C |
| 81 / 82 / 83 | Flamme / Heizbetrieb / Warmwasserbetrieb | 0/1 |
| 118 | Pufferfühler B10 | 0,1 °C |
| 138 | Laststellung | % |
| 325 | Abgastemperatur | 0,1 °C |
| 373 | Betriebsphase | 1 |
| 466 | Kesselpumpe | 0/1 |
| 700 | Zeit seit Wartung | 10 h |
| 1497 / 1498 | Gasventil 1 / 2 | 0/1 |
| 2572 | Gedämpfte Außentemperatur | 0,1 °C |
| 3101 | Vorlauftemperatur (eSTB) | 0,1 °C |
| 3158 | Brennerstarts | 1000 |
| 3159 | Betriebsstunden Brenner | 100 h |

Fachmann (in der Weboberfläche einstellbar, hier nur gelesen): 3102 P18 Sonderniveau (°C), 3103 P20 Außenfühler-Korrektur (K), 2560 P23 Anlagenfrostschutz (0,1 °C), 31 P30 Min. VL-Soll (0,1 °C), 39 P31 Max. VL-Soll (0,1 °C), 34 P32 Schaltdifferenz (0,1 K), 323 P34 Taktsperre (min), 319 P37 / 345 P38 Max. Leistung Heizung / WW (0,1 %), 384 P52 Max. WW-Ladezeit (min).

## Heizkreis (Modul 6, Mischerwerte Modul 12)

Seite „Benutzer“ – einstellbar:

| Infonummer | Bedeutung | Faktor | Bereich |
|---|---|---|---|
| 274 | Betriebsart | – | 1 Standby, 3 Normal, 4 Absenk, 5 Sommer, 11/12/13 Programm 1–3, 255 wie Leitstelle |
| 5 / 8 | Normal- / Absenk-Raumtemperatur | 0,1 °C | 10–35, Schritt 0,5 |
| 297 / 298 | Normal- / Absenk-VL-Soll | 0,1 °C | 8–85 |
| 270 | Steilheit | 0,1 | 2,5–40, Schritt 0,5 |
| 2580 | Raumfrosttemperatur | 0,1 °C | 4–35, Schritt 0,5 |
| 278 | Sommer/Winter-Umschaltung | 0,1 °C | 8–30 |
| 19 / 650 | Normal- / Absenk-WW-Soll | 0,1 °C | 8–80 |
| 2418 | Vorverlegung | min | 5–270, Schritt 5 |

Ist in Infonummer 104 Bit `0x40` gesetzt und die Buskennung nicht 0, steht 274 für die Warmwasser-Betriebsart (1 Standby, 3 Normal, 4 Absenk, 11 WW-Programm, 255 wie Leitstelle). 2585 = 1 oder 2 gibt die Warmwasser-Sollwerte frei.

Prozesswerte: 2586 gemischte Außentemperatur, 17 Raumtemperatur, 4 Vorlauf-Soll des Heizkreises, 2 Vorlauf-Soll System (Modul 6); 15 Vorlauf, 14 Warmwasser, 1257 Zirkulation (Modul 12) – jeweils 0,1 °C.

Konfiguration/Fachmann: 321 Regelvariante (0 Konstantvorlauf, 1 Witterung, 2 Witterung/Raum, 3 Raum), 2419 Heizkreis-Typ, 306 Reduziertbetrieb, 702 Frostheizgrenze, 2588 Raumthermostat.

## Eigenheiten des Moduls

- Nur ein angemeldeter Client gleichzeitig; ein offener Browser-Tab blockiert andere Zugriffe.
- Bei Last: HTTP 200 mit HTML-Seite „Sorry, the server is busy“, Nullbytes oder abgeschnittenes JSON.
- Parallele Anfragen vermeiden; zwischen Anfragen kurz pausieren.
