"""DataUpdateCoordinator für das WCM-COM."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import Key, WcmBusyError, WcmClient, WcmError
from .const import DOMAIN, SLOW_POLL_EVERY
from .datapoints import DATAPOINTS, DataPoint, Scope

_LOGGER = logging.getLogger(__name__)

# So oft darf eine Abfrage scheitern bzw. ein Wert fehlen, bevor die Entitäten
# "nicht verfügbar" werden. Das WCM-COM liefert gelegentlich 'busy' oder Teilantworten.
MAX_FAILED_POLLS = 3
MAX_MISSING = 3
WRITE_READBACK_DELAY = 3.0


@dataclass(frozen=True)
class BoundPoint:
    """Datenpunkt, gebunden an ein konkretes Gerät am Bus."""

    point: DataPoint
    busk: int

    @property
    def key(self) -> Key:
        return (self.point.module, self.busk, self.point.info)

    @property
    def device_id(self) -> str:
        prefix = "wg" if self.point.scope is Scope.GENERATOR else "hk"
        return f"{prefix}_{self.busk}"


def bind_points(generators: list[int], circuits: list[int]) -> list[BoundPoint]:
    """Datenpunkte für alle gefundenen Geräte erzeugen."""
    bound: list[BoundPoint] = []
    for point in DATAPOINTS:
        busks = generators if point.scope is Scope.GENERATOR else circuits
        bound.extend(BoundPoint(point, busk) for busk in busks)
    return bound


type WcmConfigEntry = ConfigEntry[WcmCoordinator]


class WcmCoordinator(DataUpdateCoordinator[dict[Key, int | None]]):
    """Fragt alle Werte gebündelt und nacheinander ab."""

    config_entry: WcmConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        entry: WcmConfigEntry,
        client: WcmClient,
        points: list[BoundPoint],
        scan_interval: int,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )
        self.client = client
        self.points = points
        self.paused = False
        self.hub_device_id: str | None = None
        self.present: set[Key] = set()
        self._probed = False
        self._cycle = 0
        self._failed_polls = 0
        self._missing: dict[Key, int] = {}

    def value(self, key: Key) -> int | None:
        return (self.data or {}).get(key)

    def is_present(self, bound: BoundPoint) -> bool:
        """Optionale Punkte nur, wenn sie beim ersten Abruf einen Wert hatten."""
        return not bound.point.optional or bound.key in self.present

    def _keys_for_cycle(self) -> list[Key]:
        slow_cycle = self._cycle % SLOW_POLL_EVERY == 0
        keys: list[Key] = []
        for bound in self.points:
            if bound.point.optional and bound.key not in self.present:
                continue
            if bound.point.slow and not slow_cycle:
                continue
            if bound.key not in keys:
                keys.append(bound.key)
        return keys

    async def _probe(self) -> dict[Key, int | None]:
        """Erster Abruf: Pflichtwerte und optionale Werte getrennt abfragen."""
        required: list[Key] = []
        optional: list[Key] = []
        for bound in self.points:
            target = optional if bound.point.optional else required
            if bound.key not in target:
                target.append(bound.key)
        values = await self.client.read(required) if required else {}
        if optional:
            opt_values = await self.client.read(optional)
            self.present = {k for k, v in opt_values.items() if v is not None}
            values.update({k: v for k, v in opt_values.items() if k in self.present})
        _LOGGER.debug(
            "Erster Abruf: %d Pflichtwerte, %d von %d optionalen Werten vorhanden",
            len(required),
            len(self.present),
            len(optional),
        )
        return values

    async def _async_update_data(self) -> dict[Key, int | None]:
        if self.paused and self.data is not None:
            return self.data

        try:
            if not self._probed:
                values = await self._probe()
                self._probed = True
                keys = list(values)
            else:
                keys = self._keys_for_cycle()
                values = await self.client.read(keys)
        except WcmBusyError as err:
            self._failed_polls += 1
            if self.data is not None and self._failed_polls < MAX_FAILED_POLLS:
                _LOGGER.debug("WCM-COM belegt (%s), behalte letzte Werte", err)
                return self.data
            raise UpdateFailed(f"WCM-COM antwortet nicht verwertbar: {err}") from err
        except WcmError as err:
            self._failed_polls += 1
            raise UpdateFailed(f"Abfrage fehlgeschlagen: {err}") from err

        self._failed_polls = 0
        self._cycle += 1
        data = dict(self.data or {})
        for key in keys:
            if key in values:
                data[key] = values[key]
                self._missing[key] = 0
            else:
                self._missing[key] = self._missing.get(key, 0) + 1
                if self._missing[key] >= MAX_MISSING:
                    data[key] = None
        return data

    async def async_write(self, bound: BoundPoint, raw: int) -> None:
        """Wert schreiben und lokal übernehmen; danach frisch lesen."""
        if self.paused:
            raise WcmError("Abfrage ist pausiert, Schreiben gesperrt")
        await self.client.write(bound.key, raw)
        data = dict(self.data or {})
        data[bound.key] = raw
        self.async_set_updated_data(data)
        # Der Regler übernimmt den Wert nicht sofort; kurz warten, dann zurücklesen.
        self.config_entry.async_create_background_task(
            self.hass, self._delayed_refresh(), f"{DOMAIN}_refresh_after_write"
        )

    async def _delayed_refresh(self) -> None:
        await asyncio.sleep(WRITE_READBACK_DELAY)
        await self.async_request_refresh()
