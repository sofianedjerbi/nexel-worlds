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

## 2026-11-08 · Iteration 11 — real mechanics from the rest of the pack; one consistent placement rule (user: "dandelion top not removed", "placing stones is weird, make everything consistent, loop until it's high quality")

**Bugs**: flower decor picked random halves of the two-tile sunflower per tile (a "top" floated alone) and was
painted into the ground, so it could not be broken. Dropped items were never drawn at all.

**Placement rule (sim + client)**: every placeable item has one result per kind of surface, and the ghost renders
exactly that result: blocks render their real sprite, floors render the real tile. Raw materials are never placeable;
`path` (2 stone → 2) lays cobble; `plank` builds a bridge on water or a floor on land; `dirt` fills holes and water.
Anything laid can be taken up again (shift-click returns the item). Building over a flower picks it. Tilling yields
nothing (no dirt clutter).

**New mechanics**
- Flowers are real objects (19 kinds plus the tall sunflower drawn whole): pick, place, gift, craft into potted plants.
- Ground items are visible (bobbing, with a shadow) and picked up by walking over them.
- Farming: 6 crop species (wheat, pumpkin, cauliflower, lettuce, eggplant, carrot), chosen by a tile hash shared by
  server and client; sprout → young → ripe from the pack's growth columns; the watering can (premium watering
  animation, drops) makes wet soil and halves the time to the next stage; harvest gives that species plus seeds.
- Animals: chickens lay eggs (~every 1.5–3 min, sooner when fed); cows can be milked every 2 min; feeding plays the
  pack's love-hearts animations.
- Furniture from the pack: bed (sleep: +60 energy, +10 HP, and you respawn next to it), chair, table, potted plant, clock,
  rug; fence gates that open next to people; oriented bridge planks; wooden floors.
- UI: 9-slot hotbar plus a bag (B) for the rest; hints for everything ("Feed lettuce to the cow", "Water crop (grows 2x
  faster)", "Pick flower, till & plant", "Take up the path"...).
- `--dev` server flag enables `dev_give` for automated QA only.

**QA in Chrome (Playwright, real clicks)**: built a homestead (bed, chair, table, plant, clock, rug over a flower, gate,
chest, workbench, campfire, fences, path, floor) and planted and watered 6 seeds; every placement matched its hint and
the resulting tile; screenshots reviewed. Tests: 26 pass.

## 2026-11-08 · Iteration 12 — houses, sleeping, taps (QA-driven loop)

- **Taps** (user: "a quick press resets"): a tap sent walk then stop before the first stride, while the
  client had already glided into the next tile, so it snapped back. On release the client now finishes the
  tile you visibly entered (move_to that tile, kept as a prediction until the server agrees). Measured taps of
  30/60/140 ms: +1 tile each, 260 ms: +2; largest backward jump 0.000; display always equals the server.
- **Placing on your own tile** said "Pick up"; with a placeable selected it now steps aside and places.
- **Sleeping** draws you tucked into the bed (head on the pillow, the bed's blanket over you) with zZ.
- **Houses**: `wood_wall` (3 wood → 2 at a workbench). Walls pick their piece from the pack's house tileset by
  where the room is (top, bottom, sides, corners). The client finds rooms (areas closed by walls/doors/gates,
  ≥1 wooden wall, compact: ≤14×14 and ≥60% filled) and draws the pack's shingled roof, ridge band and chimney;
  the eave hangs over the front wall so the facade and doorway stay visible; the roof fades while you are
  inside. The server uses the same rule for `sheltered` (rest bonus). Doors use the tileset's doorway piece.
- Bugs found by QA: the room flood fill shared a global `seen` set, so a fill reaching an area explored by an
  earlier open fill stopped early and called a meadow strip a room (fixed: touching another fill = open);
  corridors between old walls became roofs (fixed by the compactness rule); the roof's raised offset and the
  eave's transparent edge let the interior peek through (fixed: solid shingles plus an overhanging eave).
Tests: 27 pass (+ room shelter).

## 2026-11-08 · Iteration 13 — audit round: crafting, night, death

- Crafting is now a centred window: recipes grouped (Getting started, Tools & weapons, Building, Home, Cooking & smelting),
  each a card with the item's icon, ×N output, cost chips (icon + amount, red when short, tooltip with what you
  have) and an "at workbench" line that turns red when you're not at one. Esc closes it.
- Death shows a banner: the cause, what you dropped and where, and whether you'll wake by your bed (the observation
  now includes `spawn`).
- Night: verified the campfire glow and darkening in Chrome; fruit picking verified (+3 fruit).
- `--dev` adds `dev_time` and `dev_damage` for QA of night and death.

## 2026-11-08 · Iteration 14 — others, night, sound

- QA now runs on a separate server (port 7790, world `qa`) so test characters stop cluttering the play world.
- Others' animations verified (scripted bots: walk, axe swings with arcs, tree shakes and falls); 60 fps
  (p95 16.8 ms) with 4 bots working nearby.
- Night: glooms hunt and kill (one killed a passive bot; 7 dmg every 1.2 s). The news panel was flooded by other
  people's fights, so attacks now only show when they involve you; deaths still show for everyone.
- Sound: the pack has none, so short WebAudio effects are synthesized: footsteps, wood thunk (chop),
  stone clink (mine), soft dig, pickup and place blips, craft arpeggio, hit, munch, watering, death. Others' sounds
  fade with distance (silent beyond 12 tiles). M toggles sound.

## 2026-11-08 · Iteration 15 — animal life cycle and variety

- Eggs left on the ground (laid, dropped or spilled on death) hatch after 3 min into chicks; chicks grow into chickens
  in 5 min. Feeding two cows standing within 3 tiles of each other makes a calf, which grows into a cow in 6 min.
- Colour variants from the pack, chosen per animal: chickens and chicks (default, brown, red, blue, green), cows and
  calves (brown, light, pink, purple, green). All four kinds share one animation table (row, frames, ms per behaviour:
  idle, walk, peck/graze, sleep at night, love with hearts) measured from the sheets.
- `--dev` adds `dev_skip` (fast-forward) for QA. Verified in Chrome: 3 dropped eggs → 3 chicks after a skip.
Tests: 28 pass.

## 2026-11-08 · Iteration 16 — boats

- `boat` (8 wood + rope at a workbench). Launch it on shallow water next to you, walk onto it to board, sail over
  water (shallow and deep, 0.15 s/tile), and step onto land to get off; the boat is left moored where you
  disembarked. Dying at sea leaves the boat floating. The sim gained `can_enter`/`move` (boarding and mooring at the
  shoreline) used by step, walk and move_to; pathfinding lets you path onto your boat as the last step.
- Client: moored boats rock (pack frames); sailors are drawn sitting in the hull with the moving frames' wake, flipped
  by heading; hints "Launch boat", "Board the boat", "Sail here", "Go ashore"; splash particles and sound.
- Deep water uses rounded blob edges (a dark-blue copy of the grass layer's shapes) instead of hard rectangles.
- `--dev` adds `dev_teleport`. QA in Chrome on a lake: launch → board (sailing: true) → sail 5 tiles → go ashore (boat
  moored on the last water tile).
Tests: 29 pass.

## 2026-11-08 · Iteration 17 — mail, goals, responsive hotbar

- Mailboxes (3 wood at a workbench): placing one records you as owner. `post` leaves a letter (max 20); `open_mail`
  takes all letters out, and anyone can do it, so letters can be stolen (the owner is told who opened it). Ticks carry
  `mail` markers, so a mailbox with mail shows the pack's letter-bubble frame. Client: a mail panel (write/post, take
  the letters out, read), and toasts for "X left you a letter" and "X opened your mailbox".
- Goals card covers the whole progression (wood → workbench → berries → planting → stone → axe → campfire → watering →
  eggs/milk → house → boat → mailbox), ticked off by observed results (sheltered, sailing, act results).
- Hotbar slots scale with window width: one row and no overlap at 1200/1440/1920 px (measured).
- QA with two browser players: B posts through the panel → A gets a toast and sees "Mailbox: there's mail!" → opening shows
  the letter. Tests: 30 pass.

## 2026-11-08 · Iteration 18 — new-player audit

Scripted a fresh player (no granted items, only intents/clicks) through the early goals.
- All early resources lie within ~30 tiles of spawn on both seeds (measured), but the 18-tile empty clearing meant
  nothing was on screen at spawn: now 6 tiles, so trees/bushes/flowers are in view immediately.
- Fiber (axe, pickaxe, torch, rope) only came from rare thickets: berry bushes now also drop 1 fiber.
- The player wandered 29 tiles from the workbench and the axe card was dead ("need station"). Station recipes you
  have the materials for now show a dashed card, "Click to walk to the workbench and craft", and do exactly that
  (nearest station within 60 tiles).
- Playthrough: 3 trees, workbench placed, 2 bushes, 2 boulders, axe crafted via the card, in ~30 s with no errors.
- Welcome toast fixed ("meadow", not "shore"); flower patches slightly sparser.
Note: generation changes only apply to newly generated chunks; the existing play world keeps its first chunks.

## 2026-11-08 · Iteration 19 — mid-game audit

- Glooms walked through doors, so a house gave no safety at night, and animals walked through gates, so pens were
  impossible. Creatures can no longer enter door or gate tiles (people still can). Test added.
- Crop growth verified in Chrome over fast-forwarded stages: sprout → young → ripe for all 6 species. Found the hint
  hard-coded "Harvest wheat" while the plot was an eggplant (the server correctly gave eggplant): hints are now
  species-aware ("Harvest lettuce", "Young pumpkin (uproot)", "carrot sprout (uproot)").
Tests: 31 pass.

## 2026-11-08 · Iteration 20 — fire, glooms by day, news spam

- Torches had no UI: selecting one now offers "Set on fire" on anything flammable (and "That won't burn").
- Fire is an overlay: the burning tree, wall or crop stays visible with flames (taller over trees, smoke and ember
  particles, warm light at night) until it burns out to ash. Ticks carry `fires`. Fire jumps readily through
  wooden things but only creeps across bare grass (0.03/s vs 0.1/s), so one spark doesn't burn a whole meadow.
- Ash looked like a stone slab with a hole (recoloured tilled sheet); it is now the grass layer's soft shapes recoloured
  to charcoal, and grows back into grass after 4 min.
- QA found a player killed by a gloom in daylight (glooms lingered ~25 s after dawn and kept biting): glooms never
  attack by day and fade within ~2 s of dawn (poof). Test added.
- News: identical consecutive lines collapse into one with ×N.
- Bug caught by QA: the flame helper had been lost in the Sprout rewrite (`drawFire is not defined`); restored on the
  generated flame sprites.
Tests: 33 pass.

## 2026-11-08 · Iteration 21 — structures bigger than a tile: well, coop, picnic

