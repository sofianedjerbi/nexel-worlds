"""New enemies for Megastructure, drawn by hand as ASCII pixel art in the Sprout Lands palette.

Each enemy: a few 16x16 frames (the boss is 32x32), idle then action. `build.py` turns them into a sheet and the showcase.
One character = one pixel; see PAL. Rows are padded to the frame width, so trailing spaces may be left out.
"""

PAL = {
    "o": "754c60", "k": "2b2236", "e": "f4f0e6", "c": "f3f2c0", "p": "e8b5ac", "P": "d99a9a",
    "b": "c49a6c", "B": "aa7959", "d": "90625d",
    "g": "97bb8e", "G": "6e967c", "m": "55785f",
    "s": "b6bab1", "S": "8a8f8c", "D": "5d6260",
    "v": "766daa", "V": "5c4e92", "n": "3f3566",
    "r": "e8613a", "y": "f6c45a", "Y": "fff1a8",
    "a": "818b83", "A": "ddd5de", "h": "545959",
    "x": "3c281e40",          # ground shadow (with alpha)
}

ENEMIES = {}


def enemy(key, name, size, where, when, role, behaviour, stats, frames, anim):
    ENEMIES[key] = dict(name=name, size=size, where=where, when=when, role=role, behaviour=behaviour, stats=stats,
                        frames=frames, anim=anim)


# ------------------------------------------------------------------ Bramble: a rolling ball of thorns
enemy("bramble", "Bramble", 16, "forest edges, hedges", "day and night", "roller",
      "Sits still like a bush. When you come close it curls up and rolls straight at you; it cannot turn, so step aside. "
      "It hurts to touch, even to hit bare-handed: use a tool.",
      dict(hp=6, damage=2, speed="fast in a line", drops="thorns, berries"),
      frames={
          "idle0": [
              "",
              "    o     o",
              " o  oo   oo  o",
              " oo oGGGGGo oo",
              "  ooGggGGGGGoo",
              " ooGggGGGGrGGoo",
              "  oGGkkGGkkGGo",
              " ooGGekGGekGGGo",
              "  oGGGGGGGGGGo",
              " oomGGGkkGGGmoo",
              "  omGrGGGGGGmo",
              " o ommGGGGmmo o",
              "   oommmmmmoo",
              "    oooooooo",
              "   xxxxxxxxxx",
          ],
          "idle1": [
              "",
              "",
              "    o     o",
              " o  oo   oo  o",
              " oo oGGGGGo oo",
              "  ooGggGGGrGGoo",
              " ooGGkkGGkkGGoo",
              "  oGGekGGekGGGo",
              " ooGGGGGGGGGGGo",
              "  omGGGkkGGGmo",
              " oomGrGGGGGGmoo",
              " o ommGGGGmmo o",
              "   oommmmmmoo",
              "    oooooooo",
              "   xxxxxxxxxx",
          ],
          "roll0": [
              "",
              "      o  o",
              "   o  oooo  o",
              "   oooGGGGooo",
              "  ooGggGGGGGoo",
              " ooGggGGGGGGGo",
              "  oGgGGGGrGGGoo",
              " ooGGGGGGGGGmo",
              "  oGGGGGGGGGmoo",
              " ooGrGGGGGGmmo",
              "  oGGGGGGGmmmoo",
              "  oomGGGmmmmoo",
              "   ooommmmooo",
              "   o  oooo  o",
              "   xxxxxxxxxx",
          ],
          "roll1": [
              "",
              "    o      o",
              "    oo oo oo",
              "  o ooGGGGoo o",
              "  ooGggGGGGGoo",
              "  oGggGGGGGGGo",
              " ooGgGGGGGGGGoo",
              "  oGGGGGrGGGmo",
              " ooGGGGGGGGGmoo",
              "  oGGGGGGGGmmo",
              "  ooGGrGGmmmoo",
              "  o oommmmoo o",
              "    oo oo oo",
              "    o      o",
              "   xxxxxxxxxx",
          ],
      }, anim=dict(idle=["idle0", "idle1"], act=["roll0", "roll1"], act_name="rolling"))

