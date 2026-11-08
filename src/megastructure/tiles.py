"""Static tile, item and recipe tables.

Setting: an endless, self-extending built structure. Nobody remembers who started it;
autonomous accretors keep adding to it. Agents scavenge scrap, alloy and cable, grow
lichen and spore beds, and build (or wreck) whatever they like.
"""

from dataclasses import dataclass, field

DIRS = {"N": (0, -1), "E": (1, 0), "S": (0, 1), "W": (-1, 0)}


@dataclass(frozen=True)
class Ground:
    name: str
    char: str
    walkable: bool = True
    flammable: bool = False
    diggable: bool = True  # bare-ground dig turns it into a breach
    liquid: bool = False


@dataclass(frozen=True)
class Block:
    name: str
    char: str
    solid: bool = True
    flammable: bool = False
    hardness: int = 0  # ticks to dig by hand; 0 = cannot be dug
    drops: dict = field(default_factory=dict)
    tool: str | None = None  # tool that halves dig time
    needs_tool: str | None = None  # tool required to dig at all
    wall: bool = False  # counts as shelter


GROUNDS = [
    Ground("coolant", "~", walkable=False, diggable=False, liquid=True),
    Ground("grating", ":"),
    Ground("moss", ".", flammable=True),
    Ground("deck", ","),
    Ground("breach", "o"),
    Ground("plating", "_", diggable=False),
    Ground("slag", "'"),
    Ground("void", "=", walkable=False, diggable=False),
]
G = {g.name: i for i, g in enumerate(GROUNDS)}

BLOCKS = [
    Block("none", " ", solid=False),
    Block("scrap_heap", "T", flammable=True, hardness=12, drops={"scrap": 3}, tool="cutter"),
    Block("lichen", "b", solid=False, flammable=True, hardness=2, drops={"lichen": 2, "spore": 1}),
    Block("structure", "M", hardness=20, drops={"alloy": 2}, tool="drill", wall=True),
    Block("node", "*", hardness=24, drops={"core": 1, "alloy": 1}, needs_tool="drill", wall=True),
    Block("conduit", "H", hardness=6, drops={"cable": 2}, tool="cutter", wall=True),
    Block("terminal", "Q", hardness=10, drops={"circuit": 1, "scrap": 1}, tool="cutter", wall=True),
    Block("scrap_wall", "#", flammable=True, hardness=10, drops={"scrap_wall": 1}, tool="cutter", wall=True),
    Block("alloy_wall", "%", hardness=30, drops={"alloy_wall": 1}, tool="drill", wall=True),
    Block("hatch", "+", solid=False, flammable=True, hardness=8, drops={"hatch": 1}, tool="cutter", wall=True),
    Block("heater", "^", hardness=4, drops={"alloy": 1}),
    Block("bench", "&", flammable=True, hardness=8, drops={"bench": 1}, tool="cutter", wall=True),
    Block("sign", "?", solid=False, flammable=True, hardness=3, drops={"sign": 1}),
    Block("beacon", "!", solid=False, flammable=True, hardness=3, drops={"beacon": 1}),
    Block("fire", "x", solid=False),
    Block("spore_bed", "\"", solid=False, flammable=True, hardness=2, drops={"spore": 1}),
    Block("ripe_bed", "w", solid=False, flammable=True, hardness=2, drops={"cap": 3, "spore": 2}),
    Block("debris", "t", solid=False, hardness=3, drops={"scrap": 1}),
    Block("locker", "C", flammable=True, hardness=8, drops={"locker": 1}, tool="cutter", wall=True),
]
B = {b.name: i for i, b in enumerate(BLOCKS)}

# items that place as a block (item name -> block name)
PLACEABLE = {
    "scrap_wall": "scrap_wall",
    "alloy_wall": "alloy_wall",
    "hatch": "hatch",
    "heater": "heater",
    "bench": "bench",
    "sign": "sign",
    "beacon": "beacon",
    "spore": "spore_bed",
    "locker": "locker",
}
# items laid on the ground: item -> (grounds it can cover, resulting ground)
FILLERS = {
    "rubble": ({"breach", "coolant"}, "deck"),
    "alloy": ({"deck", "moss", "grating", "breach", "slag"}, "plating"),
}

FOOD = {"lichen": 8, "meat": 6, "cooked_meat": 25, "cap": 6, "ration": 30}

WEAPONS = {"arc_blade": 30, "pike": 18, "cutter": 12, "drill": 10}
FIST_DAMAGE = 5


@dataclass(frozen=True)
class Recipe:
    name: str
    inputs: dict
    output: dict
    ticks: int = 4
    station: str | None = None  # block that must be within 2 tiles


RECIPES = {
    r.name: r
    for r in [
        Recipe("bench", {"scrap": 4}, {"bench": 1}, 6),
        Recipe("scrap_wall", {"scrap": 2}, {"scrap_wall": 1}, 3),
        Recipe("hatch", {"scrap": 3}, {"hatch": 1}, 4),
        Recipe("sign", {"scrap": 1}, {"sign": 1}, 2),
        Recipe("beacon", {"scrap": 1, "cable": 1}, {"beacon": 1}, 2),
        Recipe("heater", {"scrap": 3, "alloy": 2}, {"heater": 1}, 4),
        Recipe("torch", {"scrap": 1, "cable": 1}, {"torch": 1}, 2),
        Recipe("cutter", {"scrap": 2, "alloy": 2, "cable": 1}, {"cutter": 1}, 6, "bench"),
        Recipe("drill", {"scrap": 2, "alloy": 3, "cable": 1}, {"drill": 1}, 6, "bench"),
        Recipe("pike", {"scrap": 2, "alloy": 1, "cable": 1}, {"pike": 1}, 5, "bench"),
        Recipe("alloy_wall", {"alloy": 3}, {"alloy_wall": 1}, 5, "bench"),
        Recipe("locker", {"scrap": 6}, {"locker": 1}, 6, "bench"),
        Recipe("cooked_meat", {"meat": 1}, {"cooked_meat": 1}, 5, "heater"),
        Recipe("ration", {"cap": 3}, {"ration": 1}, 5, "heater"),
        Recipe("ingot", {"core": 2}, {"ingot": 1}, 10, "heater"),
        Recipe("arc_blade", {"ingot": 1, "circuit": 1, "cable": 1}, {"arc_blade": 1}, 8, "bench"),
    ]
}
