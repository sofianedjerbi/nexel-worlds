"""Clothes and armor: every piece, the slot it goes in, the blow armor turns, and what each is made of."""

# Clothes and armor (sim/wear.py): the slot each piece goes in, and the percent of a blow each armor piece turns.
# How they look is the client's (web/js/wear.js); a test keeps the two lists the same.
WEAR = {
    "straw_hat": "head", "sporecap_hat": "head", "wizard_hat": "head", "leather_cap": "head", "copper_helmet": "head", "iron_helmet": "head", "gold_crown": "head", "titanium_helmet": "head", "mossback_helm": "head", "wool_beanie": "head", "flower_crown": "head", "bandana": "head", "sprout": "head",
    "linen_shirt": "top", "red_scarf": "top", "wool_sweater": "top", "overalls": "top", "leather_vest": "top", "wizard_robe": "top", "copper_chestplate": "top", "iron_chestplate": "top", "gold_chestplate": "top", "titanium_chestplate": "top", "mossback_plate": "top",
    "linen_shorts": "pants", "denim": "pants", "red_trousers": "pants", "leather_chaps": "pants", "robe_skirt": "pants", "copper_greaves": "pants", "iron_greaves": "pants", "gold_greaves": "pants", "titanium_greaves": "pants", "moss_kilt": "pants",
    "leather_boots": "shoes", "red_sneakers": "shoes", "rain_boots": "shoes", "blue_slippers": "shoes", "copper_boots": "shoes", "iron_boots": "shoes", "gold_boots": "shoes", "titanium_boots": "shoes", "moss_slippers": "shoes",
    "sparkle_charm": "effect", "firefly_charm": "effect", "leaf_charm": "effect", "heart_charm": "effect", "flame_charm": "effect", "frost_charm": "effect", "halo_charm": "effect", "spore_charm": "effect", "flower_charm": "effect",
}
# Armour's ladder (#393), the tools' one with leather for wood and stone: the percent of a blow each piece turns. A
# whole set of four turns four times as much, up to sim/wear.py ARMOR_CAP (titanium's reaches it). Old Mossback's shell
# is a set of its own. Each set's recipe: 3 for the head, 5 the top, 4 the legs, 2 the feet, of its material.
TIERS = {"leather": (5, "hide"), "copper": (7, "copper_ingot"), "gold": (8, "gold_ingot"), "iron": (10, "iron_ingot"),
         "titanium": (12, "titanium_ingot")}
SETS = {t: {"head": "gold_crown" if t == "gold" else f"{t}_cap" if t == "leather" else f"{t}_helmet",
            "top": f"{t}_vest" if t == "leather" else f"{t}_chestplate",
            "pants": f"{t}_chaps" if t == "leather" else f"{t}_greaves", "shoes": f"{t}_boots"} for t in TIERS}
ARMOR = {**{piece: TIERS[t][0] for t, pieces in SETS.items() for piece in pieces.values()},
         **{k: 12 for k in WEAR if k.startswith("moss")}}
WEAR_RECIPES = {
    "straw_hat": {"wheat": 4},
    "sporecap_hat": {"mushroom": 4},
    "wizard_hat": {"fiber": 3, "flower": 1},
    "mossback_helm": {"shell_plate": 1, "fiber": 1},
    "wool_beanie": {"fiber": 3},
    "flower_crown": {"flower": 4},
    "bandana": {"fiber": 2},
    "sprout": {"seed": 2},
    "linen_shirt": {"fiber": 4},
    "red_scarf": {"fiber": 2, "berries": 1},
    "wool_sweater": {"fiber": 6},
    "overalls": {"fiber": 5},
    "wizard_robe": {"fiber": 5, "flower": 2},
    "mossback_plate": {"shell_plate": 2},
    "linen_shorts": {"fiber": 3},
    "denim": {"fiber": 4, "berries": 1},
    "red_trousers": {"fiber": 4, "berries": 2},
    "robe_skirt": {"fiber": 4, "flower": 1},
    "moss_kilt": {"shell_plate": 1, "fiber": 2},
    "red_sneakers": {"fiber": 2, "berries": 1},
    "rain_boots": {"fiber": 2, "wheat": 1},
    "blue_slippers": {"fiber": 2, "flower": 1},
    "moss_slippers": {"shell_plate": 1},
    "sparkle_charm": {"rope": 1, "iron_ingot": 1},
    "firefly_charm": {"rope": 1, "torch": 1},
    "leaf_charm": {"rope": 1, "seed": 3},
    "heart_charm": {"rope": 1, "egg": 2},
    "flame_charm": {"rope": 1, "torch": 2, "coal": 1},
    "frost_charm": {"rope": 1, "stone": 3, "milk": 1},
    "halo_charm": {"rope": 1, "iron_ingot": 2, "flower": 2},
    "spore_charm": {"rope": 1, "mushroom": 3},
    "flower_charm": {"rope": 1, "flower": 3},
}
WEAR_RECIPES.update({piece: {TIERS[t][1]: {"head": 3, "top": 5, "pants": 4, "shoes": 2}[slot]}
                     for t, pieces in SETS.items() for slot, piece in pieces.items()})
