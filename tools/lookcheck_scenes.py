"""The scenes of tools/lookcheck.py and the worker that shoots them: one server copy (free port, saves in a temp dir,
seed 12, --dev) and one Chrome, one screen (desk 1440x900 or phone 390x844 at DPR 3), the scenes of one group in
order. Each scene is staged with dev ops at its own place of the world (200 tiles apart: what one stamps is not in
another's picture, so --only gives the same px), the hour pinned (waits.py hour still), the land at rest; then the
page's clock is frozen at the scene's own instant, Math.random seeded, N frames drawn, and the shot taken.

    PYTHONPATH=src .venv/bin/python tools/lookcheck_scenes.py --group G --screen desk --out DIR [--only a,b]"""

import argparse
import os
import socket
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tests" / "e2e"))

SCREENS = {"desk": dict(viewport={"width": 1440, "height": 900}, device_scale_factor=1),
           "phone": dict(viewport={"width": 390, "height": 844}, device_scale_factor=3, has_touch=True, is_mobile=True)}
FRAMES = 8
STEP = 150          # ms of the frozen clock between two of the frames before a shot
WATCHDOG = 150

# the page's clocks under our hand: running (as the browser's, plus an offset), or frozen at an instant; Math.random from a seed
CLOCK = """(() => { if (window.__lc) return; const P = performance, pn = P.now.bind(P), d0 = Date.now(), raf = window.requestAnimationFrame.bind(window);
  const L = window.__lc = {off: 0, at: null}; P.now = () => (L.at !== null ? L.at : pn() + L.off); Date.now = () => Math.floor(d0 + P.now());
  L.freeze = (t) => { L.at = Math.max(t, P.now()); return L.at; }; L.thaw = () => { L.off = L.at - pn(); L.at = null; return 1; };
  let raw = -1, at = 0; window.requestAnimationFrame = (f) => raf((t) => { if (t !== raw) { raw = t; at = P.now(); } f(at); });
  let s = 12; Math.random = () => { s = (s + 0x6D2B79F5) | 0; let t = Math.imul(s ^ (s >>> 15), 1 | s); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
  L.seed = (v) => { s = v | 0; return 1; };
  // (a page's intervals skip while the clock is frozen: the first screen's island steps ten times a second by one)
  const si = window.setInterval; window.setInterval = (f, ms, ...a) => si((...b) => { if (L.at === null) f(...b); }, ms, ...a);
  // FRAMES frames, each at its own instant from t: STEP ms apart (what is redone at most every so often is redone)
  L.frames = (t, n, step) => new Promise((ok) => { L.at = Math.max(t, L.at === null ? P.now() : L.at); const f = () => { if (n-- <= 0) return ok(1); L.at += step; raf(f); }; raf(f); }); })()"""


def rect(x0, y0, x1, y1):
    return [[i, j] for j in range(y0, y1 + 1) for i in range(x0, x1 + 1)]


def col(g, tiles, c):
    g.rpc("dev_col", tiles=tiles, col=c)

def go(g, x, y, z=None):
    g.rpc("dev_teleport", **({"x": x, "y": y} if z is None else {"x": x, "y": y, "z": z}))
    try:
        g.arrive(12000)
        g.wait("!HdLook.busy", 8000)
    except Exception as e:  # noqa: BLE001 - shot as it is: the picture says what is wrong
        print("  (not arrived:", str(e)[:120], ")", flush=True)
    g.page.wait_for_timeout(700)                 # (the x-ray window's hold and the eye's tilt)
    g.rest()


def meadow(g, x, y, r=14):
    """(x, y) and the land round it flat meadow at 0, nobody on it."""
    go(g, x, y)
    g.rpc("dev_creatures", clear=60)
    col(g, rect(x - r, y - r, x + r, y + r), [0])
    g.stamp(-r, -r, ["." * (2 * r + 1)] * (2 * r + 1))


# ---- the scenes: (x, y) their place; each stages and leaves you where the eye is to be
def s_meadow(g, x, y):
    meadow(g, x, y)
    g.stamp(-6, -8, ["..T...f....b...T.", "......ff.........", "f..........T...f.", ".....b......f....", "...f.....f......."])
    go(g, x, y)


def s_village(g, x, y):
    meadow(g, x, y)
    g.stamp(-4, -9, ["WWWWWWW..oooo", "WnBnLhW..\"\"\"\"", "WnnrnnW..oooo", "WKnnnnW..wwww", "WWW+WWW......", "...__....Y...", "...__..X.....", "#####__######"])
    go(g, x, y)


def s_mountain(g, x, y):
    go(g, 26, -22)
    g.rpc("dev_creatures", clear=60)
    go(g, 26, -22)


def s_wall_earth(g, x, y):
    meadow(g, x, y)
    g.stamp(-3, -2, ["......."], levels=["2222222"])           # earth, two high, just north of you
    go(g, x, y)


