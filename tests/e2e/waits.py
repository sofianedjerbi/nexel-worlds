"""Waiting for the game instead of sleeping (a Game's, game.py): the land at rest, the hour on the page, you arrived, a
tick heard, frames drawn. tests/e2e/README.md says which to use when."""

import time
import warnings

from playwright.sync_api import TimeoutError as NotYet

# The land's work, seen from the page: the frame in which a tile changed or a sea was made (the HD look's own work: HdLook.busy).
WATCH = """(() => { if (window.__land) return 1; const L = window.__land = {frame: 0, at: 0}, did = () => { L.at = L.frame; };
  const count = () => { L.frame++; requestAnimationFrame(count); }; requestAnimationFrame(count);
  { const f = drawTile; window.drawTile = function (...a) { did(); return f.apply(this, a); }; }
  if (typeof waterSteps === 'function') { const f = waterSteps; window.waterSteps = function* (...a) { did(); yield* f.apply(this, a); }; }
  return 1; })()"""
# The land at rest: all of it on the screen come, nothing of it left to draw or to make, you and the eye where you are going (it glides there for a second after a
# teleport), and `n` frames drawn since the last piece of the land was, nothing fading in or out
# (the land left behind: away.a, the same for `n` frames);
# the HD look's eye tipped to the pitch it is going to (it tilts over 400 ms into a trench, by a terrace, out of a hole: a record begun
# half way through the tilt went on one way and then back: "back and forth", two tests, one run in eight on a busy machine);
# the HD look's eye come to your level (it rises to you over some frames, hd.js: a px read on the way is another px: a cliff's rim was read 187 or 254 by how far it had come);
# every block's water made for the tiles it has now, and the water's picture drawn since (a block's water is made again a step a
# frame after its tiles change; read before, the gorge's river was the river stamped before it, west of a block's edge: #362);
# and a tick heard from the server since (who is where, what lies on the ground, a door: they come with the tick, 0.1 s)
# (frames, not ms: a busy machine draws fewer in a second, and the land is made a little a frame)
# A stepped page (clock.py STEP) whose frames stopped: its own time stops with them, so REST's timeout never came and the
# test hung to pytest's 300 s with nothing said. No frame in STALL_S s of the wall's: what its lockstep waits for
STALL_S = 30
STALLED = """([n, ms]) => { const P = performance, rest = (%s)([n, ms]); if (!window.__wallTimeout) return rest;
  return Promise.race([rest, new Promise((ok) => { let T = P.now(), at = P.real(); const look = () => { if (P.now() !== T) { T = P.now(); at = P.real(); }
    if (P.real() - at > STALL_S * 1000) ok({lockstep: window.__lockstepState ? __lockstepState() : null, tick: typeof clock === "object" ? clock.tick : null,
      watch: lastWatch, spec: spec && spec.readyState, agent: agentWs && agentWs.readyState}); else __wallTimeout(look, 1000); }; look(); })]); }""".replace("STALL_S", str(STALL_S))
REST = """([n, ms]) => new Promise((ok) => { const L = window.__land, f0 = L.frame, t0 = performance.now(), hd = HdLook.live, w0 = Voxels.wver, c0 = clock;
  const here = () => { const p = ents.get('agent' + myId); if (p && (p.x !== p.tx || p.y !== p.ty)) return false;      // (you, drawn where you are; and every block of land on the screen come and made)
    const [x, y, w, h] = viewRect(0); for (let by = Math.floor(y / B); by <= Math.floor((y + h) / B); by++) for (let bx = Math.floor(x / B); bx <= Math.floor((x + w) / B); bx++) { const b = blocks.get(bkey(bx, by)); if (!b || !Voxels.made(b) || b.seaAt !== b.ver) return false; }   // (and its water made for the tiles it has now: voxels.js work, a step a frame; till then its picture is the one before, a river's old bands)
    return true; };
  const fades = () => [away.a]; let was = fades(), calm = 0, wS = w0;
  // (the HD look: making its land is work; and what stands and the shadows on the land are looked for four times a second,
  // hd.js: once more since the last of the work, then the frames)
  const quarter = () => Math.floor(performance.now() / 250); let q0 = quarter(), at0 = L.at, crossed = !hd;
  const look = () => { if (hd) { if (HdLook.busy || L.at !== at0) { L.at = at0 = L.frame; q0 = quarter(); crossed = false; } else if (!crossed && quarter() !== q0) { crossed = true; L.at = at0 = L.frame; } }
    const at = here(); if (!at) wS = Voxels.wver;   // (the water's picture drawn again after every block's water is made: #362)
    const since = L.frame - Math.max(L.at, f0), v = fades(); calm = v.every((a, i) => Math.abs(a - was[i]) < .002) ? calm + 1 : 0; was = v;
    if (since >= n && crossed && calm >= n && at && (clock !== c0 || performance.now() - t0 > 1000) && dirtyTiles.length === 0 && !arrivingNow && Math.abs(cam.x - camT.x) < .004 && Math.abs(cam.y - camT.y) < .004 && !(hd && (HdLook.busy || Voxels.wver === wS || (HdLook.level[0] !== null && HdLook.level[1] !== HdLook.level[0]) || Math.abs(HdLook.cam.pitch - HdLook.cam.want) > .01))) ok(null);     // (the HD look makes its water ten times a second: once more since)
    else if (performance.now() - t0 > ms) ok([L.frame - f0, L.frame - L.at, dirtyTiles.length, arrivingNow, cam.x - camT.x, cam.y - camT.y, calm, here(), hd && [HdLook.cam.pitch, HdLook.cam.want]]);
    else requestAnimationFrame(look); }; look(); })"""
