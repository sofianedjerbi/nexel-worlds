"""The wait for the island (js/loading.js): a pixel scene over the still picture, the cat walking as far as the game has
come, gone once the island is painted. The owner: "the placeholder waiting screen unanimated looks bad"."""

HOLD = """(() => { const add = DOMTokenList.prototype.add; window.__hold = true;
  DOMTokenList.prototype.add = function (...a) { if (window.__hold && a.includes('scene')) { window.__held = true; return; } return add.apply(this, a); };
  window.__p = 0; Object.defineProperty(window, 'ASSETS_OF', {get: () => 100, set: () => {}}); Object.defineProperty(window, 'ASSETS_IN', {get: () => window.__p * 100, set: () => {}}); })();"""
# where the cat is: the column of the strip's middle rows with the most of its outline's purple
CAT = """(() => { const c = document.getElementById('loading'), d = c.getContext('2d').getImageData(0, 0, c.width, c.height).data; let best = -1, n = 0;
  for (let x = 0; x < c.width; x++) { let k = 0; for (let y = 4; y < c.height - 4; y++) { const i = (y * c.width + x) * 4; if (d[i + 2] > 110 && d[i] < 120 && d[i + 1] < 100) k++; } if (k > n) { n = k; best = x; } }
  return best; })()"""


def test_the_cat_walks_as_the_game_comes_then_the_island(browser, server):
    page = browser.new_page(viewport={"width": 390, "height": 844}, device_scale_factor=3, is_mobile=True, has_touch=True)
    page.add_init_script(HOLD)
    page.goto(server)
    page.wait_for_function("!!document.getElementById('loading') && typeof titleDraw === 'function'", timeout=20000)
    js = page.evaluate
    box, menu = js("document.getElementById('loading').getBoundingClientRect().toJSON()"), js("document.querySelector('#joinbox .menu').getBoundingClientRect().toJSON()")
    assert box["bottom"] <= menu["top"] and abs(box["left"] + box["width"] / 2 - (menu["left"] + menu["width"] / 2)) < 2       # above the window, on its middle
    assert box["width"] * 3 % 132 == 0 and js("getComputedStyle(document.getElementById('loading')).imageRendering") == "pixelated"   # a whole number of screen px an art px
    js("window.__p = .1")
    page.wait_for_function(f"{CAT} > 0", timeout=10000)
    near = js(CAT)
    js("window.__p = .9")
    page.wait_for_function(f"{CAT} > {near} + 60", timeout=10000)                 # it walked as far as what has come
    js("window.__hold = false; document.body.classList.add('scene')")
    page.wait_for_function("!document.getElementById('loading')", timeout=5000)    # the island painted: the wait is gone
    page.close()
