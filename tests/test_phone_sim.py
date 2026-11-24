"""tools/phone_sim.py's numbers (a CPU profile's top functions, a scenario's table row) and the GPU's clock it reads
(js/gpu_time.js, under node with a GL that answers its queries as a GPU would)."""

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from phone_sim_js import top  # noqa: E402

NODE = shutil.which("node")


def node(n, fid, url, line, children=()):
    return {"id": n, "callFrame": {"functionName": fid, "url": url, "lineNumber": line - 1}, "children": list(children)}


def test_top_names_a_canvas_call_by_its_caller_and_leaves_idle_out():
    prof = {"nodes": [node(1, "(root)", "", 1, [2, 5, 6]), node(2, "frame", "http://x/js/hd.js", 270, [3]), node(3, "ent", "http://x/js/hd.js", 18, [4]),
                      node(4, "setTransform", "", 1), node(5, "(idle)", "", 1), node(6, "(program)", "", 1)],
            "samples": [4, 4, 3, 2, 5, 5, 6], "timeDeltas": [1000] * 7}
    t = top(prof)
    assert t["self"][0] == ("setTransform <- ent hd.js:18", 2.0, 50.0)
    assert t["total"][0] == ("frame hd.js:270", 4.0, 100.0) and ("ent hd.js:18", 3.0, 75.0) in t["total"]
    assert t["meta_ms"] == {"(idle)": 2, "(program)": 1} and t["busy_ms"] == 4


def test_a_scenarios_row():
    import phone_sim
    r = {"f": [[0, 16.7, 50], [16.7, 40, 52], [56, 16.6, 60]], "hd": [[0, 5, 8, 2000, 1, 3]] * 3, "gpu": [], "long": [[1, 60]], "went": None}
    s = phone_sim.stats(r)
    assert s["over16"] == 1 and s["over33"] == 1 and s["gpu"] == "n/a" and s["long"] == [1, 60, 60] and s["heap_mb"] == [50, 60]
    assert "n/a" in phone_sim.table({"stand": s})


# A GL with the timer: a query's ms are what `cost` says that frame cost; `jump` marks the GPU's clock disjoint
GL = """
const out = [], cost = {a: 0, b: 0}; let jump = false;
function gl(name, timer) { const qs = [];
  return {name, isContextLost: () => false, QUERY_RESULT_AVAILABLE: 1, QUERY_RESULT: 2,
    getExtension: (e) => (timer && e === "EXT_disjoint_timer_query_webgl2" ? {TIME_ELAPSED_EXT: 9, GPU_DISJOINT_EXT: 8} : null),
    getParameter: (p) => (p === 8 ? jump : 0), createQuery: () => ({}),
    beginQuery: (k, q) => { q.ns = null; q.open = name; }, endQuery: () => { const q = qs.find((x) => x.open === name); },
    getQueryParameter: (q, p) => (p === 1 ? q.ns !== null : q.ns), _qs: qs }; }
globalThis.HTMLCanvasElement = function () {}; HTMLCanvasElement.prototype.getContext = function (k) { return this.ctx; };
eval(require("fs").readFileSync(process.argv[1], "utf8").replace("const GpuTime", "globalThis.GpuTime"));
const A = Object.assign(new HTMLCanvasElement(), {ctx: gl("a", true)}), B = Object.assign(new HTMLCanvasElement(), {ctx: gl("b", true)});
A.getContext("webgl2"); B.getContext("webgl2");
// each beginQuery's query is done (its ns set) when the next frame begins, at the cost of that frame
for (const c of [A.ctx, B.ctx]) { const b = c.beginQuery; c.beginQuery = (k, q) => { b(k, q); c._open = q; }; c.endQuery = () => { c._open.ns = cost[c.name] * 1e6; }; }
const step = (t, a, b) => { cost.a = a; cost.b = b; GpuTime.frame(t); };
step(0, 1, 2); step(16, 3, 4); step(32, 5, 6); out.push(GpuTime.take());
jump = true; step(48, 1, 1); jump = false; step(64, 2, 2); out.push(GpuTime.take(), GpuTime.ok, GpuTime.contexts);
GpuTime.stop(); out.push(A.ctx._open.ns);
console.log(JSON.stringify(out));
"""


@pytest.mark.skipif(NODE is None, reason="node is not installed")
def test_the_gpus_ms_are_one_frame_each_summed_over_canvases_and_a_jump_is_dropped():
    r = subprocess.run([NODE, "-e", GL, str(ROOT / "src/nexel_worlds/web/js/gpu_time.js")], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    first, second, ok, n, last = json.loads(r.stdout)
    assert first == [7, 11] and second == [4] and ok and n == 2, (first, second)       # (frame 2: 3+4, frame 3: 5+6; the jumped one gone)
    assert last == 2e6                                                                  # stop() closes the open query


NO_TIMER = """globalThis.HTMLCanvasElement = function () {}; HTMLCanvasElement.prototype.getContext = function () { return this.ctx; };
eval(require("fs").readFileSync(process.argv[1], "utf8").replace("const GpuTime", "globalThis.GpuTime"));
const c = Object.assign(new HTMLCanvasElement(), {ctx: {isContextLost: () => false, getExtension: () => null}}); c.getContext("webgl2");
GpuTime.frame(1); GpuTime.frame(2); console.log(JSON.stringify([GpuTime.ok, GpuTime.ms, GpuTime.take()]));"""


@pytest.mark.skipif(NODE is None, reason="node is not installed")
def test_no_timer_no_numbers():
    r = subprocess.run([NODE, "-e", NO_TIMER, str(ROOT / "src/nexel_worlds/web/js/gpu_time.js")], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert json.loads(r.stdout) == [False, None, []]
