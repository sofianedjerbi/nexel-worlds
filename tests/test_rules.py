"""The world's rules are said once (rules.py): the screen has them from the server, and types none of them again."""

import asyncio
import json
import re
from pathlib import Path

from megastructure import tiles as T
from megastructure.rules import FILE, rules_js, rules_table
from megastructure.server import GameServer

JS = FILE.parent
SOURCES = {f.name: f.read_text() for f in sorted(JS.glob("*.js")) if f.name != FILE.name}
# the tables the client typed for itself, before: none may be given a value of its own again (vocab.js fills the
# ones it keeps from the server's table; an empty one to fill is all that may be written)
TABLES = ["CH", "CHAR", "GROUND", "SOLID", "WALKABLE_GROUND", "DEPTH_OF", "FOOT", "FILLS", "PLACEABLE_BLOCK", "TOOL_FOR", "WEAPON_DMG", "INSTANT_DIG", "FEEDS", "FOODS", "LAND_BLOCKS", "ASIDE", "MEANWHILE", "WEAR", "CROPS", "foodValue"]
NUMBERS = ["CAN_SIZE", "FLEE_STRIDE", "BITE_HIGH", "SPRING_S", "CLIMB_S", "STOREY", "SEA", "LOW", "HIGH"]


def hello(tmp_path) -> dict:
    class Ws:
        request = type("R", (), {"path": "/spectate", "headers": {}})()
        sent = []

        async def send(self, m):
            self.sent.append(json.loads(m))

        def __aiter__(self):
            async def it():
                return
                yield
            return it()

    asyncio.run(GameServer(tmp_path / "w", seed=3).spectate(ws := Ws()))
    return ws.sent[0]


def test_the_hello_says_the_table_and_the_page_has_the_same_one(tmp_path):
    table = json.loads(json.dumps(rules_table()))
    assert hello(tmp_path)["rules"] == table
    assert FILE.read_text() == rules_js(), "web/js/rules.js is not rules.py's table: uv run python -m megastructure.rules"
    assert json.loads(FILE.read_text().split("const RULES = ", 1)[1].rstrip(";\n")) == table


def test_the_table_is_the_servers_own_constants():
    t = rules_table()
    by_name = {v["name"]: v for v in t["tiles"].values()}
    assert len(by_name) == len(t["tiles"]) == len(T.GROUNDS) + len(T.BLOCKS) - 1          # a char each, none twice
    for b in T.BLOCKS[1:]:
        said = by_name[b.name]
        assert (said.get("solid", False), said.get("burns", False), said.get("tool"), said.get("needs")) == (b.solid, b.flammable, b.tool, b.needs_tool)
    assert by_name["cave_wall"]["tool"] == "pickaxe" and all(by_name[n]["burns"] for n in ("clock", "ladder", "flower"))    # (three that had drifted)
    assert t["fills"]["stone_block"] == t["fills"]["dirt"] and t["fills"]["plank"]["~"] == ":"                               # (and the fourth)
    assert by_name["flower"]["quick"] and by_name["berry_bush"]["quick"] and "quick" not in by_name["tree"]
    assert "seed" not in t["place"] and t["sown"] == {"seed": "ou"} and t["place"]["roof"] == "roof"


def test_everything_the_client_reads_is_in_the_table_and_everything_in_it_is_read():
    read = {k for src in SOURCES.values() for k in re.findall(r"\bRULES\.(\w+)", src)}
    read |= {k for src in SOURCES.values() for names in re.findall(r"\{([^{}]*)\} = RULES\b", src) for k in re.findall(r"(\w+):", names)}
    read |= set(re.findall(r"\br\.(\w+)", SOURCES["vocab.js"]))                             # (setRules(r) fills the client's tables)
    assert read == set(rules_table()), (read ^ set(rules_table()))
    tile_keys = {k for v in rules_table()["tiles"].values() for k in v}
    asked = {k for k in tile_keys if any(re.search(rf'\bof\("{k}"\)|\btileOf\(.*\)\.{k}\b', src) for src in SOURCES.values())}
    assert asked == tile_keys - {"liquid"}, asked ^ tile_keys                               # (liquid: said by its depth, DEPTH_OF)


def test_no_rule_table_is_typed_in_the_client_again():
    again = re.compile(r"\b(?:(?:" + "|".join(TABLES) + r")\s*=\s*(?:\{(?!\})|\[(?!\])|new Set\((?!\))|[\"'`])|(?:" + "|".join(NUMBERS) + r")\s*=\s*[\d.-])")
    found = [f"{name}: {m.group(0)}" for name, src in SOURCES.items() for m in again.finditer(src)]
    assert not found, f"typed in the client again (rules.py has it; read RULES): {found}"
    # the server's own lists, as a literal: its solid things, its grounds, what burns, the feed
    t = rules_table()["tiles"]
    for what in ("solid", "ground", "burns", "walk"):
        chars = {c for c, v in t.items() if v.get(what)}
        for name, src in SOURCES.items():
            if name == "title_map.js":
                continue                                                                    # (the baked island: rows of tile chars)
            for lit in re.findall(r'"((?:[^"\\\n]|\\.){8,60})"', src):
                raw = lit.replace('\\"', '"').replace("\\'", "'")
                assert not (len(set(raw)) == len(raw) and len(set(raw) & chars) >= .8 * max(len(chars), len(raw)) and set(raw) <= set(t)), f"{name}: \"{lit}\" is the server's `{what}` list"
