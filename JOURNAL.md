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
- Transitions (the user: "musics must have transitions etc. they just spawn out of nowhere now", then "make the transition long enough to not be noticed by the player"). Each kind of music has its own gain and low-pass filter (audio.js swell): a piece arrives over 10 s by day and 14 s at night, from quiet and muffled to full, and recedes the same way over its last 12 s. When a fight starts the moment recedes over 4 s while the boss's piece comes in over 2.5 s; after the fight the boss's piece recedes over 12 s. Pieces play through more times (day 3, night 2) so the fades do not eat them. Muting stays quick. Not felt in play by me.
- Moments last 3 to 4 minutes (the user: "same for the loops, feel free to make it loop for 3-4 min"): a day piece loops 6 times (about 3:30), a night piece 4 times (about 3:50), then recedes; silence between is unchanged (50 to 140 s).
- A sound for moving the selection (the user: "add a noise in the crafting menu or in the ui when switching selection. should be the default noise when switching things, less loud than the tab switch"): `pick` in music/sfx.py, the small wooden key of `ui` without its note, 4.4 dB under it (-27.4 against -23.0, loudest 100 ms). Played when the lit recipe changes (keys, mouse) and when another hotbar slot is taken (it was `ui`); tabs, pages and buttons keep `ui`. At most one every 60 ms, so a mouse crossing the list does not rattle.

