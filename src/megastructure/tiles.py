"""Static tile, item and recipe tables.

Setting: an endless archipelago of grassy islands. People wake up here with nothing; they chop,
dig, farm, build and fence, trade, steal and burn. There are no rules and no safe zones.
Durations (`hardness`, recipe `ticks`) are in tenths of a second.
"""

from dataclasses import dataclass, field

DIRS = {"N": (0, -1), "E": (1, 0), "S": (0, 1), "W": (-1, 0)}


@dataclass(frozen=True)
class Ground:
    name: str
    char: str
    walkable: bool = True
    flammable: bool = False
    diggable: bool = True  # bare-ground dig tills it
    liquid: bool = False


@dataclass(frozen=True)
class Block:
    name: str
    char: str
    solid: bool = True
    flammable: bool = False
    hardness: int = 0  # tenths of a second to dig by hand; 0 = cannot be dug
    drops: dict = field(default_factory=dict)
    tool: str | None = None  # tool that halves dig time
    needs_tool: str | None = None  # tool required to dig at all
    wall: bool = False  # counts as shelter


GROUNDS = [
    Ground("water", "~", walkable=False, diggable=False, liquid=True),
    Ground("bridge", ":"),
    Ground("grass", ".", flammable=True),
    Ground("dirt", ","),
    Ground("tilled", "o"),
    Ground("cobble", "_", diggable=False),
    Ground("ash", "'"),
    Ground("deep_water", "=", walkable=False, diggable=False, liquid=True),
    Ground("wet_tilled", "u"),  # watered soil: crops grow twice as fast; dries when the crop grows
    Ground("floor", "n", diggable=False),  # wooden floor laid from planks
]
G = {g.name: i for i, g in enumerate(GROUNDS)}

BLOCKS = [
    Block("none", " ", solid=False),
    Block("tree", "T", flammable=True, hardness=12, drops={"wood": 3}, tool="axe", wall=True),
    Block("berry_bush", "b", flammable=True, hardness=3, drops={"berries": 2, "seed": 1}),
    Block("rock", "M", hardness=18, drops={"stone": 2}, tool="pickaxe", wall=True),
    Block("ore", "*", hardness=24, drops={"ore": 1, "stone": 1}, needs_tool="pickaxe", wall=True),
    Block("thicket", "H", flammable=True, hardness=5, drops={"fiber": 2}, tool="axe", wall=True),
    Block("mushroom", "Q", solid=False, hardness=2, drops={"mushroom": 1}),
    Block("fence", "#", flammable=True, hardness=8, drops={"fence": 1}, tool="axe", wall=True),
    Block("stone_wall", "%", hardness=30, drops={"stone_wall": 1}, tool="pickaxe", wall=True),
    Block("door", "+", solid=False, flammable=True, hardness=8, drops={"door": 1}, tool="axe", wall=True),
    Block("campfire", "^", hardness=4, drops={"stone": 1}),
    Block("workbench", "&", flammable=True, hardness=8, drops={"workbench": 1}, tool="axe", wall=True),
    Block("sign", "?", solid=False, flammable=True, hardness=3, drops={"sign": 1}),
    Block("flag", "!", solid=False, flammable=True, hardness=3, drops={"flag": 1}),
    Block("fire", "x", solid=False),
    Block("crop", "\"", solid=False, flammable=True, hardness=2, drops={"seed": 1}),
    Block("ripe_crop", "w", solid=False, flammable=True, hardness=2, drops={"wheat": 3, "seed": 2}),
    Block("stump", "t", solid=False, hardness=4, drops={"wood": 1}),
    Block("chest", "C", flammable=True, hardness=8, drops={"chest": 1}, tool="axe", wall=True),
    # appended (block ids are stored in saved chunks, so new blocks go at the end)
    Block("fruit_tree", "F", flammable=True, hardness=5, drops={"fruit": 3}, wall=True),  # picking: fruit regrows
    Block("sprout", ";", solid=False, flammable=True, hardness=2, drops={"seed": 1}),
    Block("flower", "f", solid=False, flammable=True, hardness=1, drops={"flower": 1}),
    Block("bed", "B", flammable=True, hardness=8, drops={"bed": 1}, tool="axe", wall=True),
    Block("chair", "h", flammable=True, hardness=4, drops={"chair": 1}, tool="axe"),
    Block("table", "L", flammable=True, hardness=6, drops={"table": 1}, tool="axe", wall=True),
    Block("plant", "p", hardness=3, drops={"plant": 1}),
    Block("clock", "K", flammable=True, hardness=4, drops={"clock": 1}, tool="axe", wall=True),
    Block("rug", "r", solid=False, flammable=True, hardness=3, drops={"rug": 1}),
    Block("gate", "g", solid=False, flammable=True, hardness=8, drops={"gate": 1}, tool="axe", wall=True),
    Block("wood_wall", "W", flammable=True, hardness=10, drops={"wood_wall": 1}, tool="axe", wall=True),
    Block("boat", "V", solid=False, flammable=True, hardness=6, drops={"boat": 1}, tool="axe"),  # moored on water
    Block("mailbox", "X", flammable=True, hardness=6, drops={"mailbox": 1}, tool="axe"),
]

