"""Experience and the item magnet: what you earn by working, and loot that comes to you."""

from ..tiles import REACH
from .constants import sec
from .entities import Agent

# experience for mining ore, crafting and hunting. Taking a block gives none, but for ore (as the sandbox classic has
# it: it was 2 for a tree, 1 for a rock or a stump, 2 for a ripe crop, 1 or 2 for digging down)
XP_DIG = {"ore": 4}
XP_KILL = {"chicken": 2, "calf": 1, "cow": 4, "tusker": 8, "pincer": 3, "strawman": 10, "wyrm": 20, "mossback": 100, "sporeling": 1}
XP_CRAFT = 1
MAGNET_R = REACH["magnet"]   # items within this reach (Movement.near: a circle, height counted) come to you...
LEVEL = (7, 3)               # the experience the first level takes, and how much more each one after it
MAGNET_DELAY = sec(1.2)      # ...once they've been on the ground this long (time to land, or to walk off a drop)


def level_of(xp: int) -> tuple[int, int, int]:
    """(level, xp into it, xp it takes): each level needs 3 more than the last, from 7."""
    level, need = 0, LEVEL[0]
    while xp >= need:
        xp -= need
        level += 1
        need = LEVEL[0] + LEVEL[1] * level
    return level, xp, need


class Progress:
    """Simulation mixin: experience, and ground items drawn to people standing next to them."""

    def gain_xp(self, a: Agent, n: int, x: int, y: int):
        """Experience earned at (x, y): the orbs fly from there (the client draws them)."""
        if n <= 0:
            return
        before = level_of(a.xp)[0]
        a.xp += n
        level = level_of(a.xp)[0]
        self.emit("xp", x, y, name=a.name, n=n, level=level, up=level > before)

    def attract_items(self):
        """Every other tick: piles next to someone (or under them) that have lain long enough fly into their bag."""
        if self.tick % 2 or not self.items:
            return
        for pos, aid in list(self.item_left.items()):       # what someone dropped is theirs to leave: it comes back to
            a = self.agents.get(aid)                         # them by itself once they have stepped away and come back
            if pos not in self.items or a is None or not a.online or not self.near(a, *pos, MAGNET_R):
                del self.item_left[pos]
        for aid in sorted(self.agents):
            a = self.agents[aid]
            if not a.online or a.hp <= 0:
                continue
            for dy in range(-MAGNET_R, MAGNET_R + 1):
                for dx in range(-MAGNET_R, MAGNET_R + 1):
                    pos = (a.x + dx, a.y + dy)
                    pile = self.items.get(pos)
                    if pile and self.tick - self.item_since.get(pos, 0) >= MAGNET_DELAY and self.near(a, *pos, MAGNET_R):
                        self.take_pile(a, pos, magnet=True)  # (not just dropped, nor out of reach: up on a ledge, down a drop; nor let go of by them, there: Items.take_pile)