Hypothesis: the pack's well, chicken coops, picnic blanket and basket can become useful, collision-honest objects
if the world supports multi-tile structures without changing the chunk format.
- Multi-tile structures: the block sits on the bottom-left tile and the rest of the footprint holds `part` (solid) or
  `flat_part` (walkable). One rule, shared by server (tiles.footprint/structure_at) and client (footprint/structAt):
  placing at a target covers the w×h spot centred on it and extending away from you; any part tile means the whole
  structure (dig, burn, water, describe, the agents' ASCII view). You can't place one over yourself; the ghost tints
  every covered tile and names what is in the way ("Wait, something is standing there").
- Well (2×2, 8 stone + 2 wood + rope): watering cans now hold 12 waterings (bar on the hotbar slot) and refill at a
  well or any water. Coop (2×2, 8 wood + 2 fiber): hens within 6 tiles lay twice as often, into the coop's door tile.
  Picnic blanket (3×2, walkable, 6 fiber): food eaten on it fills 50% more (hearts). Basket (3 fiber): a small chest.
- Item icons keep their aspect ratio (the boat and new structures were squashed).
- QA in Chrome: all four placed exactly where previewed, can filled from the well's right half, picnic bonus applied,
  the well taken down from a part tile clears all 4 tiles. Bug caught: the client's object whitelist didn't list the
  new chars, so nothing drew.
Tests: 37 pass (4 new).
Next: hay bales/feeding boxes from the barn sheet (feed animals in bulk), performance check on a big built area.

## 2026-11-08 · Iteration 22 — performance audit on a big built-up area

Hypothesis: a dense town (houses, fields, pens, paths) will show any client or server cost that the open meadow hides.
- Tool: `dev_stamp` (dev only) paints ASCII rows of tile chars; the QA script stamps an 80×60 town of houses, crop
  fields and fenced pens, then measures rAF gaps and JS time per frame (idle, walking, sprinting, zoom 1 and 2).
- Found a population explosion: eggs hatched without limit, so chicks became hens that laid more eggs. QA had 3.5k
  chickens, the play world 7k, and the server ran at **70 ms/tick** (100 ms budget). Now hens don't lay, eggs don't hatch
  and cows don't breed when 10+ farm animals are within 6 tiles or 200 exist in the world; on load, old worlds are
  thinned to that density (oldest kept). Result: **1.4 ms/tick p50** (7 ms max), 199 hens in QA, 200 in the play world
  (backup kept in saves/islands/world.before-thinning.sqlite). Test added.
- Client: a 96–129 ms hitch on the first steps, all inside drawEntity: the first footstep sound created the
  AudioContext mid-frame. Audio now starts on the first click or keypress. Sheets are also decoded at load. Result in
  the dense town at zoom 1: 120 fps, JS p50 2–3 ms, p99 10–14 ms, worst frame 24 ms (was 98–129).
Tests: 38 pass.
Next: hay and feeding boxes (barn sheet) for feeding animals in bulk; then revisit agents (M2/M3 harness on the new world).

## 2026-11-08 · Iteration 23 — troughs and hay

Hypothesis: feeding animals one by one doesn't scale to a farm; a trough that animals use by themselves makes the
barn sheet's feeding box and hay bales part of play.
- Hay (3 wheat, no station): feeds animals (one bale = three meals from a trough) and places as a hay bale.
- Trough (4 wood, workbench): put hay or any food in it (only feed is accepted); every ~30 s each hen or cow within
  5 tiles that isn't already in love eats from it: hens lay, pairs of cows make calves (crowding limits still apply).
  The box shows hay heaped in it while it holds feed (ticks carry `troughs`). Clicking it empty-handed takes the feed out.
- Click order fix: with an item selected, clicking a chest/basket/trough now stores it instead of trying to place it
  next to it ("Store fence in chest" used to say "Can't place fence here"); torches still set containers alight.
- QA in Chrome: trough + bale placed, trough filled by click (hay drawn in the box), fence stored in a chest, hay crafted.
Tests: 39 pass.
Next: agents. The world now has enough systems (farms, animals, houses, boats, mail) for M2/M3 runs to be interesting;
re-run the agent harness against it and measure what agents actually do.

## 2026-11-08 · Iteration 24 — fast taps snapping back, an overloaded map, ugly bush removal

User reports: "when i press briefly to walk ... (very fast pushing) it gets reset", "the map is overloaded",
"destruction of bush is ugly", "eggs everywhere".
- Taps: reproduced in Chrome (6 taps of 50 ms, 70 ms apart: the player glided 3 tiles, then snapped back to the start).
  Cause on the server: every move waited a full stride *before* stepping, and each new tap interrupted the previous
  move during that wait, so the server never moved. Movement is now step-first with a stride cooldown (`Agent.ready`):
  same top speed, but interrupted moves keep their progress. Result: worst backward correction 0.04 tile (was a full
  reset), display and server agree after every sequence. Tests: sprint now measured over 8 strides; rapid-tap test added.
- Eggs: the play world had 883 egg piles left from the chicken explosion (crowded eggs were kept forever). Now an
  uncollected egg that can't hatch rots away; hens lay half as often; limits are 6 animals per neighbourhood and 80 in
  the world; leftover egg piles are cleared on load. Play world: 883 → 2 piles, 200 → 80 hens.
- Bushes: every 20 s each loaded chunk had a 10% chance to grow a berry bush on any grass, without limit, which filled
  the meadows over hours. Nature now only grows back what the generator put there (bushes, flowers, mushrooms), and
  bushes the old rule spread are cleared when their chunk loads (nobody can plant a bush). Spawn view: 162 → 21 bushes.
  Backups: saves/islands/world.before-egg-cleanup.sqlite.
- Removal: a dug object (bush, rock, furniture...) used to vanish in one frame in a burst of red/purple squares. It now
  squashes into the ground and fades over 0.24 s, shedding debris sampled from its own sprite's colours.
- Scripted policy (in progress, interrupted for the above): needs-based rewrite (home/bed/chest/farm). 3-minute run vs
  baseline: repeats 633 → 17, bots now craft, place, sleep, store and farm; still to fix: duplicate bed placement,
  unreachable explore/flee targets (in-view reachability planned).
Tests: 41 pass.

## 2026-11-09 · Iteration 25 — a pile of player feedback: hands, keyboard, refactor, HUD, nature

User feedback, in order: bare hands by default with tools only when held; full keyboard play; birds walking in place;
"spaghetti, refactor with best practices"; lag when sprinting; chickens hop instead of walking; act in any direction
without turning ("Alt+direction isn't natural"); attack range too small, attacking not the default; "a tool without a
tool"; the news panel is too much, wants Minecraft-like chat and vitals on the hotbar; unnatural break particles; picked
fruit trees turn thinner; bushes vanish when picked.

- Hands: dig/attack only use a tool or weapon named in `with` (the item in hand); ore needs a held pickaxe. Plain
  click/Space fights, shift-click/X is the peaceful use (milk, take down, till). Bare hands now animate as a reach
  (the sheet's swings show an axe/hoe, which was the "tool without tool"). Melee reach 2 tiles, spear 3.
- Keyboard: Space acts, X is the alternative; no turning needed: it targets the faced tile, then the nearest creature
  or person in reach, then any neighbour (last direction first). A prompt above the hotbar says what Space/X will do.
  Q/1-9/0 choose what's in hand; C crafting and B bag navigate with arrows and Enter (Shift+Enter crafts 5).
  Big structures extend away from the placer (facing south puts the well south). QA: chop, craft, place, take down,
  all keyboard-only in Chrome.
- Refactor: sim.py (1.5k lines) → sim/ package: constants, entities, specs, core (tick loop) + mixins movement,
  building, items, combat, animals, needs, social, environment, observe. Done with an AST script: every method body
  byte-identical (verified), imports per module computed, ruff F/I clean. Client index.html (1.7k lines) → markup +
  css/style.css + 16 scripts by concern; server serves /js and /css with the same path-escape guard.
  A duplicate `held` declaration had broken the whole client for a while; tests/test_web.py now syntax-checks every
  script and the bundle with node.
- Animals: the chicken sheet's row 1 is a hop and row 2 the walk; we had them backwards (walk-in-place idle, hopping
  movement). Fixed and verified on a frame strip.
- Sprint: could not reproduce stalls (0 stalled frames at 10 tiles/s, DPR 1 and 2, new terrain, a copy of the play
  world; 120 fps, ~0.5 ms JS/frame). Found a real judder source: the camera offset and the player were rounded to
  pixels separately, so you wobbled 1 px against the ground at odd window widths. Fixed with screenOrigin().
- Nature: picking a fruit tree leaves the same tree, bare (fruit_bare.png is generated from the pack's last drop frame
  minus the fallen fruit); picking a bush leaves a bare bush; both bear again (4 / 3 min) and the fruit arcs into the
  picker's hands. Cutting the bare bush gives fiber. Debris now takes the struck block's colours, lands, bounces,
  settles and fades, with a dust puff from stone.
- HUD: hearts (left) and drumsticks (right) on the hotbar, energy line between, status line for starving/exhausted;
  chat bottom-left fades after 10 s, Enter opens the history; only chat, deaths, arrivals and things involving you;
  people panel is just who's awake; server stats on F3.
Tests: 61 pass (43 sim + 18 web).
Next: unfinished bot policy fixes; audit remaining info texts that still say "shift-click"; ES-module migration.

## 2026-11-09 · Iteration 26 — interaction rules review

User: punching stone should be slower, trees too; tilling should need a tool; review the interaction logic.
Rules now, server-side, the same for people and agents:
- Hardness is the time with the right tool in hand; by hand wooden things take 4x, stone 6x (rock: 0.9 s with a
  pickaxe, 5.4 s by hand, measured in Chrome); soft things (bushes, fruit, crops, flowers, paths) stay quick by hand.
  Ore needs a pickaxe in hand.
- Tilling needs a hoe in hand (new item, workbench: 2 wood + 1 stone; the pack's hoe icon, which we had been showing
  as the pickaxe; the pickaxe now uses its generated icon). Seeds still need tilled soil, so no more "till & plant" by
  hand. Watering needs the can in hand, setting fire a torch in hand (or a campfire nearby).
- Hints say "by hand (slow)"; with the hoe in hand, Space on grass tills; bots craft and hold a hoe to farm.
Tests: 62 pass (hand-speed test added; tilling/watering/fire tests now hold their tools).

## 2026-11-09 · Iteration 27 — stumps, deaths, sound, fight priority

- Felled trees leave a solid stump (axe-type, 1 wood; a tree regrows from it; you must dig it before building there).
  Round trees end the pack's felling sheet on that very stump; thin trees (no sheet) creak, fall with a swoosh and
  break into leaves; both fall away from the chopper (the sheet is mirrored when needed).
- Deaths: the creature's own sprite flashes white, lifts and fades inside a puff of smoke (also glooms at dawn,
  smoke where a person falls). Recently removed entities are remembered 2 s so a late death event still finds them.
- Sound review: everything that happens now sounds, chosen by material (wood/stone/plant/soil): strikes, breaks
  (snap/crumble/rustle), tree creak + landing thud, collect blip whenever something enters your bag, place sounds for
  anyone nearby, footsteps by ground (grass/wood/cobble), poof, hurt, animals (cluck/moo/chirp), fire, gate, chest,
  mail chime, UI click and error buzz. Verified by logging sfx calls per action in Chrome.
- Space puts the fight first: the one you're fighting (hit or hit by, 8 s), then glooms in reach, then the faced tile.
Tests: 62 pass.

## 2026-11-09 · Iteration 28 — felling, fruit, eating, movement polish

- thin_fall.png is now derived at build time from the pack's round felling sheet: per-frame crown angle measured on
  the round crown (-2, -4, -5, -32, -64, landed), the thin crown rotated about its cut, the swoosh pixels kept, and
  the burst made from the thin crown's own leaves following the round burst's profile. The thin tree is cut just
  under its crown and leaves stump_thin.png, a cut stump in the round stump's palette (rim, cut wood, highlight).
- Fruit from a tree falls with real gravity from the crown's edge (smooth at any frame rate; the pack's drop row was
  too sparse), bounces once, rests, then hops to the picker; the tree turns bare at once.
- Eating takes 1.6 s (progress bar, the food bobbing at your mouth), not possible when full.
- Animals amble at their own speed (chicken 1.6, cow 1.2, gloom 2.6 tiles/s): each step lasts most of the pause
  between steps instead of a 0.2 s hop.
- Two keys at once: turning first finishes the tile being entered in a straight line (as the server does), so no
  diagonal slide; 0 diagonal frames in Chrome over three turn patterns, display = server at the end.
Tests: 62 pass.

## 2026-11-09 · Iteration 29 — simpler needs, acting on the move, reach

- No more energy: no bar, no tiredness, no rest, no sprint cost; food is the only need. Beds stay as where you wake
  up after dying. Old saves load (unknown agent fields are dropped). Bots and the thinker updated.
- Quick actions (picking flowers, mushrooms, berries, fruit, small things; picking up) happen alongside walking or
  sprinting on the server: submit() tries them at once and the walk continues; timed ones (chopping) stop you, face
  the target, and a still-held direction walks on afterwards. Clients send the exact tile (x, y) so a walking
  client's lead doesn't miss. Held keys' auto-repeat no longer cancels a chop. Space stands you still while held.
- Reach +1: fights 3 tiles (spear 4), digging/using/feeding/milking 2 tiles; no auto-walking to targets ("too far").
- Hit animals flee for 4 s; bushes collapse into their own leaves; eating is three bites in 0.9 s with the food at
  the mouth (measured from the sheet: mouth at frame row 22), getting smaller.
Tests: 64 pass.

## 2026-11-09 · Iteration 30 — breaking, eating, placing by keyboard

- One breaking animation for everything (rocks, ore, fences, walls, furniture, structures): the sprite falls apart
  into 2x2 clumps of its own pixels that drift, land, bounce and fade (stone adds a little dust). The old squash is
  gone. Trees keep their felling sheets; small plants keep the pluck.