def s_wall_stone(g, x, y):
    meadow(g, x, y)
    col(g, rect(x - 7, y - 6, x + 7, y + 4), [5])                # a terrace five high you stand on (stone: voxels.js cfg.rock from 5),
    col(g, rect(x - 4, y - 5, x + 4, y - 2), [7])                 # a mass two over it, its south wall just north of you
    go(g, x, y, 5)


def s_build(g, x, y):
    meadow(g, x, y)
    g.stamp(-3, -2, ["......."], levels=["2222222"])
    go(g, x, y)
    g.give(stone_block=6)
    g.hold_item("stone_block")
    g.face(0, -1)
    g.page.keyboard.press("z")
    try:
        g.wait("Build.on", 3000)
    except Exception:  # noqa: BLE001, S110 - the shot says it
        pass
    g.frames(3)


def s_stair(g, x, y):
    meadow(g, x, y)
    for i in range(1, 7):
        col(g, [[x + i, y]], [-i])
    go(g, x + 3, y, -3)


def s_pit(g, x, y):
    meadow(g, x, y)
    col(g, rect(x - 1, y - 1, x + 1, y + 1), [-4])
    go(g, x, y, -4)


def s_shaft3(g, x, y):
    meadow(g, x, y)
    col(g, [[x, y]], [-3])
    go(g, x, y, -3)


def s_shaft6(g, x, y):
    meadow(g, x, y)
    col(g, [[x, y]], [-6])
    go(g, x, y, -6)


def s_room(g, x, y):
    meadow(g, x, y)
    g.stamp(-2, -2, ["BnnLh", "nnrnn", "nnnnn", "KnnnC"], levels=["ddddd"] * 4)
    go(g, x, y, -4)


def s_cave(g, x, y):
    meadow(g, x, y)
    g.stamp(-10, -8, ["." * 20] * 9, levels=["5" * 20] * 9)
    cave = ["....................", "...------...........", "..---------.---.....", "..---------------....", "....----------------", ".....------..-----..", "......---.....--....",
            "....................", "...................."]
    g.stamp(-10, -8, cave, levels=["".join("0" if c == "-" else "5" for c in r) for r in cave],
            roofs=["".join("5" if c == "-" else "0" for c in r) for r in cave], heads=["".join("2" if c == "-" else "0" for c in r) for r in cave])
    g.stamp(-1, -2, ["-", "-"], levels=["0", "0"], roofs=["5", "0"], heads=["2", "0"])      # its mouth, south
    go(g, x - 2, y - 4, 0)


def s_gorge(g, x, y):
    meadow(g, x, y, 16)
    g.stamp(-15, -11, ["." * 31] * 10 + ["(" * 31] * 3 + ["." * 31] * 10, levels=["9" * 31] * 10 + ["2" * 31] * 3 + ["6" * 31] * 10)
    go(g, x, y)


def s_night(g, x, y):
    meadow(g, x, y)
    g.stamp(-1, -3, ["^"])
    g.give(torch=1)
    go(g, x, y)
    g.hold_item("torch")


def s_wayout(g, x, y):
    meadow(g, x, y)
    col(g, [[x, y]], [-6])
    g.give(pickaxe=1)
    go(g, x, y, -6)
    g.hold_item("pickaxe")
    try:
        g.wait("WayShow.cur && !WayShow.busy", 8000)
    except Exception:  # noqa: BLE001
        print("  (no way out shown)", flush=True)


# name: (group, stage, hour); "title" is the first screen, before anyone joins. A scene that puts something in your
# hands (build, night, wayout) is the last of its group: what you hold is in the next scene's picture. (The chat log
# is hidden for the shot: what it says depends on the scenes shot before.)
SCENES = {"title": (0, None, None), "meadow": (0, s_meadow, .3), "village": (0, s_village, .3), "mountain": (0, s_mountain, .3), "night": (0, s_night, .9),
          "wall_earth": (1, s_wall_earth, .3), "wall_stone": (1, s_wall_stone, .3), "stair": (1, s_stair, .3), "pit": (1, s_pit, .3), "build": (1, s_build, .3),
          "shaft3": (2, s_shaft3, .3), "shaft6": (2, s_shaft6, .3), "room": (2, s_room, .3), "cave": (2, s_cave, .3), "gorge": (2, s_gorge, .3), "wayout": (2, s_wayout, .3)}
GROUPS = sorted({v[0] for v in SCENES.values()})
PLACE = {n: (-1500 + 200 * i, 400) for i, n in enumerate(SCENES)}
FACE = {"build": (0, -1), "wall_earth": (0, -1), "wall_stone": (0, -1)}


