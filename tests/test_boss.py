"""Old Mossback, the first boss, and its sporelings (sim/boss.py)."""

from test_wild import put

from nexel_worlds import tiles as T
from nexel_worlds.sim import CREATURES, sec
from nexel_worlds.sim.boss import ATTACKS, EXPOSED, SHELL, SPORE_LIFE


def run(sim, seconds):
    for _ in range(sec(seconds)):
        sim.step()


def wake(sim, a, boss):
    """Hit it once, then let it get up."""
    sim.step()
    assert boss.mode == "sleep"
    sim.damage(boss, 5, "test", by=a)
    sim.step()
    assert boss.mode == "" and any(e["type"] == "boss" and e["what"] == "wake" for e in a.events)


def until(sim, boss, mode, seconds=12):
    for _ in range(sec(seconds)):
        sim.step()
        if boss.mode == mode:
            return True
    return False


def test_it_sleeps_until_it_is_hit_and_goes_back_to_sleep_healed(world):
    sim, a = world
    boss = put(sim, "mossback", a.x + 6, a.y)
    hp = a.hp
    run(sim, 5)
    assert boss.mode == "sleep" and (boss.x, boss.y) == (a.x + 6, a.y) and a.hp >= hp      # a hill: it does nothing
    wake(sim, a, boss)
    a.x += 40                                                     # we run for it
    run(sim, 25)
    assert boss.mode == "sleep" and boss.hp == CREATURES["mossback"]["hp"]


def test_it_is_three_tiles_wide(world):
    sim, a = world
    boss = put(sim, "mossback", a.x + 4, a.y)
    assert sim.entity_at(a.x + 3, a.y) is boss and sim.entity_at(a.x + 5, a.y) is boss and sim.entity_at(a.x + 2, a.y) is None
    assert not sim.can_go(a, a.x + 1, a.y) or sim.entity_at(a.x + 1, a.y) is None


def test_the_stomp_warns_then_hurts_and_throws_back(world):
    sim, a = world
    boss = put(sim, "mossback", a.x + 3, a.y + 1)                # close, and not on its line
    wake(sim, a, boss)
    sim.rng.random = lambda: 0.9                                  # it does not shake instead
    put(sim, "sporeling", a.x + 9, a.y + 5, cooldown=10 ** 6); put(sim, "sporeling", a.x + 9, a.y + 6, cooldown=10 ** 6); put(sim, "sporeling", a.x + 9, a.y + 7, cooldown=10 ** 6)
    assert until(sim, boss, "stomp")
    assert any(e["type"] == "windup" and e.get("move") == "stomp" for e in a.events)
    hp, x = a.hp, a.x
    run(sim, ATTACKS["stomp"] - 0.2)
    assert a.hp >= hp                                             # the warning hurts nobody
    run(sim, 0.4)
    assert a.hp <= hp - CREATURES["mossback"]["damage"] + 2 and a.x == x - 1          # hit, and a tile further away


def test_the_snap_reaches_along_its_line_and_leaves_the_neck_out(world):
    sim, a = world
    boss = put(sim, "mossback", a.x + 4, a.y)                    # on its line, two tiles from its body
    wake(sim, a, boss)
    assert until(sim, boss, "snap") and boss.dir == (-1, 0)
    hp = a.hp
    run(sim, ATTACKS["snap"] + 0.1)
    assert a.hp <= hp - CREATURES["mossback"]["snap"] + 2
    before = boss.hp
    sim.damage(boss, sim.shell(boss, 20), "test", by=a)
    assert boss.hp == before - 20                                 # the neck is out: the blow lands in full
    run(sim, EXPOSED + 0.2)
    if boss.mode != "snap":
        assert sim.shell(boss, 20) == 20 // SHELL                 # back in its shell


def test_step_off_its_line_and_the_snap_misses(world):
    sim, a = world
    boss = put(sim, "mossback", a.x + 4, a.y)
    wake(sim, a, boss)
    assert until(sim, boss, "snap")
    a.y += 3
    hp = a.hp
    run(sim, ATTACKS["snap"] + 0.1)
    assert a.hp >= hp


def test_the_shake_drops_sporelings_that_puff_and_then_root(world):
    sim, a = world
    boss = put(sim, "mossback", a.x + 8, a.y + 5)                # far, and off its line: it shakes
    wake(sim, a, boss)
    assert until(sim, boss, "shake")
    run(sim, ATTACKS["shake"] + 0.1)
    brood = [c for c in sim.creatures.values() if c.kind == "sporeling"]
    assert 1 <= len(brood) <= 3 and all(c.mode == "land" for c in brood)
    boss.cooldown = 10 ** 6
    boss.rest = sim.tick + 10 ** 6                                # the boss holds still; watch the brood
    hp = a.hp
    assert any(until(sim, c, "puff", 1) for _ in range(12) for c in brood if c.id in sim.creatures)
    run(sim, 0.5)
    assert a.hp < hp and any(e["type"] == "boss" and e["what"] == "puff" for e in a.events)
    run(sim, SPORE_LIFE)
    assert not [c for c in sim.creatures.values() if c.kind == "sporeling" and c.born]      # rooted: gone, a mushroom left
    assert any(sim.world.block(c.x, c.y) == "mushroom" for c in brood)


def test_a_sporeling_dies_in_one_hit_and_the_boss_takes_many(world):
    sim, a = world
    boss = put(sim, "mossback", a.x + 2, a.y + 6)
    s = put(sim, "sporeling", a.x + 1, a.y, cooldown=10 ** 6)
    a.swing_ready = 0
    sim.submit(a, "attack", {"target": s.id})
    run(sim, 0.3)
    assert s.id not in sim.creatures
    sword = T.WEAPONS["sword"]                                         # (half hearts: on the shell, a blow of a sword takes half a heart)
    assert sim.shell(boss, sword) == max(1, sword // SHELL) and CREATURES["mossback"]["hp"] // max(1, sword // SHELL) > 30
