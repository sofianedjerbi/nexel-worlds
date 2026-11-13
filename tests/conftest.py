"""The `world` fixture: a fresh simulation on a flat empty deck, with one agent."""

import pytest
from helpers import clear, make


@pytest.fixture
def world(tmp_path):
    sim = make(tmp_path)
    a = sim.login("Ash", "tok")
    clear(sim, a)
    sim.keep_loaded = False                                  # no loading land around you: tests that need it turn it on
    a.hunger, a.sat = 17, 0.0                                # fed, and not healing by itself (18 and more: sim/needs.py): what a blow took stays taken
    yield sim, a
    sim.close()

