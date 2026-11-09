"""The `world` fixture: a fresh simulation on a flat empty deck, with one agent."""

import pytest
from helpers import clear, make


@pytest.fixture
def world(tmp_path):
    sim = make(tmp_path)
    a = sim.login("Ash", "tok")
    clear(sim, a)
    sim.keep_loaded = False                                  # no loading land around you: tests that need it turn it on
    yield sim, a
    sim.close()

