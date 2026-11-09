"""Simulation timing and tuning constants."""

TICK_HZ = 10


def sec(seconds: float) -> int:
    """Durations are specified in seconds and converted here, so the tick rate never changes game pace."""
    return max(1, round(seconds * TICK_HZ))

DAY_TICKS = sec(600)   # a 10-minute day

STEP = sec(0.2)        # walking speed: 5 tiles per second

VIEW_R = 10

SAY_R = 12

SHOUT_R = 48

EVENT_QUEUE = 60

MAX_TEXT = 200

EAT_SECONDS = 1.6    # eating takes a moment (and can be interrupted)
CAN_SIZE = 12        # waterings per fill

COOP_R = 6           # chickens this close to a coop lay there, twice as often

PICNIC = 1.5         # food is worth more eaten on a picnic blanket

FARM = ("chicken", "cow", "chick", "calf")

CROWD_R = 6                # this many farm animals (CROWD_N) this close: hens stop laying,

CROWD_N = 6                # eggs rot instead of hatching, cows don't breed

FLEE_SECONDS = 4           # a hit farm animal runs from its attacker this long, a tile every FLEE_STRIDE seconds
FLEE_STRIDE = 0.3
ANIMAL_MAX = 80            # and never more than this many farm animals in the world

TROUGH_R = 5               # animals this close to a filled trough feed themselves...

TROUGH_EVERY = 30          # ...about this often (seconds)

CREATURE_ID0 = 1_000_000
