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
  clock from one that fails)."""

import json
import os

import clock_sound

PACE = max(1.0, float(os.environ.get("E2E_PACE", "4")))
AHEAD = os.environ.get("E2E_AHEAD", "1") != "0"     # the next test's page loads while this one plays (pages.py)
now = 1.0           # the pace of the test that is running (conftest.py: the `pace` fixture)
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


# The day at the machine's pace on a page that plays (game.py join): the hour the page hears moves on from the last
# jump of it (dev_time) a K-th as fast as the paced world says, which is as fast as it moves at the game's own pace.
# What takes the machine's time (land made again between two pictures) took K times as much of the day: at dawn and
# with the sun low, two pictures a moment apart differed by the light (README.md rule 2), four times as often.
DAY = """(() => { const K = window.__pace; if (!K || window.__day) return 1; window.__day = 1; const real = onTick; let base = null, last = null;
  onTick = (d) => { const p = d.phase; if (base === null || Math.abs((((p - last) % 1) + 1.5) % 1 - .5) > .002) base = p;
    last = p; const on = (((p - base) % 1) + 1.5) % 1 - .5; d.phase = (((base + on / K) % 1) + 1) % 1; real(d); }; return 1; })()"""


def real(ms: float) -> float:
    """ms of the game's time -> of the machine's."""
    return ms if now == 1 else max(ms / now, min(ms, SHORT))


def held(page, ms: float):
    """Exactly `ms` of the game's time on this page (a key held): no floor."""
    getattr(page, "nap", page.wait_for_timeout)(ms / now if hasattr(page, "nap") else ms)


def paced(page, pace=None):
    """A page whose clocks run at the pace of the test that made it (or at `pace`: the next test's, pages.py)."""
    pace = pace or now
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


def set_world(url: str, pace: float):
    """The world at `url` (http://host:port) makes `pace` times its ticks from now on."""
    from websockets.sync.client import connect
    with connect(url.replace("http", "ws", 1) + "/agent") as ws:
        for i, m in enumerate(({"op": "hello", "name": f"clock{os.getpid() % 100000}", "token": "clock", "persona": "clock"}, {"op": "dev_pace", "pace": pace})):
            ws.send(json.dumps({"id": i, **m}))
            r = json.loads(ws.recv(timeout=10))
            assert r.get("ok"), r
