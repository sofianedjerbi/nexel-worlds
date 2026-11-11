"""Sound effects for every game interaction, made to sit with the background music.

Same family as music/compose.py: pure numpy, warm and soft, a touch of lo-fi.
  * anything tonal (rewards, UI, chimes) uses the music's notes: D major pentatonic (D E F# A B),
    so effects never clash with the loop; the goal chime is the music's own melody cell
  * physical models instead of beeps: resonant modes for wood and stone, granular noise for
    gravel and leaves, formant voices for animals, swept filters for air and fire
  * several variants of each frequent sound, so repeats never sound identical
  * loudness normalised per category (footsteps quiet, rewards clear, UI subtle)

    uv run python music/sfx.py      # writes music/site/sfx/*.wav + sfx.json
"""

from pathlib import Path
import json
import wave
import zlib

import numpy as np

SR = 48000
OUT = Path(__file__).with_name("site") / "sfx"

# ------------------------------------------------------------------ helpers


def tt(n):
    return np.arange(n) / SR


def N(sec):
    return int(sec * SR)


def midi(name):
    pcs = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
    pc, rest = pcs[name[0]], name[1:]
    while rest and rest[0] in "#b":
        pc += 1 if rest[0] == "#" else -1
        rest = rest[1:]
    return 12 * (int(rest) + 1) + pc


def hz(note):
    return 440.0 * 2 ** ((midi(note) - 69) / 12) if isinstance(note, str) else 440.0 * 2 ** ((note - 69) / 12)


PENTA_HIGH = ["D6", "E6", "F#6", "A6", "B6", "D7"]


def fft_filter(y, resp):
    n = len(y)
    m = 1 << int(np.ceil(np.log2(n + 4096)))
    return np.fft.irfft(np.fft.rfft(y, m) * resp(np.fft.rfftfreq(m, 1 / SR)), m)[:n]


def lp(fc, order=2):
    return lambda f: 1 / np.sqrt(1 + (f / fc) ** (2 * order))


def hp(fc, order=2):
    return lambda f: 1 / np.sqrt(1 + (fc / np.maximum(f, 1e-3)) ** (2 * order))


def bp(lo, hi, order=2):
    return lambda f: hp(lo, order)(f) * lp(hi, order)(f)


def place(dst, src, at):
    i = int(at * SR)
    if i >= len(dst):
        return dst
    m = min(len(src), len(dst) - i)
    dst[i:i + m] += src[:m]
    return dst


class Ctx:
    """Per-sound random source: same name + variant -> same sound every run."""

    def __init__(self, name, v):
        self.rng = np.random.default_rng(zlib.crc32(f"{name}/{v}".encode()))
        self.v = v

    def noise(self, n):
        return self.rng.standard_normal(n)

    def u(self, a, b):
        return float(self.rng.uniform(a, b))

    def pick(self, seq):
        return seq[int(self.rng.integers(len(seq)))]


def env_exp(n, tau, attack=0.001):
    t = tt(n)
    return np.clip(t / attack, 0, 1) * np.exp(-t / tau)


def modes(n, freqs, taus, amps, attack=0.0005):
    """A struck object: decaying sinusoids (wood, stone, metal, glass)."""
    t = tt(n)
    y = sum(a * np.sin(2 * np.pi * f * t) * np.exp(-t / d) for f, d, a in zip(freqs, taus, amps))
    return y * np.clip(t / attack, 0, 1)


def grains(c, n, count, dur_ms, lo, hi, spread=None, decay=None, amp_jitter=0.6):
    """Granular noise: many tiny filtered clicks (gravel, leaves, crackle, cracking wood)."""
    y = np.zeros(n)
    span = spread if spread else n / SR
    for _ in range(count):
        at = c.u(0, span)
        if decay:
            at = -np.log(1 - c.u(0, 0.98)) * decay
            if at >= n / SR:
                continue
        g = N(dur_ms / 1000 * c.u(0.5, 1.5))
        gr = c.noise(g) * np.exp(-tt(g) / (g / SR / 3))
        place(y, gr * (1 - amp_jitter * c.u(0, 1)), at)
    return fft_filter(y, bp(lo, hi))


def swept_noise(c, n, f_start, f_end, width=0.35, bands=28, curve=None):
    """Noise through a band that sweeps from f_start to f_end (log); a whoosh, a fire swell."""
    noise = c.noise(n)
    t = np.linspace(0, 1, n) if curve is None else curve
    centre = np.exp(np.log(f_start) + (np.log(f_end) - np.log(f_start)) * t)
    edges = np.geomspace(80, 14000, bands + 1)
    y = np.zeros(n)
    for lo, hi in zip(edges, edges[1:]):
        band = fft_filter(noise, bp(lo, hi, 3))
        fc = np.sqrt(lo * hi)
        y += band * np.exp(-((np.log(fc) - np.log(centre)) / width) ** 2)
    return y


