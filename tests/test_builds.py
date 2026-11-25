"""What a build is and what it holds (sim/builds.py): facts for the shelter rule, the AI player's judge and a screen."""

from nexel_worlds.sim import builds


def ring(sim, x, y, w=4, h=4, piece="wood_wall", door=None):
    """Walls round the w x h inside whose top-left tile is (x, y); a door at `door` (x, y) in the wall."""
    for dx in range(-1, w + 1):
        for dy in range(-1, h + 1):
            if dx in (-1, w) or dy in (-1, h):
                sim.world.set(x + dx, y + dy, block="door" if (x + dx, y + dy) == door else piece)


def test_open_land_is_no_build(world):
    sim, a = world
    assert builds.report(sim.world, a.x, a.y) == {"closed": False}


def test_a_closed_room_with_its_door_walls_and_things(world):
    sim, a = world
    x, y = a.x - 1, a.y - 1
    ring(sim, x, y, door=(x + 1, y - 1))
    sim.world.set(x + 3, y + 3, block="bed")
    sim.world.set(x, y + 3, block="campfire")
    r = builds.report(sim.world, a.x, a.y)
    assert r["closed"] and r["area"] == 16 and r["box"] == (4, 4)
    assert r["doors"] == 1 and r["walls"] == {"wood_wall": 15}
    assert r["contents"] == {"bed": 1, "campfire": 1} and r["lights"] >= 1
    assert r["roofed"] == 0.0


def test_a_gap_opens_it_and_the_shelter_rule_agrees(world):
    sim, a = world
    x, y = a.x - 1, a.y - 1
    ring(sim, x, y, w=5, h=5)
    assert builds.report(sim.world, a.x, a.y)["closed"] and sim.sheltered(a.x + 1, a.y + 1)
    sim.world.set(x + 2, y - 1, block="none")
    assert builds.report(sim.world, a.x, a.y) == {"closed": False}
    assert not sim.sheltered(a.x + 1, a.y + 1)


def test_a_long_hall_is_not_a_room(world):
    sim, a = world
    ring(sim, a.x, a.y, w=20, h=2)
    assert builds.report(sim.world, a.x, a.y) == {"closed": False}
