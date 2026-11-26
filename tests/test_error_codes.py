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
