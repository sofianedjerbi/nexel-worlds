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
FILES = [str(WEB / "js" / f"vox_{n}.js") for n in ("gl", "curve", "sky", "pages", "mesh", "models", "light", "engine")]

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
// the curved world (vox_curve.js): the same view bent and with a sky is drawn as well (the sky: one face more)
const C = box.VoxCurve, curves = [{y0: 200, yh: 60, ref: 24, sink: 2, soft: 48, g: 0, lean: .5, line: 84}, {y0: 200, yh: 60, ref: 24, sink: 2, soft: 48, g: 1.2, lean: .5, line: 84}];
seen.corners = 0; engine.draw({...view, curve: curves[1], sky: {line: 60, t: 1, shift: 0, top: [0, 0, 1], low: [1, 1, 1], cloud: [1, 1, 1], far: [0, 0, 0], near: [0, 0, 0], orb: [1, 1, 0], at: [.5, .5, 5], stars: 0}});
out.bent = seen.corners; seen.corners = 0;
// ...and what the shader is given says what the function says: the GLSL, read as JS, at every px of flat ground,
// for land under the eye, at its height and over it, with no stretch and with one
const js = C.GLSL.replace("uniform vec4 uCurve; uniform vec3 uRoll;", "").replace(/uRoll\.z/g, "c.lean").replace(/uRoll\.x/g, "c.soft").replace(/uRoll\.y/g, "c.g").replace("float curveY(float f, float h, out float past)", "function curveY(f, h)").replace(/float |int /g, "let ")
  .replace(/\bsin\(/g, "Math.sin(").replace(/\basin\(/g, "Math.asin(").replace(/\bmax\(/g, "Math.max(").replace(/uCurve\.x/g, "c.y0").replace(/uCurve\.y/g, "c.yh").replace(/uCurve\.z/g, "c.ref").replace(/uCurve\.w/g, "c.sink");
out.curve = curves.map((curve) => {
  const gpu = new Function("c", "let past; " + js + "; return (f, h) => [curveY(f, h), past];")(curve), E = C.edge(curve);
  const r = {worst: 0, flat: true, up: true, back: 0, edge: E, line: C.y(curve, E + curve.ref, curve.ref), low: C.y(curve, E - 40, -40), high: C.y(curve, E + curve.ref, curve.ref + 30),
    off: C.y(null, 123.5, 3), past: [C.past(curve, E + curve.ref + 1, curve.ref), C.past(curve, E + curve.ref - 7, curve.ref + 50), C.past(curve, E - 7, 0)]};
  for (const h of [-40, 0, 24, 60]) for (let f = 500, last = 1e9; f > -700; f -= .5) {
    const y = C.y(curve, f, h), [g, past] = gpu(f, h), s = f - Math.min(h, curve.ref);      // (s: where the bend looks at it)
    r.worst = Math.max(r.worst, Math.abs(y - g), Math.abs(past - C.past(curve, f, h)));
    if (s - .5 * Math.max(0, h - curve.ref) >= curve.y0 && Math.abs(y - (f - h)) > 1e-9) r.flat = false;      // under the bend's start: the flat picture, exactly
    if (!past) { if (y > last + 1e-6) r.up = false; r.back = Math.max(r.back, Math.abs(C.inv(curve, C.warp(curve, s)) - s)); last = y; }
  }
  return r; });
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


def test_the_bend_is_one_function_for_the_gpu_and_for_what_is_drawn_over_its_picture():
    """vox_curve.js: under the line where the bend starts the picture is the flat one exactly; over it the rows go up
    to the horizon and never back; the place found back from the screen is the place drawn there; and the shader's
    own lines, read as JS, give the same px as the function everywhere, for land under the eye, level with it and
    over it. With no stretch, and with one: then more ground is seen before the horizon."""
    near, far = run()["curve"]
    for c in (near, far):
        assert c["flat"] and c["up"]
        assert c["worst"] < 1e-4 and c["back"] < .02, c       # (px; the stretch is found by halving: a hundredth of a px at the horizon)
        # the row on the horizon is drawn on the line: at the eye's height, and lower land too (it is looked down on);
        # land 30 px higher than the eye stands half of that over the line (it leans back)
        assert abs(c["line"] - 60) < 1e-4 and abs(c["low"] - 60) < 1e-4 and abs(c["high"] - 45) < 1e-4, c
        assert c["off"] == 120.5                                 # no curve: flat
        assert c["past"] == [0, 7, 7]
    assert abs((200 - far["edge"]) / (200 - near["edge"]) - 2.2) < 1e-9      # (a stretch of 1.2: 2.2 times the ground in the bend)


def test_the_sun_on_the_land_is_the_engines_own_and_adds_no_face():
    """vox_light.js: asked for a sun (view.sun), the engine draws the same faces, lit by its own program: nothing of
    the game is needed for it."""
    out = run()
    assert out["sunCorners"] == out["corners"]
