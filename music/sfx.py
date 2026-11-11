"""Sound effects for every game interaction, made to sit with the background music. (Fable 5.2 pass.)

Pure numpy. What this pass fixed, all measured by music/audit.py against the frozen Opus set in music/opus/:
  * rumble: footsteps and thuds had most of their energy under 40 Hz (inaudible, and it made the audible part quiet);
    everything is now high-passed at 45 Hz
  * latency: every sound starts within about a millisecond (leading silence and slow swells are trimmed)
  * loudness: levels are set with the ear's weighting (ITU-R BS.1770 K-weighting), not raw RMS,
    so sounds in one family are equally loud and every variant of a sound matches
  * variants: sounds whose variants were identical now really differ (size / pitch / timing per variant)
  * context: eating, watering, filling a bucket, bare-hand hits and a startled chicken have their own sounds
  * voices: the cow has a closed-mouth start, a pitch arc and a rough onset; talk is a soft babble of vowels

Tonal sounds use the music's notes (D major pentatonic); the goal chime is the music's melody cell.

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


def tail(y, ms=8):
    """Smooth the last few ms so nothing ever stops on a click."""
    k = min(int(ms * SR / 1000), len(y) // 2)
    if k > 1:
        y = y.copy()
        y[-k:] *= 0.5 + 0.5 * np.cos(np.linspace(0, np.pi, k))
    return y


def place(dst, src, at):
    i = int(at * SR)
    if i >= len(dst):
        return dst
    m = min(len(src), len(dst) - i)
    dst[i:i + m] += tail(src[:m])
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
    return tail(y * np.clip(t / attack, 0, 1))


MATERIALS = {   # (lowest mode, highest mode, modes, loss factor eta, contact ms, contact brightness Hz)
    "wood": (110, 3200, 32, 0.035, 1.2, 6000),
    "hollow": (90, 2400, 32, 0.03, 1.5, 5000),     # boards over air: floors, chests, boats
    "stone": (380, 7500, 40, 0.07, 0.5, 9000),        # rocks rest on the ground: rings only a few ms
    "metal": (1400, 8500, 12, 0.0015, 0.2, 14000),
    "body": (55, 650, 24, 0.14, 4.0, 2500),       # flesh, fur, a sack: heavily damped, dull contact
    "dirt": (60, 700, 16, 0.3, 6.0, 1800),
    "ceramic": (480, 6500, 32, 0.025, 0.5, 8000),  # a clay pot full of soil: a short, dull clink
}


def impact(c, n, material, size=1.0, hardness=1.0, brightness=1.0, damp=1.0):
    """A strike: a short noise contact excites ~30 damped resonances spread over the material's range.
    Decay per mode follows the loss factor: tau = 1 / (pi f eta), so highs die first, as in real objects.
    damp > 1 for something resting on the ground or held: the contact soaks up the ring."""
    lo, hi, count, eta, contact, bright_hz = MATERIALS[material]
    t = tt(n)
    ir = np.zeros(n)
    for _ in range(count):
        f = np.exp(c.u(np.log(lo), np.log(hi))) / size
        tau = min(1.2, 1 / (np.pi * f * eta * damp * c.u(0.7, 1.4)))
        amp = c.u(0.3, 1.0) * (f / lo) ** (-0.5 / brightness)
        ir += amp * np.sin(2 * np.pi * f * t + c.u(0, 6.28)) * np.exp(-t / tau)
    cn = max(8, int(contact / hardness * SR / 1000))
    excite = c.noise(cn) * np.sin(np.linspace(0, np.pi, cn))
    excite = fft_filter(excite, lp(min(16000, bright_hz * hardness * brightness)))
    y = np.convolve(excite, ir)[:n]
    y += 0.25 * np.pad(excite, (0, max(0, n - cn)))[:n]          # the contact itself
    return tail(y / (np.abs(y).max() + 1e-9))


def grf(n, heel=0.0, toe=0.075, toe_amp=0.6, soft=1.0, c=None):
    """Ground reaction force of one step: a smooth heel bump, then a smaller toe bump.
    soft > 1 = softer sole (slower, rounder attack). Values follow Turchet 2016, fig. 2 (walking steps ~0.1-0.18 s)."""
    t = tt(n)
    out = np.zeros(n)
    for at, amp, tau in ((heel, 1.0, 0.006 * soft), (toe, toe_amp, 0.008 * soft)):
        if c is not None:
            if at > 0:
                at = max(0.0, at + c.u(-0.008, 0.008))   # only the toe wanders; the heel lands at t = 0
            amp *= c.u(0.85, 1.1)
        x = np.clip(t - at, 0, None) / tau
        out += amp * x ** 2 * np.exp(2 - 2 * x) * (t >= at)   # peaks at 1 when t = at + tau
    return out


def force_modes(c, n, force, lo, hi, count=6, tau=(0.004, 0.02)):
    """Impact model driven 'in force': a few damped modes of the floor, excited by the foot's force curve.
    A smooth force excites only the low modes, which is what keeps a step from sounding like a mallet."""
    t = tt(N(0.25))
    ir = np.zeros(len(t))
    for _ in range(count):
        f = np.exp(c.u(np.log(lo), np.log(hi)))
        ir += c.u(0.4, 1) * np.sin(2 * np.pi * f * t + c.u(0, 6.28)) * np.exp(-t / c.u(*tau))
    y = np.convolve(np.diff(force, prepend=0), ir)[:n]   # the floor answers to changes of force
    return y / (np.abs(y).max() + 1e-9)


def contact_noise(c, n, force, lo, hi):
    """The white-noise burst at heel and toe strikes, proportional to the exciter (Turchet 2016, 3.2.2)."""
    drive = np.clip(np.diff(force, prepend=0), 0, None)
    drive = np.convolve(drive, np.exp(-tt(N(0.02)) / 0.004))[:n]
    y = fft_filter(c.noise(n), bp(lo, hi)) * drive
    return y / (np.abs(y).max() + 1e-9)


def phism(c, n, energy, rate, freq, decay, jitter=0.35):
    """Cook's physically informed stochastic model: particle collisions as a Poisson process whose rate follows
    the input energy; each collision rings a very short resonance near freq (gravel, soil, grass, leaves)."""
    e = energy / (energy.max() + 1e-9)
    p = np.clip(rate * e / SR, 0, 1)
    hits = np.nonzero(c.rng.uniform(size=n) < p)[0]
    y = np.zeros(n)
    g = N(decay * 6)
    tg = tt(g)
    for h in hits:
        f = freq * np.exp(jitter * c.rng.standard_normal())
        grain = np.sin(2 * np.pi * f * tg + c.u(0, 6.28)) * np.exp(-tg / decay)
        m = min(g, n - h)
        y[h:h + m] += e[h] * c.u(0.2, 1) * grain[:m]
    return y / (np.abs(y).max() + 1e-9)


def fractal_noise(c, n, beta=1.0):
    """1/f^beta noise: rubbing and brushing textures (roughness)."""
    spec = np.fft.rfft(c.noise(n))
    f = np.fft.rfftfreq(n, 1 / SR)
    spec *= 1 / np.maximum(f, 40) ** (beta / 2)
    y = np.fft.irfft(spec, n)
    return y / (np.abs(y).max() + 1e-9)


def bubble(c, r_mm, amp=1.0):
    """One bubble: Minnaert f0 = 3/r, rising as it decays: f(t) = f0 (1 + 0.1 d t), d = 0.13/r + 0.0072 r^-1.5."""
    r = r_mm / 1000
    f0 = 3 / r
    d = 0.13 / r + 0.0072 * r ** -1.5
    n = N(min(0.2, 6 / d))
    t = tt(n)
    return amp * np.sin(2 * np.pi * np.cumsum(f0 * (1 + 0.1 * d * t)) / SR) * np.exp(-d * t)


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
    n = max(n or 0, N(0.45 * dur * 7))
    t = tt(n)
    y = (np.sin(2 * np.pi * f * t) * np.exp(-t / (0.45 * dur))
         + 0.3 * bright * np.sin(2 * np.pi * f * 4.0 * t) * np.exp(-t / 0.06)
         + 0.08 * bright * np.sin(2 * np.pi * f * 9.8 * t) * np.exp(-t / 0.02))
    return y * np.clip(t / 0.0015, 0, 1)


def bell(note, dur=1.6, n=None):
    """Soft bell / celesta: inharmonic but sweet, long tail."""
    f = hz(note)
    n = max(n or 0, N(0.5 * dur * 7))
    t = tt(n)
    y = (np.sin(2 * np.pi * f * t) * np.exp(-t / (0.5 * dur))
         + 0.35 * np.sin(2 * np.pi * f * 2.0 * t) * np.exp(-t / (0.25 * dur))
         + 0.18 * np.sin(2 * np.pi * f * 3.0 * t + 1) * np.exp(-t / 0.15)
         + 0.08 * np.sin(2 * np.pi * f * 4.16 * t) * np.exp(-t / 0.06))
    return y * np.clip(t / 0.002, 0, 1)


def voice(n, f0, formants, bw, harmonics=40, breath=0.0, c=None):
    """Additive voice: harmonics of a moving f0, shaped by moving formants (animals)."""
    t = tt(n)
    if c is not None:   # real voices are never perfectly steady: slow pitch jitter, a little shimmer
        drift = fft_filter(c.noise(n), lp(12))
        f0 = f0 * (1 + 0.012 * drift / (np.abs(drift).max() + 1e-9))
    ph = 2 * np.pi * np.cumsum(f0) / SR
    y = np.zeros(n)
    for k in range(1, harmonics):
        fk = k * f0
        g = sum(a / (1 + ((fk - F) / bw) ** 2) for F, a in formants(t))
        y += g / k ** 0.6 * np.sin(k * ph) * (fk < 10000)
    if c is not None:
        sh = fft_filter(c.noise(n), lp(30))
        y *= 1 + 0.12 * sh / (np.abs(sh).max() + 1e-9)
    if breath and c is not None:
        y += breath * fft_filter(c.noise(n), bp(600, 4000))
    return y


def finish(y, warmth=11000, room=0.1):
    """Shared finish: gentle low-pass, soft saturation, a small room, de-click edges."""
    y = tail(fft_filter(y, lambda f: lp(warmth, 1)(f) * hp(55, 3)(f)), 10)   # no inaudible rumble eating the headroom
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
    start = max(0, int(np.argmax(np.abs(y) > 0.05 * np.abs(y).max())) - N(0.001))   # instant: drop the lead-in
    y = y[start:].copy()
    k = N(0.0015 if start else 0.0005)
    y[:k] *= np.linspace(0, 1, k)
    # trim trailing silence
    a = np.abs(y)
    last = np.nonzero(a > 1e-4 * a.max())[0]
    return y[: last[-1] + 1] if len(last) else y


# ------------------------------------------------------------------ the sounds
# each returns a mono array; c gives the per-variant randomness

S = {}
META = {}


PHYSICAL = {"Footsteps", "Work", "Breaking", "Building", "Fights", "World", "Animals"}
IN_TUNE = {"die", "grow", "love", "collect", "orb", "craft"}      # these carry notes: never re-pitched
SIZES = [1.0, 0.93, 1.06, 0.97, 1.03, 0.9]                        # variant k is this much smaller / larger


def sfx(name, cat, when, variants=1, loud=0.5, change="remastered"):
    def deco(fn):
        S[name] = fn
        META[name] = {"cat": cat, "when": when, "variants": variants, "loud": loud, "change": change,
                      "vary": cat in PHYSICAL and name not in IN_TUNE}
        return fn
    return deco


def resize(y, factor):
    """A slightly bigger or smaller object: every resonance and the timing scale together."""
    if factor == 1.0:
        return y
    return np.interp(np.arange(0, len(y) - 1, factor), np.arange(len(y)), y)


# --- footsteps --------------------------------------------------------------------------------

@sfx("step", "Footsteps", "walking on grass and soil", 4, 0.14, "reworked")
def _(c):
    n = N(0.22)
    force = grf(n, soft=1.6, c=c)
    blades = phism(c, n, force, rate=2500, freq=3200, decay=0.0012, jitter=0.5)   # grass blades bending, snapping
    crumbs = phism(c, n, force, rate=500, freq=900, decay=0.003)                 # crumbs of soil
    earth = fft_filter(np.diff(force, prepend=0), bp(60, 240))                 # the soft earth gives a little (audible band only)
    return 0.55 * blades + 0.45 * crumbs + 0.5 * earth / (np.abs(earth).max() + 1e-9)


@sfx("tock", "Footsteps", "walking on wooden floors, bridges and boats", 4, 0.16)
def _(c):
    n = N(0.24)
    force = grf(n, soft=1.3, c=c)
    boards = force_modes(c, n, force, 140, 900, count=6, tau=(0.012, 0.035))   # a plank floor: low, short
    noise = contact_noise(c, n, force, 500, 4000)
    return boards + 0.5 * noise


@sfx("click", "Footsteps", "walking on cobblestone", 4, 0.14)
def _(c):
    n = N(0.22)
    force = grf(n, soft=1.1, c=c)
    stone = force_modes(c, n, force, 500, 2500, count=6, tau=(0.002, 0.006))   # set stones barely ring
    noise = contact_noise(c, n, force, 900, 7000)                                # the sole meeting hard stone
    grit = phism(c, n, force, rate=900, freq=4500, decay=0.0007, jitter=0.4)    # sand between the cobbles
    scuff = fractal_noise(c, n, 1.0) * np.exp(-((tt(n) - 0.11) / 0.02) ** 2)    # a little brush at toe-off
    return 0.45 * stone + 0.8 * noise + 0.35 * grit + 0.2 * fft_filter(scuff, bp(500, 6000))


@sfx("wade", "Footsteps", "wading through shallow water", 4, 0.16)
def _(c):
    n = N(0.45)
    force = grf(n, soft=2.5, toe=0.1, c=c)
    push = fft_filter(c.noise(n), lp(1800)) * force                              # exciter x low-passed noise
    y = 0.6 * push
    for _ in range(int(c.u(10, 18))):                                            # bubbles, radii by a power law
        r = 1.0 * c.u(0.05, 1) ** (-1 / 1.6)
        place(y, bubble(c, min(r, 8), amp=c.u(0.05, 0.25)), c.u(0.01, 0.3))
    return y


@sfx("thud", "Footsteps", "landing after a hop down a level", 3, 0.3, "reworked")
def _(c):
    n = N(0.25)
    force = grf(n, toe=0.012, toe_amp=0.9, soft=1.4, c=c)                       # a jump: heel and toe land together
    earth = fft_filter(np.diff(force, prepend=0), bp(55, 200))
    body = impact(c, n, "body", size=c.u(1.0, 1.3))
    crunch = phism(c, n, force, rate=1500, freq=1500, decay=0.002)
    return earth / (np.abs(earth).max() + 1e-9) + 0.5 * body + 0.35 * crunch


# --- working the land ------------------------------------------------------------------------

@sfx("chop", "Work", "an axe strike on a tree or wooden block", 4, 0.5)
def _(c):
    n = N(0.32)
    wood = impact(c, n, "wood", size=c.u(0.8, 1.1), hardness=2.0)
    bite = fft_filter(c.noise(n), bp(1500, 7000)) * env_exp(n, 0.006, 0.0005)
    split = grains(c, n, 12, 2, 1200, 6000, decay=0.02)
    return wood + 0.6 * bite + 0.4 * split


@sfx("mine", "Work", "a pickaxe strike on stone", 4, 0.45)
def _(c):
    n = N(0.45)
    rock = impact(c, n, "stone", size=c.u(0.7, 1.0), hardness=2.5)
    ring = impact(c, n, "metal", size=c.u(0.9, 1.1), hardness=2.0) * env_exp(n, 0.04)   # the pick head rings briefly
    grit = phism(c, n, env_exp(n, 0.05, 0.001), rate=1500, freq=3500, decay=0.0008)      # chips fly
    return rock + 0.08 * ring + 0.45 * grit


@sfx("dig", "Work", "a shovel in soil, digging a hole", 4, 0.4)
def _(c):
    n = N(0.35)
    thunk = fft_filter(c.noise(n), lp(350)) * env_exp(n, 0.05, 0.004)
    soil = grains(c, n, 40, 10, 250, 1800, decay=0.07)
    return thunk * 1.3 + soil * 0.9


@sfx("rustle", "Work", "cutting grass, picking flowers and plants, leaves", 4, 0.3, "reworked")
def _(c):
    n = N(0.4)
    lo = c.u(1200, 1900)
    swish = grains(c, n, int(c.u(90, 140)), 5, lo, lo * 4, decay=c.u(0.07, 0.11))     # densest at the cut, then thinning
    stems = phism(c, n, env_exp(n, 0.03, 0.001), rate=500, freq=c.u(1800, 2600), decay=0.0015)   # stalks snapping
    return swish + 0.35 * stems


@sfx("swing", "Work", "swinging a tool or a weapon", 3, 0.25)
def _(c):
    n = N(0.28)
    curve = np.sin(np.linspace(0, np.pi, n)) ** 0.7
    k = c.u(0.85, 1.2)                                                        # a heavier or a lighter tool
    return swept_noise(c, n, 500 * k, 2400 * k, 0.35, curve=np.linspace(0, 1, n)) * curve


@sfx("punch", "Work", "hitting a tree or a rock with bare hands", 3, 0.3, "new")
def _(c):
    n = N(0.22)
    hand = impact(c, n, "body", size=c.u(0.7, 0.9), hardness=1.3)
    trunk = impact(c, n, "wood", size=c.u(1.6, 2.0), hardness=0.5, damp=3.0)   # the thing barely answers
    return hand + 0.45 * trunk


# --- things break ------------------------------------------------------------------------------

@sfx("snap", "Breaking", "a wooden block or fence breaks", 3, 0.55)
def _(c):
    n = N(0.5)
    crack = grains(c, n, 80, 2, 700, 6000, decay=0.05)
    body = impact(c, n, "wood", size=c.u(1.2, 1.6), hardness=1.5)
    y = crack * 1.2 + body * 0.8
    place(y, impact(c, N(0.2), "wood", size=2.0) * 0.5, c.u(0.12, 0.2))   # a piece lands
    return y


@sfx("crumble", "Breaking", "stone breaks; digging down into a cave", 3, 0.55)
def _(c):
    n = N(0.8)
    y = np.zeros(n)
    at = 0.0
    for k in range(12):   # a cascade of stones of all sizes, slowing down
        place(y, impact(c, N(0.12), "stone", size=c.u(0.5, 1.8), hardness=c.u(0.8, 2)) * c.u(0.4, 1) * (1 - k * 0.05), at)
        at += c.u(0.015, 0.06) * (1 + k * 0.08)
    rumble = fft_filter(c.noise(n), lp(180)) * env_exp(n, 0.2, 0.02)
    return y + 0.7 * rumble + 0.4 * grains(c, n, 70, 4, 1500, 6000, decay=0.2)


@sfx("creak", "Breaking", "a tree starts to fall", 2, 0.4, "reworked")
def _(c):
    dur = c.u(0.8, 1.0)
    n = N(dur)
    t = tt(n)
    rate = c.u(22, 34) + c.u(35, 55) * np.sin(np.pi * t / dur) + 8 * np.sin(2 * np.pi * c.u(5, 9) * t)   # stick-slip
    ph = np.cumsum(rate) / SR
    pulses = (np.diff(np.floor(ph), prepend=0) > 0).astype(float)
    k = c.u(0.85, 1.2)                                                        # each trunk has its own voice
    wood = sum(fft_filter(pulses, lambda f, F=F: 1 / (1 + ((f - F) / (F / 9)) ** 2)) for F in (380 * k, 760 * k, 1250 * k))
    fibres = grains(c, n, 30, 2, 900, 5000, spread=dur) * 0.15               # fibres tearing
    return (wood / (np.abs(wood).max() + 1e-9) + fibres) * np.clip(t / 0.02, 0, 1) * np.clip((dur - t) / 0.25, 0, 1) ** 0.5


@sfx("fallthud", "Breaking", "a tree hits the ground", 2, 0.48)
def _(c):
    n = N(1.0)
    trunk = impact(c, n, "wood", size=3.5, hardness=0.6)                # a big, low log
    ground = impact(c, n, "dirt", size=2.5) * 1.2
    shake = fft_filter(c.noise(n), bp(80, 700)) * env_exp(n, 0.09, 0.003)
    y = trunk + ground + 0.6 * shake
    place(y, impact(c, N(0.3), "wood", size=2.5, hardness=0.5) * 0.35, 0.16)   # a small bounce
    return fft_filter(y + 0.14 * grains(c, n, 160, 5, 1800, 6000, decay=0.25), hp(45))


# --- building ----------------------------------------------------------------------------------

@sfx("place", "Building", "fallback: any other wooden thing is set down", 3, 0.4)
def _(c):
    n = N(0.3)
    knock = impact(c, n, "wood", size=c.u(1.3, 1.7), hardness=0.9)
    settle = fft_filter(c.noise(n), bp(300, 2000)) * env_exp(n, 0.02, 0.002)
    return knock + 0.35 * settle


@sfx("clack", "Building", "fallback: any other stone thing is set down", 3, 0.38)
def _(c):
    n = N(0.28)
    y = impact(c, n, "stone", size=c.u(1.3, 1.7), hardness=1.0, damp=6.0)
    place(y, impact(c, N(0.1), "stone", size=c.u(1.4, 1.8), damp=6.0) * 0.4, c.u(0.025, 0.045))   # it rocks and settles
    return y + 0.3 * phism(c, n, env_exp(n, 0.03, 0.001), rate=600, freq=3500, decay=0.0008)   # grit underneath


@sfx("plant", "Building", "planting a seed or a sapling", 2, 0.35)
def _(c):
    n = N(0.4)
    y = impact(c, n, "dirt", size=0.8) * 0.9                       # pressing soil
    place(y, grains(c, N(0.2), 25, 6, 300, 2500, decay=0.05) * 0.6, 0.0)
    place(y, impact(c, N(0.2), "dirt", size=1.0) * 0.5, c.u(0.12, 0.18))   # a second pat
    return y


@sfx("place_post", "Building", "fence, gate, sign or flag: a wooden post is tapped into the ground", 3, 0.42)
def _(c):
    n = N(0.45)
    y = impact(c, n, "dirt", size=1.1) * 0.8                                   # the post bites into the soil
    place(y, impact(c, N(0.15), "wood", size=c.u(1.2, 1.5), hardness=0.8, damp=2.5) * 0.9, 0.0)    # tap
    place(y, impact(c, N(0.15), "wood", size=c.u(1.2, 1.5), hardness=0.8, damp=2.5) * 0.6, c.u(0.15, 0.19))   # tap
    return y + 0.4 * grains(c, n, 20, 6, 250, 2000, decay=0.06)


@sfx("place_planks", "Building", "a wooden wall or a door goes up: boards set, one nail", 3, 0.45)
def _(c):
    n = N(0.5)
    y = impact(c, n, "hollow", size=c.u(1.5, 1.8), hardness=0.8)               # boards land against the frame
    scrape = fft_filter(c.noise(N(0.07)), bp(400, 2500)) * np.sin(np.linspace(0, np.pi, N(0.07)))
    place(y, scrape * 0.25, 0.05)
    nail = impact(c, N(0.15), "wood", size=0.6, hardness=2.2) + 0.06 * impact(c, N(0.15), "metal", size=1.4, hardness=2)
    place(y, nail * 0.6, c.u(0.2, 0.24))
    return y


@sfx("place_stone", "Building", "a stone wall or a well: a heavy stone is set on stone", 3, 0.45)
def _(c):
    n = N(0.45)
    y = impact(c, n, "stone", size=c.u(2.2, 2.8), hardness=0.7, damp=3.5)      # big, low, dense, resting on stone
    grind = fft_filter(c.noise(N(0.12)), bp(500, 4000)) * np.sin(np.linspace(0, np.pi, N(0.12)))
    place(y, grind * 0.2, 0.03)
    for _ in range(3):                                                           # loose grit settles
        place(y, impact(c, N(0.05), "stone", size=c.u(0.4, 0.6), hardness=1.5) * c.u(0.08, 0.18), c.u(0.06, 0.2))
    return y


@sfx("place_furniture", "Building", "a workbench, table, chair, chest, mailbox, clock, coop or trough is set down on its legs", 3, 0.4)
def _(c):
    n = N(0.45)
    y = impact(c, n, "hollow", size=c.u(1.1, 1.35), hardness=0.9)              # first legs touch down
    place(y, impact(c, N(0.25), "hollow", size=c.u(1.15, 1.4), hardness=0.9) * c.u(0.55, 0.75), c.u(0.03, 0.05))
    scoot = fft_filter(c.noise(N(0.1)), bp(250, 1400)) * np.sin(np.linspace(0, np.pi, N(0.1)))
    place(y, scoot * 0.18, 0.09)                                                 # a little nudge into place
    return y


@sfx("place_soft", "Building", "a rug, picnic blanket, bed, hay bale or basket: something soft is laid down", 3, 0.3)
def _(c):
    n = N(0.45)
    whump = fft_filter(c.noise(n), lp(350)) * env_exp(n, 0.06, 0.012)           # air pushed out from under it
    cloth = swept_noise(c, n, 900, 2600, 0.45) * env_exp(n, 0.09, 0.02)
    fibres = grains(c, n, 40, 5, 1200, 5000, decay=0.08)                          # straw, wicker, a crease of fabric
    return whump * 1.2 + cloth * 0.35 + fibres * 0.25


@sfx("place_pot", "Building", "a potted plant is set down", 2, 0.35)
def _(c):
    n = N(0.4)
    y = impact(c, n, "ceramic", size=c.u(1.0, 1.2), hardness=1.0)
    place(y, grains(c, N(0.2), 20, 6, 300, 2500, decay=0.05) * 0.35, 0.02)      # soil shifts inside
    return y


@sfx("place_fire", "Building", "a campfire is built: logs and stones are stacked", 2, 0.4)
def _(c):
    n = N(0.6)
    y = np.zeros(n)
    at = 0.0
    for k in range(4):                                                           # logs tumble into the ring
        place(y, impact(c, N(0.15), "wood", size=c.u(1.4, 2.2), hardness=0.9) * c.u(0.5, 1.0), at)
        at += c.u(0.05, 0.11)
    for _ in range(2):
        place(y, impact(c, N(0.08), "stone", size=c.u(1.0, 1.4), hardness=1.2) * 0.4, c.u(0.0, 0.3))
    return y


@sfx("place_boat", "Building", "a boat is put on the water", 2, 0.45)
def _(c):
    n = N(0.9)
    hull = impact(c, n, "hollow", size=c.u(2.4, 2.9), hardness=0.6, damp=1.5)   # a big hollow body, the water damps it
    y = fft_filter(hull, hp(55)) * 0.8
    place(y, S["water"](c) * 0.6, 0.01)
    lap = fft_filter(c.noise(N(0.3)), bp(300, 1500)) * np.sin(np.linspace(0, np.pi, N(0.3)))
    place(y, lap * 0.15, 0.35)                                                   # water laps against the hull
    return y


@sfx("place_floor", "Building", "planks laid as a floor or a bridge", 3, 0.35)
def _(c):
    n = N(0.4)
    y = impact(c, n, "hollow", size=c.u(1.6, 2.0), hardness=1.1)                # a board falls flat
    place(y, impact(c, N(0.2), "hollow", size=c.u(1.7, 2.1), hardness=1.1) * 0.5, c.u(0.07, 0.1))   # and the next
    return y


@sfx("place_path", "Building", "cobbles are set into a path", 3, 0.35, "reworked")
def _(c):
    n = N(0.4)
    energy = np.clip(tt(n) / 0.004, 0, 1) * np.exp(-tt(n) / 0.07)             # starts on the first stone
    clatter = phism(c, n, energy, rate=120, freq=1800, decay=0.002, jitter=0.5)   # stones knocking each other
    grit = phism(c, n, energy, rate=900, freq=4000, decay=0.0007)
    bed = fft_filter(c.noise(n), bp(70, 300)) * energy                          # bedded into sand
    return clatter + 0.35 * grit + 0.5 * bed / (np.abs(bed).max() + 1e-9)


@sfx("fill_dirt", "Building", "earth is shovelled into a hole, a field or the water", 2, 0.35)
def _(c):
    n = N(0.5)
    pour = grains(c, n, 120, 8, 200, 1800, spread=0.3) * np.sin(np.pi * np.clip(tt(n) / 0.35, 0, 1))
    thump = fft_filter(c.noise(n), lp(250)) * env_exp(n, 0.05, 0.01)
    return pour + 0.8 * thump


@sfx("gate", "Building", "a gate or a door swings open", 2, 0.35, "reworked")
def _(c):
    n = N(0.55)
    t = tt(n)
    rate = c.u(45, 65) + c.u(45, 75) * t / 0.55                             # each hinge squeaks its own way
    ph = np.cumsum(rate) / SR
    pulses = (np.diff(np.floor(ph), prepend=0) > 0).astype(float)
    hinge = sum(fft_filter(pulses, lambda f, F=F: 1 / (1 + ((f - F) / (F / 12)) ** 2)) for F in np.array([900, 1800, 2600]) * c.u(0.85, 1.2))
    hinge *= np.sin(np.pi * np.clip(t / 0.4, 0, 1))
    latch = np.roll(modes(n, [1600, 3300], [0.01, 0.006], [0.6, 0.3]), N(0.0))
    return hinge * 0.8 + latch


@sfx("chest", "Building", "opening a chest", 2, 0.4)
def _(c):
    n = N(0.7)
    y = np.zeros(n)
    place(y, S["gate"](c)[: N(0.4)] * 0.45, 0)
    place(y, impact(c, N(0.3), "hollow", size=1.3, hardness=0.9), 0.36)   # the lid falls open on its hinge
    return y


@sfx("write", "Building", "writing on a sign or a letter", 2, 0.25, "reworked")
def _(c):
    n = N(0.7)
    y = np.zeros(n)
    at = 0.0
    k = c.u(0.7, 1.35)                                    # a pencil, a quill, a piece of chalk
    while at < 0.6:   # strokes
        sn = N(c.u(0.05, 0.12))
        stroke = fft_filter(c.noise(sn), bp(1800 * k, 6000 * k)) * np.sin(np.linspace(0, np.pi, sn))
        place(y, stroke * c.u(0.5, 1), at)
        at += c.u(0.07, 0.15)
    return y


# --- getting things -------------------------------------------------------------------------

@sfx("collect", "Items", "picking up an item", 3, 0.34)
def _(c):
    lo, hi = c.pick([("A5", "D6"), ("F#5", "A5"), ("D6", "F#6")])
    n = N(1.2)
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
    return impact(c, n, "dirt", size=0.7, hardness=1.5) + 0.5 * grains(c, n, 15, 4, 800, 4000, decay=0.03)


@sfx("eat", "Items", "eating: two crunchy bites", 3, 0.3, "new")
def _(c):
    n = N(0.5)
    y = np.zeros(n)
    for k in range(2):
        bn = N(c.u(0.07, 0.1))
        crunch = grains(c, bn, int(c.u(25, 40)), 2, 900, 6500, decay=0.02)       # the food fractures
        mouth = fft_filter(c.noise(bn), bp(300, 1400)) * env_exp(bn, 0.03, 0.004)   # heard through a closed mouth
        place(y, crunch + 0.5 * mouth, k * c.u(0.17, 0.22))
    return y


@sfx("loot", "Items", "a dropped item lands and bounces", 3, 0.25)
def _(c):
    n = N(0.4)
    y = np.zeros(n)
    at, v = 0.0, 1.0
    for k in range(3):
        sn = N(0.06)
        hitf = np.exp(-((tt(sn) - 0.004) / 0.003) ** 2)
        place(y, (impact(c, sn, "dirt", size=0.6, hardness=1.5) + 0.4 * phism(c, sn, hitf, 1500, 3000, 0.001)) * v, at)
        at += 0.11 * (0.6 ** k)
        v *= 0.45
    return y


@sfx("craft", "Items", "crafting something at a workbench", 2, 0.4)
def _(c):
    n = N(1.9)
    y = np.zeros(n)
    for k in range(3):   # tap tap tap of tools
        place(y, impact(c, N(0.1), "wood", size=0.8, hardness=1.6) * 0.6, k * 0.09)
    for k, note in enumerate(("D5", "A5", "D6")):
        place(y, mallet(note, 0.7, n=N(0.7)) * (0.7 + 0.15 * k), 0.3 + k * 0.08)
    return y + 0.06 * grains(c, n, 25, 3, 6000, 12000, spread=0.6)


# --- progress -------------------------------------------------------------------------------

@sfx("chime", "Progress", "a goal completed (it plays the music's own melody cell)", 1, 0.4)
def _(c):
    n = N(2.8)
    y = np.zeros(n)
    for at, note, v in ((0, "F#6", 0.9), (0.14, "E6", 0.7), (0.28, "F#6", 0.8), (0.42, "A6", 1.0)):
        place(y, bell(note, 1.3, n=N(1.3)) * v, at)
    return y


@sfx("levelup", "Progress", "you reach a new level", 1, 0.5)
def _(c):
    n = N(3.4)
    y = np.zeros(n)
    for k, note in enumerate(("D5", "F#5", "A5", "D6", "E6", "F#6")):
        place(y, mallet(note, 0.9, n=N(0.9)) * 0.8, k * 0.075)
    pad = sum(np.sin(2 * np.pi * hz(nn) * tt(n)) for nn in ("D5", "A5", "F#6"))
    swell = np.sin(np.pi * np.clip((tt(n) - 0.35) / 1.9, 0, 1)) ** 2
    return y + 0.12 * pad * swell + 0.05 * grains(c, n, 40, 3, 6000, 12000, spread=1.6)


@sfx("mail", "Progress", "a letter arrives in your mailbox", 1, 0.35)
def _(c):
    n = N(2.2)
    paper = swept_noise(c, N(0.25), 2000, 5000, 0.5) * np.sin(np.linspace(0, np.pi, N(0.25)))
    y = np.zeros(n)
    place(y, paper * 0.4, 0)
    place(y, bell("D6", 1.0, n=N(1.0)), 0.2)
    place(y, bell("A6", 0.9, n=N(0.9)) * 0.8, 0.36)
    return y


# --- bodies and fights --------------------------------------------------------------------------

@sfx("hit", "Fights", "landing a blow", 3, 0.5)
def _(c):
    n = N(0.25)
    body = impact(c, n, "body", size=c.u(0.8, 1.1), hardness=1.5)
    slap = fft_filter(c.noise(n), bp(700, 4500)) * env_exp(n, 0.012, 0.0005)
    return body + 0.7 * slap


@sfx("hurt", "Fights", "you take damage", 2, 0.45)
def _(c):
    n = N(0.35)
    body = impact(c, n, "body", size=1.4, hardness=1.2)
    muffle = fft_filter(c.noise(n), bp(150, 900)) * env_exp(n, 0.05, 0.002)
    return body + 0.5 * muffle


@sfx("die", "Fights", "you die (gentle, not scary)", 1, 0.4)
def _(c):
    n = N(3.6)
    y = np.zeros(n)
    for k, note in enumerate(("A5", "F#5", "D5", "A4")):
        place(y, bell(note, 1.6, n=N(1.6)) * (0.9 - 0.12 * k), k * 0.32)
    return fft_filter(y, lp(3500))


@sfx("poof", "Fights", "a creature vanishes in a puff of smoke", 2, 0.35)
def _(c):
    n = N(0.6)
    puff = swept_noise(c, n, 2500, 350, 0.5) * env_exp(n, 0.15, 0.008)
    pop = impact(c, N(0.08), "body", size=0.5) * 0.4
    return puff + np.pad(pop, (0, n - len(pop)))


@sfx("gloom", "Fights", "a gloom attacks at night: a breathy, low growl", 2, 0.4, "reworked")
def _(c):
    dur = [0.9, 1.15][c.v % 2]
    n = N(dur)
    t = tt(n)
    f0 = [55, 46][c.v % 2] + 12 * np.sin(2 * np.pi * c.u(2.5, 3.5) * t) * np.exp(-t / 0.4) + c.u(-3, 3)
    growl = voice(n, f0, lambda t: [(450, 1.0), (900, 0.5)], 180, harmonics=60, c=c)
    breath = fft_filter(c.noise(n), bp(200, 1400)) * 0.3
    am = 0.7 + 0.3 * np.sin(2 * np.pi * c.u(19, 27) * t)
    env = np.clip(t / 0.03, 0, 1) * np.clip((dur - t) / 0.3, 0, 1) ** 0.6
    return fft_filter(growl * 0.35 * am + breath, lp(1800)) * env


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
        buk = voice(bn, f0, lambda t: [(1300, 1.0), (2600, 0.6)], 350, harmonics=14, c=c)
        place(y, buk * np.sin(np.pi * np.clip(t / 0.07, 0, 1)), k * c.u(0.1, 0.14))
    return y


@sfx("squawk", "Animals", "a chicken is hit or startled", 3, 0.32, "new")
def _(c):
    dur = c.u(0.2, 0.28)
    n = N(dur)
    t = tt(n)
    x = t / dur
    f0 = c.u(780, 900) * (1 + 0.25 * np.sin(np.pi * x)) * (1 - 0.25 * x)
    y = voice(n, f0, lambda t: [(1500, 1.0), (2900, 0.7)], 400, harmonics=12, c=c)
    y *= 1 - 0.5 * (0.5 + 0.5 * np.sin(2 * np.pi * c.u(60, 80) * t))          # raspy
    return y * np.sin(np.pi * np.clip(x, 0, 1)) ** 0.6


@sfx("chirp", "Animals", "a chick peeps; an egg hatches", 4, 0.25)
def _(c):
    n = N(0.35)
    y = np.zeros(n)
    for k in range(2):
        bn = N(0.06)
        t = tt(bn)
        f = c.u(3200, 4000) * (1 - 0.12 * np.sin(np.pi * t / 0.06))
        ph = 2 * np.pi * np.cumsum(f) / SR
        place(y, (np.sin(ph) + 0.15 * np.sin(2 * ph)) * np.sin(np.pi * t / 0.06) ** 1.5, k * c.u(0.1, 0.13))
    return y


@sfx("moo", "Animals", "a cow moos (petted, milked, fed, hit)", 3, 0.4, "reworked")
def _(c):
    dur = [1.25, 0.95, 1.45][c.v % 3]
    n = N(dur)
    t = tt(n)
    x = t / dur
    base = [105, 125, 92][c.v % 3] * c.u(0.97, 1.03)
    f0 = base * (0.82 + 0.38 * np.sin(np.pi * np.clip(x * 1.15, 0, 1)) ** 1.5 - 0.12 * x)   # scoops up, sags at the end
    mouth = np.clip((x - 0.12) / 0.25, 0, 1) * (1 - 0.5 * np.clip((x - 0.8) / 0.2, 0, 1))   # "mm" -> "ooo" -> closing
    vowel = lambda t: [(250 + 230 * mouth, 1.0), (650 + 350 * mouth, 0.25 + 0.45 * mouth), (2300, 0.03 + 0.1 * mouth)]
    y = voice(n, f0, vowel, 120, harmonics=60, c=c)
    ph = 2 * np.pi * np.cumsum(f0) / SR
    fry = (1 - np.clip(x / 0.18, 0, 1)) + np.clip((x - 0.85) / 0.15, 0, 1)   # rough at the start and the very end
    y *= 1 - 0.45 * fry * (0.5 + 0.5 * np.sin(ph / 2))                       # every other pulse weaker
    breath = fft_filter(c.noise(n), bp(500, 3000)) * (0.02 + 0.1 * np.clip((x - 0.75) / 0.25, 0, 1))
    env = np.clip(t / 0.06, 0, 1) * np.clip((dur - t) / 0.18, 0, 1) ** 0.7
    return (y / (np.abs(y).max() + 1e-9) + breath) * env


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
    n = N(1.4)
    y = np.zeros(n)
    for k, note in enumerate(("A5", "D6") if c.v == 0 else ("F#5", "B5")):
        place(y, bell(note, 0.7, n=N(0.7)) * 0.8, k * 0.09)
    return y + 0.05 * grains(c, n, 15, 3, 6000, 12000, spread=0.4)


# --- world -----------------------------------------------------------------------------------

@sfx("water", "World", "a splash: boarding or mooring a boat, something falls in", 3, 0.4, "reworked")
def _(c):
    n = N(0.7)
    slap = fft_filter(c.noise(n), bp(400, 5000)) * env_exp(n, 0.035, 0.002)           # the surface is hit
    crown = swept_noise(c, n, 3000, 900, 0.5) * env_exp(n, 0.14, 0.02)               # water thrown up, falling back
    y = 0.8 * slap + 0.6 * crown
    for _ in range(int(c.u(22, 34))):                                               # bubbles, radii by a power law
        r = min(9, 1.0 * c.u(0.04, 1) ** (-1 / 1.6))
        place(y, bubble(c, r, amp=c.u(0.08, 0.3)), c.u(0.03, 0.45))
    return y


@sfx("pour", "World", "watering crops: a gentle stream from the can", 2, 0.3, "new")
def _(c):
    n = N(0.8)
    t = tt(n)
    env = np.clip(t / 0.05, 0, 1) * np.clip((0.8 - t) / 0.25, 0, 1)
    y = np.zeros(n)
    for _ in range(int(c.u(110, 150))):
        r = min(3.0, 0.5 * c.u(0.03, 1) ** (-1 / 2.2))                               # mostly tiny bubbles
        at = c.u(0, 0.7)
        place(y, bubble(c, r, amp=c.u(0.1, 0.5) * env[int(at * SR)]), at)
    spray = fft_filter(c.noise(n), bp(2500, 9000)) * env * 0.08
    patter = phism(c, n, env, rate=400, freq=700, decay=0.004) * 0.25               # drops landing on soil
    return y / (np.abs(y).max() + 1e-9) + spray + patter


@sfx("fill", "World", "filling a bucket at the water", 2, 0.4, "new")
def _(c):
    n = N(0.9)
    y = np.zeros(n)
    dunk = swept_noise(c, N(0.25), 2500, 800, 0.5) * env_exp(N(0.25), 0.07, 0.004)
    place(y, dunk * 0.5, 0)
    at = 0.08
    for k in range(int(c.u(4, 6))):                                                 # glug, glug: big bubbles, higher as it fills
        place(y, bubble(c, c.u(7, 10) * (1 - 0.08 * k), amp=0.9 - 0.1 * k), at)
        at += c.u(0.09, 0.14)
    for _ in range(25):
        place(y, bubble(c, min(4, 0.8 * c.u(0.05, 1) ** (-1 / 1.8)), amp=c.u(0.05, 0.2)), c.u(0.02, 0.7))
    return y


@sfx("whoosh", "World", "lighting a fire: the flame catches", 2, 0.4, "reworked")
def _(c):
    n = N(0.8)
    curve = np.clip(tt(n) / c.u(0.25, 0.4), 0, 1) ** 0.6
    swell = swept_noise(c, n, c.u(180, 260), c.u(1500, 2200), 0.45, curve=curve)
    return swell * np.clip(tt(n) / 0.03, 0, 1) * np.clip((0.8 - tt(n)) / 0.45, 0, 1) ** 0.8


@sfx("crackle", "World", "fire burning, something burns", 3, 0.3, "reworked")
def _(c):
    n = N(1.2)
    t = tt(n)
    flick = fft_filter(c.noise(n), lp(8))
    lap = fft_filter(c.noise(n), bp(70, 450)) * (0.6 + 0.4 * flick / (np.abs(flick).max() + 1e-9))   # flames lapping
    hiss = fft_filter(c.noise(n), bp(3000, 10000)) * 0.04                                           # sap and steam
    pops = grains(c, n, int(c.u(18, 32)), 2, 1200, 9000, spread=1.1, amp_jitter=0.9)
    env = np.clip(t / 0.01, 0, 1) * np.clip((1.2 - t) / 0.3, 0, 1)
    return (0.3 * lap / (np.abs(lap).max() + 1e-9) + hiss + pops) * env


@sfx("flood", "World", "water spreads over the ground", 1, 0.35, "reworked")
def _(c):
    n = N(1.4)
    rush = fft_filter(c.noise(n), bp(300, 3000)) * np.clip(tt(n) / 0.03, 0, 1) * np.clip((1.4 - tt(n)) / 0.6, 0, 1)
    y = rush * 0.5
    for _ in range(30):
        place(y, bubble(c, min(8, 1.2 * c.u(0.05, 1) ** (-1 / 1.6)), amp=c.u(0.08, 0.3)), c.u(0.05, 1.2))
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

@sfx("say", "People", "someone nearby talks: a soft babble of two to four syllables", 5, 0.18, "reworked")
def _(c):
    vowels = {"a": (850, 1400), "e": (500, 1900), "i": (320, 2300), "o": (480, 900), "u": (350, 800)}
    notes = ["D4", "E4", "F#4", "A4", "B4"]                                     # the music's notes, at speaking pitch
    y = np.zeros(N(0.6))
    at = 0.0
    for k in range([3, 2, 4, 3, 2][c.v % 5]):
        bn = N(c.u(0.055, 0.08))
        t = tt(bn)
        f1, f2 = vowels[c.pick("aeiou")]
        f0 = np.full(bn, hz(c.pick(notes))) * (1 + 0.04 * np.sin(np.pi * t / (bn / SR)))
        syl = voice(bn, f0, lambda t, f1=f1, f2=f2: [(f1, 1.0), (f2, 0.5)], 220, harmonics=24, c=c)
        place(y, syl * np.sin(np.pi * t / (bn / SR)) ** 0.8, at)
        at += bn / SR + c.u(0.005, 0.02)
    return y


@sfx("shout", "People", "someone shouts", 2, 0.3, "reworked")
def _(c):
    n = N(0.4)
    y = np.zeros(n)
    for k, note in enumerate([("A4", "D5"), ("F#4", "B4")][c.v % 2]):           # a call: two rising syllables
        bn = N(c.u(0.13, 0.16))
        t = tt(bn)
        f0 = np.full(bn, hz(note)) * (1 + 0.05 * t / (bn / SR))
        syl = voice(bn, f0, lambda t: [(800, 1.0), (1300, 0.6), (2600, 0.25)], 300, harmonics=30, c=c)
        place(y, syl * np.sin(np.pi * t / (bn / SR)) ** 0.6, k * c.u(0.13, 0.16))
    return y


@sfx("give", "People", "someone gives you something", 1, 0.35)
def _(c):
    n = N(1.7)
    paper = swept_noise(c, N(0.2), 3000, 6000, 0.5) * np.sin(np.linspace(0, np.pi, N(0.2)))
    y = np.zeros(n)
    place(y, paper * 0.4, 0)
    for k, note in enumerate(("B5", "D6", "F#6")):
        place(y, mallet(note, 0.6, n=N(0.6)) * 0.8, 0.12 + k * 0.07)
    return y


@sfx("join", "People", "someone arrives in the world (a wind chime)", 1, 0.25)
def _(c):
    n = N(3.2)
    y = np.zeros(n)
    for k in range(6):
        place(y, bell(c.pick(PENTA_HIGH), 1.4, n=N(1.4)) * c.u(0.4, 0.8), k * c.u(0.08, 0.16))
    return fft_filter(y, lp(6000))


@sfx("leave", "People", "someone falls asleep (leaves)", 1, 0.22)
def _(c):
    n = N(2.6)
    y = np.zeros(n)
    for k, note in enumerate(("A6", "F#6", "D6")):
        place(y, bell(note, 1.2, n=N(1.2)) * (0.7 - 0.12 * k), k * 0.18)
    return fft_filter(y, lp(5000))


@sfx("ui", "Interface", "clicking a button, picking a hotbar slot, switching tabs", 3, 0.2)
def _(c):
    n = N(0.12)
    f = hz(["D6", "E6", "A6"][c.v % 3])
    return modes(n, [f, f * 2.7], [0.03, 0.01], [1, 0.3]) + 0.15 * fft_filter(c.noise(n), bp(2000, 8000)) * env_exp(n, 0.003)


@sfx("open", "Interface", "opening a panel (crafting, mailbox, chest view)", 1, 0.25, "reworked")
def _(c):
    n = N(0.9)
    slide = swept_noise(c, n, 1500, 4000, 0.5) * np.sin(np.pi * np.clip(tt(n) / 0.25, 0, 1)) * (tt(n) < 0.25) * 0.3
    y = slide
    place(y, mallet("A5", 0.4, n=N(0.35)) * 0.6, 0.0)                          # the note lands with the click
    place(y, mallet("D6", 0.4, n=N(0.35)) * 0.6, 0.07)
    return y


@sfx("close", "Interface", "closing a panel", 1, 0.22, "reworked")
def _(c):
    n = N(0.9)
    slide = swept_noise(c, n, 4000, 1500, 0.5) * np.sin(np.pi * np.clip(tt(n) / 0.25, 0, 1)) * (tt(n) < 0.25) * 0.3
    y = slide
    place(y, mallet("D6", 0.4, n=N(0.35)) * 0.6, 0.0)
    place(y, mallet("A5", 0.4, n=N(0.35)) * 0.6, 0.07)
    return y


@sfx("buzz", "Interface", "something can't be done (soft, never harsh)", 1, 0.25)
def _(c):
    n = N(0.35)
    y = np.zeros(n)
    for k, f in enumerate((180, 150)):
        place(y, modes(N(0.12), [f, f * 2.3], [0.04, 0.02], [1, 0.3]), k * 0.11)
    return fft_filter(y, lp(1500))


# ------------------------------------------------------------------ render all


def kweight(x):
    """ITU-R BS.1770 K-weighting in the frequency domain: +4 dB shelf above ~1.5 kHz, high-pass at 38 Hz."""
    n = len(x)
    f = np.fft.rfftfreq(n, 1 / SR)
    shelf = 1 + (10 ** (4 / 20) - 1) / (1 + (1681 / np.maximum(f, 1)) ** 2)
    low = 1 / np.sqrt(1 + (38 / np.maximum(f, 1e-3)) ** 4)
    return np.fft.irfft(np.fft.rfft(x) * shelf * low, n)


def loudness(y):
    """Loudest 100 ms as the ear weighs it, in dB."""
    k = kweight(y)
    w = min(len(k), N(0.1))
    c = np.cumsum(np.concatenate([[0], k ** 2]))
    return 10 * np.log10(np.max(c[w:] - c[:-w]) / w + 1e-12)


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
            raw = fn(Ctx(name, v))
            if m["vary"]:
                raw = resize(raw, SIZES[v % len(SIZES)])
            y = finish(raw)
            target = 20 * np.log10(m["loud"]) - 9         # perceived level, set per sound; every variant matches
            y *= 10 ** ((target - loudness(y)) / 20)
            y *= min(1, 0.95 / np.abs(y).max())
            f = f"{name}_{v}.wav"
            write_wav(OUT / f, y)
            files.append(f)
        manifest[name] = {"category": m["cat"], "when": m["when"], "files": files, "change": m["change"]}
        print(f"  {name:9s} {m['cat']:10s} x{m['variants']}  {len(y) / SR:.2f}s")
    (OUT / "sfx.json").write_text(json.dumps(manifest, indent=1))
    (OUT / "map.json").write_text(Path(__file__).with_name("sfx_map.json").read_text())
    print(f"{len(manifest)} sounds, {sum(len(v['files']) for v in manifest.values())} files")
