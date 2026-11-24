# Nexel Worlds — Design

An original, persistent, top-down tile world. The players are AI agents driven by local language
models; the world has no rules beyond physics. Anything can be built, dug, burned, flooded, claimed,
traded, stolen or destroyed. Claims are only markers.

## 1. Stack decision

**Python 3.14 + asyncio + `websockets`, SQLite for persistence.**

- The bottleneck is the thinker (a local LLM: 0.5–5 s per decision), not the simulation. A 5 Hz
  sim over a few hundred loaded chunks and tens of entities is a few milliseconds per tick in Python.
- The harness, the model client and the server share one language, which makes it cheap to iterate.
- If profiling shows the tick budget (200 ms) under pressure, hot paths (pathfinding, fluid and fire
  spread) move to numpy or a small Rust extension. That decision is deferred until it's measured.

## 2. World

### Coordinates
- Integer tile coordinates `(x, y)`, with `y` increasing southward. N = (0,-1), E = (1,0), S = (0,1), W = (-1,0).
- The world is unbounded and generated lazily from a seed. The spawn region is around (0,0).

### Tiles
Each tile has two layers, one byte each:

| layer   | meaning | examples |
|---------|---------|----------|
| ground  | what you stand on | `water`, `sand`, `grass`, `dirt`, `pit`, `stone_floor`, `ash`, `deep_water` |
| block   | what occupies the tile (0 = none) | `tree`, `bush`, `rock`, `ore`, `wood_wall`, `stone_wall`, `door`, `campfire`, `workbench`, `sign`, `flag`, `fire`, `crop` |

The block's properties (solid, flammable, hardness, drops) come from a static table in `tiles.py`.
Free-form data (sign text, flag owner text) is kept in a per-world `tile_meta` table keyed by `(x,y)`.

### Chunks
- 32×32 tiles. Chunk `(cx, cy) = (x >> 5, y >> 5)`.
- In memory: two `bytearray(1024)` (ground, block) plus a dirty flag and the tick it was last touched.
- On disk: SQLite table `chunks(cx, cy, data BLOB)`, where `data = zlib(ground ‖ block)` (2048 bytes raw,
  usually about 200 bytes compressed).
- Lazy load: any access to an absent chunk loads it from the DB, or generates it from the seed.
- Unload: every 10 s, chunks more than 3 chunks away from every agent and untouched for 30 s
  are saved (if dirty) and dropped. All dirty chunks are flushed every 10 s and on shutdown.

### Generation
Deterministic value noise (pure Python, seeded hash). Elevation decides water, sand, grass or rock
fields. Moisture decides tree and bush density. Ore appears in rock clusters. The same seed always
produces the same world.

## 3. Simulation

- **Fixed tick: 5 Hz** (200 ms). The world clock is `tick`; one day is 3000 ticks (10 min).
- **Determinism:** each tick runs in a fixed order. (1) Agent actions run in ascending agent id,
  one step per agent per tick. (2) Creatures. (3) Environment: fire, flood, regrowth, on
  a per-tick RNG seeded with `hash(seed, tick)`. (4) Needs: hunger, energy, health.
  Given the same world state and the same action inputs at the same ticks, the result is identical.
- **Server-side validation:** clients send intents. The server checks adjacency, inventory,
  tool requirements and solidity. Clients can't teleport or spawn items.

### Actions (multi-tick)
Each agent has **one action in flight**. An action runs for one or more ticks, then completes
or fails and returns a delta. A new action replaces any queued one (the caller gets
`interrupted`).

| tool | ticks | effect |
|------|-------|--------|
| `step(dir)` | 1 | move one tile if passable |
| `move_to(x,y)` | 1/tile | A* path (max 64 tiles, 4000 nodes), recomputed if blocked |
| `dig(dir)` | hardness / tool | removes the block (drops items). On bare ground: grass/dirt/sand → `pit` (+dirt) |
| `place(dir, item)` | 2 | places a block item on an empty, non-water adjacent tile. `dirt` fills a pit or shallow water |
| `pick_up()` | 1 | picks up all ground items on the agent's tile |
| `drop(item, n)` | 1 | drops items on the agent's tile |
| `craft(recipe)` | 3–10 | consumes inputs and yields output. Some recipes need a workbench or campfire within 2 tiles |
| `attack(target_id)` | 2 | melee within 1 tile. Damage depends on the weapon |
| `give(target_id, item, n)` | 1 | transfers items to an agent within 2 tiles |
| `eat(item)` | 2 | restores hunger |
| `rest()` | 10 | restores energy (faster near a campfire or under shelter) |
| `say(text)` | 1 | chat heard within 12 tiles |
| `shout(text)` | 1 | heard within 48 tiles. Costs 10 energy |
| `write_sign(dir, text)` | 3 | sets the text of an adjacent sign (≤ 200 chars) |
| `read_sign(dir)` | 1 | reads an adjacent sign |
| `look_far(dir)` | 1 | coarse 9×48 strip in a direction (1 char per 2×2 tiles) |
| `ignite(dir)` | 2 | needs a torch or campfire nearby. Sets a flammable block or grass alight |

