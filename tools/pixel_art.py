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
}.items()}

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
        "                ", "                ", "                ", "      dddd      ", "    ddsSsddd    ", "   dsSnNssSsd   ",
        "   dsnNNnsSsd   ", "  dssnnssnNsd   ", "  dSsssSnNnsd   ", "  dssSssnnssd   ", "   ddsssssdd    ", "     dddddd     ",
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
    "pickaxe": [
        "                ", "    hhhh        ", "   hHHHHhh      ", "  hH    oHh     ", "  h    oW  h    ", "       oW   h   ",
        "      oW        ", "     oW         ", "    oW          ", "   oW           ", "  oW            ", "  o             ",
        "                ", "                ", "                ", "                "],
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
    "mouth_top": [  # a cave mouth's top: the ground breaks off into earth steps going down into the dark (south)
        "                ", "                ", "  cccccccccccc  ", " cBBBBBBBBBBBBc ", " cBbbbbbbbbbbBc ", " cBccccccccccBc ",
        " cBoooooooooo Bc", " cBcBBBBBBBBcBc ", " cBoccccccccoBc ", " cBokkooookkoBc ", " cBokcccccckoBc ", " cBokkkkkkkkoBc ",
        " cBokkookkookoBc", " cBokkkkkkkkoBc ", " cBokkkkkkkkoBc ", " cBokkkkkkkkoBc "],
    "mouth_deep": [  # its deep end: the last steps, swallowed by the dark
        " cBokkkkkkkkoBc ", " cBokkkkkkkkoBc ", " cBokkkkkkkkoBc ", " cBkkkkkkkkkkBc ", " cBkkkkkkkkkkBc ", " cBkkkkkkkkkkBc ",
        " cBkkkkkkkkkkBc ", " cBkkkkkkkkkkBc ", " cBkkkkkkkkkkBc ", " ccBkkkkkkkkBcc ", "  ccBBkkkkBBcc  ", "   ccccccccc    ",
        "                ", "                ", "                ", "                "],
    "ramp_top": [  # below: the ramp's top, daylight falling down it from the mouth
        "  NNNNNNNNNNNN  ", " cNYYYYYYYYYYNc ", " cNYYYYYYYYYYNc ", " cBNNNNNNNNNNBc ", " cBbbbbbbbbbbBc ", " cBccccccccccBc ",
        " cBBBBBBBBBBBBc ", " cBbbbbbbbbbbBc ", " cBccccccccccBc ", " cBBBBBBBBBBBBc ", " cBbbbbbbbbbbBc ", " cBccccccccccBc ",
        " cBBBBBBBBBBBBc ", " cBbbbbbbbbbbBc ", " cBccccccccccBc ", " cBBBBBBBBBBBBc "],
    "ramp_low": [  # its foot, earth steps meeting the cave floor
        " cBbbbbbbbbbbBc ", " cBccccccccccBc ", " cBBBBBBBBBBBBc ", " cBbbbbbbbbbbBc ", " cBccccccccccBc ", " cBBBBBBBBBBBBc ",
        " cBbbbbbbbbbbBc ", " cBccccccccccBc ", "  cBBBBBBBBBBc  ", "   cccccccccc   ", "                ", "                ",
        "                ", "                ", "                ", "                "],
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
}
