"""The admins' commands (admin.py): each takes the words after its name and returns the line said in the chat.
A wrong word raises CmdError (said as it is) or ValueError/IndexError (the command's usage is said)."""

from dataclasses import dataclass, field

from .sim import CREATURES, DAY_TICKS, Creature
from .sim.constants import FOOD_MAX, HP_MAX
from .tiles import FEED, FOOD, PLACEABLE, RECIPES, WEAPONS
from .wearables import WEAR

MAX_SUMMON, MAX_GIVE, KILL_R = 50, 999, 16
TIMES = {"day": 6, "morning": 6, "noon": 12, "evening": 17, "night": 19, "midnight": 0}   # hours (sim/core.py: 18:00 on is night)


class CmdError(Exception):
    pass


def known_items() -> set[str]:
    out = set(FOOD) | set(FEED) | set(PLACEABLE) | set(WEAPONS) | set(WEAR)
    for r in RECIPES.values():
        out |= set(r.inputs) | set(r.output)
    for c in CREATURES.values():
        out |= {d[0] for d in c["drops"]}
    return out


ITEMS = sorted(known_items())


class Ctx:
    """What a command works with: the admins, the world, who typed it."""

    def __init__(self, admins, me):
        self.admins, self.sim, self.me = admins, admins.sim, me

    @staticmethod
    def choices() -> dict:
        return {"creatures": list(CREATURES), "items": ITEMS, "times": ["set"] + list(TIMES)}

    def player(self, name: str):
        if name in ("@s", "me"):
            return self.me
        a = self.sim.by_name.get(name) or next((a for n, a in self.sim.by_name.items() if n.lower() == name.lower()), None)
        if a is None:
            raise CmdError(f"No player called {name}")
        return a

    def online(self, name: str):
        a = self.player(name)
        if not a.online:
            raise CmdError(f"{a.name} is asleep (not online)")
        return a

    def move(self, a, x: int, y: int, z: int | None = None):
        self.sim.interrupt(a, "moved")                    # (whatever they were doing, walking somewhere: not from here)
        a.x, a.y = x, y
        a.z = z if z is not None else self.sim.world.surfaces(x, y)[-1]      # (the top of the land there)


def _num(w: str) -> bool:
    return w.lstrip("-").isdigit()


def tp(c: Ctx, w):
    if len(w) == 1:                                           # /tp <player>: you to them
        b = c.player(w[0])
        c.move(c.me, b.x, b.y, b.z)
        return f"Teleported to {b.name} ({b.x}, {b.y})"
    if len(w) in (2, 3) and all(map(_num, w)):                # /tp <x> <y> [z]
        c.move(c.me, int(w[0]), int(w[1]), int(w[2]) if len(w) > 2 else None)
        return f"Teleported to {c.me.x}, {c.me.y}"
    if len(w) == 2:                                           # /tp <player> <player>
        a, b = c.player(w[0]), c.player(w[1])
        c.move(a, b.x, b.y, b.z)
        return f"Teleported {a.name} to {b.name}"
    if len(w) in (3, 4) and all(map(_num, w[1:])):            # /tp <player> <x> <y> [z]
        a = c.player(w[0])
        c.move(a, int(w[1]), int(w[2]), int(w[3]) if len(w) > 3 else None)
        return f"Teleported {a.name} to {a.x}, {a.y}"
    raise ValueError


def summon(c: Ctx, w):
    kind = w[0].lower()
    if kind not in CREATURES:
        raise CmdError(f"No creature called {kind} (" + ", ".join(CREATURES) + ")")
    rest = [int(v) for v in w[1:]]
    if len(rest) in (2, 3):
        (x, y), n = rest[:2], rest[2] if len(rest) > 2 else 1
    elif len(rest) <= 1:
        x, y, n = c.me.x + 1, c.me.y, rest[0] if rest else 1
    else:
        raise ValueError
    n, sim, made = max(1, min(MAX_SUMMON, n)), c.sim, 0
    spots = [(x + dx, y + dy) for r in range(8) for dx in range(-r, r + 1) for dy in range(-r, r + 1) if max(abs(dx), abs(dy)) == r]
    for sx, sy in spots:
        if made >= n:
            break
        if not sim.stand(sx, sy):
            continue
        cr = Creature(sim.next_creature, kind, sx, sy, CREATURES[kind]["hp"], z=sim.world.surfaces(sx, sy)[-1], born=sim.tick)
        sim.next_creature += 1
        sim.creatures[cr.id] = cr
        made += 1
    if not made:
        raise CmdError(f"No room for a {kind} at {x}, {y}")
    return f"Summoned {made} {kind} at {x}, {y}"


def give(c: Ctx, w):
    a, item, n = c.player(w[0]), w[1].lower(), int(w[2]) if len(w) > 2 else 1
    if item not in ITEMS:
        raise CmdError(f"No item called {item}")
    n = max(1, min(MAX_GIVE, n))
    a.add(item, n)
    return f"Gave {n} {item} to {a.name}"


def clear(c: Ctx, w):
    a = c.player(w[0]) if w else c.me
    if len(w) > 1:
        n = a.inventory.pop(w[1].lower(), 0)
        return f"Took {n} {w[1].lower()} from {a.name}"
    n = sum(a.inventory.values())
    a.inventory.clear()
    return f"Cleared {a.name}'s inventory ({n} items)"


