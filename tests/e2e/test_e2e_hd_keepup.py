"""The HD look on a slow machine (a phone): walking, the picture is never held still (only after a jump: a teleport,
waking); the far land's patches lie on the world's grid, so a step makes only those at the edges; a walk's poses are
read back from their canvas once, not at every change of pose (hd_level.js runsOf). A phone's CPU is the tests' own
slowed by Chrome (Emulation.setCPUThrottlingRate), as tools/phone_sim.py does."""

from test_e2e_hd_sun import hd

# each frame, for n frames: [the picture held (the last one kept), your x]
FRAMES = """async (n) => { const o = []; for (let i = 0; i < n; i++) { await new Promise((r) => requestAnimationFrame(r)); o.push([HdLook.held, myPos().x]); } return o; }"""
# the px of 64 px wide canvases read back (a body's sprite: hd.js ent) over n frames
READS = """async (n) => { const P = CanvasRenderingContext2D.prototype, gi = P.getImageData; let k = 0;
  P.getImageData = function (...a) { if (this.canvas.width === 64) k++; return gi.apply(this, a); };
  try { for (let i = 0; i < n; i++) await new Promise((r) => requestAnimationFrame(r)); } finally { P.getImageData = gi; } return k; }"""


def test_walking_on_a_slow_phone_the_picture_is_never_held(browser, server):
    g = hd(browser, server)
    x0 = g.pos()[0]
    cdp = g.page.context.new_cdp_session(g.page)
    cdp.send("Emulation.setCPUThrottlingRate", {"rate": 8})         # (a slow phone: a land takes many frames to make)
    try:
        g.page.keyboard.down("Shift")
        g.page.keyboard.down("ArrowRight")
        f = g.js(FRAMES, 90)
    finally:
        g.page.keyboard.up("ArrowRight")
        g.page.keyboard.up("Shift")
        cdp.send("Emulation.setCPUThrottlingRate", {"rate": 1})
    held = [x for h, x in f if h]
    assert f[-1][1] - x0 >= 8 and not held, (f[-1][1] - x0, held)      # (it was held most of a sprint: the land made 9 tiles back)


def test_a_step_makes_only_the_far_patches_at_the_edges(browser, server):
    """(The walk's land is come before it is counted: four tiles east, then back. A step that brought a block of the
    land in, by where you woke, made the far patches over it again, rightly (they were drawn from nothing known): 563,
    one run in six, the two blocks it brought counted with them.)"""
    g = hd(browser, server)
    x, y = g.pos()
    for k in (5, 0):
        g.rpc("dev_teleport", x=x + k, y=y)
        g.arrive()
        g.rest()
    made = []
    for k in (1, 2, 3, 4):
        f0 = g.js("HdLook.work.fars")
        g.rpc("dev_teleport", x=x + k, y=y)
        g.arrive()
        g.rest()
        made.append(g.js("HdLook.work.fars") - f0)
    assert max(made[1:]) < 200, made                                   # (the first: the cleared meadow's own patches made again; 593 a step: every patch a tile off the last one's)


def test_a_walks_poses_are_read_once(browser, server):
    """(Once your dressed sheet is made (wear.js: between frames, a bear's in 300 to 500 turns; till then you are not
    drawn): on a busy page it came during the forty frames counted, and every pose was new there, 9 to 28 reads)"""
    g = hd(browser, server)
    g.wait("(() => { const e = ents.get('agent' + myId).e; return !!wornReady(agentTint(e.name), e.worn, e.race, e.bot); })()", 15000)
    g.page.keyboard.down("ArrowRight")
    try:
        g.wait(f"myPos().x >= {g.pos()[0] + 6}", timeout=12000)         # (every pose of the walk seen once)
        n = g.js(READS, 40)
    finally:
        g.page.keyboard.up("ArrowRight")
    assert n <= 6, n                                                   # (a new pose now and then, read by each of its two readers; it was one a change of pose: 75 in 80 frames of a sprint)