# Nothing asked of the server and not yet answered, nothing being done, you standing where you are going, no
# panel still sliding: a key's doing is done. (A blinking mark that never ends is not waited for.)
QUIET = """() => !Object.keys(pending).length && !busy && !pendingAct && !myAction && !progress && !pred && walking === null && !refreshing
  && (() => { const p = ents.get('agent' + myId); return !p || (p.x === p.tx && p.y === p.ty); })()
  && document.getAnimations().every((a) => a.playState !== 'running' || !a.effect || a.effect.getComputedTiming().iterations === Infinity)"""
# Nothing asked of the server still unanswered (an action is answered when it ends: a walk at its stop)
ANSWERED = """() => typeof pending === 'undefined' || !Object.keys(pending).length"""
# Nothing of the land left to make: no tile to draw, every block on the screen made, the HD look not at work
MADE = """() => typeof dirtyTiles === 'undefined' || !me || (dirtyTiles.length === 0 && !(HdLook.live && HdLook.busy) && (() => {
  const [x, y, w, h] = viewRect(0); for (let by = Math.floor(y / B); by <= Math.floor((y + h) / B); by++) for (let bx = Math.floor(x / B); bx <= Math.floor((x + w) / B); bx++) { const b = blocks.get(bkey(bx, by)); if (!b || !Voxels.made(b)) return false; }
  return true; })())"""
# You have stopped: no walk and no jump going, no step guessed (pred), your body on its tile, and the world's last tick
# has you on that same tile. What a check of where you are, here or on the server, needs: at any frame's length.
STILL = """() => typeof walking !== 'undefined' && walking === null && !pred && !Leap.on() && (() => {
  const p = ents.get('agent' + myId); return !!p && !!p.e && p.x === p.tx && p.y === p.ty && p.e.x === p.tx && p.e.y === p.ty; })()"""
FRAMES = "(n) => new Promise((ok) => { const f = () => (n-- > 0 ? requestAnimationFrame(f) : ok(1)); f(); })"


# arrive's look, up to 10 frames: {ok: drawn where the server has you (x, y), the camera on you; d: how far from it, n: frames}
ARRIVE = """async ([x, y]) => { const frame = () => new Promise(requestAnimationFrame); let d = 1e9, n = 0;
  for (; n < 10; n++) { const p = ents.get('agent' + myId), s = myPos();
    if (p && s && s.x === x && s.y === y) { d = Math.abs(p.x - x) + Math.abs(p.y - y) + Math.abs(cam.x - camT.x) + Math.abs(cam.y - camT.y); if (d < .04 && Math.abs(p.x - x) < .01 && Math.abs(p.y - y) < .01 && Math.abs(cam.x - camT.x) < .01 && Math.abs(cam.y - camT.y) < .01) return {ok: true, d, n}; }
    await frame(); }
  return {ok: false, d, n}; }"""


# Until `e` (an expression, or a function of none) holds on the page, `n` frames at the most: looked at once a frame. The guard
# counts frames, not ms: a slow runner's 200 ms frames give the game as many frames to get there as 16 ms ones do (#317)
UNTIL = """([e, n]) => new Promise((ok) => { const f = new Function("return (" + e + ")"); let k = 0;
  const look = () => { let v = false; try { v = f(); if (typeof v === "function") v = v(); } catch (x) { v = false; }
    if (v) ok(true); else if (++k > n) ok(false); else requestAnimationFrame(look); }; look(); })"""


def until(page, expr, frames=1200):
    """Until `expr` holds on `page`, `frames` frames at the most (20 s of 60 a second; a guard, never the measure)."""
    if not page.evaluate(UNTIL, [expr, frames]):
        raise AssertionError(f"not within {frames} frames: {expr[:300]}")


