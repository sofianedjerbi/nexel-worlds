"""Clothes and armor (sim/wear.py): wearing, taking off, what armor turns, what death drops, what is saved."""

import re
from pathlib import Path

from helpers import run
from test_wild import put

from megastructure.sim import CREATURES
from megastructure.tiles import ARMOR, RECIPES, WEAR


def test_wearing_takes_it_from_the_bag_and_swaps_what_was_there(world):
    sim, a = world
    a.add("straw_hat"); a.add("iron_helmet")
    assert run(sim, a, "wear", {"item": "straw_hat"})["ok"]
    assert a.worn == {"head": "straw_hat"} and not a.count("straw_hat")
    r = run(sim, a, "wear", {"item": "iron_helmet"})
    assert r["took_off"] == "straw_hat" and a.worn == {"head": "iron_helmet"} and a.count("straw_hat") == 1
    assert run(sim, a, "unwear", {"slot": "head"})["took_off"] == "iron_helmet"
    assert a.worn == {} and a.count("iron_helmet") == 1
    assert not run(sim, a, "wear", {"item": "wood"})["ok"] and not run(sim, a, "unwear", {"slot": "head"})["ok"]


def test_armor_turns_part_of_a_blow_and_clothes_none(world):
    sim, a = world
    boar = put(sim, "tusker", a.x + 9, a.y, cooldown=10 ** 6)
    a.worn = {"top": "linen_shirt", "head": "straw_hat"}
    assert sim.armor(a) == 0 and sim.guarded(a, 20) == 20
    a.worn = {"head": "iron_helmet", "top": "iron_chestplate", "pants": "iron_greaves", "shoes": "iron_boots"}
    assert sim.armor(a) == 40
    hp = a.hp
    sim.bite(boar, a)
    assert hp - a.hp == round(CREATURES["tusker"]["damage"] * 0.6)
    a.worn = {"head": "mossback_helm", "top": "mossback_plate", "pants": "moss_kilt", "shoes": "moss_slippers"}
    assert sim.armor(a) == 45                                     # capped


def test_death_drops_what_you_wore_and_the_save_keeps_what_you_wear(world):
    sim, a = world
    a.worn = {"head": "gold_crown", "effect": "flame_charm"}
    assert a.to_json()["worn"] == {"head": "gold_crown", "effect": "flame_charm"}
    assert sim.observe(a)["self"]["wearing"]["head"] == "gold_crown"
    x, y = a.x, a.y
    sim.damage(a, 999, "test")
    assert a.worn == {} and sim.items[(x, y)]["gold_crown"] == 1 and sim.items[(x, y)]["flame_charm"] == 1


def test_every_piece_has_a_recipe_and_the_client_draws_exactly_the_same_pieces():
    assert set(WEAR) <= set(RECIPES) and set(ARMOR) <= set(WEAR) and len(WEAR) == 43
    js = (Path(__file__).parent.parent / "src/megastructure/web/js/wear.js").read_text()
    table = re.search(r"const WEAR = \{(.*?)\n\};", js, re.S).group(1)
    client = dict(re.findall(r'(\w+): \["(\w+)", ', table))
    assert client == WEAR
    assert ("shell_plate", 1, 5, 5) in CREATURES["mossback"]["drops"]      # enough for the whole mossback set, every time
