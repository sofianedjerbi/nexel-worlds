"""VOX, the engine that draws the land as blocks (web/js/vox_*.js), is a layer of its own, as a library is: it runs
here with none of the game loaded, on a world made up for the test and a GPU that only counts what it is asked to
draw. A name of the game used in it would not be there to find."""

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

WEB = Path(__file__).parent.parent / "src" / "megastructure" / "web"
NODE = shutil.which("node")
pytestmark = pytest.mark.skipif(NODE is None, reason="node is not installed")
FILES = [str(WEB / "js" / f"vox_{n}.js") for n in ("gl", "curve", "sky", "pages", "mesh", "section", "models", "light", "mark", "engine")]

# A chunk of 4 x 4 tiles, flat at 0, with: a hill two high on (1,1) and (2,1); south of the first a roof at 3 over
# empty cells (a cave: its floor 0, empty up to 2, solid at 3); water on (3,3). Nothing is known round it.
# Models (vox_models.js): on (0,3) a box with a top and a front and a flat thing (a top alone); `plain`: a host that
# has no models at all.
RUN = r"""
const vm = require("vm"), fs = require("fs"), seen = {corners: 0, painted: 0, fronts: [], sides: []};
const gl = new Proxy({}, {get: (t, k) => typeof k !== "string" ? undefined : k === "drawArrays" ? (m, first, n) => { seen.corners += n; }
  : /^[A-Z_0-9]+$/.test(k) ? 1 : k.startsWith("drawingBuffer") ? 64 : () => ({})});
const canvas = () => ({width: 0, height: 0, addEventListener() {}, getContext: (kind) => kind === "webgl2" ? gl : new Proxy({}, {get: () => () => {}, set: () => true})});
const box = {document: {createElement: canvas}, performance: {now: () => 0}, console};
vm.createContext(box);
vm.runInContext(process.argv.slice(1).map((f) => fs.readFileSync(f, "utf8")).join("\n") + "\nthis.Vox = Vox; this.VoxCurve = VoxCurve;", box);
const plain = process.env.VOX_PLAIN === "1", models = {"0,3": [{x: 0, y: 2, z: 2, w: 4, d: 11, h: 2, top: [0, 0], front: [4, 0]}, {x: 0, y: 13, z: 0, w: 4, d: 3, h: 0, top: [8, 0, 1]}]};
const land = {"1,1": [2], "2,1": [2], "1,2": [0, 2, 3], "3,3": [-1]};
const host = {
  column: (x, y) => (x < 0 || y < 0 || x > 3 || y > 3 ? null : land[x + "," + y] || [0]),
  water: (x, y) => x === 3 && y === 3,
  paintTop: (x, y, z, px, at, stride) => { seen.painted++; px[at] = 0xff00ff00; },
  paintFront: (z, v, px, at, stride) => { seen.fronts.push(z); px[at] = 0xff0000ff; },
  shape: (x, y, z) => (z > 0 ? 1 : 0), profile: (id) => new Uint8Array(16).fill(id ? 2 : 0),
  band: (z) => 2,
  side: (z) => { seen.sides.push(z); return {band: [200, 150, 100], body: [180, 130, 100], foot: [140, 100, 80], shadow: [80, 64, 134, .3]}; },
};
if (!plain) { host.models = (x, y) => models[x + "," + y] || null; host.modelSheet = () => { seen.sheets = (seen.sheets || 0) + 1; return {px: new Uint32Array(16 * 16), w: 16, h: 16}; }; }
const engine = box.Vox.create(host, {size: 4, cell: 16, up: 8, levels: [-2, 4], variants: 2, under: [0, 0, 0, .8], sea: [0, 0, 1], tuck: 6, inset: 2, bands: 5});
const view = {w: 640, h: 360, pw: 640, ph: 360, ox: 0, oy: 0, tile: 48, row: 2, clear: [0, 0, 0], light: [1, 1, 1], water: null, chunks: [{cx: 0, cy: 0}]};
const out = {ready: engine.ready(), before: engine.made(0, 0)};
engine.work([{cx: 0, cy: 0}], 1e9);
out.made = engine.made(0, 0); out.faces = engine.faces; out.ledges = engine.sides; out.painted = seen.painted; out.models = engine.models;
engine.draw(view); out.corners = seen.corners; out.fronts = seen.fronts; out.sides = seen.sides;
seen.corners = 0; engine.draw({...view, sun: {dir: [-1, .45], alpha: .3, shade: [.1, .1, .3], cast: null, glass: {alpha: .5, wave: .9, ripple: 1, phase: 0}}}); out.sunCorners = seen.corners;      // the sun on it (vox_light.js)
// the curved world (vox_curve.js): the same view rolled and with a sky is drawn as well (the sky: one face more)
const C = box.VoxCurve, curve = {y0: 200, yh: 60, ref: 24, lean: .6, line: 60};
seen.corners = 0; engine.draw({...view, curve, sky: {line: 60, t: 1, shift: 0, top: [0, 0, 1], low: [1, 1, 1], cloud: [1, 1, 1], far: [0, 0, 0], near: [0, 0, 0], orb: [1, 1, 0], at: [.5, .5, 5], stars: 0}});
out.bent = seen.corners; seen.corners = 0;
// ...and what the shader is given says what the function says: the GLSL, read as JS, at every px of flat ground,
// for land under the eye, at its height and over it
const js = C.GLSL.replace("uniform vec4 uCurve;", "").replace("float curveY(float f, float h, out float past)", "function curveY(f, h)").replace(/float /g, "let ")
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
// marks (vox_mark.js): a box two levels high, a flat square, and one that is not there (a: 0), over the same view
engine.draw({...view, marks: [{x: 1, y: 1, z0: 0, z1: 2, colour: [1, 1, 1], a: 1, fill: .2}, {x: 2, y: 2, z0: 0, z1: 0, colour: [1, 1, 1], a: 1, fill: .2}, {x: 0, y: 0, z0: 0, z1: 1, colour: [1, 0, 0], a: 0}]});
out.marked = seen.corners; seen.corners = 0;
models["0,3"].push({x: 0, y: 0, z: 0, w: 4, d: 3, h: 6, top: [0, 0], front: [0, 0]}); engine.touch(0, 3); engine.work([{cx: 0, cy: 0}], 1e9);      // a post is put on the tile
out.posted = engine.models; out.repaint = seen.painted - out.painted; seen.painted = out.painted;
delete models["0,3"]; engine.touch(0, 3); engine.work([{cx: 0, cy: 0}], 1e9); out.bare = engine.models;      // ...and all of it taken away
seen.corners = 0; engine.draw(view); engine.draw(view); out.bareCorners = seen.corners / 2; out.sheets = seen.sheets || 0; seen.painted = out.painted;
delete land["1,1"]; engine.touch(1, 1); engine.work([{cx: 0, cy: 0}], 1e9);      // the hill's first tile is dug away
out.after = engine.faces; out.ledgesAfter = engine.sides; out.again = seen.painted - out.painted;
engine.forget(() => false); out.left = engine.chunks;
console.log(JSON.stringify(out));
"""


