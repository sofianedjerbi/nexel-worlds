"""The wait (index.html #boot): the first thing on the screen and nothing else, the cat running in place over a pixel
bar, moving before any script has come; its bar never goes back; gone once the island is painted. The owner: "the loading
screen looks bad, can't you just show the loading and nothing else first so it doesn't look stuck?"; "improve its
loading speed": the sheets the title never shows (assets.js LATE) are not waited for."""

HOLD = """(() => { const add = DOMTokenList.prototype.add; window.__hold = true;
  DOMTokenList.prototype.add = function (...a) { if (window.__hold && a.includes('scene')) { window.__held = true; return; } return add.apply(this, a); };
  window.__p = 0; Object.defineProperty(window, 'ASSETS_OF', {get: () => 100, set: () => {}}); Object.defineProperty(window, 'ASSETS_IN', {get: () => window.__p * 100, set: () => {}}); })();"""
# the bar's fill in art px, and the art px in screen px
BAR = "(() => { const b = parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--bootpx')); return [document.getElementById('bootfill').getBoundingClientRect().width / b, b * devicePixelRatio]; })()"
RUNNING = "document.getAnimations().filter((a) => a.playState === 'running' && a.effect.target.closest('#boot')).length"


def test_the_wait_runs_before_any_script_and_its_bar_never_goes_back(browser, server):
    page = browser.new_page(viewport={"width": 390, "height": 844}, device_scale_factor=3, is_mobile=True, has_touch=True)
    held = []
    page.route("**/js/*.js*", lambda r: held.append(r))           # (no script of the game's has come)
    page.goto(server, wait_until="commit")
    page.wait_for_function(f"!!document.getElementById('boot') && {RUNNING} === 2", timeout=10000)      # the cat runs, the meadow under it goes by
    js = page.evaluate
    assert js("[!!document.getElementById('poster'), !!document.getElementById('loading')]") == [False, False]   # the still picture and the old strip: gone
    assert js("[[2, 2], [innerWidth - 3, innerHeight - 3], [innerWidth / 2, innerHeight / 2]].every(([x, y]) => document.elementFromPoint(x, y).closest('#boot'))")   # it alone is seen
    n, px = js(BAR)
    assert n == 0 and px == round(px) and px >= 6, (n, px)        # a whole number of screen px an art px, big enough on a phone
    page.close()
    page = browser.new_page(viewport={"width": 390, "height": 844}, device_scale_factor=3, is_mobile=True, has_touch=True)
    page.add_init_script(HOLD)
    page.goto(server)
    js = page.evaluate
    page.wait_for_function("typeof titleDraw === 'function'", timeout=20000)
    js("window.__p = .5")
    page.wait_for_function(f"{BAR}[0] >= 25", timeout=5000)
    n = js(BAR)[0]
    assert n == round(n)                                           # (whole art px)
    js("window.__p = .1")                                          # what is told goes back: the bar does not
    page.wait_for_timeout(300)
    assert js(BAR)[0] >= n
    js("window.__hold = false; document.body.classList.add('scene')")
    page.wait_for_function("!document.getElementById('boot')", timeout=5000)    # the island painted: the wait is gone
    page.close()


def test_the_title_does_not_wait_for_the_sheets_it_never_shows(browser, server):
    page = browser.new_page(viewport={"width": 1440, "height": 900})
    held = []
    page.route("**/assets/emoji.png*", lambda r: held.append(r))  # (the emotes' 119 KB: not come)
    page.goto(server, wait_until="commit")                        # (the page's load event waits for every picture asked for)
    page.wait_for_function("document.body.classList.contains('scene') && !document.getElementById('boot')", timeout=30000)
    assert held and page.evaluate("!IMG.emoji.naturalWidth")
    for r in held:
        r.continue_()
    page.wait_for_function("IMG.emoji.naturalWidth > 0", timeout=10000)   # and it comes, for the world
    page.close()
