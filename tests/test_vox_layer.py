"""VOX, what draws the land as blocks for the HD look (web/js/vox_*.js), is a layer of its own, as a library is: it
loads here with none of the game, on a GPU that only counts what it is asked to draw. A name of the game used in it
would not be there to find. And the curved world's roll (vox_curve.js), the one function for where a row is drawn."""

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

WEB = Path(__file__).parent.parent / "src" / "nexel_worlds" / "web"
NODE = shutil.which("node")
pytestmark = pytest.mark.skipif(NODE is None, reason="node is not installed")
FILES = [str(WEB / "js" / f"vox_{n}.js") for n in ("gl", "curve", "sky", "mesh", "style_glsl", "style_fs", "style_land", "style_sprites", "style_glow", "style")]

RUN = r"""
const vm = require("vm"), fs = require("fs"), seen = {corners: 0, painted: 0, fronts: [], sides: []};
const gl = new Proxy({}, {get: (t, k) => typeof k !== "string" ? undefined : k === "drawArrays" ? (m, first, n) => { seen.corners += n; }
  : /^[A-Z_0-9]+$/.test(k) ? 1 : k.startsWith("drawingBuffer") ? 64 : () => ({})});
const canvas = () => ({width: 0, height: 0, addEventListener() {}, getContext: (kind) => kind === "webgl2" ? gl : new Proxy({}, {get: () => () => {}, set: () => true})});
const box = {document: {createElement: canvas}, performance: {now: () => 0}, console};
vm.createContext(box);
vm.runInContext(process.argv.slice(1).map((f) => fs.readFileSync(f, "utf8")).join("\n") + "\nthis.VoxStyle = VoxStyle; this.VoxCurve = VoxCurve; this.VoxSky = VoxSky;", box);
const out = {style: typeof box.VoxStyle.create, sky: typeof box.VoxSky.draw};
const C = box.VoxCurve, curve = {y0: 200, yh: 60, ref: 24, lean: .6, line: 60};
// ...and what the shader is given says what the function says: the GLSL, read as JS, at every px of flat ground,
// for land under the eye, at its height and over it
const js = C.GLSL.replace("uniform vec4 uCurve; uniform float uFloor;", "").replace(/uFloor/g, "(c.floor || 0)").replace("float curveY(float f, float h, out float past)", "function curveY(f, h)").replace(/float /g, "let ")
  .replace(/\bmax\(/g, "Math.max(").replace(/uCurve\.x/g, "c.y0").replace(/uCurve\.y/g, "c.yh").replace(/uCurve\.z/g, "c.ref").replace(/uCurve\.w/g, "c.lean");
{ const gpu = new Function("c", "let past; " + js + "; return (f, h) => [curveY(f, h), past];")(curve), E = C.edge(curve), top = (h, slope) => { let best = 1e9; for (let f = 500; f > -4000; f -= 1) best = Math.min(best, C.y(curve, f, h + slope * Math.max(0, curve.y0 + curve.ref - f))); return best; };
  const r = out.curve = {worst: 0, flat: true, up: true, back: 0, edge: E, line: C.y(curve, E + curve.ref, curve.ref), low: C.y(curve, E - 40, -40), high: C.line(curve, curve.ref + 30), highest: top(curve.ref + 30, 0),
    off: C.y(null, 123.5, 3), past: [C.past(curve, E + curve.ref + 1, curve.ref), C.past(curve, E + curve.ref - 7, curve.ref), C.past(curve, E - 7, 0)],
    slopes: [.25, .5, 1, 2].map((s) => top(curve.ref, s))};      // (the highest any row of a slope that rises north, s px a px, is drawn: its horizon)
  for (const h of [-40, 0, 24, 60]) for (let f = 500, last = 1e9; f > -700; f -= .5) {
    const y = C.y(curve, f, h), [g, past] = gpu(f, h), up = Math.max(0, h - curve.ref), d = curve.y0 - (f - h + up) + curve.lean * up;
    r.worst = Math.max(r.worst, Math.abs(y - g), Math.abs(past - C.past(curve, f, h)));
    if (d <= 0 && Math.abs(y - (f - h)) > 1e-9) r.flat = false;                         // before the roll's start: the flat picture, exactly
    if (!past) { if (y > last + 1e-6) r.up = false; if (!up) r.back = Math.max(r.back, Math.abs(C.inv(curve, y) - (f - h))); last = y; }
  } }
// a floor (vox_curve.js): the horizon is where a row is still a quarter of itself; the rows of tiles (48 px of the
// picture, 3 a px of paint, the flat picture's px counted from 1) are whole px of paint tall, and the rows of paint
// a height shows are some of the tile's 16, in order, the same whatever the frame
{ const cf = {y0: 200, yh: 60, ref: 0, lean: .6, floor: .25}, gpu = new Function("c", "let past; " + js + "; return (f, h) => [curveY(f, h), past];")(cf), E = C.edge(cf);
  const r = out.floor = {worst: 0, edge: E, line: C.line(cf), at: C.y(cf, E, 0), squeeze: [C.squeeze(cf, 300), C.squeeze(cf, E + .001), C.squeeze(cf, E - 500)], heights: [], whole: true, picks: true, back: 0, down: C.y(cf, E - 48, 0) - C.y(cf, E, 0)};
  for (const h of [-40, 0, 24, 60]) for (let f = 500; f > -700; f -= .5) { const [g, past] = gpu(f, h); r.worst = Math.max(r.worst, Math.abs(C.y(cf, f, h) - g), Math.abs(past - C.past(cf, f, h))); if (!past && !h) r.back = Math.max(r.back, Math.abs(C.inv(cf, C.y(cf, f, 0)) - f)); }
  for (const o of [1, 2, 3, 17.5]) for (let f = o + 48 * 5; f - 48 > E; f -= 48) { const n = (C.snap(cf, f, 0, o, 3) - C.snap(cf, f - 48, 0, o, 3)) / 3; if (Math.abs(n - Math.round(n)) > 1e-9) r.whole = false; if (o === 1) r.heights.push(Math.round(n)); }
  for (let n = 1; n <= 16; n++) for (let i = 0, last = -1; i < n; i++) { const j = C.rows(i, n, 16); if (j <= last || j > 15 || j !== Math.floor(j)) r.picks = false; last = j; } }
console.log(JSON.stringify(out));
"""


