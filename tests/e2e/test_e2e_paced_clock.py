"""The paced clock (clock.py SHIM): a page's time runs `pace` times as fast, its timers that much shorter. A timer of
N ms of the page's time fires once the page's clocks have gone N ms on, never before: a test reading Date.now() or
performance.now() against a game's timer reads at least its N (#367: at a pace of 1.1 a note's 2500 ms were a timer
of 2272.7 real ms, cut to 2272 by the browser, read as gone 2499.2 ms after it showed)."""

import pytest

import clock

pytestmark = pytest.mark.e2e

# timers of these ms of the page's time, set one after another (each from the last's turn: each begun at another
# fraction of the machine's ms, where a short read hides), each read when it fires on both of the page's clocks: ->
# [[N, Date.now() gone on, performance.now() gone on]...] of those read short, and whether a cleared one fired
TIMERS = """(Ns) => new Promise((ok) => { const short = [], P = performance; let left = Ns.length, cleared = false;
  const gone = setTimeout(() => { cleared = true; }, 50); clearTimeout(gone);
  const arm = (i) => { if (i >= Ns.length) return; const N = Ns[i], d0 = Date.now(), p0 = P.now();
    setTimeout(() => { const d = Date.now() - d0, p = P.now() - p0; if (d < N || p < N) short.push([N, d, p]); if (!--left) setTimeout(() => ok([short, cleared]), 120); }, N);
    setTimeout(() => arm(i + 1), 0); };
  arm(0); })"""


@pytest.mark.realtime   # (the pace is the test's own: the shim alone, at paces where N / pace is no whole number of ms)
@pytest.mark.parametrize("pace", [1.1, 1.3, 1.7])
def test_a_timer_of_n_ms_fires_once_the_page_s_clocks_have_gone_n_ms_on(browser, pace):
    page = browser.new_page()
    try:
        page.add_init_script(clock.SHIM % pace)
        page.goto("data:text/html,<p>paced</p>")
        Ns = [2500, 1400, 1000, 777, 500, 333, 250, 100, 50, 17] * 30
        short, cleared = page.evaluate(TIMERS, Ns)
        assert not short, str(short)                    # none read short, on either clock
        assert not cleared                              # a timer cleared never fires
    finally:
        page.close()
