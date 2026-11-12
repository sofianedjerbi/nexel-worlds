"""Who is in the world: logging in (new or returning), logging out, finding a place to wake up."""

import json
import random
import zlib

from ..tiles import GROUNDS, RACES
from .constants import SHOUT_R
from .entities import ActionError, Agent, _hash_token


class Sessions:
    """Simulation mixin: who is in the world: logging in (new or returning), logging out, finding a place to wake up."""

    def login(self, name: str, token: str, persona: str = "", race: str = "") -> Agent:
        name = name.strip()[:24]
        if not name or not name.replace("_", "").replace("-", "").isalnum():
            raise ActionError("bad_name", "name must be 1-24 letters/digits/-/_")
        a = self.by_name.get(name)
        th = _hash_token(token)
        if a is None:
            aid = max(self.agents, default=0) + 1
            x, y = self.find_spawn(aid)
            a = Agent(aid, name, x, y, persona=persona[:200])
            if persona and persona != "human":             # the AI players are not all cats: each name has its own race
                a.race = RACES[zlib.crc32(name.encode()) % len(RACES)]
            self.agents[aid] = a
            self.by_name[name] = a
            self.tokens[aid] = th
            self.store.db.execute("INSERT INTO agents VALUES(?,?,?,?)", (aid, name, th, json.dumps(a.to_json())))
            self.emit("join", x, y, radius=SHOUT_R, name=name, new=True)
        elif self.tokens[a.id] != th:
            raise ActionError("bad_token", "name is taken and the token does not match")
        else:
            if persona:
                a.persona = persona[:200]
            self.emit("join", a.x, a.y, radius=SHOUT_R, name=name, new=False)
        if race in RACES:                                # asked for one: that is who you are, new or returning
            a.race = race
        a.online = True
        a.via, a.via_done = [], 0                        # (the screen counts the tiles of its way from 1 again)
        return a

    def logout(self, a: Agent):
        if a.action:
            self.interrupt(a, "disconnected")
        a.online = False
        self.emit("leave", a.x, a.y, radius=SHOUT_R, name=a.name)

    def find_spawn(self, salt: int) -> tuple[int, int]:
        r = random.Random(self.seed * 7919 + salt * 104729 + self.tick)
        home = self.store.get_meta("spawn")                  # (a world can say where its newcomers start: showcase.py)
        cx, cy = home or (0, 0)
        for radius in (3, 8, 24) if home else (24, 48, 96, 192):
            for _ in range(200):
                x, y = cx + r.randint(-radius, radius), cy + r.randint(-radius, radius)
                if self.world.passable(x, y) and GROUNDS[self.world.get(x, y)[0]].name in ("dirt", "grass", "bridge"):
                    return x, y
        return cx, cy
