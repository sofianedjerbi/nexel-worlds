"""The interface: the bar and the inventory by keys, crafting cards, zoom, help, debug, hints, and that actions make sounds."""

import pytest
from waits import QUIET


def test_hotbar_keys_and_tab_cycle_what_is_in_hand(game):
    game.give(wood=1, stone=1, fiber=1)
    order = game.js("slotOrder(meObs.self.inventory).slice(0, 10)")
    game.press("1", 100)
    assert game.js("selected") == order[0]
    game.press("1", 100)
    assert game.js("[handSlot, selected]") == [0, order[0]]                     # the one in hand again: it stays
    game.press("Tab", 100)
    assert game.js("selected") == order[1]
    game.press("0", 100)
    assert game.js("[handSlot, selected]") == [9, order[9]]


def test_the_bar_is_ten_slots_and_i_opens_the_inventory(game):
    """Ten slots (1-9 and 0), no bag or crafting button on the bar. I opens the inventory (tests/e2e/test_e2e_bag.py),
    C the crafting; B is no key."""
    kinds = ["wood", "stone", "fiber", "seed", "flower", "rope", "torch", "plank", "path", "dirt", "egg", "bread"]
    game.give(**{k: 1 for k in kinds})
    assert game.js("[...document.querySelectorAll('#hotbar .slot .k')].map((e) => e.textContent).join('')") == "1234567890"
    assert game.js("document.querySelectorAll('#hotbar .slot').length") == 10 and game.js("!$('craftbtn') && !document.querySelector('.bagslot')")
    game.press("0", 100)
    assert game.js("selected") == game.js("slots[9]") and game.js("selected")       # the tenth slot
    game.press("b", 200)
    assert game.js("$('bag').style.display") != "block"                              # (B is no longer a key)
    game.press("i", 300)
    assert game.js("$('bag').style.display") == "block"
    game.press("Escape", 200)
    assert game.js("$('bag').style.display") == "none"
    game.press("c", 300)
    assert game.js("$('craft').style.display") == "block"
    game.press("Escape", 200)
    game.press("3", 100)
    game.press("0", 100) if not game.js("slots[9]") else game.press("`", 100)
    assert not game.errors


KIND = "(k) => { document.querySelector(`.ctab[data-kind=${k}]`).click(); return craftTab; }"
LIST = "[...document.querySelectorAll('#recipes .rcard')].map((c) => c.dataset.name)"                 # the names on the page
LIT = "[...document.querySelectorAll('#recipes .rcard:not(.no)')].map((c) => c.dataset.name)"         # ...the ones you can make
NEEDS = "[...document.querySelectorAll('#craftdetail .cneed')].map((e) => [e.querySelector('span').textContent, e.querySelector('b').textContent, e.classList.contains('miss')])"
BUTTON = "document.querySelector('#craftdetail .cbtn')"


def test_the_recipe_you_are_on_says_what_it_takes_and_what_you_have(game):
    """The right page is the one recipe you are on: its name, a line about it, each thing it takes with what you have
    of it (in red what you lack), where it is made (in red while you are not there), and one button that says why not."""
    game.press("c", 400)
    assert game.js("$('craft').style.display") == "block" and game.js("craftTab") == "Basics"
    assert game.js(KIND, "Tools") == "Tools"
    for _ in range(3):                                                                 # (wood's axe and pickaxe, stone's axe: tools go by tier)
        game.press("ArrowDown", 150)
    assert game.js("craftFocus") == "pickaxe" and game.js("document.querySelector('#craftdetail .cname').textContent") == "Pickaxe"
    assert game.js("document.querySelector('#craftdetail .cblurb').textContent") == game.js("BLURB.pickaxe") != ""
    assert game.js(NEEDS) == [["Wood", "0/2", True], ["Stone", "0/3", True], ["Fiber", "0/1", True], ["Workbench", "far", True]]
    assert game.js(BUTTON + ".textContent") == "Missing materials" and "Missing materials" in game.js("document.querySelector('.rcard[data-name=pickaxe]').title")
    game.give(wood=2, stone=4, fiber=1)
    game.until(f"JSON.stringify({NEEDS}).startsWith('[[\"Wood\",\"2/2\",false]')")   # (the detail drawn again with what you have)
    assert game.js(NEEDS) == [["Wood", "2/2", False], ["Stone", "4/3", False], ["Fiber", "1/1", False], ["Workbench", "far", True]]
    assert game.js(BUTTON + ".textContent") == "Go to a workbench" and game.js("document.querySelector('.rcard[data-name=pickaxe]').classList.contains('no')")
    game.press("Enter", 300)                                                           # not yet: it says why, and makes nothing
    assert "within 2 tiles of a workbench" in game.toast() and game.inv("pickaxe") == 0
    game.press("Escape", 200)