def run(plain=False):
    r = subprocess.run([NODE, "-e", RUN, "--", *FILES], capture_output=True, text=True, env={**os.environ, "VOX_PLAIN": "1" if plain else "0"})
    assert r.returncode == 0, r.stderr[-1500:]
    return json.loads(r.stdout)


def test_the_engine_runs_with_none_of_the_game_and_makes_the_faces_the_cells_say():
    out = run()
    assert out["ready"] and not out["before"] and out["made"]
    # tops: 12 plain tiles, the hill's two, the cave's floor and its roof = 16, each painted once; water: one face,
    # one more under each of the three tiles of shore beside it; the water tile is asked for its paint too (what
    # floats on it: this host paints something), and has a top for that
    assert out["painted"] == 17
    # fronts: the hill's two tiles, two cells each over what is south of them (the cave's empty cells; the plain);
    # the roof's one cell over the plain south of it. None on the chunk's last row (what is south is not known),
    # none into the water.
    # sides: the hill drops two levels west of its first tile and east of its second: there its lower level leans
    # out a bank, a top and a front each (its top level does not: the roof one high has none either)
    assert out["ledges"] == 2
    assert out["faces"] == 16 + 1 + 1 + 3 + 5 + 2 * 2
    # all of it drawn, six corners a face; a face that lies on the ground (the 16 tops, the water and the three under
    # the shore, what floats, the two banks' tops: 23; a model's two tops) is four strips north to south, so that it
    # bends with the ground (vox_curve.js); the 7 fronts and the model's front are one piece
    assert out["faces"] == 30 and out["corners"] == (23 * 4 + 7) * 6 + (2 * 4 + 1) * 6
    assert out["bent"] == out["corners"] + 6                     # (curved, under a sky: the same faces, and the sky's)
    assert out["fronts"] == [z for z in range(-2, 5) for _ in range(2)]      # the fronts' sheet: a level a strip, two variants
    assert out["sides"] == list(range(-2, 5))                    # the ledges' colours: a level a row


