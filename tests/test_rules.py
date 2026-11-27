"""The world's rules are said once (rules.py): the screen has them from the server, and types none of them again."""

import asyncio
import json
import re

from nexel_worlds import tiles as T
from nexel_worlds.rules import FILE, rules_js, rules_table
from nexel_worlds.server import GameServer
from nexel_worlds.sim.entities import CREATURES

JS = FILE.parent
SOURCES = {f.name: f.read_text() for f in sorted(JS.glob("*.js")) if f.name != FILE.name}
# the tables the client typed for itself, before: none may be given a value of its own again (vocab.js fills the
# ones it keeps from the server's table; an empty one to fill is all that may be written)
TABLES = ["recipes", "CH", "CHAR", "GROUND", "SOLID", "WALKABLE_GROUND", "DEPTH_OF", "FOOT", "FILLS", "PLACEABLE_BLOCK", "TOOL_FOR", "WEAPON_DMG", "INSTANT_DIG", "FEEDS", "FOODS", "LAND_BLOCKS", "ASIDE", "MEANWHILE", "WEAR", "CROPS", "foodValue", "PICK"]
NUMBERS = ["USE_R", "LAYER", "CAN_SIZE", "FLEE_STRIDE", "BITE_HIGH", "SPRING_S", "CLIMB_S", "STOREY", "SEA", "LOW", "HIGH"]


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
    assert FILE.read_text() == rules_js(), "web/js/rules.js is not rules.py's table: uv run python -m nexel_worlds.rules"
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


# THE CLIENT'S OWN TABLES keyed by the world's names: a tile's char, an item's or a tile's name, a creature's kind. Each
# says what only the screen has (its art, its sounds, its words), so it is kept here, with why; a rule of the world
# goes in rules.py's table instead (the bare plant a picked one leaves, tiles.js, was the last one typed: RULES.picked).
# A table found that is not on this list fails, and so does one on it that names something the world does not have.
KEPT = {
    "assets.js LATE": "art: the sheets of the creatures drawn later than the rest",
    "blurbs.js BLURB": "words: what the book says of each thing",
    "build.js SWAP": "the screen's own help: build mode takes the wall down first, then puts the door (two actions)",
    "characters.js SWING_ROW": "art: a tool's row in the swing sheet",
    "characters.js AMBLE": "motion: how fast a creature's picture glides between the tiles the world gives it",
    "craft.js RECIPE_GROUPS": "the book's pages: which recipes are shown together",
    "cube_icons.js CUBES": "art: the blocks drawn as cubes in the bar",
    "effects.js PCOL": "art: the colours of the bits a tile breaks into",
    "effects.js KICK": "art: the dust a step kicks up, by ground",
    "goals.js GOALS": "words: the player's first goals and their icons (kept on the page, localStorage)",
    "hd_cards.js CARD": "art: the things drawn as an upright card",
    "hold_art.js ROW": "art: a tool's row in the held sheet",
    "hold_art.js SHAPES": "art: the shapes of the held tools",
    "intent.js FILL_TEXT": "words: what a fill is called, by the ground it makes",
    "intent.js FILL_HELP": "words: the help line of each filler",
    "intent.js HARVEST": "words: what taking each thing is called",
    "ore_paint.js COL": "art: an ore's colour in the rock",
    "sound_of.js STRIKE": "sound: a hit, by what a thing is made of",
    "sound_of.js BREAK": "sound: a break, by what a thing is made of",
    "sound_of.js STEP": "sound: a footstep, by the ground",
    "sound_of.js VOICE": "sound: an animal's voice",
    "tiles.js MARKS": "art: what is drawn on a ground (tilled soil, ash, a floor, a path)",
    "title_cast.js HARD": "the title scene's cast: grounds its actors walk round",
    "title_errands.js WORK": "the title scene's cast: what its actors do in the field and woods",
    "ui.js ICONS": "art: an item's icon",
    "ui.js BARE": "art: the icons drawn without a ring",
    "wear.js LOOK": "art: how each worn thing is drawn",
    "world_decor.js CROP_ROW": "art: a crop's row in the crops sheet",
    "world_decor.js ANIMALS": "art: the farm animals' sheets",
    "world_decor.js WILD": "art: the wild creatures' frames",
    "world_decor.js CRY": "sound: the wild creatures' cries",
    "world_decor.js VARIANTS": "art: the farm animals' looks",
    # (keyed by something else that happens to be spelt like a tile's char: keys, faces, palettes)
    "keyboard.js BOOK_KEYS": "the keyboard's keys", "keyboard.js HELD": "the keyboard's keys", "mouse.js FACE": "a block's faces",
    "target_box.js FACES": "a block's faces", "race_list.js BASE": "a palette's letters", "race_list.js EXTRA": "a palette's letters",
    "wear.js BASE": "a palette's letters", "wear.js BODY": "a palette's letters", "render.js WATCH": "a place: x, y, z",
    "voxpaint.js SLIM": "a shape's letters",
    "tool_art.js METAL": "art: a tool tier's metal colours, in the paw and its swing (#393)",
}
# the kept tables with keys of their own besides the world's (a group's title, a goal's words, a material, a pose, the
# kind a tiered tool is drawn as: vocab.js toolArt, every sword the "sword"): in
# every other one, each key is a tile, an item or a creature the world has (a name dropped or changed there fails here)
MIXED = {"assets.js LATE", "characters.js SWING_ROW", "tool_art.js METAL", "craft.js RECIPE_GROUPS", "effects.js PCOL", "goals.js GOALS", "sound_of.js STRIKE", "sound_of.js BREAK",
         "keyboard.js BOOK_KEYS", "keyboard.js HELD", "mouse.js FACE", "target_box.js FACES", "race_list.js BASE", "wear.js BASE", "render.js WATCH", "voxpaint.js SLIM"}


