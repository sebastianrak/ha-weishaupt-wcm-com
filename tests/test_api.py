"""Tests des Protokoll-Clients gegen ein simuliertes WCM-COM (inkl. Digest-Auth)."""

import asyncio
import hashlib
import json
import re

import httpx
import pytest

from custom_components.weishaupt_wcm import api

USER, PW, REALM, NONCE = "wcm", "geheim", "WCM-COM", "abc123"

VALUES = {
    (10, 0, 12): 40, (10, 0, 14): 540, (10, 0, 2): 410, (10, 0, 13): 400,
    (10, 0, 118): -32768,  # Fühler nicht vorhanden
    (10, 0, 3103): -2,
    (6, 1, 274): 11, (6, 1, 5): 210,
    (6, 1, 17): -1000,  # Raumfühler fehlt (Kennung des WCM-FS)
}


class FakeWcm:
    """Simuliert das beobachtete Verhalten des WCM-COM."""

    def __init__(self) -> None:
        self.busy = 0
        self.nul = False
        self.requests = 0
        self.writes: list[tuple[int, int, int, int]] = []

    def _check_digest(self, header: str, uri: str) -> bool:
        parts = dict(re.findall(r'(\w+)="?([^",]+)"?', header))
        ha1 = hashlib.md5(f"{USER}:{REALM}:{PW}".encode()).hexdigest()
        ha2 = hashlib.md5(f"POST:{uri}".encode()).hexdigest()
        expected = hashlib.md5(
            f"{ha1}:{parts['nonce']}:{parts['nc']}:{parts['cnonce']}:{parts['qop']}:{ha2}".encode()
        ).hexdigest()
        return parts.get("username") == USER and parts.get("response") == expected

    def handler(self, request: httpx.Request) -> httpx.Response:
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Digest ") or not self._check_digest(auth, request.url.path):
            return httpx.Response(
                401,
                headers={"WWW-Authenticate": f'Digest realm="{REALM}", nonce="{NONCE}", qop="auth"'},
            )
        self.requests += 1
        if self.busy:
            self.busy -= 1
            return httpx.Response(200, text="<HTML><BODY>Sorry, the server is busy.</BODY></HTML>")
        out, unknown = [], 0
        for t in json.loads(request.content)["telegramm"]:
            m, b, cmd, n = t[0], t[1], t[2], t[3]
            if m == 0 and n == 4985:
                out.append([0, 0, 1, 4985, 0, 1, 1, 0, 61491])
            elif m == 0 and n == 4986:
                out.append([0, 0, 1, 4986, 0, 1, 1, 1, 327])
            elif cmd == 2:
                self.writes.append((m, b, n, t[6] | (t[7] << 8)))
                out.append([m, b, 2, n, 0, 0, t[6], t[7]])
            elif (m, b, n) in VALUES:
                v = VALUES[(m, b, n)] & 0xFFFF
                out.append([m, b, 1, n, 0, 0, v & 0xFF, v >> 8])
            else:
                unknown += 1
        if unknown > 5:  # beobachtet: viele unbekannte Adressen -> leere Antwort
            out = []
        text = json.dumps({"prot": "coco", "telegramm": out}) + ("\x00" * 30 if self.nul else "")
        return httpx.Response(200, text=text)


@pytest.fixture
def fake(monkeypatch):
    monkeypatch.setattr(api, "RETRY_DELAYS", (0.0, 0.0))
    monkeypatch.setattr(api, "PAUSE_BETWEEN_REQUESTS", 0.0)
    return FakeWcm()


def _client(fake: FakeWcm, password: str = PW) -> api.WcmClient:
    http = httpx.AsyncClient(transport=httpx.MockTransport(fake.handler))
    return api.WcmClient(http, "wcm.local", USER, password)


async def test_scan(fake) -> None:
    scan = await _client(fake).scan()
    assert scan.generators == [(0, 61491)]
    assert scan.circuits == [(1, 327)]


async def test_read_values(fake) -> None:
    r = await _client(fake).read(
        [(10, 0, 12), (10, 0, 14), (10, 0, 118), (10, 0, 3103), (6, 1, 274), (6, 1, 17)]
    )
    assert r[(10, 0, 12)] == 40
    assert r[(10, 0, 14)] == 540
    assert r[(10, 0, 118)] is None
    assert r[(10, 0, 3103)] == -2
    assert r[(6, 1, 274)] == 11
    assert r[(6, 1, 17)] is None


async def test_busy_then_ok(fake) -> None:
    fake.busy = 2
    assert (await _client(fake).read([(10, 0, 12)]))[(10, 0, 12)] == 40


async def test_busy_forever(fake) -> None:
    fake.busy = 10
    with pytest.raises(api.WcmBusyError):
        await _client(fake).read([(10, 0, 12)])


async def test_nul_bytes(fake) -> None:
    fake.nul = True
    assert (await _client(fake).read([(10, 0, 12)]))[(10, 0, 12)] == 40


async def test_empty_reply_is_split(fake) -> None:
    keys = [(6, 0, n) for n in range(300, 310)] + [(6, 1, 274), (6, 1, 5)]
    r = await _client(fake).read(keys)
    assert r == {(6, 1, 274): 11, (6, 1, 5): 210}


async def test_write(fake) -> None:
    client = _client(fake)
    await client.write((6, 1, 5), 215)
    await client.write((10, 0, 3103), -2)
    assert fake.writes == [(6, 1, 5, 215), (10, 0, 3103, 0xFFFE)]


async def test_wrong_password(fake) -> None:
    with pytest.raises(api.WcmAuthError):
        await _client(fake, "falsch").scan()


async def test_requests_are_serialized(fake) -> None:
    client = _client(fake)
    await asyncio.gather(client.read([(10, 0, 12)]), client.read([(10, 0, 14)]), client.scan())
    assert fake.requests == 3


def test_decode_encode() -> None:
    assert api.decode(*api.encode(-55)) == -55
    assert api.decode(0, 0x80) is None
    assert api.decode(*api.encode(-1000)) is None
    with pytest.raises(ValueError):
        api.encode(40000)
