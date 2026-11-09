"""Developer tools for QA (only with --dev): time travel, teleport, items, damage, painting tiles."""

from .sim import DAY_TICKS, TICK_HZ
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
    if op == "dev_stamp":                        # paint ASCII rows of tile chars at x, y (QA builds)
        bch, gch = {b.char: b.name for b in BLOCKS}, {g.char: g.name for g in GROUNDS}
        x0, y0 = int(msg["x"]), int(msg["y"])
        for j, row in enumerate(list(msg.get("rows") or [])[:200]):
            for i, ch in enumerate(str(row)[:200]):
                if ch in gch:
                    sim.set_tile(x0 + i, y0 + j, ground=gch[ch], block="none")
                elif ch in bch:
                    sim.set_tile(x0 + i, y0 + j, ground="grass", block=bch[ch])
        return {}
    if op == "dev_give":
        for k, n in dict(msg.get("items") or {}).items():
            agent.add(str(k), int(n))
        return {"inventory": agent.inventory}
    return {"ok": False, "error": "unknown_op", "detail": "dev ops: dev_time, dev_skip, dev_teleport, dev_damage, dev_stamp, dev_give"}
