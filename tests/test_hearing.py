"""Who perceives an event: one rule for an agent and for a screen (sim/hearing.py)."""

import asyncio
import json

import pytest

from nexel_worlds.server import GameServer
from nexel_worlds.sim.hearing import RANGE


@pytest.fixture
def gs(tmp_path):
    s = GameServer(tmp_path / "w", seed=3)
    yield s
    s.sim.close()


def screen(gs, rect=None, player=None):
    q = asyncio.Queue()
    gs.spectators[q] = rect
    if player:
        gs.players[q] = player.id
    return q


def got(q) -> list:
    out = []
    while not q.empty():
        out.append(json.loads(q.get_nowait())["ev"])
    return out


def test_an_agent_and_a_person_at_a_screen_hear_the_same_things(gs):
    sim = gs.sim
    ash, near, far = (sim.login(n, "t") for n in ("Ash", "Near", "Far"))
    near.x, near.y, far.x, far.y = ash.x + RANGE["say"], ash.y, ash.x + RANGE["say"] + 1, ash.y
    for a in (ash, near, far):
        a.z, a.events = sim.world.level(a.x, a.y), []
    qs = {"Near": screen(gs, (near.x - 5, near.y - 5, 10, 10), near),                     # Ash is off Near's screen: only what is heard counts
          "Far": screen(gs, (far.x - 30, far.y - 20, 60, 40), far)}                        # ...and on Far's
    watcher = screen(gs, (ash.x + 500, ash.y, 40, 30))                                     # a screen that only watches, somewhere else
    sim.emit("say", ash.x, ash.y, z=ash.z, **{"from": "Ash"}, text="hi")
    assert [e["text"] for e in near.events] == ["hi"] and far.events == []
    assert [e["text"] for e in got(qs["Near"])] == ["hi"] and got(watcher) == []
    assert [e["text"] for e in got(qs["Far"])] == ["hi"]                                   # (on Far's screen: the bubble is seen)
    gs.spectators[qs["Far"]] = (far.x + 100, far.y, 40, 30)                                # ...looking elsewhere: not heard
    sim.emit("say", ash.x, ash.y, z=ash.z + 2 * RANGE["say"] + 2, **{"from": "Ash"}, text="from far under")   # height is distance: a layer half a tile
    sim.emit("say", ash.x, ash.y, z=ash.z, **{"from": "Ash"}, text="again")
    assert [e["text"] for e in near.events[1:]] == ["again"] and [e["text"] for e in got(qs["Near"])] == ["again"] and got(qs["Far"]) == []
    sim.emit("shout", ash.x, ash.y, z=ash.z, **{"from": "Ash"}, text="HEY")                # a shout carries further
    assert far.events[-1]["text"] == "HEY" and got(qs["Far"])[-1]["text"] == "HEY" and got(watcher) == []


def test_the_worlds_news_what_names_you_and_the_land_reach_every_screen(gs):
    sim = gs.sim
    ash, far = sim.login("Ash", "t"), sim.login("Far", "t")
    far.x, far.events = ash.x + 900, []
    q, watcher = screen(gs, (far.x - 20, far.y - 15, 40, 30), far), screen(gs, (far.x - 20, far.y - 15, 40, 30))
    sim.emit("leave", ash.x, ash.y, name="Ash")
    sim.emit("mail", ash.x, ash.y, **{"from": "Ash"}, to="Far")                            # a letter for Far: told wherever Far is
    sim.emit("mail", ash.x, ash.y, **{"from": "Ash"}, to="Someone")
    sim.emit("attack", ash.x, ash.y, attacker="Ash", target="cow#1", damage=1)
    sim.emit("tile", ash.x, ash.y, ground="dirt", block="none")
    sim.emit("shout", ash.x, ash.y, everywhere=True, **{"from": "[Ash]"}, text="server going down")
    assert [(e["type"], e.get("to")) for e in far.events] == [("leave", None), ("mail", "Far"), ("shout", None)]
    assert [e["type"] for e in got(q)] == ["leave", "mail", "tile", "shout"]               # (the land: to keep its picture true)
    assert [e["type"] for e in got(watcher)] == ["leave", "tile", "shout"]
    assert got(screen(gs)) == [] and [e["type"] for e in (sim.emit("join", 0, 0, name="X"), *got(screen(gs)))] == ["join"]
