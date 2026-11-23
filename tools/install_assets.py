"""Install the Sprout Lands art (not in this repository: its license forbids redistributing it).

Buy the two premium packs by Cup Nooble at https://cupnooble.itch.io/ (Sprout Lands - Sprites, and Sprout Lands -
UI Pack), then:

    python tools/install_assets.py "Sprout Lands - Sprites - premium pack.zip" "Sprout Lands - UI Pack - Premium pack.zip"
    python tools/install_assets.py ~/Downloads          # or a folder holding both zips

Copies the sheets the game uses into src/megastructure/web/assets/ (git-ignored there) and makes the tiles derived
from them (tools/build_assets.py). Needs Pillow (`pip install pillow`). Leaves the zips untouched; run it again after
updating the packs.
"""

import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "src"))

SPRITES_MARK = "Characters/Premium Charakter Spritesheet.png"       # a member only the premium Sprites pack has
UI_MARK = "UI Sprites/ALL UI ASSETS on one sheet.png"                # a member only the UI pack has


def has(zip_path: Path, suffix: str) -> bool:
    with zipfile.ZipFile(zip_path) as z:
        return any(n.endswith(suffix) and "__MACOSX" not in n for n in z.namelist())


def find_zips(args: list[str]) -> tuple[Path, Path]:
    zips = []
    for a in args:
        p = Path(a).expanduser()
        if p.is_dir():
            zips += sorted(p.glob("*.zip"))
        elif p.is_file():
            zips.append(p)
        else:
            sys.exit(f"no such file or folder: {p}")
    sprites = [z for z in zips if zipfile.is_zipfile(z) and has(z, SPRITES_MARK)]
    ui = [z for z in zips if zipfile.is_zipfile(z) and has(z, UI_MARK)]
    if not sprites or not ui:
        need = [n for n, f in (("Sprout Lands - Sprites (premium)", sprites), ("Sprout Lands - UI Pack (premium)", ui)) if not f]
        sys.exit("missing: " + ", ".join(need) + ". Both premium packs are needed: https://cupnooble.itch.io/")
    return sprites[0], ui[0]


def main(argv: list[str]) -> int:
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0 if argv else 2
    sprites, ui = find_zips(argv)
    from build_assets import build

    from megastructure import art
    print(f"sprites: {sprites}\nui:      {ui}")
    build(sprites, ui, art.ASSETS)
    gone = art.missing()
    if gone:
        print("not made:", ", ".join(gone), file=sys.stderr)
        return 1
    print(f"installed {len(art.FILES)} files into {art.ASSETS}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
