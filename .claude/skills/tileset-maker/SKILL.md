---
name: tileset-maker
description: Add or change a terrain tile, ground, block, ore or liquid in Nexel Worlds and how it looks as a 3D voxel block (tops, sides, x-ray, water), following the pipeline, art rules and owner taste of past sessions. Use when adding or changing a tile, block, ore, liquid or its paint/3D look, or when the owner says a texture, wall, side or water "looks bad".
---

# Tileset maker (Nexel Worlds)

Repo: `~/nexel/nexel-worlds` (package `nexel_worlds`). Dated owner quotes and past decisions: `reference.md` beside
this file. Saved feedback: `~/.claude/projects/-Users-sdjerbi/memory/` (voxel-rigour, abstractions-not-rules,
one-mockup-page, megastructure-voxel-land, -look-at-the-sheet, -one-painter, -pixels, -water, -underground-view).

## The look, in one paragraph
Since 2026-11-19 the land is full voxels. Every solid cell is a block drawn from the world's own columns of cells, in a
tilted "HD" camera over a curved world. Trees, creatures and players stay 2D cards that face the camera. Furniture
(bed, chest, table, well) and bridges are small box models. All art is the premium **Sprout Lands** pack (Cup Nooble):
16 px cells. A level is a cube (`H = 1`, as tall as a tile is wide, the player's height). A side gets 16 rows of paint
per level. Pixel art is laid in whole art px only: never scaled, never stretched, never blurred.

## Where a tile lives (one source per decision)
1. **Rules** in `src/nexel_worlds/tiles.py`: `GROUNDS` (`Ground`: walkable, liquid...) and `BLOCKS` (`Block`: solid,
   hardness, drops, tool). Block ids are stored in saved chunks, so **append new blocks at the end**. Each needs a
   unique `char`. `DEPTH` and `DEEPER` cover water depth, `FILLERS` what fills what, `PLACEABLE` item -> block.
2. **Rules to the client:** `rules.py` builds one table from `tiles.py`. Regenerate the client copy with
   `uv run python -m nexel_worlds.rules`, which writes `web/js/rules.js` (never edit it by hand: `tests/test_rules.py`).
   The client reads it in `web/js/vocab.js`. Never type a rule table into the client again.
3. **What the land is made of** (earth or stone) comes from the world generator only. Stone depth is
   `chunks.py stone_at` and `stone.py made_of`. A dig gives `landblocks.py` (`dirt` or `stone_block`; placed
   blocks are kept as placed). The client uses `cells.js stoneAt` and `voxpaint.js rocky/level`. Owner, 2026-11-24:
   "Earth on top stone underneath should only be a matter of world generation. Grass shouldn't turn into stone."
4. **Art files:** pack sheets are copied by `tools/build_assets.py` (`COPY` dict: zip path -> name). Recoloured or
   derived ones are built there and in `tools/derived_art.py`. New 16x16 sprites are ASCII rows in
   `tools/pixel_art.py` (`GEN`, palette `P`, in the pack's colours), packed into `gen.png` plus `gen.txt`. The file
   list is `src/nexel_worlds/art.py` (`PACK`, `DERIVED`); the client load list is `web/js/assets.js` `ASSETS`.
   Rebuild with: `python tools/install_assets.py ~/Downloads` (the two zips are there).
   **Commit the sheets the game uses** (`src/nexel_worlds/web/assets/`, the license allows it, see its `CREDITS.md`);
   **never the raw packs** (the zips, `assets_pack/`: the license forbids redistributing the pack itself).
5. **Tops (2D paint of a tile):** `web/js/tiles.js`. There is one rule for a surface's cell: `drawBlobLayer` /
   `maskOf` / `blobCell` pick the sheet's rim or corner cell from the 8 neighbours. `plainCell` adds occasional
   speckled cells. `MARKS` holds what is laid on ground (soil + `furrows.js`, ash, floor, `pavement.js` path).
   `hillSheet(k)` is the sheet by level (grass 1-2, dark grass 3-4, stone 5+), a touch brighter each level up.
   `DEEP` / `deepTone` darken land under sea level, as one tone by depth.
6. **Sides and lips:** `web/js/voxpaint.js`, read from the level's own hill sheet (`relief.js colsOf`): `front`
   (south faces: the wall body, a seam, flecks, 4 variants), `rim` / `shape` (the pack's rounded lip on a top). Rules
   kept there: **one rock per wall** (every earth wall uses the first sheet's palette `EARTH`), **one tone per rock at
   every level**, and **stone from rim to foot** on a stone block.
7. **The game/engine bridge:** `web/js/voxels.js` (host: `column`, `paintTop` -> `drawTile`, `paintFront`, `rock`,
   `water`, `flow`, `models`). The engine `web/js/vox_*.js` must name **no game global** (`tests/test_vox_layer.py`
   runs it alone). Faces live in `vox_style_land.js` (chunks of 8x8, `FACES`) and `vox_mesh.js` (`rock`, `pick`). The
   atlas of paints and the shaders are in `vox_style.js` / `vox_style_glsl.js` (`AW = 2048`, highp). The x-ray mask is
   `vox_style_win.js`. Box models: `models.js`, `bridge_model.js`. Inventory cubes: `cube_icons.js` (3 faces of the
   block's own paint). The build ghost is `buildghost.js`.
8. **Water:** sea and lakes are grounds (`water`, `mid_water`, `deep_water`, `abyss`). The bed and clear water come
   from `waterbed.js`. Running water is `flow.py` + `sim/waters.py` on the server and `flow.js` on the client, drawn in
   `vox_style_land.js`.

## Steps to add or change a tile/block
1. **Look before designing.** Dump the pack sheet (PIL, a letter per colour, `|` every 16 px) and the painted px.
   The pack usually already has the right piece (end posts, corners, borders) and the game drew the wrong cell.
   Use the pack's own borders and corners. Never crop a cell to fake a border.
2. **A new LOOK goes on the mockup page first** (below). A plain fix that is not a look (a missing tile, a wrong
   cell) can land without it. For an open design question: a short plan, then wait for the owner's yes.
3. Add the rule in `tiles.py` (or the one function that decides it). Regenerate `rules.js`. Wire the art through
   the existing painters (`drawTile` / `MARKS` / `voxpaint.js` / `Models`) as data. **Never add a per-kind or
   per-situation branch.** Owner, 2026-11-23: "you duped logic and avoided abstractions to create many many little
   rules. dont like that." Find every place that decides the same thing, route them through one function, and delete
   the duplicates. Line count should go down. If the third fix to one method is another special case, stop and
   change the method.
4. Keep file sizes in limits (`tests/test_code_size.py`: 300 lines; `hd*.js` / `vox_*.js` 500). Split by concern.
5. Work in a git worktree served on another port, never in the tree the live game serves. The owner plays
   `localhost:7777` and sees web edits live. Copy server:
   `uv run nexel-worlds --port 7790 --world <copy> --saves <tmp> --seed 12 --dev`, staged with dev ops
   (`dev_col`, `dev_stamp`, `dev_teleport`, `dev_time`; `tests/e2e/game.py` `stamp`).

## QA (do all of it before showing anything)
- **Close shots of every face kind:** top, south front, east/west side, under the land, at zoom. Also check junctions
  (stair meets wall, rim ends, chunk borders) and a diagonal cliff. Check on desk and phone, by day and at night.
- **lookcheck** (16 fixed scenes, desk 1440x900 and phone 390x844, frozen clock, about 70 s):
  `PYTHONPATH=src .venv/bin/python tools/lookcheck.py [--only meadow,wall_earth,wall_stone,cave] [--accept]`.
  Output goes to `.lookcheck/last/sheet.png` (a changed scene in a red frame with its %) plus `diff_*.png`.
  `.lookcheck/accepted/` does not exist yet: the first run needs `--accept` on a known-good tree. Open the PNGs with
  Read and look at them.
- **Motion and walking:** film real frames (`tools/filmkit.py`; `tools/film_underground.py` and the other
  `film_*.py` as examples). Never judge from hand-placed poses.
- **Tests:** `PYTHONPATH=src .venv/bin/python tools/affected.py --why` lists the tests a change touches. Run those
  files with `-m e2e -n 2` (5 files at most, one run at a time), plus `-m "e2e and quick"`, plus the unit tests
  (`.venv/bin/python -m pytest`). Look tests: `test_e2e_hd_sides`, `_hd_surfaces`, `_hd_paints`, `_hd_sheet`,
  `_hd_whole`, `_hd_precision`, `_land_blocks`, `_pixels`, `_water`, `_flow`. A redraw of the land must equal the land
  made from nothing (0 px differing), including after editing one tile next to others.

## Mockup page workflow (the owner picks a number)
- There is ONE public page, updated in place: repo `sofianedjerbi/nexel-worlds-mockups`, served at
  https://sofianedjerbi.github.io/nexel-worlds-mockups/ (`index.html` + PNGs, `.nojekyll`). Never make a new page
  per round; replace old rounds.
- Build each option as **real code behind a dev URL switch** (as with `?sky=1..5` and `?under=`). Shoot real
  screenshots of the game on a copy server in the same staged places. Number the options, with **0 = today**. About
  five options; each section opens with the owner's quote. Never draw over the character.
- Push: clone it into the scratchpad, add the files, commit and push to `main`. Then check that the files really went
  in: `gh api repos/sofianedjerbi/nexel-worlds-mockups/pages/builds/latest --jq .status`. A sparse checkout once
  left the images out while the push "succeeded".
- When the owner picks ("go with 4"), build that one as the only rule, delete the switch and the other variants, and mark
  it "picked, built" on the page.

## Art rules (settled)
- Every block is 3D. Owner, 2026-11-18: "blocks should be 3d, every single one". Its sides respect the tileset:
  sides use **only the tileset's own colours, no invented shading**. Side shape is "side 4", picked 2026-11-19:
  a thin side, so a block stays 16 px wide and still shows a lit or shaded wall.
- A wall is one material from top to foot. No column-by-column grid of squares, no stone-over-earth staircase on a
  diagonal cliff ("this wall look so weird", 2026-11-19).
- Whole art px, solid steps. No dither checker strips on edges ("awful borders", 2026-11-22), no smooth gradients
  on walls, no see-through in the world's picture except water (wanted clear, "like those Minecraft shaders so we
  can see the depth", 2026-11-19).
- One light model for everything: a dug cut is lit by the same rules as a natural hill. There is no special
  "trench" or "hole" shading (removed 2026-11-23).
- **X-ray and cuts never reveal what is inside a wall**, ores included (2026-11-24). Today ores are surface boulders
  (block `ore`, `*`), and land cells are only earth or stone. If ores ever go into rock, one may show only where a
  face of it opens onto your space.
- Calm land: the pack's plain cells, with sparse decor. Pebbles and flowers on paths read as "weird artifacts"
  (2026-11-09). Surfaces must connect across tiles (pavement "textures arent connected", 2026-11-15).

## Pitfalls seen before
- Paint rows laid twice (`m.rows[(j>>1)&1]`) made stone px twice as tall: two pixel densities on one screen.
- A paint atlas that is too small spilled and reused slots: grass tops were drawn as stone after a sprint ("all
  textures are fucked up", 2026-11-23). `AW = 2048`, guarded by `test_e2e_hd_sheet.py`.
- `mediump` on phone GPUs gave lit or dark lines along tile rows. Keep `highp` (`test_e2e_hd_precision.py`).
- A tile's look depends on its neighbours (caps, sides, lips): an edit must redraw them too, across chunk borders.
- Overlapping see-through water boxes stacked tints and left dark gaps ("water propagation tiles are ugly and
  glitchy", 2026-11-23). Running water is one surface, one tint, no seam where it steps down.
- An old window or x-ray shader painting over the real blocks turned tunnel walls into dark gradient strips. Tall
  side walls seen at a slant stretch the art ("The 3d voxel style isn't respected... that 3d engine need more
  rigour", 2026-11-24). For a renderer change, write the one rule first: what is drawn, from where, and what the
  eye must always see (you and your floors).
- Never change an approved look to make an old test pass. Change the test, and say so.
- Phone GPUs: paint the land as px in JS and upload once. Never chain canvas compositing.
- Commit only your own files (another session may have uncommitted work in the tree). Use conventional commits.
  Build the demo from a clean checkout.