def run():
    r = subprocess.run([NODE, "-e", RUN, "--", *FILES], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-1500:]
    return json.loads(r.stdout)


def test_the_layer_loads_with_none_of_the_game():
    out = run()
    assert out["style"] == "function" and out["sky"] == "function"


def test_the_roll_is_one_function_for_the_gpu_and_for_what_is_drawn_over_its_picture():
    """vox_curve.js: before the line where the roll starts the picture is the flat one exactly; past it the rows go
    up to their horizon and never back before it; the place found back from the screen is the place drawn there; and
    the shader's own lines, read as JS, give the same px as the function everywhere, for land under the eye, level
    with it and over it. And every slope has its horizon: however steeply the land rises to the north, no row of
    it is drawn higher than a line (the push down is a square, a slope is a line)."""
    c = run()["curve"]
    assert c["flat"] and c["up"]
    assert c["worst"] < 1e-9 and c["back"] < 1e-6, c
    # the row on the horizon is drawn on the line: at the eye's height, and lower land too (it is looked down on);
    # level land 30 px over the eye has its horizon 12 px over the line (30 less the 0.6 of it that goes with the roll)
    assert abs(c["line"] - 60) < 1e-9 and abs(c["low"] - 60) < 1e-9 and abs(c["high"] - 48) < 1e-9 and abs(c["highest"] - 48) < .01, c
    assert c["off"] == 120.5                                     # no curve: flat
    assert c["past"] == [0, 7, 7]
    # a slope of s px up a px north: its horizon is y0 - D * (1 + s)^2 / (1 + 0.6 s)^2 (D: from the roll's start to the level horizon, 140)
    for s, top in zip((.25, .5, 1, 2), c["slopes"]):
        assert abs(top - (200 - 140 * (1 + s) ** 2 / (1 + .6 * s) ** 2)) < .5, (s, top)


def test_with_a_floor_the_horizon_is_where_a_row_is_a_quarter_of_itself_and_rows_are_whole_px_of_paint():
    """vox_curve.js, "things 6-9 tiles north are squashed into the horizon band... never scale pixel art": with
    floor .25 the roll's horizon is where level ground is squeezed to a quarter (D * floor^2 under the parabola's
    top), what is past it comes down again at once, the shader's lines say the same, and a tile's row, put on whole
    px of the paint, is a whole number of them tall, from 16 down to 4 and never under: the rows of paint it shows
    are picked by its height alone (some of its 16, in order, none twice)."""
    f = run()["floor"]
    assert f["worst"] < 1e-9 and f["back"] < 1e-6, f
    assert abs(f["edge"] - (200 - 2 * 140 * .75)) < 1e-9 and abs(f["line"] - (60 + 140 * .0625)) < 1e-9 and abs(f["at"] - f["line"]) < 1e-9
    assert f["squeeze"][0] == 1 and abs(f["squeeze"][1] - .25) < 1e-4 and f["squeeze"][2] == .25
    assert f["down"] > 0                                         # past the horizon: down again, behind it
    assert f["whole"] and f["picks"]
    assert f["heights"][0] == 16 and f["heights"] == sorted(f["heights"], reverse=True) and min(f["heights"]) >= 4, f["heights"]
