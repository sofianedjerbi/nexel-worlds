"""The page's side of tools/phone_sim.py: the CPU benchmark it calibrates by, the recorder it plays with, its plot;
and the top functions of a CPU profile.

BENCH is a fixed piece of work shaped like a frame of the game's script (typed arrays filled as a mesh is, small
objects in a Map as tiles and bodies are, a sort, strings as the debug screen writes them): its ms, median of 7
rounds, is a machine's score. The same text runs on this Mac and on a phone (`--device android --bench`).
"""

BENCH = """() => { const round = () => { const t0 = performance.now();
    const n = 120000, v = new Float32Array(n * 3), ix = new Uint32Array(n);
    for (let k = 0; k < 6; k++) for (let i = 0; i < n; i++) { const x = (i * 7 + k) % 251, y = (i * 13) % 97; v[i * 3] = x * .5 + Math.sin(y * .01); v[i * 3 + 1] = y; v[i * 3 + 2] = (x ^ y) & 15; ix[i] = (i * 2654435761) >>> 8; }
    const m = new Map(); for (let i = 0; i < 60000; i++) { const key = (i % 4000) + "," + (i % 37); const o = m.get(key) || {x: i % 4000, y: i % 37, n: 0, kind: i & 3 ? "meadow" : "stone"}; o.n++; m.set(key, o); }
    const list = [...m.values()]; list.sort((a, b) => a.n - b.n || a.x - b.x || a.y - b.y);
    let s = ""; for (let i = 0; i < 4000; i++) s += `XYZ ${list[i % list.length].x.toFixed(2)} / ${(v[i] || 0).toFixed(1)} ` + (i % 9 ? "" : "\\n");
    let h = 0; for (let i = 0; i < ix.length; i += 3) h = (h * 31 + ix[i]) | 0;
    return [performance.now() - t0, h + s.length]; };
  round(); const ms = []; for (let i = 0; i < 7; i++) ms.push(round()[0]); ms.sort((a, b) => a - b); return ms[3]; }"""

# Every frame while __sim.on: when it began, the gap since the last, the heap; the HD look's own numbers of that
# frame (hd.js hands them to HdView.perf: script ms, draws, land ms) and HdLook.faces; the GPU's ms (gpu_time.js,
# a frame or three late: a list of their own); long tasks. HdView.perf is wrapped as soon as it is there.
RECORD = """(() => { const S = window.__sim = {on: false, f: [], hd: [], gpu: [], long: [], last: 0, wrapped: false};
  try { new PerformanceObserver((l) => { if (S.on) for (const e of l.getEntries()) S.long.push([e.startTime, e.duration]); }).observe({entryTypes: ["longtask"]}); } catch (e) {}
  const wrap = () => { if (S.wrapped || typeof HdView === "undefined" || typeof GpuTime === "undefined") return; S.wrapped = true; const p0 = HdView.perf;
    HdView.perf = (now, js, drew, calls, slice, wrote) => { if (S.on) { S.hd.push([now, js, calls, HdLook.faces || 0, slice, HdLook.ms || 0]); GpuTime.frame(now); } return p0(now, js, drew, calls, slice, wrote); }; };
  const f = (t) => { wrap(); if (S.on) { const m = performance.memory; S.f.push([t, S.last ? t - S.last : 0, m ? m.usedJSHeapSize / 1048576 : 0]); } S.last = t; requestAnimationFrame(f); };
  requestAnimationFrame(f); })()"""
START = "(() => { const S = __sim; S.f = []; S.hd = []; S.long = []; S.last = 0; if (typeof GpuTime !== 'undefined') GpuTime.take(); S.on = true; return S.wrapped; })()"
STOP = """(() => { const S = __sim; S.on = false; const g = typeof GpuTime !== 'undefined' ? GpuTime.take() : []; if (typeof GpuTime !== 'undefined' && !F3.on) GpuTime.stop();
  return {f: S.f.slice(1), hd: S.hd, gpu: g, gpuOk: typeof GpuTime !== 'undefined' && GpuTime.ok, long: S.long}; })()"""

