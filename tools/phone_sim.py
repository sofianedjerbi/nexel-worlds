"""A phone on this Mac: the game played by touch in a phone's Chrome, every frame measured (tools/PHONE.md says more).

    PYTHONPATH=src ~/megastructure/.venv/bin/python tools/phone_sim.py --preset mid [--gpu soft] [--line 4g]
        [--only stand,walk,sprint,stair,swim,title] [--secs 5] [--profile sprint] [--out p1_mid] [--saves DIR]
    PYTHONPATH=src ~/megastructure/.venv/bin/python tools/phone_sim.py --device android [--bench]

Its own server (a free port, a new world under --saves, seed 7, dev tools), one headless Chrome: 390x844 CSS px, 3
device px a px (1170x2532: a phone's GPU is bound by the px it fills), touch, the CPU slowed by a rate CALIBRATED on
this machine: BENCH (phone_sim_js.py) is timed here and the rate is the reference phone's ms over this machine's
(a busy Mac gets a lower rate, as DevTools' own "mid-tier / low-tier mobile" presets, Chrome 134 on, are made).
Chrome cannot slow a GPU: `--gpu soft` draws with SwiftShader, the CPU's GL: a pessimistic slow GPU.
Scenarios, each set up at full speed, then played slowed: stand, walk (stick pushed 40 px, east then west), sprint
(80 px), stair (down a dug stair into a room under the land), swim (across deep water), title (load -> first
screen -> Wake up -> the land drawn). A frame: its gap, the script's ms and the HD look's draws/faces/land ms
(HdView.perf), the GPU's ms (gpu_time.js), long tasks, heap. Prints a table, writes OUT.json and OUT.png (--dir).
`--device android`: a real Android Chrome over USB (adb), no throttling, its own screen; the same scenarios.
A watchdog ends the run after 150 s whatever happens.
"""

import argparse
import base64
import json
import os
import socket
import subprocess
import sys
import tempfile
import threading
import time
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "tools"), str(ROOT / "tests" / "e2e")]
from perf_serve import LINES  # noqa: E402
from phone_sim_js import BENCH, PLOT, RECORD, START, STOP, top  # noqa: E402

# The reference phones, in BENCH ms (median round). Set from this Mac (Apple M5, idle: BENCH 21.9 ms, 3 runs)
# times the ratio of Geekbench 6 single-core scores (JS on one big core follows it): M5 ~4200; mid: a 2021 mid
# Android, Galaxy A52 (Snapdragon 720G) ~560: x7.5; low: a 2021 budget one, Moto G Power (Snapdragon 662) ~330: x12.7.
# A real phone's number (`--device android --bench`) replaces these.
REF = {"mid": 164.0, "low": 278.0}
OUT = Path("/tmp/nexel-mockups")
SCENES = ["stand", "walk", "sprint", "stair", "swim", "title"]


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def server(saves, port):
    proc = subprocess.Popen([sys.executable, "-m", "megastructure.server", "--saves", saves, "--world", "sim", "--port", str(port), "--seed", "7", "--dev"],
                            cwd=ROOT, env={**os.environ, "PYTHONPATH": str(ROOT / "src")}, stdout=subprocess.DEVNULL, stderr=open(Path(saves) / "server.log", "w"))
    for _ in range(100):
        try:
            socket.create_connection(("127.0.0.1", port), timeout=.2).close()
            return proc
        except OSError:
            time.sleep(.1)
    raise SystemExit("the server did not start: " + str(Path(saves) / "server.log"))


