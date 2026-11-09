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
