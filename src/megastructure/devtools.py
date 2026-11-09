"""Developer tools for QA (only with --dev): time travel, teleport, items, damage, painting tiles."""

from .sim import DAY_TICKS, TICK_HZ
from .gen import RAMP
from .tiles import BLOCKS, GROUNDS


def dev_op(sim, agent, op: str, msg: dict) -> dict:
    """Run one dev op for `agent`; returns the reply fields."""
    if op == "dev_time":                         # jump to a time of day (0..1, 0.75+ is night)
        day = sim.tick // DAY_TICKS
        sim.tick = day * DAY_TICKS + int(float(msg.get("phase", 0.8)) * DAY_TICKS)
        return {"tick": sim.tick}
    if op == "dev_skip":                         # fast-forward the simulation
        for _ in range(min(int(float(msg.get("seconds", 10)) * TICK_HZ), 20000)):
            sim.step()
        return {"tick": sim.tick}
    if op == "dev_teleport":
        agent.x, agent.y = int(msg["x"]), int(msg["y"])
        return {"x": agent.x, "y": agent.y}
    if op == "dev_damage":
        sim.damage(agent, int(msg.get("n", 10)), "dev")
        return {"hp": agent.hp}
    if op == "dev_stamp":                        # paint ASCII rows of tile chars at x, y (QA builds), on flat land
        bch, gch = {b.char: b.name for b in BLOCKS}, {g.char: g.name for g in GROUNDS}
        x0, y0 = int(msg["x"]), int(msg["y"])
        levels = list(msg.get("levels") or [])  # optional rows of heights: digits, a capital letter for stairs
        for j, row in enumerate(list(msg.get("rows") or [])[:200]):
            for i, ch in enumerate(str(row)[:200]):
                lc = levels[j][i] if j < len(levels) and i < len(levels[j]) else "0"
                lv = ord(lc) - 65 | RAMP if lc.isupper() else int(lc)
                if ch in gch:
                    sim.set_tile(x0 + i, y0 + j, ground=gch[ch], block="none", level=lv)
                elif ch in bch:
                    sim.set_tile(x0 + i, y0 + j, ground="grass", block=bch[ch], level=lv)
        return {}
    if op == "dev_creatures":                    # clear creatures within `clear` tiles; spawn {"kind", "dx", "dy"}
        from .sim import CREATURES, Creature
        r = int(msg.get("clear", 0))
        for cid in [c.id for c in sim.creatures.values() if max(abs(c.x - agent.x), abs(c.y - agent.y)) <= r]:
            del sim.creatures[cid]
        spawned = None
        if msg.get("kind") in CREATURES:
            c = Creature(sim.next_creature, msg["kind"], agent.x + int(msg.get("dx", 1)), agent.y + int(msg.get("dy", 0)),
                         CREATURES[msg["kind"]]["hp"], cooldown=int(msg.get("still", 0)))
            sim.next_creature += 1
            sim.creatures[c.id] = c
            spawned = c.id
        return {"spawned": spawned}
    if op == "dev_needs":                        # set hunger (and hp)
        agent.hunger = max(0, min(100, int(msg.get("hunger", agent.hunger))))
        agent.hp = max(1, min(100, int(msg.get("hp", agent.hp))))
        return {"hunger": agent.hunger, "hp": agent.hp}
    if op == "dev_give":
        for k, n in dict(msg.get("items") or {}).items():
            agent.add(str(k), int(n))
        return {"inventory": agent.inventory}
    return {"ok": False, "error": "unknown_op", "detail": "dev ops: dev_time, dev_skip, dev_teleport, dev_damage, dev_stamp, dev_give, dev_creatures, dev_needs"}