class Phone:
    """A page with a recorder, touch by CDP, the CPU's rate set only while a scenario plays."""

    def __init__(self, ctx, url, rate, line):
        from game import Game
        ctx.add_init_script(RECORD)
        self.page = ctx.new_page()
        self.cdp = ctx.new_cdp_session(self.page)
        self.g, self.rate, self.url = Game(self.page, url), rate, url
        if line != "none":
            r, trip = LINES[line]
            self.cdp.send("Network.enable")
            self.cdp.send("Network.emulateNetworkConditions", {"offline": False, "latency": trip * 1000, "downloadThroughput": r, "uploadThroughput": r / 2})

    def slow(self, on):
        if self.rate:
            self.cdp.send("Emulation.setCPUThrottlingRate", {"rate": self.rate if on else 1})

    def touch(self, kind, x=0, y=0):
        self.cdp.send("Input.dispatchTouchEvent", {"type": kind, "touchPoints": [] if kind == "touchEnd" else [{"x": x, "y": y, "id": 0}]})

    def stick(self, dx, ms):
        """The left thumb down at (90, 600), pushed dx px (sideways) in 8 moves, held `ms`, let go."""
        self.touch("touchStart", 90, 600)
        for i in range(1, 9):
            self.touch("touchMove", 90 + dx * i / 8, 600)
            time.sleep(.016)
        time.sleep(ms / 1000)
        self.touch("touchEnd")
        return self.g.js("[myPos().x, myPos().y]")

    def record(self, play, profile=False):
        self.slow(True)
        time.sleep(.3)                                       # (settled into the slow pace)
        if profile:                                          # (started before the frames are counted: its start stalls a frame for a second)
            self.cdp.send("Profiler.enable")
            self.cdp.send("Profiler.setSamplingInterval", {"interval": 200})
            self.cdp.send("Profiler.start")
            time.sleep(.3)
        self.g.js(START)
        at = self.g.js("typeof myPos === 'function' && myPos() ? [myPos().x, myPos().y] : null")
        went = play()
        prof = self.cdp.send("Profiler.stop")["profile"] if profile else None
        r = self.g.js(STOP)
        self.slow(False)
        r["profile"], r["went"] = prof, [at, went]
        return r


def wake(g, name):
    """The first screen usable, your name typed, Wake up (Enter), until the land is drawn round you"""
    g.page.wait_for_function("typeof titleDraw === 'function' && spec && spec.readyState === 1 && !document.body.classList.contains('booting')", timeout=60000)
    g.page.click("#name")
    g.page.keyboard.type(name)
    g.page.keyboard.press("Enter")
    g.wait("meObs && myPos() && HdLook.on && HdLook.faces > 500", 60000)


def join(ph, name):
    g = ph.g
    wake(g.load(2, look="hd"), name)
    g.rpc("dev_time", phase=.3)
    g.js("setOpt('names', false); setOpt('hints', false)")


def scene(ph, name, secs, profile):
    g, ms = ph.g, secs * 1000
    if name == "title":                                      # (the load itself slowed; START runs on the new page as soon as it has the recorder)
        def play():
            g.page.wait_for_function("typeof titleDraw === 'function'", timeout=60000)
            time.sleep(min(3, secs / 2))                     # (the first screen's own scene, played)
            wake(g, f"sim{os.getpid() % 1000}t")
            time.sleep(1)
            return "in"
        ph.slow(True)
        t0 = time.time()
        g.page.goto(ph.url + "/?zoom=2&look=hd", wait_until="commit")
        g.page.wait_for_function("window.__sim", timeout=20000)
        r = ph.record(play, profile)
        r["wall_s"] = round(time.time() - t0, 1)
        return r
    g.clear_area(12)
    if name == "stand":
        return ph.record(lambda: time.sleep(secs), profile)
    if name in ("walk", "sprint"):
        d = 40 if name == "walk" else 80
        return ph.record(lambda: (ph.stick(d, ms / 2), ph.stick(-d, ms / 2)), profile)
    x, y = g.pos()
    if name == "stair":                                      # (east: six open steps down, eight under the land, a passage: test_e2e_hd_stair.py)
        g.stamp(-9, -9, ["." * 34] * 19)
        for i in range(1, 7):
            g.rpc("dev_col", tiles=[[x + i, y]], col=[-i])
        for i in range(7, 15):
            g.rpc("dev_col", tiles=[[x + i, y]], col=[-i, -i + 3, 0])
        g.rpc("dev_col", tiles=[[x + i, y] for i in range(15, 20)], col=[-14, -11, 0])
        g.rest()
        return ph.record(lambda: ph.stick(40, ms), profile)
    if name == "swim":
        g.rpc("dev_stamp", x=x + 1, y=y - 4, rows=["(" * 40] * 9)
        g.rest()
        return ph.record(lambda: ph.stick(40, ms), profile)
    raise SystemExit("no scenario " + name)


def q(v, p):
    return round(sorted(v)[min(len(v) - 1, int(len(v) * p))], 1) if v else None


