"""Chunked tile world with lazy load/unload and SQLite persistence."""

import json
import sqlite3
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from .chunks import Chunk
from .stone import Stone
from .gen import CHUNK, HIGH, LOW, col_cave, col_floor, col_surfaces, col_top, gen_chunk, gen_chunk_steps, gen_level, gen_tile
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
class Steps:
    """Land being made a row at a time, where there is no thread for it (the in-browser demo): a future of sorts.
    World.work moves it on in the time left over between two ticks, so no tick waits on a whole chunk."""

    def __init__(self, steps):
        self.steps, self.out = steps, None

    def work(self, until: float) -> bool:
        """Go on until the clock (time.perf_counter) reads `until`; True once the chunk is made."""
        try:
            while self.out is None and time.perf_counter() < until:
                next(self.steps)
        except StopIteration as done:
            self.out = done.value
        return self.out is not None

    def result(self):
        self.work(float("inf"))
        return self.out


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


class World(Stone):
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
        self._gen, self._pending, self.water = None, {}, None   # background world generation (prefetch); water: flow.py, told of each change
        self.fresh: list[tuple[int, int]] = []         # chunks generated (not loaded) since the simulation last looked

    # ---- chunk management -------------------------------------------------
    def chunk(self, cx: int, cy: int) -> Chunk:
        c = self.chunks.get((cx, cy))
        if c is None:
            c = self.store.load_chunk(cx, cy)
            if c is not None:
                self._tidy(c)
                if c.guessed:                           # (a save from before the land kept its stone: as the generator laid it out)
                    c.lay_stone(lambda x, y: gen_level(self.seed, x, y), unknown_only=True)
                self.chunks[(cx, cy)] = c
            else:
                pending = self._pending.pop((cx, cy), None)   # (being generated in the background: take it now)
                c = self._install(cx, cy, *(pending[0].result() if pending else gen_chunk(self.seed, cx, cy)))
        c.touched = self.tick
        return c

    def _install(self, cx, cy, g, b, cols) -> Chunk:
        c = Chunk(cx, cy, g, b, cols)
        self.lay(c, lambda x, y: gen_level(self.seed, x, y))     # (its stone, the generator's: stone.py)
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
            if self.store.has_chunk(cx, cy):
                self.chunk(cx, cy)
                return True
            if not THREADS:                              # (no thread: a row at a time, between ticks: work, below)
                self._pending[(cx, cy)] = (Steps(gen_chunk_steps(self.seed, cx, cy)), self.tick + GEN_TICKS)
                return False
            if self._gen is None:
                self._gen = ThreadPoolExecutor(1, thread_name_prefix="worldgen")
            self._pending[(cx, cy)] = (self._gen.submit(gen_chunk, self.seed, cx, cy), self.tick + GEN_TICKS)
            return False
        future, due = job
        if self.tick < due or (isinstance(future, Steps) and future.out is None):
            return False
        del self._pending[(cx, cy)]
        self._install(cx, cy, *future.result()).touched = self.tick
        return True

    def work(self, until: float) -> bool:
        """Without threads: go on making the land that was asked for (prefetch) until the clock reads `until`. True
        once there is none left to make."""
        return all(not isinstance(future, Steps) or future.work(until) for future, _ in self._pending.values())

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

    def col(self, x: int, y: int) -> int:
        """The tile's column of cells, a bit each from the bottom, set where solid (gen.col_solid...)."""
        return self.chunk(x >> 5, y >> 5).cols[(y & 31) * CHUNK + (x & 31)]

    def level(self, x: int, y: int) -> int:
        """Height of the lowest ground here (a cave's floor, under a hill): 0 at sea level, below in dug pits, up to
        12 in the mountains."""
        return col_floor(self.col(x, y))

    def top(self, x: int, y: int) -> int:
        """Height of the land as seen from above (over a cave: the hill)."""
        return col_top(self.col(x, y))

    def roof(self, x: int, y: int) -> int:
        """Over the lowest ground: how far up the land goes (0 under the sky; a cave when not)."""
        c = self.col(x, y)
        return col_top(c) - col_floor(c)

    def surfaces(self, x: int, y: int) -> list[int]:
        """Every height you can stand at here, lowest first."""
        return col_surfaces(self.col(x, y))

    def solid(self, x: int, y: int, z: int) -> bool:
        """Is the cell whose top is at height z solid? (Everything under the bottom is; nothing over the top.)"""
        return z < LOW or (z <= HIGH and bool(self.col(x, y) >> (z - LOW) & 1))

    def covered(self, x: int, y: int, z: int) -> bool:
        """Standing at height z here: is there anything solid over you (a cave)?"""
        return bool(self.col(x, y) >> (z - LOW + 1))

    def set_cell(self, x: int, y: int, z: int, solid: bool):
        """Fill or empty one cell (never the bottom one)."""
        if LOW < z <= HIGH:
            c = self.chunk(x >> 5, y >> 5)
            i = (y & 31) * CHUNK + (x & 31)
            c.cols[i] = c.cols[i] | 1 << (z - LOW) if solid else c.cols[i] & ~(1 << (z - LOW))
            c.dirty = True
            self.water and self.water.cell_changed(x, y, z, solid)

    def rim(self, x: int, y: int) -> bool:
        """On a hill's rim (a lower tile next to it, diagonals too), where its edge is drawn: nothing is built or
        grows there."""
        lv = self.level(x, y)
        return any(self.level(x + dx, y + dy) < lv for dx in (-1, 0, 1) for dy in (-1, 0, 1) if dx or dy)

    def edge(self, x: int, y: int) -> bool:
        """Where a cliff face is drawn: a hill tile with lower ground straight south of it (you stand on its top)."""
        lv = self.level(x, y)
        return self.level(x, y + 1) < lv

    def ground(self, x, y) -> str:
        return GROUNDS[self.get(x, y)[0]].name

    def block(self, x, y) -> str:
        return BLOCKS[self.get(x, y)[1]].name

    def set(self, x: int, y: int, ground: str | None = None, block: str | None = None, level: int | None = None,
            roof: int | None = None, head: int | None = None):
        c = self.chunk(x >> 5, y >> 5)
        i = (y & 31) * CHUNK + (x & 31)
        if level is not None or roof is not None or head is not None:
            # (laying land out: solid up to `level`; `roof`: that much higher over a cave on that floor, `head` cells high: 2, or 1 under a roof of 2)
            f = col_floor(c.cols[i]) if level is None else level
            r = col_top(c.cols[i]) - col_floor(c.cols[i]) if roof is None else roof
            c.cols[i] = col_cave(f, head or (2 if r >= 3 else 1), f + r)
            self.relay(x, y)
        if ground is not None:
            c.ground[i] = G[ground]
        if block is not None:
            b_before = c.block[i]
            c.block[i] = B[block]
            if (x, y) in self.meta and c.block[i] != b_before:
                del self.meta[(x, y)]
                self.dirty_meta.add((x, y))
        c.dirty = True
        self.water and self.water.tile_changed(x, y)

    def set_meta(self, x, y, data: dict | None):
        if data:
            self.meta[(x, y)] = data
        else:
            self.meta.pop((x, y), None)
        self.dirty_meta.add((x, y))

    def char(self, x, y) -> str:
        return BLOCKS[gb[1]].char if (gb := self.get(x, y))[1] else GROUNDS[gb[0]].char
