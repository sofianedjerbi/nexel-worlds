# Journal

## 2026-11-08 · Iteration 1 — M1 core

**Decisions**
- Python 3.14 + asyncio + `websockets`, SQLite persistence (rationale in DESIGN.md §1). Sim is synchronous and
  asyncio-free, so it is fully unit-testable; the server wraps it in a 5 Hz loop.
- Theme (user's inspiration: an endless, autogenerating megastructure). All names and rules are original:
  8×8-cell world of halls, corridor junctions, solid mass, void shafts with grating bridges, coolant cisterns.
  **Accretors** are neutral builder automata that crawl along and extend walls/conduits, so the
  structure keeps growing on its own. **Sentinels** hunt during "lights-out". Skitters are food.
- Actions are generators that yield once per tick, which makes multi-tick actions, interruption and
  re-validation at completion simple and deterministic.

**Measured**
- 19 tests: tile edits, digging, tools, crafting/stations, fill/flood, fire spread/burnout, pathfinding,
  combat/death/drops, give/chat events, signs, lockers (break one open → loot), interrupt,
  persistence round-trip, chunk unload/reload, determinism (2 identical runs → identical state), starvation, accretors.
- 8 scripted bots over WebSocket for 4 min: 1604 decisions, **repeat rate 0.1%**, tick p50 0.21 ms,
  max 28 ms, peak RSS 36 MB, 909 tiles changed, 72 crafts. Restarting the server gave an identical agent state.

**Loop audit (fixed in the harness/policy, not by hiding errors)**
1. Diagonal lichen ping-pong: the bot walked *onto* a non-solid target and then targeted the neighbour forever.
   → Approach targets from a walkable 4-neighbour.
2. "Approach tile" was solid → move_to returned instantly with 0 steps, forever. → Check the grid for walkable spots.
3. 717/1360 `place:occupied` (random-direction placement). → Only place into free floor; building over debris is allowed.
4. 539 `no_path` repeats + tick p50 jumped to 8.9 ms: A* explored 4000 nodes per hopeless search.
   → Policy memory (unreachable targets avoided for 1500 ticks, dig out when stuck); A* got a passability memo,
   a cheaper heuristic and a 2500-node cap. 1000 ticks × 8 bots: 82 s → 3.3 s.
5. One 751 ms tick spike: chunk generation (23 ms/chunk). → Memoized cell kinds (11.6 ms/chunk) + slow-tick logging.

**Self-critique**: the scripted bots aren't "thinking". They're a baseline and the fallback policy. Hunger falls
fast (−60 per 10 min day); revisit when LLM agents are slower decision-makers.

**Also**: pulled the browser client forward from M4 because the user wanted to see and play the real game.
`http://127.0.0.1:7777/` shows a live world view, an agent list (click to follow), an event feed, and a play mode
(WASD to step, Shift+dir to dig, click to walk, command box for every tool).

**Next**: M2. Benchmark Qwen3-8B vs Qwen3-30B-A3B via mlx_lm.server, then build the thinker harness
(ReAct, notepad, outcome-grounded lessons, scripted fallback) and keep one agent alive for 30 min.

## 2026-11-08 · Iteration 2 — the client becomes a game (user feedback: "ugly", "how do I play/talk?")

**Hypothesis**: the flat-colour debug viewer hid how the world works and made playing a chore.
That matters for the project too: humans are how we'll judge whether agent behaviour looks alive.

**Change** (`web/index.html`, served by the game server at `/`)
- Procedural 16 px pixel-art textures (4 variants per tile, hashed by position). 3/4 view: solid blocks get
  a raised top and a front face, drawn back to front with entities, so walls occlude correctly. Agents hidden
  behind walls show as an x-ray silhouette.
- Lighting buffer: ambient gloom by day, near-black at lights-out with dusk/dawn ramps. Light around agents;
  warm glows from heaters and fire, cyan from terminals and accretors, red sentinel eyes. Vignette.
- Sprites for people (per-name colour, facing, bob), skitters, sentinels, accretors. Smooth interpolation.
- Play UX: join screen, Enter-to-talk chat bar (`!` shout, `/tool k=v` raw commands), speech bubbles,
  hotbar with icons (1–9 select, E eat), crafting panel (shows what you can craft right now), context clicks
  (walk / dig / attack / read sign / open locker; right-click to place; select an item and click someone to
  give it), hold WASD to keep walking, damage and loot floaters, toasts with hints.
- Server: the region reply carries time and night phase; spectators can fetch recipes.

**Bugs found by testing in real Chrome (Playwright, channel=chrome)**
1. The spectator event envelope `{"type":"event", **ev}` was overwritten by the event's own `type`, so the feed and
   bubbles were silently dead since M1. → `{"type":"event","ev":ev}`.
2. The light buffer accumulated alpha each frame and went black. → clearRect each frame.
3. Following or spawning off-screen never moved the camera (the camera only knew entities inside the region).
   → fall back to the agent list or self position.
4. A taken name gave a cryptic error; RPC calls were sent on a CONNECTING socket. → Clear message, guarded rpc.
Also: bots now reconnect when the server restarts.

**Result**: no console errors; join, walk, talk, feed and bubbles verified in a real browser.
**Next**: M2 thinker (model benchmark, then one LLM agent surviving 30 min).

## 2026-11-08 · Iteration 3 — real tileset, real responsiveness (user: "still ugly, latency is insane")

**Diagnosis**
- Latency: (1) a 1-tick action took 2 ticks (the generator yielded before acting) = 400 ms/step;
  (2) the browser polled positions every 150 ms; (3) the player waited for the server before moving.
- Ugliness: per-tile bevelled squares made a checkerboard grid, there was too much per-pixel noise, and
  non-integer scaling (16 px art at 40 px) made uneven pixels.

**Change**
- Sim: `wait(n)` counts the starting tick, so a step completes in the tick it is picked up. Server pushes
  `{"type":"tick", entities}` for each spectator's watched rect every tick; `region` also returns ground rows.
- Client renderer rewritten: tiles are cached per 32×32 block in two canvases (floor, walls) produced by
  **per-pixel shaders** (ImageData), patched live from `tile` events and periodically resynced.
  - The structure autotiles into continuous slabs (outline and bevel only where a slab meets open floor),
    with 64×48 px panel seams in world space so walls read as giant plates. 8 px front faces in a 3/4 view.
  - Floors: 2×2-tile deck panels with rivets, rust wear and scuffs. Moss is blended bilinearly across tile
    borders (no square edges). Grating over the abyss, ragged breaches, void shafts with depth falloff.
  - AO: floors darken under front faces and beside walls.
  - Hand-made 16×16 pixel sprites for objects, props, creatures and people (per-name colour, 4 facings,
    walk frames). Integer zoom 1–6 (default 3×), so pixels stay square.
- Input: client-side prediction (your character moves on keydown; the server confirms within a tick);
  the camera is locked to the player; constant-speed interpolation.

**Measured (real Chrome via Playwright)**: step round trip 200 ms (one tick, previously ~400 ms plus up to
150 ms polling), with zero perceived delay thanks to prediction; holding a key walks at 5 tiles/s; no
console errors. Tests: 19 passed.
**Next**: M2 thinker.

## 2026-11-08 · Iteration 4 — speed fix + re-theme to Sprout Lands (in progress)

**User**: "a single action can take whole seconds", then supplied the Sprout Lands art packs and asked for a
less robotic theme with real building support.

**Done**
- Timing is now in seconds: `sec()` converts every duration, and the tick rate is 10 Hz, so actions take half
  as long and future tick-rate changes never alter game pace. Actions record `expected` ticks for progress UI.
- Rate limits raised (900 act/observe per min). The old 120/min cap was throttling human walking.
- Measured the client stall: a full 32×32 per-pixel chunk re-render costs 40–50 ms, and frames freeze for up to 370 ms.
- Re-theme (sim): archipelago world gen; trees, berry bushes, thickets, rocks with ore, mushrooms; chickens
  and cows (food), glooms at night; accretors removed. Farming: dig to till, plant seeds, they ripen to wheat.
  New items and recipes (wood, stone, fiber, ore, ingot, axe, pickaxe, spear, sword, fence, stone wall, door,
  campfire, workbench, chest, planks to bridge water). Tests updated: 19 pass.
- `tools/build_assets.py` copies only the used sheets from the user's zips into `web/assets/`, generates extras
  in the pack palette (campfire, fire, flag, gloom, ore, tool and food icons, ash and deep-water recolours,
  UI 9-slices) and writes CREDITS.md (credit: Cup Nooble; the pack itself must not be redistributed).

**Next**: rewrite the client renderer on the atlas: animated water; soil, grass, tilled and stone layers
autotiled with masks computed from the layer sheet's alpha (all sheets share one 11×7 blob layout); y-sorted
sprite objects (trees, rocks, fences with N/E/S/W masks, chest, workbench, crops by growth stage); character
4-dir walk; chickens and cows; UI with the pixel font, panel and slot 9-slices; action progress bars;
incremental 3×3 tile redraws within a per-frame time budget.

## 2026-11-08 · Iteration 5 — the client on Sprout Lands art

**Change**
- Client rewritten on the atlas. Ground is layered: animated water, then soil islands (beach rim),
  grass, tilled soil, ash, cobble, planks, then rock and hedge masses. All are autotiled from a neighbour-mask
  table computed at load from the grass layer's alpha, since every sheet shares the 11×7 blob layout; plain
  interiors get decor variants. Trees, bushes, boulders, fences (N/E/S/W-connected), workbench, chest, door,
  campfire, crops, signs and flags are y-sorted sprites with characters, so canopies overlap people
  correctly. 4-direction animated character, recoloured per person; animated chickens, cows and glooms.
- UI uses the pack: pixel font, 9-slice panels and inventory slots, sprite icons per item.
- Night: multiply tint plus warm light from campfires, fires and people.
- Speed: a tile change redraws only its 3×3 neighbourhood; at most one fresh chunk is drawn per frame and
  dirty tiles get a 4 ms budget; resyncs diff instead of redrawing. The server pushes a `progress` message
  when a multi-tick action starts, and the client shows a bar instantly.
- Server serves `/assets/*` (whitelisted extensions, no path traversal; checked with `/assets/../server.py`: 404).

**Measured (real Chrome)**: chunk draw 1–2 ms (was 40–50 ms); 10 s of frames: p50 17 ms, p99 17 ms, max 17 ms,
0 frames over 100 ms (was max 367 ms). No console errors. Tests: 19 pass.
**Next**: M2 thinker on the local model.

## 2026-11-08 · Iteration 6 — beauty and honest collisions (user: "collisions are weird", "spawns everywhere", "font ugly", "loading on every action")

- **Progress bar on walking**: a step lasts 2 ticks, so it qualified for the bar. Now only real work
  (≥ 0.35 s, never step/move_to) gets one, filtered on both the server and the client.
- **Collisions**: rock outcrops were flat grey ground that blocked invisibly; the workbench was drawn 2 tiles
  wide but blocked 1; stone walls looked like floor. Now every solid thing is a sprite exactly on its tile
  (new generated boulder, stone wall and workbench sprites), and nothing non-solid looks solid.
- **World generation**: rewritten as a greenfield: big calm islands with thin beaches, an empty meadow
  around spawn, groves on a 2×2 jittered grid (spaced, denser at the centre), berry bushes and the odd hedge
  on grove edges, mushrooms under trees, small boulder fields with some ore, sparse lone features on 7×7 cells.
- **Font**: the pack's pixel fonts are caps-only and the 8×14 one was rendered off its native size (only crisp
  at 18/36 px). Switched all UI and canvas text to a rounded sans (ui-rounded).
