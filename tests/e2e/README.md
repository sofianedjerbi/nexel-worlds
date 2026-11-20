# The browser tests

Real Chrome against a fresh server on a temporary world (`conftest.py`), one new player a test, standing on a cleared
meadow (`game` fixture; `game.py` is what a test can do).

## Running

    PYTHONPATH=src .venv/bin/python -m pytest -m e2e -n 2 tests/e2e/test_e2e_water.py        # one file
    PYTHONPATH=src .venv/bin/python -m pytest -m e2e -n 2 tests/e2e/test_e2e_water.py -k bed  # some of its tests
    PYTHONPATH=src .venv/bin/python -m pytest -m "e2e and quick" -n 2 tests/e2e               # one test an area, about a minute
    PYTHONPATH=src .venv/bin/python -m pytest -m e2e -n 3 tests/e2e                           # all of it: the owner's run

- `-m e2e` is needed (the default run leaves these out). `PYTHONPATH=src` in a worktree, or the venv plays the live game's code.
- An agent runs **the files it touched and `quick`**, at `-n 2`, five files at the most, one run at a time; never the
  whole folder (several agents doing that froze the machine).
- The sounds are built files (`tools/build_audio.py` -> `src/megastructure/web/audio/`, not in git). A worktree has
  none: the sound tests skip, the two that need them say so. Link the main checkout's folder to run them.
- `--durations=20` says where the time went. A test that needed its second try is listed at the end
  ("tried a second time", with what the first try said): one that is often there is not sound.

## Groups (five files a run)

By area, for "the files I touched and their neighbours":

| area | files |
| --- | --- |
| land, picture | blocks, land, relief, pixels, edits, curve, roll, tall, section |
| light | depth, sunland, shaders, daylight, narrow, water |
| hidden | xray, holes, underground, caves, behind, views, stacked |
| HD look | hd, hd_land, hd_sun, hd_phone |
| building | build, building, floors, place, digging, climb, mark, edges |
| moving, living | moving, fall, swim, living, gathering, wild, boss, flee, wear, races, monkey |
| screens | ui, menu, bag, bookkeys, craft_search, help, prompts, complete, ask, bubbles, social, zoom, frame, models |
| first screen, phone, sound | title, title_scene, account, demo, phone, phone_taps, touch, sound, world |

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
   - `game.sleep(ms)` is for time that has to pass *in the game*: a walk, a swing, a fade whose middle is the test.
2. **Two pictures to compare are one frame drawn twice** (`twice` in `test_e2e_sunland.py`, `HASHES` in
   `test_e2e_depth.py`), not two frames a moment apart: the hour moves on (at dawn the whole picture grows lighter
   by the second), fires flicker, clouds and the low sun's shafts drift.
3. **What a test does not measure is turned off or kept out of the way**: `clouds`, `rays`, `shimmer` to 0; and what the
   world puts down by a tile's own place (a leaf on shore water, one tile in eleven) is looked for before the spot
   is chosen: a new player wakes somewhere else every run.
4. **A test that fails "under load": print the state at the failing wait first**, then fix the wait. The harness
   waits; a longer sleep is not a fix.
5. `game.press(key)` returns when what the key did is done (at most the `wait` given, 0.3 s if none); a wait over
   0.4 s is slept whole.
6. A margin on a time (`< 5 ms a step`) measures the machine as much as the code: take the best of a few rounds.
