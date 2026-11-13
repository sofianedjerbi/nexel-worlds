"""Build the static demo for GitHub Pages: the browser client plus the game's Python, run in the page by Pyodide.

    uv run python tools/build_pages.py [out_dir]      (default: dist/)

The page loads js/local.js, which boots the real server inside the tab; nothing else differs from the served client.
"""

import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PKG = ROOT / "src" / "megastructure"
WEB = PKG / "web"


def build(out: Path):
    if out.exists():
        shutil.rmtree(out)
    if not (WEB / "audio" / "sfx.json").exists():            # the sound effects are built, not committed
        sys.path.insert(0, str(ROOT / "tools"))
        import build_audio
        build_audio.build()
    shutil.copytree(WEB, out, ignore=shutil.ignore_patterns(".DS_Store"))
    page = (out / "index.html").read_text()
    hook = '<script src="js/state.js"></script>'
    assert hook in page, "index.html no longer loads js/state.js"
    (out / "index.html").write_text(page.replace(hook, '<script src="js/local.js"></script>\n' + hook))
    with zipfile.ZipFile(out / "py.zip", "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(PKG.rglob("*.py")):
            if "__pycache__" not in f.parts:
                z.write(f, Path("megastructure") / f.relative_to(PKG))
    for f in (ROOT / "tools" / "pages").iterdir():           # the showcase page (what's new) and its clip
        shutil.copy(f, out / f.name)
    page = (out / "index.html").read_text()
    box = '<div class="watch"><button class="ghost" id="watch">just watch</button></div>'
    assert box in page, "the join box changed"
    (out / "index.html").write_text(page.replace(box, box + '\n  <div class="watch"><a href="showcase.html" '
                                    'style="color:var(--ink2)">New: heights, biomes, dig anywhere</a></div>'))
    music_page(out)
    (out / ".nojekyll").write_text("")
    print(f"built {out} ({sum(f.stat().st_size for f in out.rglob('*') if f.is_file()) // 1024} KB)")


def music_page(out: Path):
    """music.html (tools/pages) plays the rendered tracks of music/site/audio, compressed to AAC (afconvert, macOS):
    the day theme, night, boss, the day suggestions (music/day.py), and the audit (music/quality.py)."""
    src = ROOT / "music" / "site" / "audio"
    wavs = [src / f"{n}.wav" for n in ("master", "night", "boss")] + sorted(src.glob("day_*.wav"))
    if not shutil.which("afconvert") or not (src / "days.json").exists() or not (src / "quality.json").exists() or not all(w.exists() for w in wavs):
        (out / "music.html").unlink()
        return print("no music page: render the music first (music/render_all.py, then music/quality.py)")
    (out / "music").mkdir()
    wavs += sorted(src.glob("dir_*.wav"))            # music/directions.py: short pieces on Surge XT
    if (src / "directions.json").exists():
        shutil.copy(src / "directions.json", out / "music" / "directions.json")
    for name in ("days.json", "quality.json"):
        shutil.copy(src / name, out / "music" / name)
    for w in wavs:
        subprocess.run(["afconvert", "-f", "m4af", "-d", "aac", "-b", "128000", str(w), str(out / "music" / (w.stem + ".m4a"))], check=True)


if __name__ == "__main__":
    build(Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "dist")
