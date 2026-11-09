"""The agent API's tool specs and the observation legend."""

from ..tiles import BLOCKS, GROUNDS
from .constants import SAY_R, SHOUT_R

LEGEND = {
    "@": "you", "P": "person", "c": "chicken (food)", "k": "cow (food)", "G": "gloom (hostile, at night)",
    "$": "items on ground",
    **{g.char: g.name for g in GROUNDS},
    **{b.char: b.name for b in BLOCKS if b.name != "none"},
}

DIR_ARG = {"dir": "N|E|S|W"}

TOOL_SPECS = {
    "step": {"args": {**DIR_ARG, "run": "bool (optional, sprint: 2x speed)"}, "desc": "move one tile"},
    "walk": {"args": {**DIR_ARG, "run": "bool (optional)"}, "desc": "keep walking in a direction until blocked or stopped"},
    "stop": {"args": {}, "desc": "stop the current action"},
    "move_to": {"args": {"x": "int", "y": "int", "run": "bool (optional)"}, "desc": "walk to absolute tile (pathfinding, <=64 tiles)"},
    "dig_down": {"args": {"with": "pickaxe"}, "desc": "dig a cave mouth (pickaxe in hand): two tiles sloping down to the "
                 "south, from where you stand. Walk south down it to go one level underground; walk north up the ramp "
                 "below to come back. Caves are bigger and ore richer deeper down"},
    "dig": {"args": {**DIR_ARG, "with": "tool in hand (optional: axe, pickaxe, hoe; default bare hands)"},
            "desc": "dig the adjacent block (tree, rock, bush, wall...) or till the ground (needs a hoe). By hand, "
                    "wood takes 4x and stone 6x as long as with an axe / pickaxe; ore needs a pickaxe"},
    "place": {"args": {**DIR_ARG, "item": "str", "text": "str (flags only, optional)"},
              "desc": "place an item: furniture/walls/etc. as blocks; dirt fills holes or water, path lays cobble, plank makes a bridge (water) or floor (land)"},
    "pick_up": {"args": {"item": "str (optional)"}, "desc": "pick up items on your tile"},
    "drop": {"args": {"item": "str", "n": "int"}, "desc": "drop items on your tile"},
    "craft": {"args": {"recipe": "str", "n": "int (optional)"}, "desc": "craft from the recipe book"},
    "attack": {"args": {"target": "entity id", "with": "weapon (optional, e.g. sword, spear, axe; default fists)"},
               "desc": "hit an agent or creature within reach (3 tiles, 4 with a spear in hand)"},
    "give": {"args": {"target": "agent id", "item": "str", "n": "int"}, "desc": "hand items to an agent within 2 tiles"},
    "eat": {"args": {"item": "str"}, "desc": "eat food"},
    "say": {"args": {"text": "str"}, "desc": f"local chat, heard within {SAY_R} tiles"},
    "shout": {"args": {"text": "str"}, "desc": f"heard within {SHOUT_R} tiles (3 per minute)"},
    "write_sign": {"args": {**DIR_ARG, "text": "str"}, "desc": "write on an adjacent sign or flag"},
    "read_sign": {"args": DIR_ARG, "desc": "read an adjacent sign or flag"},
    "look_far": {"args": DIR_ARG, "desc": "coarse view of the next 48 tiles in a direction"},
    "ignite": {"args": {**DIR_ARG, "with": "torch (optional if a campfire is near)"},
               "desc": "set an adjacent flammable tile on fire (a torch in hand, used up, or a campfire within 2 tiles)"},
    "water": {"args": {**DIR_ARG, "with": "watering_can"},
              "desc": "water a growing crop with the can in hand: grows twice as fast; aim at a well or water to refill"},
    "milk": {"args": {"target": "cow id"}, "desc": "milk an adjacent cow (every 2 minutes)"},
    "feed": {"args": {"target": "animal id", "item": "food"}, "desc": "feed an adjacent animal; fed chickens lay eggs"},
    "sleep": {"args": DIR_ARG, "desc": "lie down in a bed nearby: you wake up there after dying"},
    "post": {"args": {**DIR_ARG, "text": "str"}, "desc": "post a letter in an adjacent mailbox"},
    "open_mail": {"args": DIR_ARG, "desc": "take the letters out of an adjacent mailbox (anyone can)"},
    "store": {"args": {**DIR_ARG, "item": "str", "n": "int"}, "desc": "put items into an adjacent chest or basket, or feed (hay, food) into a trough: animals nearby then feed themselves"},
    "take": {"args": {**DIR_ARG, "item": "str (omit: take everything)", "n": "int", "list": "bool (only look inside)"},
             "desc": "take items from a chest, basket or trough nearby"},
}
