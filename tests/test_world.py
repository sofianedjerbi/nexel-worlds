"""World, persistence, determinism and the observation."""

import pytest
from helpers import clear, make

from nexel_worlds.world import Chunk


def test_chunk_pack_roundtrip():
    c = Chunk(1, -2, bytearray(range(256)) * 4, bytearray(b"\x03" * 1024))
    d = Chunk.unpack(1, -2, c.pack())
    assert d.ground == c.ground and d.block == c.block

def test_persistence_roundtrip(tmp_path):
    sim = make(tmp_path, "p")
    a = sim.login("Ash", "tok")
    clear(sim, a)
    a.add("wood", 4)
    sim.world.set(a.x, a.y - 1, block="sign")
    sim.world.set_meta(a.x, a.y - 1, {"text": "hello", "by": "Ash"})
    sim.add_items(a.x + 1, a.y, {"stone": 2})
    for _ in range(10):
        sim.step()
    pos, tick = (a.x, a.y), sim.tick
    sim.close()

    sim2 = make(tmp_path, "p")
    assert sim2.tick == tick
    with pytest.raises(Exception):
        sim2.login("Ash", "wrong")
    b = sim2.login("Ash", "tok")
    assert (b.x, b.y) == pos and b.count("wood") == 4
    assert sim2.world.block(b.x, b.y - 1) == "sign"
    assert sim2.world.meta[(b.x, b.y - 1)]["text"] == "hello"
    assert sim2.items[(b.x + 1, b.y)] == {"stone": 2}
    sim2.close()

def test_unload_and_reload_keeps_edits(tmp_path):
    sim = make(tmp_path, "u")
    sim.world.set(500, 500, block="stone_wall")
    sim.tick = sim.world.tick = 1000
    assert sim.world.unload_far([(0, 0)]) >= 1
    assert (500 >> 5, 500 >> 5) not in sim.world.chunks
    assert sim.world.block(500, 500) == "stone_wall"
    sim.close()

def test_determinism(tmp_path):
    def trace(name):
        sim = make(tmp_path, name)
        a = sim.login("Ash", "t")
        b = sim.login("Bryn", "t")
        out = []
        for i in range(1500):
            if i % 20 == 0:
                sim.submit(a, "step", {"dir": "NESW"[i // 20 % 4]})
                sim.submit(b, "dig", {"dir": "WSEN"[i // 20 % 4]})
            sim.step()
        out.append((a.x, a.y, b.x, b.y, dict(a.inventory), dict(b.inventory)))
        out.append(sorted((c.kind, c.x, c.y, c.hp) for c in sim.creatures.values()))
        out.append(sim.stats["tiles_changed"])
        sim.close()
        return out

    assert trace("d1") == trace("d2")

def test_observe_shape(world):
    sim, a = world
    o = sim.observe(a)
    assert len(o["grid"]) == 21 and all(len(r) == 21 for r in o["grid"])
    assert o["grid"][10][10] == "@" and o["legend"]["@"] == "you"
    assert o["self"]["hp"] == 20 and o["self"]["hunger"] == 17

def test_spread_bushes_are_tidied_on_load(world):
    sim, a = world
    from nexel_worlds.gen import gen_tile
    from nexel_worlds.tiles import B
    x, y = next((x, a.y) for x in range(a.x, a.x + 200) if gen_tile(sim.world.seed, x, a.y)[1] != B["berry_bush"])
    sim.world.set(x, y, block="berry_bush")
    sim.world.flush()
    del sim.world.chunks[(x >> 5, y >> 5)]
    assert sim.world.block(x, y) == "none"

def test_interrupt(world):
    sim, a = world
    sim.world.set(a.x, a.y - 1, block="rock")
    first = sim.submit(a, "dig", {"dir": "N"})
    sim.step()
    sim.submit(a, "say", {"text": "never mind"})
    assert first.result["status"] == "interrupted"


def test_land_is_generated_off_the_tick_then_installed(tmp_path):
    import time
    from nexel_worlds.world import Store, World
    from nexel_worlds.world import GEN_TICKS
    w = World(Store(tmp_path / "w.sqlite"), seed=3)
    assert w.prefetch(9, 9) is False                         # started in the background...
    time.sleep(.2)
    w.tick += GEN_TICKS - 1
    assert w.prefetch(9, 9) is False                         # ...done, but it arrives on a set tick (determinism)
    w.tick += 1
    assert w.prefetch(9, 9) and (9, 9) in w.fresh            # ...then in memory, and new land for the animals
