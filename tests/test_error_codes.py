"""A refusal says why as data (#6): its `code` and `data` ({tool, have}, {what} or {why}), the page's words made from them
(web/js/agent.js ERROR_TEXT); `detail` is the agents' sentence, read by nothing that decides."""

import re
from pathlib import Path

from helpers import run

JS = Path(__file__).parent.parent / "src" / "nexel_worlds" / "web" / "js"


def test_a_tool_missing_is_said_by_its_name_and_whether_you_have_one(world):
    sim, a = world
    sim.world.set(a.x + 1, a.y, block="ore")
    r = run(sim, a, "dig", {"dir": "E"})
    assert (r["error"], r["data"]) == ("need_tool", {"tool": "pickaxe", "have": False}), r
    a.add("pickaxe", 1)
    assert run(sim, a, "dig", {"dir": "E"})["data"] == {"tool": "pickaxe", "have": True}     # (in the bag, not in hand)
    assert "pickaxe" in r["detail"]                                                          # (the agents' words, as they were)


def test_an_item_missing_is_said_by_the_item_and_how_many(world):
    sim, a = world
    r = run(sim, a, "drop", {"item": "plank", "n": 2})
    assert (r["error"], r["data"]) == ("missing_item", {"item": "plank", "have": 0, "need": 2}), r
    a.add("plank", 1)
    assert run(sim, a, "drop", {"item": "plank", "n": 2})["data"] == {"item": "plank", "have": 1, "need": 2}


def test_what_is_in_the_way_is_said_by_what_it_is(world):
    sim, a = world
    bob = sim.login("Bob", "tok2")
    bob.x, bob.y = a.x + 1, a.y
    a.add("wood_wall", 1)
    r = run(sim, a, "place", {"dir": "E", "item": "wood_wall"})
    assert (r["error"], r["data"]) == ("occupied", {"on": "body"}), r


def test_a_wrong_target_says_why_by_a_code(world):
    sim, a = world
    r = run(sim, a, "attack", {"target": a.id})
    assert (r["error"], r["data"]) == ("bad_target", {"why": "self"}), r
    assert re.search(r"bad_target: \(d\) => \(Object\.hasOwn\(TARGET_WHY, d\.why\)", (JS / "agent.js").read_text())


def test_what_cannot_be_dug_is_named():
    from nexel_worlds.sim.entities import ActionError, failure
    r = failure(ActionError("cannot_dig", "water cannot be dug", what="water"))
    assert (r["error"], r["data"], r["detail"]) == ("cannot_dig", {"what": "water"}, "water cannot be dug")
    assert "data" not in failure(ActionError("too_soon", "wait"))                           # (none: none sent)


def test_the_page_shows_a_refusal_by_its_code():
    """What a refusal says on the page comes from errorText (its code and data, else `detail`): nothing else reads `detail`."""
    hits = [f"{p.name}:{i}: {line.strip()[:120]}" for p in sorted(JS.glob("*.js")) for i, line in enumerate(p.read_text().splitlines(), 1)
            if "r.detail" in line and "const errorText" not in line]
    assert not hits, hits
    assert re.search(r"Object\.hasOwn\(ERROR_TEXT, r\.error\)", (JS / "agent.js").read_text())


def test_every_reason_a_block_cannot_go_has_words_on_the_page():
    """block_fits' codes (storeys.py, BLOCK_WHY) are said on the page by build mode's words (floors.js WHY) or agent.js'
    TARGET_WHY; and "changed" (the world moved under you) is worded with no data sent."""
    from nexel_worlds.sim.entities import BLOCK_WHY
    js = (JS / "floors.js").read_text() + (JS / "agent.js").read_text()
    missing = [c for c in BLOCK_WHY if not re.search(rf"\b{c}: (\(\) => )?\"", js)]
    assert not missing, missing
    assert re.search(r"changed: \(\) => \"", (JS / "agent.js").read_text())


def test_every_refusal_the_game_makes_has_words_on_the_page():
    """Every code an ActionError is raised with has its words in agent.js ERROR_TEXT: a new one cannot reach people as the
    agents' sentence. (bad_args: a request the page itself made wrong, its detail says how; too_soon: never shown.)"""
    src = Path(__file__).parent.parent / "src" / "nexel_worlds"
    codes = {c for p in src.rglob("*.py") for c in re.findall(r'ActionError\("([a-z_]+)"', p.read_text())}
    js = (JS / "agent.js").read_text()
    table = js[js.index("const ERROR_TEXT = {"):js.index("\n};", js.index("const ERROR_TEXT = {"))]
    words = set(re.findall(r"(?:^\s+|, )([a-z_]+): \(", table, re.M))
    assert not codes - words - {"bad_args", "too_soon"}, sorted(codes - words - {"bad_args", "too_soon"})


def test_full_says_who_is_full(world):
    from nexel_worlds.sim.constants import FOOD_MAX
    sim, a = world
    a.add("berries", 1)
    a.hunger = FOOD_MAX
    r = run(sim, a, "eat", {"item": "berries"})
    assert (r["error"], r["data"]) == ("full", {"what": "you"}), r
