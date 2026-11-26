"""Events name who did what as data, a death's cause as a code (#6): {kind, id, name} and `code`, read by kind and code,
never by the words written for people. (A wild one was told from a person by its "a ": `attacker` "a tusker", the page
sliced it off: a player named a_tusker struck with a tusker's sound.) The words stay in `cause` for the agents till
they read the codes (nexel-agent), as they were, made from the code in one place (combat.py CAUSES)."""

import re
from pathlib import Path

from helpers import run
from test_wild import put

from nexel_worlds.sim import combat

JS = Path(__file__).parent.parent / "src" / "nexel_worlds" / "web" / "js"


def last(a, kind):
    return [e for e in a.events if e["type"] == kind][-1]


def test_a_player_named_like_a_creature_is_a_player(world):
    sim, ash = world
    bob = sim.login("a_tusker", "tok2")
    bob.x, bob.y, bob.z = ash.x + 1, ash.y, ash.z
    assert run(sim, bob, "attack", {"target": ash.id})["ok"]
    e = last(ash, "attack")
    assert e["who"] == {"kind": "agent", "id": bob.id, "name": "a_tusker"} and e["whom"] == {"kind": "agent", "id": ash.id, "name": "Ash"}
    assert (e["attacker"], e["target"]) == ("a_tusker", "Ash")       # (the agents' words, as they were)


def test_a_wild_ones_bite_and_the_death_it_brings_are_told_by_kind_and_code(world):
    sim, ash = world
    boar = put(sim, "tusker", ash.x + 1, ash.y)
    ash.hp = 1
    sim.bite(boar, ash, 2)
    hit, died = last(ash, "attack"), last(ash, "death")
    assert hit["who"] == {"kind": "tusker", "id": boar.id, "name": None} and hit["attacker"] == "a tusker"
    assert (died["code"], died["who"], died["cause"]) == ("bitten", hit["who"], "tusker")


def test_a_kill_by_a_person_is_its_code_and_its_killer(world):
    sim, ash = world
    bob = sim.login("Bob", "tok2")
    ash.hp = 1
    sim.damage(ash, 2, "killed", by=bob)
    died = last(ash, "death")
    assert (died["code"], died["who"]["id"], died["by"], died["cause"]) == ("killed", bob.id, "Bob", "killed by Bob")
    assert last(ash, "respawn")["code"] == "killed"


def test_rewording_a_cause_changes_nothing_but_its_words(world, monkeypatch):
    sim, ash = world
    monkeypatch.setitem(combat.CAUSES, "fell", "came down too hard")
    ash.hp, deaths = 1, ash.deaths
    sim.damage(ash, 2, "fell")
    died = last(ash, "death")
    assert ash.deaths == deaths + 1 and ash.hp > 0 and died["code"] == "fell" and died["who"] is None
    assert died["cause"] == "came down too hard"


def test_the_page_reads_who_and_the_code_never_the_words():
    """No script reads an attack's `attacker` (the words for people) or writes a death's `cause` out, nor cuts a word off a
    name. (A tile's `cause`, "dig" or "place", is a code already: state.js reads it as one.)"""
    hits = [f"{p.name}:{i}: {line.strip()[:120]}" for p in sorted(JS.glob("*.js")) for i, line in enumerate(p.read_text().splitlines(), 1)
            if re.search(r"\be\.attacker\b|\$\{e\.cause\}|String\(e\.(cause|attacker)\b|\.slice\(2\)", line)]
    assert not hits, hits