def shoot(g, page, name, path):
    """The clock frozen at this scene's own instant, the dice seeded, FRAMES frames drawn, the shot."""
    i = list(SCENES).index(name)
    page.evaluate("(() => { for (const n of ['parts', 'puffs']) if (window[n] && window[n].length) window[n].length = 0; if (window.pops) pops.clear(); const t = document.getElementById('toast'); if (t) t.style.display = 'none'; const c = document.getElementById('chatlog'); if (c) c.style.visibility = 'hidden'; return 1; })()")
    page.evaluate(f"(() => {{ __lc.freeze({1e8 * (i + 1)}); __lc.seed({12 + i}); return 1; }})()")
    page.evaluate(f"__lc.frames({1e8 * (i + 1)}, {FRAMES}, {STEP})")
    page.screenshot(path=str(path), animations="disabled")       # (the style sheets' animations: ended, or at their start if they never end)
    page.evaluate("__lc.thaw()")


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def worker(group, screen, out, only):
    from game import Game
    from waits import MADE
    from playwright.sync_api import sync_playwright
    names = [n for n, v in SCENES.items() if v[0] == group and (not only or n in only)]
    if not names:
        return 0
    port, saves = free_port(), tempfile.mkdtemp(prefix="lookcheck_saves_")
    assert port != 7777
    proc = subprocess.Popen([str(ROOT / ".venv" / "bin" / "python") if (ROOT / ".venv").exists() else os.path.expanduser("~/megastructure/.venv/bin/python"),
                             "-m", "megastructure.server", "--saves", saves, "--world", "look", "--port", str(port), "--seed", "12", "--dev"],
                            env=dict(os.environ, PYTHONPATH=str(ROOT / "src")), cwd=str(ROOT), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def dog():
        proc.kill()
        print(f"WATCHDOG group {group} {screen}", flush=True)
        os._exit(3)
    tm = threading.Timer(WATCHDOG, dog)
    tm.daemon = True
    tm.start()
    url = f"http://127.0.0.1:{port}"
    for _ in range(200):
        try:
            socket.create_connection(("127.0.0.1", port), timeout=.2).close()
            break
        except OSError:
            time.sleep(.1)
    errors = []
    try:
        with sync_playwright() as p:
            b = p.chromium.launch(channel="chrome", headless=True)
            try:
                page = b.new_context(**SCREENS[screen]).new_page()
                page.add_init_script(CLOCK)
                page.on("pageerror", lambda e: errors.append(str(e)[:200]))
                g = Game(page, url)
                page.goto(url + "/?look=hd")
                page.wait_for_function("typeof ready !== 'undefined'", timeout=30000)
                if "title" in names:
                    page.wait_for_function("typeof TitleScene !== 'undefined' && TitleScene.on && !arrivingNow && HdLook.live", timeout=20000)
                    # (frozen from before its start: its people where they begin, whatever the machine's speed)
                    page.evaluate("(() => { TitleScene.stop(); document.getElementById('joinbox').style.display = ''; __lc.freeze(5e7); __lc.seed(3); TitleScene.start(3); return 1; })()")
                    page.wait_for_function("TitleScene.on && !arrivingNow", timeout=20000)
                    page.wait_for_function(MADE, timeout=20000)
                    page.evaluate(f"__lc.frames(5e7, 20, {STEP})")
                    page.screenshot(path=str(Path(out) / f"title_{screen}.png"), animations="disabled")
                    page.evaluate("__lc.thaw()")
                    print(f"  shot title {screen}", flush=True)
                if any(n != "title" for n in names):
                    page.click("#name")
                    page.keyboard.type("Ava")
                    page.keyboard.press("Enter")
                    g.name = "Ava"
                    g.wait("meObs && myPos()", 40000)
                    g.js("(() => { setOpt('names', false); for (const a of cv.getAnimations()) a.finish(); return 1; })()")
                    g.settle("!arrivingNow")
                for n in names:
                    if n == "title":
                        continue
                    t0 = time.time()
                    _, stage, hour = SCENES[n]
                    g.js("(() => { if (typeof Build !== 'undefined' && Build.on) Build.toggle(false); return 1; })()")      # (out of the last scene's build mode)
                    g.rpc("dev_time", phase=hour)
                    stage(g, *PLACE[n])
                    g.face(*FACE.get(n, (0, 1)))
                    g.hour(hour, still=True)
                    shoot(g, page, n, Path(out) / f"{n}_{screen}.png")
                    print(f"  shot {n} {screen} {time.time() - t0:.1f}s", flush=True)
            finally:
                b.close()
    finally:
        proc.terminate()
        try:
            proc.wait(5)
        except Exception:  # noqa: BLE001
            proc.kill()
        tm.cancel()
        __import__("shutil").rmtree(saves, ignore_errors=True)
    if errors:
        print(f"  page errors ({screen}, group {group}):", errors[:4], flush=True)
    return 0


if __name__ == "__main__":
    a = argparse.ArgumentParser()
    a.add_argument("--group", type=int, required=True)
    a.add_argument("--screen", choices=list(SCREENS), required=True)
    a.add_argument("--out", required=True)
    a.add_argument("--only", default="")
    o = a.parse_args()
    sys.exit(worker(o.group, o.screen, o.out, set(filter(None, o.only.split(",")))))