## Iteration 92: the recipe book, all of it, without a mouse
- User: "make sure the crafting menu is usable without mouse".
- Tried first, in Chrome, with keys only. What was there: C opens, the arrows (and W S A D) move, Tab, Q and E change kind, Home, End and the page keys, Enter and Space make, Shift+Enter makes five, Esc closes. What was not: the "Can make" switch had no key; nothing on the screen said which key does what; X took what you faced in the world behind the open book (and F picked up, a number changed what you hold); I opened the inventory on top of the book, which then had no keys.
- Now (keyboard.js, craft.js): F is the switch. While the book is open the keys are its own: none acts on the world behind it (ten still do their usual thing: C, I, M, H, the chat's, the zoom's). I goes from the book to the inventory and C back: one of the two is open at a time. A held Enter makes one, not one per repeat.
- What a key does is written on it: a small cap after the button's word (F on the switch, Enter on Craft, Shift on x5, Q and E under the bookmarks), drawn as the book's own paper buttons. They show while you play by keys and are put away when the mouse moves; never on a phone. They change no size: the window and its parts stay where they were (the size test runs with them on).
- Tests (tests/e2e/test_e2e_bookkeys.py): with keys only, the caps show, X, a number and ` do nothing behind the book, F switches, a held Enter makes one workbench, W S move, Shift+Enter makes five, I and C swap the two panels, the mouse puts the caps away and a key brings them back, and shut, X is the game's again; no caps on a phone.
- Found by the full run: the land test's growing pond was at a fixed place and fell on two blocks when its player woke near a block's edge (the same kind as the pond of iteration 87; adding a test file moved who wakes where). It is put inside one block. 317 unit, 145 browser.

## Iteration 93: the races hold together on every frame
- User: "extra player sprites based on cat have some ugly things like their head popping off while using tool animation, rabbit ears are backwards when walking etc. fix all of that after auditing every sprite."
- Audit: every frame of every race (4 races x 192 frames) saved from a copy server, checked two ways: automatically (more separate pieces than the cat's own frame = something came loose) and by eye on enlarged contact sheets. Before: 17 frames flagged, all on the axe and hoe swings; by eye also a slab for a head on the side-on axe wind-up, ears floating beside the axe on the back view, tools wiped above the head.
- Cause: races.js rebuilds the head on each of the cat's frames, and measured the head on everything in the frame. On a swing that includes the tool, its arc and a raised hand, so the "head" was the axe.
- Fix (web/js/races.js): the head is measured on the body only (the piece that wears the collar). The tool, its arc and a hand held apart are set aside and put back on top untouched. A hand above the skull that holds a raised tool is kept (it went with the cat's ears, and the tool hung in the air). Side on, the face is measured on two rows so a hand against it is not taken for it.
- Bunny: side on, the pink inside of the near ear faced backwards; it now faces the way the bunny faces. The far ear no longer leaves a dark dot and a grey patch inside the top of the head.
- Clothes (web/js/wear.js) had their own copy of the same measurement: a hat on the plain cat jumped on swing frames too. Same fix.
- After: 0 frames flagged of 768; hats stay on through every swing. Tests (tests/e2e/test_e2e_races.py): no race has more pieces than the cat on any frame; the bunny's ear pink is ahead of the ear's middle in both side views.

## Iteration 94: every tool has its own swing
- User: "implement sprites for every key tool of the game".
- Before: the character sheet draws an axe, a hoe and a watering can. The game's other tools, the pickaxe, the sword and the spear, were all swung as the axe.
- Now (web/js/tool_art.js): three sets of rows are added under the sheet when it loads, made from the axe's 32 frames: same body, hand and arc, the axe taken out and the tool drawn where it was. The axe's handle gives the direction the tool points; the tool is drawn as solid shapes at eight times the size and reduced to pixels (drawn straight onto the pixels, a thin tool at an angle came out dotted). Pickaxe: the handle kept, a bar bent back with steel tips across its end. Sword: grip, gold guard, a blade with a shaded edge. Spear: a shaft through the hand, a stone point. Where the axe lay over the body and the new tool does not, the body shows through.
- Because the rows are part of the sheet, every race and every outfit has them with no other change (sprites.js ANIM: pickaxe 24, sword 28, spear 32; characters.js SWING_ROW).
- Checked: the three sets on the cat and on all four races, enlarged; 0 frames of 1,152 with a part come loose; real frames of each swing captured in play on a test server.
- Tests (tests/e2e/test_e2e_races.py): every frame of each tool differs from the axe's and from the other tools'.
- Not done: no tool is shown in the hand while walking or standing (the sheet has none there either); the hoe and the watering can are the sheet's own drawings.

## Iteration 95: a backlog of eight: experience, hearts and food, drops, tools, the swim, the screen, speech
- User: "backlog: 1/ remove exp when destroying blocks except ores like minecraft 2/ hearts hsould be one unit, not a integer => heart conversino. same for food. replicate minecraft system here. 3/ food goes away too fast. 4/ mob drop always the same thing, implement a rare drop pattern and make current drop more rare, like chickens. 5/ remove the white aura around tools. ugly. 6/ add a nice sprint animation in the water with larger trails. fast sprint. 7/ the ui is weird goals are overlapping with world . online player list should be only visible on tab like minecraft. 8/ when speaking, use the speaking sound effect in an animal crossing yaourt way".
- 1, experience (sim/progress.py): only ore gives it among blocks (it was 2 for a tree, 1 for a rock or a stump, 2 for a ripe crop, 1 or 2 for digging down). Crafting and hunting as before.
- 2 and 3, health and food (sim/needs.py, constants.py): health is 20 half hearts, food 20 half pieces (they were 0 to 100, shown in halves). Food went down by itself, a piece every 100 s: the bar was empty in 17 minutes whatever you did. Now it does not: what you do tires you (walking 0.004 a tile, sprinting 0.012, a swing or a blow 0.1, digging 0.02, healing half a heart 6), and at 4 a point of saturation goes (food in reserve, unseen; eating gives both, cooked food more of it), or of food when there is none. Standing costs nothing; walking, a point every 200 s; sprinting, every 33 s. With nine pieces or more you heal half a heart every 4 s (every half second with the bar full and a reserve); with three or fewer, no sprint; with none, half a heart goes every 4 s. The costs are this game's, not the classic's per metre: at those, a sprint here (10 tiles a second) would have emptied the bar in under two minutes.
- Blows, falls (half a heart a layer), fire, armor (to the half) and food values (bread 10, cooked meat 8, berries 2) are on the new scale; a blow on someone is shown in hearts ("-1.5"). A creature's own hp and what a weapon takes from it are as they were. Saved players are converted once (meta `vitals`). The server tells the page its scale when it greets, so a page on a server from before still draws right. The agents' prompt, the reflex and the rule brain's two thresholds are on the new scale (no new rule).
- 4, drops (sim/entities.py): each kind has a table of (item, chance, at least, at most). A chicken left a meat and an egg every time: now meat 60%, an egg 15%, and 2% a heart charm; a cow meat 80% (one or two, it was three), milk 15%, 3% leather boots; a pincer 5% a shell plate, a strawman 10% a straw hat. The boss's drops are sure. A dev tool (dev_luck) makes every line sure for the tests that watch drops fall.
- 5, tools (web/js/ui.js): the pack's icons have a ring of white px round them, a sticker's (the pickaxe was drawn with one). The axe, the pickaxe, the hoe and the can are shown without it. Tried with the ring made dark instead: heavy, and unlike the sword and the spear, which never had one. Only the tools were asked for: the wood and the crops keep theirs.
- 6, a sprint in the water (sim/movement.py, web/js/swim.js): Shift did nothing there. It is ten tiles a second, as on land (a tick a tile: there is nothing between that and a swim's two), and tires three times a swim. Looked at on real frames: the first wake was three flecks stacked a side and read as a row of fence posts; now two broken lines a side that spread nearly twice as wide and last half as long again, a churned line down the middle, water thrown up on both sides and behind at each stroke, a chevron of foam pushed ahead.
- 7, the screen (style.css, keyboard.js): the goals lay over the title panel, the list of who is awake was always there. Both show only while Tab is held (a tap on the clock, on a phone), side by side under the line of news; of the title panel only the clock's line stays while you play. A goal done is said at the top. Someone watching keeps the list.
- 8, speech (web/js/babble.js): a line was one "say" sound, and none for your own. It is a run of syllables, one for about every two letters: the start of one of the five recorded "say" voices, at the letter's pitch (each vowel has its note) and the speaker's own (from their name), a space a breath, a question rising at its end, a shout louder and higher; all put on the audio clock at once. The bubble writes the line out at the same pace. Not heard by me: I checked its timing, lengths and pitches in Chrome, not its sound.
- Not done: the play server needs a restart for 1 to 4 and 6 (its Python); the wood and the crops keep their white ring; saturation is not shown; a name for the Tab lists on a phone is only "tap the clock".

## Iteration 96: the play server restarted on the new rules; a mark that was written before its data
- User: "go on restart server" (the day before, stopping it was refused to me).
- Stopped with a SIGTERM (it saves), the world copied to saves/caves-backup-20261114-before-mob-limits, started again the same way (log: logs/server-7777.log).
- Found before starting, by reading the stopped save: `vitals` said 2 (converted) while the players still had 100 of health and up to 100 of food. A second server had opened the world a minute earlier, while the first still had the port: it marked the save on opening, the mob thinning's own commit (made before its copy) wrote the mark, and it died without saving the players. Started as it was, everyone would have had fifty hearts.
- Now: the mark is written when the players are saved (persistence.py), not on opening; and numbers over full are taken for the old scale whatever the mark says (needs.py: old_vitals), which also mends a save already left that way (this one, and a demo tab closed in its first seconds).
- After: 787 creatures became 41 (3 to 7 within 40 tiles of each player); ben and beo 20 and 20, doben2 11.5 half hearts; no slow tick, no error in the log. 333 unit tests.

## Iteration 97: the goals stay; Tab shows the day, who you are and who is awake
- User, on iteration 95's screen: "keep goals visible instead of day xxx. put help(H) in the goal menu so it goes with visible element. Tah should show: day , username and other users connected. Also the tab menu you created looks laggy".
- Now (style.css, goals.js, keyboard.js): while you play, the goals are top left again, always, with the help's link under them (it stays, with the count, when every goal is done); the title panel with its clock is put away. Held, Tab shows one panel at the top middle: the day and the hour, your name and where you are, then who is awake. On a phone, a tap on the goals.
- The lag: the goal rows have a slide in (0.35 s in four steps), and it played again each time Tab showed them. Nothing in the Tab panel moves in now; the test asks the frame after the key for the panel and for anything animating in it (none).
- A goal done is ticked where it is, as before: the line of news for it (added when the goals were hidden) is gone.
- Tests: the goals and the help's link while playing, no title and no list; Tab: the panel in the middle at once, its lines, the goals unmoved; let go, gone; someone watching keeps the title and the list. 333 unit; 153 browser passed and one setup error in the full run, a player who did not get in within 25 s (the swim sprint test's), not seen again in three runs of its file: a join that fails now says what the page had (tests/e2e/game.py).

## Iteration 98: what Tab shows, drawn as the recipe book is
- User: "Make the tab menu more beautiful". It was the old side panel moved to the middle: three lines of text and a list of names with a dot.
- Now (web/js/who.js, style.css): a window in the recipe book's manner (its pixel, --q; its paper, bevels and sunk cells: shadows of a box, no picture). At the top a cell with the sun, or the moon on a night blue cell, then "Day 4" and the hour. Under them the day as a bar, gold, its last quarter the night's blue, with a mark where the hour is (the tick's `phase`). Then a sunk list, a line for each one awake: their picture (head and shoulders from their own sheet: race, colour, hat), their name, their level; you first, lit as the recipe you are on is, with a small "you". At the foot where you are, and how many are awake and asleep.
- Eight lines at most, fewer where the screen is short (a phone on its side), then "(3 more)". Nothing moves in. On a phone, a tap on the goals, as before.
- Looked at with four players of four races, two in hats, by day and by night. The first sun was a small square: drawn again round, with orange rays.
- Tests: the window the frame after the key, in the middle, 150 px wide, nothing animating; the day, the hour, the sun, the mark at the hour; you first, lit and tagged, the other after, each with a picture; all inside the window; night falling while it shows turns the sun to the moon and moves the mark. 335 unit, 154 browser.

## Iteration 99: a sword cuts, a spear is thrust
- User: "the sword animation looks like breaking a bloc... not like attacking". It did: the sword and the spear were drawn on the axe's frames, and the sheet's axe is a chop down onto a block that stays planted there.
- Now (new web/js/swing_art.js, characters.js): an attack with a sword or a spear no longer uses the sheet's swing. The body is the standing one, stepping back one px then two or three into the blow; the weapon, the hand on it and its streak are a small sheet of their own (8 frames by 4 ways faced), laid over the body, under it when they face away. The sword starts on the sword arm's side and crosses in front to the other side with a wide streak behind it (side on: from over the shoulder to out in front, not down to the feet). The spear is drawn back, pushed out 11 px and drawn back again, a short streak behind its point. The hand takes its colours from the person's own sheet.
- Unchanged: breaking or crafting with a sword or a spear in hand is still the chop (tool_art.js rows), and so are the axe, the pickaxe and the hoe, where a chop is right.
- Looked at on the cat for every frame and way faced, then on real frames in play (24 per weapon). Tests: the sword's blade goes from the left of the body to the right of it passing below the feet; the spear's point goes out 10 px and comes back; in play each frame draws the weapon's frame for the way faced over the standing body. 340 unit; 154 browser passed, one failing in the Tab window's test (the other session's work in progress).

## Iteration 100: speech bubbles in pixels, piled, with the name on them
- User: "make chat bubbles pixelated, and handle multiple chat bubbles correctly. when one goes, others go down etc. beautiful and readable", then "they look bad with the username position".
- They were a smooth rounded box with a stroked edge, one row cut at 60 letters, each kept at the height it was given when said (so a later one hung in the air once the first had gone, and a fourth sat on the third).
- Now (new web/js/bubbles.js; render.js calls it): drawn in the text's own pixel (2 px): stepped corners, a dark edge, a shade along the foot, a stepped tail. Wrapped to five rows of 304 px, then "…" (the chat keeps the whole line). A speaker's lines are a pile, the oldest lowest with the tail, at most three (a fourth lets the oldest go at once); when one goes the others come down onto its place. Two speakers' piles do not cover each other; a pile stays on the screen. A line stays long enough to be written and read.
- The name: while someone speaks it is not written over their head. The tail points at the head (over the health bar when it shows) and the name is a dark tab on the top of the pile; a bubble is never narrower than its tab.
- Tests (test_e2e_bubbles.py): the edge is one hard colour two px thick, corner stepped off; a long line whole in its rows; oldest lowest, 2 px apart; a fourth drops the oldest and the pile lands on its place; an endless word is broken and ended. 343 unit; 157 browser passed, two that fail only in the parallel run passed alone.

## Iteration 101: a wake that stays, a day piece that closes at dusk, a runner's dust
- User's backlog: "sprinting particles in water disappear when going out of the water weirdly all at once", "day music continue at night, find a nice way to end it or transition to a night music", "improve particles when sprinting on ground".
- The wake (swim.js `drawWake`): it was drawn only while its swimmer swam, so every mark went the moment they stepped out. It is its own drawing now, also for someone on land: each mark fades in its own time where it lies. Going back in keeps the marks left.
- The music (audio.js `moments`): a piece remembers the hour it began in. When the hour turns on it, it is not cut: it plays the pass it is in to the end and closes on its last chord, receding over 12 s; then 6 to 12 s of silence (`SOUND.turn`, not the 50 to 140 s between pieces) and the new hour's piece comes in from far. The same at dawn.
- A runner's dust (effects.js `kickDust`): it was three specks. Now each footfall throws a puff back from the heel (two big pieces that go quickly, smaller ones that drift up and thin out) and three bits of the ground itself, kicked up behind, that fall back and lie a moment: green on grass, sand, stone, earth. Walking is unchanged.
- Looked at on real frames of a sprint. Tests: night falling on a day piece (it plays on, ends within its pass, a night piece within 12 s). 160 browser passed.

## Iteration 102: the water halves your speed
- User: "speed in water should be decreased, half of ground speed."
- Now (sim/constants.py `SWIM_PACE = 2`, movement.py `stride`): a tile swum takes twice a tile walked: 0.4 s swimming (2.5 tiles a second), 0.2 s at a sprint (5), from the tile you swim in. Boats are unchanged. The server says its pace in its hello (`swim_pace`) and your own walk on screen (walk.js `speedAt`) goes at it; a server from before says nothing and the page keeps the old speed. For the local agents nothing to learn: it is the server that paces them.
- Takes effect on the play server at its next restart.
- Tests: the strides in the water (0.4, 0.2; 0.4 on three pieces of food); in Chrome 2 to 3 tiles swum in a second, 4 to 6 at a sprint. 345 unit; 158 browser passed, two that failed in the parallel run passed alone.

## Iteration 103: the hours' light, a smaller Tab window in its corner, the goals in the HUD, an angry tusker
- User, on what Tab shows: "its beautiufl but a little bit too big. also day/night cycle shouldn't be all yellow and all dark, it is a gradient. make a nice pixelated gradient, and rework that day and night lightning across the game"; then "make the tab daylight bar gradient more pixelated"; then "boar should be more agressive when hit. + tab menu should be in left right corner + improve goals design and integration within hud" (read as the top right corner: the goals are top left).
- The light of the day (web/js/daylight.js, c803ebc): the world was plain day until a twentieth of a day before night, then one blue. DAYLIGHT is the day as a row of moments, each with the sky's colour, the light's (what the picture is multiplied by) and a thin wash; between two moments they are mixed. Two tries were wrong first, seen on real frames at seven hours: warm tints multiplied over grass are olive mud, and so is a wash of a sixth. The twilights are now mostly the night's blue coming or going, the wash a tenth at most.
- At night the lights are worked out an art px at a time and enlarged: rings of whole pixels, small steps at the rim, a checkered edge between two steps anchored to the land's grid. They were smooth round glows added over the picture.
- What Tab shows: its own pixel, a size under the recipe book's (300 px wide, it was 450); in the top right corner (under a phone's buttons there); its day's bar the sky's colours as flat bands with a checker where two meet, in cells of two px (the first gradient, 136 x 6 with four steps, read as smooth).
- The goals (style.css, goals.js): no sheet of paper. A part of the HUD as the hearts and the key hints are: light text with a dark edge, a pip for each goal lit when it is done, the next three each with its picture in a small cell and a box that is ticked, the help's key under them.
- A tusker that is hit (sim/wild.py): it went on as before. Now it is angry for twelve seconds from the last blow, at the one who hit it, from ten tiles (it sees four); it trots into line with them, paws the ground half as long, runs eleven tiles, shakes off a tree in half the time, rests half a second. It stamps when it turns angry, and a red mark beats by its head. A calm one is as it was.
- Tests: the light all day (no jump, white only mid day, bluest mid night, wash a tenth at most); the bar (68 x 3 cells, few colours, checkers, a long flat band); the lights (every art px one colour, steps, the fire's ground far brighter); the goals' look and pips; the window in its corner; the tusker in the simulation (lines up, half the windup, the blow, calm again after) and in Chrome (the mark's twelve red px, and it comes).
- The full runs while this was made: 157 to 158 of 161 passed each time, never the same failures. Read, not guessed: another session was saving game files in this folder while the tests ran; a player "did not get in" twice (the server's log, now kept, shows them connect and be gone a second later, with no error); the boat test's key was let go late (its pond is deeper now); the x-ray test counted a second painting of one tile, which is right when land comes in beside you (it lets three more than the tiles walked).
- Not done: the play server needs a restart for the tusker; the cause of the players who did not get in.

## Iteration 103: eating halves your speed too
- User: "eating things should also slow down player by half. accumulation possible with water slow movements".
- Now (constants.py `EAT_PACE = 2`, movement.py `stride`): while you eat a tile takes twice as long, walking or at a sprint, and the water doubles it again: 0.4 s a tile walked eating, 0.8 s swum eating. Said in the hello (`eat_pace`) and kept by your own walk on screen (walk.js `speedAt`). On the play server at its next restart.
- Tests: the strides eating, on land and in the water. 346 unit apart from the stylesheet's size (the other session's file, over its limit); 160 browser passed, one that failed in the parallel run passed alone.

## Iteration 105: the inventory, a window where everything keeps its place; the goals, a card
- User: "now: rework inventory into something stable and more readable, more intuitive. dont forget this game should be playable keyboard only. inventory should be beautiful". And, on the goals of iteration 103 (loose outlined text over the land), with a picture of it: "goal menu looks bad and weird".
- The inventory was a strip of small pictures without names: it wrapped, and its size and the order of things changed as you picked things up; its keys looked for "the nearest card" in a direction; nothing could be put on, taken off or moved without a mouse.
- Now (web/js/bag.js, css/windows.css): a window in the recipe book's manner, one size (214 x 190 of its pixels). At the top what you wear, five cells (an empty one shows faintly what goes there). The pack, three rows of ten cells. Your bar, the ten you play with, each with its key. Under them the thing the cursor is on: its picture, its name and how many, what it is for, a line about it, and what can be done, each on a button with its key.
- Stable: a thing stays in its cell until you move it, an empty cell stays empty, a new thing takes the first empty cell (ui.js: slots, as before; the window now shows the cells themselves). More than forty kinds: a second page of the pack.
- Keys: the arrows or W A S D move the cursor a cell at a time, on a grid (up from the bar is the pack, up from the pack what you wear). Enter takes in hand and closes (from the pack the thing comes onto the bar, in place of what you held, or the first empty cell). E eats, puts on, takes off. X picks a thing up and X puts it down: the two cells change places. A number sends it to that cell of the bar. Esc lets go of what is carried, then closes. No key acts on the world behind. A mouse: a click moves the cursor, a double click takes in hand, a thing is dragged from one cell to another.
- First look, corrected: the words about a thing were squeezed beside two buttons and cut, "Take off" ran out of its button, the counts were as big as the pictures: the foot is now three lines of words, then the buttons in a row, the counts small in a corner; the window grew by what that took.
- The goals: a card in the manner of what Tab shows, in the other top corner (its pixel, 122 wide): the title and how many are done, that as one bar filling from the left, the next three in a sunk list, each a line of one height with its picture in a cell and a box at the right, the help's key under them. (The pips of 103 lit here and there, as goals are not done in order; the boxes sat wherever the words ended.)
- style.css had outgrown its 300 lines: the windows drawn in the book's manner (the book, the goals' card, what Tab shows, the inventory) are in css/windows.css.
- Tests (tests/e2e/test_e2e_bag.py): the window's size and its 5, 30 and 10 cells; the bar's ten in order with their counts and keys, the rest in the pack's first cells; by name with its buttons; a new thing in the first empty cell, a count growing where it is, a cell emptied staying empty, the window unmoved; then with keys only: the cursor over the grid, X and X, a number, E on bread (eaten, the window stays), E on a hat (worn), Enter on it worn (off), Enter on a thing of the pack (on the bar, in hand, closed), it opens on what you hold, Esc twice. The pixel test holds the inventory and the goals' card to one whole pixel size each. 354 unit; the browser files this touches, 36 of 36 (the whole browser suite was not run again: another session is saving files in this folder, and a run during that is not a clean one).

## Iteration 104: a help of four short pages; capitals shout; bubbles hold a whole line
- User: "make help menu beautiful. it is awfully unreadable", then "the help page looks big compared against overall game pixelization".
- The help was a small panel in the corner: four long lines, every key run together with dots. Now (new js/help.js, css/help.css) a window in the middle, in the recipe book's manner at the pixel of what Tab shows (--w): four pages (Move, Do, Carry, Talk), five rows at most, a row a key drawn as a key and a few words on one line. Left and Right or a click turn the page (the arrows do not walk you meanwhile), H or Esc shuts it; every page is the same size. It no longer opens by itself at each join.
- User: "make shouting sounds more like shouting. No need to start with "!" just type in uppercase to shout", then "make shouting a bit less loud".
- A line in capitals is a shout (main.js, babble.js `shouted`: three letters or more, so "OK" is talk; "!" still works). Its voice (babble.js `SHOUT`): five semitones up, each syllable held as long as its recording lasts and falling three semitones, through a soft breaking curve, its bite at 2.4 kHz brought up, an echo after it; at the level of talk since the second remark. Its bubble shakes half a second as it lands. I cannot hear it: the numbers are a first setting.
- User: "higher limits ... the limit dialogue looks really weird": a bubble cut at five rows with "…". Now 400 px wide and seven rows: all a chat line can be (200 letters), nothing cut.
- The eating test expected a full walk while chewing: five tiles now (EAT_PACE).
- Tests: test_e2e_help.py; capitals shout and go through the curve, small letters do not. 354 unit, 164 browser.

## Iteration 106: the inventory is only its cells; the goals' card at the land's pixel; a line about every thing
- User, on iteration 105's inventory: "make inventory more intuivie and easy to use. only keep the description of the itme (the funny one) no need to say its a material, it can be eaten etc etc. just the funny description. also the description takes too much space. do mockups in an html page so i choose"; then, on the goals' card: "put goals tab redesign in there too. current one is too small and looks weird against the overall game pixelisation".
- The mockups (one local page, not published: it uses the pack's art): five inventories (only the cells with a label on the cursor's cell; one line under the bar; Enter opening a list of what to do; what you wear down the side; no window, the pack rising over the bar) and three goals (one at a time; the card at the land's pixel; the game's paper panel). The user: "go with 1 only the cells. go with B for goals".
- The inventory (web/js/bag.js): the strip under the cells is gone (a picture, three lines of words, a row of buttons). There are the cells, a label that hangs on the cell the cursor is on (the name, how many, the thing's funny line; moved along so that it stays inside the window; under the cell for what you wear), and one line of keys under the cells, each with its word for the thing you are on ("eat", "wear", "take off"), dim where it does nothing; a word can be clicked. The window is 214 x 155 of its pixels (it was 190 high). The keys are as they were.
- A line about every thing (web/js/blurbs.js): the twenty that are not made had none (wood: "Formerly a tree. It had plans."; an egg: "Breakfast, or a chicken. Your call."; milk: "The cow was not consulted."). The unit test holds one for every recipe and every one of those.
- The goals: the same card, in the recipe book's pixel, the land's (3 screen px an art px; it was 2, what Tab shows keeps 2 as asked before), 128 wide, without its bar: the title and how many are done, the three lines, the help's key. On a phone it keeps the smaller pixel, for room.
- Tests: the window's size and cells; the label by name with the thing's own line and nothing else (no strip, no buttons), inside the window; the keys' words on an axe, on bread, on a hat, on a hat worn, while carrying; the rest of the keys test as before. The goals' card: its width, its pixel (the root's, 3), nothing done, then one. 354 unit; the browser files this touches, 36 of 36.

## Iteration 105: a tusker that reaches you, and its dust
- User: "boar issue: angry particles sucks. Add particles on charge. he has trouble charging the player also, never hit him almost."
- Why it missed: it charged along the longer way to you from wherever it stood, so past you unless you were dead in its line, and at where you were when it began to paw. Now (sim/wild.py): calm too, it trots into line first (`TUSKER_TROT`); it aims again as it sets off; running, it leans a lane toward you every three tiles while you are still ahead (`TUSKER_LEAN`). One step aside is no longer enough; two are.
- Its dust (world_decor.js `tuskerFx`): pawing, a puff thrown back from the hoof at each scrape; charging, earth torn up behind it all the way (big puffs and bits of the ground it runs on). Angry: steam from its snout to both sides every half second and a red spark off its back; the moment it is hit, a burst of red and orange sparks with the dust. The red mark over it stays.
- Looked at on real frames (pawing, charging, hit, angry). Tests: it comes into line and runs you down where you stand; a lane aside while it paws, it still does; two aside, it runs past into the tree. 355 unit. The server's part shows at its next restart.

## Iteration 107: the goals' card small, in the inventory's pixel; H puts it away
- User, on iteration 106's card: "goals are way too big. find a smaller design that fit hte game pixelisation density. use inventory as a base for pixel density"; then "add H key to hide goals".
- The card kept its pixel (the inventory's, the land's: 3 screen px an art px) and lost art px: it was 128 by 110 of them (384 x 330 on the screen) with the book's 18 px cells and 20 px lines; it is 106 by 62 (318 x 186). One line at the top: the title, how many are done, and two keys. Three lines of 13: the small picture of a thing (the 11 px one the bar's slots hold) in a cell, its words in the small text, a box of 6. No foot.
- H puts the card away and brings it back (kept from one day to the next; a line of news says so when it goes). H was the help's key, made that day by another session with its four pages: the help is ? now (and F1, and a click on the card's "help"); its window says Esc to close, and its first page has a row for H. That choice is mine: the user asked for H, and one key cannot do both.
- Tests: the card's size on the screen and in its pixels, no words cut, each small picture in its cell, the boxes in a column; H and H; the help's tests press ?. 355 unit; the browser files this touches, 37 of 37.

## Iteration 108: H is the help again, G the goals; the goals are away unless asked for, with a tab early on
- User, on iteration 107: "h hsould be help. g = goals. by default on the screen do not show goals, well add a hint in early game". (I had given H to the goals and ? to the help: wrong.)
- Now: H is the help (and ? still opens it); G shows the goals' card and puts it away. The card is away unless you asked for it (kept from one day to the next). Early in the game, while fewer than four goals are done, a small tab sits where the card would be: "G goals 2/12" (a click on it is the key; on a phone it is always there, having no keys). A goal done while the card is away is said in the line of news. The words on waking say "G: goals. H: help."
- Mine, and seen at once by the tests: the words on waking for a phone had quotes inside a quoted string, and the page would not load (for about two minutes, on the play server too: the page's files are served as they are saved). Another session mended the line before I did. A file of the page is to be checked (`node --check`) before it is saved where the game is served from.
- Tests: away by default with the tab; G shows the card (and the tab goes); H opens the help and shuts it; G again, the tab with how many are done; a goal done while away is said. 355 unit; the browser files this touches, 35 of 35.

## Iteration 106: the game is called Nexel Worlds
- User, after a long search for a name ("megastructure looks awkward"; a fusion of two words, the -xel ending, easy to say and to spell in French and in English): "go with nexel worlds". Nexus + the -xel of pixel; a player's own world may be called a nexel.
- Where a player or a reader sees the name: the page's title, the brand panel and the join box (index.html), the readmes, the demo's pages. The code, the package, the repository, the saves and the demo's address keep `megastructure`: a rename of those is a separate decision.
- Checked by web search only: an unreleased prototype on itch.io is called Nexel, and there are companies with near names (Nexelon, Nexl). No trademark or store search was done.
- A slip: the script that renamed index.html opened it for writing before it had read it, and left it empty for about a minute (the page the play server serves). Restored from the last commit plus the new name. That file had changes of the other session that were not committed: they are lost, and I do not know what they were.

## Iteration 107: the first screen is the classic menu
- User, of five propositions on the mockup page: "go with the classic menu. one thing is wrong: player name position is awkward. go on fix and implement". Before it: the name of the game, "megastructure looks awkward", is Nexel Worlds; the line under it is one of thirty of ours, at random (js/splash.js), in place of "no rules, no safe zones".
- It was one small box in the middle. Now (new js/title.js, css/title.css; index.html's #joinbox): the world whole behind; on the left NEXEL WORLDS large, at three of the land's pixels, and the random line; on the right one window at the pixel of what Tab shows: a card with your character breathing beside the field your name is written in (the name floated over a character outside the window in the mockup: the awkward place), the five races, then Wake up, Just watch, Help, Sound.
- Keys: the field has the caret from the start; Up and Down move through the rows, Enter takes the one lit (Wake up by default; with no name the field turns pink and asks); on the races' row Left and Right change who you are. The mouse does the same. Your character is drawn in the colour your name will have in the world.
- While it shows, the brand panel and the list of who is awake are away (the name is said once). Just watch puts the menu away; the brand brings it back.
- A narrow screen: the name, the line and the window one under the other; rows 34 px for a thumb; no Help row (it is a list of keys).
- The demo's build added its "what's new" link after the old button: it adds a row to the menu now. races.js: the picker has no inline styles any more, and `pickRace`.
- Tests (test_e2e_title.py): the name once, the window whole, your name in it beside you; Enter with no name; the rows by the keys; a race by the arrows without touching the name; sound; watch and back; a join. On a phone: one under the other, a row 30 px or more. 361 unit; the browser suite passes, three that failed in the parallel run for other reasons passed alone.

## Iteration 109: the sheet is read once for the tools' rows; two tests that had been failing since the drops
- User, from the browser's console: "tool_art.js:92 Canvas2D: Multiple readback operations using getImageData are faster with the willReadFrequently attribute set to true".
- The tools' rows (web/js/tool_art.js) were made by reading the axe's frames one at a time from the sheet's own canvas, 96 reads at load. The axe's four rows are now read once, from a small canvas made for reading, and each frame is cut out of that in memory; the sheet's canvas is never read. Not done by marking the sheet for reading: everything drawn of a person comes from that canvas, and a canvas marked so is kept off the GPU.
- Checked in Chrome before it went where the game is served from: the sheet's 384 x 1728 px hash the same before and after (3589849898), and the console says nothing (it warned once before).
- Found by the tests run for it, on the code as it was: two of the "living" tests failed. One was mine since the drops went by chance (33fc4ae): it kills a hen and waits for its meat, and I had not given it the tests' switch that makes drops sure; it failed four times in ten. The other asked a hit hen to be four tiles from where you end up: it runs from where it was hit while you walk on beside it; it now asks that it be three tiles and more from where it stood. Three runs of the file after: 12 of 12 each.

## Iteration 110: the first screen has an island of its own behind it
- User: "see the opening game screen ? make the background a hardcoded map scene with nice animations, nice showcase. that loads fast."
- Behind the first screen there was the world you are about to wake in, once the server had sent it: in the demo, once Python had started, many seconds of an empty screen.
- Now (tools/build_title_scene.py, web/js/title_map.js, web/js/title_scene.js): an island made by hand, built in a throwaway world with the game's own tiles and baked into the page as the page takes land in: six blocks of 32 x 32 (26 KB), and one block of open sea used for everything round them. On it: a house with its door and mailbox, paths, a fire with two chairs and a picnic blanket, a field at every age with a well, a pen with a coop and a trough, a pond with a stream and a bridge, a pier with a boat, a hill three steps high with a flag, trees, bushes, rocks, flowers.
- It is drawn by the game itself, nothing special: the blocks are handed over as a server's would be, far from where anyone lives, and a small cast is said to be there ten times a second, as a tick would say. Mira walks from her door to the field, waters it, comes back; Tobi chops at a tree and rests; Pip sails round the island; Lou, a duck, swims the pond; three hens and a chick keep to their pen, two cows to the meadow. A day lasts 200 s, so the hours' light, dusk and the fire at night pass; the view drifts slowly. The page asks the server for no land while it plays.
- Waking up or "Just watch": the island and its cast are forgotten and the world's own land is asked for.
- Measured in Chrome: showing 0.5 s after the page is asked for.
- Tests (tests/e2e/test_e2e_title_scene.py): there at once, six blocks far from the world, the cast by name; four seconds on, each has gone its way, the boat and the duck on water, the hens in their pen, the hour and the view moved, and the server was asked only for recipes, who is there and its numbers; "Just watch" brings the world's land and the view to its middle; a player who wakes has none of it. Two land tests: the glide goes past the first screen before it measures; the other no longer needs a block without water (a player who wakes by a lake has none).
- Not done: the cast do not talk; nothing is carried or built; on "Just watch" the world's land still takes the time it takes.

## Iteration 111: a world can ask who you are (email, a code, a signed ticket)
- User: "do you think it is possible to add a full login process and secure ?", then "no standard email workflow ?", "can we do that for free?", "lets setup a fully local setup with mailpit before buying anything", "ohh yes go on".
- Before: a name belonged to the first browser that typed it (a random secret kept in that browser, its hash in the save). Another device, or a cleared browser, and the character was lost; the AI players' secrets could be guessed.
- New, apart from any world (src/megastructure/account/, `python -m megastructure.account`): an account is an id and an email. POST /code mails six digits (ten minutes, five guesses, five codes an hour for an email), POST /login gives a session (thirty days), POST /ticket a ticket for one world's address for two minutes, signed with Ed25519; /logout, /forget (the account and its email deleted), GET /key. Codes and sessions are stored hashed with a key of the service's own. Mail is plain SMTP: Mailpit here (brew install mailpit; 127.0.0.1:1025, inbox on :8025), a real service later by changing the address.
- A world with `--accounts <url>` (gate.py) lets in a ticket (a person) or its own `agent.key` (local programs: MEGASTRUCTURE_AGENT_KEY for client.py). It never sees an email. An account has one character in a world (table `owners` in the save): the first name it asks for, new, or a character from before whose secret this browser still holds. After that the character opens to the ticket only. The QA tools (--dev) are not for who came by ticket. Ten refused hellos close the connection.
- The first screen (js/account.js, title.js): one step on the screen at a time, your email, then the code (six digits typed log in by themselves), then who you are as before with a Log out row; back later, your name is there and cannot be changed. A world without --accounts, and the demo, are as they were.
- New dependency: cryptography (the signatures). The HTTP side is Python's own http.server, not websockets as I had said: a browser's fetch needs plain HTTP.
- Tests: tests/test_accounts.py (a code once, five guesses, running out, limits, forget, a ticket for one world, the door, an old character claimed, the mail itself to a small sink), tests/e2e/test_e2e_account.py (the three steps in Chrome, no way in without a ticket, back and out).
- Tried by hand through Mailpit on a scratch world (:7793). The play server (:7777) is untouched and asks nothing.
- Not done: HTTPS (a tunnel or Caddy, the day it is online), a privacy note, a page to delete your account (the service can, nothing on the screen asks), random secrets for the thinkers (the world's key covers them when the door is on), one name across worlds.

## Iteration 112: the island's people choose what they do; no cobble is cut at a tile's edge
- User: "user actions are too repetitive. the pavement (stones on the floor) looks bad , glitchy, textures arent connected".
- The pavement. Looked at the sheet first: it holds a strip three tiles long each way, a square of four and one tile on its own, no turn, no crossing. The game picked a cobbled tile at random among nine of those cells, so every tile cut its neighbour's stones at the edge. That was the game's own painter, not the island: the same in the world.
- Now (web/js/pavement.js, 55 lines): the stones are laid again, the pack's own (5 to 7 px wide, 5 or 6 high, its two greys read off its sheet), in rows: one row flush with the tile, the next half a stone along, each a px or two off its place, over four tiles by four. A stone of the half-along rows lies across two tiles and each paints its part when both are cobbled, on the same level; where the cobbles end it is pulled inside, the one beside it making room, or left out. One sheet of 64 cells made at load (sixteen tiles, each cobbled to its west or not, to its east or not); a tile is still one cell of a sheet, so the land's painter and its tests are as they were.
- Test (test_e2e_land.py): on a path that runs, turns, forks and widens, every stone found in the px is whole (w x h - 4 px, one of the pack's sizes), about four to a tile.
- The people. Each had one loop (Mira to the field and back, Tobi at one tree, the boat and the duck round and round), the same at every visit.
- Now (web/js/title_cast.js, title_talk.js; title_scene.js is the island's clock): each has things they like doing, with weights, and when one is done chooses the next by chance, never the one just done and only what can be done now. Twenty errands, written as generators (a `yield` is a tenth of a second): water, harvest and sow, chop, mine, berries, fruit, flowers, the well, the sign, feed the hens, eggs, milk a cow, post a letter, fetch it, a picnic, a view (pier, bridge, hilltop), a stroll, a talk, the fire, a sail. They find their own way (a search over the island's tiles, a level at a step), the places are baked with where to stand and the way to face (beside a small thing: from below a head hid the rock being mined).
- What they do is done to the island, through the game's own tile events, so the game shows it as it shows any: a felled tree falls and grows back from its stump, wet soil darkens and its wheat grows a stage, ripe wheat goes to the one who pulled it, a picked bush is bare for a while, the mailbox shows its letter, the trough is full, the boat is tied up at the pier when Pip comes ashore and gone when he sails.
- They talk: one calls to another not far, who waits; a line and its answer (26 pairs, 8 for the fire, a few words to themselves after some work), in the game's bubbles, not in the chat. In the evening the day's work is left and they come round the fire, going off between two whiles by it.
- A fifth, Nell (a cat), who looks at things, picks flowers and talks most. The dice are thrown anew at each visit (the clock's seed is the hour; a test gives its own).
- The view goes slowly after one of them, then another (it drifted on a sine before, often over nobody).
- Measured, the clock run by hand for two of its days (4000 steps, 40 ms): three seeds, 10 to 12 kinds of errand each for Mira, Tobi and Nell, about 190 tiles changed, about 80 lines said (70 different). Before: one kind each, none, none.
- Found by the new test on its first run: the boat jumped two tiles joining the sea road (the road's first tile was skipped). Fixed.
- Tests: test_e2e_title_scene.py (3): there at once; a day and a half by hand, twice with two seeds: many kinds, never twice running, speech, tiles changed, the fire, the boat in and out, trees + stumps constant, nobody ever on water on foot or in something solid or a tile further than a step, and the two plays differ; waking leaves nothing of it, not a bubble.
- They keep to the paths where it is not much longer: a way is the easiest, not the shortest (a path or a bridge two a tile, grass three, the field's soil six).
- Not done: nothing is carried in the hand between errands; Lou only swims; the house is never entered.

## Iteration 113: a bridge's ends, a gate seen from the side, a tree back from the brink, a chair turned to its fire
- User: "bridges are creating black ugly borders. the barrier (chicken barrier) entry portal is ugly does not work on this isde. redesign the tile. the trees on the mountain borders looks bad (general game redesign ?? how to fix that ??)", then "chickens shouldn't be able to open the doors" and "the righ tchair in the firecamp is turned at the wrong side".
- Looked at each in Chrome first, enlarged, and read the px. All four are the game's own drawing, not the island's: the same in the world.
- Bridges. The black bar at each end was a see-through px: the land a bridge ran onto was painted as a shore towards it, a shore's edge has a clear px along it with water behind, and there was no water there (water is painted under water tiles and the ones round them; a bridge was not water), so the dark behind the world showed. Now (web/js/bridge.js): water under every bridge (water.js: a bridge is depth 1); the land a bridge runs onto goes on to it with no shore between, only at its ends along the way it runs (beside it the bank is still a bank); and its ends are the pack's end pieces, never used, with their posts: on land over plain planks that run to the bank, out in the water (a pier) the ones whose posts stand in foam.
- Gates. Two faults. Drawn from the front wherever it stood: in a pen's east side, a door across a fence seen end on. And opening, it showed the sheet's cells 0, 1, 2, 3: the sheet alternates a gate hinged on the left and one hinged on the right, so it changed sides as it opened and never opened fully. Now (sprites.js, world_decor.js): in a fence that runs north and south it is the pack's side-on gate (two leaves, 32 px high, hung between the posts over and under it), five frames each way with the hinge on one side; a fence's rails go on to a gate beside it (its hinge post, and for the door to shut on), not to one over or under it.
- A gate, or a door, opened for anything beside it: a hen in its pen swung the gate open (it could not go through: animals work neither, sim/animals.py). They open for people only (render.js).
- Trees on a hill's edge. Measured the sheet: an edge tile is not flat all over. Its south edge is the cliff's face from the 8th px down; its west and east edges a ledge 7 px wide. A thing's foot is at the bottom of its tile, in the middle: a tree on the south edge of a plateau stood on the face of the cliff. No redesign of the land was needed: what grows or lies on such a tile (trees, stumps, bushes, rocks, mushrooms, flowers) is drawn back from the drop (sprites.js brink): 8 px from one to the south, 4 from one to a side, less from one only at a corner; not by water. Its tile and what it stops are unchanged; a tree felled there falls from where it stood. Worlds already made need nothing.
- Chairs. Every chair was the sheet's first of four (facing east). A chair is turned to a table or a fire a tile or two from it; with neither, east as before.
- Found by the full run of the browser tests, both real: (1) "ToolArt is not defined" on a page that reloads itself: assets.js starts loading the sheets and calls ToolArt when the character's is in, but tool_art.js came after it in the page; with the sheet in the browser's cache it could be in first, and the page never started. tool_art.js now comes first. (2) My swim test read "is it sprinting" after letting the keys go; it now asks while they are held.
- Tests (tests/e2e/test_e2e_edges.py, 4): the land at a bridge's ends is solid all over, water under every tile of it, a post at each end and none in the middle, foam at a pier's end; a gate side-on in a north-south fence and from the front in the other, opening through every other cell to the last, the fences' rails; a hen beside a gate leaves it shut, you beside one open it; a tree's place on each edge of a plateau, in its middle and by water; a chair by a fire, over and under a table, on its own.
- Whole suite after: 396 unit pass. In Chrome, 178: the last whole run had 177 pass and one fail, my own island test (it took Pip to be at sea four seconds in; the dice are new at each visit and in that one he was coming ashore). That part of it now plays a known seed: five runs of the file pass. The whole suite was not run again after that.
- Not done: a body (a person, a hen) on an edge tile stands where it stood (3 px up, as everywhere); walls and fences on an edge are not moved (they join their neighbours); a bridge one tile long has no posts (the pack has no piece with both ends).

## Iteration 114: furrows, a house in its place, a bubble's tail, a letter's bubble, shouts across the island
- User, one after the other: "see the weird line in the field?", "house layer is weird, it goes above mailbox and players in the welcome screen. also can you add 1 or 2 player shouting in welcome screen ? funny", "dialogue arrow has a weird line separating from the text bubble", "TEXT BUBBLE IS cut at house top".
- The line in the field. Dumped the tilled sheet: it is a patch with a line round it, drawn 10 px inside its outer tiles, made to lie on grass with nothing planted on its rim. Here every tilled tile is planted and at sea level it lies on bare soil of the patch's own colour: all that showed of the patch was its line, a rounded box inside the field with a row of crops outside it. Tilled soil is furrows now, over the whole tile (web/js/furrows.js): a darker line every 4 px with the light of the ridge under it, both broken here and there, in the sheet's own tones, running on from tile to tile. Up on a hill the ground under is grass, and the pack's patch is kept there.
- The house. Houses were drawn last, over everything, so the front wall (a tile and a half high) hid the head of whoever stood before it, and the mailbox. A house now takes its place among the frame's things, at its front wall's row: what is in the room or behind is under the roof, what stands before it is over the wall. (Someone in the doorway is seen there, not behind the door.)
- The letter over a mailbox: its picture was taken from the sheet's row 64; the letter's bubble begins at 62. It never showed before (the house hid it).
- The bubble's tail: the shade along a bubble's foot ran across over the opening of its tail, a line between the two. The paper runs down into the tail now and the shade is at the tail's own foot.
- Shouts (title_cast.js hail, title_talk.js): now and then someone in sight shouts across the island and is shouted back at, and whoever else is by laughs; 16 calls and answers, never the same twice running, not in the middle of a word with someone. The first comes four to seven seconds after the island wakes.
- Seen while filming it: one of them could stand in the house's doorway to talk (under the roof, unseen). Nobody stands in a doorway or indoors now.
- Tests: tilled soil is furrows on a field's rim as in its middle, the patch on a hill; the house's front is drawn before you at its door; all of the letter's bubble; the paper over the tail; the island's run counts its shouts (eight or more in five minutes, the first within ten seconds). 398 unit, and the browser tests of what was touched (67) pass; the whole browser suite was not run again (stopped by the user while it ran).
- Then: "text of dialogue is not centered within the text bubble, it is a bit high in fact". Measured in a screenshot: 2 px of paper over a capital, 6 under it to the foot's shade. The letters are one font pixel lower (bubbles.js): 4 over, 4 under, a g's tail coming down to the shade. The bubble test measures it.
- Not done: with a house in the frame's order, flames and smoke are over its roof where they were under it; the reply to a shout may come from someone out of sight.

## Iteration 115: the island is heard, under the music
- User: "keep the osunds effect of the scene but lower volume than music. not too low to not sound too weird".
- Looked first at what the first screen played: nothing of the island. A sound of the world is heard from where you are, and on the first screen you are nobody, so every one of them was dropped; and its people's lines were bubbles only (they never went through the chat, so no voice).
- Now (audio.js `ears`, `heard`): when you are nobody the page can be lent ears; the island lends the middle of its view (title_scene.js). Its sounds are the game's own with nothing added: an axe on a tree, the tree coming down, water poured, a splash at the pier, eating, a gate, the duck's strokes, and its people's voices and shouts (their lines now go through babble).
- How loud. Measured the files at their gains (loudest 50 ms): the music's usual level -29 dB, its loud passages -22; a syllable -29, an axe's blow -15, a tree's fall -14, water -21, a gate -22. So through the island's ears a voice is half what it is in the game and everything else a quarter (SOUND.scene): a voice in the middle of the view sits 6 dB under the music, an axe's blow about level with it, the rest under; all of it less from further, nothing from past 12 tiles (a shout: 30).
- The field's wheat growing is said without a cause, so without the sound of something growing (here it would never stop).
- A minute of it logged in Chrome with the sound on: 19 strokes of the duck, 13 rustles, 7 bites, 6 blows of the axe, 6 plantings, 2 shouts and their answers, 3 lines said, water, a gate, a creak; volumes 0.04 to 0.46.
- Tests: on the first screen a voice at the view's middle is heard at SOUND.scene.People, a blow six tiles off at half of SOUND.scene.rest, nothing from twenty; both under the music's own number; after "Just watch" and after waking the ears are gone and the world is heard by you at its full level. 398 unit, 35 in Chrome (island, swim, bubbles, social, sounds).
- Not judged by ear: I cannot hear it. The two numbers are SOUND.scene in audio.js.

## Iteration 116: a tree by the water stands back from it too
- User: "weird tree at sea border" (a tree with its foot on the bank and in the water).
- In iteration 113 I drew things back from a hill's edge and left water out ("not by water"), without looking at a shore tile. Dumped it now: a shore tile is cut as a hill's edge is: grass on its top 7 px, then the bank, the foam, the water, where the cliff's face would be; 7 px of bank and foam at a side. So the same fault, and the same cure: `brink` (sprites.js) counts as a drop any side the land is painted as a shore towards (water, a bridge's side), as well as lower ground.
- Looked at it in Chrome with trees and rocks put all round the pond: on the grass, back from the bank, on every side.
- Test: a tree with water to its east is drawn 4 px back, one with water to its south 8 px. 398 unit, 33 in Chrome (edges, island, x-ray, pixels).

## Iteration 117: building is a plan and then the work; houses are built block by block
- User: "create a proper building gameplay. right now building things is hard. and house looks like things that you drop onto the world where it sohuld be built block by block. looks weird. this is a real gameplay update, think about UX and 2d building in a 3d world. should be playable by keyboard only !"
- Looked at what there was. Placing: the tile you face, one press a tile (a click: a tile within two of you). To raise a wall you walked a step, turned, pressed, and again, and walled yourself in. A house: walls drawn as small crates until they closed a room, then the screen drew a roof and a tall front over the lot at once (houses.js): nothing of it was built, it was put there.
- Three things, each working on its own.
- 1. Build mode (web/js/build.js; B, and out with B or Esc). The arrows move a cursor, not you; the view goes half way to it. Space plans the piece in your hand at the cursor (the bar's numbers and Q choose it, as ever); held while the cursor moves, a row. X takes a plan back, or on something built plans to take it down. Every plan is a ghost on the ground. Your character goes to the nearest, stands within reach of it and builds it with the game's own moves (move_to, place, dig: the server checks each as it always did, nothing new is trusted), then the next. What you can walk on is built first, what closes the way last; it stands outside what the plans would close when it can (a search from where it would stand, with every solid plan built: can it still walk ten tiles off?); a plan that fails is tried once more after the others, then turns red and says why. No more plans than pieces in your pack. A click plans, a drag plans a row, shift or the right button takes. All of it by keys alone.
- 2. Walls are themselves from the first one laid (web/js/structures.js). A wall with nothing built south of it shows its front (the pack's plank wall, a tile high, its trim over it: what a house's front was); one with a wall south of it shows its top, a band going on. A door in a run east-west is the pack's door in that front; in a run north-south, an opening under a lintel. Stone walls the same, in stone. Each is drawn in its place among the frame's things, so what stands before a wall is over it; the top just south of you is seen through, it would hide you.
- 3. A roof is laid by hand, a tile at a time (sim/roofing.py, roofs.py): a new piece, `roof`, two from a log. It rests on a wall or a door, or on a roof tile beside it, no further than 3 tiles from a wall; it is its own layer over the tile (the ground and what stands under it are as they were), kept in its own table of the save, sent with the land (`roofs` in a region, a `roof` event). `unroof` takes one back. Under a roof you are sheltered. Drawn a tile at a time too: scalloped where no roof is north of it, an eave where none is south, its sides where none is beside it, the ridge half way down its run; so a roof half laid looks like one, and a whole one like the houses did. Under a roof you see through all of it; in build mode through every roof.
- "2D building in a 3D world": what I took from it. Tall things hide what is behind them, so each piece is sorted with the bodies and the top south of you thins; a roof hides a room, so it thins when you are under it or planning; the cursor rides the land's height; nothing is built on a hill's rim (as before). Not done: stacking (a second floor), walking on roofs.
- An old server (the play world runs until it is restarted) says nothing of roofs: the page then draws houses as it did. A world opened by the new code roofs its old houses once (every closed room the screen used to draw a roof over), so nobody's house loses its roof.
- The first screen's island has its roof laid by the builder, the same way.
- Seen in Chrome, keys only: a ring of 14 walls planned with Space held and built one by one; a wall taken down and a door put in its place; twenty roof tiles planned in four rows and laid; inside, the roof seen through. First try the builder walled itself in; second, it stood outside.
- Broke the page for two minutes on the way (structures.js used a table that intent.js defines later; the live page reads these files): found by my own run, fixed. A page-load check goes before saving a new file from now on.
- Tests: tests/test_roofs.py (3: where a roof rests, taking it back and the save, an old house roofed once), tests/e2e/test_e2e_build.py (2: a wall planned and built by keys alone, taken down, no more plans than pieces; a roof laid a tile at a time, taken back, seen through from under), the house test now checks both drawings (new server, old server), the help has a Build page.
- Not done: a piece bigger than a tile (well, coop) is still put by hand; no stacking or second floors; a roof stays when the wall under it goes; windows are still where the wall's run puts them, not placed; touch has no build mode; the AI players have `place` with `roof` and `unroof` but no "build this plan" tool of their own.

## Iteration 118: the first screen has its music
- Asked: "Make that the home screen song" (High tide, the longer take with the drop after two bars), after "with just
  a gradient at the beginning to avoid it popping out of nowhere".
- Change: `tools/build_audio.py` builds a sixth piece, role `menu` (`music/site/audio/menu_tide_high.wav`, written by
  `music/slowtide.py`); `audio.js` has a third track beside the moments and the boss's: while the first screen is up
  (`titleOpen()`), it loops, comes in over 6 s (level and tone, `swell`), keeps the day's pieces out, and recedes over
  5 s once you are in the world. It starts at the first key or click: a browser plays nothing before one.
- Measured: new browser test (silence before a key; the gain rises, under 0.3 then higher, full and clear after 8 s;
  no moment meanwhile; off 8 s after joining); sound tests 9 of 9, first-screen tests 7 of 7, unit 409.
- Not judged by ear by me; the user chose the piece by ear. The public demo's game build does not have it yet.

## Iteration 118: build mode, audited
- User: "Audit your building interface".
- Played it through on a copy server, keys then mouse, ten states photographed and read (1280 x 760). What was wrong, worst first:
  1. Leaving threw the plans away while the key said "Done (4 to build)". The plans not yet built were dropped without a word.
  2. Nothing said B existed: a wall in hand showed "Place wooden wall" and no more.
  3. The mode was easy to lose: once its message had gone, a thin pale cursor and three small lines were all that said the arrows no longer walk you.
  4. The mouse was half in it: the cursor stayed where the keys had left it, the label under the pointer said "Place".
  5. A door took three moves: take the wall down, wait, place the door.
  6. The lines were long and vague: "berries is not something to build with" ran under the bar; "Plan to take down" showed over bare grass.
  7. The cursor stopped eight tiles out without a sound, and a held arrow started late (the keyboard's own repeat).
  8. A plan to take something down was the same red square as a plan that had failed.
  9. Q went through the food and the tools.
  10. X on a roofed wall took the wall and left the roof in the air.
- Mended (build.js): B leaves and the plans stay on the ground, waiting; the work goes on only in build mode, so out of it your character is yours; "Build: 4 plans wait [B]" is said in the corner. Esc drops the plans (with none: leaves). With a piece in hand the corner says "Build mode: plan a lot [B]". In the mode its first line is "BUILD MODE · leave [B]", in the bar's yellow; the cursor is thicker, on a lit tile. The cursor is where the mouse points and the label says what a click plans. A door on a wall, a gate on a fence: planned in its place (the wall comes down into your pack, the door goes in). Every line 26 letters at most, each key shown only if it does something there ("Take down wooden wall", "Take the roof off", "Take the plan back"). The cursor goes ten tiles and buzzes at its limit; a held arrow steps at once, then every 75 ms after 230. To come down: an orange tile with a cross. Q: the next piece of your bar. X takes the roof first. Falling or leaving the game ends the mode.
- Coming back into the mode puts the cursor on the tile you face (my test took it to be where I had left it: the test was wrong, not the game).
- Tests: test_e2e_build.py (3): the two from before, and one for the audit: B said with a piece in hand, no X line over grass, a held arrow five tiles in 0.7 s, plans kept on leaving and built on coming back, Q among pieces only, a door planned in a wall's place, Esc twice, the mouse as the cursor. 409 unit; 29 in Chrome round it (build, edges, help, keys, ui, bag, the island).
- Not mended: touch has no build mode (the phone); plans are not kept across a reload; the corner's lines are still small text over the world rather than a panel; the cursor cannot go past ten tiles from you (walk closer); nobody else sees your plans.

## Iteration 119: a clip of build mode on the demo's "What's new" page
- User: "Create a build mode showcase video and upload it to demo website".
- The clip (tools/pages/build_mode.mp4, 6 MB, 49 s, 1280 x 720, 30 frames a second; its still: build_mode.jpg): a house from nothing by keys alone, at the game's own pace, nothing sped up. Fourteen walls planned with Space held and built one by one, a door planned in a wall's place, a floor, twenty roof tiles, then in through the door (the roof seen through) and out. A caption says each step and the keys pressed are drawn as they are pressed.
- How it is made (tools/film_build_mode.py, about two minutes, nothing the project did not have): its own game server on a throwaway world; a player in Chrome plays the scene; every frame Chrome paints is kept (its screencast, JPEG); each is given to Chrome's own H.264 encoder (WebCodecs) and the samples are written by the tool as a plain MP4, its index before its data.
- Two ways that did not do: Playwright's recorder needs a download (its ffmpeg); Chrome's MediaRecorder writes a streaming MP4 with no length (3 s shown for 49, no seeking) and softer. Checked the file that is kept: 49.46 s, seeks to 12, 30 and 46 s and plays from there; the Mac's own reader thumbnails it. (My first check said it could not be sought: the little test server could not, not the file.)
- On the demo: the first section of showcase.html ("What's new" on the first screen's menu), with the four keys under it; the README's key line is right again (it said B was the bag).
- Not done: no sound in the clip; not judged in Safari or on a phone (only that the Mac's reader opens it).

## Iteration 120: what the clip showed to be wrong with what is built
- User, having watched it: "Looks weird: window appear out of nowhere ? The door you place does not look like a door ? Wall connect weirdly ? Floor do not cover grass ?"
- Looked at the clip's own frames, enlarged. All four were so, and mine:
  1. Windows came by themselves (one wall in three of a run, a rule kept from the old houses). Nothing is put on a wall now that you did not put there.
  2. The door: in hand and as a plan it was the sheet's "wall with a small hole" (a window, to look at); standing, it was the pack's door stretched from 16 to 22 px over a dark box. It is the pack's door as drawn, between its posts, in the wall's front; the same picture in hand and as a plan.
  3. Walls were two things: a front with a trim over it where they ran east, a wide flat band where they ran north, and they met badly at every corner. A wall is one block now, a tile high: its top drawn a tile up, the same for every wall and edged where no wall is beside it, and its plank front under that where nothing is built south of it. A plan's ghost is drawn the same way.
  4. The floor was the bridge's planks, see-through along two edges (made for water under them): the grass showed in stripes. It is the pack's house floor, solid all over.
- What a wall a tile high costs: it hides the row behind it. So the tops of walls south of you and near (four rows, five tiles to a side) are seen through, as under a roof.
- The clip was filmed again with it (tools/film_build_mode.py, the same scene).
- Tests: a door's picture is the door and not the wall's; a floor tile is solid all over with no grass in it. 410 unit; 30 in Chrome (build, edges, the island, land, pixels).
- Not done: no window to place (a piece of its own, later); a door in a run north-south is still an opening under a lintel, not a door seen from its side.

## Iteration 121: a door in a wall that runs north is an opening, shaded as the game's holes are
- User: "Have you added side doors with shadow effect like holes ?" No: it was the wall's top drawn half see-through, no door, and whoever went through was under the top of the wall south of it.
- Now (structures.js): over the door's own tile the wall's band is open: the ground shows, shaded with the holes' own dark (caves.js: deepest in under the lintel, four steps lighter towards you), the band's edges go on as its posts, and the leaf lies across the way, shut, or back against a post while someone is by it. The top of the wall just south of such a door is left out (it would lie over the way through), so whoever stands in the doorway is seen.
- Seen in Chrome: a yard with a door in its east side and one in its west, a stone run with one, shut, open, and walked through.
- Test: the tile of such a door is dark at its top, lighter at its foot, the ground still under it; a door in a run going east is not one of these; standing in it opens it. 410 unit; the build tests (4) and 19 round them pass.
- Not done: under a roof it is hidden from outside, as everything under a roof is; the leaf is a plain bar (the pack has no door seen from above).

## Iteration 122: walls are thin, on their own tile; nothing of a wall is seen through
- User, with a picture of a yard they had built: "weird wall connexion on the left, and xray that trigger without roof !"
- Built their yard again on a copy (7 wide, a stub of two going east from the west wall, a door south): with the west wall whole it joined well; with one tile of the west wall missing under the stub it was their picture. Two faults, one cause: the walls a tile high of iteration 120.
  1. A block a tile high has its top one tile north of it. It hid the row behind it, and to make up for that I had the tops south of you seen through: that is the x-ray with no roof.
  2. The same top lies over a gap of one tile in a wall that runs north: the gap cannot be seen, and the wall over it shows its front instead, a patch of planks in the middle of a wall.
- No patch mends that: it is what a tall block is, seen from here. A wall is thin now (structures.js), as the pack's own house walls are and as a fence is: in the middle of its tile, all of it drawn on that tile (4 px over it). Nothing south of it: its front, a cap over the pack's planks, from the wall beside it (or its own middle) to the wall on its other side. A wall south of it: its top, a band 6 px wide, and the front of a wall joining from a side runs up to the band. A corner, a T and a crossing are one wall; a gap is a gap; a wall that ends has an end. Nothing of a wall is ever seen through: it is in nothing's way. (Roofs still are, from under them and in build mode.)
- A door in a run going north (iteration 121's opening under a lintel went with the tall walls): seen from above, the band's two ends as its posts, its leaf between them, back against a post while someone is by it, and under it the doorway's shadow in the dark of the game's holes.
- Third drawing of walls in a day (fronts and flat bands; tall blocks; thin). The first two were mine to get wrong: I chose a look, then met what it cost in the user's own house. This one I tried on their house before keeping it.
- The clip is filmed again. Tests: the test of iteration 121 rewritten (the leaf and its shadow; the ground north of a wall is as it is; the wall south of you is its own colours, not thinned; a door opens for you). 410 unit; 31 in Chrome (build, edges, the island, pixels, land).

## Iteration 123: a lower corner is joined as an upper one is
- User, with a picture: "lower corners should be linked to upper. also, great redesign of walls".
- Where a wall came down onto a front (a house's two lower corners, a T from the north) the front's cap had its dark top line right across the band: two pieces touching. The band now runs into the cap (structures.js: the line is left open over the band's width).
- Looked at both lower corners of the user's yard on a copy; the test reads the pixel where they meet (the cap's own colour). 410 unit; the four build tests pass.

## Iteration 119: zoom that can be used
- Asked: "fix the zooming process. in the game, zooming is hard, uninturitive and ugly".
- What it was (read and tried on a copy): every wheel event was a whole level, so one trackpad swipe (dozens of events)
  went from one end to the other; the picture jumped from a size to the next; nothing showed the level or its ends;
  level 1 made a player 16 px tall.
- Change: `web/js/zoom.js` owns it. The wheel is counted in distance (a mouse notch: a level; a trackpad: a level per
  90 px, at most one every 200 ms; a pinch on a trackpad counts too); a level glides into the next over 140 ms (the
  canvas is scaled, never under the window's size, then drawn at the new whole-number size); a sign (− pips +, in the
  HUD's pixels, clickable) shows while you zoom and nods at an end; a player's view stops at 2, a spectator's at 1;
  the level is kept in the browser. `+`, `−` and the phone's pinch go through the same code.
- Measured: `tests/e2e/test_e2e_zoom.py` (a notch is one level; a 40-event swipe is one level, it was the whole range;
  the glide starts and ends clean; the sign; the stop at 2; kept). Full browser run 186 pass, 1 error that is a player
  not getting in under load (passes alone); unit 413.
- Not seen by me in motion at 60 frames a second, only in screenshots taken during the glide: no edge shows.

## Iteration 120: the zoom's sign in its place, the keys of the main row
- Said: "the zoom indicator show up at a weird spot", "qwerty -+ does not work. you use the numpad ones ? ppl dont
  always have numpads".
- The sign was half way up the right edge; it is now in the middle, just over the hearts (under you).
- The keys were looked up by the character typed, among the game's shortcuts, which wait for a player. I could not
  make them fail on a US layout; what could fail: another layout (the character differs), or watching without a
  character. `zoom.js` now listens itself: the characters + = - _, else the two keys right of 0 by their place
  (Equal, Minus) and the numpad's; not while typing, not with Ctrl or Cmd (the browser's zoom), also for a watcher.
- Measured: `test_e2e_zoom.py` (Equal, Minus, with Shift, numpad; the chat's dash is not a zoom; a watcher; the
  sign's place); 6 of 6 with the old key test and the first screen's.

## Iteration 121: five commands, not thirty-four
- Said: "there's a lot of useless slash commands. like walk etc... no need for those".
- What it was: "/" listed every action of the server (31: step, walk, stop, move_to, dig, eat...), which are what the
  AI players call and, for a person, a key or a click; plus the page's three (coords, grid, perf).
- Change: `complete.js` keeps as commands only the actions with no other way in the page (I looked for each in the
  page's code): `/name` (name an animal) and `/write_sign`; with `/coords`, `/grid`, `/perf`. Any other /word does
  nothing and says "No command /word. Type / to see them." The server and the AI players' actions are untouched.
- Measured: `test_e2e_complete.py` rewritten (the list is those five; /walk and /dig do nothing; /name names a cow),
  one assertion of `test_e2e_ui.py` turned round; 17 of 17 with the interface and touch tests; unit 413.

## Iteration 122: every command again, but none listed on a "/" alone
- Said, after iteration 121: "keep all commands available client side just remove the hint on a simple '/' and also
  remove them from the help. they should be accessible if you know them, and if you know them they still show
  highlight syntax".
- Change: iteration 121's cut is undone (every action of the server is a command again). `complete.js` lists nothing
  for a "/" alone; from the first letter the commands that fit, then arguments and values, as before. The help's
  "/ Commands" row and the chat line's "/ commands" word are gone.
- Measured: `test_e2e_complete.py` (the earlier tests back, plus: nothing on "/", a list on "/s", nothing again after
  Backspace) 4 of 4; interface tests 14 of 14.

## Iteration 123: the door's sound
- Said: "door do a weird noise. fix the door noise".
- What it was (`music/sfx.py` "gate", played when a door or a gate opens): a hinge's creak, a train of 45 to 140
  pulses a second for 0.4 s, then a hard knock of wood and metal. Measured: the envelope rippling at 40-160 Hz 4 dB
  over its slower movement (a buzz). The same slow pulse train was once heard as "a fart" on the falling tree.
- Change: the latch (a small tick of metal), the bolt leaving the wood, a soft breath of noise for the swing, the
  door coming to rest; no pulses (ripple now 6 dB under), no pitch (ringcheck 0.00, and the door is no longer on its
  list of sounds allowed to ring), a little shorter and 1.5 dB quieter. `houses.js`: a door that has only just shut
  (under 0.7 s) is not heard again when it reopens (someone hovering at the sill).
- Measured: audio tests 8, sound and building browser tests 13. Not heard by me.

## Iteration 124: the list of commands is whole again
- Said: "keep the hint of all commands when starting by /". I had read "remove the hint on a simple '/'" as the list
  shown on a "/"; it was the words that advertise the commands. State now: a "/" lists every command as it always
  did (`complete.js` as before iteration 121); the help's "/ Commands" row and the chat line's "/ commands" stay out.
- Measured: `test_e2e_complete.py` as it was before iteration 121, 4 of 4.

## Iteration 125: what the game says is said in the chat
- Said: "all errors messages and shit show up on top of screen.. can't you just show them beautifully in the chat ?"
- Change: `toast()` (ui.js, some forty callers: a no, a hint, "Empty hands", "Sound off") writes a line of the chat
  while you play: a small square mark, green for a word, red for a no; the same line twice is counted (×2); it shows
  6 s, fades like the rest and stays in the history (Enter). The sign at the top stays for the first screen only
  (name taken, a code sent: no chat there); its text is still set, unseen, while you play (tests read it).
- Measured: a new test in `test_e2e_ui.py`; the eleven test files that read messages, 67 of 67.
- Seen in a screenshot on a copy: the lines sit with the chat's, in its strip.

## Iteration 126: the list of commands is the player's
- Said: "you don't get it.... the / should show hint for commands that are useful for real players. if somewhat a
  player type another command like /step, then still show /step hint but the /step needs to be written entirely.
  but / shouldn't confuse player with bot commands". (Three readings of mine before this one were wrong: 121 cut the
  commands, 122 hid the whole list, 124 brought all of it back.)
- Change: `complete.js` PLAYER = name, write_sign, with the page's coords, grid, perf: these are listed on a "/" and
  as you type. Any other action of the server is listed only when its name is written in full (/step), and then its
  arguments and their values as for the others. Every command still runs.
- Measured: `test_e2e_complete.py` (the five on "/"; /st, /ste, /di list nothing; /step and /dig list themselves;
  arguments of /eat, /drop, /milk as before) and the interface tests, 16 of 16.

## Iteration 127: a sign is written as it goes up; an animal is named with a name tag
- Asked: "turn the command that could be turned into UI (signs, naming mobs) into ui. As example Signs = write when
  placing. Naming mobs = naming tag required".
- Signs: placing a sign or a flag opens a small box (`web/js/ask.js`, the panel's pixels): what it says, Enter puts it
  up, Esc gives up, nothing typed is a blank sign (a flag then says whose it is). The server's `place` takes the text
  for a sign as it did for a flag (`sim/building.py`).
- Names: a new thing, the name tag (1 plank, 1 fiber, no bench; icon drawn in `tools/pixel_art.py`, added to the
  sheet). In hand, used on an animal: a box asks its name. The server's `name` now needs a tag and uses it up
  (`sim/animals.py`): this is so for the AI players too, and their tool list says it.
- Commands: nothing a player needs is a command any more; "/" lists the page's three (coords, grid, perf); the
  server's actions, write_sign and name among them, are hinted once written in full, as in iteration 126.
- Measured: unit 416 (a name without a tag is refused, the tag is used up; a sign placed with words reads them);
  `test_e2e_ask.py` (the box, the letters typed do not walk you, Esc, reading the sign; naming a cow) and the
  completion tests, 6 of 6. Seen in a screenshot: the box in the panel's style.
- The world that is running keeps its old rules until its server is started again.

## Iteration 128: building up, a block at a time; a roof is a block like the rest
- User: "does current building models allow building multiple floor houses ? if no, make it intuitive and possible. walls should just be blocks but for houses, building mode should allow building like minecraft: grass = grass block etc etc." Then, while I was reading: "roof break the "block rule" i feel like".
- It did not: one piece a tile, and over it a roof that was a rule of its own (a tile laid over a tile, on a wall or beside a roof, no further than three tiles from a wall, stood on by nobody, built on by nothing).
- What was already there, and I had not used: the land is cells (world.py, gen.py: a column of solid cells a tile, a layer half a tile high; you are two cells tall, jump one, fall three unhurt). That is the sandbox classic's grid, seen from above. So building up is the same thing, and nothing new to walk on had to be invented.
- A built block (sim/storeys.py, floors.py) is one more solid cell of its tile's column: `plank` (a floor) or `roof` (shingles). It rests on the block under it, or on a wall or a door a storey under it (STOREY: 3 layers: two to stand in, the block the third), or it holds to a block beside it at its own height, land or built. What it is made of and what stands on it are kept in their own table (`floors`: x, y, z, kind, thing); the cell itself is in the land's columns, so walking, jumping, falling, reach and the way somewhere (move_to, now over places with a height) go by the one rule they had. Upstairs stand: walls, a door, a fence, a gate, a bed (you wake by it, upstairs), a chair, a table, a plant, a clock, a rug.
- So: a second floor is planks on the walls and from block to block over the room; the way up is blocks, one high then two, beside a gap left in the floor; a roof is the same block in shingles, and is stood on and built on. Old roofs become roof blocks when a world is opened (each roof whole, a storey over its highest ground).
- Earth ("grass = grass block"): `dirt` on open ground raises it a layer, with its grass (the land itself: no entry kept). Digging takes it down, as it did.
- The screen (web/js/floors.js): blocks are drawn in the frame's depth order, a row at a time and in a row from the ground up; a body is drawn at its own height (a tile can be stood on at two); the land painters are sent the land alone, so no hill is painted for a floor. Seen through: what is over your head, with all that goes on from it at that height or higher (in the room: the floor above and the roof; on the steps: still the room; upstairs: the roof only). Behind a house, only the blocks drawn over you are a veil: a house of two storeys is drawn three tiles up and hid you whole.
- Build mode (build.js): the cursor has a height. It rides the ground nearest your own; R lifts it a storey, F brings it down. A thing goes on what the cursor is on; a block on top of it, or, the cursor in the air, in its cell. Planks on bare ground are a floor laid in it as ever; a roof goes a storey over what the cursor is on, so a house is roofed without a key more. A planned block holds the next; the work builds what is held first. X takes at the cursor's level, and with nothing there the lowest block over it. By hand: Space upstairs places and takes as on the ground; planks in hand on a block, facing the air: the floor goes on.
- Walls stay thin (the user's "great redesign of walls"): a wall is a piece on a floor, one a storey, and joins the walls at its own height. My reading of "walls should just be blocks": one grid, one rule for all of it, not the tall look they turned down in iteration 122. If they meant the look, that is one drawing to change.
- An old server (the play world, until it is restarted) says `roofs`: its roof tiles are shown as roof blocks, laid and taken as before, and R says floors come with a restart. Tried: the new page on the old server's code.
- Dropped: houses.js (the drawing for servers from before roofs: none is left) and the once-only roofing of closed rooms from before iteration 117.
- Seen in Chrome on a copy: a house of two storeys from outside, from behind, in the room, on the steps, upstairs.
- Tests: tests/test_storeys.py (6: where a block rests; a second floor stood on, built on, reached by steps; taken back top first and kept in the save; earth; old roofs; the way up to a floor asked for), tests/e2e/test_e2e_floors.py (3: a second floor by keys alone; what is seen from where, a bed upstairs, a fall off the edge; earth, and a floor going on by hand); the build, edge, relief and chat-completion tests moved to blocks (and `z`). 417 unit, 192 in Chrome.
- Not done, known: the AI players are told of `z` but see only the ground's layer in observe; nothing built burns; what lies on the ground is one pile a tile whatever the height (dropped upstairs, it is picked up from under); a fence upstairs joins by the ground's fences; touch has no build mode; a planned block does not carry a plan on top of it (plan the second step once the first is built); the clip on the demo shows a house of one storey.

## Iteration 129: the recipe book has a search
- Asked: "add a research feature in the crafting menu" (read as: a search).
- Change: under the list, a field (`#craftfind`, the book's sunk cell). Typed in it: in every kind at once, the things
  whose name has it, then the things made of something whose name has it ("fiber": rope, torch, name tag, flag...).
  "/" goes to it; in it the letters are its own, the arrows walk the list, Enter makes (Shift: five), Esc empties it
  and then leaves it; choosing a kind ends the search. "Can make" still narrows it. `craft.js` craftFound.