# ------------------------------------------------------------------ Mossback: a boulder that is not a boulder
enemy("mossback", "Mossback", 16, "hills, cliffs, cave mouths", "day and night", "ambusher",
      "Looks exactly like a mossy rock and never moves while watched from afar. Mine it or walk past and it wakes, "
      "stands on four stubby feet and shoves you back. Slow, very tough. Sleeps again if left alone.",
      dict(hp=18, damage=3, speed="slow", drops="stone, moss, sometimes ore"),
      frames={
          "hidden": [
              "", "", "",
              "     mggm",
              "   mgggggggm",
              "  ogGgggggGggo",
              "  oSsgggggssSo",
              " oSsssssssgssSo",
              " oSssssssssssSo",
              " oSSsssssssssSo",
              " oSSSsssssssSSo",
              "  oDSSSSSSSSDo",
              "   oooooooooo",
              "  xxxxxxxxxxxx",
          ],
          "wake": [
              "", "", "",
              "     mggm",
              "   mgggggggm",
              "  ogGgggggGggo",
              "  oSsgggggssSo",
              " oSskksssskksSo",
              " oSsyksssskysSo",
              " oSSsssssssssSo",
              " oSSSssDDssSSSo",
              "  oDSSSSSSSSDo",
              "   oooooooooo",
              "  xxxxxxxxxxxx",
          ],
          "walk0": [
              "",
              "",
              "     mggm",
              "   mgggggggm",
              "  ogGgggggGggo",
              "  oSsgggggssSo",
              " oSskksssskksSo",
              " oSsyksssskysSo",
              " oSSsssssssssSo",
              " oSSSssDDssSSSo",
              "  oDSSSSSSSSDo",
              "  oSSoooooooSSo",
              "  oSSo     oSSo",
              "  oooo     oooo",
              "  xxxxxxxxxxxx",
          ],
          "walk1": [
              "",
              "",
              "",
              "     mggm",
              "   mgggggggm",
              "  ogGgggggGggo",
              "  oSsgggggssSo",
              " oSskksssskksSo",
              " oSsyksssskysSo",
              " oSSsssssssssSo",
              " oSSSssDDssSSSo",
              "  oDSSSSSSSSDo",
              "   ooSSooSSooo",
              "    oooo oooo",
              "  xxxxxxxxxxxx",
          ],
      }, anim=dict(idle=["hidden", "hidden", "hidden", "wake"], act=["walk0", "walk1"], act_name="awake"))

# ------------------------------------------------------------------ Flit: a cave bat
enemy("flit", "Flit", 16, "caves, and above ground on dark nights", "night, underground", "swooper",
      "Hangs asleep from cave ceilings. Light or noise wakes the colony; they circle, then swoop one at a time and "
      "snatch food from your hands. Afraid of fire: a torch or a campfire keeps them off.",
      dict(hp=3, damage=1, speed="fast, flies over walls and water", drops="nothing; returns what it stole"),
      frames={
          "up": [
              "",
              " nn          nn",
              " nvn  n  n  nvn",
              " nvvn nnnn nvvn",
              " nvvvnVVVVnvvvn",
              "  nvvVeVVeVvvn",
              "   nnVkVVkVnn",
              "     nVppVn",
              "     nVeeVn",
              "      nnnn",
              "", "", "",
              "",
              "     xxxxxx",
          ],
          "mid": [
              "",
              "",
              "      n  n",
              "      nnnn",
              " nnnnnVVVVnnnnn",
              " nvvvVeVVeVvvvn",
              "  nvvVkVVkVvvn",
              "   nnnVppVnnn",
              "     nVeeVn",
              "      nnnn",
              "", "", "",
              "",
              "     xxxxxx",
          ],
          "down": [
              "",
              "",
              "      n  n",
              "      nnnn",
              "     nVVVVn",
              "   nnVeVVeVnn",
              "  nvvVkVVkVvvn",
              " nvvvnVppVnvvvn",
              " nvvn nVeeVn nvvn"[:16],
              " nvn   nnnn  nvn",
              " nn          nn",
              "", "",
              "",
              "     xxxxxx",
          ],
          "sleep": [
              "      nnnn",
              "     nVVVVn",
              "    nvVVVVvn",
              "    nvvVVvvn",
              "    nvvVVvvn",
              "    nvvVVvvn",
              "     nvVVvn",
              "     nVkkVn",
              "      nVVn",
              "      n  n",
          ],
      }, anim=dict(idle=["sleep"], act=["up", "mid", "down", "mid"], act_name="flying"))

