---
name: sprite-maker
description: Make or change a character, race, robot, creature/boss, held tool, item icon or wearable sprite for Nexel Worlds the way past sessions did (ASCII/computed pixel art in Python, or frames derived at load in the web client from the cat sheet), checked by looking at real frames, and shown on the mockup page for the owner's numbered pick before it goes in-game. Use when making or changing a character, creature, item or wearable sprite, its animation, or how something is held.
---

# Sprite maker (Nexel Worlds)

The owner's dated verdicts are in `reference.md` beside this file. Owner memory with the full stories:
`~/.claude/projects/-Users-sdjerbi/memory/` `megastructure-sprites.md`, `megastructure-enemies.md`,
`megastructure-pixels.md`, `one-mockup-page.md`, `judge-motion-on-real-frames.md`, `voxel-rigour.md`.
**You can see images**: open every sheet and strip you make, enlarged, with the Read tool before showing anything.

## Hard rules
- **Original art only** (CLAUDE.md: "own art, names, rules. Don't recreate any existing game"). Base art is the licensed
  Sprout Lands pack (Cup Nooble). New pixels are drawn *in its style and palette*, never traced from another game.
- **A new LOOK goes on the mockup page first**, numbered, `0` = today, and is built only after the owner picks
  ("go with tin cat", "go with A. Low at the side"). Bug fixes that are not a look change can land directly.
  Being convinced by your own renders is not the owner's pick (2026-11-18: an unasked look cost a round to undo).
- **Whole pixels only.** Never scale pixel art by a non-integer, never blur, never rotate with smoothing
  (`Image.NEAREST` only). A smaller version is redrawn by whole pixels (loot.js `smallPx`: 11 px from 16), not scaled.
  Squash/stretch = rows left out or drawn twice, never resizing. An item's art px = the land's px.
- **Sprites stay flat 2D facing the camera** in the voxel world (owner, 2026-11-18). Block-like things (cube icons,
  block faces) use only the tileset's own paint and colours, no invented shading, nothing stretched.
- **Never draw over the character** (in a mockup or the game) and nothing see-through over the world's picture.
- **Every direction, every state.** Down, up, left, right (right = left mirrored for creatures); idle, walk, actions.
- Never run scripts against the owner's live server (:7777); use a copy server on a free port with temp saves.
  At most `-n 2` for browser tests, only the files you touched, one run at a time (the Mac hung on 2026-11-19).

## Where sprites come from (pick the path)
| What | Source | Made by | Lands in |
|---|---|---|---|
| Player cat, all frames | `web/assets/character.png` (pack: 8 cols x 48 px; rows idle 0, walk 4, run 8, hoe 12, axe 16, water 20; x4 dirs down/up/right/left) | the pack | as is |
| Extra player rows | derived from the cat sheet **at load** (`assets.js`), so tint, race and clothes inherit them | `tool_art.js` (pickaxe/sword/spear 24-35, from the axe frames), `jump_art.js` (36), `aim_art.js` (40) | `ANIM` in `sprites.js`; sheet now 384x2112 |
| Races, robots | cat frames with the head rebuilt per frame | `races.js` (`raceSheet(key, tint, bot)`, `robot()`) | client |
| Clothes / armor | painted per frame at skull/collar/feet found on the frame | `wear.js` (look), `wear_items.js` (16 px bag icons, charm effects); slots/recipes in `src/nexel_worlds/wearables.py`; a test keeps both lists equal | client |
| Held items, attacks | drawn from the grip, at angles, whole px | `held.js`, `hold_art.js`, `swing_art.js` (own 8x4 sheet), `cube_icons.js` (blocks: 13/11/8 px) | client |
| Small objects/items (16x16) | ASCII rows + palette `P` in `tools/pixel_art.py` `GEN` | `tools/build_assets.py` -> `gen.png` | `web/assets/` |
| Pack-derived art | pack sheets | `tools/derived_art.py` (via build_assets) | `web/assets/` |
| Creatures, bosses | `design/enemies/roster/<key>.py` (ASCII grids or computed with `design/enemies/art.py` helpers) | `design/enemies/build.py` | `design/enemies/site/sheets/` + `web/assets/<key>.png` for `IN_GAME` |

Paths in `web/` mean `src/nexel_worlds/web/`.

## Pipeline: a creature or boss
1. Read the game's own sheets first (cow, chicken, character) and `WILD`/`ANIMALS` in `web/js/world_decor.js`:
   walks 8 frames ~90 ms (player 85), idle a 1 px breath at ~220-260 ms, shadow a soft purple oval (80,64,134, low
   alpha) three rows deep, a distinct body plan and silhouette per creature, side views in profile like the cow.
2. Write `design/enemies/roster/<key>.py` exporting `ENEMY = dict(key, name, pal, cell=(w,h), ms={anim: ms or [per
   frame]}, dirs={"down"|"up"|"left": {anim: [frames]}}, ...)`. One char = one px; build frames from parts
   (`canvas`, `ell`, `dot`, `part`, `ground`, `leg`, `shift`, `edit`, `mirror`) or from a phase, never redraw each frame.