- The name tag sits with the farm's things (Home), not in Basics: the first kind keeps its two pages.
- Measured: `test_e2e_craft_search.py`; full browser run before this last move 191 pass, 3 fail, 1 error: two were
  mine (an older test naming without a tag, the book's key test with a ninth thing in Basics: both corrected), the
  floors test and a player not getting in pass alone. Unit 421.

## Iteration 130: what the game says is dressed
- Said: "default dialogue (you wake up in meadows..) and things like that are ugly, add bold, line return, change
  sentences idk make them beautiful in the chat".
- Change: a line of the game's (not a player's) may carry **bold**, a new line and `K` a key drawn as a key
  (`main.js` rich); its lines hang under each other beside the mark. Rewritten: the welcome (your name, four short
  lines, the keys as keys, shown 16 s), who came, left, died, gave, named (names in bold), in hand, sound, goal done,
  a sign read (its words on their own line), a letter, build mode. Where a message is read as text (the first
  screen's sign, the tests) it is plain.
- Measured: the test of iteration 125 extended (bold, key, new line; plain text; a player's `**` stays as typed);
  the fourteen test files that read messages, 80 of 80. Seen in a screenshot.

## Iteration 129: a house of two storeys beside doben3, and doben4 to try it
- Asked: "create doben4 next to doben3 and showcase there a nice multi-floor building with item in doben4 inventory to test it".
- doben4 joined from the user's own browser (its token is kept there, as for every name they play), stands at
  (90, 179) beside doben3. West of them, at (83..90, 170..176): walls and a door stamped on the ground, the rest laid
  by doben4 with the game's own `place`: a floor of planks, a table and chairs, a chest, a clock; two steps by the west
  wall; the floor upstairs on the walls, its front row a terrace over the door; walls and a door upstairs, a bed, a
  table, a rug; a roof a storey over that; a path and flowers. Tried first on a copy of the world.
- Two faults seen while looking at it: standing on a roof, the roof tile south of you was thinned as if it covered you
  (now only a block higher than where you stand can); someone upstairs over a door opened it (now only people on the land).

## Iteration 130: stairs and ladders
- Asked: "create stairs and ladders to access upper floors".
- The way up was a pile of planks, one high then two, beside a hole in the floor: right, but nothing said so. Two
  pieces now (sim/climbing.py, web/js/climbing.js; the same rules both sides, so your walk and the hints say what the
  server will do).
- Stairs (1 wood: 2): put beside a higher place (a floor's edge, a terrace, a ledge, 2 to 7 layers up), one press
  lays the whole flight: a step a tile, a layer lower each, down to the ground. Straight out from it; where that way
  is shut (often by you, standing before the wall), along it. A step is a column of built blocks (kind `stairs`),
  drawn as planks with a tread: lit at its nose, the next riser's shadow at its back. A stairs a step; X takes a step
  back, its whole column.
- Ladder (2 wood): against anything taller beside it, on the ground or on a floor. Walk into the taller thing from
  the ladder and you come out on top (the lowest place up there you can stand on, the ladder's tile open all the way:
  a floor over a ladder needs a hatch); walk off the top onto it and you climb down: no fall, however high. Only
  people climb. Drawn from its foot to the top it leads to, rails and rungs in the houses' wood; climbing is a
  straight slide, not a hop or a fall. The way somewhere (move_to) goes up ladders too.
- Icons drawn in tools/pixel_art.py and added at the end of gen.png. A ladder is heard as a fence post going in
  (tools/build_audio.py SOUNDS_LIKE: the sound map is in music/, which I leave alone).
- Tried on a copy of the world on doben4's house: a flight up to its terrace from the west end, a ladder from the
  terrace onto the roof, climbed and come down unhurt.
- Tests: tests/test_climbing.py (3), tests/e2e/test_e2e_climb.py (2: a flight by Space and walked up, one planned in
  build mode; a ladder against a cliff six layers up, climbed and come down unhurt).

## Iteration 131: the goals' card moves smoothly
- Said: "see the item sliding animation on goals? it looks buggy (low fps)".
- What it was: a row slid in over 0.35 s in four steps (about 11 pictures a second, on purpose) and went out in
  eight steps over 1.6 s; and at each change all three rows were made again, so all three slid in again; the one
  just done jumped to the top first.
- Change: `goals.js` keeps the rows; the one done stays where it was and fades out, the ones that stay glide up to
  their place (260 ms), only the new goal comes in (300 ms); no steps anywhere (`windows.css`). The card shown with G
  is there at once, as before.
- Measured: a new test in `test_e2e_social.py` (the same rows kept, none stepped, only the new one comes in); the
  social tests 8 of 8. Not seen by me in motion.

## Iteration 132: the arrows bring back what you sent
- Asked: "implement up/down arrow to browse chat/command history".
- Change (`main.js`): in the chat line, Up goes back through the lines you sent (talk and commands), Down forward,
  and past the newest the line you were writing is back as it was. Begun from a "/", only the commands. The last 50
  are kept in the browser, a line sent twice once. The arrows stay the list's (complete.js) while a list of several
  is shown for a line with something typed; on a bare "/", Down walks the list and Up goes to the last command.
- Measured: a new test in `test_e2e_complete.py` (the order back and forth, the draft, commands only from "/", the
  list's arrows, kept after a reload); completion 5 of 5, and the interface, touch and social tests.

## Iteration 133: the tusker is where it is
- Said: "boar is kinda buggy it glitches a few pixels somewhat teleporting near to its location when doing key moves".
- Looked for it in three places. The sheet: every animation's frames sit on the same pixels. The charge: drawn at
  ten tiles a second, no jump (worst frame step 0.28 tile). The moves around it: trotting into line (a tile every
  0.2 s when angry) and at the end of a charge the world moves it faster than the 1.2 tiles a second it was drawn
  ambling at, so it began to paw, or stood dazed, up to 0.7 tile from its tile and slid there during the move.
- Change: an animal goes at the world's pace when that is faster than its amble (`state.js` p.pace, from its last two
  places; `render.js`), and a tusker pawing or dazed closes what is left at once (8 tiles a second).
- Measured (`test_e2e_wild.py`, the drawn place frame by frame): a quarter of a second into a warning or a daze it
  is under 0.02 tile from its tile (0.69 with the old rule, same test); no frame moves it more than 0.6 tile. The
  wild, living, world and moving tests pass. Not seen by me in motion.

## Iteration 134: a ladder is climbed, stairs look like stairs
- User: "ladder animation is awful !!!!! and stairs does not look like stairs at all".
- Looked first: every frame Chrome painted while climbing a ladder six layers up a cliff, and the stairs tower close up.
  The climb was three frames: the server moved you at once and your screen slid you in a straight line from the
  ladder's foot to the top in a fifth of a second, walking, the ladder drawn over your body (you were sorted behind
  it), the camera jumping with you. A step was a plank floor block at its height: a flight was boxes. The packs have
  no wooden stairs nor ladder (only stone slabs in hill slopes), so both stay drawn by the game.
- Ladder (climbing.js, walk.js, render.js, characters.js; sim/movement.py): a layer takes CLIMB_S (0.15 s): the
  server holds your next step till you are up (or down), your walk crosses the climb at that pace, and so does anyone
  seen climbing. Drawn: up the rungs on the ladder's own tile first, facing it, legs going, a rung's tock now and then;
  only at the top over the edge (down: over the edge first, then down the rungs). In front of the ladder while on it;
  the camera follows the body as drawn.
- Stairs (climbing.js drawStep): no longer a plank block. Rising north: small steps, a board and a darker riser, three
  to a tile over its top and front, a stringer down each side, the same rhythm from the ground to the floor. Rising
  east or west: two treads across each tile, the one nearer the foot half a layer lower, stringers along its sides
  and a stepped stringer in front. Rising south: each step's tread front, the next over the rest.
- Seen in Chrome on a copy of the world (the two towers by doben3): all four flights and the climb, frame by frame.
- Tests: the ladder test samples the climb (on the rungs half a second and more, on the ladder's tile, facing it, held
  back over its foot); the stairs test checks each step is drawn as a step. 429 unit.

## Iteration 134: one unit of health, the half heart
- Said: "i see that player damages are numbers, are they healths ? damage to the player should be health and vice versa
  for the damage player gives and mob lifes. heart and demi heart should be the universal health unit. because default
  player hit damage should be 0.5 not 5 hearts".
- What it was: a person's health in half hearts (20), but a creature's on a scale of its own (a cow 30, a tusker 40)
  and weapons on that scale (bare hands 5, a sword 30), shown raw over a creature ("-5") and divided by five on a
  person.
- Change: everything in half hearts. Bare hands 1 (half a heart), pickaxe 2, axe 3, spear 4, sword 6 (`tiles.py`);
  creatures a fifth of what they were (chicken 2, cow 6, tusker 8, strawman 10, wyrm 12, Old Mossback 60...,
  `sim/entities.py`), so each takes about the same number of blows; a creature saved on the old scale is capped at its
  kind's. A blow is said in hearts with a small heart beside it, on a creature as on a person, and a fall too.
- Measured: unit 429 (the boss test restated); a new browser test (a punch on a cow: 5 of 6 left, "-0.5"); full
  browser run 199 pass, 1 error (a player not getting in, under load).
- The world that is running keeps the old numbers until its server is started again; until then the page shows a
  punch on a creature as "-2.5" and the boss's bar is wrong.

## Iteration 135: no x-ray on a ladder or a flight of stairs
- User: "xray is triggered at certain moment during star walk and ladder climbing".
- Measured on a copy, frame by frame (xray.a), ladders against a cliff six layers high on each of its sides and
  flights up a cliff three layers high from each side: the circle opened on the side ladders half way up. Its rule
  measures how much of you the ground south of you hides, from the height you are at; that height was the land's
  under you, not the step, the floor or the rung you are on, and where you were was not where you are drawn on a
  ladder.
- xray.js now takes the height you are at (Floors.standOf: built blocks counted; on a ladder, the climb's own height)
  and where you are drawn. Measured again: no circle on any flight nor on the side ladders; behind the cliff at a
  ladder's foot it is there as anywhere behind a cliff, and goes as you climb out.
- Test: a ladder at the cliff's side, climbed: the circle stays shut. climb, x-ray and relief tests, 29.

## Iteration 135: a door opens and closes, and is heard doing both
- Said, of the door's sound of iteration 123 (a latch, a breath, a soft stop): "fix the door noise, i dont hear
  anything. i hear a clic that does not sound like a door at all"; then, of two knocks of a board I had begun:
  "a door that open/close noise. not a toctoc".
- Change (`music/sfx.py`): opening ("gate"): the latch lets go, one clack, then the door swings on its hinge, a dry
  wooden creak with no pitch (grains of noise in the wood's band, thickest while it moves fastest; no pulses at a
  rate, which is what buzzed in the first one). Closing (new, "door_close"): the swing, shorter, one thud as it
  meets its frame, the latch catching. Both about 5 dB louder than the click. `structures.js`, `sprites.js`: a door
  or a gate that begins to shut plays the closing one.
- Measured: opening 0.45 s, the creak at its fullest a quarter of a second in; closing 0.33 s, the thud at 0.17 s;
  no pulse ripple in either (-5 to -7 dB); the door test hears both; audio, world, sound and floors tests pass.
- Not heard by me: four versions now, each judged by the user's ear only.

## Iteration 136: the door's sound without a click in it
- Said, of iteration 135: "i still hear a click when opening and closing. i just wanna hear the door noise !"
- Measured, a new meter: how far the loudest 2 ms stand over the 50 ms around them. A knock (a board being set):
  +10 dB. Iteration 135's door: the latch, and also its swing, made of 130 grains of noise a second, each grain +8 to
  +10 dB: the swing itself was clicking.
- Change (`music/sfx.py`): no latch, no metal, nothing struck. The swing is one continuous creak whose pitch follows
  the door (150 to 310 Hz opening, back down closing; a little unsteady; through the wood's resonances) over the air
  the board pushes. Closing ends in a low soft whump of noise, not a blow.
- Measured: opening +4.3 dB, closing +5.3 dB (half a knock's sharpness); opening 0.6 s, closing 0.45 s; no slow
  pulse ripple (the creak is too fast to rattle). The door and sound tests pass.
- Not heard by me. The creak is a note that glides: if it reads as a squeak, it wants to be lower or shorter.

## Iteration 137: the moan is out of the door
- Said, of iteration 136: "that does not sound like a door sound anymore.. sound like an old person moaning". The
  creak was a note gliding through resonances, which is how a voice is made.
- Change: the note is out. A door opening is the air the board pushes (a soft swish, 0.6 s); closing, the swish and
  a low soft whump. No click (the meter of 136: +6.7 and +5.3 dB), no note (ringcheck 0.02). It is a stopgap: plain,
  and not yet "a door".
- Five versions made without hearing them, five refused. Asked of the user: a recording of a real door (a free pack
  made for games), which is a file to download and so theirs to allow.

## Iteration 136: nothing turns see-through on a ladder or stairs
- User: "xray still trigger mid-ladder and at the last staircase step !"
- Measured on a copy of the world, each ladder of doben4's ladder tower and each flight of the stairs tower, per frame:
  the x-ray circle never opened; what did was the veil (floors.js: a built block drawn over your body is seen through,
  for walking behind a house). From the sides, half way up a ladder and for two frames on a flight's last step: it took
  the place a straight line had you at, not your body on the rungs, and the height of the tile you were leaving. Behind
  the tower, up its back ladder and its back flight: a see-through stripe down the tower's top while your head already
  showed over the edge.
- Now the veil takes you as drawn (on the rungs; the higher tile while you step), is never on a ladder (its foot
  included) nor on stairs, and comes and goes over 0.15 s instead of at once. Measured again: no veil and no circle on
  any of the eight, the veil behind a house as before.
- Test: up a ladder behind a block, nothing turns see-through. climb, floors, build, x-ray tests: 21.

## Iteration 138: six doors to choose from
- Said, to my asking for a recording: "nah ??? just like other sound effect, create it. do a showcase html page in
  local".
- `music/doors.py` makes six doors, each an opening and a closing, from the same parts as the other effects (struck
  wood and board, friction, shaped noise), as unlike each other as a door allows: clunk and swish; an old hinge
  (slips you can count, quickening and slowing); wood dragged on wood; one knock each way; a heavy door (a low
  rumble, a deep thud); the latch working (three sounds in a blink). `music/site/door.html` plays each (Open, Close,
  Both), with the stopgap that is in the game now. http://127.0.0.1:8099/door.html
- Measured: all twelve at the game's door level; the page loads and plays all fourteen files. None is in the game:
  the choice is the user's ear.

## Iteration 137: over the top of a ladder, not under it
- User: "at the end of hte ladder, i go under the platform before going over it".
- Stepping over at a ladder's top, you were placed in the frame's order by the top's row alone; a built block there is
  placed by its row and its height, so the block you were stepping onto was drawn after you, over you, till the step
  was done. Now (climbing.js climbOf) on the rungs you are placed in front of the ladder and of what its foot stands on,
  and over the edge as anyone standing up there is: the row and your height. Filmed on a copy: up the front ladder of
  the tower, over the edge onto its top, in front all the way.
- Test: up a ladder onto a block, the step over is placed after the block.

## Iteration 139: the door is one knock each way
- Chosen by ear on the page of iteration 138: "go with one knock sound effect".
- `music/sfx.py`: "gate" (a door or a gate opens) is one wooden knock, "door_close" one knock lower and fuller; made
  from the page's own recipe and random source, never resized or re-pitched: the game's two files differ from the
  two that were heard by less than one step of 16 bits. The page's other candidates stay in `music/doors.py`.
- Measured: the files compared sample by sample; audio tests, the door test and the sound tests pass.

## Iteration 152: real shadows and reflections

"we want real shaders, reflection, not just color hue tweaks, shadows, like minecraft". Iteration 144 only repainted
the finished picture. Now a shader also adds to the world (js/sun.js): every tree, wall, thing, animal and person
throws its own shape on the ground away from the sun (west and long in the morning, short at noon, east in the
evening, faint at night), and what stands by water is seen in it upside down under its feet, rippling. Both are the
frame's own sprites drawn once more through a transform onto a layer (`ctx` is pointed at it meanwhile, so whatever
draws a body or a wall draws its shadow with no code of its own), a shadow filled flat, a reflection kept where
there is water; render.js calls it between the ground and what stands on it. A look "Natural" keeps the colours.
Looked at on a staged pond, morning, noon, evening, night: the first shadows hung under their things (a sprite has
empty rows under it: each one's lowest painted row is found once). Tests: one in Chrome (a tree's shadow west in
the morning and east in the evening, its reflection in the pond); 453 pass, and the browser suite but for a digging
test of the other session's work in progress. Left: light from a fire throws no shadow; clouds are not in the
water; hills throw none.

Then, from the user: "player shadow does not start properly at player feet" (I had set a body's foot by eye, at .74
of a tile: a person's is the sheet's own measure, 13 art px under the body's place, and each animal kind's is found
once from its lowest painted row); and "player reflection is visible even if player is standing on a mountain,
because there's water under it" (the mask was every water tile: now a water tile counts down to where the nearest
land south of it begins on the screen, so none of it behind a hill). A test builds that hill over a pond; it fails
without the fix. And "with shader you can remove the white circle under the player": with a shader's shadows on, the
pale mark under you is not drawn (you have a shadow, and it starts at your feet with nothing over it).

And "particle shadow create weird patterns.. especially the one when sprinting in water": drawing a body does more
than paint it (dust, spray, a step's sound, where its swing is), and for its shadow and its reflection it was drawn
twice more: three times the spray, and the wake itself laid over as a shadow. Now a copy of the body is drawn for
those, what it throws up is taken back, it makes no sound, and a body in the water has neither shadow nor
reflection. A test counts the spray of a sprint in water with and without a shader.

## Iteration 144: shaders

"add nice shaders in the settings menu, like minecraft shaders". The game is a 2D canvas; a shader takes the finished
picture each frame and repaints it on a WebGL canvas laid over it (js/shader.js, #fx): bright parts glow (two blurs
of a quarter-size picture), colours are graded, cloud shadows drift over the land (fixed to it, an art pixel at a
time, none at night or in a cave), corners darken. Six looks (Soft glow, Golden hour, Vivid, Dreamy, Moody, Old
screen) and a Shaders page: which, strength, glow, cloud shadows, dark corners. Off by default: nothing of it exists
until asked for, and the 2D canvas is never touched. Looked at by day and by night on real frames: the first glow
whitened the whole meadow by day (grass is as bright as a lamp's pool), so by day the glow is a third and starts
higher. Measured: 1.5 ms of script a frame with a shader, 1.3 without (960 x 600). Not tried on a phone.
The same slip as iteration 143, caught at once this time by looking: a comment added by script inside a line of
uniforms swallowed two of them and the picture went grey. Comments go on a line of their own, always.
Tests: one new in Chrome (the picture is graded, strength 0 is the plain picture, off hides it); 451 + 217 pass.

## Iteration 143: a menu on Esc, and settings

"implement a full settings menu into the game (echap) like minecraft with lot of options". Esc with nothing to shut
opens a short list (back, settings, help, leave); the first screen has a Settings row. Four pages, 39 rows, each one
acting at once and kept in the browser (js/options.js: defaults and opt(); js/menu.js: the window; css/menu.css):
Sound (all on or off, everything, music, how often it plays, seven families), Picture (zoom, sharpness, light at
night, particles, water shimmer, fall shake, smooth zoom, hearts and gains), Screen (bubbles, names, how long a chat
line stays, key hints, mouse tips, goals, coordinates, grid, performance), Keys (sprint held or pressed once, and
eleven actions that take another key: the hints and the help follow; walking, numbers and the windows' own keys stay).
The music now leaves through a gain of its own so that its volume can be set. Esc no longer empties your hands (` does).

A mistake of mine, live for about twenty minutes: a comment I added in the middle of a line of state.js swallowed
the rest of it (W = innerWidth), the canvas was 0 px wide and the world was not drawn. My own screenshot showed a
plain sea-coloured screen behind the menu and I took it for the headless browser. The full suite caught it (29
failures). Rule: a plain background in a screenshot of the game is a failure until shown otherwise; run the suite
before believing a screenshot. Tests: 4 new in Chrome; 437 + 211 pass.

## Iteration 142: the AI players are robots

"go with tin cat" (the first of eleven): the race as it is, in steel, nothing over the face. Made for every race by
one function (web/js/races.js robot()): steel body with a little of the player's colour, grey bolts for the blush,
ear lining and bell in the race's own light, the duck's bill and feet still orange. Looking at the five sheets, the
frog had lost its eyes (dark eyes in the dark edge of its bumps): its eyes are lit. The ten refused designs and their
hook are deleted. In the game: the world marks a player that came with a persona of its own (`bot` in what watchers
are sent, views.py), and the page draws it from its robot sheet, in the world and in the list of who is here, clothes
and all. Tests: one for the server, one in Chrome (steel, eyes uncovered, a hat fits, an AI player that joins is
marked and a person is not). 430 + 6 pass. The server on 7777 sends the mark only once restarted.

## Iteration 141: five robots for the cat, none with a visor

The robots of iteration 140 were refused: "black thing on their face is ugly. suggest 5 robotic design for the cat,
before generalizing to everyone". I had generalised one untested idea to five races. Now: one race, five unlike
designs, the user picks (design/enemies/robots_cat.js, page design/enemies/site/robots.html): tin (the cat in steel,
its own eyes), lamp eyes and an aerial, a pale lit screen for a face, enamel in the player's colour with steel parts,
a brass wind-up with a key in its back. The visor robot is out of web/js/races.js; raceSheet's third argument is now
a design, so nothing of a refused look stays in the game's code. Race tests: 5 pass. Next: the user's choice, then
the other races.

Then "more concepts": six more on the same page, further apart: one eye, a box head with aerials (the only one that
changes the outline), scrap, a white shell trimmed in the player's colour, neon (dark body, everything lit), a heart
light. A design's `mix` now says how much of the person's colour each of its colours takes (the shell tints its trim,
not its body).

## Iteration 140: a robot of each race, shown before it is used
- Asked: "design a robotic equivalnet of each race for AI players, and create a showcase page for it before
  implementing them".
- Design: a robot is its race in plate. The head keeps the race's outline; steel with a dark edge where the fur was;
  a dark visor across the face with two lit eyes; the ears' lining, the cheeks and the bell as lamps, in a light of
  the race's own (cat cyan, bunny pink, bear amber, frog green, duck yellow). The frog has no visor: its eyes are the
  two lenses on its head, its mouth a grille. The plate keeps a little of the player's colour.
- Made as the races are: `web/js/races.js` raceSheet(key, tint, bot) draws it from the cat's sheet, so every
  animation exists. Nothing in the game calls it with `bot` yet. `design/enemies/robots.py` saves the sheets;
  `design/enemies/site/robots.html` shows each race and its robot from every side, walking, at work, in three
  players' colours and on a dark ground. http://127.0.0.1:8098/robots.html
- Looked at, enlarged, before the page: the frog's first robot was a grey frog (no visor, small lenses): grille and
  cheek lamps added. Race and first-screen tests pass (the races are as they were).
- Not done, on purpose: the world does not say which players are AI; that, and who wears what, wait for the user.

## Iteration 138: the name goes with the body
- User: "the username does not properly follow the player."
- What is drawn over a body (its name and health, what it says, its marks, the progress bar) followed it only in a
  fall: up a ladder it stayed on the straight line from the foot to the top, a tile and more from the climber, and in
  a hop (each step of a flight) it stood still while the body jumped. jump.js overBody: the same place as the body, on
  a ladder (climbing.js), in a hop and in a fall; used by the name, the bubbles, the marks and the progress bar.
- Filmed on a copy: up a side ladder of the tower and up a flight, the name over the head all the way.
- Test: on the rungs, the name's place is the body's. climb, bubbles, interface, fall tests: 19.

## Iteration 139: behind a tower or a house, a circle round you as through a hill
- User, with a picture of doben4 at the back ladder of the tower, only the name showing: "there should be xray here!!"
- Iteration 136 left the veil out on ladders and stairs, and there you were lost behind the tower. What was wrong with
  the veil was its shape and its trigger, not that it came: each block over you was seen through whole (a stripe down
  the tower's top), and it took you where a straight line had you.
- Now (floors.js draw, holed): when what is built south of you is drawn over your body (you as drawn: on the rungs, at
  the height you are at), the blocks in front of you round you are drawn with a circle in them, as the hill's x-ray
  does (xray.js): clear in its middle, fading in rings to whole at its edge, 1.7 tiles across; it comes and goes over
  0.15 s. On ladders and stairs too.
- Measured on a copy, per frame, the eight ladders and flights of the two towers: open on the back ladder and the back
  flight from the foot until you are on top, without a break; never on the others. Seen: behind the tower, behind the
  house.
- Tests: up a ladder behind a block, the circle is open at its foot and gone on top; behind the house it opens.
  climb, floors, build, edges, x-ray: 27.

## Iteration 142: build mode breaks and digs as it builds
- User: "now the build mode: it isn't intuitive to dig holes. it should be used to both destroy blocks break things
  and also build things !! intuitive !!"
- X in build mode took a plan back or took down what had been built; a tree, a rock, the ground itself said "Nothing
  built there". Now, as in the sandbox classics: Space builds with the piece in hand, X breaks what is at the cursor:
  a plan back; a thing, a tree, a rock, a bush, a wall, a step, a floor down (with the right tool if your character
  has one: an axe for wood, a pickaxe for stone); on bare ground a hole, a layer deeper each time (by hand, slowly;
  with a pickaxe, faster). Held while the cursor moves: a row. The corner says what X does there ("Chop tree", "Mine
  rock", "Dig a hole", "Take down wooden wall"); the greeting and the help say it too.
- Server (sim/underground.py dig_land): `dig` with `z` at the land's own top on a tile beside you takes that cell (a
  hole, a layer deeper; the ground keeps its grass); not under someone, not past -12. Without `z`, dig is what it was.
- Seen on a test server: a row of holes dug with X held, one dug twice more; a tree, a rock and a fence planned down
  and taken.
- Tests: tests/test_climbing.py (a hole beside you), test_e2e_build.py (X breaks a tree and a rock, digs a row of holes,
  a layer deeper again); the audit tests now see X dig over grass. 430 unit; build, help, climb, floors: 12.

## Iteration 143: a broken action no longer stops the world's clock
- Building a showcase house on a copy of the world, the copy froze: 0 ticks a second, nothing in the log. Run again
  under a wrapper that printed what killed the tick task: `place` aimed by x, y on a tile holding a block said
  `f"{args['dir']} has {b}"`, a KeyError (no `dir`), out of the action's generator, out of `step()`, and the tick
  loop's task died with it, silently (its exception is never looked at). The same `args['dir']` was in step, chest,
  write_sign and read_sign: any of them, aimed by x, y, could freeze a world.
- Now: those say "that tile …"; an action that raises anything but a refusal fails with `error: "bug"`, the exception
  written to the log (sim/entities.py `failure`), and the tick goes on; the server logs a tick that breaks and keeps
  ticking. Test: test_building.py (the refusal said; a broken action fails, two ticks still pass).
- The live server runs the old code until it is restarted: the house was built there only after the copy proved
  every placement of it free of that path (the strip in front cleared first).
- The house (three storeys, by x 72-80, y 161-168, north-west of doben4's): the ground floor with stairs up along the
  west wall; the first floor with a short wall from the back, a ladder against it under a hatch; the attic on top with
  a roof terrace round it. A ladder in the open middle of a room is never climbed (every step off it is floor at its
  height): it has to lean on a wall. Walked by an agent on the copy: ground → first floor → attic → roof terrace → ground.

## Iteration 144: Shift ↑ ↓ for floors, and the x-ray goes round the cursor in a hole
- User: "R for up a floor.. not natural. also what for down a floor ? if i want to go mine like minecraft i need to
  dig my stair down ! this is not easy since the selector become unvisible, it should trigger xray too and be able to
  go down a floor. R is unnatural also"
- Seen first on a copy: a staircase dug down with X (−1, −2, −3). The cursor rode into each hole, but two layers down
  a hole's floor is drawn behind the grass in front of it: the cursor sat on that grass, the hole itself unseen.
- Keys: in build mode Shift ↑ is a floor up, Shift ↓ a floor down (WASD too, by the key's place; PgUp/PgDn as
  before; R/F still work, unsaid). Down was only ever "back from up"; now, below your own floor, the cursor sinks a
  storey (as far as four): from upstairs onto the ground floor under you, into a pit, a cave. The corner says
  "Shift ↑ ↓ A floor up, down" and "floor -1"; the greeting and the help page say it. Shift in build mode no longer
  toggles running (keyboard.js).
- X-ray (xray.js): in build mode the cursor is looked at first: two layers or more under the ground in front of it,
  the circle goes round the cursor, not you (the hill's own see-through, the same picture), and back to you when
  it comes out. Compared on the copy with it off: off, the deepest step can't be seen; on, the hole shows down to
  the cursor.
- Tests: test_e2e_build (the circle round the cursor two layers down, gone away from the hole), test_e2e_floors
  (Shift ↑ ↓ up and back, Shift did not set you running; upstairs Shift ↓ is the room under, "floor -1"). Build,
  floors, climb, help, menu, moving, keys, ui, behind: 43 pass; 438 unit.

## Iteration 145: the house of three floors on the demo's "What's new" page
- User: "Showcase it on the demo website" (the house of three storeys, its stairs and ladder; and the floors keys).
- A clip, filmed like the build mode's: tools/film_floors.py builds the same house on a throwaway world (the plan
  that built it in the user's world, as the game's own requests: stamp and place, 467 of them, 0 refused) and a
  player plays it by keys: in at the door, up the stairs, to the ladder, into the short wall it leans on (the climb),
  out of the attic onto the roof terrace, back down by walking off the top onto the ladder; then build mode upstairs:
  Shift ↑ to the attic, Shift ↓ twice to the ground floor under you ("floor -1"), seen through yours. 33 s, 4.4 MB.
  Every leg checked as it was played (upstairs 1,3 z3; attic 4,1 z6; roof 5,5 z6; down the ladder 5,1 z3; hp 20
  throughout). Decoded at 3, 12, 20, 27, 32 s by macOS's AVFoundation (headless Chrome shows a paused video's first
  frame whatever the seek, for the old clip too).
- Cut on the way: the first take came down by `move_to`, and the server's path stepped off the roof terrace's edge
  (no hurt: hp 20), so its caption "down by the ladder and the stairs" was false; the take now comes down by the
  ladder, by keys. A stair dug down into the ground was filmed too and left out: a dug hole still reads as a flat
  brown patch (the known weak point), not something to show off yet. Shift ↑ from the ground put the cursor two
  storeys up off the top of the screen (the camera follows you, not the cursor): filmed from the first floor instead.
- The filming itself moved to tools/filmkit.py (the screencast, the encoder, the MP4 writer, the throwaway server),
  shared by film_build_mode.py and film_floors.py; a scene can choose its poster (a frame while filming).
- The page: a section "New: houses with floors" over build mode's; build mode's own list said R and F for floors and
  "X takes a plan back": now Shift with the arrows, and X breaks what is at the cursor or digs.
- Next: the camera might follow the build cursor when it leaves the screen; a dug hole's floor drawn as dug earth;
  the pathfinder stepping off a roof's edge rather than taking the ladder (no hurt, but not what a person would do).

## Iteration 146: what hides you, four ways to try; Q and E for floors
- User: "Shift + u/d is unintuitive. And depth visualisation is unintuitive"; asked, they chose Q / E for floors and
  "cut away" for what hides you; then: "Showcase multiple things in megastructure demo ... No I mean multiple up/down
  visualisation": several views to try in the demo, not only the one chosen.
- Keys: in build mode E lifts the cursor a floor, Q brings it down (and under your own floor), PgUp/PgDn as well;
  Shift ↑ ↓ and R/F are gone. Q no longer goes to the next piece in build mode (the bar's numbers do). The corner says
  "Q E A floor down, up"; the greeting and the help (Build page) say it.
- Views (options.js VIEWS, setting `above`; V goes from one to the next, toasted; Esc, Settings, Picture, "What hides
  you"; the help has a page "See" with zoom and V):
  - Cut away (the usual one): what is over you (the house you are in; in build mode, everything over the cursor's
    floor) is not drawn; a house in front of you loses the blocks near you that are in front; the ground in front of
    you (a hill, the lip of a hole you dug) is gone over the whole of its picture, not in a soft circle.
  - Outline: the same, with the edges of what is gone drawn in the walls' ink (blocks: their top's free sides; the
    ground: the edge of what the rock was drawn over).
  - Faded: drawn faint (over you as before, .12; in front, 65% of it gone).
  - Circle: as it was.
  The land's picture is the x-ray's own (relief.js through xrayPicture): only how it is put on the screen differs.
- Seen in Chrome in six places, each in the four views: in the house's room, upstairs, build mode looking at the
  floor under yours, behind the house, down a stair dug three deep, behind a hill three high. Read best: cut away in
  the room and in build mode (nothing in the way at all); the circle and cut away behind a hill; outline in a room
  is a wireframe of every storey over you (nested rectangles), busy with three storeys.
- Tests: test_e2e_views (V and the Picture row; in a house, alpha 0/0/.12/.12 and the outline's ink drawn; Q to the
  floor under yours cuts away all over it, E back; behind a rise, the x-ray uniform 1 / .65 and its edges in ink).
  The circle's own tests (x-ray, behind, caves) choose the circle (conftest: circle_view); floors and build tests use
  Q and E. Full browser suite 209 passed (one player could not join under load; it passes alone), 441 unit.
- The demo's What's new page: a section "four ways to see what hides you" with a clip (tools/film_views.py: V in the
  house, behind it, down a dug stair; build mode Q and E), and the floors clip filmed again with Q and E.
- Next: the user picks a view (or asks for others); a dug hole's floor drawn as dug earth.

## Iteration 147: digging down, "Earth and a keyhole"; Q and E a layer
- User: "i wasn't talking about that kind of demo.. but concepts of build mode when breaking block down, under the
  player". Five mockups (local page, a throwaway server with the drawing changed on the fly) in four places (a pit
  beside you, a one-tile shaft, a stair dug down, a cave under you): earth and a keyhole, a stacked cursor, a window
  cut down, a whole-layer view, a side-view panel; and today's. They chose 1, "but attention: your rendering has some
  weird lines in the middle! also how do you make it more intuitive with keyboard ??"
- Measured first, today: a dug floor is grass (a hole three deep reads as a raised table); the x-ray circle round
  the cursor shows the grass round the hole and the cursor seems to sit on it; on solid ground Q did nothing but turn
  the corner's "BUILD MODE" into "floor -1" (it counted storeys; X digs layers); nothing said how deep the cursor is.
- The lines: at the foot of a hole's walls, the grass of the ground beside it (its px past its level's shape, under
  the cliff's foot or its side) was painted at the lower level's height: a green line, two art px, along the floor.
- Change:
  - tiles.js: ground under sea level (only ever dug: gen.py never goes under 0) is the soil, no grass, a shade
    darker a layer down (dugSheet); a hole's walls (the sheet of levels 0 and under, relief.js) and the rims of dug
    steps are earth; the px that made the line are that floor's earth (dugFoot: south, east, west).
  - keyhole.js: where the ground hides the build cursor (the grass in front, or earth or a cave's roof over it),
    its own column is drawn as if cut open in front: the wall behind, a band a layer, down to its floor; faint when
    it is in the ground (not dug yet). Beside the cursor, how far under you it is ("-3"). The x-ray circle no longer
    goes round the cursor. A floor drawn alone, three layers down, showed a tile and a half south of its hole.
  - build.js: Q and E go to the next height the cursor can be at on its tile: in the ground a layer at a time, or
    what is under it (the floor under yours, a cave's, a pit's); on the ground; in the air a storey at a time. In
    the ground X digs down to it, every layer over it from the top (a layer under another waits for it). The corner:
    "BUILD · -3", "X Dig down to -3", "Q E A layer down, up"; the red selector of a bad hint is at the cursor's
    height (it stayed on the surface); the mouse points at the sunk cursor's height.
- Result (Chrome, throwaway server): B, Q Q Q (the cursor three layers down, its column faint, "-3"), X: three
  layers dug, top first, by the character standing at the rim (1 dirt, 2 stone); the pit, the shaft and the stair
  show earth floors and walls with no green line; a pit's south row and a stair's last step show their keyhole
  joined to the hole. Tests: test_e2e_digging (Q/E by layers and X digging down to it; no grass on a dug floor, at
  its walls' foot nor beside a step, which fails with the fix taken out: 16 green px; the keyhole where the grass
  hides the cursor, none on the ground); floors, views and build tests on layers and the keyhole. 445 unit; browser
  211 passed + help fixed (a row too long) + one that fails only under load (gathering; passes alone).
- Next: the user tries it (a reload at :7777); the online demo when they ask.

## Iteration 148: the keys beside what they act on
- User: "the keys appear in the chat, as a guide in each mode. can't you make it more intuitive ??" Looked: each
  mode's greeting put its keys in the chat (build mode: two lines of keys every time), and the rest were a list in
  the bottom corner, away from where you look.
- Change (prompts.js): the keys are drawn beside what they act on, in the corner's keycaps. By the build cursor: at
  its right what Space and X do there ("1-9 Pick a piece" with nothing in hand); at its left "E Up" over "Q Down"
  where the cursor can go up or down, and its depth between them, like a lift's panel (over it, they hid your
  feet). By what you face, playing by keys: Space and X. The corner keeps the rest (build mode's name and Esc; eat,
  pick up, B). A toast with a key in it shows and goes, not kept in the chat (only the welcome is); build mode
  says nothing when it opens.
- Tests: test_e2e_prompts (build mode: nothing in the chat, the keys at the cursor's right, E over Q at its left,
  the corner only the mode, following the cursor; what you face: Space beside it); test_e2e_ui (a guide is not
  kept in the chat); game.actions() reads both. 448 unit, browser 214 + one under load (sound; passes alone).

## Iteration 149: a way down is a tunnel; dug stairs without artefacts
- User (playing, screenshots): "i want to dig a tunnel down, like minecraft you know when you go donw you do l shape
  tunnels. this enforce me to dig huge columns !!!" and "ugly weird artefacts in stairs going down".
- Measured: X with the cursor in the ground dug every layer over it (a column open to the sky); the server only ever
  took a tile's top cell. Their stairs: the deepest floors greyed to olive (each colour channel darkened to the same
  floor), a stray green px at corners where a lower floor is diagonal, light lines down the sides of steps (grass
  recoloured to the lightest earth). A tunnel seen from inside (the cave view): floors only, the hill showing in
  the gap between each step and the next.
- Change:
  - Server (sim/underground.py): a cell inside the land with air beside it (over, under, a side) is dug, and what is
    over it stays, a roof; only from beside it, between your feet and your head (not through the land); a shut-in
    cell is refused with a reason.
  - Build mode: X with the cursor in the ground digs the room to stand there (the two cells over its floor), not the
    column; where no air is beside it: "Dig the step before it first" (red). The character goes down into the
    tunnel to dig the next step (a tunnel's floor is a place to stand). Q a layer down a tile on, X: a step.
  - Drawing: dug earth darkens warm (channels to different floors); walls have no light lines; the px past a wall's
    foot are the floor's earth on each side and the corners south; in the cave view a step down in the tunnel has
    its face, and so does the drop from open ground into it.
- Result: on a throwaway server, five steps south by keys (Q, X, ↓, Q, X...): the first two open, from the third a
  roof ([-3, 0], [-4, 0], [-5, 0]), the character digs from inside and walks down to -5, the cave view continuous.
  Tests: test_climbing (a tunnel dug a step at a time, walked down and up, a shut-in cell refused);
  test_e2e_digging (the way down by keys, the third step under a roof). 449 unit; browser 212 + 3 fixed.
- The live server needs a restart for tunnels (the server's dig); the drawing is in with a reload.
- Next: the cave view's edge art on a narrow tunnel; the sides of steps (dark ledges) could be quieter.

## Iteration 150: a hollow dug under the meadow is drawn open
- User (screenshot, after the restart): "dauben is completely buried and appear here... the underground view is
  buggy as hell". Read on a copy of the save: doben4 at depth -8 at the end of a stair dug east (open steps -3 to -7,
  their own tile a pocket under a roof left at ground level). Rebuilt on a throwaway server: in the pocket the cave
  view's picture stopped 48 px under each hollow, the floor (64 px down) not drawn: they stood on the grass, four
  tiles south of their tile; and as a cave nothing in front was cut away, so the stair leading there was hidden.
- Change: a hollow dug under level ground (floor under sea level, land over it no higher than the meadow: only
  digging makes one) is drawn open, as a hole is (cells.js: levelAt, standAt; what is in it is seen); the cave view
  is for caves under hills (it no longer takes dug hollows; its picture reaches a floor dug deep). A dug step's side
  is a line, not a ledge (it drew a dark post down each step).
- Result: in the pocket the stair is seen joined to where you stand (the ground in front cut away, the user's view),
  a tunnel dug south reads as a trench to the character. Tests: test_e2e_digging (the pocket: drawn at -8, seen, no
  cave view); caves, x-ray, behind, relief, build, world: 50 passed; 449 unit.
- The server need not restart (drawing only): a reload.

## Iteration 151: under ground, audited: one way to be seen, square steps, no flash
- User (screenshot of their stair): "still got the weird green line issue. also there's no gradient, when going
  down/up blocks it flashes... the whole vision underground sucks and deserves a full audit, 'what hides you'".
- Audit, on a copy of the live save (another port) and on a throwaway world: 15 situations built and shot (stairs
  dug east, west, south, north; pits; a shaft; tunnels and a room under a roof; a cave; behind a hill; an L; a
  trench: 27 pictures), and a walk down a stair kept frame by frame. Found:
  1. The green line is not paint: a gap two px wide in the picture seen through the meadow in front, at each step's
     side and at a stair's end. The steps had a hill's rounded shape; what was left over outside it fell under a rule
     made for mountains (rock joining a hill: nothing to see there), and the meadow showed through.
  2. Each step had a dark bar and a wavy foot: the rim of a hill, drawn on dug ground.
  3. The flash: walking down, the height the place was worked out from was the next step's while you were still on
     this one, so the steps two behind you fell out of what is seen through, then came back (the cut-away changed
     twice a step); and the picture coming over the one before was put on the land faint, each for its share: half
     way, a quarter of the meadow showed between them. Measured on a walk down eight steps and back up: 33 frames
     where the green on screen round you jumps and comes back.
  4. A tunnel or a room under a roof was drawn open for good (iteration 150): walking over it, you stood at its
     bottom. Before that, as a cave: its floor far from its stair.
  5. What is seen through ended cut square on the meadow, with no edge: a pit's floor like a sheet of paper.
- Change:
  - Dug ground is cut square (relief.js: a level under sea level is all of its tile; tiles.js: no hill rim on it).
    The px past the lip of the ground round a hole are the wall's earth, one colour (a dashed line along a stair).
  - One way to be seen under ground: the land is drawn as it is from above, a roof is a roof (cells.js). In a
    hollow dug under level ground you are hidden as in a hole, and seen through what hides you (xray.js): the
    place you are in goes under roofs, their floors are kept in the picture (their roof left out, like the rock in
    front), painted by the land's own painter with the levels the picture has (relief.js: R.lk), the tiles round
    them drawn with their edge to them. Who is in that place with you shows; who walks over it fades. Caves under
    hills keep their own view.
  - The place is, in dug ground, all you could walk to under sea level, from your tile's own height: the whole
    stair stays seen as you walk it. Two pictures are added up, each for its share, then put on the land once.
  - In dug ground what is seen through ends in a line, the hole's own outline, where the ground beside it or in
    front stands higher.
- Result: the user's stair on the copy: every step a clean square, darker a layer down, joined to its wall, no
  green; the pocket at its end shows from inside, the meadow is whole from above. The walk: 33 flashes -> 1 (61 px,
  at the top). Tests: test_e2e_digging (a stair: square earth, no meadow in any step as drawn, the steps over you
  still of the place, two pictures half way make a whole one; a tunnel: its roof from above, seen through from
  inside, its floor and the stair down to it); the x-ray's own tests on mountains unchanged.
- Left: what is seen through is nine tiles wide (a long tunnel ends straight at its side); a tunnel that goes on
  under a hill is a cave there; a tree in front of a hole still stands in front of it.

## Iteration 152: under ground you see what light shows
- User (while 151 was being tested): "underground vision should display as much as player can see, it is player
  vision. if fire is here, player see it, so it should be visible . design a proper model". And, before: "there's no
  gradient".
- Looked: a cave under a hill already has a model (cavelight.js): all of the cave is shown, daylight comes in at
  its mouth and dies away over six tiles, you light a little round you, a fire more; the rest is dark. A tunnel dug
  under the meadow had none: seen through its roof four tiles from you and no further (a walk's reach, a picture
  nine tiles wide), all of it as bright as day, then cut off; a fire five tiles on was not drawn.
- The model, one for both:
  1. From above, the land is the land: a roof is the meadow, nobody under it is seen.
  2. In the ground (a hole, a stair, a tunnel, a room) you see the place you are in: all the dug ground you could
     walk to from where you stand, as far as the screen goes (twelve tiles), through whatever hides it from above.
  3. How much of it you see is light: under the sky, daylight; under a roof, daylight a few tiles in from where the
     place is open to the sky, a little round you (and round anyone else there), more round a fire however far it
     is; between them it is dark, not gone.
  4. Whatever is in the place is drawn with it: a fire, what lies there, who stands there. Who walks over it fades.
- Change: xray.js: ground that was dug is of the place as far as XRAY.wide (12 tiles), the picture as wide and as
  tall as that ground is drawn (it was 9 tiles, round you). cavelight.js: drawUnderDark, the cave's light on the
  picture's px under a roof (each px from its tile's light and the tiles' beside it; 0.4 ms a frame); the picture
  of a twenty-tile tunnel is painted in 9 ms, over 3 to 5 frames. xrayviews.js: the views that are not the circle,
  out of xray.js (300 lines). Build mode, ladders and what is on a tile go by the tile's real ground (cells.js:
  groundAt), not by how it is drawn: a step's test failed now and then under load, the tunnel seen through or not
  when X was pressed.
- Result (a tunnel 14 tiles long with a fire, a side tunnel to a room with a fire, by day and by night, looked at):
  from the mouth the tunnel is bright, darkens, and the fires show lit in the distance; at night only you and the
  fires light it. 60 frames a second walking it. Test: test_e2e_digging (a fire nine tiles in: drawn, its tile lit,
  the tunnel between dark, the mouth bright).
- Left: light goes round corners (no line of sight); a tunnel under a hill is still a cave there.

## Iteration 153: one way to be seen when you are hidden
- User, with a picture of a stair dug west under a hill: "this is very weird and ugly !". Then: "everything should
  have the same view ! not per-situation view. there should be an unique 'player is hided, xray on' view".
- Looked (a copy of the live save, the watcher on doben4's tile): the stair runs under a hill, so it was drawn by
  the cave's own view (caves.js): each floor alone, flat, where it is drawn (a layer down, half a tile south), no
  wall behind it: five squares of earth lying on the hill, up to three tiles south of the stair. Iteration 151 gave
  hollows under the meadow to the x-ray and left hollows under hills to that view: two ways, and the stair crossed
  from one to the other.
- Was wrong: I called it "left" in 152 ("a tunnel under a hill is still a cave there") and shipped it. A second view
  for the same situation is a bug, not a leftover.
- Change: one rule. The land is always drawn as it is. Where you are hidden (ground in front, or a roof: a hill, the
  meadow over a tunnel), the x-ray is on and shows the place you are in through what hides it; nothing else does.
  - cells.js: `hollow` (any roof) in place of dugHollow; caveOpen, openCave, inOpenCave gone. caves.js keeps what a
    cave is from outside (its mouths on the hill) and loses its open view, its shadows and its floors (271 lines to
    190). cavelight.js: one light, under any roof (107 to 48).
  - xray.js: the place goes under roofs of any kind, as far as dug ground did (12 tiles). Behind a floor under a
    roof its wall goes up to the top of the land, cut open (the land's painter did that already); of it, the hollow's
    own back wall is as it is and the roof cut through over it is earth in the shade (relief.js notes which px are a
    wall's band): a burrow in a bank, as high as the hollow is. Earth left between two parts of the place (two
    tunnels side by side, a pillar) is cut level with the floor behind it and shows as cut earth: the land as drawn
    showed there, a strip of meadow between two floors, the nearer tunnel a floor on the grass.
  - A hill's side rule (no wall where rock left out joins a kept hill) is not for a floor under a roof: it left a
    green notch in the wall. The mouths of the place you are seen in are not drawn on its hill (a dark line stayed
    under the picture); a picture's own mouths go by that picture, not by the one shown while it is painted (the
    pixel test caught it).
- Result: on a sheet of 24 situations before and after (stair under a hill, cave room, passages through a hill, tunnels
  four ways, a room, two tunnels, eight down, a cave with a stair dug in it, behind a hill, a pit, a shaft), and on
  the live copy: the stair is a lit tunnel in dark earth under the hill, a cave is its room with the wall behind it;
  behind a hill, a pit, an open stair: as they were, to the eye. Filmed walking down the stair and into a cave: no
  frame brighter or darker than the ones beside it by more than a step.
- Measured before landing it, in a cave 22 x 12 under a hill: the picture was nine tiles wide (it took its size from
  dug ground alone), a square hole in the hill; and the cave's mouth was dark unless the meadow outside it was near
  you. Now the picture is as wide and as tall as the place under its roof, up to the top of the land behind it, and
  a way out is in daylight wherever it is. That cave (266 floors on the screen): the picture 12 ms, painted over 4
  to 6 frames; the light 1.1 ms a frame; 60 frames a second walking, 14 frames of 206 over 20 ms (worst 28).
- Tests: the cave view's two tests are now the x-ray's (in a cave; in from behind a hill); new: the stair under a
  hill (floors, the wall behind each up to the land's top, roof darker than the back wall), two tunnels (cut earth
  between, no green), a cave eighteen wide (both its ends in the picture, its far mouth in daylight, its middle dark).
- Left: a cave's floor has no soft shadow along its walls any more (the land's painter has none); light still goes
  round corners; the picture stops twelve tiles from you in a cave larger than that.
- Then, from the user: "How does it looks like now ? Do a demo on static demo website GH pages". Filmed it
  (tools/film_underground.py, 31 s: a stair under a hill, a cave with a fire, V through the four views, a tunnel by
  night, the meadow over it) for the "What's new" page, and looked at the frames first. Two things they showed:
  - At night a fire in a tunnel lit a ring of the meadow over it, and standing on the meadow over a fire you stood
    in its glow: night's lights were drawn where they are on the screen, roof or no roof (so who hid under the
    ground at night glowed through it too). Now a light under a roof lights what the picture shows under that roof,
    and nothing when it is hidden (daylight.js: underRoof; cavelight.js: underPx, the picture's px under a roof,
    made once). A test: the meadow over a fire four down is as dark as the meadow anywhere (520 against 323 before).
  - Standing on the meadow over a campfire in a tunnel, the game offers "Campfire: cook here": what is on a tile is
    acted on whatever height you are at. Not fixed here: it is the rules' question too (intent.js reads the tile's
    thing; the server's reach counts tiles, not height). Open.
- The page's two pictures of the view before this one (the land over you dimmed) are gone. The pixel test of the
  x-ray failed once in a loaded run (4176 px) and passed 3 times alone and in four runs at once: not understood.
- Then, on the published clip: "The borders are still abrupt, like cut without separation". The earth cut open
  stopped square against the grass: the only line was on dug floors, in a brown that does not show on dark earth,
  and none on walls or in caves; and the soft shadow the old cave view had along its floor was gone with it. Now
  where the cut ends against the land in front of it or beside it there is a line (a dark brown of the pack's
  kind) and a shadow three px in from it, in steps: the place reads as set into the ground. Not over it where the
  land's own edge is (its grass hangs there), nor across a way out (ground that goes on level with a floor), nor
  between two floors of the place. The earth's own drawing (cut earth between tunnels, the roof cut through, the
  edge) is its own file, xraycut.js (xray.js was at 291 lines). Looked at on nine situations at two zooms; behind
  a hill is as it was. Tests: the line and the shadow at a tunnel's front and end, none between its floors; a line
  along a cave room's side, none across its doorway.
- Then, on a zoomed picture of a room: "Outline is buggy here !". Three things in it: the line ran beside the
  land's own rim (the tile beside the room has its edge drawn toward it: two outlines side by side, the rim stopping
  half way down and the line going on alone); the line stopped short of the top of the wall; and a dark dot sat
  where the stair's wall meets the room's. Now there is one edge: no line where a tile beside the place or behind
  it has its own edge there, the line from where that ends, and a wall's band counts as the tile in front of it (a
  hill's edge is set in two px: those two rows were taken for the tile behind, a border two px high with its shadow
  round it). The line is the land's brown, a little darker (112, 70, 58), not ink. Looked at px by px at the
  junctions (a map of what each px is), then on the 24 situations.
- Then: "Top outline is kinda broken. Also make outline the default". The outline view (V) drew its line round
  all that the ground in front had been drawn over. Since iteration 151 that is more than the cut: the tiles beside
  the place are in the picture with their own edge, so the line ran a tile out from the cut, on top and on each
  side; it also crossed a stair's wall where the meadow's edge had been, and went round the sliver of meadow a
  hill's side had covered. Now, in the ground or under a roof, the outline goes round the place itself as one
  shape (xraycut.js says which px are the place's: dug, under a roof or cut, seen through or not; a wall's
  in-between px, the tile behind painted a level down, count as the tile in front, like its bands); behind a hill
  and no more it is as it was. Outline is the usual view (options.js): who never chose gets it, who chose keeps
  theirs. Looked at on the 24 situations in the usual view. Tests: the line along a tunnel's wall top, its floor's
  front and its end, none a tile out, none across it or the stair's wall; V starts from the outline.
- Then, on a zoomed picture of the stair: "It goes under the background tiles. Completely.." The tiles beside a
  place under a roof were drawn again with a hill's edge toward its floor (grass and lip, as round an open hole:
  iteration 151). Over the top of the cut that put the land's tiles on the picture: the outline ran under them, in
  hooks at every step of the wall's top. Now those tiles stay as they are on the land and the cut is a window in
  it, straight along its tiles, with its own edge all round (a hole open to the sky keeps the land's rim: that is
  the land). The place's shape is worked out from whole tiles (each tile's column from the top of the wall behind
  it to the foot of its floor), not a px at a time from what each px was painted as: where a hill steps down
  beside the wall, slivers of grass showed in it and the line went round them; those px are the wall's band now.
  Land that stands in front of the place and is not left out (a hill's face before a cave's room, seen from its
  mouth) is not of its shape.
- Then, on the sheet: "The line shouldn't show up at intersections with same level": the outline closed a cave's
  doorway and both ends of a passage, where the floor goes on level with the meadow. It is open there, as the
  cut's own line already was. Tests: no line across a cave's way out; the hill beside a room is as it is.
- Then, a crop of where the stair under its roof meets the open pit: "Weird artefact here". A px map of the corner
  showed three things. The slivers made into wall kept their level and were not marked as wall, so against the
  meadow beside them they counted as ground that goes on level with it: no line for the top two px and down the
  side. The end of a ledge that had hung from the roof's side (two px by two) and the band under it, two px out of
  step with the wall's, stood in the pit's wall: the line went round them in a hook. And along the pit's own side the
  meadow tile's set-in edge shows two px of itself painted a level down: taken for ground level with the floor, no
  line there. Now: a wall cut through is its bands and no more (a px there that is anything else, or a band out of
  step, is the band as the painter paints it); the four px of an open hole's wall next to a roofed tile are that
  wall's own px from further in (relief.js hands its px over); and ground level with a floor is a tile's own top,
  not what shows of it a level down.
- The demo's pages name every script, style and clip, the worker and the game's Python with the build's own mark
  (tools/build_pages.py: stamp): GitHub Pages lets a browser keep a file ten minutes and a phone keeps a clip
  longer, so a page loaded again after a publish could be the build before ("Now update the demo": it was, the
  files compared equal).
- Then two more crops. "Upper is weird here": on the staged stair the first tile of the open pit has a hill behind
  it, and the outline ran under the land's own rim there, along its curved foot. One edge for the outline as for
  the cut's line: the land's rim where it has one (round what is open to the sky), the line elsewhere; which tile
  has a rim is asked of the tiles, not of what each px was painted as (stubs stayed at a rim's rounded corners).
  And: "There shouldn't be a line where player can travel to outside (outside notion isn't really to be taken as
  it..)": a stair's top step was lined off from the meadow you step onto it from. The rule was ground level with
  the floor; it is now the game's own step (cells.js: landAt): no line on a side of a floor you can walk off that
  way, level, a step up or a drop. Tests: no line west of a stair's top step nor in front of it, one under the
  next; none under an open stair's rim.
- Then: "See how lightning is cut ? Uniformise it with a real lightning model, sun outside goes inside etc". Two
  things lit the place: the floors and walls under a roof took their tile's light, and the earth cut through over
  them was a flat shade darker, baked into the picture, from the roof's edge on: a line down the wall where the
  roof starts. And a light counted its reach as the crow flies: a fire lit the tunnel beside its own through the
  earth between them (at night its glow too). One model now (cavelight.js), for every px of the place, under a
  roof or not: under the sky, the light outside; under a roof the sun comes in at every way out and fades along
  the way; you, the others, a fire light round them by the longer of the straight line and three quarters of the
  tiles walked (a search over the place's tiles, kept a picture); earth cut through has the sky's light alone, for
  two tiles and a half. Each px takes it from its tile and the tiles beside it. Night's lamps under a roof go over
  the columns of the tiles they reach, no further (daylight.js; xraycut.js hands the columns over).
- And: "Tile transition is broken there": beside a roofed floor that has a part of the place open to the sky beside
  it too, the tile behind kept the corner the hole's rim turns on the land, a wedge of earth over the corner of the
  cut. That tile is drawn without it (xray.js): the rim ends where the cut starts.
- Tests: the dark of the wall's top is the same on both sides of where a roof starts and grows with the way in; by
  night a floor two tiles from a fire is lit and the floor of the tunnel beside it, straight across the earth, is
  not. The tests that read the baked shade read the light.
- The x-ray's pixel test, which failed now and then on a loaded machine (4176 px, the same each time), was mine:
  the picture of a cave's mouths on its hill is drawn again when the place seen through its roof changes, and that
  was put off while any tile was still being drawn. It is drawn at once now (caves.js); two loaded runs pass.
  tests/e2e/test_e2e_underground.py: the tests of being seen under ground, out of test_e2e_digging.py (313 lines).
- And: "This border is weird", the east end of an open stair: the thin line the land paints down a dug tile's side
  (its side wall, a px or two) was left out of the place's shape, so the outline ran two px in from the tile's edge,
  a strip of wall outside it, and missed the floor's corner. It is of the place: the line is on the tile's edge.
- Then: "Still got a weird tileset jump", where the stair open to the sky goes in under the hill. Measured on the
  screen, a px at a time (a column each side of the seam): the wall cut through had its bands on the tiles' lines;
  the land's own wall, of a hole open to the sky, has the bands over the sea's level two px up (a hill's edge is set
  in two px) and two px of the tile's foot under them. So every line of the wall broke by two px where the roof
  starts. The cut lays its bands as the land does now (xraycut.js); it still starts on its tile's line, so its first
  band is two px short. At that corner too: two px of the cut's ink went up the side of the pit's wall, into its
  rim (no line there now), a px of wall was left in the corner of the tile behind the roof (grass now), and the
  earth's dark started at half its strength at the very line where the roof starts (cavelight.js: from nothing).
- What I tried first and threw away: the land's own rim round a place under a roof, as round a pit, so that both
  sides of the seam were one thing. It is what the user had sent back before ("It goes under the background tiles.
  Completely.."): I looked at that picture again before landing it. The roof's top stays a clean line.
- Test: the rows of the wall that are darker than those over and under them are the same down the pit's wall and
  down the wall under the roof beside it (5, 15, 23, 31; they were 7, 15, 23, 31), no line up the pit's side, grass
  to the corner, the dark next to nothing at the seam. It fails on the code before.
- Wrong in the entry above: the x-ray's pixel test is not fixed. It failed again on a loaded machine, at its first
  place, 4176 px, with the caves' redraw at once. It now says where the two pictures differ: a box a tile and a half
  wide at the east end of the water, beside the cave's plateau, not at the cave's mouth. Cause not found; it passes
  alone and in most loaded runs (it failed in two of about twelve today).
- Then, on the picture of that seam: "Lightning show clear distinction with floor. And the first step of the stairs
  look awkward".
  The light: the earth cut through over a hollow had the sky's light alone, so from the second tile in it was much
  darker than the hollow under it and its floor: down a dug stair, a stair of light and dark with hard edges. That
  was my "burrow in a bank", and it is the cut in the light the user had asked to be rid of. One light now: every
  px of the place, wall, earth or floor, has its tile's (cavelight.js, 93 lines; xraycut.js no longer says which
  px are earth).
  The first step: a floor one step under the meadow in front of it was seen whole through that meadow, a flat
  square lying on the grass with no edge (no line there: you can walk off it), and the pit's rim stopped short at
  its corner. A step up in front of a floor is not cut through any more (xray.js: only ground two layers over a
  floor hides it): it is the way out, and it keeps its edge as on the land. It is also what you see standing on
  that step, so nothing changes as you walk down. And the side of the next step, which is against that meadow now,
  has its line: the line's rule looked at the tile stepped onto that way, not at the ground that is really beside
  the px (ground in front of that tile, a row on, is cut through: a line).
- Tests: the earth over a tunnel is as dark as the floor under it, two and four tiles in; the first step's meadow is
  not rock and not seen through, and the second step has its line down its side; the stair test said every step was
  seen whole: every step but the first. The new test of the seam read the screen while one picture was still coming
  over another, once, on a loaded machine: it waits for the picture to be whole.