# ------------------------------------------------------------------ Glub: a bog toad
enemy("glub", "Glub", 16, "shores, shallow water, wet fields", "dusk and rain", "lasher",
      "Sits half in the water and croaks. Anything that walks within three tiles gets a lash of its tongue, "
      "which also yanks small items out of your hands and into the water. It never chases.",
      dict(hp=8, damage=2, speed="does not move; 3-tile tongue", drops="slime, what it swallowed"),
      frames={
          "sit": [
              "", "", "", "",
              "   oo      oo",
              "  oeko    oeko",
              "  oGGooooooGGo",
              " oGGGGGGGGGGGGo",
              " oGgGGGGGGGGgGo",
              " oGooooooooooGo",
              " oGccccccccccGo",
              " ooGccccccccGoo",
              "oGGooGccccGooGGo",
              "ooo  oooooo  ooo",
              " xxxxxxxxxxxxxx",
          ],
          "croak": [
              "", "", "",
              "   oo      oo",
              "  oeko    oeko",
              "  oGGooooooGGo",
              " oGGGGGGGGGGGGo",
              " oGgGGGGGGGGgGo",
              " oGooooooooooGo",
              " oGcppppppppcGo",
              " oGppppppppppGo",
              " ooGppppppppGoo",
              "oGGooGccccGooGGo",
              "ooo  oooooo  ooo",
              " xxxxxxxxxxxxxx",
          ],
          "lash0": [
              "", "", "", "",
              "   oo      oo",
              "  okko    okko",
              "  oGGooooooGGo",
              " oGGGGGGGGGGGGo",
              " oGgGGGGGGGGgGo",
              " oGoooooookkkGo",
              " oGcccccccPPPPPP",
              " ooGccccccckkGoo"[:16],
              "oGGooGccccGooGGo",
              "ooo  oooooo  ooo",
              " xxxxxxxxxxxxxx",
          ],
          "lash1": [
              "", "", "", "",
              "   oo      oo",
              "  oeko    oeko",
              "  oGGooooooGGo",
              " oGGGGGGGGGGGGo",
              " oGgGGGGGGGGgGo",
              " oGoooooookkkGo",
              " oGcccccccPPkGo",
              " ooGccccccckGoo",
              "oGGooGccccGooGGo",
              "ooo  oooooo  ooo",
              " xxxxxxxxxxxxxx",
          ],
      }, anim=dict(idle=["sit", "sit", "croak", "croak"], act=["lash1", "lash0", "lash0", "lash1"], act_name="tongue lash"))

