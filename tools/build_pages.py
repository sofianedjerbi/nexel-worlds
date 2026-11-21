"""Build the static demo for GitHub Pages: the browser client plus the game's Python, run in the page by Pyodide.

    uv run python tools/build_pages.py [out_dir]      (default: dist/)

The page has js/local.js in it, which boots the real server inside the tab. For a phone's line the client is sent as
few files (src/megastructure/web_bundle.py: one script, the pictures in one pack, the styles in the page), Python's own
library without what the game never opens (tools/build_stdlib.py), and a service worker keeps all of it for the next
visit (tools/pages/sw.js, marked with the commit and the build's content). tools/perf_load.py measures the result.
"""

import base64
import hashlib
import os
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "tools")]      # (this copy's own code, not an installed one)
import build_stdlib  # noqa: E402
from megastructure import web_bundle  # noqa: E402
PKG = ROOT / "src" / "megastructure"
WEB = PKG / "web"


def build(out: Path):
    if out.exists():
        shutil.rmtree(out)
    if not (WEB / "audio" / "sfx.json").exists():            # the sound effects are built, not committed
        import build_audio
        build_audio.build()
    shutil.copytree(WEB, out, ignore=shutil.ignore_patterns(".DS_Store"))
    page = (out / "index.html").read_text()
    # the world's own start is in the page, first of all, and so are the styles: nothing to wait for before the first
    # picture, and the game's Python comes with the page (js/local.js; it was a script among seventy, loaded in its turn)
    hook = '<canvas id="c"></canvas>'
    assert page.count(hook) == 1, "index.html no longer has its canvas first"
    page = page.replace(hook, "<script>\n" + (out / "js" / "local.js").read_text() + "</script>\n" + hook)
    (out / "js" / "local.js").unlink()
    line, mark = '<script src="js/splash.js"></script>\n', '<div id="help"></div>'      # (the line under the name: chosen as the page is read, not swapped a second later)
    assert page.count(line) == 1 and page.count(mark) == 1, "index.html no longer has its splash line or its help"
    page = page.replace(line, "").replace(mark, "<script>\n" + (out / "js" / "splash.js").read_text() + "</script>\n" + mark)
    names = web_bundle.SCRIPT.findall(page)
    page, files = web_bundle.packed(out, page)               # one script, one pack of pictures, the styles in the page
    for name, body in files.items():
        (out / name).write_bytes(body)
    for n in names:
        (out / "js" / n).unlink()
    # (the five small pictures the styles name, 0.2 to 0.4 KB each: in the page, not five more requests)
    page = re.sub(r"url\((assets/[\w.]+\.png)\)", lambda m: "url(data:image/png;base64," + base64.b64encode((out / m.group(1)).read_bytes()).decode() + ")", page)
    small = '"assets/title_poster_s.webp"'                  # (a phone's still picture of the island: in the page too, 45 KB: there with the first picture.
    assert page.count(small) == 1, "index.html no longer names its small poster"     #  Asked for, it came at 0.85 s behind seventy scripts and showed at 1.6 s)
    page = page.replace(small, '"data:image/webp;base64,' + base64.b64encode((out / "assets" / "title_poster_s.webp").read_bytes()).decode() + '"')
    font, ask = "url(assets/sprout-pixel.ttf)", '<link rel="preload" href="assets/sprout-pixel.ttf" as="font" type="font/ttf" crossorigin>\n'   # (and the game's letters, 17 KB: the first picture had its window and no word in it)
    assert page.count(font) == 1 and page.count(ask) == 1, "index.html no longer names its font"
    page = page.replace(font, "url(data:font/ttf;base64," + base64.b64encode((out / "assets" / "sprout-pixel.ttf").read_bytes()).decode() + ")").replace(ask, "")
    (out / "index.html").write_text(page.replace("</head>", '<link rel="preconnect" href="https://cdn.jsdelivr.net" crossorigin>\n</head>', 1))
    with zipfile.ZipFile(out / "py.zip", "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(PKG.rglob("*.py")):
            if "__pycache__" not in f.parts:
                z.write(f, Path("megastructure") / f.relative_to(PKG))
    for f in (ROOT / "tools" / "pages").iterdir():           # the showcase page (what's new) and its clips (tools/film_*.py)
        shutil.copy(f, out / f.name)
    # (a design shown online: the sky over a curved world, design/enemies/horizon_capture.py makes its pictures)
    shutil.copy(ROOT / "design" / "enemies" / "site" / "horizon.html", out / "horizon.html")
    shutil.copytree(ROOT / "design" / "enemies" / "site" / "horizon", out / "horizon")
    page = (out / "index.html").read_text()
    box = '<button class="item" id="titlehelp">'      # (the first screen's menu: one row more online, before Help)
    assert page.count(box) == 1, "the join box changed"
    (out / "index.html").write_text(page.replace(box, '<a class="item" href="showcase.html"><span>What\'s new</span></a>\n    ' + box))
    music_page(out)
    v = stamp(out)
    if os.environ.get("DEMO_PYODIDE"):                       # (a copy of Pyodide somewhere else than the CDN: tools/perf_load.py measures with one)
        w = out / "js" / "local_worker.js"
        text, n = re.subn(r'const PYODIDE = "[^"]+"', f'const PYODIDE = "{os.environ["DEMO_PYODIDE"]}"', w.read_text())
        assert n == 1, "local_worker.js no longer names Pyodide's address"
        w.write_text(text)
    offline(out, v)
    (out / ".nojekyll").write_text("")
    print(f"built {out} ({sum(f.stat().st_size for f in out.rglob('*') if f.is_file()) // 1024} KB)")


def offline(out: Path, v: str):
    """The smaller python_stdlib beside the page (if Pyodide's can be had), and the service worker told what to keep."""
    w = out / "js" / "local_worker.js"
    text = w.read_text()
    address = re.search(r'const PYODIDE = "([^"]+)"', text).group(1)
    python = [address + n for n in ("pyodide.mjs", "pyodide.asm.mjs", "pyodide.asm.wasm", "pyodide-lock.json")]
    full = None if os.environ.get("DEMO_STDLIB") == "full" else build_stdlib.full()        # ("full": Pyodide's own, to list what the game uses)
    if full:
        build_stdlib.trim(full, out / "std.zip")
        name = f"python_stdlib.{web_bundle.mark((out / 'std.zip').read_bytes())}.zip"
        (out / "std.zip").rename(out / name)
        old, size = "const STDLIB = null;", '"python_stdlib": [2.5e6, 25]'
        assert text.count(old) == 1 and text.count(size) == 1, "local_worker.js no longer names its python_stdlib"
        w.write_text(text.replace(old, f'const STDLIB = new URL("../{name}", self.location.href).href;').replace(size, f'"python_stdlib": [{(out / name).stat().st_size}, 13]'))
        python.append(name)
    else:
        python.append(address + "python_stdlib.zip")
    page = (out / "index.html").read_text()
    files = ["./"] + re.findall(r'<script src="(js/game\.[^"]+)"', page) + re.findall(r'"url":"(assets/pack\.[^"]+)"', page) + [f"js/local_worker.js?v={v}", f"py.zip?v={v}"]
    assert len(files) == 5, files
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip() or "nogit"
    sw = (out / "sw.js").read_text()
    for old, new in (('const BUILD = "dev";', f'const BUILD = "{commit}-{v}";'), ("const FILES = [];", f"const FILES = {files!r};"), ("const PYTHON = [];", f"const PYTHON = {python!r};")):
        assert sw.count(old) == 1, f"sw.js no longer has {old}"
        sw = sw.replace(old, new)
    (out / "sw.js").write_text(sw)
    hook = "<script>\n// The demo build"
    assert page.count(hook) == 1, "the page no longer begins with local.js"
    (out / "index.html").write_text(page.replace(hook, '<script>\nwindow.SW_FILE = "sw.js";\n// The demo build'))


def stamp(out: Path) -> str:
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
    for name, old in (("index.html", '"js/local_worker.js"'), ("index.html", '"assets/title_poster.webp"'), ("js/local_worker.js", '"../py.zip"')):
        text = (out / name).read_text()
        assert old in text, f"{name} no longer names {old}"
        (out / name).write_text(text.replace(old, old[:-1] + f'?v={v}"'))
    return v


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