def test_the_recipe_book_shows_five_names_of_one_kind_and_one_recipe(game):
    """Six kinds, a bookmark each; five names at a time, of the kind you are on (it was sixty pictures at once, then
    twelve cards); the switch keeps only what you can make; the button makes the one you are on."""
    game.give(wood=4)
    game.press("c", 400)
    assert game.js("[...document.querySelectorAll('.ctab')].map((e) => e.dataset.kind)") == ["Basics", "Tools", "Build", "Home", "Metal", "Wear"]
    assert game.js(LIST) == ["workbench", "campfire", "torch", "rope", "plank"] and game.js("craftFocus") == "workbench"
    assert game.js("$('craftmore').textContent") == "Basics · 1 of 2" and game.js("document.querySelectorAll('#craftdetail .chead').length") == 1
    assert "workbench" in game.js(LIT) and "campfire" not in game.js(LIT)
    game.js("$('craftonly').click()")                                                  # only what you can make
    assert game.js(LIST) == game.js(LIT) and "workbench" in game.js(LIST) and game.js("$('craftonly').classList.contains('on')")
    game.js("$('craftonly').click()")
    game.press("Tab", 200)                                                             # tools: you can't make them yet
    assert game.js("craftTab") == "Tools" and game.js("craftFocus") == "wood_axe" and game.js(LIT) == []
    assert game.js(BUTTON + ".classList.contains('off')")
    assert game.js(KIND, "Basics") == "Basics" and game.js("craftFocus") == "workbench"
    game.js(BUTTON + ".click()")
    game.until(f"({QUIET})()")                          # (made: the server has answered)
    assert game.inv("workbench") == 1
    game.press("Escape", 200)
    game.press("c", 300)                                                               # opened again: where you were
    assert game.js("craftTab") == "Basics"
    game.press("Escape", 200)


def test_the_recipe_book_is_driven_by_keys(game):
    """Up and down go through the names and turn the page at its ends; left and right, Q and E, Tab change kind; Home
    and End go to the first and the last of the kind; Enter makes the one you are on."""
    game.give(wood=4)
    game.press("c", 400)
    names = game.js("craftGroups()[0][2]")
    walked = [game.js("craftFocus")]
    for _ in names[1:]:
        game.press("ArrowDown", 80)
        walked.append(game.js("craftFocus"))
    assert walked == names and game.js("craftPage") == 1                               # every name of the kind, in order, over two pages
    game.press("ArrowDown", 80)
    assert game.js("craftFocus") == names[-1]                                          # (the last: it stays)
    game.press("Home", 150)
    assert game.js("craftFocus") == names[0] and game.js("craftPage") == 0
    game.press("End", 150)
    assert game.js("craftFocus") == names[-1]
    for _ in range(4):                                                                 # (nine names: four on the second page)
        game.press("ArrowUp", 80)
    assert game.js("craftFocus") == names[-5] and game.js("craftPage") == 0            # (back up over the page's edge)
    for key, kind in (("e", "Tools"), ("ArrowRight", "Build"), ("Tab", "Home"), ("q", "Build"), ("ArrowLeft", "Tools")):
        game.press(key, 150)
        assert game.js("craftTab") == kind, key
    game.press("q", 150)
    assert game.js("craftFocus") == "workbench"
    game.press("ArrowDown", 80)
    game.press("PageUp", 150)                                                          # (a page that does not turn: the first line again, and lit)
    assert game.js("craftFocus") == "workbench" == game.js("document.querySelector('#recipes .cur').dataset.name")
    assert game.js("document.querySelector('#craftdetail .cname').textContent") == "Workbench"
    game.press("Enter", 1200)
    assert game.inv("workbench") == 1
    game.press("Escape", 200)
    assert not game.errors