### Needs and death
- Hunger 0–100 drops 1 per 50 ticks. At 0 the agent loses 1 HP per 25 ticks.
- Energy 0–100 drops with work (dig 1, attack 2, shout 10). At 0, actions take twice as long.
- HP 0–100. Death drops the whole inventory on the tile. The agent respawns near a random spawn
  point with an empty inventory and a `deaths` counter. Identity and memory persist; possessions don't.

### Environment
- **Fire:** `fire` blocks burn for 25–75 ticks and spread with p = 0.02/tick to flammable neighbours
  (trees, wood walls, doors, grass ground), then leave `ash` ground. Water stops it.
- **Flood:** a `pit` next to water becomes water with p = 0.05/tick. Water doesn't spread over
  ground that isn't a pit.
- **Regrowth:** stumps and bushes regrow slowly in loaded chunks (p = 1e-4/tile-tick on grass).
- **Creatures:** `grazer` (passive, gives meat and hide) and, at night, `prowler` (hostile, weak).

## 4. Agent API (WebSocket, JSON text frames)

Endpoint `ws://127.0.0.1:7777/agent`. Every client message has an `id`, and the reply echoes it.

```jsonc
// → login. The name identifies a persistent character, the token protects it
{"id":1,"op":"hello","name":"Ash","token":"secret","persona":"builder"}
// ← {"id":1,"ok":true,"agent":{"id":3,"name":"Ash","x":4,"y":-2,...},"tick":1234,"protocol":1}

{"id":2,"op":"observe"}
// ← {"id":2,"ok":true,"obs":{
//      "tick":1240,"time":"day 2, 14:20","self":{"x":4,"y":-2,"hp":100,"hunger":80,"energy":95,
//      "inventory":{"wood":3},"action":null},
//      "grid":["~~..T..","..@..#.",...],   // 21×21 centred on the agent, row 0 = north
//      "legend":{"~":"water","T":"tree",...},
//      "entities":[{"id":5,"kind":"agent","name":"Bryn","dx":3,"dy":-1,"hp":90}],
//      "items":[{"dx":1,"dy":0,"item":"stone","n":2}],
//      "events":[{"tick":1238,"type":"say","from":"Bryn","text":"hi"}],  // since last observe
//      "signs":[{"dx":-2,"dy":0,"text":"MINE. keep out"}]}}

{"id":3,"op":"act","tool":"dig","args":{"dir":"N"}}
// ← sent when the action finishes:
// {"id":3,"ok":true,"result":{"tool":"dig","status":"done","ticks":6,
//   "changed":{"inventory":{"wood":+2},"tiles":[{"x":4,"y":-3,"block":"none"}],"energy":-1},
//   "events":[...]}}
// or {"id":3,"ok":false,"error":"blocked","detail":"tile N is water"}

{"id":4,"op":"tools"}      // ← machine-readable tool list with arg schemas (for LLM prompts)
{"id":5,"op":"recipes"}    // ← the recipe book
```

Spectators connect to `ws://127.0.0.1:7777/spectate` and receive `{"type":"tick", ...}` deltas
and the event stream (M4).

### Rate limits
- One action in flight per agent (more `act` calls interrupt the current one).
- 120 `act` + 120 `observe` calls per rolling minute per agent. Excess calls get `rate_limited`.
- `say` max 6/min, `shout` max 1/min.

## 5. Persistence and the event log

`saves/<world>/world.sqlite`:
- `meta(key, value)`: seed, tick, version
- `chunks(cx, cy, data)`
- `tile_meta(x, y, json)`
- `agents(id, name, token_hash, json)`
- `ground_items(x, y, json)`
- `creatures(id, json)`

`saves/<world>/events.jsonl` is an append-only stream of every state-changing event
(`tile`, `move`, `item`, `say`, `attack`, `death`, `craft`, ...) with ticks. Replays read it.

## 6. Thinker harness (M2+)

There is one harness process per agent (or several agents as asyncio tasks in one process). It talks
to the game over the Agent API and to **one shared local model server**: `mlx_lm.server`, an
OpenAI-compatible HTTP server on 127.0.0.1. Requests from all agents go through a FIFO, so one
generation runs at a time.

The loop is observe → prompt (persona, notepad, lessons, observation, last results) → one
tool call (JSON) → execute → record the outcome. A scripted fallback policy keeps the agent alive
while the model queue is long. Lessons are written only from observed outcomes and deduplicated.

## 7. RAM budget (32 GB machine)

| component | budget |
|-----------|--------|
| macOS + desktop apps | ~8 GB |
| model server: Qwen3-30B-A3B-Instruct-2507 4-bit (weights ~16 GB + KV ~2 GB) **or** Qwen3-8B 4-bit (~5 GB + 1 GB) | 18 GB / 6 GB |
| game server (Python, ~200 chunks, entities, SQLite) | < 0.5 GB |
| harness for 8 agents (one process) | < 0.5 GB |
| spectator/dashboard | < 0.2 GB |
| **headroom** | ≥ 4 GB with 30B-A3B |

Both models are already in the local HF cache. M2 benchmarks both and picks one, measuring
decision latency against decision quality. The server and the harness report their RSS on the dashboard.

## 8. Milestones
M1 server, world, persistence, CLI, scripted bots · M2 one LLM agent survives 30 min ·
M3 eight agents, one shared model · M4 spectator, replay, metrics · M5 6 h+ emergence runs.
