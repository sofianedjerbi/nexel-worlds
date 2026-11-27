"""A player in Chrome, for end-to-end tests: join, look at the screen and the server, press keys, use dev tools.

What the tools change is waited for, not slept on: land stamped is on the page (and drawn) when stamp() returns,
things given are in your pack when give() does. They slept a fixed while instead (0.4 s a stamp, 0.7 s a cleared
area, 0.8 s a gift: 440 s of the suite's 1440, and under load not always long enough)."""

import itertools
import json
import os
import time
import warnings

import clock
from playwright.sync_api import TimeoutError as NotYet
from waits import ANSWERED, MADE, QUIET, Waits


SERVER_LOG = None        # the test server's log (conftest.py)
HOURED = set()           # the tests whose first page has set the hour (Game.join): a test's later pages leave it
_names = itertools.count(1)
# what the tests on this worker's world laid out (dev_stamp, dev_col): [x0, y0, x1, y1] boxes, for the next HD test to lay
# its place out again over them (test_e2e_hd_sun.py hd)
BUILT = []


def new_name(prefix="e2e") -> str:
    """A name nobody has in this worker's world (they were drawn at random from nine thousand: now and then a
    second player had the first one's name, and was turned away)."""
    return f"{prefix}{os.getpid() % 100000}n{next(_names)}"


# Is the land stamped at (x0, y0) on the page as it was stamped? (Tiles this screen has not loaded: not waited for.)
STAMPED = """([x0, y0, rows, levels, roofs]) => rows.every((row, j) => [...row].every((ch, i) => {
  const x = x0 + i, y = y0 + j; if (!tile(x, y)) return true;
  const lc = levels[j] && levels[j][i] !== undefined ? levels[j][i] : '0', lv = /[0-9]/.test(lc) ? +lc : lc === lc.toUpperCase() ? lc.charCodeAt(0) - 55 : 96 - lc.charCodeAt(0);
  const rf = roofs[j] && roofs[j][i] !== undefined ? +roofs[j][i] : 0;
  return combAt(x, y) === ch && floorAt(x, y) === lv && (rf < 2 || roofAt(x, y) === rf); }))"""
# Ask for your pack again until it has what was given (the page asks every 0.7 s by itself)
HAS = """async (inv) => { const ok = () => meObs && Object.entries(inv).every(([k, n]) => (meObs.self.inventory[k] || 0) === n);
  for (let i = 0; i < 40 && !ok(); i++) { await refresh(); if (!ok()) await new Promise((done) => setTimeout(done, 25)); } return ok(); }"""
# What the page's sockets did, and when (ms since the page came): said when a player does not get in
SOCKETS = """(() => { const log = window.__sockets = [], WS = window.WebSocket, at = () => Math.round(performance.now());
  window.WebSocket = class extends WS { constructor(...a) { super(...a); const u = String(a[0]).replace(/^wss?:\\/\\/[^/]+/, ''); log.push([at(), u, 'new']);
    this.addEventListener('open', () => log.push([at(), u, 'open']));
    this.addEventListener('close', (e) => log.push([at(), u, 'close', e.code, e.reason, e.wasClean]));
    this.addEventListener('error', () => log.push([at(), u, 'error']));
    this.addEventListener('message', (m) => { if (u === '/agent' && log.filter((r) => r[1] === u && r[2] === 'message').length < 4) log.push([at(), u, 'message', String(m.data).slice(0, 60)]); });
    const send = this.send.bind(this); this.send = (d) => { if (u === '/agent' && log.filter((r) => r[1] === u && r[2] === 'send').length < 4) log.push([at(), u, 'send', String(d).slice(0, 60)]); return send(d); }; } }; })()"""


