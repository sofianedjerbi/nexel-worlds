"""Chunked tile world with lazy load/unload and SQLite persistence."""

import json
import sqlite3
import sys
import zlib
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from .gen import CHUNK, RAMP, gen_chunk, gen_tile
from .tiles import BLOCKS, GROUNDS, B, G

THREADS = sys.platform != "emscripten"   # the in-browser demo has no threads: it generates land inline
GEN_TICKS = 3                            # land generated in the background arrives this many ticks after it's asked for

SCHEMA = """
CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS chunks(cx INTEGER, cy INTEGER, data BLOB, PRIMARY KEY(cx, cy));
CREATE TABLE IF NOT EXISTS tile_meta(x INTEGER, y INTEGER, json TEXT, PRIMARY KEY(x, y));
CREATE TABLE IF NOT EXISTS agents(id INTEGER PRIMARY KEY, name TEXT UNIQUE, token_hash TEXT, json TEXT);
CREATE TABLE IF NOT EXISTS ground_items(x INTEGER, y INTEGER, json TEXT, PRIMARY KEY(x, y));
CREATE TABLE IF NOT EXISTS creatures(id INTEGER PRIMARY KEY, json TEXT);
"""


class Chunk:
    __slots__ = ("cx", "cy", "ground", "block", "level", "dirty", "touched")

    def __init__(self, cx, cy, ground, block, level=None):
        self.cx, self.cy = cx, cy
        self.ground, self.block = ground, block
        self.level = level if level is not None else bytearray(CHUNK * CHUNK)   # heights (gen.RAMP flags stairs)
        self.dirty = False
        self.touched = 0

    def pack(self) -> bytes:
        return zlib.compress(bytes(self.ground) + bytes(self.block) + bytes(self.level), 6)

    @classmethod
    def unpack(cls, cx, cy, data: bytes) -> "Chunk":
        raw = zlib.decompress(data)
        n = CHUNK * CHUNK
        # chunks saved before the land had relief carry no levels: they stay flat (nothing built on them moves)
        return cls(cx, cy, bytearray(raw[:n]), bytearray(raw[n:2 * n]), bytearray(raw[2 * n:3 * n]) if len(raw) >= 3 * n else None)


class Store:
    """Thin SQLite wrapper. One connection, owned by the server thread."""

    def __init__(self, path: Path | str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.path)
        self.db.executescript(SCHEMA)
        self.db.execute("PRAGMA journal_mode=WAL")

    def get_meta(self, key, default=None):
        row = self.db.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
        return json.loads(row[0]) if row else default

    def set_meta(self, key, value):
        self.db.execute("INSERT OR REPLACE INTO meta VALUES(?,?)", (key, json.dumps(value)))

    def load_chunk(self, cx, cy) -> Chunk | None:
        row = self.db.execute("SELECT data FROM chunks WHERE cx=? AND cy=?", (cx, cy)).fetchone()
        return Chunk.unpack(cx, cy, row[0]) if row else None

    def has_chunk(self, cx, cy) -> bool:
        return self.db.execute("SELECT 1 FROM chunks WHERE cx=? AND cy=?", (cx, cy)).fetchone() is not None

    def save_chunk(self, c: Chunk):
        self.db.execute("INSERT OR REPLACE INTO chunks VALUES(?,?,?)", (c.cx, c.cy, c.pack()))

    def commit(self):
        self.db.commit()

    def close(self):
        self.db.commit()
        self.db.close()


