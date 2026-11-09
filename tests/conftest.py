"""The `world` fixture: a fresh simulation on a flat empty deck, with one agent."""

import pytest
from helpers import clear, make


@pytest.fixture
def world(tmp_path):
    sim = make(tmp_path)
    a = sim.login("Ash", "tok")
    clear(sim, a)
    yield sim, a
    sim.close()

