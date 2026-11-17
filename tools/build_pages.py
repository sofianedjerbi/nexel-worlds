"""Build the static demo for GitHub Pages: the browser client plus the game's Python, run in the page by Pyodide.

    uv run python tools/build_pages.py [out_dir]      (default: dist/)

The page loads js/local.js, which boots the real server inside the tab; nothing else differs from the served client.
"""

import hashlib
import re
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
    for f in (ROOT / "tools" / "pages").iterdir():           # the showcase page (what's new) and its clips (tools/film_*.py)
        shutil.copy(f, out / f.name)
    page = (out / "index.html").read_text()
    box = '<button class="item" id="watch"><span>Just watch</span></button>'      # (the first screen's menu: one row more, online)
    assert box in page, "the join box changed"
    (out / "index.html").write_text(page.replace(box, box + '\n    <a class="item" href="showcase.html"><span>What\'s new</span></a>'))
    music_page(out)
    stamp(out)
    (out / ".nojekyll").write_text("")
    print(f"built {out} ({sum(f.stat().st_size for f in out.rglob('*') if f.is_file()) // 1024} KB)")


def stamp(out: Path):
    """Every script, style and clip a page names, the worker and the game's Python get the build's own mark (?v=...,
    from what the build holds): GitHub Pages lets a browser keep a file ten minutes, and a phone keeps a clip longer,
    so a page loaded again after a publish showed the build before. ("Now update the demo": it was.)"""
    mark = hashlib.sha1()
    for f in sorted(out.rglob("*")):
        if f.is_file() and f.suffix in (".js", ".css", ".zip", ".html", ".mp4", ".jpg", ".png", ".gif", ".json"):
            mark.update(f.relative_to(out).as_posix().encode() + f.read_bytes())
    v = mark.hexdigest()[:10]
    for page in ("index.html", "showcase.html", "music.html"):
        if (out / page).exists():
            text = (out / page).read_text()
            (out / page).write_text(re.sub(r'((?:src|href|poster)=")((?:js|css)/[^"?#]+|[^"/:?#]+\.(?:mp4|jpg|png|gif))"', rf'\1\2?v={v}"', text))
    for name, old in (("js/local.js", '"js/local_worker.js"'), ("js/local_worker.js", '"../py.zip"')):
        text = (out / name).read_text()
        assert old in text, f"{name} no longer names {old}"
        (out / name).write_text(text.replace(old, old[:-1] + f'?v={v}"'))


def music_page(out: Path):
    """music.html (tools/pages) plays the rendered tracks of music/site/audio, compressed to AAC (afconvert, macOS):
    the day theme, night, boss, the day suggestions (music/day.py), and the audit (music/quality.py)."""
    src = ROOT / "music" / "site" / "audio"
    wavs = [src / f"{n}.wav" for n in ("master", "night", "boss")] + sorted(src.glob("day_*.wav"))
    if not shutil.which("afconvert") or not (src / "days.json").exists() or not (src / "quality.json").exists() or not all(w.exists() for w in wavs):
        (out / "music.html").unlink()
        return print("no music page: render the music first (music/render_all.py, then music/quality.py)")
    (out / "music").mkdir()
    wavs += sorted(src.glob("dir_*.wav")) + sorted(src.glob("bright_*.wav")) + sorted(src.glob("piece_*.wav")) + sorted(src.glob("final_*.wav"))      # directions.py, bright.py, pieces.py, master.py
    for name in ("directions.json", "bright.json", "pieces.json", "final.json"):
        if (src / name).exists():
            shutil.copy(src / name, out / "music" / name)
    for name in ("days.json", "quality.json"):
        shutil.copy(src / name, out / "music" / name)
    for w in wavs:
        subprocess.run(["afconvert", "-f", "m4af", "-d", "aac", "-b", "128000", str(w), str(out / "music" / (w.stem + ".m4a"))], check=True)


if __name__ == "__main__":
    build(Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "dist")