class World:
    def __init__(self, store: Store, seed: int | None = None):
        self.store = store
        stored = store.get_meta("seed")
        if stored is None:
            stored = seed if seed is not None else 1337
            store.set_meta("seed", stored)
            store.commit()
        self.seed = stored
        self.chunks: dict[tuple[int, int], Chunk] = {}
        self.tick = 0  # set by the simulation; used for "touched"
        self.meta: dict[tuple[int, int], dict] = {
            (x, y): json.loads(j) for x, y, j in store.db.execute("SELECT x, y, json FROM tile_meta")
        }
        self.dirty_meta: set[tuple[int, int]] = set()
        self._gen, self._pending = None, {}             # background world generation (prefetch)
        self.fresh: list[tuple[int, int]] = []         # chunks generated (not loaded) since the simulation last looked

    # ---- chunk management -------------------------------------------------
    def chunk(self, cx: int, cy: int) -> Chunk:
        c = self.chunks.get((cx, cy))
        if c is None:
            c = self.store.load_chunk(cx, cy)
            if c is not None:
                self._tidy(c)
                self.chunks[(cx, cy)] = c
            else:
                pending = self._pending.pop((cx, cy), None)   # (being generated in the background: take it now)
                c = self._install(cx, cy, *(pending[0].result() if pending else gen_chunk(self.seed, cx, cy)))
        c.touched = self.tick
        return c

    def _install(self, cx, cy, g, b, lv) -> Chunk:
        c = Chunk(cx, cy, g, b, lv)
        c.dirty = True
        self.chunks[(cx, cy)] = c
        self.fresh.append((cx, cy))                     # new land: the simulation may put animals on it
        return c

    def prefetch(self, cx: int, cy: int) -> bool:
        """Bring a chunk into memory without stalling the tick: from disk at once, or generated on a background
        thread (generating costs ~30 ms) and installed exactly GEN_TICKS later (waiting, rarely, if it isn't done),
        so the simulation stays deterministic. True once it's in memory; call again later until then."""
        if (cx, cy) in self.chunks:
            return True
        job = self._pending.get((cx, cy))
        if job is None:
            if self.store.has_chunk(cx, cy) or not THREADS:
                self.chunk(cx, cy)
                return True
            if self._gen is None:
                self._gen = ThreadPoolExecutor(1, thread_name_prefix="worldgen")
            self._pending[(cx, cy)] = (self._gen.submit(gen_chunk, self.seed, cx, cy), self.tick + GEN_TICKS)
            return False
        future, due = job
        if self.tick < due:
            return False
        del self._pending[(cx, cy)]
        self._install(cx, cy, *future.result()).touched = self.tick
        return True

    def _tidy(self, c: Chunk):
        """Older worlds spread berry bushes at random until meadows filled up. Nobody can plant a bush, so a
        bush where the generator never put one came from that: clear it. Lone thickets (hedge balls) aren't
        generated any more and nobody can make one: clear those too."""
        bush, thicket = B["berry_bush"], B["thicket"]
        for i, blk in enumerate(c.block):
            if blk == thicket:
                c.block[i] = B["none"]
                c.dirty = True
            elif blk == bush:
                x, y = c.cx * CHUNK + i % CHUNK, c.cy * CHUNK + i // CHUNK
                if gen_tile(self.seed, x, y)[1] != bush:
                    c.block[i] = B["none"]
                    c.dirty = True

    def flush(self):
        for c in self.chunks.values():
            if c.dirty:
                self.store.save_chunk(c)
                c.dirty = False
        for pos in self.dirty_meta:
            m = self.meta.get(pos)
            if m:
                self.store.db.execute("INSERT OR REPLACE INTO tile_meta VALUES(?,?,?)", (*pos, json.dumps(m)))
            else:
                self.store.db.execute("DELETE FROM tile_meta WHERE x=? AND y=?", pos)
        self.dirty_meta.clear()
        self.store.commit()

    def unload_far(self, anchors: list[tuple[int, int]], radius: int = 3, idle_ticks: int = 150):
        """Save and drop chunks far from every anchor (agent position) and idle."""
        keep = set()
        for x, y in anchors:
            acx, acy = x >> 5, y >> 5
            for dy in range(-radius, radius + 1):
                for dx in range(-radius, radius + 1):
                    keep.add((acx + dx, acy + dy))
        dropped = 0
        for key in list(self.chunks):
            c = self.chunks[key]
            if key not in keep and self.tick - c.touched > idle_ticks:
                if c.dirty:
                    self.store.save_chunk(c)
                del self.chunks[key]
                dropped += 1
        if dropped:
            self.store.commit()
        return dropped

    # ---- tile access ------------------------------------------------------
    def get(self, x: int, y: int) -> tuple[int, int]:
        c = self.chunk(x >> 5, y >> 5)
        i = (y & 31) * CHUNK + (x & 31)
        return c.ground[i], c.block[i]

    def level_raw(self, x: int, y: int) -> int:
        return self.chunk(x >> 5, y >> 5).level[(y & 31) * CHUNK + (x & 31)]

    def level(self, x: int, y: int) -> int:
        """Height of the land here, 0-3."""
        return self.chunk(x >> 5, y >> 5).level[(y & 31) * CHUNK + (x & 31)] & 0x0F

    def ramp(self, x: int, y: int) -> bool:
        """Stairs: from here you can go down to the tile south of you (and come up from it)."""
        return bool(self.chunk(x >> 5, y >> 5).level[(y & 31) * CHUNK + (x & 31)] & RAMP)

    def can_step(self, x0: int, y0: int, x1: int, y1: int) -> bool:
        """Between neighbouring tiles: on the level, or up and down stairs. Cliffs can't be climbed."""
        l0, l1 = self.level(x0, y0), self.level(x1, y1)
        if l0 == l1:
            return True
        if x0 != x1 or abs(l0 - l1) != 1:
            return False
        upper = (x0, y0) if l0 > l1 else (x1, y1)
        return self.ramp(*upper) and max(y0, y1) == upper[1] + 1      # the stairs lead south, down to the landing

    def ground(self, x, y) -> str:
        return GROUNDS[self.get(x, y)[0]].name

    def block(self, x, y) -> str:
        return BLOCKS[self.get(x, y)[1]].name

    def set(self, x: int, y: int, ground: str | None = None, block: str | None = None, level: int | None = None):
        c = self.chunk(x >> 5, y >> 5)
        i = (y & 31) * CHUNK + (x & 31)
        if level is not None:                    # the raw level byte (height, with gen.RAMP for stairs)
            c.level[i] = level
        if ground is not None:
            c.ground[i] = G[ground]
        if block is not None:
            b_before = c.block[i]
            c.block[i] = B[block]
            if (x, y) in self.meta and c.block[i] != b_before:
                del self.meta[(x, y)]
                self.dirty_meta.add((x, y))
        c.dirty = True

    def passable(self, x: int, y: int) -> bool:
        g, b = self.get(x, y)
        return GROUNDS[g].walkable and not BLOCKS[b].solid

    def set_meta(self, x, y, data: dict | None):
        if data:
            self.meta[(x, y)] = data
        else:
            self.meta.pop((x, y), None)
        self.dirty_meta.add((x, y))

    def char(self, x, y) -> str:
        g, b = self.get(x, y)
        return BLOCKS[b].char if b else GROUNDS[g].char
