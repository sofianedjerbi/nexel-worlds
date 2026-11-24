"""Authoritative, deterministic tick simulation (see core.Simulation).

The simulation is split by domain into mixins; this package re-exports the public names.
"""

from .constants import (
    CAN_SIZE,
    COOP_R,
    CREATURE_ID0,
    CROWD_N,
    CROWD_R,
    DAY_TICKS,
    EVENT_QUEUE,
    FARM,
    MAX_TEXT,
    PICNIC,
    SAY_R,
    SHOUT_R,
    STEP,
    TICK_HZ,
    TROUGH_EVERY,
    TROUGH_R,
    VIEW_R,
    sec,
)
from .core import Simulation
from .entities import CREATURES, Action, ActionError, Agent, Creature
from .specs import DIR_ARG, LEGEND, TOOL_SPECS

__all__ = ["Action", "ActionError", "Agent", "CAN_SIZE", "COOP_R", "CREATURES", "CREATURE_ID0", "CROWD_N", "CROWD_R", "Creature", "DAY_TICKS", "DIR_ARG", "EVENT_QUEUE", "FARM", "LEGEND", "MAX_TEXT", "PICNIC", "SAY_R", "SHOUT_R", "STEP", "TICK_HZ", "TOOL_SPECS", "TROUGH_EVERY", "TROUGH_R", "VIEW_R", "sec", "Simulation"]