def stats(r):
    gap, hd = [f[1] for f in r["f"]], r["hd"]
    js, gpu = [h[1] for h in hd], r["gpu"]
    return {"frames": len(gap), "fps": round(len(gap) / (sum(gap) / 1000), 1) if gap else 0,
           "gap": [q(gap, .5), q(gap, .95), q(gap, 1)], "over16": sum(g > 16.8 for g in gap), "over33": sum(g > 33.4 for g in gap),
           "script": [q(js, .5), q(js, .95), q(js, 1)], "gpu": [q(gpu, .5), q(gpu, .95), q(gpu, 1)] if gpu else "n/a",
           "long": [len(r["long"]), round(sum(d for _, d in r["long"])), round(max([d for _, d in r["long"]], default=0))],
           "draws": q([h[2] for h in hd], .5), "faces": q([h[3] for h in hd], .5), "land_ms_p95": q([h[4] for h in hd], .95),
           "heap_mb": [round(r["f"][0][2]), round(r["f"][-1][2])] if r["f"] else None, "went": r.get("went")}


def table(res):
    rows = [f"{'scenario':8} {'fps':>5} {'gap ms med/p95/max':>20} {'>16.7':>6} {'>33':>5} {'script med/p95/max':>20} {'GPU med/p95/max':>18} {'long n/ms/max':>14} {'draws':>6} {'faces':>7} {'heap MB':>8}"]
    for name, s in res.items():
        f = lambda v: "/".join("-" if x is None else f"{x:g}" for x in v) if isinstance(v, list) else v
        rows.append(f"{name:8} {s['fps']:>5} {f(s['gap']):>20} {s['over16']:>6} {s['over33']:>5} {f(s['script']):>20} {f(s['gpu']):>18} {f(s['long']):>14} {s['draws'] or '-':>6} {s['faces'] or '-':>7} {f(s['heap_mb'] or []):>8}")
    return "\n".join(rows)


def plot(ctx, runs, title, path):
    """The plot drawn on a canvas of a blank page of the same browser (phone_sim_js.py PLOT), its PNG written"""
    page = ctx.new_page()
    rows = [{"name": k, "note": f"{s['fps']} fps  gap p95 {s['gap'][1]}", "note2": f"script p95 {s['script'][1]}  GPU p95 {s['gpu'][1] if s['gpu'] != 'n/a' else 'n/a'}",
             "gap": [f[1] for f in r["f"]], "js": [h[1] for h in r["hd"]], "gpu": r["gpu"]} for k, (r, s) in runs.items()]
    path.write_bytes(base64.b64decode(page.evaluate(PLOT, {"title": title, "rows": rows}).split(",", 1)[1]))
    page.close()


