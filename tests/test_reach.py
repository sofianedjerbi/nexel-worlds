"""Reach: what you can break, hit, use and pick up is within a circle round you, and height is distance too."""

from helpers import run
from test_wild import put

from nexel_worlds.sim import CREATURES, sec
from nexel_worlds.sim.progress import MAGNET_DELAY


def test_reach_is_a_circle_round_you(world):
    """So many tiles as the crow flies (and the half tile to the far tile's edge), not a square: its corners are out."""
    sim, a = world
    sim.world.set(a.x + 3, a.y + 1, block="flower")
    sim.world.set(a.x + 3, a.y + 2, block="flower")
    assert run(sim, a, "dig", {"x": a.x + 3, "y": a.y + 1})["ok"]                          # 3.2 tiles off: within 3 and a half
    assert run(sim, a, "dig", {"x": a.x + 3, "y": a.y + 2})["error"] == "out_of_range"     # 3.6: the corner of what was a square
    cow = put(sim, "cow", a.x + 3, a.y + 2)
    assert run(sim, a, "attack", {"target": cow.id})["error"] == "out_of_range"
    cow.x, cow.y = a.x + 2, a.y + 2
    assert run(sim, a, "attack", {"target": cow.id})["ok"]                                 # 2.8


def test_what_is_too_high_or_too_low_is_out_of_reach(world):
    """A layer is half a tile. A flower on a ledge beside you: 6 layers up is 1 tile and 3 up, 3.2 off, within reach
    (3 and a half); 8 layers is 4.1: no. The wall itself is at your own height: a pickaxe still cuts into it."""
    sim, a = world
    x, y = a.x, a.y
    sim.world.set(x + 1, y, level=6, block="flower")
    assert run(sim, a, "dig", {"dir": "E"})["ok"] and a.count("flower") == 1
    sim.world.set(x + 1, y, level=8, block="flower")
    assert run(sim, a, "dig", {"dir": "E"})["error"] == "out_of_range" and a.count("flower") == 1
    assert run(sim, a, "place", {"dir": "E", "item": "flower"})["error"] == "out_of_range"   # nor put anything up there
    sim.world.set(x, y + 1, level=8)
    a.add("pickaxe")
    assert run(sim, a, "dig", {"dir": "S", "with": "pickaxe"})["ok"]                       # the cell in front of you
    sim.world.set(x - 1, y, level=-8)                                                      # a pit beside you, a cow at the bottom
    cow = put(sim, "cow", x - 1, y)
    assert run(sim, a, "attack", {"target": cow.id})["error"] == "out_of_range"
    assert run(sim, a, "milk", {"target": cow.id})["error"] == "out_of_range"
    sim.world.set(x - 1, y, level=-4)                                                      # half as deep: 2.2 off
    assert run(sim, a, "attack", {"target": cow.id})["ok"]


def test_items_on_a_ledge_do_not_fly_to_you(world):
    """They come from a tile and a half round you: two layers up next to you is 1.4 off, three is 1.8."""
    sim, a = world
    sim.world.set(a.x + 1, a.y, level=3)
    sim.world.set(a.x - 1, a.y, level=2)
    sim.add_items(a.x + 1, a.y, {"wood": 1})
    sim.add_items(a.x - 1, a.y, {"stone": 1})
    for _ in range(MAGNET_DELAY + sec(2)):
        sim.step()
    assert a.count("stone") == 1 and a.count("wood") == 0 and (a.x + 1, a.y) in sim.items


def test_a_bite_reaches_no_higher_than_your_hand(world):
    """What you can't hit for its height can't hit you: a pincer at the foot of the ledge you stand on."""
    sim, a = world
    for dy in (-1, 0, 1):
        sim.world.set(a.x + 1, a.y + dy, level=-6)                                         # a drop beside you, six layers
    crab = put(sim, "pincer", a.x + 1, a.y)
    hp = a.hp
    for _ in range(sec(4)):
        sim.step()
    assert a.hp == hp and crab.id in sim.creatures


def test_every_reach_is_the_one_tables(world):
    """tiles.py REACH (and a tile more, a walking player's lead): a hand to an animal, a blow, a station."""
    from nexel_worlds.tiles import LEAD, LONG, REACH
    sim, a = world
    cow = put(sim, "cow", a.x + REACH["animal"] + LEAD, a.y)
    a.add("wheat", 2)
    assert run(sim, a, "feed", {"target": cow.id, "item": "wheat"})["ok"]                  # (it was 2, with no lead: it failed now and then on the walk)
    cow.x += 1
    assert run(sim, a, "feed", {"target": cow.id, "item": "wheat"})["error"] == "out_of_range"
    sim.creatures.clear()
    moss = put(sim, "mossback", a.x + REACH["melee"] + LEAD + CREATURES["mossback"]["wide"], a.y)   # a wide creature is nearer by its width
    assert sim.within(a, "melee", moss.x, a.y, who="mossback") and not sim.within(a, "melee", moss.x + 1, a.y, who="mossback")
    assert sim.within(a, "melee", moss.x + LONG["spear"], a.y, weapon="spear", who="mossback")
    sim.world.set(a.x + 2, a.y + 1, block="workbench")
    assert sim.near_block(a, "workbench")
    sim.world.set(a.x + 2, a.y + 1, block="none")
    sim.world.set(a.x + 2, a.y + 2, block="workbench")                                     # the corner of what was a square: out, as for all else
    assert not sim.near_block(a, "workbench")
    sim.world.set(a.x + 1, a.y, level=-30, block="workbench")                              # beside you, thirty layers down: height is distance
    assert not sim.near_block(a, "workbench")


def test_reach_rule_is_pure_and_the_world_uses_it():
    """Programs on the agent API check reach before acting with the world's own rule, not a copy of it."""
    from nexel_worlds.sim.bodies import in_reach, reach_of
    from nexel_worlds.tiles import LEAD, LONG, REACH
    assert reach_of("melee") == REACH["melee"] + LEAD
    assert reach_of("melee", "spear") == REACH["melee"] + LEAD + LONG["spear"]
    assert reach_of("melee", who="mossback") == REACH["melee"] + LEAD + 1
    assert in_reach(3, 0, 0, 2.5) and not in_reach(3, 1, 0, 2.5) and not in_reach(2, 0, 8, 2)


def test_an_untouchable_creature_refuses_the_blow_by_its_table_flag():
    from nexel_worlds.sim.entities import CREATURES
    assert [k for k, c in CREATURES.items() if c.get("untouchable")] == ["wisp"]