class Waits:
    def until(self, expr, frames=1200):
        """Until `expr` holds on the page, `frames` frames at the most (waits.until)."""
        until(self.page, expr, frames)

    def frames(self, n=2):
        """Until `n` more frames are drawn (what was set on the page is in the picture of the next one)."""
        self.js(FRAMES, n)

    def still(self, timeout=8000):
        """Until you have stopped and the world has you where you are (STILL): in place of a sleep after a walk, a tap,
        a jump, before what reads where you are."""
        self._until(f"({STILL})()", timeout)

    def until_world(self, check, frames=600):
        """Until check(the world's word on you: game.server()) holds, asked once a frame, `frames` frames at the most:
        for what only the world knows (what is in your pack, your hearts). -> its last word."""
        for _ in range(frames):
            s = self.server()
            if check(s):
                return s
            self.frames(1)
        return self.server()

    def hold_until(self, keys, expr, timeout=8000):
        """The keys held until `expr` holds on the page (you past a tile, in the air, at an edge), then let go: how far
        a hold goes is the game's, not the frames' (a sleep with keys held went further the longer a frame was, and
        less far on a runner whose frames are cut at 0.1 s)."""
        for k in keys:
            self.page.keyboard.down(k)
        try:
            self._until(expr, timeout)
        finally:
            for k in reversed(keys):
                self.page.keyboard.up(k)

    def rest(self, frames=3, timeout=20000):
        """Until the land is at rest: all of it drawn and made, and `frames` frames drawn since (after land was
        stamped, a setting changed what is drawn, a teleport: where a sleep of 0.6 to 1.2 s was, too short on a busy
        machine and too long on an idle one). Then the picture can be read."""
        self.js(WATCH)
        late = self.js(STALLED % REST, [frames, timeout])
        if isinstance(late, dict):
            raise AssertionError(f"the page made no frame in {STALL_S} s of the wall's time: {late}")
        if late:
            warnings.warn(f"the land was not at rest after {timeout} ms: frames, frames since its last piece, tiles to draw, arriving, the eye's way to go, frames nothing faded, the land on the screen all come: {late}", stacklevel=2)

    def arrive(self, timeout=8000):
        """After a teleport: until you are drawn where the server has you, and the land there is at rest. It fails when
        you stop getting there: no nearer for `timeout` ms AND 30 frames (#67: once 0.82 of a tile short for 8 s), not
        when frames are slow: on a renderer drawing a frame every 2 s you glide there a step a frame, and arrive."""
        s = self.server()
        t0 = last = time.monotonic()
        best, still = None, 0
        while True:
            r = self.page.evaluate(ARRIVE, [s["x"], s["y"]])
            if r["ok"]:
                break
            now = time.monotonic()
            if best is None or r["d"] < best - 1e-3:
                best, still, last = r["d"], 0, now
            else:
                still += r["n"]
            if (still >= 30 and now - last >= timeout / 1000) or now - t0 > 120:
                raise AssertionError(f"not drawn where the server has you, {s['x']}, {s['y']}: " + str(self.js("(() => { const p = ents.get('agent' + myId); return [p && [p.x, p.y, p.tx, p.ty], myPos(), [cam.x, cam.y], [camT.x, camT.y]]; })()")))
        self.rest()

    def hour(self, phase, timeout=20000, still=False):
        """The time of day (0 sunrise, .375 noon, .75 nightfall), back when the page has it and has drawn the land
        by it: the server says the hour with its next tick, 0.1 s on or more.
        still: and the page's hour stays that one, to the next hour(): for two pictures taken a moment apart that
        are compared px by px (a setting on, then off, the land made again between them). With the sun low the light
        changes by the second, and on a busy machine the moment is long: the sun's side of a step "had a shadow"
        (11 to 43 units of 255), two runs in three with two browsers at work, never alone."""
        self.js("(() => { if (window.__sun) { onTick = window.__sun; window.__sun = null; } return 1; })()")
        if self.js("HdLook.live"):
            # (the HD look: the land made as it is before the hour jumps. A jump that came while the land was being made
            # for a stamp left that land without the new hour's shadows until the sun had moved an eighth of a tile on,
            # 1.3 s: hd.js marks the land as made for the new hour, hd_sun.js painted the hour's before into it. In play
            # the hour moves a step at a time)
            self.rest()
        self.rpc("dev_time", phase=phase)
        try:
            self._until("(p) => Math.abs((((clock.phase || 0) - p) % 1 + 1.5) % 1 - .5) < .004", timeout, phase)
        except NotYet as e:
            raise AssertionError(f"the hour {phase} did not come to the page: {self.js('[clock.phase, clock.tick, clock.time]')}") from e
        if still:
            self.js("(p) => { const real = window.__sun = onTick; onTick = (d) => { d.phase = p; real(d); }; clock.phase = p; return 1; }", phase)
        self.rest()

    def heard(self):
        """Until the page has a tick the server made after now (the next one: 0.1 s at most on an idle machine)."""
        t = self.rpc("ping").get("tick")
        if t is None:
            return self.tick(2)
        self.settle(f"clock.tick > {t}")
