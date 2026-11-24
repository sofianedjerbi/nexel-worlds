# The browser tests

Real Chrome against a fresh server on a temporary world (`conftest.py`), one new player a test, standing on a cleared
meadow (`game` fixture; `game.py` is what a test can do, `waits.py` how it waits), the game's time running four times
as fast (`clock.py`), every page shut when its test is over (`pages.py`).

## Running

    PYTHONPATH=src .venv/bin/python -m pytest -m e2e -n 2 tests/e2e/test_e2e_water.py        # one file
    PYTHONPATH=src .venv/bin/python -m pytest -m e2e -n 2 tests/e2e/test_e2e_water.py -k bed  # some of its tests
    PYTHONPATH=src .venv/bin/python -m pytest -m "e2e and quick" -n 2 tests/e2e               # one test an area, about a minute
    PYTHONPATH=src .venv/bin/python -m pytest -m e2e -n 3 tests/e2e                           # all of it: the owner's run

- `-m e2e` is needed (the default run leaves these out). `PYTHONPATH=src` in a worktree, or the venv plays the live game's code.
- An agent runs **the files it touched and `quick`**, at `-n 2`, five files at the most, one run at a time; never the
  whole folder (several agents doing that froze the machine).
- The sounds are built files (`tools/build_audio.py` -> `src/nexel_worlds/web/audio/`, not in git). A new worktree
  has none: the tests that need them skip (they waited a minute for them) until they are built; the demo's test
  builds them the first time it runs.
- **What to run for a change**: `tools/affected.py` prints the e2e (and unit) test files your changes ask for (git's
  changes since main and the working tree's, or the files given), from the JS globals and file names each test names;
  `--why` says why each is there, `--run` runs them at `-n 3`, then the quick set. A helper here (game.py, waits.py)
  asks for the quick set only.
- **How the HD look looks**: `tools/lookcheck.py` shoots 16 fixed scenes (desk and phone) on its own server copy, the
  page's clock frozen (the same code gives the same px), in about 70 s; writes `.lookcheck/last/sheet.png` (a changed
  scene in a red frame with its %), `diff_*.png`, and a one-line table against `.lookcheck/accepted/` (gitignored).
  `--only meadow,cave` for some, `--accept` to make the shots the accepted ones.
- `--durations=20` says where the time went. A test that needed its second try is listed at the end
  ("tried a second time", with what the first try said): one that is often there is not sound.

## The tests' clock

The game's time runs `PACE` (4) times as fast in a test: the world makes forty ticks a second (the dev tool
`dev_pace`), and each page's clocks, timers, frame times, style-sheet animations and sound card are multiplied before
any of its code runs (`clock.py`, `clock_sound.py`). Nothing of the game knows: a walk is still five tiles a second
of its own time, a piece of music still thirty-five seconds of its own. To the game it is a machine four times slower:
fifteen frames to one of its seconds, four times as long to the server and back.

- `game.sleep(ms)`, `page.wait_for_timeout(ms)`, `game.hold(keys, ms)`: ms of the **game's** time. (A sleep is at
  least 60 ms of the machine's, and lasts until the land is made: what a sleep also gave was time to the machine.)
- **`@pytest.mark.realtime`** (or `pytestmark`): the test runs at the game's own pace, as all did. For a test that
  measures the machine (what a frame costs, frames a second, a lag in ms), that looks at every frame of a movement
  (no stop, no jump: at 15 frames a second of the game's time there are both), that taps a key and counts on the
  answer coming within a tick, or that has a clock that is not the page's (a second server, the demo's worker).
  A test that fails on the fast clock and passes with `E2E_PACE=1` is one of these: mark it, do not stretch it.
- `E2E_PACE=1 pytest ...`: the whole run as it was. `E2E_AHEAD=0`: no page loaded ahead (below).
- The day goes at the machine's pace on a page that plays (`clock.py` `DAY`): the hour moves on from the last
  `dev_time` as fast as it does at the game's own pace. Land made again between two pictures takes the machine's
  time, and took four times as much of the day: the light of dawn and of a low sun moved between them.
- What takes the machine's time takes it still (land made, a picture read): the land's share of a frame is the
  machine's (`render.js` `LAND_MS` reads the tests' pace: the one line of the game that knows).

## Pages

- The `browser` fixture counts the pages and contexts a test opens and shuts what it left open (`pages.py`). A page
  left open was a player left awake where the next players woke: drawn on their screens, counted with who was there.
- The next test's page loads while this one plays, and waits at the first screen (`browser.ahead`, `take`): a new page
  as ever, but not new-born. A test about the first screen itself opens its own (`browser.new_page`).