def _client_tables():
    """Every UPPER_CASE table literal of the client keyed by the world's names, -> {"file NAME": (keys, matched)}."""
    t = rules_table()
    chars = set(t["tiles"])
    names = ({v["name"] for v in t["tiles"].values()} | set(t["place"]) | set(t["food"]) | set(t["tools"]) | set(t["weapons"])
             | set(t["wear"]) | set(t["crops"]) | set(t["feed"]) | set(t["recipes"]) | {i for r in t["recipes"].values() for i in r["inputs"]})
    names |= {d[0] for c in CREATURES.values() for d in c.get("drops", ())}         # (what a creature leaves)
    kinds = set(CREATURES)
    found = {}
    for file, src in SOURCES.items():
        if file == "vocab.js":
            continue                                                       # (the client's vocabulary: filled from the table, and its words for it)
        for m in re.finditer(r"\bconst\s+([A-Z][A-Z0-9_]+)\s*=\s*(\{|new Set\(\[|\[)", src):
            i, opn = m.end() - 1, src[m.end() - 1]
            depth, j, q = 0, i, None
            while j < len(src):                                            # (to its closing bracket, strings skipped)
                c = src[j]
                if q:
                    q = None if c == q and src[j - 1] != "\\" else q
                elif c in "\"'`":
                    q = c
                elif c == opn:
                    depth += 1
                elif c == {"{": "}", "[": "]"}[opn]:
                    depth -= 1
                    if not depth:
                        break
                j += 1
            body = src[i + 1:j]
            if opn == "{":
                for _ in range(4):
                    body = re.sub(r"\{[^{}]*\}|\[[^\[\]]*\]", "0", body)
                keys = [a or b or c for a, b, c in re.findall(r"""(?:^|,)\s*(?:"((?:[^"\\]|\\.)+)"|'([^']+)'|([A-Za-z_]\w*))\s*:""", body)]
                keys = [k.replace('\\"', '"') for k in keys]
            else:
                keys = re.findall(r"""["']([^"'\n]{1,20})["']""", body)
            for world in (names, kinds, {c for c in chars if len(c) == 1}):
                hit = [k for k in keys if k in world]
                if len(hit) >= 2 and len(hit) >= .5 * len(keys):
                    found[f"{file} {m.group(1)}"] = (keys, world)
                    break
    return found


def test_the_clients_own_tables_keyed_by_the_worlds_names_are_its_art_sounds_and_words():
    found = _client_tables()
    new = sorted(set(found) - set(KEPT))
    assert not new, f"a table keyed by the world's names typed in the client: put it in rules.py's table, or say here why only the screen has it: {new}"
    assert not set(KEPT) - set(found), f"kept, but no longer there: {sorted(set(KEPT) - set(found))}"
    stale = {k: [n for n in keys if n not in world] for k, (keys, world) in found.items() if k not in MIXED}
    assert not any(stale.values()), f"keyed by what the world does not have (rules.py's names): {({k: v for k, v in stale.items() if v})}"
