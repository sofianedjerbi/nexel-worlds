"""Pixel art drawn for this game in the pack's style: a palette and small ASCII-art sprites (generated into gen.png)."""

from PIL import Image


def art(rows: list[str], pal: dict) -> Image.Image:
    img = Image.new("RGBA", (16, 16))
    px = img.load()
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if ch != " " and ch in pal and x < 16 and y < 16:
                px[x, y] = pal[ch]
    return img

def hexc(h: str, a: int = 255):
    h = h.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), a)

# Generated sprites, drawn in the pack's palette (outline #5b3f3f-ish browns, soft greens, warm lights)
P = {k: hexc(v) for k, v in {
    "o": "6b4a3a", "w": "a8775a", "W": "c99a6e", "s": "8a8f8c", "S": "b6bab1", "d": "5d6260",
    "r": "e8613a", "y": "f6c45a", "Y": "fff1a8", "f": "cf4b3e", "p": "b8463a",
    "g": "4a3a5e", "G": "6a5687", "e": "f4f0e6", "k": "2b2236",
    "n": "d9a441", "N": "f5d77a", "m": "b25b4c", "M": "e08a6f", "c": "8c5a3c", "b": "e8c48c", "B": "c79a5c",
    "t": "9db86a", "T": "6f8f4a", "h": "7a7d81", "H": "c9ced1",
    "u": "90625d", "U": "c49a6c", "l": "cfeaf2", "L": "8cc4d8",   # house wood (the wall sheet's outline and plank) and glass
    # the pack's own item icons (its axe, its hoe): the white sticker edge, the head's four greys, the handle's three browns
    "1": "f3f4e7", "2": "818b83", "3": "c1c8b9", "4": "6b7470", "5": "9da89a", "6": "90625d", "7": "b68962", "8": "754c60",
}.items()}
P["x"] = (0, 0, 0, 70)  # soft shadow

