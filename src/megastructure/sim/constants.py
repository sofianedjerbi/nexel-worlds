"""Simulation timing and tuning constants."""

TICK_HZ = 10


def sec(seconds: float) -> int:
    """Durations are specified in seconds and converted here, so the tick rate never changes game pace."""
    return max(1, round(seconds * TICK_HZ))

DAY_TICKS = sec(600)   # a 10-minute day

STEP = sec(0.2)        # walking speed: 5 tiles per second
SLOPE_UP, SLOPE_DOWN = 0.6, 0.2   # a step up a slope takes 60% longer, down it 20% (client: render.js)
FALL_SAFE, FALL_HP = 3, 5         # a fall of up to 3 layers is nothing; each layer more costs half a heart

VIEW_R = 10

SAY_R = 12

SHOUT_R = 48

EVENT_QUEUE = 60

MAX_TEXT = 200

TARGET_R = 3         # actions aimed at x, y: tiles.USE_R plus one, to absorb a walking client's lead
LAYER = 0.5          # a layer of height is half a tile: in what you can reach, height is distance too (Movement.near)
ASIDE = ("eat",)     # done with the hands: whatever the feet are doing goes on (Agent.aside)
MOVES = ("walk", "move_to", "step", "stop")   # movement (stop: walking to where the player's screen stopped): quick actions happen alongside it instead of stopping it
VIA_FAR, VIA_MAX = 8, 8               # a tile a screen walked to: how far it may be from the last, and how many are kept (Movement.follow)
ATTACK_COOLDOWN = 0.4    # seconds between two swings
EAT_SECONDS = 0.9    # eating takes a moment (three bites; walking on doesn't stop it, doing something else does)
CAN_SIZE = 12        # waterings per fill

COOP_R = 6           # chickens this close to a coop lay there, twice as often

PICNIC = 1.5         # food is worth more eaten on a picnic blanket

FARM = ("chicken", "cow", "chick", "calf")

CROWD_R = 6                # this many farm animals (CROWD_N) this close: hens stop laying,

CROWD_N = 3                # eggs rot instead of hatching, cows don't breed

FLEE_SECONDS = 4           # a hit farm animal runs from its attacker this long, a tile every FLEE_STRIDE seconds
FLEE_STRIDE = 0.3

TROUGH_R = 5               # animals this close to a filled trough feed themselves...

TROUGH_EVERY = 30          # ...about this often (seconds)

CREATURE_ID0 = 1_000_000
