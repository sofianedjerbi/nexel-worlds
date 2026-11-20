"""A player in Chrome, for end-to-end tests: join, look at the screen and the server, press keys, use dev tools.

What the tools change is waited for, not slept on: land stamped is on the page (and drawn) when stamp() returns,
things given are in your pack when give() does. They slept a fixed while instead (0.4 s a stamp, 0.7 s a cleared
area, 0.8 s a gift: 440 s of the suite's 1440, and under load not always long enough)."""

import itertools
import json
import os
import time
import warnings

from playwright.sync_api import TimeoutError as NotYet


SERVER_LOG = None        # the test server's log (conftest.py)
_names = itertools.count(1)


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


class Game:
    def __init__(self, page, url):
        self.page, self.url, self.errors = page, url, []
        page.on("pageerror", lambda e: self.errors.append(str(e)))

    # ---- session
    def join(self, name, zoom=4, curve=None, look="classic"):
        """(curve: the settings' Curved world: None, as the game has it for a player (Far); False: the flat picture,
        for a test that cannot be about the curved one; "near", "far": that one)"""
        self.page.add_init_script(SOCKETS)
        # (look: the settings' Look; the tests that came before the HD look pin the classic picture's px: classic unless asked)
        self.page.goto(f"{self.url}/?zoom={zoom}&look={look}" + ("" if curve is None else f"&curve={curve or 0}"))
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
        self.rpc("dev_time", phase=.3)
        # (awake: the land there and drawn; and the picture all there, not still coming in over the first screen's: that
        # takes 0.7 s, and a test that looked at the canvas's animations meanwhile counted it with its own)
        self.js("(() => { for (const a of cv.getAnimations()) a.finish(); return 1; })()")
        self.settle("!arrivingNow")

    def flat(self):
        """The flat picture for this page (the settings' Curved world off): for a test that counts the art px of a
        face far north of you, which are whole px only there. A last resort: each use says why."""
        self.js("(() => { Curve.force = 'off'; return 1; })()")
        self.wait("!Curve.on")

    def js(self, expr, arg=None):
        return self.page.evaluate(expr, arg) if arg is not None else self.page.evaluate(expr)

    def rpc(self, op, **kw):
        return self.js(f"(a) => rpc({json.dumps(op)}, a)", kw)

    def wait(self, expr, timeout=5000):
        self.page.wait_for_function(expr, timeout=timeout)

    def sleep(self, ms):
        self.page.wait_for_timeout(ms)

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
                self.page.wait_for_function(e, arg=a, timeout=timeout)
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
        self.tick(2)

    def spawn(self, kind, dx, dy, still=0):
        return self.rpc("dev_creatures", kind=kind, dx=dx, dy=dy, still=still)["spawned"]

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
        self.sleep(100)

    def face(self, dx, dy):
        self.js(f"(() => {{ const p = ents.get('agent' + myId); p.fx = {dx}; p.fy = {dy}; }})()")
        self.sleep(100)          # let a frame redraw the hints

    # ---- keys
    def press(self, key, wait=300):
        self.page.keyboard.press(key)
        self.sleep(wait)

    def hold(self, keys, ms):
        for k in keys:
            self.page.keyboard.down(k)
        self.sleep(ms)
        for k in reversed(keys):
            self.page.keyboard.up(k)

    def start_recording(self):
        """Record our character's on-screen position every frame, until recording() is called."""
        self.js("""() => { window.__rec = []; const t0 = performance.now(); window.__recOn = true;
          function f(n) { const p = ents.get('agent' + myId); if (p) __rec.push([n - t0, p.x, p.y]);
            if (__recOn) requestAnimationFrame(f); } requestAnimationFrame(f); }""")

    def recording(self):
        return self.js("(() => { __recOn = false; return __rec; })()")

    def act(self, tool, **args):
        return self.js(f"(a) => act({json.dumps(tool)}, a)", args)

    def timed(self, fn):
        t0 = time.time()
        r = fn()
        return r, time.time() - t0
