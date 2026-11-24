"""How long a phone waits: the first screen, Wake up usable, in the world. One browser, one visit (or two: cold, warm).

    PYTHONPATH=src python tools/perf_load.py demo  --line fast3g [--warm] [--cpu 4] [--dist dist] [--pyodide DIR]
    PYTHONPATH=src python tools/perf_load.py local --line fast3g [--warm] [--bundle]
    PYTHONPATH=src python tools/perf_load.py demo  --line none --walk 10 --cpu 6        (frames while sprinting, in the world)

`demo`: the built site (tools/build_pages.py) behind tools/perf_serve.py, which is the line (the page's worker too).
`local`: the game's own server on a temporary world; the line is Chrome's own (its page's requests only).
A phone: 390x844, 3 device px a px, touch, the CPU slowed `--cpu` times. Times are ms from the visit's start, read on the
page (a 50 ms watch). Prints one JSON line. Port 7819; a watchdog ends the run after 150 s whatever happens.
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PORT = 7819
sys.path.insert(0, str(ROOT / "tools"))
from perf_serve import LINES, serve  # noqa: E402

WATCH = """
window.__perf = {long: [], m: {}, frames: null};
try { new PerformanceObserver((l) => { for (const e of l.getEntries()) __perf.long.push([Math.round(e.startTime), Math.round(e.duration)]); }).observe({entryTypes: ["longtask"]}); } catch (e) {}
(() => { const m = __perf.m, at = (k, ok) => { try { if (!(k in m) && ok()) m[k] = Math.round(performance.now()); } catch (e) {} };
  const see = () => {
    at("wait", () => !!document.getElementById("boot"));            // (the wait on the screen: index.html #boot)
    at("js_bytes", () => ASSET_PACK.jsGot >= ASSET_PACK.jsLen);      // (the demo's script read, web_bundle.py)
    at("title_bytes", () => ASSET_PACK.got >= ASSET_PACK.need);       // (the pictures the first screen waits for)
    at("scripts", () => typeof titleDraw === "function");
    at("decoded", () => window.ASSETS_OF && ASSETS_IN >= ASSETS_OF);
    at("island", () => blocks.size > 0);
    at("ready", () => document.body.classList.contains("scene"));      // (the first screen whole: the island painted, the wait gone)
    at("usable", () => typeof titleDraw === "function" && spec && spec.readyState === 1 && !document.body.classList.contains("booting"));
    at("in", () => meObs !== null);
    at("world", () => meObs !== null && !!myPos() && HdLook.on && HdLook.faces > 500 && HdLook.catSeen() > .8);
  };
  setInterval(see, 50); })();
// the wait's bar, every frame it is on the screen: [ms, % said] (index.html #boot)
__perf.bar = []; (() => { const f = (t) => { const s = document.getElementById("bootsay"); if (!s && __perf.bar.length) return;
  if (s) __perf.bar.push([Math.round(t), parseInt(s.textContent.replace(/\\D+/g, "")) || 0]); requestAnimationFrame(f); }; requestAnimationFrame(f); })();
