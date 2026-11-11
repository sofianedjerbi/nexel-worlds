"""A player in Chrome, for end-to-end tests: join, look at the screen and the server, press keys, use dev tools."""

import json
import time


class Game:
    def __init__(self, page, url):
        self.page, self.url, self.errors = page, url, []
        page.on("pageerror", lambda e: self.errors.append(str(e)))

    # ---- session
    def join(self, name, zoom=4):
        self.page.goto(f"{self.url}/?zoom={zoom}")
        self.page.wait_for_function("typeof ready !== 'undefined'")
        self.page.click("#name")
        self.page.keyboard.type(name)
        self.page.keyboard.press("Enter")
        self.name = name
        self.wait("meObs && myPos()", 8000)
        self.rpc("dev_time", phase=.3)

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

    def stamp(self, dx, dy, rows, levels=None):
        """Paint tiles relative to us; `levels`: optional rows of heights (digits)."""
        x, y = self.pos()
        self.rpc("dev_stamp", x=x + dx, y=y + dy, rows=rows, levels=levels or [])
        self.sleep(400)

    def clear_area(self, r=10):
        """Flat meadow around us, no animals near (they wander into tests)."""
        self.rpc("dev_creatures", clear=40)
        self.stamp(-r, -r, ["." * (2 * r + 1)] * (2 * r + 1))
        self.sleep(300)

    def spawn(self, kind, dx, dy, still=0):
        return self.rpc("dev_creatures", kind=kind, dx=dx, dy=dy, still=still)["spawned"]

    def give(self, **items):
        self.rpc("dev_give", items=items)
        self.sleep(800)          # the client refreshes its observation every 0.7 s

    def inv(self, item):
        return self.server()["inventory"].get(item, 0)

    # ---- the screen
    def actions(self):
        return self.js("$('actions').innerText").replace("\n", " | ")

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
