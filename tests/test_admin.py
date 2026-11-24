"""Admins (admin.py): an operator role outside the world. Who may be one, that it is kept, and what each command does."""

import asyncio
import json

import pytest

from nexel_worlds.sim import DAY_TICKS
from nexel_worlds.sim.constants import FOOD_MAX, HP_MAX


@pytest.fixture
def gs(tmp_path):
    from nexel_worlds.server import GameServer
    s = GameServer(tmp_path / "w", seed=3, admins=["Boss"])
    yield s
    s.sim.close()


def players(gs):
    boss, joe, bot = gs.sim.login("Boss", "t", "human"), gs.sim.login("Joe", "t", "human"), gs.sim.login("Robo", "t", "builder")
    return boss, joe, bot


def test_nobody_but_the_names_given_is_an_admin_and_a_player_is_refused(gs):
    boss, joe, bot = players(gs)
    assert gs.admin.is_admin(boss) and not gs.admin.is_admin(joe) and not gs.admin.is_admin(bot)
    for line in ("/tp 0 0", "/give Joe wood 5", "/time set night", "/op Joe", "/kick Boss", "/summon cow"):
        r = gs.admin.run(joe, line)
        assert r == {"ok": False, "text": "You can't do that"}, line
    assert joe.count("wood") == 0 and "Joe" not in gs.admin.names
    assert gs.admin.run(joe, "/list")["ok"] and "Boss" in gs.admin.run(joe, "/list")["text"]   # (anyone: /list, /help)
    h = gs.admin.run(joe, "/help")["text"]
    assert "/list" in h and "/tp" not in h
    assert "/tp" in gs.admin.run(boss, "/help")["text"]
    assert [c["name"] for c in gs.admin.cmds(joe)["cmds"]] == ["help", "list"]


def test_an_ai_player_can_never_be_an_admin(gs, tmp_path):
    boss, joe, bot = players(gs)
    r = gs.admin.run(boss, "/op Robo")
    assert not r["ok"] and "AI" in r["text"] and not gs.admin.is_admin(bot)
    gs.admin.names.add("Robo")                               # (even a list that names it: an AI player is no admin)
    assert not gs.admin.is_admin(bot) and gs.admin.run(bot, "/tp 0 0")["text"] == "You can't do that"


def test_op_and_deop_are_kept_across_a_restart(tmp_path):
    from nexel_worlds.server import GameServer
    (tmp_path / "w").mkdir()
    (tmp_path / "w" / "admins.txt").write_text("# admins\nFileAdmin\n")
    gs = GameServer(tmp_path / "w", seed=3, admins=["Boss"])
    boss, joe, _ = players(gs)
    gs.sim.login("FileAdmin", "t", "human")
    assert gs.admin.run(boss, "/op Joe")["ok"] and gs.admin.is_admin(joe)
    assert gs.admin.run(boss, "/deop FileAdmin")["ok"]
    gs.sim.close()
    gs = GameServer(tmp_path / "w", seed=3)                  # (no --admin this time)
    names = gs.admin.names
    assert "Joe" in names and "Boss" in names and "FileAdmin" not in names     # (deop takes it out of the file too)
    assert gs.admin.run(gs.sim.login("Joe", "t", "human"), "/deop Joe")["ok"]
    gs.sim.close()
    gs = GameServer(tmp_path / "w", seed=3)
    assert "Joe" not in gs.admin.names
    gs.sim.close()


def test_tp_moves(gs):
    boss, joe, _ = players(gs)
    assert gs.admin.run(boss, "/tp 40 -12")["ok"] and (boss.x, boss.y) == (40, -12)
    assert gs.admin.run(boss, "/tp 41 -12 5")["ok"] and (boss.x, boss.y, boss.z) == (41, -12, 5)
    assert gs.admin.run(boss, "/tp Joe")["ok"] and (boss.x, boss.y) == (joe.x, joe.y)
    assert gs.admin.run(boss, "/tp Joe 7 8")["ok"] and (joe.x, joe.y) == (7, 8)
    gs.admin.run(boss, "/tp 0 0")
    assert gs.admin.run(boss, "/tp Joe Boss")["ok"] and (joe.x, joe.y) == (boss.x, boss.y)
    assert not gs.admin.run(boss, "/tp Nobody")["ok"]
    assert gs.admin.run(boss, "/tp")["text"].startswith("Usage")


def test_summon_spawns(gs):
    boss, _, _ = players(gs)
    before = sum(c.kind == "cow" for c in gs.sim.creatures.values())
    r = gs.admin.run(boss, "/summon cow 3")
    assert r["ok"], r
    assert sum(c.kind == "cow" for c in gs.sim.creatures.values()) == before + 3
    assert not gs.admin.run(boss, "/summon dragon")["ok"]