class Game(Waits):
    def __init__(self, page, url):
        self.page, self.url, self.errors, self.loaded = page, url, [], None
        page.on("pageerror", lambda e: self.errors.append(str(e)))

    # ---- session
    def join(self, name, zoom=4, curve=None):
        """(curve: the settings' Curved world: None, as the game has it for a player (on); False: the flat picture,
        for a test that cannot be about the curved one; True: the curved one)"""
        self.load(zoom, curve)
        self.page.wait_for_function("typeof ready !== 'undefined'")
        self.page.click("#name")
        self.page.keyboard.type(name)
        self.page.keyboard.press("Enter")
        self.name = name
        state = """() => ({me, myId, obs: !!meObs, toast: $('toast').style.display === 'block' ? $('toastt').innerText : '', clock: $('clock').textContent,
          agent: typeof agentWs === 'undefined' || !agentWs ? null : agentWs.readyState, spec: typeof spec === 'undefined' || !spec ? null : spec.readyState, stamp: webStamp, url: location.href,
          now: Math.round(performance.now()), sockets: window.__sockets})"""
        try:
            # (in; or the socket shut before you were: seen in five runs of eight, a busy machine, the server's log
            # saying "connected" and, two or three seconds on, "disconnected": the cause not found. Once more, then,
            # the same name: the server knows it. What the page had is said, so that it can be found one day)
            self.wait("(meObs && myPos()) || (agentWs && agentWs.readyState === 3 && !me)", 25000)
            if not self.js("!!(meObs && myPos())"):
                warnings.warn(f"{name} was shut out and went in again: {self.js(state)}", stacklevel=2)
                self.js(f"joinGame({json.dumps(name)})")
                self.wait("meObs && myPos()", 25000)         # (however busy the machine)
        except Exception as e:                               # not in: say what the page has, so that the cause can be read afterwards
            state = self.js(state)
            said = []
            if SERVER_LOG and SERVER_LOG.exists():           # what the server said of them, anything that went wrong in it, and its last words
                lines = SERVER_LOG.read_text(errors="replace").splitlines()
                said = [ln[:200] for ln in lines if name in ln or "Traceback" in ln or "ERROR" in ln or "Error" in ln][-12:] + ["...the log's end:"] + [ln[:160] for ln in lines[-14:]]
            raise AssertionError(f"{name} did not get in: {state}; page errors: {self.errors}; server: {said}") from e
        self.js(clock.DAY)
        # (morning, set by the test's first page only: dev_time only goes forward, so a second page of the same test set it
        # again and sent the world on to tomorrow's .3, 12000 ticks, mid-test: a Nyxwing summoned 4 s before had come 1199.6 s
        # ago for the late page. Whatever hour the test is at, its later pages leave the world's day as it is)
        test = os.environ.get("PYTEST_CURRENT_TEST", "").split(" ")[0]
        if test not in HOURED:
            HOURED.add(test)
            self.rpc("dev_time", phase=.3)
        # (awake: the land there and drawn; and the picture all there, not still coming in over the first screen's: that
        # takes 0.7 s, and a test that looked at the canvas's animations meanwhile counted it with its own)
        self.js("(() => { for (const a of cv.getAnimations()) a.finish(); return 1; })()")
        self.settle("!arrivingNow")

    def load(self, zoom=4, curve=None, wait="load"):
        """The page asked for (once: join() asks, unless it was asked for ahead, pages.py). -> self"""
        ask = f"{self.url}/?zoom={zoom}" + ("" if curve is None else f"&curve={curve or 0}")
        if self.loaded != ask:
            self.page.add_init_script(SOCKETS)
            self.page.goto(ask, wait_until=wait)
            self.loaded = ask
        return self

    def flat(self):
        """The flat picture for this page (the settings' Curved world off): for a test that counts the art px of a
        face far north of you, which are whole px only there. A last resort: each use says why."""
        self.js("(() => { Curve.force = 'off'; return 1; })()")
        self.wait("!Curve.on")

    def js(self, expr, arg=None):
        return self.page.evaluate(expr, arg) if arg is not None else self.page.evaluate(expr)

    def rpc(self, op, **kw):
        if op == "dev_stamp" and kw.get("rows"):
            BUILT.append([kw["x"], kw["y"], kw["x"] + max(map(len, kw["rows"])) - 1, kw["y"] + len(kw["rows"]) - 1])
        elif op == "dev_col" and kw.get("tiles"):
            t = kw["tiles"]
            BUILT.append([min(a for a, _ in t), min(b for _, b in t), max(a for a, _ in t), max(b for _, b in t)])
        return self.js(f"(a) => rpc({json.dumps(op)}, a)", kw)

    def wait(self, expr, timeout=5000):
        self._until(expr, timeout)

    def _until(self, expr, timeout, arg=None):
        """Until `expr` (an expression, or a function of `arg`) holds on the page, `timeout` ms at the most. Stepped
        (clock.py STEP): ms of the page's own time, which a slow runner gives at a seventh of the wall's (8 s of it
        in some 50 s), the wall only a guard; then asked once more, and the timeout's error if it still does not hold."""
        if not clock.step:
            return self.page.wait_for_function(expr, arg=arg, timeout=timeout)
        ask = f"(a) => {{ const v = ({expr}); return !!(typeof v === 'function' ? v(a) : v); }}"
        t = self.page.evaluate("performance.now()")
        self.page.wait_for_function(f"([a, until]) => ({ask})(a) || performance.now() >= until", arg=[arg, t + timeout],
                                    timeout=max(30000, timeout * 30))
        if not self.page.evaluate(ask, arg):
            raise NotYet(f"not within {timeout} ms of the page's own time: {expr[:200]}")

    def sleep(self, ms):
        """Time that has to pass in the game (a walk, a swing, a fade). Not for "until it is drawn": rest(), hour(),
        frames(); not for "until the server has it": wait()."""
        self.page.wait_for_timeout(ms)
        if clock.now != 1 and ms >= 200:
            # (on the tests' clock a sleep is a quarter of itself: the game's time. What it also gave was the machine's
            # time: land being made, and the server's answers on their way, which take what they take. Until those are
            # done, then; the whole sleep at the most)
            try:
                self._until(f"({MADE})() && ({ANSWERED})()", ms - clock.real(ms))
            except NotYet:
                pass

    # ---- the world around us
    def pos(self):
        p = self.js("myPos()")
        return p["x"], p["y"]

    def server(self):
        """The server's truth about us: position and inventory."""
        s = self.rpc("observe")["obs"]["self"]
        return s

    def tile(self, dx, dy):
        x, y = self.pos()
        return self.js(f"combAt({x + dx}, {y + dy})")

    def settle(self, expr, arg=None, timeout=3000):
        """Until the page has it, then until the land is drawn. (Not there after `timeout`: on, as after the sleep
        this was: the test says what is wrong, in its own words.)"""
        for e, a in ((expr, arg), ("dirtyTiles.length === 0", None)):
            try:
                self._until(e, timeout, a)
            except NotYet:
                pass

    def stamp(self, dx, dy, rows, levels=None, roofs=None, heads=None):
        """Paint tiles relative to us; `levels`: optional rows of heights (digits, a-l below sea level); `roofs`: how
        much higher the land goes over a cave on that ground; `heads`: how many cells of that are empty (2 if not said).
        Back when the page has them."""
        x, y = self.pos()
        self.rpc("dev_stamp", x=x + dx, y=y + dy, rows=rows, levels=levels or [], roofs=roofs or [], heads=heads or [])
        self.settle(STAMPED, [x + dx, y + dy, rows, levels or [], roofs or []])
        # (and nothing of the stamp itself left in the air: the dust of what it took away, the bounce of what it put.
        # A sleep let them go; a fall's dust was counted with the stamp's, a wall read through it)
        self.js("(() => { parts.length = 0; puffs.length = 0; pops.clear(); return 1; })()")

    def tick(self, n=1):
        """Until the world has said `n` more ticks to the page (what a tick carries: who is where, what lies on the ground)."""
        for _ in range(n):
            self.js("(() => { window.__tick = clock; return 1; })()")
            self.settle("clock !== window.__tick")

    def clear_area(self, r=10):
        """Flat meadow around us, no animals near (they wander into tests), nothing lying on the ground (left by one)."""
        self.rpc("dev_creatures", clear=40)
        self.stamp(-r, -r, ["." * (2 * r + 1)] * (2 * r + 1))
        # (and you on it: the stamp lays the meadow at level 0 under you, your own height stays where you woke. Woken on a
        # hill, your first step was a fall of four layers and more: "assert 'step' in {'fallthud', 'rustle'}", the sound
        # test on main's run 45843840225)
        s = self.server()
        if s.get("z", 0) != 0:
            self.rpc("dev_teleport", x=s["x"], y=s["y"], z=0)
            self.arrive()
        # (a tick made after the clearing, and the meadow made: a test's own land is not stamped into chunks still being
        # painted for the clearing. It waited two ticks of whatever came, 0.15 to 0.25 s: most of the painting, by chance)
        self.rest()

    def spawn(self, kind, dx, dy, still=0):
        """A creature beside you; back when the page has it (it comes with the next tick: a key pressed before that
        acted on nothing)."""
        cid = self.rpc("dev_creatures", kind=kind, dx=dx, dy=dy, still=still)["spawned"]
        if cid is not None:
            try:
                self._until(f"ents.has({json.dumps(kind + str(cid))})", 1500)
            except NotYet:
                pass                 # (out of what this screen is told of: as it was)
        return cid

    def lucky(self):
        """Every creature leaves all it can (its drops are by chance: sim/entities.py), for as long as this server runs."""
        self.rpc("dev_luck", luck=1000)

    def give(self, **items):
        """Things into your pack; back when the page has them."""
        inv = self.rpc("dev_give", items=items).get("inventory") or {}
        if not self.js(HAS, {k: inv.get(k, 0) for k in items}):
            self.sleep(800)      # (not seen: as it was, the page's own next look)

    def inv(self, item):
        return self.server()["inventory"].get(item, 0)

    # ---- the screen
    def actions(self):
        """The keys said on the screen: beside what you face or the build cursor (prompts.js), and in the corner."""
        return " | ".join(t for t in (self.js(f"$('{w}').innerText").strip().replace("\n", " | ") for w in ("prompts", "actions")) if t)

    def toast(self):
        return self.js("$('toast').style.display === 'block' ? $('toastt').innerText : ''")

    def hold_item(self, name):
        self.js(f"selectItem({json.dumps(name)})")
        self.frames(2)

    def face(self, dx, dy):
        self.js(f"(() => {{ const p = ents.get('agent' + myId); p.fx = {dx}; p.fy = {dy}; }})()")
        self.frames(2)           # let a frame redraw the hints

    # ---- keys
    def press(self, key, wait=300):
        """A key, then until what it did is done (QUIET), `wait` ms at the most: a key that only moves a mark or opens
        a panel is done in two frames, one that asks the server when it has answered. (It slept `wait` whatever the
        key: 0.3 s x 490 presses.) A wait of more than 0.4 s is slept whole: it was written for something the page
        does not say it is doing (a pile flying into your hands, the dust of a dig, a door swinging)."""
        self.page.keyboard.press(key)
        if 60 < wait <= 400:
            self.frames(2)
            try:
                self._until(QUIET, wait)
            except NotYet:
                pass
        elif wait:
            self.sleep(wait)

    def hold(self, keys, ms):
        for k in keys:
            self.page.keyboard.down(k)
        t0 = time.time()
        if ms <= 150:
            # (a tap: and a frame drawn with the key down, since it is a frame that sets you out (walk.js walkOn): a key
            # let go before one is a stop where you stand. 90 ms of the game's time are 22 of the machine's on the tests'
            # clock, less than a frame of a busy one: "(8, -12, 6) == (8, -11, 0)", a tap down a ladder that did nothing)
            self.frames(1)
        clock.held(self.page, ms if clock.step else max(0, ms - (time.time() - t0) * 1000 * clock.now))   # (stepped: ms of the page's own time, STEP)   # (the game's time to the ms: a tap of 90 ms is a tile, one of 240 is two)
        for k in reversed(keys):
            self.page.keyboard.up(k)
        # (and the server's answers to what the keys asked: the walk's, its stop's. They take the machine's time, the hold
        # the game's: at a pace over 1 a short hold was let go before the walk was answered, and what the test read next
        # was the server half way: a step not finished, a wall not yet met)
        try:
            self._until(ANSWERED, 3000)
        except NotYet:
            pass

    def start_recording(self):
        """Our character's on-screen position every frame, until recording(): [ms, x, y, tiles ahead of the world (walk.js
        leadOf; 0 not walking)]. A loop goes on while its recording is the last asked for (else two ran into one)."""
        self.js("""() => { window.__rec = []; const t0 = performance.now(), id = window.__recId = (window.__recId || 0) + 1; window.__recOn = true;
          function f(n) { if (!__recOn || __recId !== id) return; const p = ents.get('agent' + myId); if (p) __rec.push([n - t0, p.x, p.y, walking && p.walking ? leadOf(p, n) : 0]);
            requestAnimationFrame(f); } requestAnimationFrame(f); }""")

    def recording(self):
        return self.js("(() => { __recOn = false; return __rec; })()")

    def act(self, tool, **args):
        return self.js(f"(a) => act({json.dumps(tool)}, a)", args)

    def timed(self, fn):
        t0 = time.time()
        r = fn()
        return r, time.time() - t0
