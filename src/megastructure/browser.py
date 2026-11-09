"""The game inside a browser tab (the GitHub Pages demo): the real server runs under Pyodide and the client's
sockets are in-page objects instead of websockets. Loaded by web/js/local.js; never imported by the server."""

import asyncio
import sys
import types
from pathlib import Path


def _stub_native():
    """Modules the server imports that don't exist (or aren't needed) in the browser."""
    ws = types.ModuleType("websockets")
    for name, attrs in {"asyncio": {}, "asyncio.server": {"serve": None}, "exceptions": {"ConnectionClosed": ConnectionError},
                        "datastructures": {"Headers": None}, "http11": {"Response": None}}.items():
        mod = types.ModuleType("websockets." + name)
        mod.__dict__.update(attrs)
        sys.modules["websockets." + name] = mod
    sys.modules["websockets"] = ws
    if "resource" not in sys.modules:
        res = types.ModuleType("resource")
        res.RUSAGE_SELF = 0
        res.getrusage = lambda _who: types.SimpleNamespace(ru_maxrss=0)
        sys.modules["resource"] = res


_stub_native()
from .server import GameServer  # noqa: E402


class Socket:
    """One client connection: the page pushes messages into `inbox`, the server's sends go to `deliver`."""

    def __init__(self, path: str, deliver, closed):
        self.request = types.SimpleNamespace(path=path)
        self.remote_address = "this tab"
        self.inbox: asyncio.Queue = asyncio.Queue()
        self.deliver, self.closed = deliver, closed

    def push(self, raw: str):
        self.inbox.put_nowait(raw)

    async def send(self, raw: str):
        self.deliver(raw)

    def shut(self):
        self.inbox.put_nowait(None)

    async def close(self, *_):
        self.shut()

    def __aiter__(self):
        return self

    async def __anext__(self):
        raw = await self.inbox.get()
        if raw is None:
            raise StopAsyncIteration
        return raw


game: GameServer | None = None


def start(saves: str) -> int:
    """Open (or create) the demo world in `saves` and start ticking; returns the tick it resumes at."""
    global game
    game = GameServer(Path(saves) / "demo")
    asyncio.ensure_future(game.tick_loop())
    return game.sim.tick


def connect(path: str, deliver, closed) -> Socket:
    ws = Socket(path, deliver, closed)

    async def run():
        try:
            await game.handler(ws)
        finally:
            closed()

    asyncio.ensure_future(run())
    return ws


def save():
    """Write everything to the database (the page then syncs it to IndexedDB)."""
    if game is not None:
        game.sim.flush()
