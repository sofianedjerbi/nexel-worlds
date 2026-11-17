"""The agent API's tool specs and the observation legend."""

from ..tiles import BLOCKS, GROUNDS
from .constants import SAY_R, SHOUT_R

LEGEND = {
    "@": "you", "P": "person", "c": "chicken (food)", "k": "cow (food)",
    "D": "tusker (a boar: charges in a straight line, step aside)", "I": "pincer (a shore crab: snaps if you stand next to it)",
    "S": "strawman (a scarecrow: walks toward you at night, fears firelight)",
    "i": "wisp (a light at night: harmless, it leads you on)", "E": "wyrm (a sea serpent in deep water: keep off its line)",
    "G": "Old Mossback (a giant tortoise, three tiles wide, asleep until hit: back off when it rises, step aside when its head pulls in)",
    "s": "sporeling (a small walking mushroom: one hit kills it)",
    "$": "items on ground",
    **{g.char: g.name for g in GROUNDS},
    **{b.char: b.name for b in BLOCKS if b.name != "none"},
}

DIR_ARG = {"dir": "N|E|S|W"}

TOOL_SPECS = {
    "step": {"args": {**DIR_ARG, "run": "bool (optional, sprint: 2x speed)"}, "desc": "move one tile"},
    "walk": {"args": {**DIR_ARG, "run": "bool (optional)"}, "desc": "keep walking in a direction until blocked or stopped"},
    "stop": {"args": {}, "desc": "stop the current action"},   # (a player's screen also says walk's `from`, stop's `at`: Movement.follow)
    "move_to": {"args": {"x": "int", "y": "int", "run": "bool (optional)", "z": "int (optional): a height there, a floor built over a room"}, "desc": "walk to absolute tile (pathfinding, <=64 tiles)"},
    "dig_down": {"args": {"with": "pickaxe"}, "desc": "dig down where you stand (by hand, or faster with a pickaxe in hand). The block "
                 "under your feet goes and you come down with it, on a hill or into a pit below sea level (down to "
                 "-512); over a hollow you fall in (a fall of more than 3 layers hurts: 5 hp a layer). You can jump "
                 "onto ground one layer higher; higher than that is a wall: dig toward it with a pickaxe to take out "
                 "the block in front of you (a tunnel). Caves are empty space under the hills (in_cave in your stats)"},
    "dig": {"args": {**DIR_ARG, "with": "tool in hand (optional: axe, pickaxe, hoe; default bare hands)", "z": "int (optional): the height of something built over the ground"},
            "desc": "dig the adjacent block (tree, rock, bush, wall...) or till the ground (needs a hoe); with z on bare ground, the ground there comes down a layer (a hole: faster with a pickaxe). By hand, "
                    "wood takes 4x and stone 6x as long as with an axe / pickaxe; ore needs a pickaxe. A built block in front of you (a step, "
                    "the floor you stand level with) comes back into your pack, what stands on it first"},
    "place": {"args": {**DIR_ARG, "item": "str", "text": "str (what a sign or a flag says, optional)", "z": "int (optional): a height, to build over the ground"},
              "desc": "place an item: furniture/walls/etc. as blocks; dirt fills holes or water, and on open ground raises it a layer; path lays cobble, plank makes a bridge (water) or floor (land); "
                      "roof lays a roof block over that tile, a storey up (3 layers: it rests on a wall or door under it, or holds to a block beside it; you can stand on it; under a roof you are sheltered). "
                      "stairs put beside a place 2 to 7 layers higher lay the whole flight down from it (a stairs a step); a ladder goes against something taller and is climbed by walking into it. "
                      "With z, plank or roof is a block in that cell (on the block under it: a step; or a storey over a wall; or beside a block), and a wall, door, bed... stands on the block built at that height"},
    "unroof": {"args": {**DIR_ARG}, "desc": "take the block built over that tile (a roof, a floor) back into your pack"},
    "pick_up": {"args": {"item": "str (optional)"}, "desc": "pick up items on your tile"},
    "drop": {"args": {"item": "str", "n": "int"}, "desc": "drop items on your tile"},
    "craft": {"args": {"recipe": "str", "n": "int (optional)"}, "desc": "craft from the recipe book"},
    "attack": {"args": {"target": "entity id", "with": "weapon (optional, e.g. sword, spear, axe; default fists)"},
               "desc": "hit an agent or creature within reach (3 tiles, 4 with a spear in hand; a circle round you, and height counts: a layer is half a tile, so not up a cliff or down one)"},
    "give": {"args": {"target": "agent id", "item": "str", "n": "int"}, "desc": "hand items to an agent within 2 tiles"},
    "eat": {"args": {"item": "str"}, "desc": "eat food (a moment: you can walk meanwhile, nothing else)"},
    "wear": {"args": {"item": "str"}, "desc": "put on a hat, top, pants, shoes or charm you carry (iron, gold, leather and mossback pieces are armor)"},
    "unwear": {"args": {"slot": "head|top|pants|shoes|effect"}, "desc": "take off what you wear there"},
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
    "name": {"args": {"target": "animal id", "text": "str"}, "desc": "name an animal within 2 tiles with a name tag you carry (used up; craft: 1 plank, 1 fiber): a named animal is yours, it never goes away (wild ones over the limit around a player do, out of sight)"},
    "sleep": {"args": DIR_ARG, "desc": "lie down in a bed nearby: you wake up there after dying"},
    "post": {"args": {**DIR_ARG, "text": "str"}, "desc": "post a letter in an adjacent mailbox"},
    "open_mail": {"args": DIR_ARG, "desc": "take the letters out of an adjacent mailbox (anyone can)"},
    "store": {"args": {**DIR_ARG, "item": "str", "n": "int"}, "desc": "put items into an adjacent chest or basket, or feed (hay, food) into a trough: animals nearby then feed themselves"},
    "take": {"args": {**DIR_ARG, "item": "str (omit: take everything)", "n": "int", "list": "bool (only look inside)"},
             "desc": "take items from a chest, basket or trough nearby"},
}
