"""The tests' clock: the game's time runs PACE times as fast, in the world and on every page, so a walk, a build, a
fight, a fade or a day that takes seconds takes a quarter of them. Nothing of the game is changed by it: the world
makes PACE times as many ticks a second (the dev tool dev_pace, devtools.py: only a server started with --dev has
it), and a page's clocks (performance.now, Date.now, timers, the frame's time) are multiplied before any of its code
runs. To the game it is a machine PACE times slower drawing the same game: fewer frames and a longer way to the
server for each second of its own.

- `page.wait_for_timeout(ms)`, `game.sleep(ms)`: ms of the game's time.
- A test that measures the machine's own time (what a frame costs, frames in a second), or that has a clock of its
  own that is not the page's (the sound card's, a second server, the game in the page with its worker):
  `@pytest.mark.realtime` (or `pytestmark`), and it runs as it always did, at 1.
- `E2E_PACE=1` in the environment: the whole run at the game's own pace (to tell a test that fails because of the
  clock from one that fails). `E2E_PACE` is the most: a machine whose frames are slow gets less (`fit`)."""

import json
import os

import clock_sound

PACE = max(1.0, float(os.environ.get("E2E_PACE", "4")))
# (a frame is 0.1 s of the game's time at the most: what moves in a longer one is cut there (render.js update), as on a
# machine that cannot keep up. On the fast clock a frame of the machine's is PACE times as long to the game: Chrome
# drawing on the CPU (the runners, ci.yml) takes 70 to 100 ms a frame, 0.3 to 0.4 s of the game's at 4, and the walk went
# at a third of its pace, every jump short. The pace is fitted to the machine (`fit`, conftest.py `machine`): a frame
# under FRAME_BUDGET ms of the game's time, PACE at the most, 1 at the least)
FRAME_BUDGET = 70
AHEAD = os.environ.get("E2E_AHEAD", "1") != "0"     # the next test's page loads while this one plays (pages.py)
now = 1.0           # the pace of the test that is running (conftest.py: the `pace` fixture)
# LOCKSTEP (#276): every test is stepped (STEP) and its world ticks when its page asks (server.py dev_step), unless it
# is `realtime`: it measures the machine's own time, or has a clock that is not the page's. E2E_LOCKSTEP=0: only the
# tests marked `stepped` are, their world on its own clock, and the others run on the fast clock (PACE)
LOCKSTEP = os.environ.get("E2E_LOCKSTEP", "1") != "0"
step = False        # the test that is running is `stepped`: its pages' time goes 1/60 s a frame, whatever the machine (STEP)
seed = coming_seed = 0   # the chances of the test that is running, and of the one after it (SEED; conftest.py: from their ids)
pages = 0           # the pages of the running test given their chances so far: each page its own sequence (SEED)
coming = None       # the pace of the test after it, if it plays on the `game` fixture's page; None: it does not, or there is none (conftest.py)

# (a sleep is never cut under SHORT ms of the machine's time, or its own length: what it waited for may be an answer
# from the server, which comes no sooner on a fast clock)
SHORT = 60

SHIM = """(() => { const K = %s; if (K === 1 || window.__pace) return; window.__pace = K;
  const P = performance, pn = P.now.bind(P), dn = Date.now.bind(Date), d0 = dn(), st = window.setTimeout, si = window.setInterval, raf = window.requestAnimationFrame;
  P.real = pn;
  P.now = () => pn() * K;
  Date.now = () => d0 + (dn() - d0) * K;
  window.setTimeout = (f, ms, ...a) => st(f, (ms || 0) / K, ...a);
  window.setInterval = (f, ms, ...a) => si(f, (ms || 0) / K, ...a);
  // (a frame's time: the page's clock when the frame began, the same for all that is called in it. Not its own time
  // multiplied: the browser moves that one by the rate its animations are given, below, and from when they were)
  let raw = -1, at = 0;
  window.requestAnimationFrame = (f) => raf((t) => { if (t !== raw) { raw = t; at = P.now(); } f(at); }); })()"""


