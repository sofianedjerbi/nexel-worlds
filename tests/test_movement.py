"""Walking, sprinting, pathfinding, boats, and acting on the move."""

from helpers import run


def test_step_and_blocked(world):
    sim, a = world
    x, y = a.x, a.y
    assert run(sim, a, "step", {"dir": "E"})["ok"]
    assert (a.x, a.y) == (x + 1, y)
    sim.world.set(a.x + 1, a.y, block="rock")
    r = run(sim, a, "step", {"dir": "E"})
    assert not r["ok"] and r["error"] == "blocked"

def test_move_to_pathfinds_around_wall(world):
    sim, a = world
    for dy in range(-3, 4):
        sim.world.set(a.x + 2, a.y + dy, block="rock")
    gx, gy = a.x + 4, a.y
    r = run(sim, a, "move_to", {"x": gx, "y": gy})
    assert r["ok"] and (a.x, a.y) == (gx, gy) and r["steps"] > 4

def test_sprint_is_faster(world):
    sim, a = world
    def pace(run_):          # ticks for 8 strides back and forth (the cooldown is what limits speed)
        t0 = sim.tick
        for i in range(8):
            run(sim, a, "step", {"dir": "E" if i % 2 else "W", "run": run_})
        return sim.tick - t0
    walk = pace(False)
    assert pace(True) < walk

def test_rapid_taps_keep_their_progress(world):
    """Interrupting a walk with another movement (fast key taps) must not throw the stride away."""
    sim, a = world
    x0 = a.x
    for _ in range(6):
        sim.submit(a, "walk", {"dir": "E"})
        sim.step()
        sim.submit(a, "move_to", {"x": a.x + 1, "y": a.y})
        sim.step()
    assert a.x - x0 >= 5

def test_walk_keeps_going_until_stopped(world):
    sim, a = world
    x0 = a.x
    act = sim.submit(a, "walk", {"dir": "E"})
    for _ in range(20):
        sim.step()
    assert a.x - x0 >= 4 and act.result is None
    sim.submit(a, "stop", {})
    sim.step()
    assert act.result["status"] == "interrupted"
    sim.world.set(a.x + 2, a.y, block="rock")
    r = run(sim, a, "walk", {"dir": "E"})
    assert r["stopped"] == "blocked" and r["steps"] == 1

def test_boats_launch_board_sail_and_moor(world):
    sim, a = world
    for dx in range(1, 6):
        sim.world.set(a.x + dx, a.y, ground="water")
    sim.world.set(a.x + 6, a.y, ground="grass")
    a.add("boat", 1)
    assert run(sim, a, "place", {"dir": "E", "item": "boat"})["ok"] and sim.world.block(a.x + 1, a.y) == "boat"
    x0 = a.x
    assert run(sim, a, "step", {"dir": "E"})["ok"] and a.sailing and sim.world.block(a.x, a.y) == "none"
    run(sim, a, "move_to", {"x": x0 + 6, "y": a.y})
    assert a.x == x0 + 6 and not a.sailing and sim.world.block(x0 + 5, a.y) == "boat"

def test_quick_actions_happen_on_the_move(world):
    sim, a = world
    walk = sim.submit(a, "walk", {"dir": "E"})
    for _ in range(4):
        sim.step()
    sim.world.set(a.x, a.y - 1, block="flower")                         # a flower right beside us now
    pick = sim.submit(a, "dig", {"x": a.x, "y": a.y - 1})
    assert pick.result["ok"] and a.count("flower") == 1 and a.action is walk   # picked instantly, still walking
    sim.world.set(a.x + 1, a.y - 1, block="tree")
    chop = sim.submit(a, "dig", {"x": a.x + 1, "y": a.y - 1})
    assert a.action is chop and walk.result["status"] == "interrupted"  # chopping takes time: it stops the walk
    assert run(sim, a, "dig", {"x": a.x + 5, "y": a.y})["error"] == "out_of_range"

def test_hitting_while_walking(world):
    sim, a = world
    from nexel_worlds.sim import Creature
    walk = sim.submit(a, "walk", {"dir": "E"})
    sim.step()
    hen = Creature(sim.next_creature, "chicken", a.x + 1, a.y - 1, 10); sim.next_creature += 1
    sim.creatures[hen.id] = hen
    hit = sim.submit(a, "attack", {"target": hen.id})
    assert hit.result["ok"] and a.action is walk                       # the punch lands, the walk goes on


def test_you_eat_while_you_walk(world):
    """Eating is done with the hands (constants.ASIDE): it runs beside a walk, which goes on, and beside starting one.
    (It replaced the walk: you stood still for every bite.) Nothing else is done meanwhile: a punch, a dig, another
    bite are refused until it is eaten (they stopped the meal, and a player could chop with his mouth full); talking is."""
    sim, a = world
    a.hunger = 8
    a.add("berries", 3)
    walk = sim.submit(a, "walk", {"dir": "E"})
    for _ in range(3):
        sim.step()
    x = a.x
    eat = sim.submit(a, "eat", {"item": "berries"})
    assert a.action is walk and a.aside is eat                              # both at once
    for _ in range(12):
        sim.step()
    assert eat.result["ok"] and a.hunger == 10 and a.count("berries") == 2   # eaten...
    assert a.action is walk and walk.result is None and a.x >= x + 4       # ...and still walking, at its pace
    eat = sim.submit(a, "eat", {"item": "berries"})                         # the other way round: eating, then setting off
    sim.submit(a, "stop", {})
    sim.step()
    walk = sim.submit(a, "walk", {"dir": "W"})
    assert a.aside is eat and eat.result is None
    for _ in range(12):
        sim.step()
    assert eat.result["ok"] and a.count("berries") == 1 and a.action is walk
    eat = sim.submit(a, "eat", {"item": "berries"})                         # something else for the hands: not while eating
    sim.world.set(a.x - 1, a.y - 1, block="tree")
    for tool, args in (("dig", {"x": a.x - 1, "y": a.y - 1}), ("attack", {"dir": "W"}), ("eat", {"item": "berries"}), ("pick_up", {})):
        no = sim.submit(a, tool, args)
        assert no.result["error"] == "hands_full" and a.aside is eat and eat.result is None, tool
    assert sim.world.block(a.x - 1, a.y - 1) == "tree" and a.action is walk and walk.result is None    # (and the walk goes on)
    said = sim.submit(a, "say", {"text": "mm"})                             # ...talking is, and the meal goes on
    sim.step()
    assert said.result["ok"] and a.aside is eat
    for _ in range(12):
        sim.step()
    assert eat.result["ok"] and a.count("berries") == 0 and a.aside is None
    dig = sim.submit(a, "dig", {"x": a.x - 1, "y": a.y - 1})                # eaten: the hands are free again
    assert dig.result is None or dig.result["error"] != "hands_full"