# Every recipe of every kind, one after the other: the places of the window and of its parts (in the book's px), and
# the recipes where something spills out of its place or is cut
BOOK = """() => { const q = parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--q')), seen = new Set(), bad = []; let n = 0;
  const at = (e) => { const r = e.getBoundingClientRect(); return [r.left, r.top, r.width, r.height].map((v) => Math.round(v / q * 10) / 10).join(); };
  const cut = (e) => e.scrollHeight > e.clientHeight + 1 || e.scrollWidth > e.clientWidth + 1;
  for (const [t] of craftGroups()) { craftTurn({tab: t});
    for (let p = 0, pages = craftView().pages; p < pages; p++) { craftTurn({page: p});
      for (const name of craftView().shown) { focusRecipe(name); n++;
        const d = $('craftdetail'), w = d.querySelector('.cneeds'), wr = w.getBoundingClientRect();
        seen.add([$('craft'), $('recipes'), d, w, d.querySelector('.chead'), d.querySelector('.cblurb'), d.querySelector('.cbtns')].map(at).join(' '));
        const kept = [...w.children].every((c) => { const r = c.getBoundingClientRect(); return r.width > 0 && r.top >= wr.top && r.bottom <= wr.bottom && r.left >= wr.left && r.right <= wr.right && !cut(c); });
        if (!kept || [d, w, d.querySelector('.cblurb'), d.querySelector('.cname')].some(cut)) bad.push(name); } } }
  return {n, sizes: [...seen], bad}; }"""


def test_the_recipe_book_is_one_size_whatever_it_shows(game):
    """The window and each part of its pages keep their place and their size, whatever the recipe (it grew by a line
    for the seven that take four things, and moved up). What a recipe takes has a place of four lines: more than four
    go two abreast, then three, without their names; more than twelve, what you lack comes first and the last place
    says how many more. Nothing spills and nothing is cut."""
    game.give(wood=9, stone=4)
    game.press("c", 400)
    plain = game.js(BOOK)
    assert plain["n"] == game.js("Object.keys(recipes).length") >= 80 and len(plain["sizes"]) == 1 and not plain["bad"], plain
    assert game.js("Math.max(...Object.values(recipes).map((r) => Object.keys(r.inputs).length + (r.station ? 1 : 0)))") == 4   # (a line each, today)
    game.js("""(() => { const all = ['wood', 'stone', ...Object.keys(recipes).filter((n) => n !== 'wood' && n !== 'stone')], take = (n) => Object.fromEntries(all.slice(0, n).map((k, i) => [k, i === 2 ? 120 : i % 3 + 1]));
      recipes.well.inputs = take(5); recipes.coop.inputs = take(10); recipes.clock.inputs = take(15); return 1; })()""")
    big = game.js(BOOK)
    assert big["sizes"] == plain["sizes"] and not big["bad"], big
    needs = "(() => { const w = document.querySelector('#craftdetail .cneeds'); return [w.className, w.children.length, getComputedStyle(w.querySelector('.cneed > span')).display, (w.lastChild.querySelector('b') || w.lastChild).textContent, [...w.querySelectorAll('.cneed:not(.more)')].map((c) => c.classList.contains('miss'))]; })()"
    game.js("(() => { craftTurn({tab: 'Home'}); craftTurn({page: 1}); focusRecipe('well'); })()")
    cls, n, name, _, _ = game.js(needs)
    assert cls == "well cneeds c2" and n == 6 and name == "none"                       # six: two abreast, a picture and a number each
    game.js("focusRecipe('coop')")
    cls, n, _, last, _ = game.js(needs)
    assert cls == "well cneeds c3" and n == 11 and last == "far"                       # eleven: three abreast
    game.js("(() => { craftTurn({page: 0}); focusRecipe('clock'); })()")
    cls, n, _, last, miss = game.js(needs)
    assert cls == "well cneeds c3" and n == 12 and last == "+5 more"                   # sixteen: eleven and "+5 more"...
    assert all(miss) and game.js("document.querySelector('#craftdetail .cneed.more').title").endswith("Wood 9/1, Stone 4/2")   # ...what you lack first (the wood and the stone, which you have, are its first two)
    game.js("$('craftonly').click()")                                                  # nothing to list, and no recipe on the right page
    assert game.js("document.querySelectorAll('#recipes .rcard').length") == 0
    assert game.js("(() => { const r = $('craft').getBoundingClientRect(), q = parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--q')); return [r.width / q, r.height / q]; })()") == [252, 155]
    game.press("Escape", 200)


