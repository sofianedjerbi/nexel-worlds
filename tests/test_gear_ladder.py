"""One ladder for tools and armour (#393, the owner: "tiers on armor too, like Minecraft"): wood < stone < copper < iron
< titanium for the pickaxe, the axe and the sword; leather < copper < gold < iron < titanium for the four pieces of
armour, each tier's set rising in what it turns; an old save's sword is the iron one (in a pack, a pile, a chest:
sim/persistence.py; the paw holds what the screen picks from the pack)."""

from helpers import make

from nexel_worlds.ores import TIERS, TOOLS
from nexel_worlds.sim.wear import ARMOR_CAP
from nexel_worlds.tiles import RECIPES, WEAPONS
from nexel_worlds.wearables import ARMOR, SETS, WEAR


def test_every_tier_has_a_pickaxe_an_axe_and_a_sword_each_made_and_each_hitting_harder_a_tier_up():
    for kind in ("axe", "pickaxe", "sword"):
        ladder = [f"{t}_{kind}" if kind == "sword" or t != "stone" else kind for t in TIERS]
        assert all(item in RECIPES for item in ladder), (kind, [i for i in ladder if i not in RECIPES])
        hits = [WEAPONS[item] for item in ladder]
        assert hits == sorted(set(hits)), (kind, hits)                   # (rising, no two alike)
    assert all(TOOLS[f"{t}_axe" if t != "stone" else "axe"][1] == i for i, t in enumerate(TIERS))
    assert all(WEAPONS[f"{t}_sword"] > WEAPONS[f"{t}_axe" if t != "stone" else "axe"] for t in TIERS)   # (a sword is the weapon)


def test_every_armour_tier_is_a_set_of_four_made_of_its_material_turning_more_a_tier_up():
    order = ["leather", "copper", "gold", "iron", "titanium"]
    assert list(SETS) == order
    each = []
    for tier in order:
        pieces = SETS[tier]
        assert set(pieces) == {"head", "top", "pants", "shoes"} and all(WEAR[p] == slot for slot, p in pieces.items()), (tier, pieces)
        assert all(p in RECIPES for p in pieces.values()), (tier, pieces)
        assert len({ARMOR[p] for p in pieces.values()}) == 1, (tier, {p: ARMOR[p] for p in pieces.values()})
        each.append(ARMOR[pieces["top"]])
    assert each == sorted(set(each)), each
    assert 4 * each[-1] >= ARMOR_CAP > 4 * each[-2]                       # (only a whole titanium set turns as much as armour can)


def test_an_old_saves_sword_is_the_iron_sword(tmp_path):
    sim = make(tmp_path)
    a = sim.login("Old", "tok")
    a.inventory.update({"sword": 1})
    sim.flush(); sim.close()
    sim = make(tmp_path)
    a = sim.by_name["Old"]
    assert a.inventory.get("iron_sword") == 1 and "sword" not in a.inventory, a.inventory
    sim.close()
