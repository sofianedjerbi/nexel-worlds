"""A line for a death, said to everyone (death_lines.py, #383): every cause has its lines, every creature that bites its
own; what was in hand, the food starved with, the water, the night add theirs; every line is in the third person (it
names the one who died) and fills in; the server picks one for the death event, the same for all who read it, and a
death never gets the last death's line."""

import random
import re
import string

from test_event_refs import last

from nexel_worlds import tiles as T
from nexel_worlds.death_lines import LINES, fitting, pick, say
from nexel_worlds.sim.combat import CAUSES
from nexel_worlds.sim.entities import CREATURES

RULES = dict(food=T.FOOD, weapons=T.WEAPONS, tools=T.TOOLS)


def test_every_cause_and_every_biting_creature_has_lines_of_its_own():
    for code in CAUSES:
        assert len(LINES["struck" if code in ("admin", "dev") else code]) >= 3, code
    for kind, spec in CREATURES.items():
        if spec.get("damage"):
            assert len(LINES[kind]) >= 3, kind


def test_every_line_names_the_one_who_died_and_fills_in():
    for pool, lines in LINES.items():
        for t in lines:
            names = {f for _, f, _, _ in string.Formatter().parse(t) if f}
            assert "name" in names and names <= {"name", "who", "item", "Item"}, t
            assert not re.search(r"\b(you|your|you're|you'll)\b", t, re.I), f"a line for everyone, in the third person: {t}"
            assert "{" not in say(pool, lines.index(t), name="Ash", who="Rook", item="iron_axe")


def test_a_death_s_lines_are_its_situation_s():
    pools = lambda **s: {p for p, _, _ in fitting(**s, **RULES)}      # noqa: E731
    assert pools(code="bitten", kind="tusker", held="sword", water=True, night=True) == {"bitten", "tusker", "hand_weapon", "water", "night"}
    assert pools(code="killed") == {"killed", "hand_none"}
    assert pools(code="fell") == {"fell"}
    assert pools(code="starvation", held="bread", dropped={"wood": 3, "bread": 2}) == {"starvation", "fed"}
    assert pools(code="dev", held="sword") == {"struck"}
    assert {i for p, _, i in fitting(code="starvation", dropped={"bread": 2}, **RULES) if p == "fed"} == {"bread"}
    assert say("fed", 1, name="Ash", item="cooked_meat") == "Ash was saving the cooked meat for later. There was no later."


def test_a_death_never_gets_the_last_death_s_line():
    rng, line = random.Random(3), None
    for _ in range(200):
        p, i, _ = pick(rng, line, code="fell", **RULES)
        assert [p, i] != line
        line = [p, i]


def test_the_server_picks_one_line_for_the_death_the_same_for_all(world):
    sim, ash = world
    bob = sim.login("Bob", "tok2")
    seen = []
    for _ in range(6):
        bob.held = "sword"; bob.inventory["sword"] = 1
        bob.hp = 1
        sim.damage(bob, 2, "killed", by=ash)
        died = last(bob, "death")
        heard = last(ash, "death")
        assert (heard["line"], heard["item"]) == (died["line"], died["item"])      # (one event, one line, for all who hear it)
        pool, i = died["line"]
        assert pool in {"killed", "hand_weapon"} and died["item"] == ("sword" if pool == "hand_weapon" else None)
        assert "Bob" in say(pool, i, name=died["name"], who=died["who"]["name"], item=died["item"])
        seen.append(died["line"])
    assert all(a != b for a, b in zip(seen, seen[1:]))
