"""Developer tools for QA (only with --dev): time travel, teleport, items, damage, painting tiles."""

from .sim import DAY_TICKS, TICK_HZ
from .tiles import BLOCKS, GROUNDS


def dev_op(sim, agent, op: str, msg: dict) -> dict:
    """Run one dev op for `agent`; returns the reply fields."""
    if op == "dev_time":                         # jump to a time of day (0..1, 0.75+ is night)
        # forward only (tomorrow if that hour is past): the clock going back left everyone waiting on cooldowns
        # stamped in what was now the future (nobody could walk for minutes)
        t = sim.tick // DAY_TICKS * DAY_TICKS + int(float(msg.get("phase", 0.8)) * DAY_TICKS)
        sim.tick = t if t >= sim.tick else t + DAY_TICKS
        return {"tick": sim.tick}
    if op == "dev_pace":                         # the world's clock runs `pace` times as fast (ticks a second: ticking.py tick_loop): the
        sim.clock_rate = max(.05, min(16.0, float(msg.get("pace", 1))))   # browser tests' clock (tests/e2e/clock.py), whose pages run theirs as fast
        return {"pace": sim.clock_rate}
    if op == "dev_skip":                         # fast-forward the simulation
        for _ in range(min(int(float(msg.get("seconds", 10)) * TICK_HZ), 20000)):
            sim.step()
        return {"tick": sim.tick}
    if op == "dev_teleport":
        sim.interrupt(agent, "moved")            # (whatever they were doing, walking somewhere: not from here)
        agent.x, agent.y, agent.z = int(msg["x"]), int(msg["y"]), int(msg.get("z", 99))   # (z: up top unless given)
        return {"x": agent.x, "y": agent.y}
    if op == "dev_damage":
        sim.damage(agent, int(msg.get("n", 10)), "dev")
        return {"hp": agent.hp}
    if op == "dev_stamp":                        # paint ASCII rows of tile chars at x, y (QA builds), on flat land
        bch, gch = {b.char: b.name for b in BLOCKS}, {g.char: g.name for g in GROUNDS}
        x0, y0 = int(msg["x"]), int(msg["y"])
        levels = list(msg.get("levels") or [])  # optional rows of heights: as the agents see them (0-9, A-C, a-l below)
        roofs = list(msg.get("roofs") or [])    # optional rows of the rock over each tile (a cave), digits
        heads = list(msg.get("heads") or [])    # ...and of how many cells of that are empty over the floor, digits
        for j, row in enumerate(list(msg.get("rows") or [])[:200]):
            for i, ch in enumerate(str(row)[:200]):
                lc = levels[j][i] if j < len(levels) and i < len(levels[j]) else "0"
                lv = int(lc) if lc.isdigit() else ord(lc) - 55 if lc.isupper() else 96 - ord(lc)
                rf = int(roofs[j][i]) if j < len(roofs) and i < len(roofs[j]) else 0
                hd = int(heads[j][i]) if j < len(heads) and i < len(heads[j]) else None
                if ch in gch:
                    sim.set_tile(x0 + i, y0 + j, ground=gch[ch], block="none", level=lv, roof=rf, head=hd)
                elif ch in bch:
                    sim.set_tile(x0 + i, y0 + j, ground="grass", block=bch[ch], level=lv, roof=rf, head=hd)
        return {}
    if op == "dev_creatures":                    # clear creatures within `clear` tiles; spawn {"kind", "dx", "dy"}
        from .sim import CREATURES, Creature
        r = int(msg.get("clear", 0))
        for cid in [c.id for c in sim.creatures.values() if max(abs(c.x - agent.x), abs(c.y - agent.y)) <= r]:
            del sim.creatures[cid]
        if "clear" in msg:                       # ...and what lies on the ground there: a pile one test left was drawn,
            for at in [p for p in sim.items if max(abs(p[0] - agent.x), abs(p[1] - agent.y)) <= r]:   # and counted, in
                del sim.items[at]                # the next one's, whenever its player woke near it
            sim.water.clear_near(agent.x, agent.y, r)     # (and water one left running, poured: flow.py. A can's puddle swam a later test's player)
        spawned = None
        if msg.get("kind") in CREATURES:
            c = Creature(sim.next_creature, msg["kind"], agent.x + int(msg.get("dx", 1)), agent.y + int(msg.get("dy", 0)),
                         CREATURES[msg["kind"]]["hp"], z=sim.height(agent), cooldown=int(msg.get("still", 0)))   # (at your height, or the ground under it)
            sim.next_creature += 1
            sim.creatures[c.id] = c
            spawned = c.id
        return {"spawned": spawned}
    if op == "dev_hit":                          # a blow of n on `creature` (its id), as if you had struck it (its shell, its sky: combat.py)
        c = sim.creatures.get(int(msg.get("creature", -1)))     # (not "id": that is the message's own, its answer's address)
        if c is not None:
            sim.damage(c, sim.shell(c, int(msg.get("n", 10))), "dev", by=agent)
        return {"hp": c.hp if c is not None and c.id in sim.creatures else 0}
    if op == "dev_luck":                         # every line of a creature's drops is sure (or back to its chance: luck=1)
        sim.luck = float(msg.get("luck", 1000))
        return {"luck": sim.luck}
    if op == "dev_race":                         # become another race (looks only)
        from .tiles import RACES
        if msg.get("race") in RACES:
            agent.race = msg["race"]
        return {"race": agent.race}
    if op == "dev_needs":                        # set food (and health)
        agent.hunger = max(0, min(20, int(msg.get("hunger", agent.hunger))))      # (half pieces: 20 is full)
        agent.sat = float(msg.get("sat", 0 if "hunger" in msg else agent.sat))    # (no reserve unless asked for: what is set is what shows)
        agent.hp = max(0.5, min(20, float(msg.get("hp", agent.hp))))               # (half hearts: 20 is ten hearts)
        return {"hunger": agent.hunger, "hp": agent.hp}
    if op == "dev_col":                          # land laid out a column at a time, at any depth: `tiles` [[x, y]...], each `col`: the heights where it changes (cells.col_runs); `dug`: as if dug to that: its rock stays what it was (chunks.py)
        from .cells import runs_col
        col, tiles = runs_col([int(v) for v in msg["col"]]), [(int(p[0]), int(p[1])) for p in msg.get("tiles") or []]
        for x, y in tiles:
            sim.raze(x, y)
            sim.world.chunk(x >> 5, y >> 5).cols[(y & 31) * 32 + (x & 31)] = col
        for x, y in tiles:                       # (laid out, all of it: its stone by the land round it; dug: as it was)
            if not msg.get("dug"):
                sim.world.relay(x, y)
            sim.set_tile(x, y, cause="dev", ores=True)
        return {}
    if op == "dev_admin" and getattr(sim, "admins", None):    # you are an admin (the tests' /op: admin.py)
        if not agent.bot:
            sim.admins.op(agent.name)
        return {"admin": sim.admins.is_admin(agent)}
    if op == "dev_give":
        for k, n in dict(msg.get("items") or {}).items():
            agent.add(str(k), int(n))
        return {"inventory": agent.inventory}
    return {"ok": False, "error": "unknown_op", "detail": "dev ops: dev_time, dev_pace, dev_skip, dev_teleport, dev_damage, dev_stamp, dev_col, dev_give, dev_creatures, dev_needs, dev_race, dev_luck"}