# ------------------------------------------------------------------ Pilfer: a thief
enemy("pilfer", "Pilfer", 16, "anywhere people build", "night", "thief",
      "Does not fight. Sneaks to unlocked chests, mailboxes and dropped items, takes one thing and runs for its den. "
      "Catch it before it gets home and it drops the lot. Fences and closed doors stop it; it fits through open gates.",
      dict(hp=4, damage=0, speed="very fast when carrying", drops="everything it stole"),
      frames={
          "idle0": [
              "",
              "   o      o",
              "  oao    oao",
              "  oaaooooaao",
              "  oaaaaaaaao",
              "  oahhaahhao",
              "  ohekAAekho",
              "   oAAkkAAo   oo",
              "    oAAAAo   oao",
              "   oaaaaaao  oho",
              "   oaAAAAao oao",
              "   oaAAAAaooho",
              "   oao  oaoo",
              "   oo    oo",
              "  xxxxxxxxxxx",
          ],
          "idle1": [
              "",
              "   o      o",
              "  oao    oao",
              "  oaaooooaao",
              "  oaaaaaaaao",
              "  oahhaahhao",
              "  ohkeAAkeho",
              "   oAAkkAAo  oo",
              "    oAAAAo  oao",
              "   oaaaaaao oho",
              "   oaAAAAaooao",
              "   oaAAAAaoho",
              "   oao  oaoo",
              "   oo    oo",
              "  xxxxxxxxxxx",
          ],
          "run0": [
              "",
              "",
              "     o      o",
              "    oao    oao",
              "    oaaooooaao",
              "    oaaaaaaaao",
              "    oahhaahhao",
              "    ohekAAekho",
              " oo  oAAkkAAo",
              "oaoo oobbbboo",
              "ohaooaobBBboao",
              " oahaaaobbbao",
              "  ooaaaaoooao",
              "   oao   oo",
              "  xxxxxxxxxxx",
          ],
          "run1": [
              "",
              "",
              "     o      o",
              "    oao    oao",
              "    oaaooooaao",
              "    oaaaaaaaao",
              "    oahhaahhao",
              "    ohekAAekho",
              "     oAAkkAAo",
              " ooo oobbbboo",
              "oahaoaobBBboao",
              " oohaaaobbbao",
              "   oaaaaoooao",
              "    oo  oao",
              "  xxxxxxxxxxx",
          ],
      }, anim=dict(idle=["idle0", "idle0", "idle1", "idle0"], act=["run0", "run1"], act_name="running off with loot"))

# ------------------------------------------------------------------ Emberling: what a fire left alone becomes
enemy("emberling", "Emberling", 16, "born from campfires and burning things", "any time a fire is left untended", "arsonist",
      "A fire nobody feeds for a night hops out of its ring. It wanders toward wood: fences, walls, crops, trees, "
      "and sets alight what it touches. Water puts it out at once; rain kills it. It never attacks people on purpose.",
      dict(hp=2, damage="burns what it touches", speed="hops, slow", drops="ash, a hot coal"),
      frames={
          "flick0": [
              "       y",
              "      yry",
              "      yrry  y",
              "   y yrrrry yy",
              "  yy yrYYrryry",
              "  yryrYYYYrrry",
              "  yrrYYYYYYrry",
              "  yrYYkYYkYYry",
              "  yrYYYYYYYYry",
              "   rrYYkkYYrr",
              "   rrrYYYYrrr",
              "    rrrrrrrr",
              "     dd  dd",
              "",
              "   xxxxxxxxxx",
          ],
          "flick1": [
              "        y",
              "    y  yry",
              "   yy  yrry",
              "   yry yrrry y",
              "  yrryrrYYryyy",
              "  yrrrrYYYYrry",
              "  yrrYYYYYYrry",
              "  yrYYkYYkYYry",
              "  yrYYYYYYYYry",
              "   rrYYkkYYrr",
              "   rrrYYYYrrr",
              "    rrrrrrrr",
              "     dd  dd",
              "",
              "   xxxxxxxxxx",
          ],
          "hop0": [
              "      y",
              "     yry   y",
              "    yrrry yy",
              "   yrrYYrryry",
              "  yrrYYYYrrry",
              "  yrYYYYYYYry",
              "  yrYkYYYkYry",
              "  yrYYYYYYYry",
              "   rrYkkkYrr",
              "    rrYYYrr",
              "     rrrrr",
              "    dd   dd",
              "",
              "",
              "    xxxxxxxx",
          ],
          "hop1": [
              "",
              "",
              "        y",
              "   y   yry  y",
              "  yry yrrry yy",
              "  yrryrYYYrryy",
              " yrrrYYYYYYrrry",
              " yrYYYkYYkYYYry",
              " yrYYYYYYYYYYry",
              "  rrYYYkkYYYrr",
              "  rrrrYYYYrrrr",
              "   rrrrrrrrrr",
              "    ddd  ddd",
              "",
              "  xxxxxxxxxxxx",
          ],
      }, anim=dict(idle=["flick0", "flick1"], act=["hop1", "hop0", "hop0", "hop1"], act_name="hopping"))