"""
# the bar, read: the biggest step up from one frame to the next, the longest it said the same while the page waited, steps back
BAR = """(() => { const b = __perf.bar; let jump = 0, still = 0, back = 0, from = 0;
  for (let i = 1; i < b.length; i++) { jump = Math.max(jump, b[i][1] - b[i - 1][1]); back += b[i][1] < b[i - 1][1];
    if (b[i][1] !== b[from][1]) from = i; else if (b[i][1] < 100) still = Math.max(still, b[i][0] - b[from][0]); }
  return {frames: b.length, jump, still_ms: still, back, said: b.filter((x, i) => !i || x[1] !== b[i - 1][1]).map((x) => x[1] + "@" + x[0]).join(" ")}; })()"""
FRAMES = """(ms) => new Promise((ok) => { const gaps = [], t0 = performance.now(); let last = t0;
  const f = (t) => { gaps.push(t - last); last = t; if (t - t0 < ms) requestAnimationFrame(f); else { gaps.sort((a, b) => a - b);
    const q = (p) => +gaps[Math.min(gaps.length - 1, Math.floor(gaps.length * p))].toFixed(1);
    ok({frames: gaps.length, p50: q(.5), p90: q(.9), p99: q(.99), max: q(1), over50: gaps.filter((g) => g > 50).length, over100: gaps.filter((g) => g > 100).length}); } };
  requestAnimationFrame(f); })"""


def visit(page, url, a, cdp):
    t0 = time.time()
    page.goto(url, wait_until="commit", timeout=120000)
    page.wait_for_function(f"__perf.m.{a.until}", timeout=125000, polling=100)
    page.wait_for_function("!document.getElementById('bootsay')", timeout=10000, polling=100)
    out = {"bar": page.evaluate(BAR),"marks": dict(page.evaluate("__perf.m")), "worker": page.evaluate("window.bootTook || null")}
    if a.join:
        page.fill("#name", "perf")
        t = page.evaluate("performance.now()")
        page.evaluate("document.getElementById('join').click()")
        page.wait_for_function("__perf.m.world", timeout=40000, polling=50)
        m = page.evaluate("__perf.m")
        out["marks"].update(m)
        out["play_to_in"], out["play_to_world"] = round(m["in"] - t), round(m["world"] - t)
    long = page.evaluate("__perf.long")
    ready = out["marks"].get("ready", 1e9)
    out["long"] = {"to_ready": max([d for t, d in long if t <= ready] or [0]), "n": len(long), "total": sum(d for _, d in long), "top": sorted(long, key=lambda x: -x[1])[:6]}
    out["heap_mb"] = round(cdp.send("Runtime.getHeapUsage")["usedSize"] / 1e6, 1)
    out["wall_s"] = round(time.time() - t0, 1)
    return out


def walk(page, cdp, a):
    """Sprint east and west for `a.walk` seconds: the gaps between frames, the script's share, the heap."""
    touch = lambda kind, x=0, y=0: cdp.send("Input.dispatchTouchEvent", {"type": kind, "touchPoints": [] if kind == "touchEnd" else [{"x": x, "y": y}]})
    cdp.send("Performance.enable")
    met = lambda: {m["name"]: m["value"] for m in cdp.send("Performance.getMetrics")["metrics"]}
    out, legs = {"legs": [], "heap_mb": []}, max(1, int(a.walk // 5))
    cdp.send("HeapProfiler.enable")
    m0, h0 = met(), cdp.send("Runtime.getHeapUsage")["usedSize"]
    out["from"], builds = page.evaluate("myPos()"), page.evaluate("HdLook.builds")
    for leg in range(legs):
        way = 1 if leg % 2 == 0 else -1
        touch("touchStart", 90, 600)
        for i in range(1, 9):
            touch("touchMove", 90 + way * i * 9, 600)                 # (pushed far: a sprint)
        out["legs"].append(page.evaluate(FRAMES, 5000))
        touch("touchEnd")
        if leg % 4 == 3:                                      # (every 20 s: what is still held after a collection: a leak grows here)
            cdp.send("HeapProfiler.collectGarbage")
            out["heap_mb"].append(round(cdp.send("Runtime.getHeapUsage")["usedSize"] / 1e6, 1))
    m1 = met()
    world = page.evaluate("rpc('metrics').then((r) => r.metrics || r)")
    out["tick_ms"] = {k: world.get(k) for k in ("tick_ms_p50", "tick_ms_max")}
    secs = m1["Timestamp"] - m0["Timestamp"]
    frames = sum(g["frames"] for g in out["legs"])
    out.update(secs=round(secs, 1), script_ms_frame=round((m1["ScriptDuration"] - m0["ScriptDuration"]) * 1000 / frames, 2),
               task_ms_frame=round((m1["TaskDuration"] - m0["TaskDuration"]) * 1000 / frames, 2), fps=round(frames / secs, 1),
               heap_before_mb=round(h0 / 1e6, 1), heap_after_mb=round(cdp.send("Runtime.getHeapUsage")["usedSize"] / 1e6, 1),
               pos=page.evaluate("myPos()"), land_made=page.evaluate("HdLook.builds") - builds, nodes=m1.get("Nodes"), listeners=m1.get("JSEventListeners"))
    return out


def main():
    p = argparse.ArgumentParser()
    p.add_argument("what", choices=["demo", "local"])
    p.add_argument("--line", default="fast3g", choices=list(LINES))
    p.add_argument("--cpu", type=float, default=4)
    p.add_argument("--warm", action="store_true", help="a second visit in the same browser, and its numbers")
    p.add_argument("--join", action="store_true", help="press Wake up and wait for the land")
    p.add_argument("--walk", type=float, default=0, help="seconds of sprinting in the world (implies --join; 120 at most: the watchdog)")
    p.add_argument("--dist", default=str(ROOT / "dist"))
    p.add_argument("--pyodide", default=None)
    p.add_argument("--bundle", action="store_true", help="local: the server with one script (NEXEL_BUNDLE=1)")
    p.add_argument("--port", type=int, default=PORT)
    p.add_argument("--until", default="usable", choices=["ready", "usable"], help="ready: the first screen whole (no Python needed)")
    p.add_argument("--desk", action="store_true", help="a desk's 1440x900 window, not a phone")
    p.add_argument("--no-sw", action="store_true")
    p.add_argument("--stale", action="store_true", help="demo: the warm visit is a day later (the site's files are asked for again: 304s)")
    a = p.parse_args()
    a.join = a.join or a.walk > 0
    threading.Timer(150, lambda: (print("watchdog: 150 s", flush=True), os._exit(3))).start()
    from playwright.sync_api import sync_playwright
    proc = httpd = None
    if a.what == "demo":
        httpd = serve(a.dist, a.port, a.line, a.pyodide, 0 if a.stale else 600)
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
    else:
        saves = tempfile.mkdtemp(prefix="perf_saves")
        proc = subprocess.Popen([sys.executable, "-m", "nexel_worlds.server", "--saves", saves, "--world", "perf", "--port", str(a.port), "--seed", "12"],
                                cwd=ROOT, env={**os.environ, "PYTHONPATH": str(ROOT / "src"), "NEXEL_BUNDLE": "1" if a.bundle else ""},
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(1.5)
    url, res = f"http://127.0.0.1:{a.port}/", {"what": a.what, "line": a.line, "cpu": a.cpu}
    pw = sync_playwright().start()
    browser = pw.chromium.launch(channel="chrome", headless=True)
    try:
        screen = dict(viewport={"width": 1440, "height": 900}) if a.desk else dict(viewport={"width": 390, "height": 844}, has_touch=True, is_mobile=True, device_scale_factor=3)
        ctx = browser.new_context(**screen, service_workers="block" if a.no_sw else "allow")
        ctx.add_init_script(WATCH)
        if a.line != "none":                                 # (what a phone on such a line says of it: the demo starts its world by it, js/local.js)
            ctx.add_init_script("Object.defineProperty(navigator, \"connection\", {value: {downlink: %s, effectiveType: \"%s\", saveData: false}});" % ((1.6, "3g") if a.line == "fast3g" else (9, "4g")))
        page = ctx.new_page()
        reqs = []
        page.on("requestfinished", lambda r: reqs.append((r.url, r.resource_type)))
        cdp = ctx.new_cdp_session(page)
        cdp.send("Emulation.setCPUThrottlingRate", {"rate": a.cpu})
        if a.what == "local" and a.line != "none":
            rate, trip = LINES[a.line]
            cdp.send("Network.enable")
            cdp.send("Network.emulateNetworkConditions", {"offline": False, "latency": trip * 1000, "downloadThroughput": rate, "uploadThroughput": rate / 2})
        for name in ["cold"] + (["warm"] if a.warm else []):
            reqs.clear()
            if httpd:
                urllib.request.urlopen(url + "__reset").read()
            if name == "warm" and not a.no_sw and a.what == "demo":
                try:                                             # (the second visit is the service worker's, once it has everything)
                    page.wait_for_function("window.swReady === true || !('serviceWorker' in navigator) || !window.swAsked", timeout=60000)
                except Exception:  # noqa: BLE001
                    res["sw"] = "not ready after 60 s"
            if name == "warm":
                a.join_saved, a.join = a.join, False
            res[name] = visit(page, url, a, cdp)
            if name == "warm":
                a.join = a.join_saved
            res[name]["requests"] = len(reqs)
            if httpd:
                log = json.loads(urllib.request.urlopen(url + "__log").read())
                kinds = {}
                for e in log:
                    path = e["path"].split("?")[0]
                    k = "pyodide" if path.startswith("/pyodide/") else "audio" if path.startswith("/audio/") else Path(path).suffix.lstrip(".") or "html"
                    n, b = kinds.get(k, (0, 0))
                    kinds[k] = (n + 1, b + e["wire"])
                res[name]["net"] = {"requests": len(log), "kb": round(sum(e["wire"] for e in log) / 1024), "not_modified": sum(e["status"] == 304 for e in log),
                                    "by_kind": {k: [n, round(b / 1024)] for k, (n, b) in sorted(kinds.items(), key=lambda kv: -kv[1][1])}}
            else:
                sizes = page.evaluate("performance.getEntriesByType('resource').map((e) => [e.initiatorType, e.transferSize, e.encodedBodySize])")
                res[name]["net"] = {"requests": len(sizes) + 1, "kb": round(sum(s[1] for s in sizes) / 1024), "body_kb": round(sum(s[2] for s in sizes) / 1024)}
        if a.walk:
            res["walk"] = walk(page, cdp, a)
        ctx.close()
    finally:
        browser.close()
        pw.stop()
        if httpd:
            httpd.shutdown()
        if proc:
            proc.terminate()
            proc.wait(10)
    print(json.dumps(res), flush=True)
    os._exit(0)


if __name__ == "__main__":
    main()