def mallet(note, dur=1.0, bright=1.0, n=None):
    """Warm marimba-like bar: fundamental + tuned 4th and 10th partials, the 'reward' voice."""
    f = hz(note)
    n = n or N(dur)
    t = tt(n)
    y = (np.sin(2 * np.pi * f * t) * np.exp(-t / (0.45 * dur))
         + 0.3 * bright * np.sin(2 * np.pi * f * 4.0 * t) * np.exp(-t / 0.06)
         + 0.08 * bright * np.sin(2 * np.pi * f * 9.8 * t) * np.exp(-t / 0.02))
    return y * np.clip(t / 0.0015, 0, 1)


def bell(note, dur=1.6, n=None):
    """Soft bell / celesta: inharmonic but sweet, long tail."""
    f = hz(note)
    n = n or N(dur)
    t = tt(n)
    y = (np.sin(2 * np.pi * f * t) * np.exp(-t / (0.5 * dur))
         + 0.35 * np.sin(2 * np.pi * f * 2.0 * t) * np.exp(-t / (0.25 * dur))
         + 0.18 * np.sin(2 * np.pi * f * 3.0 * t + 1) * np.exp(-t / 0.15)
         + 0.08 * np.sin(2 * np.pi * f * 4.16 * t) * np.exp(-t / 0.06))
    return y * np.clip(t / 0.002, 0, 1)


def voice(n, f0, formants, bw, harmonics=40, breath=0.0, c=None):
    """Additive voice: harmonics of a moving f0, shaped by moving formants (animals)."""
    t = tt(n)
    ph = 2 * np.pi * np.cumsum(f0) / SR
    y = np.zeros(n)
    for k in range(1, harmonics):
        fk = k * f0
        g = sum(a / (1 + ((fk - F) / bw) ** 2) for F, a in formants(t))
        y += g / k ** 0.6 * np.sin(k * ph) * (fk < 10000)
    if breath and c is not None:
        y += breath * fft_filter(c.noise(n), bp(600, 4000))
    return y