def test_zoom_help_and_debug_keys(game):
    z0 = game.js("zoom")
    game.press("+", 300)                               # (a level glides into the next: zoom.js)
    assert game.js("zoom") == z0 + 1
    game.press("-", 300)
    assert game.js("zoom") == z0
    game.press("h", 200)
    assert game.js("$('help').style.display") == "block"
    game.press("h", 200)
    game.press("F3", 300)                              # the debug screen (f3.js), with the server's numbers
    game.wait("(() => { const e = document.getElementById('f3'); return e && e.style.display !== 'none' ? e.innerText : ''; })().includes('ms/tick')")
    game.press("F3", 100)
    assert not game.js("F3.on")


def test_hover_hints_follow_the_mouse(game):
    game.stamp(2, 0, ["M"])
    x, y = game.pos()
    sx, sy = game.js("([x, y]) => { if (HdLook.on) return HdLook.screenOf(x + .5, y + .5, topAt(x, y)); const S = TS(), [ox, oy] = screenOrigin(S); return [ox + x * S + S / 2, oy + y * S + S / 2]; }", [x + 2, y])   # (the rock's tile's middle as the look draws it: the HD eye is not the flat one's, and a level is a cube)
    game.page.mouse.move(sx - 3, sy)
    game.page.mouse.move(sx, sy)
    game.until("$('hover').innerText.includes('Mine rock')")
    assert "Mine rock" in game.js("$('hover').innerText")
    assert game.js("inputMode") == "mouse"
    game.press("d", 100)
    assert game.js("inputMode") == "keys"


def test_actions_make_their_sounds(game):
    game.js("window.__snd = []; const s0 = sfx; window.sfx = (n, x, y) => { __snd.push(n); s0(n, x, y); }")
    game.stamp(1, 0, ["f"])
    game.stamp(-1, 0, ["T"])
    game.face(1, 0)
    game.press("e", 600)
    game.face(-1, 0)
    game.give(axe=1)
    game.hold_item("axe")
    game.press("x", 0)
    game.wait(f"combAt({game.pos()[0] - 1}, {game.pos()[1]}) === 't'", 8000)
    game.until("['rustle', 'collect', 'chop', 'creak', 'fallthud', 'pick'].every((k) => __snd.includes(k))")   # (the fall's sounds come after the tile turns)
    heard = set(game.js("__snd"))
    assert {"rustle", "collect", "chop", "creak", "fallthud", "pick"} <= heard, heard     # (pick: the axe taken in hand; chop: the strike, struckOnce if no frame drew it, agent.js)


def test_coords_and_perf_are_typed_in_the_chat_line(game):
    """/coords and /perf are debugging aids, off until asked for (js/debug.js); any other /word is still an action.
    /coords and /perf open the debug screen (f3.js), as F3 does."""
    say = lambda line: (game.page.keyboard.press("Enter"), game.page.keyboard.type(line), game.page.keyboard.press("Enter"), game.until(f"({QUIET})()"))   # (said, and what it asked answered)
    text = "(() => { const e = document.getElementById('f3'); return e && e.style.display !== 'none' ? e.innerText : ''; })()"
    game.js("(() => { F3.set(false); return 1; })()")
    game.until(f"{text} === ''")
    x, y = game.pos()
    assert game.js(text) == ""
    say("/coords")
    game.wait(text + f".includes('XYZ {x}.00 / {y}.00 / 0')")
    assert game.js("localStorage.getItem('nexel-f3')") == "1"
    say("/coords")
    assert game.js(text) == ""
    say("/perf")                                               # what the frames cost
    game.wait(text + ".includes(' fps') && " + text + ".includes('ticks ')")
    seen = game.js(text)
    assert " fps" in seen and "script " in seen and "ticks " in seen and "world " in seen and "blocks" in seen, seen
    say("/perf")
    assert game.js(text) == ""
    game.stamp(0, -1, ["f"])
    say("/dig dir=N")                                          # (not one of ours: sent to the server; say waits for its answer)
    assert game.inv("flower") == 1 and not game.errors


def test_the_crafting_list_is_not_made_again_while_it_is_shut(game):
    """It was built again, every card of it, each time what is near you changed: every step you took."""
    made = "$('recipes').dataset.sig"
    before = game.js(made)
    game.give(wood=10)                                         # (enough for a workbench)
    game.press("d", 600)
    game.rest()                                                # (the walk done, the page settled: anything it would draw is drawn)
    assert game.js(made) == before and game.js("$('craft').style.display") != "block"
    game.press("c", 300)                                       # opened: it is up to date
    assert game.js(made) != before
    assert "workbench" in game.js(LIT)