# ------------------------------------------------------------------ Cairn: the boss under the hills (32x32)
def overlay(rows, block, x, y, width=32):
    """Stamp a small block of rows onto a copy of rows at (x, y); spaces in the block are transparent."""
    out = [r.ljust(width) for r in rows] + [" " * width] * max(0, y + len(block) - len(rows))
    for dy, line in enumerate(block):
        row = list(out[y + dy])
        for dx, ch in enumerate(line):
            if ch != " ":
                row[x + dx] = ch
        out[y + dy] = "".join(row)
    return [r.rstrip() for r in out]


CAIRN_BODY = [
    "",
    "            mggggm",
    "          mgggggggggm",
    "         ogGggggggGggo",
    "         oSsgggggggsSo",
    "         oSskkssskksSo",
    "         oSsykssskysSo",
    "         oSsssssssssSo",
    "         oSSssDDDssSSo",
    "          oDSSSSSSSDo",
    "       oooooooooooooooooo",
    "      oSssgggssssssgggssSo",
    "      oSsssgssssssssgsssSo",
    "      oSssssssssssssssssSo",
    "      oSsssssssDDsssssssSo",
    "      oSssssssDsssssssssSo",
    "      oSsssssDDsssssssssSo",
    "      oSSssssssssssssssSSo",
    "      oSSSssssssssssssSSSo",
    "      oDSSSSssssssssSSSSDo",
    "       oDDSSSSSSSSSSSSDDo",
    "        oooooooooooooooo",
    "        oSSo      oSSo",
    "        oSSo      oSSo",
    "       oSSSSo    oSSSSo",
    "       oooooo    oooooo",
    "     xxxxxxxxxxxxxxxxxxxxxx",
]
FIST = [" oooo", "oSssSo", "oSssso", "oSSsso", "oSSSSo", " oooo"]
DUST = ["  c  c", " c cc ", "cccccc"]


def cairn(fist_y, dust=False, eyes="y"):
    rows = overlay(overlay(CAIRN_BODY, FIST, 0, fist_y), FIST, 26, fist_y)
    if eyes != "y":
        rows = [r.replace("sykssskys", f"s{eyes}ksssk{eyes}s") for r in rows]
    if dust:
        rows = overlay(overlay(rows, DUST, 0, 17), DUST, 26, 17)
    return rows


enemy("cairn", "Cairn", 32, "the deepest cave level", "always there, asleep until disturbed", "boss",
      "A heap of boulders in a wide chamber. Dig too close and it stands up. It walks slowly, raises both fists and slams: "
      "the shock breaks blocks around it and knocks you back, so walls do not save you. Its fists are stuck for a moment after "
      "each slam: that is when to strike the mossy head. Defeated, it falls back into a heap, and the ore it sat on is yours.",
      dict(hp=120, damage="6, and it breaks blocks", speed="slow; slam every few seconds", drops="ore, gems, a mossy heart"),
      frames={"idle": cairn(15), "raise": cairn(4, eyes="r"), "slam": cairn(20, dust=True, eyes="r")},
      anim=dict(idle=["idle"], act=["idle", "raise", "raise", "slam", "slam", "slam"], act_name="fist slam"))