def test_give_clear_heal_feed_kill(gs):
    boss, joe, _ = players(gs)
    assert gs.admin.run(boss, "/give Joe wood 5")["ok"] and joe.count("wood") == 5
    assert not gs.admin.run(boss, "/give Joe unobtainium")["ok"]
    gs.admin.run(boss, "/give Joe stone 2")
    assert gs.admin.run(boss, "/clear Joe wood")["ok"] and joe.count("wood") == 0 and joe.count("stone") == 2
    assert gs.admin.run(boss, "/clear Joe")["ok"] and joe.inventory == {}
    joe.hp, joe.hunger = 3, 2
    assert gs.admin.run(boss, "/heal Joe")["ok"] and joe.hp == HP_MAX
    assert gs.admin.run(boss, "/feed Joe")["ok"] and joe.hunger == FOOD_MAX
    d = joe.deaths
    assert gs.admin.run(boss, "/kill Joe")["ok"] and joe.deaths == d + 1
    gs.admin.run(boss, "/summon chicken 2")
    assert gs.admin.run(boss, "/kill @e chicken")["ok"]
    assert not any(c.kind == "chicken" and abs(c.x - boss.x) <= 16 and abs(c.y - boss.y) <= 16 for c in gs.sim.creatures.values())


def test_time_changes_forward(gs):
    boss, _, _ = players(gs)
    t0 = gs.sim.tick
    assert gs.admin.run(boss, "/time set night")["ok"] and gs.sim.is_night() and gs.sim.tick >= t0
    assert gs.admin.run(boss, "/time set 12")["ok"] and gs.sim.tick % DAY_TICKS == DAY_TICKS // 2
    assert not gs.admin.run(boss, "/time set 30")["ok"]


def test_kick_disconnects_and_ban_blocks_join(gs):
    boss, joe, _ = players(gs)

    class Ws:
        closed = None

        async def close(self, code, why):
            self.closed = (code, why)

    async def go():
        ws = gs.conns[joe.id] = Ws()
        assert gs.admin.run(boss, "/kick Joe")["ok"]
        await asyncio.sleep(0)
        assert ws.closed == (4001, "Kicked by an admin")
        ws.closed = None
        assert gs.admin.run(boss, "/ban Joe")["ok"]
        await asyncio.sleep(0)
        assert ws.closed and "Banned" in ws.closed[1]
    asyncio.run(go())
    assert gs.admin.refuse(gs.sim.login("Joe", "t", "human")) and not joe.online      # (at the door: sent away)
    assert not gs.admin.refuse(boss)
    assert gs.admin.run(boss, "/unban Joe")["ok"] and not gs.admin.refuse(gs.sim.login("Joe", "t", "human"))


def test_spawn_seed_save_say_and_every_command_is_logged(gs, tmp_path):
    boss, joe, _ = players(gs)
    assert gs.admin.run(boss, "/setspawn 5 6")["ok"] and gs.sim.store.get_meta("spawn") == [5, 6]
    gs.admin.run(boss, "/tp 90 90")
    assert gs.admin.run(boss, "/spawn")["ok"] and abs(boss.x - 5) <= 24 and abs(boss.y - 6) <= 24
    assert gs.admin.run(boss, "/seed")["text"] == "Seed: 3"
    assert gs.admin.run(boss, "/save")["ok"]
    joe.x, joe.y = 5000, 5000
    assert gs.admin.run(boss, "/say hello all")["ok"]
    assert any(e.get("type") == "shout" and e.get("text") == "hello all" for e in joe.events)   # (everywhere)
    gs.admin.run(joe, "/tp 0 0")
    lines = [json.loads(ln) for ln in (tmp_path / "w" / "events.jsonl").read_text().splitlines()]
    admin = [e for e in lines if e["type"] == "admin"]
    assert [e["cmd"] for e in admin] == ["/setspawn 5 6", "/tp 90 90", "/spawn", "/seed", "/save", "/say hello all", "/tp 0 0"]
    assert admin[-1]["by"] == "Joe" and admin[-1]["ok"] is False                            # (a refused one too)


def test_the_tab_list_says_who_is_an_admin(gs):
    boss, joe, _ = players(gs)

    class Ws:
        request = type("R", (), {"path": "/spectate", "headers": {}})()
        sent = []

        async def send(self, m):
            self.sent.append(json.loads(m))

        def __aiter__(self):
            async def it():
                yield json.dumps({"op": "agents", "id": 1})
            return it()

    ws = Ws()
    asyncio.run(gs.spectate(ws))
    got = {a["name"]: a.get("admin", False) for a in next(m for m in ws.sent if m.get("id") == 1)["agents"]}
    assert got == {"Boss": True, "Joe": False, "Robo": False}