- **UI**: vitals with heart, food and energy icons; a 9-slot hotbar where items keep their slot (1–9 select);
  free-floating wooden slots; help is opt-in.

## 2026-11-08 · Iteration 7 — our own pixel font (user: "use a pixelated font everywhere")

The pack's fonts are caps-only. `tools/build_font.py` draws a 5×7 pixel font with lowercase, descenders,
punctuation and a few symbols (♥ ☠ · …), and compiles it to TTF with fontTools: each pixel is a square
contour, 100 units with unitsPerEm 900, so it is pixel-exact at 9/18/27/36 px. Spacing is proportional
(glyphs are trimmed to their ink, plus 1 px). All CSS and canvas text uses it at 18 px (2×) with
27/36 px titles; synthetic bold is disabled. Also fixed a leftover "sentinel#…" attacker name.

## 2026-11-08 · Iteration 8 — intuitive play (user: "I can walk through tree things, they're everywhere, nothing is intuitive")

**Diagnosis**: the "tree things" were walkable stumps left by the 8 scripted bots' chopping; the bots also
littered workbenches and fences. Placing needed select plus right-click on an adjacent tile, with no
preview. Clicks gave no hint of what they would do. At zoom 1 the meadows were still peppered with bushes and boulders.

**Change**
- Felled trees leave clean ground and regrow later on the same spot; no stumps. Scripted bots stopped (they
  only cluttered the world; agents come back as RL). Fresh world.
