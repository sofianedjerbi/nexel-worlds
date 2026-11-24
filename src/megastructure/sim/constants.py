"""Simulation timing and tuning constants."""

TICK_HZ = 10


def sec(seconds: float) -> int:
    """Durations are specified in seconds and converted here, so the tick rate never changes game pace."""
    return max(1, round(seconds * TICK_HZ))

DAY_TICKS = sec(1200)  # a 20-minute day

PACE = {"walk": 5, "sprint": 10, "sail": 1 / 0.15}   # tiles a second (Movement.stride; a screen walks at the same: rules.py)
STEP = sec(1 / PACE["walk"])
EAT_PACE = 2           # and so does a tile walked while eating (the two add up: a tile swum while eating takes four times as long)
SWIM_PACE = 2          # a tile in the water takes this many times a tile on land: half the speed, swimming or sprinting
SLOPE_UP, SLOPE_DOWN = 0.6, 0.2   # a step up a slope takes 60% longer, down it 20% (client: render.js)
CLIMB_S = 0.15                    # up or down a ladder: seconds a layer, rung by rung (client: climbing.js)
FALL_SAFE, FALL_HP = 3, 1         # a fall of up to 3 layers is nothing; each layer more costs half a heart

# Health and food, as the sandbox classic has them (needs.py). Health is counted in half hearts, ten hearts in all;
# food in half pieces, ten on the bar. (They were 0 to 100, and food went down by itself, a piece every 100 s.)
HP_MAX, FOOD_MAX = 20, 20
OLD_SCALE = 5                     # what a number on the old scale (0 to 100) is divided by
SAT_START = 5.0                   # saturation: food in reserve, unseen; what tires you takes it first, then the food
TIRED_MAX = 4.0                   # tiredness: at 4, a point of saturation goes (of food, when there is none), and it starts again
# what tires you, and by how much. Standing costs nothing. Walking: 200 s of it a point; sprinting, a point every 33 s
# (the classic's are per metre of a much slower walk); a sprint in the water (dash), every 13 s; healing a half heart
# costs a point and a half
TIRES = {"walk": 0.004, "sprint": 0.012, "swim": 0.01, "dash": 0.03, "jump": 0.05, "attack": 0.1, "hurt": 0.1, "dig": 0.02, "heal": 6.0}
HEAL_FOOD, HEAL_EVERY = 18, sec(4)   # with nine pieces or more: half a heart back every 4 s
FAST_HEAL_EVERY = sec(0.5)        # with the bar full and saturation left: every half second
STARVE_EVERY = sec(4)             # with no food left: half a heart gone every 4 s
SPRINT_FOOD = 6                   # with three pieces or fewer: no sprinting

VIEW_R = 10

SAY_R = 12

SHOUT_R = 48

EVENT_QUEUE = 60

MAX_TEXT = 200

LAYER = 0.5          # a layer of height is half a tile: in what you can reach, height is distance too (Movement.near)
ASIDE = ("eat",)     # done with the hands: whatever the feet are doing goes on (Agent.aside)
MOVES = ("walk", "move_to", "step", "stop", "leap")   # movement (stop: walking to where the player's screen stopped): quick actions happen alongside it instead of stopping it
MEANWHILE = MOVES + ("say", "shout", "jump")  # all that can be done while the hands are full (eating): walking, jumping, and talking. No punching, no digging, nothing else
SPRING_S = 3.0       # a jump said while walking holds this long for its step (a player's screen walks up to a few tiles ahead of the world)
VIA_FAR, VIA_MAX = 8, 8               # a tile a screen walked to: how far it may be from the last, and how many are kept (Movement.follow)
ATTACK_COOLDOWN = 0.4    # seconds between two swings
EAT_SECONDS = 0.9    # eating takes a moment (three bites; you walk on meanwhile, and do nothing else: MEANWHILE)
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

NAME_MAX = 16              # a creature's name (/name), in characters

CREATURE_ID0 = 1_000_000
