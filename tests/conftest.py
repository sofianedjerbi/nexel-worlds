"""The `world` fixture: a fresh simulation on a flat empty deck, with one agent."""

import pytest
from helpers import clear, make


def pytest_terminal_summary(terminalreporter):
    """Which tests needed their second try (the browser's: tests/e2e/conftest.py), and what the first one said: a test
    that is often here is not sound. (Here, not there: the one that reports loads this file whatever is asked for.)"""
    again = terminalreporter.stats.get("rerun", [])
    if again:
        terminalreporter.section("tried a second time")
        for r in again:
            said = [ln for ln in str(r.longrepr).splitlines() if ln.startswith("E ")]
            terminalreporter.line(f"{r.nodeid}: {(said[0][1:].strip() if said else str(r.longrepr).strip().splitlines()[-1])[:170]}")


@pytest.fixture
def world(tmp_path):
    sim = make(tmp_path)
    a = sim.login("Ash", "tok")
    clear(sim, a)
    sim.keep_loaded = False                                  # no loading land around you: tests that need it turn it on
    a.hunger, a.sat = 17, 0.0                                # fed, and not healing by itself (18 and more: sim/needs.py): what a blow took stays taken
    yield sim, a
    sim.close()

