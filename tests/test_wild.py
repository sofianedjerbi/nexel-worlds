"""Wild creatures (tusker, pincer, strawman, wisp, wyrm) and how rarely creatures turn up."""

from helpers import clear, run

from megastructure.sim import CREATURES, DAY_TICKS, Creature, sec
from megastructure.sim.spawning import HOME_R, PASSIVE, PASSIVE_CAP


def put(sim, kind, x, y, **kw):
    c = Creature(sim.next_creature, kind, x, y, CREATURES[kind]["hp"], **kw)
    sim.next_creature += 1
    sim.creatures[c.id] = c
    return c


def night(sim):
    sim.tick = (sim.tick // DAY_TICKS) * DAY_TICKS + int(0.8 * DAY_TICKS)
    assert sim.is_night()


def test_tusker_warns_then_charges_in_a_straight_line(world):
    sim, a = world
    boar = put(sim, "tusker", a.x + 4, a.y)
    sim.step()
    assert boar.mode == "windup" and boar.dir == (-1, 0)          # it saw you: it paws the ground, facing you
    assert any(e["type"] == "windup" and e["id"] == boar.id for e in a.events)
    hp = a.hp
    for _ in range(sec(0.5)):
        sim.step()
    assert a.hp >= hp and (boar.x, boar.y) == (a.x + 4, a.y)      # the warning hurts nobody and it has not moved
    for _ in range(sec(1.5)):
        sim.step()
    assert a.hp <= hp - CREATURES["tusker"]["damage"] + 2         # you stood there: it ran you down (you heal a little)


def test_step_well_aside_and_the_tusker_runs_past_into_a_tree(world):
    sim, a = world
    boar = put(sim, "tusker", a.x + 4, a.y)
    sim.world.set(a.x - 3, a.y + 1, block="tree")
    sim.step()
    a.y += 2                                                      # two lanes out of its line: it leans one toward you, no more
    hp = a.hp
    for _ in range(sec(2)):
        sim.step()
    assert a.hp >= hp
    assert boar.mode == "stun" and (boar.x, boar.y) == (a.x - 2, a.y - 1)   # it rammed the tree and stands dazed


def test_the_tusker_lines_up_aims_as_it_sets_off_and_leans(world):
    """It almost never hit: it charged along the longer way from wherever it stood (past you, unless you were dead in
    its line) and at where you were when it began to paw. It trots into line first, aims again as it sets off, and
    leans a lane toward you as it runs: one small step aside is not enough any more."""
    sim, a = world
    boar = put(sim, "tusker", a.x + 4, a.y + 2)                    # not in line with us
    hp = a.hp
    for _ in range(sec(3)):
        sim.step()
        if a.hp < hp:
            break
    assert a.hp < hp                                              # it came into line, and ran us down where we stood
    boar.mode, boar.rest, boar.x, boar.y, a.hp = "", 0, a.x + 4, a.y, hp
    sim.step()
    assert boar.mode == "windup"
    a.y += 1                                                      # one lane aside while it paws
    for _ in range(sec(2)):
        sim.step()
    assert a.hp < hp


def test_pincer_snaps_only_if_you_stay_next_to_it(world):
    sim, a = world
    crab = put(sim, "pincer", a.x + 1, a.y)
    hp = a.hp
    sim.step()
    assert crab.mode == "windup"
    for _ in range(sec(1)):
        sim.step()
    assert hp - CREATURES["pincer"]["damage"] <= a.hp < hp
    a.x -= 6                                                      # walk off: it does not follow far
    hp = a.hp
    for _ in range(sec(5)):
        sim.step()
    assert a.hp >= hp


def test_strawman_is_a_scarecrow_by_day_and_walks_at_night_but_not_into_firelight(world):
    sim, a = world
    straw = put(sim, "strawman", a.x + 6, a.y)
    for _ in range(sec(10)):
        sim.step()
    assert (straw.x, straw.y) == (a.x + 6, a.y)                   # daylight: it does not move
    night(sim)
    hp = a.hp
    for _ in range(sec(12)):
        sim.step()
    assert a.hp < hp                                              # it came, and it grabbed
    sim.creatures.clear()
    straw = put(sim, "strawman", a.x + 6, a.y)
    sim.world.set(a.x + 4, a.y + 2, block="campfire")
    for _ in range(sec(10)):
        sim.step()
    assert (straw.x, straw.y) == (a.x + 6, a.y)                   # in the firelight it is only a scarecrow


def test_wisp_keeps_ahead_of_you_at_night_calls_and_cannot_be_hit(world):
    sim, a = world
    from helpers import run
    night(sim)
    wisp = put(sim, "wisp", a.x + 2, a.y)
    for _ in range(sec(2)):
        sim.step()
    assert max(abs(wisp.x - a.x), abs(wisp.y - a.y)) >= 4         # you were close: it slipped away
    calls = 0
    for _ in range(sec(8)):
        sim.step()
        calls += wisp.mode == "windup"
    assert calls                                                  # you hung back: it called
    hp = a.hp
    wisp.x, wisp.y, wisp.cooldown = a.x + 1, a.y, 10 ** 6
    assert run(sim, a, "attack", {"target": wisp.id})["error"] == "bad_target"
    assert a.hp >= hp and wisp.id in sim.creatures


def test_wyrm_stays_in_deep_water_and_lunges_along_its_line(world):
    sim, a = world
    for dx in range(1, 7):                                        # a channel of deep water running east from the shore
        sim.world.set(a.x + dx, a.y, ground="deep_water", block="none")
    wyrm = put(sim, "wyrm", a.x + 5, a.y)
    hp = a.hp
    for _ in range(sec(6)):
        sim.step()
    assert sim.world.ground(wyrm.x, wyrm.y) == "deep_water"        # it came up the channel, never onto land
    assert a.hp <= hp - CREATURES["wyrm"]["damage"] + 4            # we stood on its line, within reach
    a.y -= 3                                                       # off the line, away from the water
    hp = a.hp
    for _ in range(sec(6)):
        sim.step()
    assert a.hp >= hp


def test_saved_glooms_are_gone_when_a_world_is_opened(world):
    sim, a = world
    ghost = put(sim, "tusker", a.x + 30, a.y)
    ghost.kind = "gloom"                                           # as an old save would have it
    sim.thin_wild(sim.world.store)
    assert ghost.id not in sim.creatures


def test_only_tuskers_and_pincers_spawn_by_themselves_and_creatures_stay_rare(world):
    sim, a = world
    clear(sim, a, r=45)
    seen = set()
    for _ in range(DAY_TICKS):                                    # a whole day and night
        sim.step()
        seen |= {c.kind for c in sim.creatures.values()}
        near = [c for c in sim.creatures.values() if max(abs(c.x - a.x), abs(c.y - a.y)) <= 40]
        assert sum(c.kind in PASSIVE for c in near) <= PASSIVE_CAP + 3      # (a herd may overshoot the cap a little)
        assert sum(c.kind not in PASSIVE for c in near) <= 4
        a.hp = 100
    assert seen <= {"chicken", "cow", "chick", "calf", "tusker", "pincer"}      # no strawman, wisp or wyrm (and no gloom)


def test_a_world_from_before_is_thinned_once_and_copied_first(world):
    sim, a = world
    sim.creatures.clear()
    home = [put(sim, "chicken", a.x + 3, a.y + i) for i in range(3)]
    wild = [put(sim, "cow", a.x + HOME_R + 30 + i, a.y) for i in range(40)]
    sim.world.store.set_meta("spawn_rules", 1)
    sim.thin_wild(sim.world.store)
    left = [c for c in wild if c.id in sim.creatures]
    assert all(c.id in sim.creatures for c in home)               # the ones by your side are yours
    assert 4 <= len(left) <= 12                                   # about one in five of the rest
    assert sim.world.store.path.with_name(sim.world.store.path.stem + ".before-rare-mobs.sqlite").exists()
    sim.thin_wild(sim.world.store)
    assert len([c for c in wild if c.id in sim.creatures]) == len(left)      # only once


def test_the_client_table_matches_the_sheets():
    """world_decor.js WILD gives each sheet's cell size and animation columns: they must fit the PNG the game ships."""
    import json
    import re
    import struct
    from pathlib import Path
    root = Path(__file__).parent.parent
    js = (root / "src/megastructure/web/js/world_decor.js").read_text()
    design = {e["key"]: e for e in json.loads((root / "design/enemies/site/enemies.json").read_text())}
    for kind in ("tusker", "pincer", "strawman", "wisp", "wyrm", "mossback", "sporeling"):
        line = re.search(rf"^  {kind}: {{(.*)}},$", js, re.M).group(1)
        cw, ch = (int(re.search(rf"{k}: (\d+)", line).group(1)) for k in ("cw", "ch"))
        spans = [(int(a), int(b)) for a, b in re.findall(r"[a-z]+: \[(\d+), (\d+), ", line)]
        png = (root / f"src/megastructure/web/assets/{kind}.png").read_bytes()
        w, h = struct.unpack(">II", png[16:24])
        assert (w, h) == (max(a + b for a, b in spans) * cw, 4 * ch), kind
        if kind in design:                                             # (the ones still on the design page)
            assert [cw, ch] == design[kind]["cell"] and w == design[kind]["frames"] * cw
        assert kind in CREATURES


def test_a_tusker_that_is_hit_goes_for_whoever_hit_it(world):
    """Hit, a tusker went on as before: one charge, three seconds' rest, whoever was nearest. Now it is angry for
    twelve seconds: at the one who hit it, from further than it sees; it lines itself up with them, paws the ground
    half as long, shakes off a tree in half the time and charges again at once."""
    from megastructure.sim.wild import ANGRY, TUSKER_ANGRY, TUSKER_SEES
    sim, a = world
    clear(sim, a, r=12)
    a.hp, a.hunger = 20, 17
    boar = put(sim, "tusker", a.x + 2, a.y, cooldown=10 ** 6)       # (held still: we hit it first)
    assert run(sim, a, "attack", {"target": boar.id})["ok"]
    assert sim.tick < boar.angry <= sim.tick + sec(TUSKER_ANGRY)
    assert boar.foe == a.id and any(e["type"] == "enrage" and e["id"] == boar.id for e in a.events)
    boar.cooldown = 0
    boar.x, boar.y, boar.mode, boar.cooldown = a.x + 7, a.y + 3, "", 0      # (put) further than it sees, and not in line with us
    assert max(abs(boar.x - a.x), abs(boar.y - a.y)) > TUSKER_SEES
    for _ in range(sec(0.2) * 3 + 2):
        sim.step()
    assert boar.y == a.y and boar.mode == "windup" and boar.dir == (-1, 0)       # it trotted into our line, and paws the ground at us
    start = sim.tick
    while boar.mode == "windup":
        sim.step()
    assert sim.tick - start <= sec(ANGRY["windup"])                # ...half as long
    hp = a.hp
    for _ in range(sec(1.5)):
        sim.step()
    assert a.hp == hp - CREATURES["tusker"]["damage"]              # ran down: we stood there
    a.y += 2                                                       # out of its line: it lines up again, and comes again
    hits = [e for e in a.events if e["type"] == "attack"]
    for _ in range(sec(4)):
        sim.step()
        a.hp = 20
    assert len([e for e in a.events if e["type"] == "attack"]) > len(hits) or boar.mode in ("windup", "charge", "stun")
    for _ in range(sec(TUSKER_ANGRY) + sec(6)):                    # left alone, it calms down
        sim.step()
        a.hp = 20
        a.x, a.y = boar.x + 30, boar.y + 30                        # (far from it)
    assert boar.angry <= sim.tick and boar.id in sim.creatures


def test_a_calm_tusker_is_as_it_was(world):
    from megastructure.sim.wild import TUSKER_REST
    sim, a = world
    clear(sim, a, r=12)
    boar = put(sim, "tusker", a.x + 6, a.y + 3)                    # past what it sees: it does not come
    for _ in range(sec(3)):
        sim.step()
    assert boar.mode == "" and max(abs(boar.x - a.x), abs(boar.y - a.y)) >= 4 and boar.angry == 0
    assert TUSKER_REST == 3.0