def calibrate(ctx, a):
    """This machine's BENCH ms, and the rate that makes it the preset's phone: their ratio, corrected once by the
    bench run at that rate (Chrome's throttle is not linear: x7.4 gave 180 ms for 164). -> ms, rate, slowed ms, GPU"""
    bp = ctx.new_page()
    bp.goto("about:blank")
    mine = bp.evaluate(BENCH)
    gl = bp.evaluate("(() => { const gl = document.createElement('canvas').getContext('webgl2'), d = gl && gl.getExtension('WEBGL_debug_renderer_info'); return gl ? gl.getParameter(d ? d.UNMASKED_RENDERER_WEBGL : gl.RENDERER) : 'no WebGL 2'; })()")
    rate, slowed = 0, None
    if not a.device and a.preset != "none":
        rate, cdp = a.cpu or max(1.0, REF[a.preset] / mine), ctx.new_cdp_session(bp)
        for i in range(1 if a.cpu else 2):
            cdp.send("Emulation.setCPUThrottlingRate", {"rate": rate})
            slowed = bp.evaluate(BENCH)
            if i == 0 and not a.cpu:
                rate = max(1.0, rate * REF[a.preset] / slowed)
        rate, slowed = round(rate, 1), round(slowed, 1)
    bp.close()
    return mine, rate, slowed, gl


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--preset", default="mid", choices=["mid", "low", "none"])
    p.add_argument("--cpu", type=float, default=0, help="a rate of your own instead of the preset's")
    p.add_argument("--gpu", default="hw", choices=["hw", "soft"])
    p.add_argument("--line", default="none", choices=list(LINES))
    p.add_argument("--only", default=",".join(SCENES))
    p.add_argument("--secs", type=float, default=5)
    p.add_argument("--profile", default="", help="scenarios (a,b) to take a CPU profile of: their top functions")
    p.add_argument("--device", default="", choices=["", "android"])
    p.add_argument("--bench", action="store_true", help="only the benchmark: this machine's (or the phone's) score")
    p.add_argument("--saves", default="")
    p.add_argument("--out", default="")
    p.add_argument("--dir", default=str(OUT))
    a = p.parse_args()
    threading.Timer(150, lambda: (print("watchdog: 150 s", flush=True), os._exit(3))).start()
    from playwright.sync_api import sync_playwright
    port = free_port()
    saves = a.saves or tempfile.mkdtemp(prefix="phone_sim")
    Path(saves).mkdir(parents=True, exist_ok=True)
    proc, pw, browser = None if a.bench else server(saves, port), sync_playwright().start(), None
    try:
        if a.device == "android":                            # (adb: Chrome's DevTools socket here, and the phone's localhost:port to this server)
            subprocess.run(["adb", "forward", "tcp:9222", "localabstract:chrome_devtools_remote"], check=True)
            subprocess.run(["adb", "reverse", f"tcp:{port}", f"tcp:{port}"], check=True)
            browser = pw.chromium.connect_over_cdp("http://127.0.0.1:9222")
            ctx = browser.contexts[0]
        else:
            args = ["--use-angle=swiftshader", "--enable-unsafe-swiftshader"] if a.gpu == "soft" else []
            browser = pw.chromium.launch(channel="chrome", headless=True, args=args)
            ctx = browser.new_context(viewport={"width": 390, "height": 844}, has_touch=True, is_mobile=True, device_scale_factor=3)
        mine, rate, slowed, gl = calibrate(ctx, a)
        head = {"chrome": browser.version, "preset": a.preset, "bench_ms": round(mine, 1), "rate": rate, "bench_slowed_ms": slowed, "target_ms": REF.get(a.preset),
                "gpu": a.gpu, "renderer": gl, "line": a.line, "device": a.device or "sim"}
        print(json.dumps(head), flush=True)
        if a.bench:
            return
        ph = Phone(ctx, f"http://127.0.0.1:{port}", rate, a.line)
        join(ph, f"sim{os.getpid() % 1000}")
        runs = {}
        for name in a.only.split(","):
            t0 = time.time()
            r = scene(ph, name, a.secs, name in a.profile.split(","))
            runs[name] = (r, stats(r))
            print(name, json.dumps(runs[name][1]), f"({time.time() - t0:.0f} s)", flush=True)
            if r.get("profile"):
                head["top_" + name] = top(r["profile"])
                for kind in ("self", "total"):
                    print(f"  {kind} (of {head['top_' + name]['busy_ms']} ms busy; {head['top_' + name]['meta_ms']})", *(f"   {pc:5.1f} %  {ms:7.1f} ms  {k}" for k, ms, pc in head["top_" + name][kind]), sep="\n", flush=True)
        res = {k: s for k, (r, s) in runs.items()}
        print(table(res), flush=True)
        out = Path(a.dir) / (a.out or f"p1_{a.preset}_{a.gpu}")
        out.parent.mkdir(parents=True, exist_ok=True)
        out.with_suffix(".json").write_text(json.dumps({"head": head, "stats": res, "frames": {k: {"gap": [round(f[1], 2) for f in r["f"]], "script": [round(h[1], 2) for h in r["hd"]], "gpu": [round(v, 2) for v in r["gpu"]]} for k, (r, s) in runs.items()}}))
        plot(ctx, runs, f"{a.preset} (CPU x{rate}, bench {mine:.0f} ms), GPU {a.gpu}: {gl[:60]}", out.with_suffix(".png"))
        print("wrote", out.with_suffix(".json"), out.with_suffix(".png"), flush=True)
    except Exception:  # noqa: BLE001 - said, then everything shut (os._exit would swallow it)
        traceback.print_exc()
    finally:
        if browser and not a.device:
            browser.close()
        pw.stop()
        if proc:
            proc.terminate()
            proc.wait(10)
        os._exit(0)


if __name__ == "__main__":
    main()