GEN = {
    "campfire0": [
        "                ", "                ", "       y        ", "      yry       ", "     yrYry      ", "     rrYYr      ",
        "    ryYYYyr     ", "    rrYYYrr     ", "   swwrrrrwws   ", "  sSowwwwwwoSs  ", "  ssooWWWWoossx ", "   sSSssssSSsx  ",
        "    xxxxxxxxx   ", "                ", "                ", "                "],
    "campfire1": [
        "                ", "                ", "        y       ", "       yry      ", "      yrYr      ", "     yrYYry     ",
        "     ryYYYr     ", "    rrYYYYrr    ", "   swwrrrrwws   ", "  sSowwwwwwoSs  ", "  ssooWWWWoossx ", "   sSSssssSSsx  ",
        "    xxxxxxxxx   ", "                ", "                ", "                "],
    "flag": [
        "      oW        ", "      oWffff    ", "      oWfffpff  ", "      oWffffpff ", "      oWfffppf  ", "      oWffpf    ",
        "      oWf       ", "      oW        ", "      oW        ", "      oW        ", "      oW        ", "      oW        ",
        "     xowx       ", "     xxxx       ", "                ", "                "],
    "gloom0": [
        "                ", "                ", "                ", "      kkkk      ", "    kkGGGGkk    ", "   kGGGGGGGGk   ",
        "  kGGeegGeeGGk  ", "  kGGekgGekGGk  ", "  kGGGGGGGGGGk  ", " kgGGGGGGGGGGgk ", " kggGGGGGGGGggk ", " kgggggggggggggk",
        "  kk kgggk kkk  ", "   xxxxxxxxxxx  ", "                ", "                "],
    "gloom1": [
        "                ", "                ", "                ", "                ", "     kkkkkk     ", "   kkGGGGGGkk   ",
        "  kGGeegGeeGGk  ", "  kGGekgGekGGk  ", " kgGGGGGGGGGGgk ", " kggGGGGGGGGggk ", "kgggggggggggggk ", "kgggggggggggggggk",
        " kkk kgggggk kk ", "  xxxxxxxxxxxxx ", "                ", "                "],
    "fire0": [
        "                ", "                ", "                ", "       y        ", "   y  yry   y   ", "  yry yrYy yry  ",
        "  rYry rYr yYr  ", " yrYYr rYYryYYr ", " rYYYrrYYYrYYYr ", " rrYYYrYYYrYYrr ", "  rrrrrrrrrrrr  ", "   pppppppppp   ",
        "                ", "                ", "                ", "                "],
    "fire1": [
        "                ", "                ", "        y       ", "   y   yry  y   ", "  yry yrYr yry  ", "  rYr yrYy rYr  ",
        " yrYyr rYYr yYr ", " rYYYr rYYrrYYr ", " rYYYYrYYYrYYYr ", " rrYYYrYYrrYYrr ", "  rrrrrrrrrrrr  ", "   pppppppppp   ",
        "                ", "                ", "                ", "                "],
    "fiber": [
        "                ", "                ", "        T       ", "      T tT      ", "     tT tT T    ", "    T tTtT tT   ",
        "    tTtTtTtT    ", "     tTtTtT     ", "      oWWo      ", "      tTtT      ", "     tT  tT     ", "    tT    tT    ",
        "                ", "                ", "                ", "                "],
    "ore": [
        "                ", "                ", "                ", "      dddd      ", "    ddsSsddd    ", "   dsSaAssSsd   ",
        "   dsaAAasSsd   ", "  dssaassaAsd   ", "  dSsssSaAasd   ", "  dssSssaassd   ", "   ddsssssdd    ", "     dddddd     ",
        "                ", "                ", "                ", "                "],
    "meat": [
        "                ", "                ", "                ", "       mmm      ", "     mmMMMm     ", "    mMMMMMMm    ",
        "    mMMeMMMm    ", "    mMMMMMMm    ", "     mmMMMm     ", "      mmmeee    ", "          eeH   ", "           He   ",
        "                ", "                ", "                ", "                "],
    "cooked_meat": [
        "                ", "                ", "                ", "       ccc      ", "     ccBBBc     ", "    cBBbBBBc    ",
        "    cBBBBbBc    ", "    cBbBBBBc    ", "     ccBBBc     ", "      ccceee    ", "          eeH   ", "           He   ",
        "                ", "                ", "                ", "                "],
    "bread": [
        "                ", "                ", "                ", "                ", "     cccccc     ", "   ccBBbBBBcc   ",
        "  cBbBBBbBBBBc  ", "  cBBBBBBBbBBc  ", "  cBBbBBBBBBBc  ", "   ccBBBBBBcc   ", "     cccccc     ", "                ",
        "                ", "                ", "                ", "                "],
    "torch": [
        "                ", "       y        ", "      yry       ", "      rYr       ", "      rYr       ", "      oWo       ",
        "      oWo       ", "       W        ", "       W        ", "       W        ", "       W        ", "       o        ",
        "                ", "                ", "                ", "                "],
    "rope": [
        "                ", "                ", "      bbbb      ", "    bB    Bb    ", "   bB  bb  Bb   ", "   b  bBBb  b   ",
        "   b  b  b  b   ", "   bB  bb  Bb   ", "    bB    Bb    ", "      bbbb  B   ", "             B  ", "                ",
        "                ", "                ", "                ", "                "],
    "sword": [
        "                ", "             HH ", "            HSH ", "           HSH  ", "          HSH   ", "         HSH    ",
        "        HSH     ", "   n   HSH      ", "    n HSH       ", "     nSH        ", "     onn        ", "    oW  n       ",
        "   oW           ", "  oo            ", "                ", "                "],
    "spear": [
        "                ", "            HH  ", "           HSSH ", "           SSH  ", "          oSH   ", "         oW     ",
        "        oW      ", "       oW       ", "      oW        ", "     oW         ", "    oW          ", "   oW           ",
        "  oW            ", "                ", "                ", "                "],
    "pickaxe": [   # in the manner of the pack's axe and hoe: their handle, a head that curves to two points, the sticker edge
        "                ", "                ", "    111111      ", "   15533331     ", "    11455331    ", "      1145531   ",
        "        145531  ", "       16745331 ", "      167814531 ", "     16781 1531 ", "    16781  1431 ", "   16781    151 ",
        "  16781      1  ", "  1881          ", "   11           ", "                "],
    "axe": [
        "                ", "         hh     ", "        hHHh    ", "       ohHHHh   ", "       oWhHHh   ", "      oW  hh    ",
        "      oW         ", "     oW         ", "    oW          ", "   oW           ", "  oW            ", "  o             ",
        "                ", "                ", "                ", "                "],
    "ingot": [
        "                ", "                ", "                ", "                ", "      hhhhhh    ", "    hHHHHHHHh   ",
        "   hHHSSHHHhh   ", "  hhhhhhhhhhd   ", "  hHHHHHHHHd    ", "  hhhhhhhhd     ", "                ", "                ",
        "                ", "                ", "                ", "                "],
    "boulder": [
        "                ", "                ", "                ", "      dddd      ", "    ddSSSsdd    ", "   dSSHSSsssd   ",
        "  dsSHHSSssssd  ", "  dsSSSSsssssd  ", "  dssSSssssssd  ", "  dsssssssshsd  ", "  ddssssssssdd  ", "   dddsssssdd   ",
        "    xddddddxx   ", "     xxxxxx     ", "                ", "                "],
    "stone_wall": [
        "dddddddddddddddd", "dSSSSSdSSSSSSSdd", "dSHHSSdSSHSSSSsd", "dSSSSsdSSSSSsssd", "ddddddddddddddd ", "dSSsdSSSSSSdSSsd",
        "dSSsdSSHSSsdSSsd", "dsssdsssssdssssd", "dddddddddddddddd", "dhhhhdhhhhhhdhhd", "dhhhhdhhhhhhdhhd", "ddddddddddddddd ",
        "dhhhhhhdhhhhhhhd", "dhhhhhhdhhhhhhhd", "dddddddddddddddd", "xxxxxxxxxxxxxxxx"],
    "workbench": [
        "                ", "                ", "     H  hh      ", "    HhH hh  s   ", "  oooooooooooo  ", " oWWWWWWWWWWWWo ",
        " oWWbWWWWWWbWWo ", " oWWWWWWWWWWWWo ", " oooooooooooooo ", " owwwwwwwwwwwwo ", " o oo      oo o ", " o oo      oo o ",
        " o oo      oo o ", " ooo        ooo ", "  xxxxxxxxxxxx  ", "                "],
    "window": [  # for house fronts: wooden frame and sill, four glass panes
        "                ", "                ", "   uuuuuuuuuu   ", "   uUUUUUUUUu   ", "   uUllulLlUu   ", "   uUlLulllUu   ",
        "   uUuuuuuuUu   ", "   uUllullLUu   ", "   uULlulllUu   ", "   uUUUUUUUUu   ", "  uuuuuuuuuuuu  ", "  uUUUUUUUUUUu  ",
        "   uuuuuuuuuu   ", "                ", "                ", "                "],
    "heart": [
        "                ", "                ", "                ", "   ffff  ffff   ", "  fMMMMffMMMMf  ", "  fMeMMMMMMMMf  ",
        "  fMMMMMMMMMMf  ", "  fMMMMMMMMMMf  ", "   fMMMMMMMMf   ", "    fMMMMMMf    ", "     fMMMMf     ", "      fMMf      ",
        "       ff       ", "                ", "                ", "                "],
    "food": [
        "                ", "                ", "        T       ", "       Tt       ", "    ffffTfff    ", "   fMMMMMMMMf   ",
        "  fMeMMMMMMMMf  ", "  fMMMMMMMMMMf  ", "  fMMMMMMMMMMf  ", "  fMMMMMMMMMMf  ", "   fMMMMMMMMf   ", "    fMMffMMf    ",
        "     ff  ff     ", "                ", "                ", "                "],
    "bolt": [
        "                ", "                ", "        ooooo   ", "       oyyyyo   ", "      oyyyyo    ", "     oyyyyo     ",
        "    oyyyyyooo   ", "   oyyyyyyyyo   ", "   oooyyyyyo    ", "     oyyyyo     ", "    oyyyyo      ", "   oyyyo        ",
        "   oyyo         ", "   ooo          ", "                ", "                "],
    "stone_item": [
        "                ", "                ", "                ", "                ", "      dddd      ", "    ddsSSsd     ",
        "   dsSSSsssd    ", "   dsSsssssd    ", "   dssssssdd    ", "    ddssddd     ", "      ddd       ", "                ",
        "                ", "                ", "                ", "                "],
    "ladder": [
        "                ", "    oW    oW    ", "    oW    oW    ", "    oWwwwwoW    ", "    oWooooow    ", "    oW    oW    ",
        "    oWwwwwoW    ", "    oWooooow    ", "    oW    oW    ", "    oWwwwwoW    ", "    oWooooow    ", "    oW    oW    ",
        "    oWwwwwoW    ", "    oWooooow    ", "    oo    oo    ", "                "],     # two rails and their rungs, in the wood of the pack's houses
    "stairs": [
        "                ", "                ", "          oooooo", "          oWWWWo", "          owwwwo", "      oooooWwwwo",
        "      oWWWWwwwwo", "      owwwwwwwwo", "  oooooWwwwwwwwo", "  oWWWWwwwwwwwwo", "  owwwwwwwwwwwwo", "  owwwwwwwwwwwwo",
        "  oooooooooooooo", "                ", "                ", "                "],     # three steps, seen from the side
    "name_tag": [   # a paper tag on a string, a hole at its point, two lines written on it
        "                ", "                ", "  B             ", "   B            ", "    B           ", "    oooooooooo  ",
        "   oeeeeeeeeeeo ", "  oeeoeeeeeeeeo ", " oeeo oecccceeo ", "  oeeoeeeeeeeeo ", "   oeeeeccceeeo ", "    oooooooooo  ",
        "                ", "                ", "                ", "                "],
}