# STEPPED (a test marked `stepped`, #47): the page's time is its own, 1/60 s a frame, whatever the machine. A test of how
# a move looks frame by frame (a jump's arc, the eye's easing, a sprint's speed) gets the same frames on a runner drawing
# a frame in 100 ms as on one drawing it in 16: what moves in a frame is never cut (render.js: 0.1 s at the most), a
# jump's top is never between two frames. performance.now() and Date.now() say T; a frame asked for (rAF) runs at the
# next of the machine's, with T a 60th of a second on; a timer runs when T reaches it. The world keeps the machine's
# clock: twice a second of T the page tells it how fast T goes (dev_pace), so it stays with the page (the walk's LEAD).
# A wait on the page (game.sleep, a key held) is ms of T. A busy wait on performance.now() would never end: such a test
# (a slow frame made on purpose: test_e2e_tap_slow.py) stays `realtime`.
STEP = """(() => { if (window.__step) return; window.__step = 1;
  const P = performance, pn = P.now.bind(P), dn = Date.now.bind(Date), raf = window.requestAnimationFrame.bind(window), st = window.setTimeout.bind(window);
  const F = 1000 / 60, T0 = pn(), D0 = dn(); let T = T0, n = 0, id = 0, w0 = T0, v0 = T0;
  P.real = pn; P.now = () => T; Date.now = () => Math.round(D0 + T - T0);
  const frames = new Map(), timers = new Map(), later = (e) => st(() => { throw e; });
  window.requestAnimationFrame = (f) => { frames.set(++id, f); return id; };
  window.cancelAnimationFrame = (k) => { frames.delete(k); };
  window.setTimeout = (f, ms, ...a) => { timers.set(++id, {at: T + (+ms || 0), f, a}); return id; };
  window.setInterval = (f, ms, ...a) => { const e = Math.max(1, +ms || 0); timers.set(++id, {at: T + e, f, a, every: e}); return id; };
  window.clearTimeout = window.clearInterval = (k) => { timers.delete(k); };
  // LOCKSTEP (#276): the page that drives the world (window.__lockstep, game.py join: the test's first) runs a frame only
  // once the world is at the tick of that frame's time (dev_step, server.py), its answer and the tick itself come: page
  // and world one time, however slow the machine. An answer not come in 2 s of the wall's time is asked again (to is
  // absolute: nothing made twice), and said every fifth time
  let drive = null;
  const ask = () => { const to = drive.asked; drive.sent = pn(); rpc("dev_step", {to}).then((r) => { if (drive && drive.asked === to && r && r.tick >= to) drive.ok = true; }); };
  window.__lockstep = (tick0, hz) => { drive = {tick0, hz, T0: T, asked: tick0, ok: true, sent: 0, tries: 0}; return 1; };
  // A world ahead of what was asked was sent on by a dev op (dev_time, dev_skip: a day is 12000 ticks): counted from
  // there, or the page would wait out the jump in frames, the world making nothing meanwhile
  const owed = (t) => { if (!drive) return false;
    if (typeof clock === "object" && clock.tick > drive.asked) Object.assign(drive, {tick0: clock.tick, T0: t, asked: clock.tick, ok: true});
    const want = drive.tick0 + Math.floor((t - drive.T0) * drive.hz / 1000);
    if (want > drive.asked) { drive.asked = want; drive.ok = false; drive.tries = 0; ask(); }
    if (drive.ok && typeof clock === "object" && clock.tick >= drive.asked) return false;
    if (pn() - drive.sent > 2000) { if (++drive.tries % 5 === 0) console.error(`lockstep: no tick ${drive.asked} from the world in ${drive.tries * 2} s (it is at ${clock && clock.tick})`); ask(); }
    return true; };
  const tick = () => { if (owed(T + F)) { raf(tick); return; } T += F; n++;
    for (const [k, t] of [...timers].sort((a, b) => a[1].at - b[1].at)) if (t.at <= T && timers.has(k)) {
      if (t.every) t.at += t.every; else timers.delete(k); try { if (typeof t.f === "function") t.f(...t.a); } catch (e) { later(e); } }
    const fs = [...frames.values()]; frames.clear(); for (const f of fs) try { f(T); } catch (e) { later(e); }
    if (n % 30 === 0 && !drive) { const r = (T - v0) / Math.max(1, pn() - w0); w0 = pn(); v0 = T;
      if (typeof rpc === "function") rpc("dev_pace", {pace: Math.max(.05, Math.min(1, r))}); }
    raf(tick); };
  raf(tick); })()"""


# SEEDED (#276): a page's Math.random is a sequence of its test's own (mulberry32 from the test's id), the same at every
# run whatever ran before: what the game draws by chance (a burst of dust, the splash's line, a sound's pick) as well
SEED = """(() => { if (window.__seed !== undefined) return; let a = window.__seed = %d >>> 0;
  Math.random = () => { a = (a + 0x6D2B79F5) >>> 0; let t = a; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; })()"""