- Sparser generation: lone meadow features on 11×11 cells, grove-edge bushes on 4×4 cells in a narrower band,
  boulder fields rarer but still enough stone.
- **Intents**: every hovered tile resolves to one action, shown as the cursor hint ("Chop tree", "Pick
  berries", "Mine ore", "Plant seed", "Till & plant seed", "Fill hole", "Build bridge", "Open chest",
  "Give wheat to X", "Attack chicken"...). Clicking walks to the nearest free side and does it (using the
  server's arrival position, not the last tick, for the facing direction). Pointing at a tree's canopy
  targets the tree.
- **Placing**: select a placeable item and a ghost of it follows the cursor, tinted green or red with a
  reason ("Can't place workbench here"); click to walk over and place. Esc deselects. Hotbar tooltips say
  how to use each item. Workbench and campfire clicks open the craft panel.
- **Goals card** (top left) for new players: wood, workbench, berries, planting, stone, axe, campfire;
  completed goals drop off.
- People list shows only who's awake (+N asleep).

**Verified in Chrome (Playwright)**: hover shows "Chop tree"; one click walks 15 tiles and chops (+3 wood, 2.8 s);
a second tree works too; craft workbench; select it (key 2); hover shows "Place workbench" with the ghost; click places it.
No page errors. 19 tests pass.

## 2026-11-08 · Iteration 9 — animation (user: "the animation sequence isn't good; animate every action")

**Diagnosis**: the walk cycled frames 0–3, but in the pack frames 0–1 are the idle breathing pose and 2–3 are the
walk, so walking stuttered between standing and stepping. Actions had no animation at all.

**Change**
- Walk = frames 2–3 every 120 ms with footstep dust; idle = frames 0–1 slowly.
- The pack's actions sheet (4 directions × hoe/axe/can, 2 frames) is recoloured per person like the walk sheet.
  dig/attack/craft swing (axe for wood things and fights, hoe for earth and stone), facing the target (the
  server now sends each agent's action `dir` and target `tid` per tick). On every strike: debris particles by
  material (wood chips and leaves, stone chips, dirt clods, berries, sparks) and a shake on the target.
- Trees: the pack's animated tree sways in the wind and plays its hit frames when struck; felling plays the pack's
  13-frame falling animation, then fades (no stump).
- Placed objects bounce in; removed objects burst into debris; tilling throws dirt.
- Fights: the target flashes white with a knockback, plus hit sparks and a floating damage number; deaths and
  creature kills puff into dust. Eating bobs with crumbs; resting floats "z"; place/pick up/give/store hop;
  crafting throws sparks. Chickens and cows use their real idle (row 0) and 8-frame walk (row 1) cycles; glooms hop.
- Your own action animates the instant you click (not after the server reply).

**Verified**: a frame-by-frame capture in Chrome of walk → axe swings → shakes and chips → felling → +3 wood; no page errors.

## 2026-11-08 · Iteration 10 — use the whole premium pack; sprinting; honest animation (user feedback, several rounds)

**Audit** (frames in the pack vs used): premium character 0/192, chicken 11/115, cow 11/42, chest 1/10, door 1/18,
fruit trees 0/~100, crops 2/59, water objects 0/18; emoji, cursors and flowers unused. Also a real bug: the chicken
walk row has 7 frames, not 8, so it blinked.

**Change**
- **Premium character** (8-frame rows): idle, walk, run, hoe, axe. Swings strike on frame 4 (with the
  pack's arc), where debris and the target shake fire. Left/right rows were swapped twice; settled by measuring the
  eye and collar-bell position (the pink spot is the inner ear, at the back): rows go down, up, right, left.
- **Sprinting**: Shift doubles speed (0.1 s/tile) and costs 1 energy per 4 tiles (sim `stride()`); Space uses the
  faced tile; the run animation shows for everyone (`run` is in the tick).
- **Continuous walking**: a held key sends one `walk` (server walks at an exact stride until blocked or `stop`)
  instead of a step per round trip. Your own position glides at the exact stride speed, never more than a tile ahead of the
  server; others move at their pace. Measured in Chrome: walk 10.0 tiles/2 s, speed p10=p50=p90=5.0, 0 stalled
  frames (was 22), first motion 27 ms; sprint 19.8 tiles/2 s at 10.0, 0 stalls.
- **Action animations only on confirmation**: the server pushes `progress` when any timed action actually starts; the
  client animates only then, so refused actions (no tool, blocked...) show nothing (was 1 frame).
- **Anchors audited** against each sheet's measured base: the falling tree was 8 px off (−24 → −32), the young tree
  floated (−18 → −13), the character sat 2 px high, the chicken 2 px high. Fixed.
- **Fruit trees** (apple, pear, peach, orange; 15% of grove trees): sway; picking plays the 12-frame fruit drop,
  gives 3 fruit, and the fruit regrows in 4 min. **Crops** grow sprout → young → ripe.
- **Chests** open and close when used; **doors** swing open when someone is next to them.
- **Animals**: chickens walk (7 frames), peck and sleep at night; cows walk, graze and sleep; whims change every 4 s.
- **Decor** baked into the ground layer: lily pads, reeds and rocks on shore water; flower patches in meadows.
- **Emotes** from the pack's emoji sheet (cat faces, hearts, stars, !, ?, zZ, skull) for chat moods, gifts,
  crafting, being hit, resting and death. The **cat-paw cursor** points when hovering something actionable.
- **Lag**: water was a drawImage per tile per frame (thousands at zoom 1), now one pattern fill. The JS frame cost
  is ~6 ms per second of play; 60 fps at zoom 1 and 3.
Tests: 22 pass (sprint, walk/stop, fruit regrowth added).
