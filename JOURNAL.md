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