3. Preview while drawing: `uv run --with pillow python design/enemies/build.py <key> <scratchpad>/<key>.png` (6x, on
   grass), then open it. Writes nothing in the repo.
4. Showcase: add the key to `ORDER` in build.py, run `uv run --with pillow python design/enemies/build.py`
   (writes `site/sheets/`, `site/enemies.json`, copies reference sheets), serve `design/enemies/site/` (it was
   http://127.0.0.1:8098/) and put the pick on the mockup page.
5. In game (after the pick): add to `IN_GAME` (build.py writes `web/assets/<key>.png`), a `WILD` row in
   `world_decor.js` (`cw, ch`, `[col, frames, ms]` per anim), sim in `src/nexel_worlds/sim/wild.py`. Owner rule:
   new creatures do not spawn naturally until the owner says so; meeting one must be rare.

## Pipeline: a player sprite change (pose, race, robot, held tool, clothes)
1. **Record today first** on a copy server: real frames from the browser (CDP `Page.startScreencast` or Playwright
   shots), desk 1440x900 and phone 390x844 DPR 3, all four facings, stand / walk / jump / aim / work / attack.
2. Dump the sheets the code makes to PNG with Playwright, the way `design/enemies/robots.py` does
   (`raceSheet(k, tint, bot).toDataURL()` on a server of its own), and view enlarged contact sheets.
3. Make a new set of rows from existing frames by moving whole rows/columns and adding parts in the sheet's own
   colours (pattern: `jump_art.js`, `aim_art.js`), hooked in `assets.js` so tint/race/clothes inherit it; name the rows
   in `ANIM`. Measure a head or skull on the **body only** (the connected piece wearing the collar), never on tool px.
4. Put 2-5 unlike options on the mockup page, then build the picked one; update size checks in the tests
   (`test_e2e_races.py`, `test_e2e_wear.py`, `test_e2e_jump.py`) if the sheet grows.

## Pipeline: an item / object icon
16x16 ASCII in `tools/pixel_art.py` `GEN` with palette `P` (reuse its keys; the pack's own tool icons use `1`-`8`:
sticker edge, four greys, three handle browns). Rebuild: `python tools/build_assets.py <folder with the two zips>` or
`python tools/install_assets.py <zips>`. Icons on the ground and in HUD slots are made smaller by whole px (11 px), with
no white sticker edge. Blocks are cubes (`cube_icons.js`), not flat textures.

## Mockup page (the owner decides here)
- One page, updated in place: repo `sofianedjerbi/nexel-worlds-mockups`, https://sofianedjerbi.github.io/nexel-worlds-mockups/.
  Local working copy used last: `~/.claude/jobs/fa29ccbd/tmp/mockups/` (index.html, a folder per row, `.pair` rows of
  BEFORE/AFTER). Clone it if missing, add a row at the top, commit, `git push` to `main`, check Pages built:
  `gh api repos/sofianedjerbi/nexel-worlds-mockups/pages/builds/latest --jq .status`.
- Options numbered (or A/B/C), `0`/today first, real pictures of the game at 1:1 or whole-px enlarged, crops so the
  difference is obvious ("in mockup i dont see any difference between A,B,C"; "put the comparison together in
  evidence"). Say which one you recommend and why, in a line each. Write the pick at the top once built.
- Robots/races/clothes/enemies showcases also live in `design/enemies/site/*.html`.

## Check / QA before reporting
- Open every sheet: all 4 facings x every anim x every race (cat, bunny, bear, frog, duck), dressed and bare, robot.
  Flag frames with more connected pieces than the cat's frame (heads or hats popping off).
- Judge motion only on recorded real frames, wrapped into rows at full size, before and after.
- Tests (from the repo root): `PYTHONPATH=src .venv/bin/python -m pytest -m e2e -n 1 tests/e2e/test_e2e_races.py`
  and the ones you touched: `test_e2e_wear.py test_e2e_hand.py test_e2e_aim.py test_e2e_jump.py test_e2e_pixels.py
  test_e2e_wild.py test_e2e_boss.py`, unit `tests/test_races.py tests/test_wear.py`.
- Scene look check if the change shows in the world: `PYTHONPATH=src .venv/bin/python tools/lookcheck.py --only <scenes>`.
- Web files are served live (reload); server Python needs a restart only the owner asks for.

## Pitfalls seen before
- Heads/hats popping off on tool frames: the head was measured on tool px (fixed 2026-11-13).
- Bunny side-view ear pink must face forward; ear artefacts next to the cat's own ear animation.
- Tool drawn as the axe's chop: a sword attack looked "like breaking a bloc" -> `swing_art.js`.
- Held tools floating: the cat has no arms; the hand is a 4x4 ring and six code paths place it differently. A
  proposed single grip rule (ring always touching the body outline at one paw point per facing) awaited the owner's
  go on 2026-11-24: check before building it.
- A sheet loaded from cache before its script: define `ToolArt` etc. before `assets.js` in the page.
- `design/enemies/site/web` is a symlink to the old `src/megastructure/web` and is broken since the rename: pages
  that load `web/js/...` (index, races, robots) need it pointed at `src/nexel_worlds/web` (do it only if asked).
- Checking only hand-placed poses or sheets and never the real game ("i still cant see the sword look").
