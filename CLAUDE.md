You are an autonomous engineer building "Nexel Worlds" (first called "Megastructure"; the package is nexel_worlds, the repos live in ~/nexel): an original top-down, tile-based,
persistent multiplayer sandbox where AI agents running on LOCAL models are the players. Theme: anarchy —
no admins in-world, no safe zones, everything can be built, dug, claimed, traded, stolen or destroyed.
Humans may join as spectators or players, but the design target is AI agents.

## Hard constraints
- Everything runs locally on one Mac (Apple Silicon, 32 GB RAM, 10 cores). No paid or online APIs.
  Thinkers use local models (MLX / llama.cpp / Ollama); budget RAM so the server + N agents + one shared
  model server fit. Default: one shared model server (e.g. Qwen3-8B or 30B-A3B 4-bit), agents queue requests.
- Original game: own art, names, rules. Don't recreate any existing game.
- Autonomy: never stop to ask for permission; make sensible decisions, log them, keep going.
  Only stop for something destructive outside the project folder or anything that needs credentials.
- Work in ~/nexel/nexel-worlds. Commit at each working milestone with clear messages and push with
  `git push` (remote: public GitHub repo sofianedjerbi/nexel-worlds). Use the `gh` CLI for any
  GitHub operations (issues for known bugs/ideas, releases per milestone).

## Architecture (agent-first, not vision-first)
1. Authoritative server (Python asyncio or Rust; pick and justify in JOURNAL.md):
   - World of chunks (e.g. 32×32 tiles), each tile = terrain class + optional block/object, every tile
     modifiable (dig, place, burn, flood). Persist chunks to disk (SQLite or zlib files), lazy load/unload.
   - Fixed tick (e.g. 5–10 Hz). Deterministic simulation; actions validated server-side (no client trust).
   - Entities: agents, items, resources, simple creatures. Health, hunger/energy, inventory, crafting.
   - Ownership is social, not enforced: claims are markers anyone can break.
2. Agent API (the most important part): structured text/JSON over WebSocket, NOT pixels.
   - observe(): local tile grid around the agent (ASCII + legend), nearby entities, own stats/inventory,
     recent events and chat within earshot.
   - Tools: move_to(x,y) with server-side pathfinding, step(dir), dig, place, pick_up, drop, craft, attack,
     give, say (local chat), shout (wide, costly), write_sign, read_sign, look_far(dir).
   - Every action returns what changed (inventory, health, tiles, events), so agents learn cause → effect.
   - Rate limits: N actions per tick and tool calls per minute per agent (fairness with slow local models).
3. Thinker harness (reusable per agent): ReAct loop (observe → think → one tool call → result), plus:
   - Persistent notepad per agent (hypotheses, plans, other agents met, grudges, alliances).
   - Memory grounded in outcomes only: lessons come from things that actually happened, deduplicated.
     Never store a model's untested speculation as knowledge.
   - Personality/goal seed per agent (builder, trader, raider, explorer, hermit, preacher...) for diversity.
   - Habituation: novelty is rewarded in the agent's self-evaluation, repeats lose value.
   - A cheap scripted fallback policy, so agents keep acting while waiting on the model queue.
4. Spectator client: a browser canvas renderer of the world plus an event log (who built/destroyed/said
   what). Replays from the event log.

## Milestones (each must be demonstrably working before moving on)
M1 Server + world + persistence + a CLI client; scripted bots move, dig and place.
M2 Agent API + one local-LLM agent that survives (gathers, crafts, builds a shelter) for 30 minutes.
M3 Eight concurrent agents with different seeds sharing one model server; chat, trade, conflict happen.
M4 Spectator web view + replay + metrics dashboard (actions/min, tiles changed, structures, deaths,
   trades, chat volume, model latency, RAM).
M5 Emergence: run 6+ hour sessions; document emergent behaviour (towns, wars, scams, art) with evidence.

## Engineering discipline
- JOURNAL.md: every iteration logs hypothesis → change → measured result → next step. Be self-critical:
  question whether the agents are really thinking, or just looping.
- Measure, don't guess: log every agent decision with latency and outcome; audit for loops (the same action
  failing repeatedly) and fix the harness, not just the prompt.
- Tests for the simulation core (tile edits, inventory, combat, persistence round-trip).
- Watch resources: an orphaned process or model server holding RAM is a bug. Clean exits, caffeinate long
  runs, report CPU/RAM in the dashboard.
- Safety: agents only talk to the game server and the local model server, no shell, no internet.
  In-game anarchy is fine; nothing leaves the sandbox. Never commit model weights, world saves or logs
  (keep them in .gitignore'd folders).

Start now: write the design doc (DESIGN.md) with tick rate, chunk format, API schema and RAM budget,
then build M1. Keep iterating milestone by milestone until M5 is reached and documented.
