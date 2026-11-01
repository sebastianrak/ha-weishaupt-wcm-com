"""Client für die lokale parameter.json-Schnittstelle (Protokoll "coco") des WCM-COM.

Telegrammaufbau laut webApp.js der Weboberfläche:
    [Modultyp, Buskennung, Befehl, Infonummer, Index, Protokoll, LowByte, HighByte]
Befehl 1 = lesen, 2 = schreiben, 255 = Fehler. Werte sind vorzeichenbehaftete
16-Bit-Zahlen; 0x8000 und -1000 bedeuten "Fühler nicht vorhanden"
(-1000 liefert der Heizkreisregler, beobachtet am WCM-FS 327).

Diese Datei hat keine Home-Assistant-Abhängigkeit und lässt sich separat testen.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
import json
import logging

import httpx

_LOGGER = logging.getLogger(__name__)

CMD_READ = 1
CMD_WRITE = 2
CMD_ERROR = 255

MAX_TELEGRAMS_PER_REQUEST = 20
SPLIT_CHUNK_SIZE = 4
PAUSE_BETWEEN_REQUESTS = 1.0
RETRY_DELAYS = (2.0, 4.0)
REQUEST_TIMEOUT = 20.0

INFO_SCAN_GENERATORS = 4985
INFO_SCAN_CIRCUITS = 4986

# (Modultyp, Buskennung, Infonummer)
type Key = tuple[int, int, int]


class WcmError(Exception):
    """Basisfehler."""


class WcmConnectionError(WcmError):
    """Gerät nicht erreichbar."""


class WcmAuthError(WcmError):
    """Anmeldung abgelehnt."""


class WcmBusyError(WcmError):
    """Gerät meldet 'server is busy' oder liefert Müll."""


class WcmProtocolError(WcmError):
    """Antwort nicht verwertbar oder Befehl abgelehnt."""


NOT_AVAILABLE = frozenset({-0x8000, -1000})


def decode(low: int, high: int) -> int | None:
    """Zwei Bytes in einen vorzeichenbehafteten Wert wandeln (None = nicht vorhanden)."""
    value = (low & 0xFF) | ((high & 0xFF) << 8)
    if value >= 0x8000:
        value -= 0x10000
    if value in NOT_AVAILABLE:
        return None
    return value


def encode(value: int) -> tuple[int, int]:
    """Vorzeichenbehafteten Wert in Low-/High-Byte wandeln."""
    if not -0x7FFF <= value <= 0x7FFF:
        raise ValueError(f"Wert {value} außerhalb des 16-Bit-Bereichs")
    if value < 0:
        value += 0x10000
    return value & 0xFF, (value >> 8) & 0xFF


@dataclass
class ScanResult:
    """Ergebnis des Bus-Scans: Listen aus (Buskennung, Softwarenummer)."""

    generators: list[tuple[int, int]] = field(default_factory=list)
    circuits: list[tuple[int, int]] = field(default_factory=list)


class WcmClient:
    """Serialisierter Zugriff auf das WCM-COM (verträgt keine Parallelzugriffe)."""

    def __init__(
        self,
        client: httpx.AsyncClient,
        host: str,
        username: str | None,
        password: str | None,
    ) -> None:
        self._client = client
        self._url = f"http://{host}/parameter.json"
        self._auth = httpx.DigestAuth(username, password or "") if username else None
        self._lock = asyncio.Lock()

    async def _post(self, telegrams: list[list[int]]) -> list[list[int]]:
        """Eine Anfrage senden; bei 'busy' oder Müll bis zu zweimal wiederholen."""
        body = json.dumps({"prot": "coco", "telegramm": telegrams}, separators=(",", ":"))
        last_err: WcmError = WcmConnectionError("keine Antwort")
        for attempt in range(len(RETRY_DELAYS) + 1):
            if attempt:
                await asyncio.sleep(RETRY_DELAYS[attempt - 1])
            try:
                resp = await self._client.post(
                    self._url,
                    content=body,
                    headers={"Content-Type": "text/plain;charset=UTF-8"},
                    auth=self._auth,
                    timeout=REQUEST_TIMEOUT,
                )
            except httpx.HTTPError as err:
                last_err = WcmConnectionError(f"{type(err).__name__}: {err}")
                continue
            if resp.status_code in (401, 403):
                raise WcmAuthError(f"HTTP {resp.status_code}")
            if resp.status_code != 200:
                last_err = WcmConnectionError(f"HTTP {resp.status_code}")
                continue
            text = resp.content.decode("utf-8", errors="replace").replace("\x00", "").strip()
            if not text:
                last_err = WcmBusyError("leere Antwort")
                continue
            if text.startswith("<"):
                if "busy" in text.lower():
                    last_err = WcmBusyError("server is busy")
                else:
                    last_err = WcmProtocolError(f"HTML statt JSON: {text[:80]}")
                continue
            try:
                data = json.loads(text)
            except ValueError:
                last_err = WcmBusyError("abgeschnittenes oder ungültiges JSON")
                continue
            telegram_list = data.get("telegramm") if isinstance(data, dict) else None
            if not isinstance(telegram_list, list):
                last_err = WcmProtocolError("Feld 'telegramm' fehlt")
                continue
            return [
                t
                for t in telegram_list
                if isinstance(t, list) and t and all(isinstance(x, int) for x in t)
            ]
        raise last_err

    async def _read_chunk(self, chunk: list[Key]) -> dict[Key, int | None]:
        wanted = set(chunk)
        telegrams = await self._post([[m, b, CMD_READ, n, 0, 0, 0, 0] for (m, b, n) in chunk])
        result: dict[Key, int | None] = {}
        for t in telegrams:
            if len(t) != 8 or t[2] != CMD_READ or t[4] != 0:
                continue
            key = (t[0], t[1], t[3])
            if key in wanted:
                result[key] = decode(t[6], t[7])
        return result

    async def read(self, keys: list[Key]) -> dict[Key, int | None]:
        """Werte lesen. Fehlende Werte fehlen im Ergebnis, 0x8000 ergibt None."""
        result: dict[Key, int | None] = {}
        async with self._lock:
            first = True
            for i in range(0, len(keys), MAX_TELEGRAMS_PER_REQUEST):
                chunk = keys[i : i + MAX_TELEGRAMS_PER_REQUEST]
                if not first:
                    await asyncio.sleep(PAUSE_BETWEEN_REQUESTS)
                first = False
                part = await self._read_chunk(chunk)
                if not part and len(chunk) > SPLIT_CHUNK_SIZE:
                    # Beobachtet: eine Anfrage mit vielen nicht vorhandenen Adressen
                    # kommt komplett leer zurück. Dann in kleinen Stücken nachfragen.
                    _LOGGER.debug("Leere Antwort auf %d Telegramme, frage einzeln nach", len(chunk))
                    for j in range(0, len(chunk), SPLIT_CHUNK_SIZE):
                        await asyncio.sleep(PAUSE_BETWEEN_REQUESTS)
                        part.update(await self._read_chunk(chunk[j : j + SPLIT_CHUNK_SIZE]))
                result.update(part)
        return result

    async def write(self, key: Key, raw: int) -> None:
        """Einen Rohwert schreiben (wie der Button 'Übernehmen' der Weboberfläche)."""
        module, busk, info = key
        low, high = encode(raw)
        async with self._lock:
            telegrams = await self._post([[module, busk, CMD_WRITE, info, 0, 0, low, high]])
        for t in telegrams:
            if len(t) >= 4 and (t[0], t[1], t[3]) == key and t[2] == CMD_ERROR:
                raise WcmProtocolError(f"Schreiben von {info} abgelehnt")

    async def scan(self) -> ScanResult:
        """Bus-Scan wie die Menüs 'Wärmeerzeuger' und 'Heizkreise'."""
        async with self._lock:
            telegrams = await self._post(
                [
                    [0, 0, CMD_READ, INFO_SCAN_GENERATORS, 0, 0, 0, 0],
                    [0, 0, CMD_READ, INFO_SCAN_CIRCUITS, 0, 0, 0, 0],
                ]
            )
        result = ScanResult()
        for t in telegrams:
            # Antwortformat: [0, 0, 1, Info, 0, Prot, Anzahl, Busk1, SW1, Busk2, SW2, ...]
            if len(t) < 7 or t[0] != 0 or t[2] != CMD_READ:
                continue
            count = t[6]
            pairs = [
                (t[7 + 2 * i], t[8 + 2 * i]) for i in range(count) if 8 + 2 * i < len(t)
            ]
            if t[3] == INFO_SCAN_GENERATORS:
                result.generators = pairs
            elif t[3] == INFO_SCAN_CIRCUITS:
                result.circuits = pairs
        return result
