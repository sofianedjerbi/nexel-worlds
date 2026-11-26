"""Events name who did what as data, a death's cause as a code (#6, #171): {kind, id, name} and `code`, read by kind and
code, never by words. (A wild one was told from a person by its "a ": `attacker` "a tusker", the page sliced it off: a
player named a_tusker struck with a tusker's sound.) No event carries words: each reader writes its own from the codes
(the page's death.js WHY_DIED, the agents' nexel-agent rl/facts.py told)."""

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
    assert "attacker" not in e and "target" not in e                    # (no words to tell it by)


def test_a_wild_ones_bite_and_the_death_it_brings_are_told_by_kind_and_code(world):
    sim, ash = world
    boar = put(sim, "tusker", ash.x + 1, ash.y)
    ash.hp = 1
    sim.bite(boar, ash, 2)
    hit, died = last(ash, "attack"), last(ash, "death")
    assert hit["who"] == {"kind": "tusker", "id": boar.id, "name": None} and "attacker" not in hit
    assert (died["code"], died["who"]) == ("bitten", hit["who"]) and "cause" not in died


def test_a_kill_by_a_person_is_its_code_and_its_killer(world):
    sim, ash = world
    bob = sim.login("Bob", "tok2")
    ash.hp = 1
    sim.damage(ash, 2, "killed", by=bob)
    died = last(ash, "death")
    assert (died["code"], died["who"]["id"], died["by"]) == ("killed", bob.id, "Bob") and "cause" not in died
    assert last(ash, "respawn")["code"] == "killed"


def test_a_death_s_code_is_one_of_a_closed_set(world):
    """A cause is a code of CAUSES, whose words are its readers' own: a code that is not one is a bug, not a new sentence."""
    import pytest
    sim, ash = world
    ash.hp = 1
    with pytest.raises(ValueError):
        sim.damage(ash, 2, "came down too hard")
    assert set(combat.CAUSES) >= {"killed", "bitten", "burnt", "fell", "starvation", "fire"}


def test_the_page_reads_who_and_the_code_never_the_words():
    """No script reads an attack's `attacker` (the words for people) or writes a death's `cause` out, nor cuts a word off a
    name. (A tile's `cause`, "dig" or "place", is a code already: state.js reads it as one.)"""
    hits = [f"{p.name}:{i}: {line.strip()[:120]}" for p in sorted(JS.glob("*.js")) for i, line in enumerate(p.read_text().splitlines(), 1)
            if re.search(r"\be\.attacker\b|\$\{e\.cause\}|String\(e\.(cause|attacker)\b|\.slice\(2\)", line)]
    assert not hits, hits