## Groups (five files a run)

By area, for "the files I touched and their neighbours":

| area | files |
| --- | --- |
| land, picture | land, relief, pixels, edits, curve, tall, water, models, picture_options |
| hidden, light | stacked, daylight |
| HD look | hd, hd_land, hd_sun, hd_sky, hd_phone, hd_window, hd_stair, hd_trench, hd_behind, hd_paints |
| building | build, buildghost, building, floors, digging, climb, edges, wayout, wayshow, target |
| moving, living | moving, fall, swim, living, gathering, wild, boss, flee, wear, races, monkey |
| screens | ui, menu, bag, bookkeys, craft_search, help, prompts, complete, ask, bubbles, social, zoom, frame, f3 |
| first screen, phone, sound | title, title_scene, account, demo, bundle, phone, phone_taps, touch, sound, world |

## Rules

1. **Never sleep, then assert.** A sleep is too short on a busy machine and too long on an idle one. Wait for the
   state, then read:
   - land stamped, a setting that changes the picture, a teleport: `game.rest()` (all the land on the screen come
     and made, you and the eye arrived, nothing fading, a tick heard, three frames since). `game.stamp()` returns when the
     tiles are on the page; `rest()` is when they are drawn as blocks, lit, and the water made.
   - the hour: `game.hour(phase)` (on the page, and drawn by it). Not `rpc("dev_time")` and a sleep.
   - a teleport: `game.rpc("dev_teleport", ...); game.arrive()`.
   - a creature: `game.spawn()` returns when the page has it.
   - anything else the server or the page does: `game.wait("<what you are about to assert>")`, or `game.settle(...)`
     when the assert that follows should say what is wrong in its own words.
   - what is set on the page and read from the next picture: `game.frames(2)`.
   - `game.sleep(ms)` is for time that has to pass *in the game*: a walk, a swing, a fade whose middle is the test
     (ms of the game's time: the tests' clock, above).
2. **Two pictures to compare are one frame drawn twice** (`twice` in `test_e2e_sunland.py`, `HASHES` in
   `test_e2e_depth.py`), not two frames a moment apart: the hour moves on (at dawn the whole picture grows lighter
   by the second), fires flicker, clouds and the low sun's shafts drift. Where they have to be two frames (a setting
   changed and the land made again between them): `game.hour(phase, still=True)`, and the page's hour stays that one
   until the next `hour()`.
3. **What a test does not measure is turned off or kept out of the way**: `clouds`, `rays`, `shimmer` to 0; and what the
   world puts down by a tile's own place (a leaf on shore water, one tile in eleven) is looked for before the spot
   is chosen: a new player wakes somewhere else every run.
4. **A test that fails "under load": print the state at the failing wait first**, then fix the wait. The harness
   waits; a longer sleep is not a fix.
5. `game.press(key)` returns when what the key did is done (at most the `wait` given, 0.3 s if none); a wait over
   0.4 s is slept whole.
6. A margin on a time (`< 5 ms a step`) measures the machine as much as the code: take the best of a few rounds.
7. **One px of ground is not the ground.** The meadow has darker patches a tile wide and tufts, stone and a dug floor
   have specks, water has a lily pad on some tiles: all by the tile's own place, and a player wakes somewhere else
   every run. Read the colour most px of a piece have (`MOST` in `test_e2e_water.py`, `test_e2e_hd_trench.py`), or
   the middle one of a few (`spot` in `test_e2e_hd_stair.py`); for "it is meadow", ask for green, not for the px of
   another tile. A test that fails one run in six with a colour 10 % off is this.
8. **`dev_col` lays out columns and leaves what stands**: the world's trees, a pond's water. "Whole land round you"
   is `stamp` with `.` (a meadow, nothing on it). A tree five tiles south of a deep room hid the player in it; a
   pond's tiles in the room were not the room.
9. **Two reads that must agree are one `js` call** (a count, and the line that says it): the game goes on between two.
10. **A script or a picture is held back by a gate, not by ms** (`page.route` keeps the request, the test lets it go
    when it has looked): 700 ms are 175 on the tests' clock.
11. `game.hold(keys, ms)` of a tap (150 ms and less) lasts until a frame was drawn with the key down: the walk sets
    out in a frame (`walk.js`), and a tap let go before one is a stop where you stand.
12. `rest()` knows the land of the flat screen's rectangle. The HD look on a big screen draws more (out to the
    horizon): wait for what is asserted (`HdLook.bare() === 0`).
