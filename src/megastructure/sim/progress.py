"""Experience and the item magnet: what you earn by working, and loot that comes to you."""

from .constants import sec
from .entities import Agent

# experience for felling, mining, harvesting, crafting and hunting
XP_DIG = {"tree": 2, "bare_fruit_tree": 2, "stump": 1, "rock": 1, "ore": 4, "ripe_crop": 2}
XP_KILL = {"chicken": 2, "calf": 1, "cow": 4, "tusker": 8, "pincer": 3, "strawman": 10, "wyrm": 20, "mossback": 100, "sporeling": 1}
XP_CRAFT = 1
MAGNET_R = 1                 # items within this many tiles (diagonals too) come to you...
MAGNET_DELAY = sec(1.2)      # ...once they've been on the ground this long (time to land, or to walk off a drop)


def level_of(xp: int) -> tuple[int, int, int]:
    """(level, xp into it, xp it takes): each level needs 3 more than the last, from 7."""
    level, need = 0, 7
    while xp >= need:
        xp -= need
        level += 1
        need = 7 + 3 * level
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
        self.emit("xp", x, y, radius=8, name=a.name, n=n, level=level, up=level > before)

    def attract_items(self):
        """Every other tick: piles next to someone (or under them) that have lain long enough fly into their bag."""
        if self.tick % 2 or not self.items:
            return
        for aid in sorted(self.agents):
            a = self.agents[aid]
            if not a.online or a.hp <= 0:
                continue
            for dy in range(-MAGNET_R, MAGNET_R + 1):
                for dx in range(-MAGNET_R, MAGNET_R + 1):
                    pos = (a.x + dx, a.y + dy)
                    pile = self.items.get(pos)
                    if not pile or self.tick - self.item_since.get(pos, 0) < MAGNET_DELAY:
                        continue
                    got = dict(pile)
                    for k, n in got.items():
                        a.add(k, n)
                    del self.items[pos]
                    self.item_since.pop(pos, None)
                    self.dirty_items.add(pos)
                    self.emit("pick_up", *pos, name=a.name, items=got, magnet=True)
