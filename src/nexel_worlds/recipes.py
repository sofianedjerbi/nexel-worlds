"""The recipes: what each thing is made of, how long it takes and at which station (tiles.py re-exports them: one
place for the world's rules, cut by concern)."""

from dataclasses import dataclass


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
        Recipe("roof", {"wood": 1}, {"roof": 2}, 3),
        Recipe("ladder", {"wood": 2}, {"ladder": 1}, 3),
        Recipe("stairs", {"wood": 1}, {"stairs": 2}, 3),   # a step each: a flight up a storey takes two (sim/climbing.py)       # shingles: a block laid a storey up, on walls or beside a block (sim/storeys.py)
        Recipe("stone", {"stone_block": 1}, {"stone": 2}, 2),   # a block of the land broken up: the material (a block dug is the block: landblocks.py)
        Recipe("path", {"stone": 2}, {"path": 2}, 3),
        Recipe("fence", {"wood": 2}, {"fence": 1}, 3),
        Recipe("door", {"wood": 3}, {"door": 1}, 4),
        Recipe("sign", {"wood": 1}, {"sign": 1}, 2),
        Recipe("flag", {"wood": 1, "fiber": 1}, {"flag": 1}, 2),
        Recipe("campfire", {"wood": 3, "stone": 2}, {"campfire": 1}, 4),
        Recipe("torch", {"wood": 1, "fiber": 1}, {"torch": 1}, 2),
        Recipe("rope", {"fiber": 3}, {"rope": 1}, 3),
        Recipe("name_tag", {"plank": 1, "fiber": 1}, {"name_tag": 1}, 2),     # a name for an animal: used up on it (sim/animals.py)
        Recipe("wood_axe", {"wood": 3, "fiber": 1}, {"wood_axe": 1}, 4),            # the first tools: no workbench
        Recipe("wood_pickaxe", {"wood": 3, "fiber": 1}, {"wood_pickaxe": 1}, 4),
        Recipe("axe", {"wood": 2, "stone": 2, "fiber": 1}, {"axe": 1}, 6, "workbench"),
        Recipe("pickaxe", {"wood": 2, "stone": 3, "fiber": 1}, {"pickaxe": 1}, 6, "workbench"),
        Recipe("copper_axe", {"wood": 2, "copper_ingot": 2}, {"copper_axe": 1}, 6, "workbench"),
        Recipe("copper_pickaxe", {"wood": 2, "copper_ingot": 3}, {"copper_pickaxe": 1}, 6, "workbench"),
        Recipe("iron_axe", {"wood": 2, "iron_ingot": 2}, {"iron_axe": 1}, 7, "workbench"),
        Recipe("iron_pickaxe", {"wood": 2, "iron_ingot": 3}, {"iron_pickaxe": 1}, 7, "workbench"),
        Recipe("titanium_axe", {"wood": 2, "titanium_ingot": 2}, {"titanium_axe": 1}, 8, "workbench"),
        Recipe("titanium_pickaxe", {"wood": 2, "titanium_ingot": 3}, {"titanium_pickaxe": 1}, 8, "workbench"),
        Recipe("wood_sword", {"wood": 3, "fiber": 1}, {"wood_sword": 1}, 4),
        Recipe("stone_sword", {"wood": 1, "stone": 2, "fiber": 1}, {"stone_sword": 1}, 6, "workbench"),
        Recipe("copper_sword", {"copper_ingot": 2, "wood": 1}, {"copper_sword": 1}, 7, "workbench"),
        Recipe("iron_sword", {"iron_ingot": 2, "wood": 1}, {"iron_sword": 1}, 8, "workbench"),
        Recipe("titanium_sword", {"titanium_ingot": 2, "wood": 1}, {"titanium_sword": 1}, 9, "workbench"),
        Recipe("hoe", {"wood": 2, "stone": 1}, {"hoe": 1}, 5, "workbench"),
        Recipe("spear", {"wood": 2, "stone": 1, "fiber": 1}, {"spear": 1}, 5, "workbench"),
        Recipe("stone_wall", {"stone": 3}, {"stone_wall": 1}, 5, "workbench"),
        Recipe("chest", {"wood": 6}, {"chest": 1}, 6, "workbench"),
        Recipe("cooked_meat", {"meat": 1}, {"cooked_meat": 1}, 5, "campfire"),
        Recipe("bread", {"wheat": 3}, {"bread": 1}, 5, "campfire"),
        Recipe("iron_ingot", {"iron_ore": 1, "coal": 1}, {"iron_ingot": 1}, 10, "campfire"),     # smelting: an ore and coal to burn
        Recipe("copper_ingot", {"copper_ore": 1, "coal": 1}, {"copper_ingot": 1}, 8, "campfire"),
        Recipe("titanium_ingot", {"titanium_ore": 2, "coal": 2}, {"titanium_ingot": 1}, 14, "campfire"),
        Recipe("gold_coin", {"gold_ore": 1, "coal": 1}, {"gold_coin": 3}, 10, "campfire"),       # gold is money: minted, never a tool
        Recipe("gold_ingot", {"gold_ore": 1, "coal": 1}, {"gold_ingot": 1}, 10, "campfire"),     # or cast, for gold armour
        Recipe("wire", {"copper_ingot": 1}, {"wire": 3}, 4, "workbench"),                      # copper's electrical parts
        Recipe("watering_can", {"stone": 3, "wood": 1}, {"watering_can": 1}, 6, "workbench"),
        Recipe("bed", {"wood": 6, "fiber": 3}, {"bed": 1}, 8, "workbench"),
        Recipe("chair", {"wood": 2}, {"chair": 1}, 4, "workbench"),
        Recipe("table", {"wood": 4}, {"table": 1}, 5, "workbench"),
        Recipe("clock", {"wood": 2, "iron_ingot": 1}, {"clock": 1}, 6, "workbench"),
        Recipe("rug", {"fiber": 4}, {"rug": 1}, 4),
        Recipe("plant", {"stone": 1, "flower": 1}, {"plant": 1}, 3),
        Recipe("gate", {"wood": 3}, {"gate": 1}, 4),
        Recipe("wood_wall", {"wood": 3}, {"wood_wall": 2}, 5, "workbench"),
        Recipe("boat", {"wood": 8, "rope": 1}, {"boat": 1}, 10, "workbench"),
        Recipe("mailbox", {"wood": 3}, {"mailbox": 1}, 4, "workbench"),
        Recipe("well", {"stone": 8, "wood": 2, "rope": 1}, {"well": 1}, 10, "workbench"),
        Recipe("coop", {"wood": 8, "fiber": 2}, {"coop": 1}, 8, "workbench"),
        Recipe("picnic_blanket", {"fiber": 6}, {"picnic_blanket": 1}, 4),
        Recipe("basket", {"fiber": 3}, {"basket": 1}, 3),
        Recipe("hay", {"wheat": 3}, {"hay": 1}, 3),
        Recipe("trough", {"wood": 4}, {"trough": 1}, 5, "workbench"),
        Recipe("hob", {"stone": 8, "campfire": 1}, {"hob": 1}, 10, "workbench"),     # a clay dome round a fire: set down, it walks (sim/hob.py)
    ]
}


STATIONS = sorted({r.station for r in RECIPES.values() if r.station})


def can_craft(r: Recipe, inv: dict, stations=(), n: int = 1) -> dict:
    """Can `n` of it be made, with this bag and these stations within reach? The one answer (the world's craft, what
    it tells each player of themselves, a screen's craft book). -> n: how many times the bag allows; missing: what is
    short for the `n` asked; station: the station it wants and has not; ok."""
    missing = {k: v * n - inv.get(k, 0) for k, v in r.inputs.items() if inv.get(k, 0) < v * n}
    station = r.station if r.station and r.station not in stations else None
    return {"ok": not missing and not station, "n": min(inv.get(k, 0) // v for k, v in r.inputs.items()), "missing": missing, "station": station}