- Strike effects land on the tile actually worked on (the server reports each agent's target, `at`).
- Eating: a crisp 8x8 version of the food (2x2 → 1 px), raised to the mouth for three bites that take round chunks
  out of it, a small nod, crumbs of its colours falling to your feet.
- Keyboard placement: with a placeable item in hand, Space places on the tile in front of you and only there; the
  ghost shows it (green/red) and the panel says why it can't go there (red). A creature in the spot blocks it.
Tests: 64 pass.

## 2026-11-09 · Iteration 31 — small files, and an end-to-end suite

- Every source file under 300 lines (a test enforces it): sim tests by domain with shared helpers, asset tooling
  (pixel_art, derived_art), server (web_static, views, devtools), characters.js out of render.js, thinker (prompts,
  lessons), sim core (persistence, sessions).
- Hits land at once with a 0.4 s cooldown, so you can fight while walking; Space doesn't stop you when it hits.
- End-to-end suite (`uv run pytest -m e2e`, ~3 min): a fresh server on a temporary world, real Chrome, 31 scenarios in
  moving, gathering, building, living, social (two players, spectator, boat) and a random-input monkey; every test
  also fails on any page error. Checks both the screen and the server's truth.
- Found and fixed by it: "open chest" with empty hands only listed the contents (now takes everything; `list: true`
  to look); a catch-up slide could cut a corner (own and others' catch-up moves one axis at a time).
  Test-side issues fixed too (reading hints before a frame redrew; clicking a tile relative to a moving player).
Tests: 136 unit + 31 end-to-end, 3 full e2e runs green after the fixes.
- More end-to-end coverage (45 scenarios): houses/doors/shelter, glooms at night, wells, campfire cooking, signs,
  milking and feeding, coops, picnic bonus, hotbar/Q/bag/crafting by keys, zoom/help/F3, hover hints, sounds per action.
  Fixed: crafting cards still promised "walk to the workbench" though nothing walks you any more (now: "go within 2
  tiles of a workbench"). Added dev_needs for tests that need hunger. Two full runs green (3.7 min each).

## Iteration 32 — Space never stops you
- Hypothesis: holding Space to stand still (and slow work replacing the walk) feels like the game grabbing your sprite.
- Change: Space no longer halts walking. On the move it only does what's instant (hits, picks, pick-ups); chopping/mining/placing wait until you stand. Server: a swing sent on the move before the arm is ready is dropped (`too_soon`) instead of waiting and stopping the walk. Houses got a pack-exact roof, plank facade, windows, an opening door and chimney smoke (iteration 31's commit).
- Result: 143 unit + 46 e2e green (`test_space_never_stops_you` replaces the stop-to-chop test).
- Next: other structures from outside; keep looping e2e.

## Iteration 33: a playable demo on GitHub Pages
- Hypothesis: the server is pure stdlib Python, so Pyodide can run it unchanged in a browser tab and a static host can serve the game.
- Change: `browser.py` runs `GameServer` under Pyodide with in-page sockets (websockets/resource stubbed); `js/local.js` boots it and exposes a `LocalSocket` that `openSocket()` uses when present; the world is a SQLite file on IDBFS, synced every 15 s and on hide. `tools/build_pages.py` builds `dist/` (client + py.zip, local.js injected); `tools/publish_demo.sh` pushes it to a public repo (Pages isn't available for the private repo on this plan).
- Result: in headless Chrome the world is up ~2 s after load (Pyodide cached), tick p50 0.2 ms; the saved player is there after a reload. New e2e test `test_e2e_demo.py`; 147 unit tests green.
- Next: run publish_demo.sh once the public demo repo is approved.

## Iteration 34: selector, loot, quieter chat, faster tests
- The selector is four pixel brackets that glide between targets. Its box comes from the opaque pixels actually drawn for the aimed thing (drawImage is measured through flips and bounces), so trees, stumps, rocks, mushrooms and every mob are hugged with no per-type numbers.
- Chat no longer reports hits, only deaths. Lone thickets (a hedge tile that only reads well in groups) are no longer generated and are cleared on load; fiber comes from cutting picked bushes.
- Drops (creature and player deaths) hop out of the poof and bounce into the pile's own slots.
- Tests: pytest-xdist (`-n 6` in addopts). e2e 3m40s -> 47s, unit 3.8s -> 1.7s; the demo test saves directly instead of waiting 15 s.

## Iteration 35: item magnet and experience
- Server (`sim/progress.py`): piles within 1 tile of a living player fly into their bag once they've been on the ground for 1.2 s (`item_since`), as a `pick_up` event with `magnet`. Experience for felling (2), mining rock/ore (1/4), harvesting (2), crafting (1 each), hunting (chicken 2, cow 4, gloom 6); level n needs 7 + 3n; `xp` is saved and shown as `xp` and `level` in observations; an `xp` event carries where it was earned.
- Client (`js/xp.js`): pixel orbs burst from the source, hop, then home in on whoever earned them with a pitch-varied blip; the bar under the vitals leaves out orbs still flying, so it fills as they land; level-up arpeggio, sparks and a "Level n!" float. Magnet loot slides up into the player.
- Tests: unit (levels, xp sources, magnet delay and range) and e2e (ore -> orbs -> bar; a kill's loot comes to you). Coop test accepts the egg in the bag. 158 unit + 49 e2e green.
- Next: give levels a use (e.g. faster work per level, or recipes unlocked by level).

## Iteration 36: vitals in the pack's style; more animals
- Vitals: health uses the UI pack's wooden heart badges (full, half, empty); food is a meat on the same badge with a light face when filled; experience is the pack's wooden slider track with a green fill and the level on a cream knob. Both are drawn on canvases and only redrawn when they change.
- Wildlife (`sim/wildlife.py`, out of animals.py): the old rule kept 3 animals per online player in the whole world, one spawn every 10 s. Now about 16 farm animals are kept within 20 tiles of each player, arriving as herds of 2-4 just out of view; up to 3 glooms per player at night. When the world cap (80) is reached, the farthest animal outside everyone's area that nobody keeps (fed, milked, near a coop/trough/fence) leaves to make room.
- Result: QA world 4 -> 18 animals near the player after 90 s. 160 unit + 49 e2e green.

## Iteration 37: spawning after the sandbox classics (replaces iteration 36's herd quota)
- `sim/spawning.py`. Ticking: creatures only live in chunks within 48 tiles of someone awake; those chunks are kept loaded, nearest first, one every other tick, and new land is generated on a background thread (`World.prefetch`; inline in the browser demo) and installed exactly 3 ticks after it is asked for, so the tick never waits ~30 ms for world generation and the simulation stays deterministic.
- Animals belong to the land: a newly generated chunk gets a herd (80%: 2-5 hens or 2-4 cows on its meadow, placed inside the chunk so nothing cascades), persistent. Every 20 s each player whose 40-tile surroundings hold fewer than 18 animals may get another herd. Glooms: a spawn cycle every second at night, packs of 1-3, only in the dark (no campfire or fire within 6, not indoors), up to 5 around each player; despawned past 64 tiles at once, past 32 by chance. Every spawn is at least 16 tiles from everyone and only in loaded land. The global animal cap is gone (breeding stays limited locally).
- Result: fresh world, 15 s after joining: 56 animals in 26 chunks, worst tick 23 ms. 163 unit + 49 e2e green.
- Flake seen once (1 in 4 full runs): test_a_click_picks_on_the_move under parallel load; passed 4/4 alone and the next 2 full runs.

## Iteration 38: relief (hills, terraces, stone peaks, stairs)
- Generation: a height per tile, 0-3 (`gen_level`): two-octave noise over inland high ground, terraced; shores, water and the spawn meadow stay low; level 3 is bare stone peaks with boulders and ore. Stairs (`RAMP` flag): a pair of tiles cut into a south cliff that goes on either side, landing clear; each 6-tile stretch of a cliff row gets the first place that fits. 96% of plateau land (>= 20 tiles) has stairs down (seed 11, 256x256).
- Storage: chunks carry a third byte array (height | RAMP); chunks saved before relief load flat, so nothing already built ends up across a cliff.
- Rules: `World.can_step` (same level, or up/down stairs going south) in step, walk, move_to (A* edge check), creature moves; blocked messages say "a cliff (find stairs)" / "a drop". Agents get a `heights` grid in observations when there is relief, and a prompt line.
- Client: each level lays the pack's hill sheet (grass, darker grass, stone) as a blob layer over the tiles at least that high (edge tiles carry the cliff face); paths/tilled soil/floors redrawn on top; stairs are the pack's slope pieces with their grass background cut out at build time (stairs1/stairs2), drawn a quarter per tile; cliffs under stairs suppressed. Walking prediction respects cliffs (`canStep`).
- Also: dropped items hover smoothly (device pixels).
- Tests: unit (cliffs, drops, stairs both ways, move_to via stairs, generation has terraces/stairs/peaks deterministically, old saves flat) and e2e (keys: stopped by a cliff, up the stairs, screen and server agree). 169 unit + 50 e2e green.

## Iteration 39: natural slopes, and nothing on a hill's rim
- The pack's stairs (cliff caps with holes, floating planks) are replaced by a slope drawn at build time (`ramp_art`) in each hill sheet's colours: the hill's grass runs out through the cliff and fans onto the ground, lit, with contour dashes, the cliff face turning down its sides and tapering; its foot fades into the ground below (meadow for level 1, the lower terrace for level 2). Slopes every ~10 tiles of cliff (was 6), and only where the hilltop behind is walkable.
- Rims: a hill tile with any lower neighbour (diagonals too) is its rim, where the cliff or edge is drawn: not walkable (`World.edge` in passable/can_enter, client `edgeAt`), nothing generated there, nothing placed there; structures must stand on one level clear of rims. Slopes are the way through.
- Tests: rim rules, nothing generated on rims; 171 unit + 50 e2e green.

## Iteration 40: slopes as passes, four ways up; animals' diet
- A slope no longer juts out onto the land below (it read as a bump). It's a pass through the cliff: on the hill tiles beside it (and diagonally above), the slope counts as low ground, so the cliff ends in the hill sheet's own rounded corners and the rim curves in to meet the hilltop; the slope's ground runs from the hilltop's colour down to the land below inside the gap.
- Variants (per pair, by hash): soft grass with contours, a worn earth path winding up, stone steps, log steps. Pairs never touch (each 10-tile stretch keeps its last tile free).
- Climbing: a step up takes 60% longer, down 20% (server pace and client prediction), with a puff on each step up.
- Animals eat what grows and hay, not eggs, meat or milk.
- 174 unit + 50 e2e green.
- Reverted the slope art to iteration 39's (the user preferred it); kept: pairs never touch, slower climbing with a puff, animals' diet.
- Slopes: two variants (contour dashes; staggered with tufts). The foot has no border any more: base and dashes fade into the ground from halfway down, sooner at the sides.
- Slopes: one evenly lit plane (no bright patch mid-slope), fading only at the foot; variants: dashes, tufts, two grass steps, curved contours.
- Slope light: grows from the crest (no edge where the hilltop ends), dimmed along the walls, fading at the foot; 4 tones with a 4x4 ordered dither instead of smooth bands.
- Slope variant 5: contour dashes with lit lips.
- Borders: only the cliff face (lower ground straight south) is off-limits; north and side rims are walkable right up to the edge (nothing built there still). Walking lines up on the server's row/column, not the drawn position.

## Iteration 41: hop down off any edge
- Slopes on the north and side edges broke the 3/4 view (height only shows through the south cliff face), so instead people hop down one level off any edge they can stand on (Pokemon-style ledges); up still only by the south slopes. Animals keep to their level. Path-finding uses hops.
- Client: the same rule in prediction; the sprite arcs ~7 px over the edge, its shadow staying on the ground, a puff and a thud on landing.
- 176 unit + 51 e2e green.

## Iteration 42: fewer animals, rare slopes
- Too many animals (827 in the play world, mostly hatched chicks). Spawning: herds on 20% of new chunks (was 80%), 2-3 hens or 1-2 cows; top-up to 6 within 40 tiles every 45 s (was 18 / 20 s); glooms up to 3, in ones or twos. Breeding stops at 3 animals within 6 tiles (was 6). Play world thinned to at most 2 per 32x32 (125 left; backup kept).
- Slopes rare: one cliff row in five, one per 24 tiles of it (10 in 256x256, was ~75). Hopping down covers going down; up needs a slope.

## Iteration 43: underground
- Each level below is a region of the same world, 1,000,000 tiles east per level (layers.py): digging, building, items, saving work unchanged, and people on other levels are out of sight and earshot. Pickaxe in hand, X (dig_down, 3 s) digs a hole where you stand and takes you down onto a ladder in a small chamber; Space on a ladder climbs up, on a hole goes down. As deep as you like.
- Generation: rock (cave_wall) with caves whose noise scale grows with depth (bigger caves deeper), ore 3% -> 15%, rare mushrooms.
- Client: earth floor (soil sheet), rock as the pack's stone-hill sheet (faces to the south), dark with light around people, fires and under ladders (daylight from the hole), darker deeper; a fade through black when changing level; depth toast.
- Tests: unit (dig down/climb, levels, others out of sight), e2e (X down, Space up). 187 unit + 52 e2e green.
- Revised: no teleport. dig_down cuts a cave mouth (2 tiles sloping south); you walk down it: the cave under the mouth fades in around it (house-sized circle, drawn from the level below's own tiles) while the dark closes in, and the server moves you below at the deep end (the client predicts it, so the view just carries on). Up the ramp below reverses it. The client never drops its own player from view and resyncs from observations if far off.

## Iteration 44: a gentler way through a cave mouth
- Hypothesis: the descent still felt like a teleport. Measured per frame in Chrome: the server moves you below one step ahead of your glide, and the client snapped you 1.5 tiles forward when the level changed (tick and resync paths both).
- Change: the client carries your walk to the other level (levelShift in cave.js) instead of snapping. Three steps over about 5 tiles of walking, depending only on where you stand, so it looks the same from either level: the light dims and the other level shows through around the mouth (soft edge); in the mouth the world narrows to a pool of light where both levels blend (the level switch happens here); then the pool opens out. Mouth steps take twice as long (MOUTH_STEP, server + client), so it lasts about 1.4 s.
- Result: blend and tunnel values change smoothly every frame both ways, no position jump. 186 unit + 52 e2e green.

## Iteration 45: playable on a phone, published on GitHub Pages
- Touch (js/touch.js, only on touch screens): a floating joystick for the left thumb (four ways, sprint when pushed far), A/B buttons on the right labelled with what they'll do (A held keeps going, but never restarts work in progress: re-sending cut every chop short), Eat/Pick up when possible, Bag/Craft/Talk at the top, pinch to zoom, zoom 2 on small screens. HUD scales to fit; controls move above it when the screen is narrow; no page zoom/scroll/selection.
- Measured in emulated phones (390x844, 844x390): joystick walks, A chops a tree, HUD inside the screen. New e2e test_e2e_touch.
- Published the in-browser (Pyodide) build to GitHub Pages: sofianedjerbi/megastructure-demo.

## Iteration 46: a house-like step before the real underground
- User idea: an intermediate step where the underground shows at the same time as the surface, like walking into a house, then the real (dark) underground.
- Change (cave.js): approaching a mouth, the cave room below (its open tiles joined to the ramp, up to 5 tiles around, plus the rock walls around them) appears cut out of the land, outlined in the pack's ink, with daylight around it. On the slope both levels show at once (the level switch happens here, where both look the same). Walking on into the cave, the land around fades out and the darkness fades in. The pool-of-light tunnel step is gone.
- Result: per-frame values are continuous both ways, and the level switches only where both levels are fully shown. 190 unit + 53 e2e green. Showcase clip and text updated, demo republished.

## Iteration 47: layers, the level below always in view
- User: the underground shouldn't be a transient step but a layer; level n+1 always visible, for a layered depth feeling; showcase with 5 levels.
- Change (js/layers.js): down every cave mouth in view, the pit of the level below is drawn: the room under the mouth (round, ~7 tiles across), a shade darker (SHADE .3), sunk DROP .3 tile lower, its top edge and sides in shadow, outlined. Recursively 4 levels deep. A level is only cut where its own floor is bare, so its ramps, rock and things stay over the levels below. Walking down a mouth, its pit loses its shade and drop as you go (the level switch on the slope stays invisible). Also fixed: descents below level 1 had no transition (mouthNear only looked for ramps up there).
- Showcase: 4 mouths dug as a stairway (each a tile east and south of the last) in a QA world; clip walks meadow -> level 4 -> meadow. First tries were unreadable (stamped open boxes, deeper pits covering the ramps); cutting only bare floor fixed it.
- Result: 192 unit green; e2e 52/53, the one failure (building) passes 3/3 alone: flaky under load, not this change.

## Iteration 48: the level below only through holes
- User: hard to read; don't show the layer under the player unless there's a hole.
- Change: the level below shows only through a mouth's two tiles (darker, sunk, shadowed), never under solid ground; from below, the level above covers everything but the ramp's hole until you walk 2 tiles in, then fades. The cave-room pit (caveRoom) is gone.
- Result: each level reads at a glance: a bright ramp up, and a darker hole down showing the next ramp. 192 unit + 53 e2e green. Showcase clip and stills redone, demo republished.

## Iteration 49: always the level you're on; holes under what stands
- User: weird not to show the level the player is on; the player showed above trees.
- Change: no more land-above overlay underground: you see your own level, with a 0.45 s crossfade of the last frame when you change level. Holes are drawn right after the ground, before the y-sorted sprites (trees, people), so nothing is redrawn on top any more.
- Result: 192 unit green; e2e 52/53, the failure (test_a_click_picks_on_the_move) also fails on the code before this change, and passes 3/3 alone: flaky.

## Iteration 50: underground like a house
- User: looked wrong; lost; couldn't see the top layer; use border/corner tiles instead of cropping.
- Model: underground, the level above stays on screen, dimmed (a cave above is in its dark), and the part of the cave you're in (the open tiles joined to you within 7, plus the rock round them) is drawn over it with the soil sheet's and the stone sheet's own edge and corner tiles (caveview.js). The cave's dark covers only that part. Arriving it fades in (0.4 s); leaving it fades out over the new view. Only your part's sprites, people and fires show; the level below only through holes in it. The crossfade snapshot is gone.
- Result: each level reads at a glance in screenshots and the 5-level walk. 194 unit + 53 e2e green.

## Iteration 51: a world of blocks, seen from above (no ramps)
- User: after a series of mockups (scratchpad td2.py, five.py; showcase on Pages as a "design preview"): every layer is a floor you can stand on, like Minecraft; dig ahead or down; no ramps, jump up a layer; the tileset's own borders; underground, see what's above instead of walls.
- Change, server: dig_down digs where you stand: on a hill the ground comes down a layer with you; on the lowest ground (level 0 or a cave floor) a one-tile hole, you drop to the level below onto a floor cut for you. Walking onto any hole drops you (through holes under holes). Up: on the surface you jump onto ground one layer higher (two is a wall: dig into it, `dig` with a pickaxe takes higher ground down a layer); underground, under a hole, stepping toward open ground beside it on the level above jumps you out. move_to does the jump for an adjacent tile, and may end on a hole. Stairs (the RAMP flag), the two-tile mouth, ladders, MOUTH_STEP, ramp art: gone; old stairs load as plain ground, old ladders as floor. Hill edges are no longer off-limits (you stand on the top of the edge tile).
- Change, client: holes drawn with the pack's own edges (the hill sheet with its top cleared, on the tiles around the hole; the soil sheet as the floor below). Underground rock is drawn only as the stone sheet's edges round the caves; the levels above are stacked under your level (meadow first, each level down dimmer), so through the rock you see the caves over you and the meadow. Only your level's caves are dark (one mask of all its blocks; drawing block by block with destination-in had wiped each other out). layers.js and the cave "region" are gone.
- Result: 192 unit + 53 e2e green (the dig e2e was flaky when a natural cave lay north of the hole: correct behaviour, you walk into it; the test now puts rock there). Screenshots: surface holes read as pits, level 1 shows the meadow through its rock, level 2 shows level 1's caves dimmed.
- Next: terrain with real heights and biomes (more levels, mountains, plains, forests...).

## Iteration 52: biomes and real heights
- User: the real game should have heights, complex patterns, biomes, like Minecraft.
- Change (gen.py): biomes from moisture and ruggedness noise: plains (meadows, flowers, groves), forest (trees close together, fruit, berries, mushrooms), highlands (steeper rolling ground, boulders), dry lands (bare earth, grass patches, stones, lone trees), swamps (pools, thickets, mushrooms), mountains (stone, boulders and ore). Heights 0-12: rolling ground in steps of one layer (you jump them), mountain ranges in stone terraces with cliffs to dig through. Rivers wind from the hills to the sea and cut canyons. Sinkholes: holes in the meadow where a cave lies right under. Spawn is plains. Client: levels 1-2 grass sheet, 3-4 darker grass, 5+ stone, each layer a touch brighter so terraces of one sheet read as steps.
- Measured: 40 ms per chunk (28 before). Map of 800x800 tiles: all six biomes, lakes, rivers. Screenshots: mountain terraces readable, forests dense, spawn green.
- Result: 193 unit + 53 e2e green.
- Known: worlds saved before this keep their explored land; new land around it is generated the new way (seams at the edge of what was explored). Rivers sometimes loop (contours of one noise).

## Iteration 53: higher ground drawn higher (stacked levels, solid banded walls)
- User: going from layer 0 to layer 2 at once looks the same as one layer. Mockups (scratchpad slopes/cliffs.html, one page updated in place): stacked layers best; then "A2 solid"; then its variants: "A2a strata" chosen.
- Change (js/relief.js): each level k >= 2 is drawn 6 px higher per level (levels 0 and 1 in place, as approved): a copy of the block's ground cut to the tiles at least that high, lifted. Where a lifted level ends over lower ground its wall is painted down to the ground below: a band per layer (lit top row, mid, dark foot row) in that layer's own sheet colours (found by reading each sheet's south face: the grass sheets' face and the stone one sit on different rows), the sheet's ink at the foot. Everything on a tile is lifted with it (objects, people while walking between levels, items, fires, nameplates, the selector), and a click finds the lifted tile drawn under the pointer. Layers are rebuilt from the block canvas when a tile of it is redrawn.
- Measured: 60 fps on plains and over mountains (1400x900, zoom 2). Screenshots: terraces 1/2/3 layers up read as three heights; mountain terraces show stone walls.
- Result: 195 unit + 54 e2e green (test_a_click_picks_on_the_move failed once in the full run, passes 3/3 alone: the known flaky one). New e2e: higher ground drawn higher, clicks find it.
- Known: a sprite standing just north of a much higher tile is drawn over that tile's raised top (sprites are drawn after all the ground); a one-layer drop from level 1 to 0 is still the sheet's thin face while higher ones get a 6 px wall each.

## Iteration 54: underground you could not tell where you were
- User (fell into a hole on the islands world): "the screen is so ugly i don't understand a thing". Watched via ?follow=ben: the meadow above showed through the rock almost at full brightness (looked like where you are), while the caves you can walk in were darkened into brown pits: inverted.
- Change: what's above is faded (saturate .35) and veiled (.6) so it reads as over you; your level's cave dark is lighter (.36 + .03/level, max .55) and your light reaches 6 tiles. Now the lit earth is where you are, the faded dark is rock.
- Result: screenshot of ben's view reads at a glance (caves lit, rock dark, the hole beside him). World e2e green.

## Iteration 55: lag, borders, and back to the approved look underground
- User: "LAGGING", "weird borders", "the cave effect is totally absent", then "that dark view is so ugly, why does the whole surface turn into night, why don't I see the cave entrances we designed?"
- Measured (a copy of the islands world, headed Chrome, Retina): underground 23 fps (43 ms median, 200 ms worst) vs 120 on the surface. Toggling parts: the canvas filter (saturate) used to fade the level above cost it all (23 -> 114 fps). JS time was ~1 ms a frame: the cost was GPU-side.
- Change: no filter. The look underground back to the approved mockup: the meadow above in daylight, a shade dimmer (no night veil); your caves shaded a little (.45, deeper down a touch more), lit around you. Cave floors now round off along the rock (they counted rock tiles as floor: hard squares), the gap colour under the stack is the rock's, not black.
- The cave entrances from the design were never in the game: now a hole on the surface shows the tunnels leaving it below (js/entrances.js): an opening cut into the wall behind it (its top drawn on the wall's tile, through the cliff face), shade under the edge to the sides and front. The level below is fetched for holes in view; holes redraw when it arrives.
- Result: 121 fps underground (was 23). e2e green.

## Iteration 56: the height shows from the sides too (earth ledges)
- User: diagonal cliffs looked like boxes, the strata did not work on the sides, a +3 side looked like a +1; then (mockups on the one local page, benchmarked on a test map with 1-wide strips, a lone tower, nested rings, an L, staircases): "A looks perfect".
- Change (js/relief.js): every level is raised the same 6 px (level 1 too, so +1 always looks like +1). Each raised level is built from three parts: its body (a 6 px wall band: lit top row, dark foot row, the level's sheet colours), the ledge round the level above (3 px, in the sheet's own side-edge colours read off its west edge tile; a sliver between two of its own edges takes the top colour), and its own tiles cut to the sheet's own shape (never squares: the raised copies used to lift the ground under rounded corners). Worked out over the block plus a tile round it so ledges cross block borders. No dark ink line at walls' foot.
- Measured: 60 fps on plains and mountains; rebuilding all 12 visible blocks' relief 243 ms (~20 ms a block, only when a block's ground changes).
- Result: 199 unit green; e2e 54/55: test_random_play's server tick max (83 ms > 60) also fails 2/3 with this change stashed: chunk generation got slower with biomes (iteration 52), it runs inside the tick. Next: generate chunks off the tick.

## Iteration 57: the land is cells; a layer is half a tile; you fall
- User, over a long review on the one mockup page: the underground "levels", their darkness and transitions had to go ("no underground notion... exactly the same rendering as a hole in the mountains"); cave entries drawn as fixed art were wrong ("a cave is just empty space, entries are just intersection", "block removed notion shouldn't be hardcoded"); picked 8 px a layer out of four rendered sizes; asked for falls of any height with fall damage, going up one layer at a time only; "no need to keep compatibility".
- Change, server: a tile's relief is its column of 32 cells, a bit each, solid or empty (gen.col_*, chunks.py; chunk format 4, older saves are made anew). No roof, headroom or level byte: floor, top, the heights you can stand at and "covered" are read off the column. An agent has a height z. A step: where the cell at body height is solid, a jump up onto it if it is ground; where it is empty, in at your own height and down onto the ground under you (Movement.landing), a fall beyond 3 layers costing 5 hp a layer (Movement.fell). dig takes out the cell in front of you (a step cut down or a tunnel), dig_down the one under your feet. move_to never takes a fall that hurts, except the one step asked for.
- Change, client: cells.js mirrors the server's rule; a layer is 8 px, a side wall 4 px a layer. caves.js: the cave you are in (the covered tiles you would walk onto from yours) is one cached overlay a block drawn over the untouched hill (no relief rebuild: entering a cave used to redraw whole blocks, and every roofed tile each frame); openings are drawn wherever a hill's empty cells show on a face (south: in the wall; east/west: in the side wall, open outward; north: only a shadow from under the hill's edge), as wide as the tiles side by side and as high as the cells. X, Y, Z on screen.
- Mistake: my screenshot scripts joined the server the user was playing on; dev_time moved the clock back and froze their movement cooldowns ("slow as fuck, sprint does not work"). dev_time now only goes forward; scripts only ever run against a copy on another port.
- Measured: walking in and out of a cave 60 fps, no frame over 16.8 ms (was a visible hitch). 219 unit green; e2e 71/72 (test_muting_stops_new_sounds fails 1 run in 3 on its own: it counts a sound that ends).
- Not done: generated caves are still thin noise tunnels along hill feet; the server keeps one object a tile (a thing on a hollow tile sits on its lowest ground); creatures only know the lowest ground. Next: generate real caves (chambers and passages as empty cells), chunk generation off the tick.

## Iteration 59: cave entries round a corner; side entries; the demo starts in the cave showcase
- User: at a corner the black opening and its shadow on the two faces "should be connected"; an entry in a pit's side was drawn over the ground in front of it; "sideway angles looks pretty rough"; "upload this whole demo online".
- Change (js/caves.js drawFace): at an outer corner the hole in the south wall runs to the one in the side, in an inner corner the side's runs up to the wall's; shadows are collected a px each for the block and shaded once, so two that meet are one. A side opening is the wall's opening turned: LEDGE px a cell (lowest outermost), rimmed and darker in under the hill, corners rounded. Each face is cut off where higher ground further south is drawn over it.
- Change (demo): `showcase.py` builds the cave showcase into a new world (what was a scratch script), a world can name its spawn point (meta `spawn`), the in-browser demo opens world "caves" with it. The demo had stopped booting: `web_stamp()` looked for web files that are not in the in-page build.
- Result: 270 unit green; cave, relief and demo browser tests green (the full browser suite was not run). Demo republished.

## Iteration 60: weak machines (one picture a block, the demo's server in a worker, faster land)
- User: "Game show poor performance on poor hardware. Optimize it, async, parallel, multicore.. and simply make things simpler."
- Measured first (Chrome with the CPU slowed 4x and 6x, a profile and a count of what each frame paints). The client's JavaScript was not the problem (60 fps, 85-90% idle). What a weak GPU and little memory pay for was: every block drawn as a canvas per level each frame (about 60 block-sized draws a frame, 114-264 MB of canvases after a short walk, never freed), and in the demo the Python server on the page's own thread (walking into new land: frames up to 433 ms, 10 over 100 ms in 9 s).
- Change, client: a block's raised levels are painted into one picture when it is built (relief.js; ground + that picture = 2 draws a block); blocks left more than a block outside the watched area are forgotten (state.js); the canvas uses at most 2 device px a CSS px, and drops to 1 when frames stay over 30 ms for 4 s on a dense screen; the room search (a flood fill of the view twice a second) is skipped when no wall is in sight.
- Change, demo: the Pyodide server runs in a module worker (js/local_worker.js); the page's sockets are messages to it.
- Change, land: the noise lattice points and repeated fbm lookups are cached (gen.py): 55.5 -> 21.7 ms a chunk, 72 chunks checked byte-identical to before.
- Result: block-sized draws a frame 62 -> 15, canvas memory 114-264 MB -> 4-20 MB (bounded). Demo at 4x slowdown, running into new land: 47.5 -> 59 fps, worst frame 433 -> 50 ms, none over 100 ms. Native server while land generates on its thread: tick max 0.6 ms, so no process pool. 270 unit green; browser suite 83/84 (test_e2e_swim's shore-foam check failed once in the full run, passes alone).
- Not measured: a real weak device (only CPU throttling here, which does not slow the GPU). Not touched: the music (a 36 MB wav decoded whole into memory: likely the next cost on small machines).

## Iteration 61: walking froze on quick turns; the demo makes land between ticks
- User: "Character moving is buggy, sometimes freezes.."
- Measured (a script holding and releasing keys, the sprite's position sampled every frame, against a copy server): walking straight and rolling from one key onto the next were fine. Letting go of a key and pressing another within a few ms stalled the sprite 150-280 ms at half the turns: round corners 3.7 tiles/s walking (5 is full), 5.4 sprinting (10 is full); turning right round 2.8 and 3.0. Yesterday's code (a worktree at f12a744) does the same: not from the performance work.
- Cause: on release the client finishes the tile it is entering (move_to, with `pred`); the new walk then replaced that move_to on the server before its step was made, so the server walked on from one column and the client from the next, and the client ignored the server's position until `pred` ran out (0.6 s).
- Change: `walk` takes `from` (the tile you were stepping into): the server makes that step first (sim/movement.py). keyboard.js sends it when a walk starts with a step still unconfirmed; turning right round cancels that step instead.
- Result: corners 5.0 walking and 10.0 sprinting, right round 4.75 and 8.9, no stall over 120 ms but one of 133; client and server end on the same tile every time. Random key mashing on hills and round the caves: no freeze.
- Also: in the demo (no threads) a new chunk was made inside a tick. It is now made a row at a time in the time left before the next tick (gen_chunk_steps, World.work): ticks stay at 0.2 ms while 69 chunks are made. And the commit before this one broke test_web (local_worker.js not in its list): fixed.
- 273 unit green; browser suite 83/84 (test_muting_stops_new_sounds, the known flaky one).

## Iteration 62: your screen walks you, the server retraces it (phones: sprinting stopped at every tile)
- User: "Still glitchy on phone while going fast. Especially in water it is literally square per square. Overworld sprinting on phone is so bad."
- Measured (a thumb-stick script, the sprite sampled every frame, copy servers; the phone can only reach the online demo, the play server listens on 127.0.0.1). Water with the stick pushed far (sprint): standing still 33% of the time, 15 stops in 4 s: the server never sprints in water, the screen glided at sprint speed, got a tile ahead and waited, every tile. A server that cannot keep 10 ticks a second (ticks of 90-170 ms): walking 13% still, sprinting 9%, a stop every tile. In the demo on a desktop the ticks already reach the page up to 165 ms apart. Cause of both: the screen was only ever allowed one tile ahead of the server's last word.
- Change: the screen walks you itself (new js/walk.js): each step at the server's own pace (swimming is never a sprint), looking at the land as the server does, without waiting. It tells the server the tiles it turned at (`walk`'s `from`) and stopped on (`stop`'s `at`), numbered; the server makes them first, in order, a stride a tile (Movement.follow, Agent.via) and says how far it got (`vn`). More than 2 tiles ahead of it the screen slows down, at 4 it waits; where the server could not follow, the screen goes back to it. Let go and straight back: the tile is not made (`cut`). What you do after stopping waits until the server is on your tile. The stick's sprint line is sticky (14 px).
- Result (same script): water, stick pushed far: 5.0 tiles/s, no stop (was 33% still). Server too slow: no stop walking or sprinting, you move at the server's pace (3.4 and 6.6 tiles/s), one 67 ms pause in 9 runs. Uneven ticks (20-110 ms): full speed, no stop. Keyboard: corners 5.0 and 10.0, right round 5.1 and 10.4, taps and squares unchanged; screen and server end on the same tile in every run.
- Seen on the way, not changed: land the screen already holds is only asked again every 30 s, so a big change just outside your view (my test's pond) can be stale for that long.
- Not measured: a real phone (frame rate there is still unknown).

## Iteration 63: behind a mountain, a circle round you is seen through it
- User: "When going behind huge Walls and mountains, add a x-ray aura circle around the player, fading around him."
- Before: behind higher ground you were cut at its edge (clipBehind): behind a cliff of 2 layers or more, gone.
- Change (new js/xray.js): when the ground in front (south) covers more than half of you (8 art px starts it, 14 is whole), a circle of 3 tiles round you shows what is behind: the land painted again, small, with the ground in the way cut down to your height (its footprint the earth colour of its walls, outlined: still a wall; a single layer up, a step you can jump, only shaded), you and whoever is beside you drawn whole, trees and creatures standing on the cut ground faded out. Only where the hill really covers what is behind it; the rest of the screen is untouched. It fades in rings (pixel steps, not a blur) and comes and goes in about 0.2 s. Nothing is cached or rebuilt: 0.12 ms a frame.
- Result: steady at full strength while sprinting along behind a wall (120 frames, min 1.00); gone two tiles out from behind a 4-layer hill. 277 unit green. Browser suite, full run: 85/88 after adapting the "a hill hides you" test (it now turns the circle off); the three that failed (boat launch, random play, and the known mute test) are not the same ones as the run before (old mossback) and the first two pass alone, the boat one 4 times in 4: the full run is flaky on this loaded machine.
- Not done: walls people build (they are a tile high, sprites: they never hide you whole). Terraces rising a layer a tile never cover you enough to start it.

## Iteration 64: half the paint a frame (water put together small; nothing painted where there is nothing)
- User: "Further improve performance."
- Measured first. JavaScript is not the cost: at a 6x slower CPU the page is 88-97% idle in every scene. What is left for a weak phone is paint, so I counted what each stage of a frame paints on a phone-sized screen (844x390 at DPR 2), in screens: 7.8 on a field, 10.0 on a shoreline, 9.8 over the sea, 10.9 over the sea at night. The water alone was 6.75 screens: its bottom, the bottom again in sliding strips, two nets of light (added), the tint, two layers of waves, each the size of the screen wherever a block in view held any water. Under every block the old animated water was still painted (1 screen), though the new water's bottom covers it everywhere. A block's cave overlay and its raised-ground picture were painted whole, mostly empty (2 screens on the showcase field for the caves).
- Change: the water is all art pixels, so it is put together a pixel an art pixel on a canvas the size of the view (16x fewer pixels at zoom 2, DPR 2), only inside the box of each block's water, and blown up onto the screen once (water.js). The old water under the blocks is gone (render.js). The raised-ground picture and the cave overlay are painted only where they have something (relief.js: the box of the raised tiles, their ledges and walls; caves.js: round the hollow tiles).
- Result: paint a frame 7.8 -> 3.0 (field), 10.0 -> 3.0 (shoreline), 9.8 -> 3.0 (sea), 10.9 -> 4.1 (night sea). A whole frame, painted and flushed, at a 4x slower CPU (headless Chrome, so painted by the CPU): 13.4-15.2 ms -> 6.8-7.8 ms in the five scenes. The picture is the same to the pixel: 26 screenshots with time frozen (13 scenes: sea, shores, river, pond, field, hills, caves from outside and inside, night; desktop and phone size), old code against new, 0 pixels differ (the references themselves repeat exactly). 277 unit green; browser suite 87/88 (the known mute test); a new test holds a frame over water under 4.5 screens of paint.
- Seen, not changed: a block built before its neighbour has arrived shows a column of flat ground along that edge until it is rebuilt (one screenshot caught it, old code and new alike). The music is fetched whole on the first tap, 37.5 MB, and decoded to 75 MB of memory (boss.wav: 11.5 MB, 23 MB decoded, when a fight starts): on a phone that is now the largest cost by far, and it is the music session's (not touched).
- Not measured: a real phone. Headless Chrome paints with the CPU; a phone's GPU pays for paint differently, but less paint is less work on both.

## Iteration 65: the music is streamed; the x-ray circle shows water and comes only when you are hidden; three glitches
- User: "optimize the music without touching it; fix the glitches; the xray aura shouldn't activate on very small edge, only when it makes sense; the xray circle effect is not handled correctly" (two screenshots: swimming in a channel between two 12-layer plateaus).
- Music, measured: music.wav was fetched whole on the first tap (37.5 MB) and held decoded (75 MB at 32 kHz, 113 MB once the browser resamples it to 48 kHz). Change: the build cuts each loop into 8 s pieces, lossless FLAC, each with 50 ms of its neighbours at both ends (tools/build_audio.py; soundfile added to the dev tools); the player schedules them one after the other on the context's own sample grid, fetches each a second before the piece before it starts, and lets it go once played (audio.js). Muted, it stops fetching and comes back at the piece it was in. The first piece now starts with the effects' download, not after it.
- Music, result: the pieces hold exactly the samples of the old file (compared). First note after 596 KB, not 37.5 MB; 2 pieces held (about 6 MB); 21 MB over a whole loop instead of 37.5 (boss: 5.5 instead of 11.5). Joins: three pieces scheduled as the player does, rendered offline in Chrome, against the same 24 s played as one buffer: the difference at the joins is 6e-8 (float rounding) at 48 and at 44.1 kHz; 8.000000000 s between the starts in the real player.
- X-ray, the screenshots (reproduced on a copy of the play world, at the character's own tiles): (1) the circle copied the land's picture, which has no water in it (water.js paints the water under the land): swimming, you were shown on the plateau's top. It now takes the water from the water canvas of the frame. (2) It looked only 4 rows south for ground to see through; a 12-layer plateau starting 5 rows south is drawn up over you all the same: the circle was cut off in a straight line. It now looks as far as such ground can reach (12 rows).
- X-ray, when: it came from 8 px of cover (a 2-layer step). Now it is the share of your body that is hidden, over the two columns you stand across: nothing under 75%, whole at 95%, and only after 0.15 s. Measured: walls 1 and 2 layers high right in front: never; 3 and more: yes; a wall 5 high, a tile further back too; walking or sprinting past a lone pillar 8 high: never; standing behind it: yes.
- Glitches: (1) a block's relief redrawn while it was first being built dropped the note to rebuild it: a column of flat ground along a block's edge when its neighbour arrived just then (relief.js; a test reproduces it). (2) A spectator's queue drops events past 2,000 waiting, without a word: my 5,000-tile test pond left the page with old land for up to 30 s. It is now told to ask for its land again once it has caught up (views.py `resync`). (3) Dying, a dev teleport or doing something else did not forget the way a screen had walked (iteration 62): the server could walk on to an old tile afterwards (core.py interrupt).
- Tests: 279 unit, 91/91 browser (the mute test that failed one run in three counted a sound that ended: it now compares when each sound last started). New: pieces are the same samples and wrap the loop; streaming and mute; water in the circle is covered by the frozen screenshots only; the lost rebuild; resync on both sides.
- Not done: the sound effects are still 14.5 MB of wav fetched on the first tap (FLAC would halve the download, not the memory). A lossy codec would take the music to about 5 MB, but it would no longer be the same samples.

## Iteration 66: the x-ray circle slices every side (no wall faces inside it)
- User (a screenshot, swimming at the corner of a channel): "inner walls are sometimes reappearing".
- Reproduced on the test server (a channel of water with 12-layer rock on every side): the circle cut only the ground south of you. A wall beside or behind you, still at its full height in the circle's picture, was then drawn with its face all the way down to the cut ground south of it: twelve bands of wall where there is none, as soon as a tile beside you was high and the one south of it was cut.
- Change (js/xray.js): inside the circle the land is sliced at your height on every side. Everything higher is its plain earth footprint with an outline along the open ground; what is at your height or lower is as it is. No face of higher ground is ever drawn in it.
- Result: the channel corner, its middle and its east arm show the water and plain footprints (screenshots before and after). A test samples the wall tile beside you: one colour (it fails on the old code: bands). 279 unit; browser suite 90/92 in the full run: the new test's first, too strict colour check (fixed, 21/21 of relief and caves after), and the hit-cow test, green alone.

## Iteration 67: the x-ray circle is only the hidden ground
- User, after iteration 66: "the xray circle shouldn't be visible where area isn't hidden also". Slicing every side had turned the whole circle into a brown footprint wherever rock stood, hiding nothing or not.
- Change (js/xray.js): no rock is painted at all. The circle shows the ground that rock is drawn over, where you could be on it (your height, a step up, or lower), with its water, and a dark edge with a little shade where that ground meets rock. Rock that hides no such ground, beside you, behind you or in front, stays exactly as drawn. A tree or a creature fades only where it stands in the way of ground the circle shows.
- Result: in the 12-layer channel and at the user's plateau spot the circle is the channel alone. Test: the wall tile beside you is the same pixels with the circle on or off, the hidden channel behind you is not. Relief and cave browser tests 21/21.

## Iteration 68: the x-ray circle is cut to the pixel
- User (a screenshot at the edge of a channel): "it still shows the circle where the area is already visible, creating weird artefacts".
- Cause: the circle was cut out in whole tile columns of rock plus 8 px each side, from each rock tile's top down to the ground. Real cliffs have rounded edges and ledges of 4 and 8 px, so the cut-out also covered ground and water that show anyway; there the plainly painted ground replaced the real picture (seams), with the dark edge line I had added along rock, and translucent squares in the fading rings.
- Change: the rock in the circle is a picture made from the land's own shapes (relief.js: levelShape, shared with the relief builder; rockOf: the levels from two over where you stand, at their lifts, with their ledges and walls, a block at a time, a few ms a frame, kept while the circle is on). The plainly painted ground is kept only where that picture is. No edge line.
- Result: at the edge of the play world's channel only the strip under the plateau's edge shows through; the open channel is untouched. The land itself is drawn as before the refactor: 8 frozen screenshots of hills, caves, fields and shores, 0 pixels differ. Tests: ground that already shows is the same pixels with the circle on or off, ground under the wall's top is not. Relief and cave browser tests 22/22.

## Iteration 69: reach is a circle, and height is distance
- User: "the height should count as a distance preventing us from: breaking blocks, killing mobs and picking up items if too high. Respect the original range in a circle around the player."
- Before: reach was a square on the map (so many tiles each way, diagonals included) and height did not count: a tree at the top of a 12-layer cliff could be chopped from its foot, a cow at the bottom hit from the top, loot on a ledge flew to you.
- Change: one rule, the same on the server (sim/movement.py: near, reach) and in the browser (intent.js: reaches). Something is within reach r when the straight line to it, height included, is at most r tiles and a half (the half: to the far tile's edge, so the old range holds straight ahead and its near diagonals; only the square's far corners go). A layer is half a tile, as it is drawn. The ranges are the old ones: use 2, fists 2, spear 3 on your screen (the server allows a tile more for a walking screen's lead), loot 1, give 2. What is on a tile is at its ground nearest your own height; people at their own height, creatures on the lowest ground. Digging into a wall you face is at your own height, whatever stands on top.
- What that gives, next to you: breaking, placing, using, hitting with fists: up to 4 layers up or down (2 tiles); a spear 6; loot comes from 2 layers, not 3. Two tiles off: 3 layers. Creatures follow the same sense: a bite reaches 4 layers, no further (a pincer at the foot of your ledge cannot hurt you).
- Browser: what is too high is not offered (the action list, the keyboard's pick of what Space does), a placing ghost turns red, and Space or a click says "Out of reach: too high up, or too far down" instead of "Too far".
- Tests: tests/test_reach.py (the circle's corner, a flower 6 and 8 layers up, placing, the wall at your height, a cow in a pit, loot on ledges, the pincer); a browser test (a flower 6 layers up is not offered and Space says why; 2 layers, picked). One old browser test had its tree on the square's corner (2, 2): moved to (2, 1). 284 unit; browser suite 93/95 in the full run (old mossback and the swim sounds test, both green alone, the latter 4 runs in 4).

## Iteration 70: creatures stand on the land as people do (one rule for every body)
- User: "make mobs able to go up and down same way as player, this should be abstracted. Same layering pattern (layer handling etc)."
- Before: a creature had no height. It lived on the lowest ground of its tile and stepped only onto ground of the same level (world.can_step): one layer was a wall to it, a tusker rammed a step, cows never left their terrace.
- Change, server: sim/bodies.py (Bodies, a mixin of the simulation) is the layering for anyone who stands in the world, a person or a creature: the height it stands at (z, on both; saved with both), `landing` (a jump up a layer where there is room over it and over your own head; a step in at your own height otherwise, coming down on the ground under you), `step_onto`, `in_cave`, `safe_step`, and reach (near, with height). Movement keeps what is only a person's (water, boats, pace, falls that hurt, picking up); Animals keeps what is only a creature's: `_creature_move` now takes any step a person could, except through a door or gate, onto someone, or down a fall that would hurt (more than 3 layers). So creatures hop up a layer, come down up to three, walk in under a hill at their height or over it on top. Old Mossback (three tiles wide) still keeps to the level; the wisp flies over the top of whatever is there. A creature saved before this has no height: it stands on the lowest ground, as they all did.
- Change, browser: creatures are sent with their height. The jump's puff, the hop down's arc and its landing are drawn for any body (characters.js). Someone on the hill over the cave you are in is not drawn at its floor (caves.js unseen).
- Tests: tests/test_bodies.py (a cow up a layer, not up three; down three, not four; a chicken in under a hill and another over it; a tusker charges up a step and hits you; height saved, and an old save without it). Browser: a tusker comes up your step and is drawn lifted. 290 unit; browser suite 95/96 in the full run (a click-while-walking test, green alone 3 in 3).
- Tests made steady on the way (they failed some runs in the full suite, none from this): the boss test waits for the boss to be asleep instead of 0.9 s; the swim sound test lets the last stroke finish; the swim layer test looks at the block the pond is in.
- Not done: creatures do not look for a way round or up to you (they step toward you, as before, now over steps); farm animals wander over steps too, so a terrace no longer pens them (fences do).

## Iteration 71: a sprite behind a ledge is cut along the ledge's own edge
- User (a screenshot: their character at the corner of a ledge, cut straight across at the collar): "corner angles aren't transparent ??"
- Reproduced (a ledge a layer high west and south of you, its edge in steps): behind higher ground a sprite is clipped to the hill's top edge (relief.js clipBehind), and that edge was one straight line a tile column, a px under the tile's top. The ledge's drawn edge is set in a few px from there and rounded at a corner: between the cut and the edge, and all round the corner, the ground behind showed but not the sprite.
- Change: the cut follows the ground's own shape, an art px column at a time: for every layer of the higher ground in front, the first drawn row of its sheet cell (the cells the land is built from). Nothing is redrawn.
- Also: the x-ray circle now comes from two layers right in front of you. Measured on the same map, two layers leave only the ears (I had taken the body for 22 px over the tile's foot; it is 20), and it stayed off at 73% hidden. One layer hides you to the waist: no circle, as before.
- Result: before and after screenshots at the ledge's corner; a test reads the cut strip by strip in your own tile column (it was -7 px all the way across; it now rounds off down the corner). Tests: 291 unit, browser 97/97. On the way: the relief test file passed 300 lines (the x-ray tests have their own file now), and the click-while-walking test raced its own reading of where you are (it failed some full runs): it clicks the flower's tile itself.

## Iteration 72: the hop (a jump that looked wrong, twice)
- User: "now improve the jumping animation. it looks weird"; then, of my first rewrite: "jumping still looks bad..".
- First rewrite, wrong: I judged it on poses I had placed by hand (a run-up, a crouch, an arc, a landing, the sprite squashed and stretched). Seen as the browser really shows it, frame by frame (a screencast of walking up a step), it popped up, hung, and popped down: the pose switch and the stretching each moved the sprite 2-3 px in one frame, and scaling a 16 px sprite smears its pixels.
- What the frames showed of the old one too: the hang. Up a layer the step took 300 ms instead of 200 (the server's SLOPE_UP), the screen slowed down for it, and the body sat near the top of its arc for most of that, legs walking; then a 2 px snap.
- Change: js/jump.js. A hop is one arc over the straight line between the two heights, from the middle of a tile to the middle of the next, high enough to clear the edge (2 px going up, 1 coming down). The pose is the one it took off in; nothing is scaled. Its shadow is on the ground under it (the lower ground until the edge). Dust where it leaves the ground and where it lands. The same for creatures. And the screen no longer slows down for it (walk.js): a hop takes the time of a step; the server, a tick behind after it, catches up (iteration 62's lead).
- Also: someone between two tiles is behind the hill in front by the ground they are over, not the lower of the two (relief.js clipBehind): hopping onto a ledge in front of you, you were hidden until you had landed.
- Result, on the real frames: up a step, 11 frames of even rise and fall (183 ms), no pop; onto a ledge in front, over its edge and down on it; off it, out and down. Walking up a step and on: 3.1 tiles or more in 0.7 s (under 3 before). Tests: the arc's shape, the shadow, the pace. 293 unit, browser 98/98.

## Iteration 73: /coords and /grid
- User: "make coordinates showable with /coords command system and /grid to show grid for debugging".
- The chat line already sent any /word as an action to the server (/dig dir=N). Change (new js/debug.js): /coords and /grid are done in the page, each on until typed again and kept between visits. /coords: X, Y and the height Z you stand at, top right, with the tile you aim at and its height (it was always shown; it is now off until asked for). /grid: every tile outlined where it is drawn, lifted with its ground, its height written in it, and the borders of the 32-tile blocks in orange. Listed in the help.
- Tests: a browser test types both, and /dig dir=N to see the rest still goes to the server. 295 unit, browser 99/99.

## Iteration 74: everybody stands 3 px up in their tile
- User, with /grid on: "the character sits at the bottom of a tile. it should sit at its center. what do you think?" I showed three rows of the same seven situations (now; 3 px up; feet at the tile's middle) and said: not the middle (the body moves three quarters into the tile above, out of line with the rocks and crops of its own row, onto the trunk of a tree to the north), but 3 px up. User: "Go with the 3px lift. ensure every mechanics are adapted, item picking, also same should apply to mobs".
- Before: the sheets put the feet 2 px over the tile's bottom: the shadow on the line between two tiles, hanging off a ledge's brink.
- Change: one rule in one place (relief.js: STAND = 3, bodyY, and UP, the same in tiles). drawEntity draws every body through it: people, farm animals, wild creatures, Old Mossback, the dying. What goes with where a body stands follows: its name, speech, emote, progress bar and night glow; the dust of its steps and hops, its splashes and wake, crumbs; what flies to it (loot, orbs, a picked plant); the cut behind a ledge (its feet line); the x-ray circle (how much of you is hidden counts from your feet: a layer hides your legs, two leave the top of your head and bring the circle; its middle); the pointer (the lower half of the tile above someone is their head and shoulders: pointing there means them; tileAtScreen says how far down the tile). A boat stays where a moored one is drawn. Nothing on the server depends on it.
- Result: a sheet of the player on open ground, between rocks, at a cliff's foot, on its brink, beside a cow, a chicken and a tusker, and swimming: all on one line, shadows inside their tiles. Tests: the sheet cell of a person and of a cow is drawn 3 px higher; pointing over a cow's tile. 295 unit, browser 100/100.

## Iteration 75: you eat while you walk
- User: "add the ability to eat while moving".
- Before: an agent did one thing at a time. Eating took 0.9 s and replaced the walk: you stood still for every bite (the tool's own comment said so).
- Change, server: an agent has a second slot, `aside`, for what the hands do while the feet do something else (constants.ASIDE: eating). submit() puts such a tool there: a walk under way goes on, and a walk started later doesn't end it; anything else you start (chopping, a fight) stops the meal, as it stopped the walk; dying, leaving and being moved stop both. step() advances both; wait() marks the length on the action being stepped. Clients are told who eats what (`eats`) and get its progress.
- Change, browser: E on the move doesn't stop you (the meal has its own state on your screen, so setting off or turning doesn't end it there); the bites, the food at the mouth and the crumbs are drawn on a walking character, yours and other people's.
- Tests: unit (eating beside a walk, a walk begun during a meal, a tree chopped: the meal stops); browser (E while walking: no pause over 80 ms in 1.6 s, 7 tiles gone, the bread eaten; others are told walk + bread; a meal begun standing goes on as you set off). 296 unit; the living tests 10/10.

## Iteration 76: the bar is ten slots; I for the inventory, C for crafting
- User: "improve the UI: only 10 inventory slots, remove 'bag' and crafting table from the ui, map i to inventory and c to craft".
- Before: nine slots, then a "bag" slot (B) and a crafting-table button (C) on the same row; what did not fit the nine was in the bag.
- Change (ui.js, keyboard.js, main.js, touch.js, index.html): the bar is ten slots and nothing else, keys 1 to 9 and 0. An empty slot's key, or the key of the slot in hand again, is empty hands (so 0 still empties your hands while the tenth slot is empty; ` always does). I opens the inventory: everything you carry, by name, the ten of the bar first, then "not on your bar"; picking one takes it in hand, and one from beyond the bar comes onto it. C opens the crafting as before; its button is gone (on a phone the buttons at the top stay: Items, Craft, Talk). B is no longer a key.
- Read as a change of the interface only: nothing limits what you can carry. More than ten kinds of thing still go to the inventory, beyond the bar.
- Tests: the UI test for the bag rewritten for this (ten keys, no buttons, 0, B dead, I, picking from beyond the bar, C). 296 unit, browser 101/101.

## A fall is a fall: its own time, wind, dust, and what it cost shown where you land
- User: improve the "falling from high heights" effect: noise + animation.
- Before, on the real frames (a screencast of walking off towers of 3, 4, 8 and 12 layers): a fall was a hop. One arc in the time of a step (twelve layers, 96 px, in a fifth of a second, the screen jumping with it), the thud of a one-layer hop, and nothing to say it had hurt: the server's `fall` event was not read at all, only the hearts changed.
- Change (js/jump.js): a drop of 3 layers or more is a fall. You walk to the edge on the ground you leave; from the edge you come down by your own weight (1000 art px/s2), however long that takes (0.22 s for 3 layers, 0.25 for 4, 0.35 for 8, 0.43 for 12: measured), legs going (two frames of the run in turn), your shadow waiting on the ground below, your name and what you say falling with you. The camera comes down with you (render.js). Landing: dust thrown out low to both sides, more the further you fell, smoke, and a thump (the hop's for a short fall, the falling tree's from 4 layers). A fall that hurt is shown where you land, not when you stepped off: you flash, the number rises, you bounce, the ground shakes for a third of a second, and you are heard (state.js keeps the event until then).
- Noise (audio.js fallWind): the wind in your ears, rising and swelling with your speed and cut when you land. It is made in the page (noise through a band), not a sample: it has to follow the fall, and adding a sample means a full audio build while the music is being worked on. The thumps and the hurt are the existing samples.
- Found on the way, and fixed (relief.js behindHill): since yesterday every puff of dust, spark and splash on level ground went unseen. The check for "behind higher ground" compared 0 with less than 0 where the ground is level, and looked a row too far: anything not on the very top line of its tile was hidden, everywhere. It now needs higher ground, and its top edge over the spot.
- Tests (tests/e2e/test_e2e_fall.py): eight layers: 0.28-0.44 s in the air, each frame further than the last, the camera on you, the wind on then off, dust at the landing, the flash, "-25" and the shake; two layers is still a hop, three a fall; dust is painted on level ground and hidden under a ledge's top. 297 unit; browser: the fall, moving, relief, creature and living tests 44/44; the full run 100/104 with the machine busy (sound and swim tests, 7/7 alone).
- Not done: someone whose ground is dug from under them still drops at once; other people's falls are shown from their walk as it reaches the page (the same code, a little late).

## Iteration 77: the x-ray circle is the land's own painter, without the rock in front
- User: "the borders of the mountain I'm under are still visible; mobs should fade, not disappear instantly"; then a screenshot (a canyon between two 12-layer plateaus): "layer going above visible layers shouldn't be visible, the xray should eliminate that also; find a reliable way to prevent all of that"; then "investigate the xray effect in every aspect and ensure there's no visible artefacts".
- Stepped back. One cause behind every artifact since iteration 63: the circle painted the land with its own, simpler drawing (a tile's flat picture, plain wall bands, a cut-out worked out apart). Wherever that differed from the real painter there was a seam, a square, a stray edge. And it could only show flat open ground: in the canyon the cliff behind you stayed under the front plateau's top layer.
- Change: one rule. In the circle the land is drawn without the rock in front of you (two layers or more over you, south of your row), and nothing else changes. The land's painter (relief.js reliefSteps) now works on any rect of tiles, with or without some tiles left out; shapes and colours are still worked out from the whole land, so what is kept comes out the same px as on the real land. xray.js paints the 9 tiles round you with it and shows only the px where, on the real land, the left-out rock is on top. Where only the rock's own inside is behind it (where it stands; where it joins a hill beside you) the rock stays as drawn. A kept cliff's side shows as any cliff corner does. Cave mouths in what is kept show too (caves.js).
- Creatures: behind the rock, what it hides of them is drawn as faint as the circle is there (behind.js clipBehind, a second pass); on the rock they thin out toward the middle. No more on/off at a threshold. Dust and sparks show in the circle.
- Cost: the picture is kept and painted again when you change tile or height, or the land changes: 3.5 ms in the canyon (6.4 before ledges were grown only from the tiles that end a shape, which every block's build gains from too), 2.5 ms a frame at the most. On a 4x slower CPU the new picture is there 2-3 frames after a step. A step toward the rock or away changes what is seen through by a row: the new picture comes over the old one in 0.12 s, not at once.
- Proof, on frozen frames in Chrome: (1) the land itself, 12 scenes on two worlds before and after the painter's rewrite: 0 px differ. (2) The circle's painter is the land's: with no rock left out and its whole picture shown, the frame equals the frame without it at 100 places (zoom 2-5, pixel ratio 1-3): 0 px differ. This is what found the missing cave mouths. (3) The user's spot, on a copy of the play world: the cliff behind, the water, no plateau layer. (4) What the circle shows equals the same px with the front plateau really taken away. (5) Twelve built scenes looked at one by one: thin and thick wall, notch, pits, canyon, slot, stairs, pillar, drop, ledge, corner. (6) Every real frame while walking out of a corner and along a wall.
- Tests: 9 browser tests for the circle (2 and 4 above; hidden ground only; ground that shows is never touched; a cliff's side beside open water; things on the rock; creatures fade; painted once a tile). 299 unit; browser 110/110. The boss test waits longer for its land to load: it failed whenever the boss was spawned across a chunk border, circle or not.
- Decided, could be otherwise: where the rock itself stands it stays as drawn (a straight edge at its foot). Cutting it flat to an earth-coloured footprint was tried: standing in a pit, the whole circle turns brown, which is what iteration 67 was told off for.
- Found on the way, and fixed after (behind.js tileBehind, drawBehind): a tree, a rock or things dropped behind a hill were always drawn over the hill, as if they stood on top of it; only bodies were cut at a hill's edge. They are now cut the same way, and show through the hill in the circle like anybody. Which tiles are behind something is kept a block until the land changes, so a frame asks nothing for the rest: a whole frame on a phone-sized screen at a 4x slower CPU is 6.6-8.8 ms, as before. Two tests (hidden by a wall and seen in the circle; cut at a ledge's edge, the crown over it). 300 unit, browser 112/112.

## Iteration 78: the crafting screen is larger, says what can be made now, and has more keys
- User (a side task): improve the crafting screen: good to look at, clear, easy with the keyboard alone.
- Change (css/style.css, js/craft.js): the window is 860 px wide (it was 640), its slots 64 px with 40 px icons, its text 20 to 28 px. What can be made right now wears a green tick; the rest is faded further. Beside the tabs: the category's name and how many are ready. Q and E change category as Tab does; Home and End go to the first and the last recipe; the recipe you are on stands out and scrolls into view.
- Result: looked at on a screenshot (12 wood, 6 stone, 4 fiber: 13 ready). A browser test for the ticks, the count and the new keys; UI and building tests 16/16.
- The side task had stopped while waiting for its tests, its work not committed: finished and committed here.

## Iteration 79: land coming in costs a quarter of what it did, a little a frame (the only late frames)
- User: "can you improve performance further? what's the bottleneck?"
- Measured first, each part alone. (1) A steady frame is nothing: Chrome's own trace on the M5 at 120 fps (3024x1720): 0.5 ms on the page's thread, 0.7 ms on the GPU process's (0.57 of it with every drawImage of the game switched off: Chrome's own), 1.6 ms of CPU a frame over four threads. With the CPU slowed 4x: 60 fps, 87% idle. (2) The server: 0.1-0.2 ms a tick, 4% of a core; in the demo's worker the same. (3) What is late: frames while new land comes in, and only those. Camera gliding 10 tiles a second (a sprint) for 14 s, three ways, old code against new on twin copies of the worlds: phone size at 6x slower, 36 / 18 / 48 frames over 16.7 ms of script (worst 44 ms) and land not built yet on the screen in 3-5% of frames; the play Mac itself, 10 / 8 / 20 frames over the 8.3 ms of its 120 Hz screen.
- Why: a block (32x32 tiles) cost 42 ms to build at the foot of the play world's twelve-layer mountains (19 ms its ground, 23 its raised picture), in steps of up to 10 ms, and was built about 2.2 times (again whenever a block arrived beside it). A tile twelve layers up was painted as fourteen sheets one over the other; its raised picture painted all twelve levels whole. A block's water (its bottom, 34x34 tiles) was made again inside the frame each time any tile of the block was drawn again.
- Change, the ground (tiles.js): the block a tile is in is kept from one lookup to the next (no key string a tile); a tile's sheets are noted, then painted from the last one that is solid all over (cellSolid: every px of the cell at full alpha, read off the sheet). 7.3 -> 1.3 ms a block.
- Change, the raised picture (relief.js): at each level a block's tiles with nothing to work out are gone over 16 px at a time: hidden to the last px by the level above (that level whole on the tile and on the tile south of it, both solid as drawn), nowhere near the level, or wholly its own (a plain copy). Runs of whole tiles are filled a row at a time. A step every 32 rows. 16.4 -> 4.9 ms a block, longest step 10 -> 1.8 ms. The x-ray circle uses the same painter without the skipping (it leaves tiles out), so its "whole picture equals the frame" test now checks one against the other.
- Change, the water (water.js): made as the last steps of building the block, and only when what it is made of changed (the depth drawn at each tile and where land is: compared), not whenever a tile was drawn again; no canvases at all for a block without water (2 MB each before).
- Change, the frame (render.js, relief.js reliefWork): one allowance for all land work, 3 ms a frame (7.5 while something on the screen is missing, 12 while you arrive): tiles to draw, then raised ground, what is on the screen first, then what is about to be, then the rest of what was asked for. Nothing is built from ground still being drawn. The cave overlay waits for the tiles too.
- Result, same glide: 6x slower, 0 frames over 16.7 ms (worst 10 ms), nothing missing; test world at 4x, 64 / 4 / 47 -> 0; the Mac, 0 frames over 8.3 ms (worst 7.3). A block: 23.6 -> 6.2 ms on the play world, 14.7 -> 3.5 on the test world.
- The same land: every block's ground and raised picture hashed before and after at ten places (44 blocks): equal. Old tile painter against new on 30,720 tiles: 0 px. Old water layer against new, 39 blocks: 0 px, same foam and glints. Thirteen whole frames, old and new code on twin servers started from the same save: 0 px. (Against screenshots a few hours old four scenes differed: the world had grown. And a canvas read back once is painted by another path in Chrome, a few half-transparent px round differently: compare after a first read.)
- Also: the crafting list was built again, every card, at each step you took, shut or not (11 ms at 4x): only while it is open. `/perf` (debug.js), for a real phone, which no emulation here stands for: frames a second and the longest wait, the script's work a frame and its land part, ticks reaching the screen, what a tick costs the world. The debug text sits under the buttons on a phone.
- The demo's first visit, counted: 7.3 MB before the land shows, 6.2 of them Python itself (jsdelivr); then 15 MB of sound effects, 198 wav files. They are FLAC now (tools/build_audio.py): 5.0 MB, the same samples (all 198 decoded both ways in Chrome: equal). The music's files are not touched.
- Not done, by size: each block is still built about twice (the block beside it arriving); the effects are held decoded (about 45 MB at 48 kHz); Python's 6.2 MB. Not measurable here: the worker cannot be slowed by Chrome's throttle (pages only), so the phone's tick time is still an estimate; `/perf` on the phone says it.
- Tests: tests/e2e/test_e2e_land.py (the land is the same with every layer painted and with only what shows; no long step; water made again only when it changed; the glide: nothing missing, no long frame), `/perf`, the crafting list. 302 unit; browser 118/118.

## Iteration 80: black tiles on a phone; the land is painted in the page, not by the GPU
- User, with a screenshot from the phone (the demo, Chrome on Android): "Dark spots". Pure black tiles along a cliff's top, single black tiles on a plateau, a black wedge in the x-ray circle. The game paints no black: what is under the land is #2b2420.
- Not reproduced here, and that is the finding: the same world, the same spot, the same screen (501 px wide at 1.9167, read off the screenshot's tile size), software drawing and the Mac's GPU, a player standing there, the camera gliding the user's route in the real demo (Python in the page): 0 black px, 442 places scanned. And nothing wrong to be found in what is built: the ground is never read before its tiles are all painted (counted at each cut: 346 cuts, none from unpainted ground).
- What the black tiles are, from the screenshot laid over my picture of the same spot: every one is a tile that the raised picture cut out of the ground at more than one level (a terrace's tiles with nothing in front of them: the cliff's top, the corner of a step; in the x-ray circle too). Black is the colour of the mask they are cut with. Since iteration 79 that mask and the walls were put into two canvases kept from level to level, a few rows at a time (putImageData with a dirty rect), the ground drawn into the mask (source-in), a few rows of the result drawn into the picture. A desktop GPU does it in the order it is written; the phone's left the mask.
- First, at once (81d5ff4, published): whole pictures put and drawn again, as before iteration 79, which the phone drew right. 4.9 -> 7.3 ms a block.
- Then the cause, removed rather than avoided: nothing of the land is put together by the GPU any more. A block's ground is px in the page (b.px, a Uint32 a px): a tile's sheets are laid cell by cell from the sheets' own px (tiles.js layCell: a solid cell a copy a row, another px over px, its see-through shadows as a canvas lays them). The raised picture is worked out px by px from those (relief.js) and made a canvas once, at the end, with the ground's own canvas: two uploads a block, no mask, no blend mode, no canvas written again after it was drawn from. The x-ray picture takes the blocks' px the same way, and its two masks are a canvas each (one was written again after it was drawn from: the same thing waiting to happen).
- A block shown and its raised picture are now swapped together (before, tiles drawn again showed on the old raised picture until the new one was ready).
- Measured: the px against the same tiles laid by a canvas, 19 blocks at three places of the play world: 0 px differ. On the test world a sheet's see-through shadow rounds one step differently on some px (0x76 for 0x77 in one channel), as it does between two canvases. A block: ground 1.5-2.1 ms, raised picture and water 4.4-5.3 ms, no step over 0.3 ms once warm (all of it in the page now: before, part of the work was the GPU process's, which the 6x slowdown did not slow). Glide at a sprint, phone-sized, 6x slower: 0 frames over 16.7 ms (worst 12-15), land not built on the screen in 0-1% of frames.
- Not known: whether the phone now draws it right. Nothing here can stand for its GPU. The demo is republished; the user's phone says.
- Tests: the land is px (equal to the canvas's tiles; a block built draws on no canvas and puts two pictures, once each); the water test waits for the rebuild instead of 900 ms. 302 unit; browser 119/119.

## Iteration 81: the chat line finishes what you type
- User: "Add auto completion on chat".
- What there was: a /word typed in the chat line is an action sent to the server (/dig dir=N), or one of three done in the page (/coords, /grid, /perf). Nothing said which exist, what they take, or how an argument is spelled.
- Change (js/complete.js, 103 lines): a "/" lists the commands over the line as you type: the server's actions with what each does (its own list, asked for once when the line opens: the "tools" request the agents use, so it cannot fall behind), and the page's three. Then the command's arguments not given yet (dir=), then what an argument can be: N E S W, a slot, what you carry (to eat: what can be eaten), the recipes with what they cost, who is near with how far (the id the server wants is put in the line). A number or a text is yours to write: the list says what it is ("x: int"). Tab takes the marked one (the first, or where the arrows moved the mark; what starts with what is typed comes first, the shortest first: /di is dig, not dig_down); a click or a tap takes any, and the line keeps the caret (no Tab on a phone). Enter sends the line as it is typed. In plain talk nothing is listed; Tab finishes the name of someone near (two that start alike: the list).
- Found on the way: run=false was sent as the text "false", which the server takes for yes. true and false are sent as what they are.
- Tests (tests/e2e/test_e2e_complete.py, 4): a command built with Tab and the arrows and sent; what each kind of argument offers; a name in plain talk; taps on a phone-sized screen (the list on the screen, over the line; the line keeps the caret). The x-ray test that failed now and then under a full run waits for the land and for you to be where the server has you, not 700 ms. 305 unit; browser 123/123, twice.
- Not done: no history of what you typed (the arrows are the list's only while there is a list).

## Iteration 82: no wall strip in the circle, beside a hill the rock joins
- User: "Weird wall artefact in xray" (a screenshot, the demo on a phone, at night: in the river against the bank, a strip of brown wall half a tile wide, as tall as the bank, standing alone between the water and the rock beside you).
- Reproduced before touching anything: a corner and a bank in steps built on a test world show the same strip; so do three places of the demo's own river, found from its land (23 places are of that kind along the canyon).
- Cause (relief.js, the land's painter with rock left out): the rock in front of you (south) and the hill beside you (on your row: kept) are one mass. Where a kept tile has that rock right under it, the painter draws no wall: there is nothing behind but the rock's inside, and the rock stays as drawn (iteration 77). But the hill's side sticks out a few px over your tile (its ledges), and under that ledge the painter did draw a wall, "as at any corner": the strip. It was decided px by px, from what was painted just above in the same column.
- Change: decided from the tiles. At a level, a kept tile goes on south as rock when the tile under it is left out and as high. Along that line no wall is drawn and nothing shown, a layer down: under the tile, and beside it over lower ground as far as the hill's side reaches (the px columns its ledges have got to at the levels below, where the side is widest, so nothing of the side is left over higher up either). A wall is still drawn where the level really ends: a hill beside you taller than the rock keeps its real corner, a hill lower than the rock shows whole through it.
- First try, thrown away: only "no wall under a kept ledge with rock under it". The strip went, a stub of it stayed where a ledge's rounded end stops short of the line, and it would have left a strip of bare rock beside a hill with a real wall. Eight scenes side by side showed it; the px-by-px rule could not tell the two apart, the tiles can.
- Measured: eight built scenes (corner, steps, each side; on land; a low plateau; hill taller, hill lower), circle on, before and after, beside the land with the circle off: the strip is gone in all, and along the hill the screen is the same px as with the circle off. The three demo places at night: gone. The picture costs what it did: 1.6 ms (corner, steps), 2.1-2.3 ms (canyon), median of 40.
- Tests: one more for the circle (corner, steps, a taller hill, each on both sides: along the hill the same px as without the circle, and the water shows beside it); it fails on the painter as it was. Two tests waited a fixed time and failed with the machine busy (other sessions' training on every core): they wait for what they need. 305 unit; browser 124/124 with two workers (with four, on the busy machine, join and teleport waits time out here and there; those pass alone).
- Not done: in a corridor one tile wide between two hills, both sides reach over your tile and little of its ground shows between them, as on the land itself.

## Iteration 83: the circle shows the place you are in, not only what is behind you
- User, on the fix of iteration 82 (a screenshot: the circle is a box up and to the left of you, cut dead at your feet and at your side): "but it does not show what's in front of me".
- Stepped back: the wall strip was a symptom. The rule of iteration 77 was "the rock seen through is what stands two layers over you, south of your row". Along a bank that goes off in steps the river ahead is hidden by bank tiles on your own row and north of it: never seen through. Iteration 67 had it right in words ("the ground rock is drawn over, where you could be on it") and iteration 77 lost it. The strip was that same row line, drawn.
- Change (xray.js): the rock seen through is, of the mass that hides you (the ground two layers or more over you that joins up, tile to tile, with what is drawn over your tile), the tiles on the line of sight to the place you are in: the ground you could walk or drop to from where you stand, within 4 tiles (your height, a step up, or lower; no rock on the way). A tile is on the line of sight to a ground tile north of it in its column when it is high enough to be drawn over it: two layers a row. So the river ahead shows, each column of the bank cut at its own foot; a cliff with nothing of your place behind it stays whole; a rock standing apart stays whole whatever it hides (cut too, on the first try, a pillar behind you left a square of the front wall's top in the grass where it stood).
- The painter (relief.js), now that kept ground and rock left out can sit side by side: a kept tile grows its side ledge only where the land itself ends, not over the rock beside it; no wall is painted on rock left out, except under a kept tile whose real wall the rock's ledge hid; and the px columns a hill's side reaches over the rock's line stay as drawn for every level of that rock (a hill lower than the rock in front left its side standing alone above it).
- Found on the way, the real cause of x-ray tests failing "with the machine busy" (blamed on load three times today, and before): the tests' frozen-frame helper stamps a frame with performance.now(), and the next real frame can be stamped earlier. dt went negative, and every body standing still was moved by 0/0: its place NaN for good, so no circle and no "you are where the server has you". render.js: dt is never under 0. Seen by printing the state at the failing wait instead of waiting longer: the player's place on screen was null. 1 run in 3 failed before, 0 in 9 after.
- Measured: 15 built scenes looked at one by one, circle on beside circle off (corner, steps narrow and wide, a bend, hill taller and lower, nook, canyon, wall, pillars behind, pit, each side): no strip, no tick, no stub, the place shown to the bank's foot. Three places of the demo's river at night, before and after: the river ahead shows. A picture costs 1.6 ms (corner, steps) and 2.2 ms (canyon), median of 40; it was 1.4-1.5 and 1.9-2.0.
- Tests: the circle shows the ground ahead round a bank's corner, all of your tile, the bank's foot as drawn, no px in a wall's colours, on both sides; a pillar behind you is the same px as with the wall in front taken away; the corner test has a lower hill too. My scenes are land, not water, and flattened after (a scene of water left in the shared world broke a land test that looks for a dry block). The join waits 25 s, not 8 (it timed out in a different test each full run on the busy machine). 305 unit; browser 126/126.
- Not done: the place is what you could walk to within 4 tiles; ground you could reach only by a way that leaves that circle stays hidden. In a corridor one tile wide both sides reach over your tile, as on the land itself.

## Iteration 84: an item's pixels are the game's pixels
- User: "items looks off, the pixelization of them does not match the pixelization of the game". Then, seeing the first fix live: "its better but the items are wayyy too big !!". Then: "can you make them also more pixelated in the inventory bar also ?".
- Measured before touching anything (screenshots blown up, desktop at 1x and 2x, a phone at 2.625): a thing on the ground was its 16 px icon drawn 10 px across, so its pixels were 1.9 screen px beside the land's 3 (1.25 beside 2 on a phone), uneven, and smaller still as it flew to your hands. In the bar an icon's pixel was 1.84 CSS px on a 1280 px desktop and 1.5 on a phone, in a frame at 2 stretched to 55.04 px (seams between its nine pieces). Crafting: 2.5 in the list, 1.75 in the tabs and the needs; goals 1.5. And seven icons (boat, mailbox, bed, plant, well, coop, picnic blanket) were bigger sprites squeezed into 16 px with smoothing: a blur.
- Rule now, one for all: an art pixel of an item is a whole number of screen pixels: the land's own on the ground, the frame's own in the HUD. Nothing is drawn at a size in between.
- The ground, first try, wrong: the 16 px icon as it is, at the zoom. Right pixels, but a log as wide as a body: the user's second message. A thing on the ground must be about the size it was (10 px), so it needs a smaller picture, not a smaller drawing of the same one.
- The ground, now (loot.js ghostIcon): a small icon of 11 px made from the 16 px one by whole pixels: of every three px across and down the first two become one (the colour most of them have, the darker of two as many), the third stays. Half size (8 px) was tried beside it and is too crude; an even two thirds by area lost a torch's stick and a bone. The white sticker edge of the pack's item icons is taken off first (kept, it came out in pieces). Big things (a boat) are reduced straight from their sprite. A pile, loot hopping out and loot flying to your hands draw that icon at the zoom; what is caught fades instead of shrinking; landing, a thing sits a pixel lower for a moment instead of being squeezed flatter.
- The HUD (style.css, ui.js hudFit): art pixels rounded to whole screen pixels: --u for a slot's frame (about 2 CSS px), --i for the item in it, --u3 for the crafting's big picture. First the 16 px icon sat in its slot at the frame's pixel (2): whole, but finer than the land's 3, which the user's third message is about. Now a slot shows the same small 11 px picture as the ground, at --i: the land's own pixel at the zoom the game starts with (3 CSS px, 2 on a small phone), and no more than fits the frame. The same in the inventory, the crafting list, its tabs and needs, the goals, the death list; only the crafting's big picture is the 16 px icon. The bar's pixel goes down a screen pixel at a time while ten slots do not fit across, or the HUD would take more than a quarter of a phone's height; the hearts likewise where two rows do not fit. Nothing is scaled any more (a phone's whole HUD was, by .97 or .74).
- Two things that made whole sizes still come out uneven on the phone: the frame was a border image in nine pieces, whose joints showed between two screen pixels (it is put whole now, as a background); and the HUD, the bag and the crafting were centred by moving them half their own size, onto a half pixel (they are centred by their margins).
- Icons of big things in the HUD (ui.js smallArt): the sprite is trimmed to what is drawn, then each n x n block becomes one pixel of the colour most of it has. A mailbox is 8 px of its cell: its own pixels, untouched. The px are worked out in the page and put once.
- Found on the way: two drops that came to rest in the same long frame were drawn twice for that frame, once as loot and once as the pile (the hand-over is decided before any is drawn now; the test for it failed one run in two on this busy machine, and was right); the bag lay over the hearts (it sits on the HUD, whatever its height); the xp bar and the hearts kept the width of a bar that had since been fitted smaller; a focused recipe was scaled by 1.1 (it only lifts). A completion test of iteration 81 waited a fixed 1.8 s for two friends to be known and failed once in a full run: it waits for them.
- Decided, and it is the user's to overrule: the slots' frames keep the size they had (2 CSS px a pixel on a desktop, 4 screen px on the phone tested), so the frames' pixels are whole but finer than the items' and the land's (3, and 5). Frames at the land's pixel mean a bar a quarter bigger (the frame is 7 art px a side round the picture: 804 px wide for 636), and on a phone a bar that reaches under the left thumb.
- Tests (tests/e2e/test_e2e_pixels.py, 9): every draw of a thing on the ground is its picture times the zoom, at zoom 2 and 3 (fails on the old size), and a small icon has only its icon's colours and no white edge; in the HUD on six screens (desktop 1x, 2x, 1.5x, a narrow window, a phone lying and standing) an item is the 11 px picture at a whole number of screen pixels, the land's own where the slot has room, its frame whole too, nothing scaled or moved by half its size; a big thing's icon has no blended colour. 306 unit; browser 136/136.
- Not done: the coop and the picnic blanket are rough at a third of their size (whole pixels, but a drawn icon would be better). Emotes over heads are still 32 px art drawn at 3/8. The hearts' pixel (2.5 CSS px) is neither the slots' nor the land's. Picked fruit still flies at its full 16 px. Without its white edge a brown thing (wood, bread) stands out less on a slot's brown.

## Iteration 85: eating, your hands are full
- User: "can you make player that eat not able to punch / breka things ? he can walk nothing else".
- What there was (iteration of the walking meal): eating is done with the hands beside a walk, and "doing something else stops the meal". So a player could punch, chop, dig or pick up with the food at his mouth; the meal ended, and the bites were lost.
- Change, the server's rule (sim/core.py submit, constants.MEANWHILE): while a meal is under way everything but walking (walk, step, move_to, stop) and talking (say, shout) is refused with "hands_full", and the meal goes on. Another bite is refused too. Talking is let through on purpose: a line typed during a bite must not be lost; it is the one thing beyond "walk" and it does nothing to the world.
- The page (agent.js, intent.js): while you eat nothing but those is asked for, and no swing is shown (the punch was drawn at once, before the server answered).
- Tests: the sim test of the walking meal now holds that a dig, a punch, a second bite and a pick-up are refused and the walk and the meal go on, that talking does not stop the meal, and that the hands are free once it is eaten; a browser test presses Space on a tree and F on a thing underfoot during a meal (nothing asked for, no swing, the tree stands, the meal is finished), then both work. 306 unit; browser 136/136.
- Not done: the server the user plays on runs the old rule until it is started again (the page's own rule holds for a player at once; an agent's actions are refused only after that).

## Iteration 86: smoke, glows and shadows in the land's pixels; numbers on the slots that read
- User: "same for particles , i want them pixellated. not pure circles". Then: "numbers in the bottom inventory slots arent really visible".
- What there was: chips and sparks were already square art pixels. The round things were not: a smoke puff (a creature's poof, landing dust, chimney smoke) was a smooth circle with a stroked edge, an xp orb's glow a smooth disc, and the shadows under you, under a jump, under loot and under a pile smooth ellipses.
- Change (effects.js pixelOval): a round shape is rows of whole art pixels, each art pixel filled if its middle is inside, on whole screen pixels; a puff's edge is its outermost art pixel all round. All six use it; no arc or ellipse is drawn on the game's canvas any more. A shadow has an odd number of rows, so it is an oval (8, 10, 12, 10, 8 under you) and not a bar (the first try gave a pile a plain 8 x 2 rectangle).
- Done beyond the words: the shadows and the orb's glow are not particles. They were the same smooth circles among pixel art, so they went the same way; said to the user.
- The numbers: a slot's key (1 to 0) was cream on the cream frame, with no edge: nearly gone. The count had a thin blurred edge. First try: a near-black rim one font pixel wide on both, the key yellow. User: "now its a bit.. too much readable". Second try, my mistake: the rim's colour put in a variable used inside another variable, which does not resolve where it is used, so the rim went altogether, and the user saw it live: "its almost invisible to the eye !!". Now, the middle: the count white with a rim in the ink's brown, the key cream with a lighter brown rim, both one font pixel wide. On a touch screen the keys are not shown: there are none.
- Measured: frames of a poof, dust and a pile before and after, blown up (scratchpad items/puffs_cmp.png, k_bars.png).
- Tests: with the zoom at 2 and 3, a poof, dust, an orb, your shadow and a pile's draw no arc and no ellipse, and every row is whole art pixels on whole screen pixels. 306 unit; browser 138/138.
- Not done: lights at night, the cave's light and the x-ray circle's edge are still smooth gradients (light, not shapes). The hearts' pixel is still not the slots'.

## Iteration 87: the crafting, one kind at a time, on cards that say it all
- User: "now improve the crafting menu. there's too much content, too many data, it's ugly, small and unreadable". Then, on the first version (the layout below, in plain rounded boxes): "the concept is much better but it still looks bad".
- What there was: a wall of sixty small slots, all the recipes at once ("All"), most of them faded to a third and greyed; ten tabs that were pictures with no name; a pane beside it for the one recipe you pointed at (name, needs, where, a button); a line of keys under it. On a phone the thumbs' buttons and the ones at the top lay over it.
- Now (craft.js, 104 lines; style.css): on the left the kinds, by name, each with how many of it can be made now; the first is "Can make": everything you can make here and now, and the panel opens on it every time (nothing yet: on Start). On the right only the recipes of the kind you are on, each a card: its picture (the 16 px icon at the land's pixel), its name at 27 px, what it needs as small pictures with a number (what you lack in red, have/need), then "at" and the station (red while you are not there). A card you can make is lit: a click, a tap or Enter makes it; five at once on a small button (or Shift). A card you cannot make is quieter and still read; a click says why. No pane, no tabs without names, no line of keys.
- The look, second go (style.css): the first version was the right layout drawn like a web page: smooth rounded boxes, soft outlines, pictures floating on cream, beside pixel frames. Now it is drawn in the panel's own five colours and in pixels: a card is a face with an edge one art pixel wide that leaves the corners out and a lip under it (shadows of the box moved by a pixel: no image, so no joints); the cards lie in a tray a shade under the paper, so the ones you can make stand out of it and the others lie flat; a recipe's picture sits in a cell of the slots' own wood, where an item is drawn to be seen; the kind you are on is a plank of that wood; the counts are square green tags; the x and x5 are tiles that go down when pressed; names start with a capital. Nothing in it is a rounded box any more.
- A phone: the panel is all of the screen, over the thumbs' buttons, which are put away while it is open (they showed through it); names at 18 px, two columns. Its frame is on whole screen pixels there (the panel's border is 9 art px at a whole number of screen pixels now, for every panel), so its pieces show no joints.
- Keys: as before (arrows, Tab or Q and E, Home and End, Enter, Esc); right at the end of a row goes to the next card, so every card is reached with one key.
- How it was made: in a copy of the tree with its own server, looked at on three screens, and brought over in one go (the user sees the play server's files live; see the memory note of the day).
- Found by the full run: a list of names asked for with Tab in the chat was wiped when the server's list of commands arrived after it (complete.js, iteration 81): that list is made again only while a command is being typed. The test for it failed one run in three, alone; eight of eight after.
- Tests: a card says what is missing (have/need in red, the station in red, then not); one kind shows at a time, it opens on what can be made, a lit card is made with a click and an unlit one says why; counts beside the kinds, keys over every card in order; on a phone the panel is within the screen, the thumbs' buttons hidden, and a tap makes a lit card. The pixel test now covers the kinds' pictures, the needs' and the cards'.
- Tests found on the way, both mine or old: the land test's pond was stamped at a fixed place and fell across a corner of four blocks when its player woke near one, so no block was without water (which player wakes where changes whenever a test is added: it failed every run after I added three); it is stamped inside one block. My test of the round shapes left a pile of wood in the world the tests share, and the x-ray test, waking near it, counted it; it picks it up. 306 unit; browser 139/139.
- Not done: Clothes (19) and Armor (15) are long lists to scroll; the pictures of the kinds are the first recipe's, not drawn for them; a wooden thing (a door, a fence) is brown on the cell's brown, as in the bar.

## Iteration 88: the crafting is a recipe book; a line about each thing; a pickaxe worth looking at
- User, on iteration 87's menu: "still looks awkward. some elements are not hte same size as others, it has too many items on screen, overwhelming for player. create a mockup html page with 5 propositions". Of the five (a second bar; a grid of slots; a short list and the one you are on; one at a time; six cards with words): "3 is the best. iterate on it with 5 new designs inspired on it, nice icons, minecraft inspired designs". Of those five (as chosen; a crafting table; a recipe book; trades; only the list): "go with 3/ recipe book one. add a short description for each object. funny. also redo the pickaxe design it is horrible".
- What was wrong with 87, in their words and my reading of them: things of several sizes side by side (a picture of 48, needs of 33, tags, two sizes of text) and twelve cards with three or four things on each. The mockups were made from one slot, one picture and one or two text sizes, and showed five names at most.
- The book (craft.js, 138 lines; style.css): five kinds instead of eleven (Basics, Tools, Build, Home, Wear), a bookmark each down the window's side. Left page: a switch "Can make" and two arrows, then five names at a time, each with its picture in a sunk cell; lit if you can make it. Right page, for the one you are on only: its picture and name, a line about it, each thing it takes with what you have of it (9/4 in green, 0/2 in red), the station ("here" or "far"), and one button that says "Craft" or why not; "x5" beside it when you have enough for five.
- One pixel size for all of it, --q: the land's (3 CSS px; on a small phone 2 and a screen pixel more, so a name is a finger high), less while its 272 x 160 pixels would not fit the window. A cell is 18 of them round the whole 16 pixel icon (not the small picture of the slots: the user asked for nice icons); the text is the font at that pixel; a window, a cell, a button are a face, a bevel and an edge that leaves the corners out, all shadows of the box, in the panel's colours.
- Keys: up and down through the names, turning the page at its ends; left and right, Q and E, Tab the kinds; Home and End; Enter makes (Shift: five); the wheel turns pages. It opens where you left it.
- A line about each thing (js/blurbs.js): eighty of them, 48 characters at most, e.g. the pickaxe: "Asks the rock politely. Several times. Hard."; the door: "A wall that changes its mind."; the coop: "A tiny house. The rent is paid in eggs.". A unit test holds that every recipe has one, no two alike, short enough for two lines.
- The pickaxe (tools/pixel_art.py, its cell of gen.png): it was a hairline drawing with no edge beside the pack's axe and hoe. Drawn again in their manner: their handle (three browns), a head that curves from a point up left to a point down right in their four greys, lit on its outer side, and their white sticker edge. Four candidates were drawn from an arc of varying thickness and looked at beside the axe and the hoe; the slimmest was kept. Only that cell of the sheet changed (checked cell by cell). What lies on the ground takes its sticker edge off whenever most of an icon's outline is near white (it was: whenever it came from the pack's sheet), so the new pickaxe is treated as the axe is.
- How it was made: two rounds of mockups on the one local page (the game's own font, frames and exported icons on a real screenshot), then the game's code in a copy of the tree, and brought over in one go.
- Tests: the right page says what a recipe takes and what you have (in red what you lack, the station far), and the button why not; five names of one kind, five kinds, the switch, the button makes; every name of a kind is reached with the down key over its pages, the kinds with five different keys; on a phone the book is within the screen, a name a finger high, a tap on a name and a tap on the button; the book's icons, cells and font are one whole pixel size.
- Found by the full runs: how many a recipe makes was a cream number on the result's light cell, nearly unseen: it is "x2" beside the name. A wear test still counted the three old kinds of clothes. And one more test broken by what another left: the x-ray painter test's player woke near the pile the fade test leaves, so 4176 px differed. Rather than chase each one, the tests' clear_area now takes the piles near as well as the creatures (devtools dev_creatures with `clear`; a unit test). 310 unit; browser 139/139.
- Not done: Wear is nine pages (43 things); the bookmarks have no names but a tooltip; no key for the switch; the spear, the sword and the torch are still hairline drawings like the old pickaxe.

## Iteration 89: the recipe book is one size, whatever is on its pages
- User: "the crafting table size should not change depending on its content ! too many items required = become bigger. decide of a default size and cap it with nice handling of crafts that requires lot of items".
- Measured first, every recipe one after the other: the window was 252 x 155 of its pixels for 73 recipes and 161 for the seven that take four things (three materials and a station: the axe, the pickaxe, the spear, the well, three charms), and it moved up 9 px with it, since it is centred. Its height was `max-content`.
- Now (style.css, craft.js): the window is 252 x 155 always, and each part of the right page has its place and keeps it: the name (two lines at most), the line about it (two), a place for what it takes, the button. That place holds four lines (the gaps of the page went from 4 px to 3 and the lines' from 2 to 1 to make room for the fourth in the old height, so a phone keeps its pixel size).
- More than four things: they go two abreast without their names (a picture and have/need; up to eight), then three abreast with smaller numbers (up to twelve). More than twelve: what you lack comes first, and the last place says "+5 more" (its tooltip names them). No recipe takes more than four today; tried with made-up ones of 6, 11 and 16.
- Found on the way: PageUp, Home or "<" on the first page left one name lit and the right page on it, while Enter made the first of the page (the list was not drawn again when nothing turned, but the place in it was reset). It is drawn again.
- Tests: every recipe of every kind gives one place and size for the window and its parts, nothing spills or is cut; the same with recipes of 6, 11 and 16 things, which go two and three abreast and say "+5 more" with what you lack first; the empty list too. The keys test holds the lit line and Enter together. 310 unit, 140 browser.
- Not done: in the tight layouts a thing's name is only a tooltip, which a phone does not have.

## Iteration 90: a limit of creatures around each player; the ones over it go out of sight; a named one stays
- User: "mob spawning mechanics are broken i see tooooo many mobs wtf !!! add per player limits lol like minecraft and despawning off-screen if needed, unless named mob or rare mob".
- Measured first. The play world's save (read, not touched): 789 creatures, 764 of them chickens, 310 within 40 tiles of one player and 54 on their screen; 772 of the 789 were hatched, not spawned. In a simulation of the rules as they were, three hens beside a player standing still were 333 creatures two hours later and 542 after six (876 for a player who walks about).
- Why: the spawner was not the cause. An egg hatched wherever fewer than three animals were within six tiles, and nothing else held the number down. Hens walk some fifty tiles an hour, so there is always an uncrowded place to lay; and they drop down cliffs but cannot climb them, so they gather in the low ground (median: twelve within six tiles, four times the "crowded" number). Animals never despawned.
- Now (sim/spawning.py): a player's limits, counted within 40 tiles of them: 6 animals, 2 enemies. Nothing is born past them: an egg hatches only near a player who has room for one more animal (else it rots, as a crowded one did). Where there are more than the limit, the ones over it go, the farthest first, at most twenty a second, and never one that someone can see: on a screen (the server tells the simulation the rectangles the screens watch) or within 16 tiles of anyone. Spawns too are now on no screen.
- Who never goes: a rare one (strawman, wisp, wyrm, Old Mossback, sporelings); a named one; an animal within six tiles of a coop or a trough (a farm is somebody's, named or not).
- Names (there were none): `/name target=<id> text=Daisy` on a creature within two tiles. The name is saved with the world, drawn over it as a player's is, said in the chat, and shown in the list of who is near when a command asks for a target.
- A world saved under the old rules is thinned once when opened (after a copy, world.before-mob-limits.sqlite): where anyone will wake up, down to the limit (any six, not the six at their feet); far from everyone, one in five. Tried on a copy of the play world: 792 creatures become 26; 4 to 6 chickens within 40 tiles of each player, none on their screen. A tick costs 0.03 ms.
- After, the same simulations: 7 creatures near a player standing still after six hours (was 341), 32 in the whole world for one who walks about (was 876).
- Tests (tests/test_mob_limits.py): three hens for an hour and a half never pass the limit, and do breed; an egg rots where nobody is and where there are enough animals; fifty chickens round a player: the ones in sight stay, the others go, the farthest first; nothing goes on a watched screen, by a coop, or with a name (and only two of five tuskers stay); a saved world is thinned once and copied first. In Chrome: /name, the name drawn, the chat line, the list. 316 unit, 141 browser.
- Not done: a name can only be given by typing the command (no button); the limit counts farm and named animals too, so a big farm keeps wild ones away; animals frozen far from everyone stay in the save until someone comes near.

## Iteration 91: new music in the game: moments by day and by night, a loop for the boss
- User, after choosing the pieces by ear over many rounds: "go on wire them into the game with the music system etc." Earlier: "keep those two for random day / night moments".
- Before: one background loop all the time (Meadow Road) and a boss loop, both synthesised in numpy; the user refused every version of them.
- Now the music is five pieces written in Python and played on the Surge XT synthesizer's own sounds (music/pieces.py), mixed to one loudness (music/master.py, -20 LUFS): Side street day and night, Far shore day and night, Old Mossback.
- The player (web/js/audio.js): no constant loop. By day and by night a piece plays now and then (a moment), with 50 to 140 s of silence between, the first 8 to 20 s after sound starts; never the same piece twice running; a day piece twice through, a night piece once, fading on its last chord. While Old Mossback is awake in view its piece loops and a moment in progress gives way; after the fight, 20 to 40 s of silence.
- Levels: the files are 3 dB quieter than the old theme, so SOUND.music went from .45 to .64 and bossMusic from 1.2 to 1.4: the music sits against the effects where it did. 11 sound-effect files that were 0.5 to 4 dB under their intended level are fixed (music/sfx.py).
- The build (tools/build_audio.py) packages the pieces by role (TRACKS); the manifest has `tracks` and `play` in place of `music` and `boss`.
- Tests: tests/e2e/test_e2e_sound.py: a moment plays and M silences it; the boss piece takes over and hands back to silence; a piece ends by itself, the gap follows, night picks a night piece. 6 pass, with the boss and demo tests.
- Not done: Far shore night C is wired in but the user has not chosen between C and D; the pieces are short (34 to 58 s); the gaps are my guess, not yet felt in play. The live server serves the new client on a page reload; no restart is needed for this.