# Crop species: which plant a sprout becomes is a pure function of its tile, shared with the web client
# (index.html cropSpecies) so both agree without sending extra state.
CROPS = ["wheat", "pumpkin", "cauliflower", "lettuce", "eggplant", "carrot"]


def crop_species(x: int, y: int) -> str:
    h = (((x * 73856093) & 0xFFFFFFFF) ^ ((y * 19349663) & 0xFFFFFFFF)) & 0xFFFFFFFF
    return CROPS[h % len(CROPS)]
B = {b.name: i for i, b in enumerate(BLOCKS)}

# items that place as a block (item name -> block name)
PLACEABLE = {
    "fence": "fence",
    "stone_wall": "stone_wall",
    "door": "door",
    "campfire": "campfire",
    "workbench": "workbench",
    "sign": "sign",
    "flag": "flag",
    "seed": "sprout",
    "chest": "chest",
    "flower": "flower",
    "wood_wall": "wood_wall", "boat": "boat", "mailbox": "mailbox", "bed": "bed", "chair": "chair", "table": "table", "plant": "plant", "clock": "clock", "rug": "rug", "gate": "gate",
}
# Items laid into the ground: item -> {ground it can go on: resulting ground}. One item, one obvious result
# per surface; raw materials (wood, stone, fiber, ore) are never placeable themselves.
LAND = ("grass", "dirt", "ash")
FILLERS = {
    "dirt": {"tilled": "dirt", "wet_tilled": "dirt", "water": "dirt"},
    "path": {g: "cobble" for g in LAND},
    "plank": {"water": "bridge", **{g: "floor" for g in LAND}},
}
SEED_GROUNDS = {"tilled", "wet_tilled"}  # seeds only take on tilled soil

FOOD = {"pumpkin": 14, "cauliflower": 10, "lettuce": 8, "eggplant": 10, "carrot": 9, "fruit": 10, "berries": 8, "mushroom": 6, "egg": 10, "meat": 6, "cooked_meat": 25, "wheat": 4, "bread": 30, "milk": 12}

WEAPONS = {"sword": 30, "spear": 18, "axe": 12, "pickaxe": 10}
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
        Recipe("workbench", {"wood": 4}, {"workbench": 1}, 6),
        Recipe("plank", {"wood": 1}, {"plank": 2}, 3),
        Recipe("path", {"stone": 2}, {"path": 2}, 3),
        Recipe("fence", {"wood": 2}, {"fence": 1}, 3),
        Recipe("door", {"wood": 3}, {"door": 1}, 4),
        Recipe("sign", {"wood": 1}, {"sign": 1}, 2),
        Recipe("flag", {"wood": 1, "fiber": 1}, {"flag": 1}, 2),
        Recipe("campfire", {"wood": 3, "stone": 2}, {"campfire": 1}, 4),
        Recipe("torch", {"wood": 1, "fiber": 1}, {"torch": 1}, 2),
        Recipe("rope", {"fiber": 3}, {"rope": 1}, 3),
        Recipe("axe", {"wood": 2, "stone": 2, "fiber": 1}, {"axe": 1}, 6, "workbench"),
        Recipe("pickaxe", {"wood": 2, "stone": 3, "fiber": 1}, {"pickaxe": 1}, 6, "workbench"),
        Recipe("spear", {"wood": 2, "stone": 1, "fiber": 1}, {"spear": 1}, 5, "workbench"),
        Recipe("stone_wall", {"stone": 3}, {"stone_wall": 1}, 5, "workbench"),
        Recipe("chest", {"wood": 6}, {"chest": 1}, 6, "workbench"),
        Recipe("cooked_meat", {"meat": 1}, {"cooked_meat": 1}, 5, "campfire"),
        Recipe("bread", {"wheat": 3}, {"bread": 1}, 5, "campfire"),
        Recipe("ingot", {"ore": 2}, {"ingot": 1}, 10, "campfire"),
        Recipe("sword", {"ingot": 2, "wood": 1}, {"sword": 1}, 8, "workbench"),
        Recipe("watering_can", {"stone": 3, "wood": 1}, {"watering_can": 1}, 6, "workbench"),
        Recipe("bed", {"wood": 6, "fiber": 3}, {"bed": 1}, 8, "workbench"),
        Recipe("chair", {"wood": 2}, {"chair": 1}, 4, "workbench"),
        Recipe("table", {"wood": 4}, {"table": 1}, 5, "workbench"),
        Recipe("clock", {"wood": 2, "ingot": 1}, {"clock": 1}, 6, "workbench"),
        Recipe("rug", {"fiber": 4}, {"rug": 1}, 4),
        Recipe("plant", {"stone": 1, "flower": 1}, {"plant": 1}, 3),
        Recipe("gate", {"wood": 3}, {"gate": 1}, 4),
        Recipe("wood_wall", {"wood": 3}, {"wood_wall": 2}, 5, "workbench"),
        Recipe("boat", {"wood": 8, "rope": 1}, {"boat": 1}, 10, "workbench"),
        Recipe("mailbox", {"wood": 3}, {"mailbox": 1}, 4, "workbench"),
    ]
}
