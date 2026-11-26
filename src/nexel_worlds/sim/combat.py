"""Fighting, damage, death and respawn."""

from .. import tiles as T
from ..tiles import DIRS
from .constants import ATTACK_COOLDOWN, FARM, FLEE_SECONDS, FOOD_MAX, HP_MAX, SAT_START, sec
from .entities import CREATURES, ActionError, Agent, Creature, ref, roll_drops
from .progress import XP_KILL


# A death's cause is a code (#6), its words for people made from it here alone: the `cause` the agents read till they read
# `code` (nexel-agent), as they were
CAUSES = {"killed": "killed by {who}", "burnt": "burnt by a hob", "bitten": "{kind}", "fell": "fell", "starvation": "starvation",
          "fire": "fire", "admin": "admin", "dev": "dev"}


def cause_text(code: str, who: dict | None) -> str:
    return CAUSES[code].format(who=(who or {}).get("name") or "", kind=(who or {}).get("kind") or "")


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
            raise ActionError("bad_target", "you cannot attack yourself", why="self")
        if isinstance(t, Creature) and CREATURES[t.kind].get("untouchable"):
            raise ActionError("bad_target", "your hand goes through it", why="untouchable")
        weapon = self.held(a, args)
        reaches = lambda: self.within(a, "melee", t.x, t.y, self.height(t), weapon, getattr(t, "kind", None))
        if not reaches():
            raise ActionError("out_of_range", "target is out of reach, height counted (a layer is half a tile)", why="far")
        # the hit lands at once, then the arm needs ATTACK_COOLDOWN before the next swing: a ready swing takes no
        # time, so you can fight while walking; one sent too soon waits for the cooldown, or on the move is dropped
        if self.tick < a.swing_ready and getattr(self, "passing", None) is a:
            raise ActionError("too_soon", "your arm is still swinging")
        while self.tick < a.swing_ready:
            yield
        if not reaches() or t.hp <= 0:
            raise ActionError("missed", "target moved away")
        a.swing_ready = self.tick + sec(ATTACK_COOLDOWN)
        dmg = T.WEAPONS.get(weapon, T.FIST_DAMAGE)                 # (in half hearts, from a creature or a person alike)
        dmg = self.shell(t, dmg) if isinstance(t, Creature) else self.guarded(t, dmg)     # Old Mossback's shell (boss.py), or armor (wear.py)
        if isinstance(t, Creature) and t.kind == "gustling":
            dmg = self.gust_struck(t, a, dmg)                        # spinning up, it scatters; otherwise it runs (wild.py)
        self.tire(a, "attack")
        name = t.name if isinstance(t, Agent) else f"{t.kind}#{t.id}"
        self.emit("attack", a.x, a.y, attacker=a.name, target=name, who=ref(a), whom=ref(t), damage=dmg, weapon=weapon or "fists")
        a.bump("attacks")
        if isinstance(t, Creature):
            t.cooldown = 0
            if t.kind in FARM:                      # farm animals don't stand there and take it: they run
                t.scared, t.threat = self.tick + sec(FLEE_SECONDS), (a.x, a.y)
            elif t.kind == "tusker":                # ...and a tusker takes it badly (wild.py)
                self.enrage(t, a)
        before = t.deaths if isinstance(t, Agent) else 0
        self.damage(t, dmg, "killed", by=a)
        killed = t.deaths > before if isinstance(t, Agent) else t.id not in self.creatures
        return {"target": name, "damage": dmg, "target_hp": 0 if killed else t.hp, "killed": killed}

    def damage(self, target, n: float, code: str, by: Agent | None = None, who=None):
        """`code`: of CAUSES; `by`: the person it is put down to (a kill, a hob's owner); `who`: what did it, `by` if not said."""
        target.hp -= n
        if isinstance(target, Agent):
            self.tire(target, "hurt")
        if target.hp <= 0:
            if isinstance(target, Agent):
                self.kill_agent(target, code, by, who or by)
            else:
                self.kill_creature(target, by)

    def kill_agent(self, a: Agent, code: str, by: Agent | None, who=None):
        who = ref(who) if who is not None else None
        cause = cause_text(code, who)
        for item in a.worn.values():             # what you wore falls with the rest
            a.add(item)
        a.worn = {}
        self.add_items(a.x, a.y, dict(a.inventory))
        dropped = dict(a.inventory)
        a.inventory.clear()
        a.deaths += 1
        self.stats["deaths"] += 1
        if by:
            by.bump("kills")
        self.emit("death", a.x, a.y, name=a.name, code=code, who=who, cause=cause, by=by.name if by else None,
                  dropped=dropped)
        if a.action or a.aside:
            self.interrupt(a, "you died")
        if a.sailing:
            self.world.set(a.x, a.y, block="boat")
            a.sailing = False
        bed = a.spawn
        if bed and len(bed) > 2 and self.thing(*bed) == "bed":        # a bed upstairs: beside it, on its floor
            spots = [(bed[0] + dx, bed[1] + dy) for dx, dy in DIRS.values() if self.thing(bed[0] + dx, bed[1] + dy, bed[2]) == "none"
                     and bed[2] in self.world.surfaces(bed[0] + dx, bed[1] + dy)] or [tuple(bed[:2])]
            a.x, a.y, a.z = *spots[0], bed[2]
        elif bed and self.world.block(*bed[:2]) == "bed":
            spots = [(bed[0] + dx, bed[1] + dy) for dx, dy in DIRS.values() if self.stand(bed[0] + dx, bed[1] + dy)]
            a.x, a.y = spots[0] if spots else self.find_spawn(a.id * 31 + a.deaths)
        else:
            a.spawn = None
            a.x, a.y = self.find_spawn(a.id * 31 + a.deaths)
        a.hp, a.hunger, a.sat, a.tired = HP_MAX, FOOD_MAX, SAT_START, 0.0
        a.events.append({"tick": self.tick, "type": "respawn", "code": code, "who": who, "cause": cause,
                         "by": by.name if by else None, "x": a.x, "y": a.y})

    def kill_creature(self, c: Creature, by: Agent | None):
        self.creatures.pop(c.id, None)
        drops = roll_drops(c.kind, self.rng, self.luck)      # (not the same thing every time: entities.py)
        for item, n in c.loot.items():                       # and what it carried (a gustling's snatches: wild.py)
            drops[item] = drops.get(item, 0) + n
        self.add_items(c.x, c.y, drops)
        if by:
            by.bump(f"killed_{c.kind}")
            self.gain_xp(by, XP_KILL.get(c.kind, 0), c.x, c.y)
        self.emit("creature_died", c.x, c.y, kind=c.kind, id=c.id, by=by.name if by else None, drops=drops)