def test_a_tile_that_changed_is_painted_again_alone_and_its_chunks_faces_made_again():
    out = run()
    assert out["again"] == 1                                     # one tile, one top
    # its two fronts are gone; the hill's other tile now drops west as well as east: two ledges still
    assert out["after"] == 16 + 1 + 1 + 3 + 3 + 2 * 2 and out["ledgesAfter"] == 2
    assert out["left"] == 0                                      # (and a chunk let go of is gone)


def test_models_are_boxes_of_two_faces_made_again_with_their_tile():
    out = run()
    assert out["models"] == 3                                    # a box: its top and its front; a flat thing: its top
    assert out["faces"] == 16 + 1 + 1 + 3 + 5 + 2 * 2            # (the land's faces are the land's alone)
    assert out["posted"] == 5 and out["repaint"] == 1            # a box more on the tile that was touched: two faces more
    assert out["bare"] == 0 and out["bareCorners"] == (23 * 4 + 7) * 6      # none left: nothing of them is drawn
    assert out["sheets"] == 1                                    # the sheet is asked for once, however many frames


def test_a_host_with_no_models_is_drawn_as_before():
    out = run(plain=True)
    assert out["models"] == 0 and out["posted"] == 0 and out["sheets"] == 0
    assert out["faces"] == 16 + 1 + 1 + 3 + 5 + 2 * 2 and out["corners"] == (23 * 4 + 7) * 6


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


def test_a_mark_is_a_box_of_the_land_its_top_its_front_and_its_corners():
    """vox_mark.js: a cell shown as a box is its top's wash in four strips (it bends with the ground) and its front's
    in one, a bracket of two arms at each of its four outer corners and a tick each side where the top meets the
    front, each with a px of ink under it; a flat square has no front and no ticks; one with no strength is not drawn."""
    out = run()
    box, flat = (4 + 1) + (4 * 2 + 2) * 2, 4 + (4 * 2) * 2
    assert out["marked"] == out["corners"] + (box + flat) * 6