# The land's ores (ores.py), as items and as the hill's boulder ("ore": iron): the boulder's rock, its specks (a: dark,
# A: light) in each ore's colours. Ingots: the ingot's bar (h, H, S, d) in each metal's. The tiered tools: the pack's
# pickaxe (its head's greys 2 to 5), the axe and the sword (h, H, S: the head, the blade) in each tier's.
ORE_SPECKS = {"ore": ("b07a5a", "e0b896"), "iron_ore": ("b07a5a", "e0b896"), "coal": ("2a2a30", "55555f"),
              "copper_ore": ("c4683a", "6fbf98"), "gold_ore": ("d9a441", "fff1a8"), "titanium_ore": ("7f9fc6", "e2f0ff")}
METALS = {"copper_ingot": ("a8552e", "d9844f", "f2b27e", "7a3b20"), "gold_ingot": ("bd9230", "f2cf5c", "fff3b8", "8a6424"),
          "titanium_ingot": ("8aa3bf", "c9dcef", "f2f8ff", "5d7690")}
HEADS = {"wood": ("7a5236", "a0714a", "8a6040", "b88a5c"), "copper": ("93502c", "f2b27e", "d9844f", "e09a66"), "iron": ("8f9a9e", "dfe5e6", "b9c3c6", "cdd5d7"),
         "titanium": ("6f8db3", "e6f2ff", "a9c6e6", "c9def4")}
