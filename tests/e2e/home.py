"""Where an HD test plays (test_e2e_hd_sun.py hd): one place of the tests' world, flat dry land, the same for every test
and every run, its meadow laid out again by each test.

A new player wakes round the world's one waking place, a few tiles from where the last one did, by chance. A test that
read the land round it read the world's own land there too: hills 13 tiles south stood in front of the meadow it looked
at (test_e2e_hd_far), a light patch of the meadow was "not green" (test_e2e_hd_land), the land beyond the laid-out
meadow carried the x-ray window on (test_e2e_hd_vanish). One run in eight each, by where the player woke. Here every
tile within FLAT of the place is dry land at level 0 or 1 in the world the tests make (conftest.py: seed 7), checked
with the world's own generator; the test lays the meadow out 12 tiles round it and over all that the tests before it
on this worker's world laid out near it (game.py BUILT), so what they built there is gone; and a test stands on the same tile in every run, its patches and tufts the same: it passes every time or
fails every time. (One place, not one a test: the first trip to a place makes its land, 2 to 4 s.)"""

from megastructure import gen

SEED = 7                   # the tests' world (conftest.py server)
FLAT = 40                  # tiles round the place that are dry land at level 0 or 1
PLACE = (0, -40)           # 40 tiles north of the waking place: its land is near what a new page has made already (a place
                           # 1600 tiles off, its land made again by every test's new page, cost 15 % more on five HD files)


def flat(x, y, r=FLAT) -> bool:
    """Every tile within r of (x, y) is dry land at level 0 or 1 (every other tile looked at)."""
    return all(gen._dry(SEED, x + i, y + j) and gen._land(SEED, x + i, y + j) <= 1
               for j in range(-r, r + 1, 2) for i in range(-r, r + 1, 2))


assert flat(*PLACE), "the tests' world changed: look for another PLACE (home.flat)"