# The land cut open (view.cut) is a section through blocks: vox_section.js. A chunk of 8 x 8 tiles, all solid up to 3,
# with a room in (2,2): its floor 0, empty up to 2, a roof at 3. The cut: the room down to its floor, the tile south of
# it down to 0 too, the next one down to 2 (the eye's line: two levels a tile).
CUT = r"""
const vm = require("vm"), fs = require("fs"), seen = {corners: 0};
const gl = new Proxy({}, {get: (t, k) => typeof k !== "string" ? undefined : k === "drawArrays" ? (m, first, n) => { seen.corners += n; }
  : /^[A-Z_0-9]+$/.test(k) ? 1 : k.startsWith("drawingBuffer") ? 64 : () => ({})});
const canvas = () => ({width: 0, height: 0, addEventListener() {}, getContext: (kind) => kind === "webgl2" ? gl : new Proxy({}, {get: () => () => {}, set: () => true})});
const box = {document: {createElement: canvas}, performance: {now: () => 0}, console};
vm.createContext(box);
vm.runInContext(process.argv.slice(1).map((f) => fs.readFileSync(f, "utf8")).join("\n") + "\nthis.Vox = Vox; this.VoxSection = VoxSection;", box);
const land = {"2,2": [0, 2, 3]};
const host = {column: (x, y) => (x < 0 || y < 0 || x > 7 || y > 7 ? null : land[x + "," + y] || [3]), water: () => false, paintTop() {}, paintFront() {},
  shape: () => 0, profile: () => new Uint8Array(16), band: () => 2, side: () => ({band: [200, 150, 100], body: [180, 130, 100], foot: [140, 100, 80], shadow: [80, 64, 134, .3]})};
const cfg = {size: 8, cell: 16, up: 8, levels: [-2, 4], variants: 2, under: [0, 0, 0, .8], sea: [0, 0, 1], tuck: 6, inset: 2, bands: 5};
const cutOf = (x, y, w, h, at) => { const px = new Uint8Array(w * h * 4); for (let j = 0; j < h; j++) for (let i = 0; i < w; i++) { const lv = at(x + i, y + j); if (lv === null) continue; const v = lv + 32768, o = (j * w + i) * 4; px[o] = v & 255; px[o + 1] = v >> 8; px[o + 2] = 255; px[o + 3] = 255; } return {x, y, w, h, px, ver: "a", a: 1, earth: [.3, .2, .2]}; };
const cut = cutOf(2, 2, 1, 3, (x, y) => [0, 0, 2][y - 2]), strip = (z) => Math.max(-2, Math.min(4, z)) + 2;
const m = box.VoxSection.build(host, cfg, strip, cut), out = {tops: m.tops, fronts: m.fronts, banks: m.banks, n: m.n, corners: m.pages.reduce((s, p) => s + p[2], 0)};
// each piece of a face: [x, y, z, kind, bits] of its first corner (16 bytes a corner; px from the cut's corner tile)
const view16 = new DataView(m.data); out.faces = [];
for (let at = 0; at < m.data.byteLength; at += 16 * 6) out.faces.push([view16.getInt16(at, true), view16.getInt16(at + 2, true), view16.getInt16(at + 4, true), view16.getUint8(at + 9), view16.getUint8(at + 8)]);
const engine = box.Vox.create(host, cfg), view = {w: 640, h: 360, pw: 640, ph: 360, ox: 0, oy: 0, tile: 48, row: 2, clear: [0, 0, 0], light: [1, 1, 1], water: null, chunks: [{cx: 0, cy: 0}]};
engine.ready(); engine.work([{cx: 0, cy: 0}], 1e9);
engine.draw(view); out.plain = seen.corners; seen.corners = 0; engine.draw({...view, cut}); out.open = seen.corners; out.made = engine.section.faces;
// what making it again costs, as walking a tile makes it: the widest place there is (29 x 29 tiles of cave under 12
// levels of rock, and the six rows south of it cut for the eye's line)
const deep = {column: (x, y) => (x >= 0 && x < 29 && y >= 0 && y < 29 ? [0, 2, 12] : [12]), water: () => false, shape: () => 0, band: () => 2};
const big = cutOf(0, 0, 29, 35, (x, y) => (y < 29 ? 0 : Math.min(12, 2 * (y - 29)))), {performance} = require("perf_hooks"), times = [];
for (let k = 0; k < 30; k++) { const t0 = performance.now(); out.big = box.VoxSection.build(deep, cfg, strip, big).n; times.push(performance.now() - t0); }
out.ms = times.sort((a, b) => a - b)[5];
console.log(JSON.stringify(out));
"""


def cut_run():
    r = subprocess.run([NODE, "-e", CUT, "--", *FILES], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-1500:]
    return json.loads(r.stdout)


def test_the_land_cut_open_is_a_section_with_the_walls_of_the_hole_and_the_tops_of_what_is_sliced():
    out = cut_run()
    # the wall north of the room: the chunk has its two cells that look into the room; the cut lifts the roof off, and
    # the cell behind the roof (level 3) is seen: one front, at the room's north edge, in a cave's dark (bit 8)
    assert out["fronts"] == 1 and [0, 0, 24, 1, 8] in out["faces"], out
    # the tiles south of the room are solid and sliced: a top each, the cut's kind (5), at 0 and at 2; the higher
    # one drops to the lower north of it: a line along that side (bit 1); none where the land beside it still stands
    assert out["tops"] == 2 and [0, 16, 0, 5, 0] in out["faces"] and [0, 32, 16, 5, 1] in out["faces"], out
    # west and east of the room and of the tile cut to 0, the rock stands three levels over the cut: its levels 1 and
    # 2 lean out a bank each (2 px a level), on the cut tile: 2 x 2 x 2; none beside the tile cut to 2 (one level
    # stands over it: a wall's top level does not lean)
    assert out["banks"] == 8 and out["n"] == 11, out
    assert out["corners"] == (2 + 8) * 4 * 6 + 1 * 6             # (what lies is four strips, as the land's: it bends with it)
    # drawn: the land twice (what is left, then what was left out, to mark it), the cut's faces once, the fill
    assert out["made"] == 11 and out["open"] == 2 * out["plain"] + out["corners"] + 6, out


def test_making_the_section_again_when_the_cut_changes_tile_costs_under_two_ms():
    out = cut_run()
    assert out["big"] > 500, out                                 # (its north wall ten levels over the cave's own, the sliced tops south of it, the banks)
    assert out["ms"] < 2, out