for _n, (_a, _b) in ORE_SPECKS.items():
    GEN.setdefault(_n, GEN["ore"])
PAL = {n: {"a": hexc(a), "A": hexc(b)} for n, (a, b) in ORE_SPECKS.items()}
for _n, (h, H, S, d) in METALS.items():
    GEN[_n] = GEN["ingot"]
    PAL[_n] = {"h": hexc(h), "H": hexc(H), "S": hexc(S), "d": hexc(d)}
for _t, (c4, c3, c2, c5) in HEADS.items():
    GEN[f"{_t}_pickaxe"] = GEN["pickaxe"]
    PAL[f"{_t}_pickaxe"] = {"4": hexc(c4), "3": hexc(c3), "2": hexc(c2), "5": hexc(c5)}
    GEN[f"{_t}_axe"] = GEN["axe"]
    PAL[f"{_t}_axe"] = {"h": hexc(c4), "H": hexc(c3)}
# a sword of each tier (ores.py SWORDS): the iron one is the first sword's own colours; its blade's edge (H) and face (S)
GEN["iron_sword"] = GEN.pop("sword")
for _t, (_h, _s) in {"wood": ("7a5236", "b88a5c"), "stone": ("5d6260", "a3a8a0"), "copper": ("93502c", "f2b27e"),
                     "titanium": HEADS["titanium"][:2]}.items():
    GEN[f"{_t}_sword"] = GEN["iron_sword"]
    PAL[f"{_t}_sword"] = {"H": hexc(_h), "S": hexc(_s)}
