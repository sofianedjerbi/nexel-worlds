"""Who is in the world: logging in (new or returning), logging out, finding a place to wake up."""

import json
import random
import zlib

from ..tiles import GROUNDS, RACES
from .constants import SHOUT_R
from .entities import ActionError, Agent, _hash_token


def owners_of(db) -> dict[str, int]:
    """account id -> the character it plays here (a world with a door: gate.py; it never holds an email)."""
    db.execute("CREATE TABLE IF NOT EXISTS owners(account TEXT PRIMARY KEY, agent INTEGER UNIQUE)")
    return dict(db.execute("SELECT account, agent FROM owners"))


class Sessions:
    """Simulation mixin: who is in the world: logging in (new or returning), logging out, finding a place to wake up."""

    def login(self, name: str, token: str, persona: str = "", race: str = "") -> Agent:
        name = name.strip()[:24]
        if not name or not name.replace("_", "").replace("-", "").isalnum():
            raise ActionError("bad_name", "name must be 1-24 letters/digits/-/_")
        a = self.by_name.get(name)
        if a is not None and a.id in self.owners.values():   # an account's character: only its ticket wakes it (enter)
            raise ActionError("login_needed", "this character belongs to an account: log in with its email")
        th = _hash_token(token)
        if a is None:
            aid = max(self.agents, default=0) + 1
            x, y = self.find_spawn(aid)
            a = Agent(aid, name, x, y, persona=persona[:200])
            if a.bot:             # the AI players are not all cats: each name has its own race
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
        return self._wake(a, race)

    def _wake(self, a: Agent, race: str) -> Agent:
        if race in RACES:                                # asked for one: that is who you are, new or returning
            a.race = race
        a.online = True
        a.via, a.via_done = [], 0                        # (the screen counts the tiles of its way from 1 again)
        return a

    def enter(self, account: str, name: str, token: str, race: str = "") -> Agent:
        """Through the door with a ticket: an account has one character in a world. The first time, the name it asks
        for becomes its own: a new character, or one from before there were accounts, if this browser still holds
        that character's secret (it is the same person)."""
        aid = self.owners.get(account)
        if aid is None:
            if not name.strip():
                raise ActionError("name_needed", "pick a name")
            a = self.by_name.get(name.strip()[:24])
            if a is not None and a.id in self.owners.values():
                raise ActionError("bad_token", "name is taken")
            a = self.login(name, token, "human", race)
            self.owners[account] = a.id
            self.store.db.execute("INSERT INTO owners VALUES(?,?)", (account, a.id))
            return a
        a = self.agents[aid]
        self.emit("join", a.x, a.y, radius=SHOUT_R, name=a.name, new=False)
        return self._wake(a, race)

    def logout(self, a: Agent):
        if a.action or a.aside:
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