# (stepped: the note's timer and Date.now() on one clock; paced at 1.1, 2500 ms were a timer fired at 2499.2, #367)
@pytest.mark.stepped
def test_what_the_game_says_shows_over_the_bar_not_in_the_chat_nor_at_the_top(game):
    """"'you're full' messages etc they could show up above the chat beautifully like item": while you play, a short
    word from the game shows a moment where the name of what you take in hand shows (red for a no, with its buzz), the
    newest in place of the last, never cut short by the older one's timer; it is not a line of the chat, and the sign at
    the top is not shown. The dressed welcome (a key in it, said to the chat) is still a line of the chat."""
    n = game.js("$('chatlog').children.length")
    game.js("(() => { window.__sfx = []; const o = sfx; sfx = function (k, ...r) { __sfx.push(k); return o(k, ...r); }; toast('You are full.'); return 1; })()")
    over = "[$('heldname').className, $('heldname').textContent]"
    assert game.js(over) == ["on note", "You are full."] and "buzz" not in game.js("__sfx")
    game.js("(() => { toast('Too far: get closer.', true); return 1; })()")              # the newest in its place, red, buzzing
    assert game.js(over) == ["on note bad", "Too far: get closer."] and "buzz" in game.js("__sfx")
    assert game.js("getComputedStyle($('heldname')).color") == "rgb(255, 176, 160)"     # (the game's warm red for a no, as the chat's)
    assert game.js("$('chatlog').children.length") == n                                  # not in the chat
    assert game.js("getComputedStyle($('toast')).display") == "none" and game.toast() == "Too far: get closer."
    b = game.js("(() => { const h = $('heldname').getBoundingClientRect(), s = $('hotbar').getBoundingClientRect(); return [h.bottom <= s.top + 1, Math.abs((h.left + h.right) / 2 - (s.left + s.right) / 2) < 2]; })()")
    assert b == [True, True], b                                                         # over the bar, in its middle
    game.give(dirt=1, bread=1)
    game.hold_item("dirt"); game.hold_item("bread")                                      # a newer event: an item's name in its place
    game.wait("$('heldname').textContent === label('bread') && $('heldname').className === 'on'")
    game.js("(() => { new MutationObserver((m, o) => { if (!$('heldname').classList.contains('on')) { window.__goneAt = Date.now(); o.disconnect(); } }).observe($('heldname'), {attributes: true}); toast('You are full.'); return 1; })()")   # (when it first goes, the page's time)
    t0 = game.js("+$('heldname').dataset.t")
    assert game.js(over)[1] == "You are full."
    game.frames(2)                                                                       # (two frames: still well within the first note, at any rhythm short of 1.2 s a frame)
    game.js("(() => { toast('You are full.'); return 1; })()")                          # the same again: shown again from the start
    t1 = game.js("+$('heldname').dataset.t")
    assert t1 > t0
    game.until("window.__goneAt")                                                         # then it goes, when its own time is up: not at the
    assert game.js("__goneAt") >= t1 + game.js("BAR_NOTE_MS")                             # name's end (1.4 s, its timer cut nothing) nor the first's (it began again)
    game.js("(() => { toast('What hides you: **Cut away** `V`'); return 1; })()")                 # a guide (a key in it) shows and goes:
    assert game.js("$('chatlog').children.length") == n and "Cut away" in game.toast()               # not kept in the chat (prompts.js)
    assert "Cut away" not in game.js("$('heldname').textContent")
    game.js("(() => { toast('In hand: **wood**\\nSecond line `M`', false, NOTE_MS, true); return 1; })()")   # dressed: bold, a new line, a key (the welcome)
    last = "$('chatlog').lastElementChild"
    assert game.js(last + ".className") == "note sys" and game.js("getComputedStyle($('chatlog').lastElementChild, '::before').width") == "6px"      # a line of the chat, its mark
    assert game.js(last + ".querySelector('b').textContent") == "wood" and game.js(last + ".querySelector('kbd').textContent") == "M" and game.js(last + ".querySelectorAll('br').length") == 1
    assert game.toast() == "In hand: wood Second line M"                                               # (plain where it is read as text)
    game.until("$('chatlog').lastElementChild.classList.contains('old')")
    assert game.js("$('chatlog').lastElementChild.classList.contains('old')")                         # it fades, and stays in the history
    game.js("(() => { act('say', {text: 'a **b** `c`'}); return 1; })()")                             # what a player says is never dressed
    game.wait("[...$('chatlog').children].some((d) => d.textContent.includes('a **b** `c`'))", 5000)
