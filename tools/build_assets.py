"""Build the web client's art from the Sprout Lands packs (by Cup Nooble) plus generated extras.

    uv run --with pillow python tools/build_assets.py ~/Downloads

Only the sheets the game uses are copied into src/megastructure/web/assets/ (the license forbids
redistributing the pack itself). Extra tiles in the same palette are generated here.
"""

import io
import sys
import zipfile
from pathlib import Path

from PIL import Image

OUT = Path(__file__).resolve().parent.parent / "src" / "megastructure" / "web" / "assets"
SPRITES = "Sprout Lands - Sprites - premium pack.zip"
UI = "Sprout Lands - UI Pack - Premium pack.zip"

COPY = {  # zip-internal path suffix -> output name
    "Tilesets/ground tiles/Water.png": "water.png",
    "Tilesets/ground tiles/New tiles/Soil_Ground_Tiles.png": "soil.png",
    "Tilesets/ground tiles/New tiles/Grass_Tile_Layers.png": "grass.png",
    "Tilesets/ground tiles/Old tiles/Tilled_Dirt_v2.png": "tilled.png",
    "Tilesets/ground tiles/New tiles/Stone_Ground_Tiles.png": "stone.png",
    "Tilesets/ground tiles/New tiles/Bush_Tiles.png": "hedge.png",
    "Tilesets/Building parts/Stone_Path.png": "cobble.png",
    "Tilesets/Building parts/Paths.png": "planks.png",
    "Tilesets/Building parts/Fences.png": "fences.png",
    "Tilesets/Building parts/Fence gates animation sprites .png": "gates.png",
    "Tilesets/Building parts/Wooden_Bridge_v2.png": "bridge.png",
    "Tilesets/Building parts/Basic_Furniture.png": "furniture.png",
    "Tilesets/Building parts/Chest.png": "chest.png",
    "Tilesets/Building parts/door animation sprites.png": "door.png",
    "Objects/Trees, stumps and bushes.png": "trees.png",
    "Objects/Mushrooms, Flowers, Stones.png": "nature.png",
    "Objects/work station.png": "workbench.png",
    "Objects/signs.png": "signs.png",
    "Objects/Farming Plants.png": "crops.png",
    "Objects/Items/All items.png": "items.png",
    "Characters/Premium Charakter Spritesheet.png": "character.png",
    "Objects/Tree animations/tree_sprites.png": "tree_anim.png",
    "Objects/Tree animations/tree apple sprites.png": "tree_apple.png",
    "Objects/Tree animations/tree pear sprites.png": "tree_pear.png",
    "Objects/Tree animations/tree peach sprites.png": "tree_peach.png",
    "Objects/Tree animations/tree orange sprites.png": "tree_orange.png",
    "Objects/Water Objects.png": "water_objects.png",
    "emojis/Emoji spritesheet.png": "emoji.png",
    "Objects/Tree animations/tree_fall_animation_sprite_sheet.png": "tree_fall.png",
    "Animals/Chicken/chicken default.png": "chicken.png",
    "Animals/Cow/Brown cow animations.png": "cow.png",
    "UI Sprites/ALL UI ASSETS on one sheet.png": "ui.png",
}


def read_member(z: zipfile.ZipFile, suffix: str) -> bytes:
    for name in z.namelist():
        if name.endswith(suffix) and "__MACOSX" not in name:
            return z.read(name)
    raise KeyError(suffix)


def recolor(img: Image.Image, fn) -> Image.Image:
    img = img.convert("RGBA")
    px = img.load()
    for y in range(img.height):
        for x in range(img.width):
            r, g, b, a = px[x, y]
            if a:
                px[x, y] = (*fn(r, g, b), a)
    return img


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


def build(downloads: Path):
    OUT.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(downloads / SPRITES) as zs, zipfile.ZipFile(downloads / UI) as zu:
        for suffix, name in COPY.items():
            z = zu if suffix.startswith(("UI Sprites", "fonts", "emojis")) else zs
            (OUT / name).write_bytes(read_member(z, suffix))
        tilled = Image.open(io.BytesIO(read_member(zs, "Tilesets/ground tiles/Old tiles/Tilled_Dirt_v2.png")))
        water = Image.open(io.BytesIO(read_member(zs, "Tilesets/ground tiles/Water.png")))
        ui = Image.open(io.BytesIO(read_member(zu, "UI Sprites/ALL UI ASSETS on one sheet.png"))).convert("RGBA")
        paw = Image.open(io.BytesIO(read_member(zu, "UI Sprites/Mouse sprites/Catpaw Mouse icon.png"))).convert("RGBA")
        point = Image.open(io.BytesIO(read_member(zu, "UI Sprites/Mouse sprites/Catpaw pointing Mouse icon.png"))).convert("RGBA")

    # burnt ground: the tilled-soil layer, darkened and desaturated toward ash grey
    def ashen(r, g, b):
        lum = (r * 0.3 + g * 0.59 + b * 0.11)
        return (int(lum * 0.45 + r * 0.12), int(lum * 0.43 + g * 0.1), int(lum * 0.45 + b * 0.1))
    recolor(tilled, ashen).save(OUT / "ash.png")
    recolor(water, lambda r, g, b: (int(r * 0.62), int(g * 0.74), int(b * 0.86))).save(OUT / "water_deep.png")
    recolor(tilled.copy(), lambda r, g, b: (int(r * 0.72), int(g * 0.62), int(b * 0.55))).save(OUT / "tilled_wet.png")
    # UI pieces used as CSS 9-slices
    paw.resize((32, 32), Image.NEAREST).save(OUT / "cursor.png")
    point.resize((32, 32), Image.NEAREST).save(OUT / "cursor_point.png")
    ui.crop((11, 59, 37, 87)).save(OUT / "panel.png")
    ui.crop((345, 9, 375, 39)).save(OUT / "slot.png")
    ui.crop((345, 57, 375, 87)).save(OUT / "slot_sel.png")

    names = list(GEN)
    sheet = Image.new("RGBA", (16 * len(names), 16))
    for i, n in enumerate(names):
        sheet.alpha_composite(art(GEN[n], P), (16 * i, 0))
    sheet.save(OUT / "gen.png")
    (OUT / "gen.txt").write_text("\n".join(names) + "\n")

    (OUT / "CREDITS.md").write_text(
        "# Art credits\n\n"
        "Assets - From: **Sprout Lands** (Sprites pack and UI pack, premium) - By: **Cup Nooble**\n"
        "https://cupnooble.itch.io/\n\n"
        "License summary: modification allowed; use in commercial and non-commercial projects allowed;\n"
        "the asset pack itself may not be redistributed or resold, even modified; no NFTs or AI training;\n"
        "credit required. Only the sheets this game uses are included here.\n\n"
        "`gen.png`, `ash.png` and `water_deep.png` are extra tiles made for this game in the pack's style.\n")
    print("wrote", sorted(p.name for p in OUT.iterdir()))


if __name__ == "__main__":
    build(Path(sys.argv[1]).expanduser() if len(sys.argv) > 1 else Path.home() / "Downloads")
