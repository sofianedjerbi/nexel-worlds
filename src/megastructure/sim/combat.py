"""Fighting, damage, death and respawn."""

from .. import tiles as T
from ..tiles import DIRS
from .constants import SHOUT_R
from .entities import CREATURES, ActionError, Agent, Creature


class Combat:
    """Simulation mixin: fighting, damage, death and respawn."""

    @staticmethod

    def held(a: Agent, args) -> str | None:
        """The item the action is done with (`with`), if the agent carries it; None means bare hands."""
        item = args.get("with")
        return item if item and a.count(item) else None

    def best_weapon(self, a: Agent):
        best = max((w for w in T.WEAPONS if a.count(w)), key=lambda w: T.WEAPONS[w], default=None)
        return best

    def _find_target(self, tid):
        try:
            tid = int(tid)
        except (TypeError, ValueError):
            raise ActionError("bad_args", "target must be an entity id")
        t = self.agents.get(tid) or self.creatures.get(tid)
        if t is None or (isinstance(t, Agent) and not t.online):
            raise ActionError("no_target", f"no entity {tid} here")
        return t

    def _tool_attack(self, a, args):
        t = self._find_target(args.get("target"))
        if t is a:
            raise ActionError("bad_target", "you cannot attack yourself")
        weapon = self.held(a, args)
        reach = T.REACH.get(weapon, T.REACH[None])
        if max(abs(t.x - a.x), abs(t.y - a.y)) > reach:
            raise ActionError("out_of_range", f"target must be within {reach} tiles (including diagonals)")
        yield from self.wait(a, 0.4)
        if max(abs(t.x - a.x), abs(t.y - a.y)) > reach or t.hp <= 0:
            raise ActionError("missed", "target moved away")
        dmg = T.WEAPONS.get(weapon, T.FIST_DAMAGE)
        self.spend(a, 2)
        name = t.name if isinstance(t, Agent) else f"{t.kind}#{t.id}"
        self.emit("attack", a.x, a.y, attacker=a.name, target=name, damage=dmg, weapon=weapon or "fists")
        a.bump("attacks")
        if isinstance(t, Creature):
            t.cooldown = 0
        before = t.deaths if isinstance(t, Agent) else 0
        self.damage(t, dmg, f"killed by {a.name}", by=a)
        killed = t.deaths > before if isinstance(t, Agent) else t.id not in self.creatures
        return {"target": name, "damage": dmg, "target_hp": 0 if killed else t.hp, "killed": killed}

    def damage(self, target, n: int, cause: str, by: Agent | None = None):
        target.hp -= n
        if target.hp <= 0:
            if isinstance(target, Agent):
                self.kill_agent(target, cause, by)
            else:
                self.kill_creature(target, by)

    def kill_agent(self, a: Agent, cause: str, by: Agent | None):
        self.add_items(a.x, a.y, dict(a.inventory))
        dropped = dict(a.inventory)
        a.inventory.clear()
        a.deaths += 1
        self.stats["deaths"] += 1
        if by:
            by.bump("kills")
        self.emit("death", a.x, a.y, radius=SHOUT_R, name=a.name, cause=cause, by=by.name if by else None,
                  dropped=dropped)
        if a.action:
            self.interrupt(a, "you died")
        if a.sailing:
            self.world.set(a.x, a.y, block="boat")
            a.sailing = False
        bed = a.spawn
        if bed and self.world.block(*bed) == "bed":
            spots = [(bed[0] + dx, bed[1] + dy) for dx, dy in DIRS.values() if self.world.passable(bed[0] + dx, bed[1] + dy)]
            a.x, a.y = spots[0] if spots else self.find_spawn(a.id * 31 + a.deaths)
        else:
            a.spawn = None
            a.x, a.y = self.find_spawn(a.id * 31 + a.deaths)
        a.hp, a.hunger, a.energy = 100, 70, 80
        a.events.append({"tick": self.tick, "type": "respawn", "cause": cause,
                         "by": by.name if by else None, "x": a.x, "y": a.y})

    def kill_creature(self, c: Creature, by: Agent | None):
        self.creatures.pop(c.id, None)
        self.add_items(c.x, c.y, CREATURES[c.kind]["drops"])
        if by:
            by.bump(f"killed_{c.kind}")
        self.emit("creature_died", c.x, c.y, kind=c.kind, id=c.id, by=by.name if by else None)