# The plot: one band a scenario, a bar a frame (its gap between frames, ms), the script's ms under it in a darker
# tone, the GPU's as a line of dots; lines at 16.7 and 33 ms. Drawn on a canvas in whole px, no smoothing.
PLOT = """(runs) => { const W = 1200, band = 150, top = 46, c = document.createElement('canvas'); c.width = W; c.height = top + runs.rows.length * band + 10;
  document.body.style.margin = 0; document.body.appendChild(c); const g = c.getContext('2d'); g.imageSmoothingEnabled = false;
  g.fillStyle = '#2b2233'; g.fillRect(0, 0, c.width, c.height); g.font = '14px monospace'; g.fillStyle = '#f4e8c8';
  g.fillText(runs.title, 10, 20); g.fillStyle = '#d9a066'; g.fillRect(10, 30, 12, 8); g.fillStyle = '#f4e8c8'; g.fillText('frame gap', 26, 39);
  g.fillStyle = '#8a5a44'; g.fillRect(120, 30, 12, 8); g.fillStyle = '#f4e8c8'; g.fillText('script', 136, 39); g.fillStyle = '#7ec8e3'; g.fillRect(210, 33, 4, 4); g.fillStyle = '#f4e8c8'; g.fillText('GPU', 220, 39);
  const ms = 66, X0 = 250;
  runs.rows.forEach((r, i) => { const y0 = top + i * band, h = band - 24, k = h / ms, base = y0 + h;
    g.fillStyle = '#3a2f45'; g.fillRect(X0, y0, W - X0 - 10, h); g.fillStyle = '#f4e8c8'; g.fillText(r.name, 10, y0 + 16);
    g.fillText(r.note, 10, y0 + 34); g.fillText(r.note2, 10, y0 + 52);
    const n = Math.max(r.gap.length, 1), bw = Math.max(1, Math.floor((W - X0 - 10) / n));
    r.gap.forEach((v, j) => { const hh = Math.round(Math.min(ms, v) * k); g.fillStyle = v > 33.4 ? '#d95763' : v > 16.8 ? '#d9a066' : '#99c46b'; g.fillRect(X0 + j * bw, base - hh, Math.max(1, bw - (bw > 2)), hh); });
    r.js.forEach((v, j) => { const hh = Math.round(Math.min(ms, v) * k); g.fillStyle = '#8a5a44'; g.fillRect(X0 + Math.round(j * n / Math.max(1, r.js.length)) * bw, base - hh, Math.max(1, bw - (bw > 2)), hh); });
    r.gpu.forEach((v, j) => { g.fillStyle = '#7ec8e3'; g.fillRect(X0 + Math.round(j * n / Math.max(1, r.gpu.length)) * bw, base - Math.round(Math.min(ms, v) * k) - 1, 3, 3); });
    for (const [l, col] of [[16.7, '#f4e8c8'], [33.3, '#d95763']]) { g.fillStyle = col; for (let x = X0; x < W - 10; x += 4) g.fillRect(x, base - Math.round(l * k), 2, 1); g.fillText(l + '', X0 - 34, base - Math.round(l * k) + 4); }
    g.fillStyle = '#f4e8c8'; g.fillText('66 ms', X0 - 46, y0 + 10); });
  return c.toDataURL('image/png'); }"""


META = {"(idle)", "(program)", "(garbage collector)", "(root)"}


def top(profile, n=8):
    """A CDP CPU profile's busy time -> {"self": [(function file:line, ms, % of busy)], "total": the same with what
    it calls, "meta_ms": idle, "(program)" (Chrome's own work outside JS), the collector}. Busy: JS and the collector.
    A native function (a canvas call) is named with the game's function that called it."""
    nodes = {nd["id"]: nd for nd in profile["nodes"]}
    up = {c: nd["id"] for nd in profile["nodes"] for c in nd.get("children", [])}
    name = lambda cf: f"{cf['functionName'] or '(anonymous)'} {cf['url'].rsplit('/', 1)[-1]}:{cf['lineNumber'] + 1}" if cf["url"] else cf["functionName"]
    dt = dict.fromkeys(nodes, 0)
    for sid, d in zip(profile["samples"], profile["timeDeltas"]):
        dt[sid] += d
    own, inc, meta = {}, {}, {}
    for i, us in dt.items():
        cf = nodes[i]["callFrame"]
        if cf["functionName"] in META:
            meta[cf["functionName"]] = meta.get(cf["functionName"], 0) + us
            continue
        k = name(cf) if cf["url"] or i not in up else f"{cf['functionName']} <- {name(nodes[up[i]]['callFrame'])}"
        own[k] = own.get(k, 0) + us
        seen, j = set(), i
        while j in nodes:
            c = nodes[j]["callFrame"]
            if c["url"] and name(c) not in seen:
                seen.add(name(c))
                inc[name(c)] = inc.get(name(c), 0) + us
            j = up.get(j)
    busy = (sum(own.values()) + meta.get("(garbage collector)", 0)) or 1
    rows = lambda d: [(k, round(v / 1000, 1), round(100 * v / busy, 1)) for k, v in sorted(d.items(), key=lambda kv: -kv[1])[:n]]
    return {"self": rows(own), "total": rows(inc), "meta_ms": {k: round(v / 1000) for k, v in meta.items() if v}, "busy_ms": round(busy / 1000)}