def stepped_wait(page, ms: float):
    """ms of a stepped page's own time (STEP): until its T has gone on by ms (the machine's time it takes, as it comes)."""
    t = page.evaluate("performance.now()")
    page.wait_for_function("(t) => performance.now() >= t", arg=t + ms, timeout=max(30000, ms * 30))


# The day at the machine's pace on a page that plays (game.py join): the hour the page hears moves on from the last
# jump of it (dev_time) a K-th as fast as the paced world says, which is as fast as it moves at the game's own pace.
# What takes the machine's time (land made again between two pictures) took K times as much of the day: at dawn and
# with the sun low, two pictures a moment apart differed by the light (README.md rule 2), four times as often.
DAY = """(() => { const K = window.__pace; if (!K || window.__day) return 1; window.__day = 1; const real = onTick; let base = null, last = null;
  onTick = (d) => { const p = d.phase; if (base === null || Math.abs((((p - last) % 1) + 1.5) % 1 - .5) > .002) base = p;
    last = p; const on = (((p - base) % 1) + 1.5) % 1 - .5; d.phase = (((base + on / K) % 1) + 1) % 1; real(d); }; return 1; })()"""


def fit(frame_ms: float) -> float:
    """The pace for a machine whose frame of the game takes `frame_ms` of its time -> PACE, fitted."""
    global PACE
    PACE = max(1.0, min(PACE, round(FRAME_BUDGET / max(frame_ms, 1e-3), 1)))
    return PACE


def real(ms: float) -> float:
    """ms of the game's time -> of the machine's."""
    return ms if now == 1 else max(ms / now, min(ms, SHORT))


def held(page, ms: float):
    """Exactly `ms` of the game's time on this page (a key held): no floor."""
    getattr(page, "nap", page.wait_for_timeout)(ms / now if hasattr(page, "nap") else ms)


def paced(page, pace=None):
    """A page whose clocks run at the pace of the test that made it (or at `pace`: the next test's, pages.py)."""
    mine = pace is None                          # (this test's own page; a page asked for ahead is the next test's: pages.py)
    pace = pace or now
    global pages
    if mine:                                     # (each page of a test its own sequence: two pages drew the same ids and tokens)
        pages += 1
    page.add_init_script(SEED % (((seed if mine else coming_seed) + (pages - 1 if mine else 0) * 0x9E3779B9) & 0xFFFFFFFF))
    if step and mine and pace == 1:
        page.add_init_script(STEP)
        page.wait_for_timeout = lambda ms: stepped_wait(page, ms)
        page.nap = page.wait_for_timeout
        return page
    if pace != 1:
        page.add_init_script(SHIM % pace)
        page.add_init_script(clock_sound.SHIM % pace)
        try:                                     # (and what the style sheets move: a window sliding in, the zoom's glide, a fade)
            dev = page.context.new_cdp_session(page)
            dev.send("Animation.enable")
            dev.send("Animation.setPlaybackRate", {"playbackRate": pace})
        except Exception:  # noqa: BLE001, S110 - a browser without it: they take their own time, as a sleep's floor allows
            pass
        nap = page.wait_for_timeout
        page.wait_for_timeout = lambda ms: nap(real(ms))
        page.nap = nap
    return page


def drive(game):
    """The test's first page (game.py join) drives its world's ticks, in a stepped test (LOCKSTEP; STEP: __lockstep)."""
    if step and LOCKSTEP:
        from nexel_worlds.sim import TICK_HZ
        r = game.rpc("dev_lockstep", on=True)
        game.js(f"__lockstep({int(r['tick'])}, {TICK_HZ})")


def tell_world(url: str, *ops: dict):
    """The world at `url` (http://host:port) told the dev ops `ops`, in order, by a player of the tests' own."""
    from websockets.sync.client import connect
    with connect(url.replace("http", "ws", 1) + "/agent") as ws:
        for i, m in enumerate(({"op": "hello", "name": f"clock{os.getpid() % 100000}", "token": "clock", "persona": "clock"}, *ops)):
            ws.send(json.dumps({"id": i, **m}))
            r = json.loads(ws.recv(timeout=10))
            assert r.get("ok"), r


def let_go(url: str):
    """The world at `url` back on the wall's clock, whoever drove its ticks (LOCKSTEP)."""
    tell_world(url, {"op": "dev_lockstep", "on": False, "force": True})


def set_world(url: str, pace: float):
    """The world at `url` makes `pace` times its ticks from now on."""
    tell_world(url, {"op": "dev_pace", "pace": pace})