def kill(c: Ctx, w):
    if w and w[0] == "@e":                                    # /kill @e [creature|all] [r]: the creatures near you
        kind = w[1].lower() if len(w) > 1 else "all"
        r = max(1, min(128, int(w[2]) if len(w) > 2 else KILL_R))
        if kind != "all" and kind not in CREATURES:
            raise CmdError(f"No creature called {kind}")
        gone = [cid for cid, cr in c.sim.creatures.items() if (kind == "all" or cr.kind == kind)
                and max(abs(cr.x - c.me.x), abs(cr.y - c.me.y)) <= r]
        for cid in gone:
            del c.sim.creatures[cid]
        return f"Removed {len(gone)} {'creatures' if kind == 'all' else kind} within {r} tiles"
    a = c.player(w[0]) if w else c.me
    c.sim.kill_agent(a, "admin", None)
    return f"Killed {a.name}"


def time_(c: Ctx, w):
    if len(w) != 2 or w[0] != "set":
        raise ValueError
    h = TIMES.get(w[1].lower())
    h = float(w[1]) if h is None else h
    if not 0 <= h <= 24:
        raise ValueError
    sim = c.sim                                               # forward only (devtools.py dev_time: the clock going back
    t = sim.tick // DAY_TICKS * DAY_TICKS + int(h % 24 / 24 * DAY_TICKS)   # left everyone's cooldowns in the future)
    sim.tick = t if t >= sim.tick else t + DAY_TICKS
    sim.world.tick = sim.tick
    return f"Time set to {sim.clock()}"


def heal(c: Ctx, w):
    a = c.player(w[0]) if w else c.me
    a.hp = HP_MAX
    return f"Healed {a.name}"


def feed(c: Ctx, w):
    a = c.player(w[0]) if w else c.me
    a.hunger = FOOD_MAX
    return f"Fed {a.name}"


def kick(c: Ctx, w):
    a = c.online(w[0])
    c.admins.kick(a, "Kicked by an admin")
    return f"Kicked {a.name}"


def ban(c: Ctx, w):
    a = c.player(w[0])
    if a is c.me:
        raise CmdError("You can't ban yourself")
    c.admins.banned.add(a.name)
    c.admins.save()
    c.admins.kick(a, "Banned by an admin")
    return f"Banned {a.name}"


def unban(c: Ctx, w):
    if w[0] not in c.admins.banned:
        raise CmdError(f"{w[0]} is not banned")
    c.admins.banned.discard(w[0])
    c.admins.save()
    return f"Unbanned {w[0]}"


def setspawn(c: Ctx, w):
    x, y = (int(w[0]), int(w[1])) if len(w) >= 2 else (c.me.x, c.me.y)
    c.sim.store.set_meta("spawn", [x, y])                    # (where newcomers wake: sessions.py find_spawn)
    return f"Spawn set to {x}, {y}"


def spawn(c: Ctx, w):
    x, y = c.sim.find_spawn(c.me.id)
    c.move(c.me, x, y)
    return f"Teleported to spawn ({x}, {y})"


def list_(c: Ctx, w):
    up = sorted(a.name for a in c.sim.agents.values() if a.online)
    return f"{len(up)} online: " + ", ".join(up)


def help_(c: Ctx, w):
    mine = c.admins.is_admin(c.me)
    return "\n".join(f"**{cm.usage}** {cm.desc}" for cm in COMMANDS.values() if mine or not cm.admin)


def save(c: Ctx, w):
    c.sim.flush()
    c.sim.store.commit()
    return f"Saved the world (tick {c.sim.tick})"


def say(c: Ctx, w):
    text = " ".join(w).strip()[:200]
    if not text:
        raise ValueError
    c.sim.emit("shout", c.me.x, c.me.y, radius=1 << 20, **{"from": f"[{c.me.name}]"}, text=text)
    return "Said to everyone"


@dataclass
class Cmd:
    usage: str
    desc: str
    fn: object
    admin: bool = True
    args: tuple = field(default_factory=tuple)               # what each word can be, for the page's list: player, creature, item, time


COMMANDS = {
    "help": Cmd("/help", "what you can use", help_, False),
    "list": Cmd("/list", "who is online", list_, False),
    "tp": Cmd("/tp <player> | <x> <y> [z] | <player> <player>", "teleport", tp, args=("player", "player")),
    "summon": Cmd("/summon <creature> [x y] [n]", "bring creatures", summon, args=("creature",)),
    "give": Cmd("/give <player> <item> [n]", "give items", give, args=("player", "item")),
    "clear": Cmd("/clear <player> [item]", "empty an inventory", clear, args=("player", "item")),
    "kill": Cmd("/kill <player> | @e [creature] [r]", "kill a player, or remove creatures near you", kill, args=("player|@e", "creature")),
    "time": Cmd("/time set <day|noon|night|0-24>", "set the hour (forward)", time_, args=("set", "time")),
    "heal": Cmd("/heal <player>", "full health", heal, args=("player",)),
    "feed": Cmd("/feed <player>", "full food", feed, args=("player",)),
    "kick": Cmd("/kick <player>", "disconnect a player", kick, args=("player",)),
    "ban": Cmd("/ban <player>", "keep a player out", ban, args=("player",)),
    "unban": Cmd("/unban <player>", "let a player back in", unban, args=("player",)),
    "setspawn": Cmd("/setspawn [x y]", "where newcomers wake (here)", setspawn),
    "spawn": Cmd("/spawn", "teleport to spawn", spawn),
    "op": Cmd("/op <player>", "make an admin", lambda c, w: c.admins.op(c.player(w[0]).name), args=("player",)),
    "deop": Cmd("/deop <player>", "no longer an admin", lambda c, w: c.admins.deop(w[0]), args=("player",)),
    "seed": Cmd("/seed", "the world's seed", lambda c, w: f"Seed: {c.sim.seed}"),
    "save": Cmd("/save", "save the world now", save),
    "say": Cmd("/say <text>", "say to everyone", say),
}