def finish(y, warmth=11000, room=0.1):
    """Shared finish: gentle low-pass, soft saturation, a small room, de-click edges."""
    y = fft_filter(y, lp(warmth, 1))
    y = np.tanh(1.2 * y / (np.abs(y).max() + 1e-9)) / np.tanh(1.2)
    if room:
        n = N(0.35)
        r = np.random.default_rng(1).standard_normal(n) * np.exp(-tt(n) / 0.08)
        r = fft_filter(r, lp(4000))
        r[: N(0.008)] = 0
        r /= np.sqrt(np.sum(r ** 2))
        wet = np.pad(np.convolve(y, r), (0, 1))[: len(y) + n]
        y = np.concatenate([y, np.zeros(n)]) + room * wet
    fade = min(N(0.01), len(y) // 4)
    y[-fade:] *= np.linspace(1, 0, fade)
    y[: N(0.0005)] *= np.linspace(0, 1, N(0.0005))
    # trim trailing silence
    a = np.abs(y)
    last = np.nonzero(a > 1e-4 * a.max())[0]
    return y[: last[-1] + 1] if len(last) else y


# ------------------------------------------------------------------ the sounds
# each returns a mono array; c gives the per-variant randomness

S = {}
META = {}


def sfx(name, cat, when, variants=1, loud=0.5):
    def deco(fn):
        S[name] = fn
        META[name] = {"cat": cat, "when": when, "variants": variants, "loud": loud}
        return fn
    return deco


# --- footsteps --------------------------------------------------------------------------------

@sfx("step", "Footsteps", "walking on grass and soil", 4, 0.14)
def _(c):
    n = N(0.16)
    thump = fft_filter(c.noise(n), lp(260)) * env_exp(n, 0.025, 0.004)
    crunch = grains(c, n, 14, 6, 600, 3200, spread=0.05) * np.exp(-tt(n) / 0.05)
    return thump * 1.4 + crunch * 0.7


@sfx("tock", "Footsteps", "walking on wooden floors, bridges and boats", 4, 0.16)
def _(c):
    n = N(0.2)
    s = c.u(0.92, 1.08)
    knock = modes(n, [190 * s, 470 * s, 980 * s], [0.05, 0.025, 0.012], [1, 0.5, 0.25])
    return knock + 0.3 * fft_filter(c.noise(n), bp(800, 4000)) * env_exp(n, 0.006)


@sfx("click", "Footsteps", "walking on cobblestone", 4, 0.14)
def _(c):
    n = N(0.14)
    s = c.u(0.9, 1.1)
    tap = modes(n, [1250 * s, 2650 * s, 4100 * s], [0.015, 0.009, 0.005], [1, 0.6, 0.3])
    return tap * 0.7 + grains(c, n, 8, 4, 2000, 8000, spread=0.03) * np.exp(-tt(n) / 0.03) * 0.8


@sfx("wade", "Footsteps", "wading through shallow water", 4, 0.16)
def _(c):
    n = N(0.32)
    sw = swept_noise(c, n, 700, 2500, 0.5) * env_exp(n, 0.08, 0.02)
    y = sw
    for _ in range(4):   # bubbles: tiny rising sines
        bn = N(c.u(0.02, 0.05))
        f = c.u(500, 1300)
        bub = np.sin(2 * np.pi * np.cumsum(f * (1 + 2.5 * tt(bn) / (bn / SR))) / SR) * np.exp(-tt(bn) / 0.015)
        place(y, 0.4 * bub, c.u(0.03, 0.2))
    return y


@sfx("thud", "Footsteps", "landing after a hop down a level; striking wood or stone bare-handed", 3, 0.3)
def _(c):
    n = N(0.3)
    t = tt(n)
    body = np.sin(2 * np.pi * np.cumsum(70 + 60 * np.exp(-t / 0.02)) / SR) * env_exp(n, 0.08, 0.002)
    return body + 0.4 * fft_filter(c.noise(n), lp(900)) * env_exp(n, 0.03)


# --- working the land ------------------------------------------------------------------------

@sfx("chop", "Work", "an axe strike on a tree or wooden block", 4, 0.5)
def _(c):
    n = N(0.4)
    s = c.u(0.9, 1.1)
    wood = modes(n, [160 * s, 380 * s, 820 * s, 1500 * s], [0.12, 0.06, 0.03, 0.012], [1, 0.7, 0.4, 0.2])
    bite = fft_filter(c.noise(n), bp(1200, 6000)) * env_exp(n, 0.008)
    return wood + 0.7 * bite


@sfx("mine", "Work", "a pickaxe strike on stone", 4, 0.45)
def _(c):
    n = N(0.5)
    s = c.u(0.95, 1.05)
    ping = modes(n, [1870 * s, 2930 * s, 4480 * s], [0.12, 0.07, 0.04], [0.6, 0.4, 0.2])
    rock = modes(n, [420 * s, 760 * s], [0.03, 0.02], [0.8, 0.5])
    grit = grains(c, n, 20, 5, 1500, 7000, spread=0.04) * np.exp(-tt(n) / 0.05)
    return ping * 0.7 + rock + grit * 0.8


@sfx("dig", "Work", "a shovel in soil, digging a hole", 4, 0.4)
def _(c):
    n = N(0.35)
    thunk = fft_filter(c.noise(n), lp(350)) * env_exp(n, 0.05, 0.004)
    soil = grains(c, n, 40, 10, 250, 1800, decay=0.07)
    return thunk * 1.3 + soil * 0.9


@sfx("rustle", "Work", "cutting grass, picking flowers and plants, leaves", 4, 0.3)
def _(c):
    n = N(0.4)
    leaves = grains(c, n, 90, 5, 1500, 6000, spread=0.3) * np.sin(np.pi * np.clip(tt(n) / 0.32, 0, 1))
    return leaves


@sfx("swing", "Work", "swinging a tool or a weapon", 3, 0.25)
def _(c):
    n = N(0.28)
    curve = np.sin(np.linspace(0, np.pi, n)) ** 0.7
    return swept_noise(c, n, 500, 2400, 0.35, curve=np.linspace(0, 1, n)) * curve


# --- things break ------------------------------------------------------------------------------

@sfx("snap", "Breaking", "a wooden block or fence breaks", 3, 0.55)
def _(c):
    n = N(0.5)
    crack = grains(c, n, 70, 2, 800, 6000, decay=0.06)
    body = modes(n, [140, 330, 700], [0.1, 0.05, 0.02], [1, 0.6, 0.3])
    return crack * 1.2 + body * 0.8


@sfx("crumble", "Breaking", "stone breaks; digging down into a cave", 3, 0.55)
def _(c):
    n = N(0.8)
    y = np.zeros(n)
    for k in range(9):   # a little cascade of rocks, each lower and later
        at = 0.02 + k * c.u(0.03, 0.07)
        f = c.u(300, 900) * (1 - k * 0.05)
        place(y, modes(N(0.15), [f, f * 1.9, f * 3.1], [0.03, 0.02, 0.01], [1, 0.5, 0.3]) * (1 - k * 0.07), at)
    rumble = fft_filter(c.noise(n), lp(200)) * env_exp(n, 0.25, 0.02)
    return y + 0.8 * rumble + 0.5 * grains(c, n, 60, 4, 1500, 6000, decay=0.2)


@sfx("creak", "Breaking", "a tree starts to fall", 2, 0.4)
def _(c):
    n = N(0.9)
    t = tt(n)
    rate = 30 + 40 * np.sin(np.pi * t / 0.9) + 8 * np.sin(2 * np.pi * 7 * t)   # stick-slip
    ph = np.cumsum(rate) / SR
    pulses = (np.diff(np.floor(ph), prepend=0) > 0).astype(float)
    wood = sum(fft_filter(pulses, lambda f, F=F: 1 / (1 + ((f - F) / (F / 9)) ** 2)) for F in (380, 760, 1250))
    return wood * np.sin(np.pi * np.clip(t / 0.9, 0, 1)) ** 0.5


@sfx("fallthud", "Breaking", "a tree hits the ground", 2, 0.75)
def _(c):
    n = N(1.0)
    t = tt(n)
    boom = np.sin(2 * np.pi * np.cumsum(48 + 50 * np.exp(-t / 0.05)) / SR) * env_exp(n, 0.22, 0.004)
    crash = fft_filter(c.noise(n), bp(100, 900)) * env_exp(n, 0.12)
    leaves = grains(c, n, 160, 5, 1800, 6000, decay=0.25)
    return boom * 1.6 + crash * 0.6 + leaves * 0.18


# --- building ----------------------------------------------------------------------------------

@sfx("place", "Building", "placing a wooden block, a wall, a fence", 3, 0.45)
def _(c):
    n = N(0.35)
    s = c.u(0.95, 1.05)
    knock = modes(n, [130 * s, 310 * s, 690 * s], [0.08, 0.04, 0.02], [1, 0.6, 0.3])
    settle = fft_filter(c.noise(n), bp(300, 2500)) * env_exp(n, 0.02)
    return knock + 0.5 * settle


@sfx("clack", "Building", "placing stone or cobble; a chest lid", 3, 0.4)
def _(c):
    n = N(0.3)
    s = c.u(0.95, 1.05)
    a = modes(n, [620 * s, 1500 * s, 2600 * s], [0.03, 0.015, 0.008], [1, 0.5, 0.3])
    b = np.roll(modes(n, [700 * s, 1700 * s], [0.02, 0.01], [0.6, 0.3]), N(0.035))
    return a + b + 0.3 * fft_filter(c.noise(n), bp(1500, 7000)) * env_exp(n, 0.006)


@sfx("plant", "Building", "planting a seed or a sapling", 2, 0.35)
def _(c):
    n = N(0.45)
    pat = fft_filter(c.noise(n), lp(500)) * env_exp(n, 0.03, 0.003)
    t = tt(n)
    sprout = np.sin(2 * np.pi * np.cumsum(hz("A5") * (1 + 0.19 * np.clip(t / 0.08, 0, 1))) / SR) * np.exp(-t / 0.12)
    return pat + 0.35 * np.roll(sprout, N(0.05))


@sfx("gate", "Building", "a gate or a door swings open", 2, 0.35)
def _(c):
    n = N(0.55)
    t = tt(n)
    rate = 55 + 60 * t / 0.55
    ph = np.cumsum(rate) / SR
    pulses = (np.diff(np.floor(ph), prepend=0) > 0).astype(float)
    hinge = sum(fft_filter(pulses, lambda f, F=F: 1 / (1 + ((f - F) / (F / 12)) ** 2)) for F in (900, 1800, 2600))
    hinge *= np.sin(np.pi * np.clip(t / 0.4, 0, 1))
    latch = np.roll(modes(n, [1600, 3300], [0.01, 0.006], [0.6, 0.3]), N(0.0))
    return hinge * 0.8 + latch


@sfx("chest", "Building", "opening a chest", 2, 0.4)
def _(c):
    n = N(0.6)
    lid = S["gate"](c)[: n]
    lid = np.pad(lid, (0, max(0, n - len(lid))))
    thunk = np.roll(modes(n, [150, 360, 800], [0.08, 0.04, 0.02], [1, 0.5, 0.25]), N(0.35))
    return lid * 0.5 + thunk


@sfx("write", "Building", "writing on a sign or a letter", 2, 0.25)
def _(c):
    n = N(0.7)
    y = np.zeros(n)
    at = 0.0
    while at < 0.6:   # pencil strokes
        sn = N(c.u(0.05, 0.12))
        stroke = fft_filter(c.noise(sn), bp(1800, 6000)) * np.sin(np.linspace(0, np.pi, sn))
        place(y, stroke * c.u(0.5, 1), at)
        at += c.u(0.07, 0.15)
    return y


# --- getting things -------------------------------------------------------------------------

@sfx("collect", "Items", "picking up an item", 3, 0.38)
def _(c):
    lo, hi = c.pick([("A5", "D6"), ("F#5", "A5"), ("D6", "F#6")])
    n = N(0.6)
    y = np.zeros(n)
    place(y, mallet(lo, 0.5, n=N(0.5)), 0)
    place(y, mallet(hi, 0.6, n=N(0.55)), 0.065)
    return y + 0.08 * grains(c, n, 10, 3, 6000, 12000, spread=0.1)


@sfx("orb", "Items", "an experience orb flies into you", 6, 0.22)
def _(c):
    note = PENTA_HIGH[c.v % len(PENTA_HIGH)]
    return bell(note, 0.5, n=N(0.5)) * 0.9


@sfx("drop", "Items", "dropping an item", 2, 0.3)
def _(c):
    n = N(0.25)
    t = tt(n)
    pop = np.sin(2 * np.pi * np.cumsum(hz("A5") * np.exp(-t / 0.08)) / SR) * env_exp(n, 0.06, 0.002)
    return pop + 0.3 * fft_filter(c.noise(n), lp(500)) * env_exp(n, 0.02)


@sfx("loot", "Items", "a dropped item lands and bounces", 3, 0.25)
def _(c):
    n = N(0.4)
    y = np.zeros(n)
    for k, (at, v) in enumerate(((0, 1), (0.13, 0.45), (0.21, 0.2))):
        place(y, modes(N(0.08), [700, 1600], [0.015, 0.008], [1, 0.4]) * v, at)
    return y


@sfx("craft", "Items", "crafting something at a workbench", 2, 0.45)
def _(c):
    n = N(1.1)
    y = np.zeros(n)
    for k in range(3):   # tap tap tap of tools
        place(y, modes(N(0.1), [300, 750, 1600], [0.03, 0.015, 0.008], [1, 0.5, 0.2]) * 0.6, k * 0.09)
    for k, note in enumerate(("D5", "A5", "D6")):
        place(y, mallet(note, 0.7, n=N(0.7)) * (0.7 + 0.15 * k), 0.3 + k * 0.08)
    return y + 0.06 * grains(c, n, 25, 3, 6000, 12000, spread=0.6)


# --- progress -------------------------------------------------------------------------------

@sfx("chime", "Progress", "a goal completed (it plays the music's own melody cell)", 1, 0.4)
def _(c):
    n = N(1.8)
    y = np.zeros(n)
    for at, note, v in ((0, "F#6", 0.9), (0.14, "E6", 0.7), (0.28, "F#6", 0.8), (0.42, "A6", 1.0)):
        place(y, bell(note, 1.3, n=N(1.3)) * v, at)
    return y


@sfx("levelup", "Progress", "you reach a new level", 1, 0.5)
def _(c):
    n = N(2.4)
    y = np.zeros(n)
    for k, note in enumerate(("D5", "F#5", "A5", "D6", "E6", "F#6")):
        place(y, mallet(note, 0.9, n=N(0.9)) * 0.8, k * 0.075)
    pad = sum(np.sin(2 * np.pi * hz(nn) * tt(n)) for nn in ("D5", "A5", "F#6"))
    swell = np.sin(np.pi * np.clip((tt(n) - 0.35) / 1.9, 0, 1)) ** 2
    return y + 0.12 * pad * swell + 0.05 * grains(c, n, 40, 3, 6000, 12000, spread=1.6)


@sfx("mail", "Progress", "a letter arrives in your mailbox", 1, 0.35)
def _(c):
    n = N(1.2)
    paper = swept_noise(c, N(0.25), 2000, 5000, 0.5) * np.sin(np.linspace(0, np.pi, N(0.25)))
    y = np.zeros(n)
    place(y, paper * 0.4, 0)
    place(y, bell("D6", 1.0, n=N(1.0)), 0.2)
    place(y, bell("A6", 0.9, n=N(0.9)) * 0.8, 0.36)
    return y


# --- bodies and fights --------------------------------------------------------------------------

@sfx("hit", "Fights", "landing a blow", 3, 0.5)
def _(c):
    n = N(0.3)
    t = tt(n)
    body = np.sin(2 * np.pi * np.cumsum(110 + 80 * np.exp(-t / 0.015)) / SR) * env_exp(n, 0.06, 0.001)
    slap = fft_filter(c.noise(n), bp(700, 4500)) * env_exp(n, 0.015)
    return body + 0.8 * slap


@sfx("hurt", "Fights", "you take damage", 2, 0.45)
def _(c):
    n = N(0.45)
    t = tt(n)
    thump = np.sin(2 * np.pi * np.cumsum(90 * np.exp(-t / 0.3)) / SR) * env_exp(n, 0.1, 0.002)
    muffle = fft_filter(c.noise(n), bp(200, 1200)) * env_exp(n, 0.05)
    return thump + 0.6 * muffle


@sfx("die", "Fights", "you die (gentle, not scary)", 1, 0.4)
def _(c):
    n = N(2.4)
    y = np.zeros(n)
    for k, note in enumerate(("A5", "F#5", "D5", "A4")):
        place(y, bell(note, 1.6, n=N(1.6)) * (0.9 - 0.12 * k), k * 0.32)
    return fft_filter(y, lp(3500))


@sfx("poof", "Fights", "a creature vanishes in a puff of smoke", 2, 0.35)
def _(c):
    n = N(0.6)
    t = tt(n)
    puff = swept_noise(c, n, 2500, 400, 0.5) * env_exp(n, 0.15, 0.01)
    bwoop = np.sin(2 * np.pi * np.cumsum(hz("D6") * np.exp(-t / 0.15)) / SR) * env_exp(n, 0.12, 0.005)
    return puff + 0.25 * bwoop


@sfx("gloom", "Fights", "a gloom attacks at night: a breathy, low growl", 2, 0.4)
def _(c):
    n = N(0.9)
    t = tt(n)
    f0 = 55 + 12 * np.sin(2 * np.pi * 3 * t) * np.exp(-t / 0.4) + c.u(-4, 4)
    growl = voice(n, f0, lambda t: [(450, 1.0), (900, 0.5)], 180, harmonics=60)
    breath = fft_filter(c.noise(n), bp(200, 1400)) * 0.3
    am = 0.7 + 0.3 * np.sin(2 * np.pi * 23 * t)
    return fft_filter(growl * 0.35 * am + breath, lp(1800)) * np.sin(np.pi * np.clip(t / 0.9, 0, 1)) ** 0.6


# --- animals -----------------------------------------------------------------------------------

@sfx("cluck", "Animals", "a chicken clucks (petted, fed, hit, laying)", 4, 0.3)
def _(c):
    n = N(0.45)
    y = np.zeros(n)
    count = 2 + c.v % 2
    for k in range(count):
        bn = N(0.07)
        t = tt(bn)
        f0 = c.u(650, 850) * np.exp(-t / 0.12)
        buk = voice(bn, f0, lambda t: [(1300, 1.0), (2600, 0.6)], 350, harmonics=14)
        place(y, buk * np.sin(np.pi * np.clip(t / 0.07, 0, 1)), k * c.u(0.1, 0.14))
    return y


@sfx("chirp", "Animals", "a chick peeps; an egg hatches", 4, 0.25)
def _(c):
    n = N(0.35)
    y = np.zeros(n)
    for k in range(2):
        bn = N(0.06)
        t = tt(bn)
        f = c.u(3000, 3800) * (1 + 0.25 * t / 0.06)
        place(y, np.sin(2 * np.pi * np.cumsum(f) / SR) * np.sin(np.pi * t / 0.06), k * 0.11)
    return y


@sfx("moo", "Animals", "a cow moos (petted, milked, fed, hit)", 3, 0.4)
def _(c):
    n = N(1.2)
    t = tt(n)
    base = c.u(95, 120)
    f0 = base * (1 + 0.25 * np.sin(np.pi * np.clip(t / 1.1, 0, 1)) - 0.1 * t)
    vowel = lambda t: [(300 + 350 * np.clip(t / 0.6, 0, 1), 1.0), (800 + 300 * np.clip(t / 0.6, 0, 1), 0.5), (2500, 0.1)]  # "mm" -> "oo"
    y = voice(n, f0, vowel, 150, harmonics=50, breath=0.04, c=c)
    return y * np.sin(np.pi * np.clip(t / 1.15, 0, 1)) ** 0.7


@sfx("milk", "Animals", "milking a cow into a pail", 2, 0.35)
def _(c):
    n = N(0.8)
    y = np.zeros(n)
    for k in range(3):   # squirts into a pail
        sn = N(0.12)
        t = tt(sn)
        sq = fft_filter(c.noise(sn), bp(1200, 4500)) * np.exp(-t / 0.05)
        ring = np.sin(2 * np.pi * c.u(900, 1100) * (1 - 0.2 * t / 0.12) * t) * np.exp(-t / 0.06)
        place(y, sq * 0.6 + ring * 0.4, k * 0.22)
    return y


@sfx("lay", "Animals", "a hen lays an egg", 1, 0.3)
def _(c):
    n = N(0.6)
    y = np.zeros(n)
    place(y, S["cluck"](c) * 0.8, 0)
    t = tt(N(0.15))
    plop = np.sin(2 * np.pi * np.cumsum(500 * np.exp(-t / 0.05)) / SR) * np.exp(-t / 0.04)
    place(y, plop, 0.3)
    return y


@sfx("hatch", "Animals", "an egg hatches", 1, 0.3)
def _(c):
    n = N(0.6)
    crack = grains(c, n, 12, 2, 2000, 9000, spread=0.15)
    y = crack * 0.8
    place(y, S["chirp"](c) * 0.9, 0.2)
    return y


@sfx("love", "Animals", "an animal is happy: petting, love hearts, a calf is born", 2, 0.3)
def _(c):
    n = N(0.8)
    y = np.zeros(n)
    for k, note in enumerate(("A5", "D6") if c.v == 0 else ("F#5", "B5")):
        place(y, bell(note, 0.7, n=N(0.7)) * 0.8, k * 0.09)
    return y + 0.05 * grains(c, n, 15, 3, 6000, 12000, spread=0.4)


# --- world -----------------------------------------------------------------------------------

@sfx("water", "World", "filling a bucket, watering, a splash, boarding a boat", 3, 0.4)
def _(c):
    n = N(0.6)
    splash = swept_noise(c, n, 3000, 900, 0.5) * env_exp(n, 0.12, 0.004)
    y = splash
    for _ in range(7):
        bn = N(c.u(0.02, 0.06))
        f = c.u(400, 1400)
        bub = np.sin(2 * np.pi * np.cumsum(f * (1 + 3 * tt(bn) / (bn / SR))) / SR) * np.exp(-tt(bn) / 0.02)
        place(y, 0.35 * bub, c.u(0.02, 0.35))
    return y


@sfx("whoosh", "World", "lighting a fire: the flame catches", 2, 0.4)
def _(c):
    n = N(0.8)
    curve = np.clip(tt(n) / 0.35, 0, 1) ** 0.6
    swell = swept_noise(c, n, 200, 1800, 0.45, curve=curve)
    return swell * np.sin(np.pi * np.clip(tt(n) / 0.8, 0, 1)) ** 0.8


@sfx("crackle", "World", "fire burning, something burns", 3, 0.3)
def _(c):
    n = N(1.2)
    roar = fft_filter(c.noise(n), bp(120, 700)) * 0.25
    pops = grains(c, n, 25, 2, 1500, 9000, spread=1.1, amp_jitter=0.9)
    return (roar + pops) * np.sin(np.pi * np.clip(tt(n) / 1.2, 0, 1)) ** 0.3


@sfx("flood", "World", "water spreads over the ground", 1, 0.35)
def _(c):
    n = N(1.4)
    rush = fft_filter(c.noise(n), bp(300, 3000)) * np.sin(np.pi * np.clip(tt(n) / 1.4, 0, 1))
    y = rush * 0.5
    for _ in range(14):
        bn = N(c.u(0.02, 0.05))
        bub = np.sin(2 * np.pi * np.cumsum(c.u(500, 1200) * (1 + 2 * tt(bn) / (bn / SR))) / SR) * np.exp(-tt(bn) / 0.015)
        place(y, 0.3 * bub, c.u(0.05, 1.2))
    return y


@sfx("grow", "World", "a crop or a sapling grows a stage", 2, 0.18)
def _(c):
    note = c.pick(["A6", "B6", "D7"])
    n = N(0.6)
    t = tt(n)
    sparkle = np.sin(2 * np.pi * np.cumsum(hz(note) * (1 + 0.06 * np.clip(t / 0.1, 0, 1))) / SR) * env_exp(n, 0.15, 0.01)
    return sparkle + 0.2 * grains(c, n, 8, 3, 6000, 12000, spread=0.2)


@sfx("descend", "World", "going down into a cave", 1, 0.4)
def _(c):
    n = N(1.2)
    y = swept_noise(c, n, 1500, 150, 0.5) * np.sin(np.pi * np.clip(tt(n) / 1.2, 0, 1))
    place(y, S["crumble"](c)[: N(0.6)] * 0.5, 0.0)
    return y


# --- people and interface -----------------------------------------------------------------------

@sfx("say", "People", "someone nearby says something (a soft talk blip)", 5, 0.18)
def _(c):
    note = ["D5", "E5", "F#5", "A5", "B5"][c.v % 5]
    n = N(0.12)
    t = tt(n)
    y = voice(n, np.full(n, hz(note)), lambda t: [(900, 1.0), (1800, 0.4)], 400, harmonics=10)
    return y * np.sin(np.pi * np.clip(t / 0.12, 0, 1))


@sfx("shout", "People", "someone shouts", 2, 0.3)
def _(c):
    n = N(0.35)
    y = np.zeros(n)
    for k, note in enumerate(("A5", "D6")):
        bn = N(0.14)
        t = tt(bn)
        f0 = np.full(bn, hz(note)) * (1 + 0.03 * np.sin(2 * np.pi * 9 * t))
        place(y, voice(bn, f0, lambda t: [(1100, 1.0), (2400, 0.6)], 500, harmonics=14) * np.sin(np.pi * t / 0.14), k * 0.13)
    return y


@sfx("give", "People", "someone gives you something", 1, 0.35)
def _(c):
    n = N(1.0)
    paper = swept_noise(c, N(0.2), 3000, 6000, 0.5) * np.sin(np.linspace(0, np.pi, N(0.2)))
    y = np.zeros(n)
    place(y, paper * 0.4, 0)
    for k, note in enumerate(("B5", "D6", "F#6")):
        place(y, mallet(note, 0.6, n=N(0.6)) * 0.8, 0.12 + k * 0.07)
    return y


@sfx("join", "People", "someone arrives in the world (a wind chime)", 1, 0.25)
def _(c):
    n = N(2.2)
    y = np.zeros(n)
    for k in range(6):
        place(y, bell(c.pick(PENTA_HIGH), 1.4, n=N(1.4)) * c.u(0.4, 0.8), k * c.u(0.08, 0.16))
    return fft_filter(y, lp(6000))


@sfx("leave", "People", "someone falls asleep (leaves)", 1, 0.22)
def _(c):
    n = N(1.6)
    y = np.zeros(n)
    for k, note in enumerate(("A6", "F#6", "D6")):
        place(y, bell(note, 1.2, n=N(1.2)) * (0.7 - 0.12 * k), k * 0.18)
    return fft_filter(y, lp(5000))


@sfx("ui", "Interface", "clicking a button, picking a hotbar slot, switching tabs", 3, 0.2)
def _(c):
    n = N(0.12)
    f = hz(["D6", "E6", "A6"][c.v % 3])
    return modes(n, [f, f * 2.7], [0.03, 0.01], [1, 0.3]) + 0.15 * fft_filter(c.noise(n), bp(2000, 8000)) * env_exp(n, 0.003)


@sfx("open", "Interface", "opening a panel (crafting, mailbox, chest view)", 1, 0.25)
def _(c):
    n = N(0.4)
    slide = swept_noise(c, n, 1500, 4000, 0.5) * np.sin(np.pi * np.clip(tt(n) / 0.25, 0, 1)) * 0.4
    y = slide
    place(y, mallet("A5", 0.4, n=N(0.35)) * 0.6, 0.05)
    place(y, mallet("D6", 0.4, n=N(0.35)) * 0.6, 0.12)
    return y


@sfx("close", "Interface", "closing a panel", 1, 0.22)
def _(c):
    n = N(0.4)
    slide = swept_noise(c, n, 4000, 1500, 0.5) * np.sin(np.pi * np.clip(tt(n) / 0.25, 0, 1)) * 0.4
    y = slide
    place(y, mallet("D6", 0.4, n=N(0.35)) * 0.6, 0.03)
    place(y, mallet("A5", 0.4, n=N(0.35)) * 0.6, 0.1)
    return y


@sfx("buzz", "Interface", "something can't be done (soft, never harsh)", 1, 0.25)
def _(c):
    n = N(0.35)
    y = np.zeros(n)
    for k, f in enumerate((180, 150)):
        place(y, modes(N(0.12), [f, f * 2.3], [0.04, 0.02], [1, 0.3]), k * 0.11)
    return fft_filter(y, lp(1500))


# ------------------------------------------------------------------ render all


def loudness(y):
    """Loudest 50 ms RMS: the part you actually hear."""
    w = N(0.05)
    if len(y) <= w:
        return np.sqrt(np.mean(y ** 2))
    c = np.cumsum(np.concatenate([[0], y ** 2]))
    return np.sqrt(np.max(c[w:] - c[:-w]) / w)


def write_wav(path, y):
    pcm = (np.clip(y, -1, 1) * 32767).round().astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("*.wav"):
        old.unlink()
    manifest = {}
    for name, fn in S.items():
        m = META[name]
        files = []
        for v in range(m["variants"]):
            y = finish(fn(Ctx(name, v)))
            y *= m["loud"] * 0.5 / loudness(y)          # same perceived level within a category
            y *= min(1, 0.95 / np.abs(y).max())
            f = f"{name}_{v}.wav"
            write_wav(OUT / f, y)
            files.append(f)
        manifest[name] = {"category": m["cat"], "when": m["when"], "files": files}
        print(f"  {name:9s} {m['cat']:10s} x{m['variants']}  {len(y) / SR:.2f}s")
    (OUT / "sfx.json").write_text(json.dumps(manifest, indent=1))
    print(f"{len(manifest)} sounds, {sum(len(v['files']) for v in manifest.values())} files")