# a hide: a pelt stretched out flat, four legs and a tail, a lighter belly (cows and tuskers leave one: leather)
GEN["hide"] = [
    "                ", "                ", "   cc      cc   ", "   cBccccccBc   ", "    cBBBBBBBc   ", "   cBBbbbbBBBc  ",
    "  cBBbbBbbbBBc  ", "  cBbbbbbbBbBc  ", "  cBBbbbbbbBBc  ", "   cBBbBbbbBc   ", "   cBBBBBBBBc   ", "  cBc cccc cBc  ",
    "  cc        cc  ", "                ", "                ", "                "]
GEN["gold_coin"] = [
    "                ", "                ", "                ", "      nnnn      ", "    nnNNNNnn    ", "   nNNYYNNNNn   ",
    "   nNYNnnNNNn   ", "  nNNNnNNnNNNn  ", "  nNNNnnnNNNNn  ", "  nNNNNnNNnNNn  ", "   nNNnnnNNNn   ", "   nnNNNNNNnn   ",
    "    nnnnnnnn    ", "     xxxxxx     ", "                ", "                "]
GEN["wire"] = [
    "                ", "                ", "                ", "      aaaa      ", "    aaAAAAaa    ", "   aA aaaa Aa   ",
    "   a aAAAAa a   ", "   a a aa a a   ", "   a aA  Aa a   ", "   aA aaaa Aa   ", "    aaAAAAaa  A ", "      aaaa   A  ",
    "                ", "                ", "                ", "                "]
PAL["wire"] = {"a": hexc("a8552e"), "A": hexc("f2b27e")}

# Nyxwing's drop: the core at the end of its tail, an eclipse (a dark moon over a gold sun), as an item of the usual size
GEN["eclipse_core"] = [
        "                ", "             Y  ", "     nnnnnn     ", "    nNNNGGGn    ", "   nNNGkkkkGn   ", "  nNYGkkkkkkGn  ",
        "  nNNGkkkkkkGn  ", "  nNNGkkkkkkGn  ", "  nNNNGkkkkGGn  ", "  nNNNNGkkGGNn  ", "  nNNNNNGGGNNn  ", "   nNNNNNNNNn   ",
        "    nNNNNNNn    ", "     nnnnnn     ", "            Y   ", "                "]


def gen_sheet():
    """The generated sprites in one strip, 16 px each, and their names in its order (web/assets gen.png, gen.txt)."""
    names = list(GEN)
    sheet = Image.new("RGBA", (16 * len(names), 16))
    for i, n in enumerate(names):
        sheet.alpha_composite(art(GEN[n], {**P, **PAL.get(n, {})}), (16 * i, 0))
    return sheet, names


if __name__ == "__main__":       # only the strip (the rest of the art needs the pack's zips: build_assets.py)
    from pathlib import Path
    out = Path(__file__).resolve().parent.parent / "src" / "nexel_worlds" / "web" / "assets"
    sheet, names = gen_sheet()
    sheet.save(out / "gen.png")
    (out / "gen.txt").write_text("\n".join(names) + "\n")
    print("wrote gen.png:", len(names), "sprites")

