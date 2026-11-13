"""People: combat, death, giving, chat, mail, hunger."""

from helpers import run


def test_combat_death_and_drop(world):
    sim, a = world
    b = sim.login("Bryn", "tok2")
    b.x, b.y = a.x + 1, a.y
    b.add("wood", 5)
    a.add("spear", 1)
    b.hp, b.hunger = 4, 10                                   # two hearts left (and not healing)
    r = run(sim, a, "attack", {"target": b.id})              # bare fists: the spear stays in the bag
    assert r["ok"] and r["damage"] == 1 and b.hp == 3 and not r["killed"]     # half a heart
    r = run(sim, a, "attack", {"target": b.id, "with": "spear"})
    assert r["ok"] and r["killed"]
    assert b.deaths == 1 and (b.hp, b.hunger, b.sat) == (20, 20, 5.0) and not b.inventory   # woken whole and fed
    assert sim.items[(a.x + 1, a.y)]["wood"] == 5
    r = run(sim, a, "step", {"dir": "E"})          # walking onto the pile picks it up
    assert r["ok"] and r["changed"]["inventory"]["wood"] == 5 and (a.x, a.y) not in sim.items

def test_give_and_chat_events(world):
    sim, a = world
    b = sim.login("Bryn", "tok2")
    b.x, b.y = a.x + 1, a.y
    a.add("berries", 3)
    assert run(sim, a, "give", {"target": b.id, "item": "berries", "n": 2})["ok"]
    assert b.count("berries") == 2 and a.count("berries") == 1
    sim.observe(b)
    run(sim, a, "say", {"text": "trade?"})
    ev = sim.observe(b)["events"]
    assert any(e["type"] == "say" and e["text"] == "trade?" and e["from"] == "Ash" for e in ev)

def test_mailbox_post_and_open(world):
    sim, a = world
    a.add("mailbox", 1)
    run(sim, a, "place", {"dir": "N", "item": "mailbox"})
    b = sim.login("Pen", "x")
    b.x, b.y = a.x + 1, a.y - 1
    assert run(sim, b, "post", {"dir": "W", "text": "meet me at the lake"})["owner"] == "Ash"
    r = run(sim, a, "open_mail", {"dir": "N"})
    assert r["letters"][0]["text"] == "meet me at the lake" and r["letters"][0]["from"] == "Pen"
    assert run(sim, a, "open_mail", {"dir": "N"})["letters"] == []

def test_starvation_kills(world):
    sim, a = world
    a.hunger = 0
    a.hp = 2
    for _ in range(200):
        sim.step()
    assert a.deaths == 1
