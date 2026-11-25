"""Sound effects for every game interaction. Fable 5.2 rewrite: new generators, not a remaster.

Pure numpy, stereo. The Opus 5.5 set is frozen in music/opus/sfx.py; this file shares no sound generator with it
apart from the research models both rely on (ground-reaction footsteps, particle collisions, Minnaert bubbles).

What is different in kind:
  * strike(): every material has its own mode structure (a solid log, hollow boards, stone, flesh, soil, a clay pot,
    iron) plus the noisy contact that makes a knock a knock. A soft or long contact cannot excite the highs.
    Hard things chatter for a few milliseconds when set down.
  * space(): the game is outdoors. Opus put every sound in the same small room. Here outdoor sounds are dry, with a
    ground reflection and a faint stereo scatter; only the chest, the cave and the tonal sounds get a room.
  * texture(): leaves, cloth, water wash, fire and air are noise whose bands swell independently, not steady hiss.
  * rewards and interface are played by the soundtrack's own instruments (felt piano, soft analog pluck),
    in the music's notes (D major pentatonic); the goal chime is the music's melody cell.
  * mastering: 55 Hz high-pass, instant start, levels by ITU-R BS.1770 weighting, variants that really differ.

    uv run python music/sfx.py      # writes music/site/sfx/*.wav + sfx.json
"""

from pathlib import Path
import json
import wave
import zlib

import numpy as np

SR = 48000
OUT = Path(__file__).with_name("site") / "sfx"

# ------------------------------------------------------------------ basics


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
    return 440.0 * 2 ** ((midi(note) - 69) / 12)


PENTA = ["D", "E", "F#", "A", "B"]


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


def norm(y):
    return y / (np.abs(y).max() + 1e-9)


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


def env_exp(n, tau, attack=0.001):
    t = tt(n)
    return np.clip(t / attack, 0, 1) * np.exp(-t / tau)


class Ctx:
    """Per-sound random source: same name + variant -> same sound every run."""

    def __init__(self, name, v):
        self.rng = np.random.default_rng(zlib.crc32(f"fable/{name}/{v}".encode()))
        self.v = v

    def noise(self, n):
        return self.rng.standard_normal(n)

    def u(self, a, b):
        return float(self.rng.uniform(a, b))

    def pick(self, seq):
        return seq[int(self.rng.integers(len(seq)))]


# ------------------------------------------------------------------ strike: material models

BAR = (1.0, 2.76, 5.40, 8.93, 13.34)       # free-bar mode ratios: logs, posts, boards


def _bars(c, f1, sets, eta, rolloff=0.8):
    fs, ts, am = [], [], []
    for mult, gain in sets:
        for r in BAR:
            f = f1 * mult * r * c.u(0.97, 1.03)
            if f < 9000:
                fs.append(f)
                ts.append(1 / (np.pi * f * eta * c.u(0.8, 1.3)))    # loss factor: highs die first
                am.append(gain / r ** rolloff)
    return fs, ts, am


def _dense(c, fs, ts, am, lo, hi, count, eta, level):
    """Real objects are not ideal bars: many weak, irregular modes fill the gaps (this is what stops a knock sounding like a xylophone)."""
    for _ in range(count):
        f = np.exp(c.u(np.log(lo), np.log(hi)))
        fs.append(f)
        ts.append(1 / (np.pi * f * eta * c.u(0.7, 1.4)))
        am.append(level * c.u(0.4, 1.0))
    return fs, ts, am


def mat_wood(c, size):        # a solid piece: a log, a trunk, a post
    fs, ts, am = _bars(c, 190 / size * c.u(0.92, 1.08), ((1.0, 1.0), (1.63, 0.6)), 0.1)     # green wood: heavily damped, a tok not a note
    fs, ts, am = _dense(c, fs, ts, am, 300 / size, 4500 / size, 16, 0.1, 0.3)
    return fs, ts, am, [(500, 5000, 0.006, 0.8)]


def mat_plank(c, size):       # boards over air: floors, furniture, chests, hulls
    fs, ts, am = _bars(c, 120 / size * c.u(0.92, 1.08), ((1.0, 1.0), (1.31, 0.7), (1.74, 0.5), (2.2, 0.35)), 0.15)
    fs.append(c.u(85, 130) / size)   # the air inside answers: the hollow "boom"
    ts.append(0.014)
    am.append(0.6)
    fs, ts, am = _dense(c, fs, ts, am, 150 / size, 3500 / size, 28, 0.15, 0.35)   # a plate has a crowd of modes
    return fs, ts, am, [(250, 3500, 0.012, 0.7)]


def mat_stone(c, size):       # dense and resting on the ground: almost no ring, mostly contact
    k = size ** 0.5                 # no pings: a crowd of very short modes under a noisy contact
    fs, ts, am = _dense(c, [], [], [], 700 / k, 7000 / k, 40, 0.09, 0.2)
    return fs, ts, am, [(900 / k, 9000, 0.003, 1.0), (250 / k, 1800, 0.010, 0.6)]


def mat_body(c, size):        # flesh, a sack, a bale
    fs = [70 / size * c.u(0.9, 1.1), 115 / size * c.u(0.9, 1.1), 165 / size * c.u(0.9, 1.1)]
    return fs, [0.03, 0.022, 0.015], [1.0, 0.6, 0.35], [(80, 900, 0.018, 0.7)]


def mat_dirt(c, size):
    fs = [c.u(60, 85) / size, c.u(90, 120) / size]
    return fs, [0.022, 0.016], [1.0, 0.6], [(60, 600, 0.025, 1.0), (800, 3000, 0.010, 0.15)]


def mat_metal(c, size):       # a pick head, a nail, a pail
    f1 = 2300 / size * c.u(0.95, 1.05)
    return [f1, f1 * 2.76, f1 * 5.4], [0.12, 0.08, 0.05], [1.0, 0.6, 0.3], [(3000, 12000, 0.002, 0.4)]


def mat_ceramic(c, size):     # a clay pot full of soil
    f1 = 950 / size * c.u(0.95, 1.05)
    return [f1, f1 * 2.32, f1 * 3.65, f1 * 5.1], [0.014, 0.01, 0.007, 0.005], [1.0, 0.7, 0.4, 0.25], [(1500, 8000, 0.003, 0.7)]


MATS = {"wood": (mat_wood, 0.0012), "plank": (mat_plank, 0.002), "stone": (mat_stone, 0.0006), "body": (mat_body, 0.005),
        "dirt": (mat_dirt, 0.007), "metal": (mat_metal, 0.0003), "ceramic": (mat_ceramic, 0.0006)}


def strike(c, n, mat, size=1.0, hard=1.0, chatter=0.0, damp=1.0):
    """One object hit once. size > 1 is bigger (lower); hard > 1 is a harder, shorter contact (brighter);
    chatter is the chance it rattles against what it lands on; damp > 1 when it is held or half-buried."""
    model, contact = MATS[mat]
    contact = contact / hard
    fs, ts, am, residuals = model(c, size)
    t = tt(n)
    y = np.zeros(n)
    for f, d, a in zip(fs, ts, am):
        f = max(f, 60.0)                                   # nothing below what a speaker can play
        a = a / (1 + (f * contact * 0.8) ** 2)             # a long contact cannot excite the highs
        y += a * np.sin(2 * np.pi * f * t) * np.exp(-t * damp / d)
    y = norm(y)
    for lo, hi, tau, gain in residuals:                    # the contact itself: shaped noise, very short
        top = max(lo * 1.5, min(hi, 0.9 / contact))
        y += gain * norm(fft_filter(c.noise(n), bp(lo, top)) * env_exp(n, tau, contact / 2))
    if chatter and c.u(0, 1) < chatter:
        d1 = c.u(0.006, 0.016)
        y = y + 0.35 * np.concatenate([np.zeros(N(d1)), y])[:n] + 0.14 * np.concatenate([np.zeros(N(d1 * c.u(1.7, 2.2))), y])[:n]
    return tail(norm(y))


# ------------------------------------------------------------------ steps, particles, bubbles, air


def grf(n, toe=0.075, toe_amp=0.6, soft=1.0, c=None):
    """Ground reaction force of one step: a heel bump at t = 0, then a smaller toe bump (Turchet 2016)."""
    t = tt(n)
    out = np.zeros(n)
    for at, amp, tau in ((0.0, 1.0, 0.006 * soft), (toe, toe_amp, 0.008 * soft)):
        if c is not None:
            if at > 0:
                at = max(0.0, at + c.u(-0.008, 0.008))
            amp *= c.u(0.85, 1.1)
        x = np.clip(t - at, 0, None) / tau
        out += amp * x ** 2 * np.exp(2 - 2 * x) * (t >= at)
    return out


def phism(c, n, energy, rate, freq, decay, jitter=0.35):
    """Cook's stochastic particle model: Poisson collisions whose rate follows the energy.
    Each collision is a tiny burst of NOISE, band-limited around freq. (Sine pings here sound like water drops.)"""
    e = energy / (energy.max() + 1e-9)
    hits = np.nonzero(c.rng.uniform(size=n) < np.clip(rate * e / SR, 0, 1))[0]
    y = np.zeros(n)
    g = max(8, N(decay * 6))
    env = np.exp(-tt(g) / decay)
    for h in hits:
        m = min(g, n - h)
        y[h:h + m] += e[h] * c.u(0.2, 1) * (c.noise(g) * env)[:m]
    spread = 1.7 + jitter
    return norm(fft_filter(y, bp(freq / spread, freq * spread)))


def bubble(c, r_mm, amp=1.0):
    """One bubble: Minnaert f0 = 3/r, rising as it decays."""
    r = r_mm / 1000
    f0 = 3 / r
    d = 0.13 / r + 0.0072 * r ** -1.5
    n = N(min(0.2, 6 / d))
    t = tt(n)
    return amp * np.sin(2 * np.pi * np.cumsum(f0 * (1 + 0.1 * d * t)) / SR) * np.exp(-d * t)


def bubbles(c, y, count, scale, rmax, span, alpha=1.6, amp=(0.08, 0.3), start=0.02):
    for _ in range(count):
        place(y, bubble(c, min(rmax, scale * c.u(0.04, 1) ** (-1 / alpha)), amp=c.u(*amp)), c.u(start, span))
    return y


def texture(c, n, lo, hi, bands=8, rate=20, depth=0.4, tilt=-0.25):
    """Living noise: each band swells on its own. Keep depth low for dry things (leaves, cloth, paper):
    deep independent swells gurgle like a brook, which is right only for water and fire (depth 0.8+)."""
    white = c.noise(n)
    edges = np.geomspace(lo, hi, bands + 1)
    y = np.zeros(n)
    for a, b in zip(edges, edges[1:]):
        band = fft_filter(white, bp(a, b, 3))
        band /= np.sqrt(np.mean(band ** 2)) + 1e-9
        m = norm(fft_filter(c.noise(n), lp(rate)))
        y += band * np.clip(1 + 1.5 * depth * m, 0, None) * (a / lo) ** tilt
    return norm(y)


def sweep(c, n, f_start, f_end, width=0.4, curve=None, bands=24):
    """Noise through a band that moves (a swing, a whoosh, a slide)."""
    noise = c.noise(n)
    x = np.linspace(0, 1, n) if curve is None else curve
    centre = np.exp(np.log(f_start) + (np.log(f_end) - np.log(f_start)) * x)
    edges = np.geomspace(80, 14000, bands + 1)
    y = np.zeros(n)
    for lo, hi in zip(edges, edges[1:]):
        y += fft_filter(noise, bp(lo, hi, 3)) * np.exp(-((np.log(np.sqrt(lo * hi)) - np.log(centre)) / width) ** 2)
    return norm(y)


def stickslip(c, n, rate, formants, q=10):
    """Friction: pulses at a wandering rate through the object's resonances (hinges, a bending trunk)."""
    pulses = (np.diff(np.floor(np.cumsum(rate) / SR), prepend=0) > 0).astype(float)
    return norm(sum(fft_filter(pulses, lambda f, F=F: 1 / (1 + ((f - F) / (F / q)) ** 2)) for F in formants))


def voice(n, f0, formants, bw, harmonics=40, c=None):
    """Harmonics of a moving pitch shaped by moving formants, with the small unsteadiness of a real throat."""
    if c is not None:
        f0 = f0 * (1 + 0.012 * norm(fft_filter(c.noise(n), lp(12))))
    ph = 2 * np.pi * np.cumsum(f0) / SR
    y = np.zeros(n)
    form = formants(tt(n))
    for k in range(1, harmonics):
        fk = k * f0
        y += sum(a / (1 + ((fk - F) / bw) ** 2) for F, a in form) / k ** 0.6 * np.sin(k * ph) * (fk < 10000)
    if c is not None:
        y *= 1 + 0.12 * norm(fft_filter(c.noise(n), lp(30)))
    return y


# ------------------------------------------------------------------ the soundtrack's instruments


def felt(note, dur=0.8, vel=0.6, octave=0):
    """The music's felt piano, one note."""
    f = hz(note) * 2 ** octave
    n = N(dur + 1.2)
    t = tt(n)
    bright = 2000 + 2600 * vel
    y = np.zeros(n)
    for k in range(1, 16):
        fk = k * np.sqrt(1 + 0.0004 * k * k)
        if f * fk > 9000:
            break
        tau = 4.5 / k ** 0.7 * (220 / max(f, 110)) ** 0.35 * min(1.0, dur)
        y += (1 / k ** 1.1) / (1 + (f * fk / bright) ** 2) * np.sin(2 * np.pi * f * fk * t) * (0.55 * np.exp(-t / (tau * 0.3)) + 0.45 * np.exp(-t / tau))
    hammer = fft_filter(np.random.default_rng(int(f)).standard_normal(n), bp(250, 2500, 1)) * np.exp(-t / 0.01) * 0.07
    y = np.tanh(1.8 * (y + hammer)) / 1.8
    return tail(y * np.clip(t / 0.004, 0, 1) * np.where(t > dur, np.exp(-(t - dur) / 0.25), 1.0), 30)


def glow(note, dur=0.5, vel=1.0, octave=0, glide=0.0):
    """The music's soft analog pluck: a rounded triangle whose brightness falls quickly, two voices a hair apart."""
    f = hz(note) * 2 ** octave
    n = N(dur * 3.5 + 0.1)
    t = tt(n)
    y = np.zeros(n)
    for det in (-4, 5):
        ph = 2 * np.pi * np.cumsum(f * 2 ** (det / 1200) * (1 + glide * np.exp(-t / 0.05))) / SR
        y += sum(((-1) ** ((k - 1) // 2)) / k ** 2 * np.sin(k * ph) * np.exp(-t * (3 + 9 * k)) for k in (1, 3, 5, 7, 9))
        y += 0.2 * sum(np.sin(k * ph) / k * np.exp(-t * (20 + 14 * k)) for k in range(1, 9) if k * f < 9000)
    return tail(0.5 * vel * y * np.clip(t / 0.003, 0, 1) * np.exp(-t / (0.5 * dur)), 20)


def shimmer(c, n, count, span, level=0.12):
    """A few tiny high pings in the music's notes (not hiss)."""
    y = np.zeros(n)
    for _ in range(count):
        f = hz(c.pick(PENTA) + "7") * c.pick([1, 1, 2])
        g = N(0.25)
        tg = tt(g)
        place(y, level * c.u(0.4, 1) * np.sin(2 * np.pi * f * tg) * np.exp(-tg / c.u(0.03, 0.07)) * np.clip(tg / 0.002, 0, 1), c.u(0, span))
    return y


def seq(n, notes, voice_fn, gap, **kw):
    y = np.zeros(n)
    for k, item in enumerate(notes):
        note, v = item if isinstance(item, tuple) else (item, 1.0)
        place(y, voice_fn(note, vel=v, **kw), k * gap)
    return y


# ------------------------------------------------------------------ space and finish

_IRS = {}


def _ir(kind):
    if kind not in _IRS:
        length, tau, pre, lo, hi = {"out": (0.09, 0.03, 0.015, 400, 5000), "in": (0.3, 0.07, 0.006, 150, 4500),
                                    "hall": (0.45, 0.1, 0.008, 200, 5000), "cave": (0.9, 0.22, 0.02, 120, 3500),
                                    "sky": (3.2, 0.62, 0.035, 90, 5500)}[kind]
        r = np.random.default_rng(len(kind) * 7 + 3)
        n = N(length)
        irs = []
        for _ in range(2):   # left and right differ: the tail is wide, the direct sound stays in the middle
            ir = fft_filter(r.standard_normal(n), bp(lo, hi)) * np.exp(-tt(n) / tau)
            ir[: N(pre)] = 0
            irs.append(ir / np.sqrt(np.sum(ir ** 2)))
        _IRS[kind] = irs
    return _IRS[kind]


WET = {"out": 0.03, "in": 0.07, "hall": 0.07, "cave": 0.18,     # a touch of air, never an audible echo
       "sky": 0.42}                                                   # the boss in the open sky: a long, diffuse tail (no repeat)


def space(y, kind):
    """Mono in, stereo out. Outdoors: a ground reflection a few ms late and a faint scatter. Indoors: a short room."""
    if kind == "out":
        d = N(0.0028)
        y = y + 0.3 * fft_filter(np.concatenate([np.zeros(d), y])[: len(y)], lp(2500, 1))
    irs = _ir(kind)
    n = len(y) + len(irs[0])
    dry = np.concatenate([y, np.zeros(n - len(y))])
    return np.stack([dry + WET[kind] * np.pad(np.convolve(y, ir), (0, 1))[:n] for ir in irs])


def finish(y, kind):
    y = tail(fft_filter(y, lambda f: lp(12000, 1)(f) * hp(55, 3)(f)), 10)
    y = np.tanh(1.1 * norm(y)) / np.tanh(1.1)
    st = space(y, kind)
    mono = np.abs(st).max(axis=0)
    start = max(0, int(np.argmax(mono > 0.05 * mono.max())) - N(0.001))        # instant: no lead-in
    last = np.nonzero(mono > 1e-4 * mono.max())[0][-1]
    st = st[:, start:last + 1].copy()
    k = N(0.0015 if start else 0.0005)
    st[:, :k] *= np.linspace(0, 1, k)
    f = min(N(0.01), st.shape[1] // 4)
    st[:, -f:] *= np.linspace(1, 0, f)
    return st


# ------------------------------------------------------------------ registry

S, META = {}, {}
PHYSICAL = {"Footsteps", "Work", "Breaking", "Building", "Fights", "World", "Animals", "Boss"}
SIZES = [1.0, 0.93, 1.06, 0.97, 1.03, 0.9]


def sfx(name, cat, when, variants=1, loud=0.5, kind=None, tuned=False, change="reworked", seed=None):
    """seed: the name its random source is drawn from, when that is not its own (a sound picked by ear among drafts
    keeps the draft's seed, so the game's is the very one that was heard)."""
    def deco(fn):
        S[name] = fn
        META[name] = {"cat": cat, "when": when, "variants": variants, "loud": loud, "change": change, "seed": seed or name,
                      "kind": kind or ("hall" if tuned or cat in ("Progress", "Interface") else "out"),
                      "vary": cat in PHYSICAL and not tuned}
        return fn
    return deco


def resize(y, factor):
    return y if factor == 1.0 else np.interp(np.arange(0, len(y) - 1, factor), np.arange(len(y)), y)


def smooth(x, sec):
    k = max(1, N(sec))
    return np.convolve(x, np.ones(k) / k, "same")


# ================================================================== footsteps

@sfx("step", "Footsteps", "walking on grass and soil", 4, 0.14)
def _(c):
    n = N(0.24)
    f = grf(n, soft=1.6, c=c)
    blades = phism(c, n, f, 2600, 3000, 0.0012, 0.5)                      # blades bending and snapping
    brush = texture(c, n, 1500, 7000, 6, 30) * smooth(f, 0.012)           # grass brushing the shoe
    crumbs = phism(c, n, f, 500, 900, 0.003)
    earth = strike(c, n, "dirt", size=c.u(1.1, 1.4))                      # soft ground giving
    return 0.45 * blades + 0.3 * norm(brush) + 0.4 * crumbs + 0.55 * earth


@sfx("tock", "Footsteps", "walking on wooden floors, bridges and boats", 4, 0.16)
def _(c):
    n = N(0.26)
    y = strike(c, n, "plank", size=c.u(1.3, 1.7), hard=0.5)                # the heel on boards, a soft sole
    place(y, strike(c, N(0.18), "plank", size=c.u(1.4, 1.8), hard=0.4) * c.u(0.4, 0.55), c.u(0.065, 0.09))   # the toe
    return y + 0.12 * norm(texture(c, n, 600, 4000, 5, 40) * smooth(grf(n, soft=1.3), 0.01))   # sole scuff


@sfx("click", "Footsteps", "walking on cobblestone", 4, 0.14)
def _(c):
    n = N(0.24)
    f = grf(n, soft=1.1, c=c)
    y = strike(c, n, "stone", size=c.u(1.3, 1.7), hard=0.6)                # heel: a dull tk, no ring
    place(y, strike(c, N(0.1), "stone", size=c.u(1.4, 1.8), hard=0.5) * c.u(0.4, 0.55), c.u(0.065, 0.09))
    grit = phism(c, n, f, 900, 4500, 0.0007, 0.4)                          # sand between the stones
    scuff = fft_filter(texture(c, n, 500, 6000, 5, 40), lp(5000)) * np.exp(-((tt(n) - 0.11) / 0.02) ** 2)
    return y + 0.35 * grit + 0.2 * scuff


@sfx("wade", "Footsteps", "wading through shallow water", 4, 0.16)
def _(c):
    n = N(0.5)
    f = grf(n, soft=2.5, toe=0.1, c=c)
    push = norm(fft_filter(c.noise(n), lp(1800)) * f)                      # the leg pushing water aside
    wash = texture(c, n, 500, 4000, 6, 12, 0.9) * env_exp(n, 0.12, 0.03)       # it closing behind
    return bubbles(c, 0.6 * push + 0.35 * wash, int(c.u(12, 20)), 1.0, 8, 0.32, amp=(0.05, 0.25), start=0.01)


@sfx("swim", "Footsteps", "a swimming stroke: an arm pulls through the water", 5, 0.09, change="new")
def _(c):
    n = N(0.6)
    t = tt(n)
    pull = np.sin(np.pi * np.clip(t / c.u(0.36, 0.44), 0, 1)) ** 2             # no attack: the arm slides in, pulls, and lets go
    push = norm(fft_filter(c.noise(n), bp(120, c.u(700, 1000))) * pull)          # the water moved aside: low and soft
    wash = texture(c, n, 500, 3200, 6, 9, 0.8) * np.exp(-((t - c.u(0.26, 0.32)) / 0.11) ** 2)   # it closing behind the hand
    return bubbles(c, 0.7 * push + 0.3 * wash, int(c.u(3, 7)), 0.8, 5, 0.4, amp=(0.02, 0.08), start=0.12)


@sfx("thud", "Footsteps", "landing after a hop down a level", 3, 0.3)
def _(c):
    n = N(0.28)
    f = grf(n, toe=0.012, toe_amp=0.9, soft=1.4, c=c)                      # both feet at once
    return strike(c, n, "body", size=c.u(1.1, 1.4)) + 0.8 * strike(c, n, "dirt", size=c.u(1.3, 1.6)) + 0.3 * phism(c, n, f, 1500, 1500, 0.002)


# ================================================================== work

@sfx("chop", "Work", "an axe strike on a tree or wooden block", 4, 0.5)
def _(c):
    n = N(0.36)
    bite = norm(fft_filter(c.noise(n), bp(1500, 8000)) * env_exp(n, 0.004, 0.0003))        # the edge going in
    block = strike(c, n, "wood", size=c.u(0.9, 1.2), hard=2.0)
    trunk = strike(c, n, "wood", size=c.u(2.3, 2.8), hard=0.5, damp=1.5)                   # the whole tree answers, low
    chips = phism(c, n, np.roll(env_exp(n, 0.06, 0.004), N(0.012)), 300, 2500, 0.002)      # chips flying off
    return block + 0.5 * bite + 0.4 * trunk + 0.3 * chips


@sfx("mine", "Work", "a pickaxe strike on stone", 4, 0.45)
def _(c):
    n = N(0.4)
    y = strike(c, n, "stone", size=c.u(0.9, 1.3), hard=1.4)                               # rock answering: a dry tchak, no ring
    y += 0.5 * norm(fft_filter(c.noise(n), bp(500, 3500)) * env_exp(n, 0.012, 0.0004))    # the weight behind the pick
    y += 0.4 * phism(c, n, env_exp(n, 0.05, 0.001), 1500, 3000, 0.0008)                   # dust and chips
    for _ in range(3):                                                                    # shards landing
        place(y, strike(c, N(0.06), "stone", size=c.u(0.6, 0.9)) * c.u(0.1, 0.2), c.u(0.05, 0.2))
    return y


@sfx("dig", "Work", "a shovel in soil, digging a hole", 4, 0.4)
def _(c):
    n = N(0.42)
    t = tt(n)
    bite = np.clip(t / 0.003, 0, 1) * np.exp(-t / 0.06)                                   # the blade cutting in: gritty, not soft
    crunch = phism(c, n, bite, 4000, 2400, 0.0008, 0.5) + 0.5 * phism(c, n, bite, 900, 900, 0.002)
    blade = norm(fft_filter(c.noise(n), bp(1500, 6000)) * env_exp(n, 0.02, 0.001))        # steel against grit
    toss = np.clip((t - 0.13) / 0.02, 0, 1) * np.exp(-(t - 0.13) / 0.09)                  # the soil thrown aside, landing
    return crunch + 0.4 * blade + 0.3 * strike(c, n, "dirt", size=1.0, hard=1.5) + 0.55 * phism(c, n, toss, 900, 1200, 0.003)


@sfx("rustle", "Work", "cutting grass, picking flowers and plants, leaves", 4, 0.3)
def _(c):
    n = N(0.36)
    t = tt(n)
    lo = c.u(1800, 2600)
    y = np.zeros(n)
    for at, amp in ((0.0, 1.0), (c.u(0.06, 0.09), c.u(0.5, 0.8)), (c.u(0.14, 0.19), c.u(0.3, 0.5))):   # a few soft brushes, no snap
        x = np.clip(t - at, 0, None)
        y += amp * norm(fft_filter(c.noise(n), bp(lo, lo * 3.5, 1))) * np.clip(x / 0.015, 0, 1) * np.exp(-x / 0.05) * (t >= at)
    return y * (1 + 0.45 * norm(fft_filter(c.noise(n), lp(35))))                          # leaves flutter


@sfx("swing", "Work", "swinging a tool or a weapon", 3, 0.25)
def _(c):
    n = N(0.2)
    arc = np.sin(np.linspace(0, np.pi, n)) ** 2
    k = c.u(0.85, 1.2)
    low = norm(fft_filter(c.noise(n), bp(250 * k, 1500 * k, 1)))                          # plain moving air, no tuned sweep
    high = norm(fft_filter(c.noise(n), bp(1200 * k, 5000 * k, 1)))
    return (low * arc + 0.6 * high * arc ** 3) * np.clip(tt(n) / 0.004, 0, 1)             # the highs only at the fastest moment


@sfx("punch", "Work", "hitting a tree or a rock with bare hands", 3, 0.3, change="new")
def _(c):
    n = N(0.22)
    return strike(c, n, "body", size=c.u(0.7, 0.9), hard=1.3) + 0.45 * strike(c, n, "wood", size=c.u(1.8, 2.3), hard=0.4, damp=3.0)


# ================================================================== breaking

def _crack(c, n, count, span):
    y = np.zeros(n)
    for _ in range(count):                                                                # fibres letting go, one by one
        g = N(c.u(0.0008, 0.002))
        place(y, c.noise(g) * np.exp(-tt(g) / (g / SR / 3)) * c.u(0.3, 1), -np.log(1 - c.u(0, 0.95)) * span / 3)
    return norm(fft_filter(y, bp(700, 9000)))


@sfx("snap", "Breaking", "a wooden block or fence breaks", 3, 0.42)
def _(c):
    n = N(0.5)
    y = _crack(c, n, int(c.u(5, 9)), 0.05) + 0.8 * strike(c, n, "wood", size=c.u(1.2, 1.6), hard=1.5)
    y += 0.3 * phism(c, n, env_exp(n, 0.06, 0.002), 500, 3000, 0.0015)                    # splinters
    place(y, strike(c, N(0.2), "wood", size=c.u(1.8, 2.3), damp=2.0) * 0.4, c.u(0.12, 0.2))   # a piece lands
    return y


@sfx("crumble", "Breaking", "stone breaks; digging down into a cave", 3, 0.55)
def _(c):
    n = N(0.85)
    t = tt(n)
    y = 0.9 * norm(fft_filter(c.noise(n), bp(600, 8000)) * env_exp(n, 0.006, 0.0003))     # the rock cracks: one sharp report
    at = 0.01
    for k in range(int(c.u(14, 20))):                                                     # pieces knocking as they fall apart
        place(y, strike(c, N(0.1), "stone", size=c.u(0.6, 2.2), hard=c.u(0.8, 1.6)) * c.u(0.35, 1) * (1 - k * 0.04), at)
        at += c.u(0.012, 0.045) * (1 + k * 0.07)
    fall = np.clip(t / 0.03, 0, 1) * np.exp(-t / 0.22)
    pebbles = phism(c, n, fall, 1400, 2200, 0.0012, 0.6)                                  # gravel pouring down
    dust = phism(c, n, fall, 3000, 5500, 0.0005, 0.3)
    rumble = norm(fft_filter(c.noise(n), bp(60, 220)) * env_exp(n, 0.2, 0.01))            # the weight of it
    return y + 0.6 * pebbles + 0.2 * dust + 0.6 * rumble


@sfx("creak", "Breaking", "a tree starts to fall: the trunk cracks and tips (the thud follows 0.36 s later)", 2, 0.4)
def _(c):
    dur = c.u(0.3, 0.34)                                                                  # over before the tree lands
    n = N(dur)
    t = tt(n)
    y = _crack(c, n, int(c.u(10, 14)), dur * 1.6)                                         # fibres letting go
    for j in range(int(c.u(6, 9))):                                                       # splinters breaking, closer and closer together
        at = dur * 0.9 * (1 - (1 - (j + c.u(0.2, 0.8)) / 9) ** 1.8)                       # (no friction pulses here: a slow pulse train through
        sn = N(0.07)                                                                      # low resonances is exactly how a raspberry is made)
        place(y, c.u(0.25, 0.5) * (strike(c, sn, "wood", size=c.u(0.6, 1.1), hard=c.u(1.6, 2.4), damp=2) + 0.5 * _crack(c, sn, 3, 0.02)), at)
    air = sweep(c, n, 500, 2400, 0.7) * (t / dur) ** 1.5                                  # the crown starting to move through the air
    y = y + 0.22 * air
    place(y, 0.8 * strike(c, N(0.1), "wood", size=c.u(1.5, 1.9), hard=1.5), 0)            # the first crack of the trunk
    return y * np.clip(t / 0.004, 0, 1) * np.clip((dur - t) / 0.05, 0, 1)


@sfx("fallthud", "Breaking", "a tree hits the ground", 2, 0.48)
def _(c):
    n = N(1.1)
    y = strike(c, n, "wood", size=c.u(3.6, 4.4), hard=0.5) + 1.2 * strike(c, n, "dirt", size=2.5)
    place(y, strike(c, N(0.3), "wood", size=3.0, hard=0.4) * 0.35, c.u(0.14, 0.19))        # it bounces once
    for _ in range(int(c.u(3, 6))):                                                       # branches breaking under it
        place(y, (_crack(c, N(0.08), 3, 0.03) + 0.6 * strike(c, N(0.08), "wood", size=c.u(0.7, 1.0))) * c.u(0.15, 0.3), c.u(0.02, 0.28))
    leaves = texture(c, n, 1800, 7000, 8, 25) * env_exp(n, 0.3, 0.02)
    return y + 0.3 * norm(leaves)


# ================================================================== building

@sfx("place", "Building", "fallback: any other wooden thing is set down", 3, 0.4)
def _(c):
    n = N(0.3)
    return strike(c, n, "wood", size=c.u(1.4, 1.8), hard=0.8, chatter=0.7) + 0.25 * strike(c, n, "dirt", size=1.0)


@sfx("clack", "Building", "fallback: any other stone thing is set down", 3, 0.38)
def _(c):
    n = N(0.28)
    return strike(c, n, "stone", size=c.u(1.3, 1.7), chatter=1.0) + 0.3 * phism(c, n, env_exp(n, 0.03, 0.001), 600, 3500, 0.0008)


@sfx("plant", "Building", "planting a seed or a sapling", 2, 0.35)
def _(c):
    n = N(0.42)
    y = 0.9 * strike(c, n, "dirt", size=0.8) + 0.5 * phism(c, n, env_exp(n, 0.05, 0.002), 700, 1200, 0.003)   # pressing soil
    place(y, strike(c, N(0.2), "dirt", size=1.0) * 0.5, c.u(0.12, 0.18))                   # a second pat
    return y


@sfx("place_post", "Building", "fence, gate, sign or flag: a wooden post is tapped into the ground", 3, 0.42)
def _(c):
    n = N(0.48)
    y = 0.8 * strike(c, n, "dirt", size=1.1) + 0.35 * phism(c, n, env_exp(n, 0.06, 0.002), 500, 900, 0.003)
    place(y, strike(c, N(0.18), "wood", size=c.u(1.2, 1.5), hard=0.7, damp=2.0) * 0.9, 0.0)        # mallet on the post
    place(y, strike(c, N(0.18), "wood", size=c.u(1.2, 1.5), hard=0.7, damp=2.5) * 0.6, c.u(0.15, 0.19))
    return y


@sfx("place_planks", "Building", "a wooden wall or a door goes up: boards set, one nail", 3, 0.45)
def _(c):
    n = N(0.5)
    y = strike(c, n, "plank", size=c.u(1.5, 1.9), hard=0.8)                                # boards against the frame
    place(y, norm(texture(c, N(0.07), 400, 2500, 5, 50) * np.sin(np.linspace(0, np.pi, N(0.07)))) * 0.25, 0.05)
    nail = strike(c, N(0.15), "wood", size=0.7, hard=2.2) + 0.07 * strike(c, N(0.15), "metal", size=1.4, damp=2.0)
    place(y, nail * 0.6, c.u(0.2, 0.24))
    return y


@sfx("place_stone", "Building", "a stone wall or a well: a heavy stone is set on stone", 3, 0.45)
def _(c):
    n = N(0.45)
    y = strike(c, n, "stone", size=c.u(2.4, 3.0), hard=0.6) + 0.6 * strike(c, n, "dirt", size=1.6)   # the weight of it
    place(y, norm(texture(c, N(0.12), 500, 4000, 5, 60) * np.sin(np.linspace(0, np.pi, N(0.12)))) * 0.2, 0.03)   # it grinds into place
    for _ in range(3):
        place(y, strike(c, N(0.05), "stone", size=c.u(0.5, 0.7)) * c.u(0.08, 0.18), c.u(0.06, 0.2))
    return y


@sfx("place_furniture", "Building", "a workbench, table, chair, chest, mailbox, clock, coop or trough is set down on its legs", 3, 0.4)
def _(c):
    n = N(0.45)
    y = strike(c, n, "plank", size=c.u(1.1, 1.35), hard=0.9)
    place(y, strike(c, N(0.25), "plank", size=c.u(1.15, 1.4), hard=0.9) * c.u(0.55, 0.75), c.u(0.03, 0.05))   # the other legs
    place(y, norm(texture(c, N(0.1), 250, 1400, 4, 60) * np.sin(np.linspace(0, np.pi, N(0.1)))) * 0.18, 0.09)   # nudged into place
    return y


@sfx("place_soft", "Building", "a rug, picnic blanket, bed, hay bale or basket: something soft is laid down", 3, 0.3)
def _(c):
    n = N(0.45)
    whump = strike(c, n, "body", size=c.u(1.5, 1.9), hard=0.5)                             # air pushed out from under it
    cloth = texture(c, n, 800, 5000, 7, 25) * env_exp(n, 0.09, 0.02)
    return 0.9 * whump + 0.45 * norm(cloth) + 0.2 * phism(c, n, env_exp(n, 0.08, 0.01), 400, 2500, 0.0015)   # straw, wicker


@sfx("place_pot", "Building", "a potted plant is set down", 2, 0.35)
def _(c):
    n = N(0.4)
    return strike(c, n, "ceramic", size=c.u(1.0, 1.2), chatter=0.6) + 0.3 * phism(c, n, env_exp(n, 0.05, 0.003), 500, 1200, 0.003)


@sfx("place_fire", "Building", "a campfire is built: logs and stones are stacked", 2, 0.4)
def _(c):
    n = N(0.6)
    y = np.zeros(n)
    at = 0.0
    for _ in range(4):
        place(y, strike(c, N(0.18), "wood", size=c.u(1.4, 2.2), hard=0.9) * c.u(0.5, 1.0), at)
        at += c.u(0.05, 0.11)
    for _ in range(2):
        place(y, strike(c, N(0.08), "stone", size=c.u(1.0, 1.4)) * 0.4, c.u(0.0, 0.3))
    return y


def _splash(c, n, big=1.0):
    slap = norm(fft_filter(c.noise(n), bp(400, 5000)) * env_exp(n, 0.035, 0.002))          # the surface is hit
    crown = sweep(c, n, 3000, 900, 0.5) * env_exp(n, 0.14, 0.02)                           # water thrown up, falling back
    wash = texture(c, n, 400, 3500, 6, 10, 0.9) * env_exp(n, 0.2, 0.05)
    return bubbles(c, 0.8 * slap + 0.6 * crown + 0.3 * wash, int(c.u(22, 34) * big), 1.0, 9, min(0.45, n / SR - 0.1))


@sfx("place_boat", "Building", "a boat is put on the water", 2, 0.4)
def _(c):
    n = N(0.95)
    y = 0.8 * strike(c, n, "plank", size=c.u(2.5, 3.0), hard=0.6, damp=1.5) + 0.6 * _splash(c, n)
    place(y, norm(texture(c, N(0.3), 300, 1500, 4, 8, 0.9) * np.sin(np.linspace(0, np.pi, N(0.3)))) * 0.15, 0.4)   # water lapping the hull
    return y


@sfx("place_floor", "Building", "planks laid as a floor or a bridge", 3, 0.35)
def _(c):
    n = N(0.4)
    y = strike(c, n, "plank", size=c.u(1.6, 2.0), hard=1.1, chatter=0.5)
    place(y, strike(c, N(0.2), "plank", size=c.u(1.7, 2.1), hard=1.1) * 0.5, c.u(0.07, 0.1))
    return y


@sfx("place_path", "Building", "cobbles are set into a path", 3, 0.35)
def _(c):
    n = N(0.4)
    e = np.clip(tt(n) / 0.004, 0, 1) * np.exp(-tt(n) / 0.07)
    y = phism(c, n, e, 120, 1800, 0.002, 0.5) + 0.35 * phism(c, n, e, 900, 4000, 0.0007)
    for k in range(3):
        place(y, strike(c, N(0.08), "stone", size=c.u(1.0, 1.5)) * c.u(0.4, 0.7), k * c.u(0.04, 0.07))
    return y + 0.4 * strike(c, n, "dirt", size=1.0)


@sfx("fill_dirt", "Building", "earth is shovelled into a hole, a field or the water", 2, 0.35)
def _(c):
    n = N(0.5)
    e = np.clip(tt(n) / 0.01, 0, 1) * np.clip((0.35 - tt(n)) / 0.2, 0, 1)
    return phism(c, n, e, 1200, 800, 0.004, 0.5) + 0.4 * phism(c, n, e, 400, 2200, 0.0015) + 0.7 * strike(c, n, "dirt", size=1.4)


# The door. Five made without hearing them were refused, each for its own fault: a slow pulse train ("a weird noise"),
# a lone latch ("a clic that does not sound like a door"), two knocks ("not a toctoc": it wants an opening and a
# closing), a swing of noise grains ("still a click"), a gliding note ("an old person moaning"). Then six were put on
# a page to be chosen by ear (music/doors.py, local/music/door.html): "go with one knock sound effect". So: one wooden knock
# each way, the knock of the wood and the board's body under it as one sound: higher to open, lower and fuller to
# close. (One variant each: these are the two that were heard and chosen.)
def door_knock(c, size, hard, body):
    return strike(c, N(0.3), "wood", size=size, hard=hard) + body * strike(c, N(0.3), "plank", size=size * 1.15, hard=hard)


@sfx("gate", "Building", "a gate or a door opens: one wooden knock", 1, 0.55, kind="out", tuned=True)      # (tuned: never resized or re-pitched: as chosen)
def _(c):
    return door_knock(Ctx("door_knock_open", 0), 0.85, 1.1, 0.4)        # (the very knock of the page: its own random source)


@sfx("door_close", "Building", "a gate or a door closes: one knock, lower and fuller", 1, 0.55, kind="out", tuned=True)
def _(c):
    return door_knock(Ctx("door_knock_close", 0), 1.25, 0.9, 0.7)


@sfx("chest", "Building", "opening a chest", 2, 0.4, kind="in")
def _(c):
    n = N(0.7)
    t = tt(N(0.36))
    k = c.u(0.9, 1.15)
    y = np.zeros(n)
    place(y, 0.1 * strike(c, N(0.05), "metal", size=1.5, damp=3.0), 0)                      # the latch
    place(y, 0.45 * stickslip(c, len(t), c.u(50, 70) + 60 * t / 0.36, (700 * k, 1500 * k, 2300 * k), 12) * np.sin(np.pi * t / 0.36) ** 0.5, 0.02)
    place(y, strike(c, N(0.3), "plank", size=c.u(1.2, 1.4), hard=0.9), 0.38)                 # the lid falls back
    return y


@sfx("write", "Building", "writing on a sign or a letter", 2, 0.25)
def _(c):
    n = N(0.7)
    y = np.zeros(n)
    k = c.u(0.7, 1.35)                                                                    # a pencil, a quill, chalk
    at = 0.0
    while at < 0.6:
        sn = N(c.u(0.05, 0.12))
        place(y, texture(c, sn, 1800 * k, 6000 * k, 5, 80) * np.sin(np.linspace(0, np.pi, sn)) * c.u(0.5, 1), at)
        at += c.u(0.07, 0.15)
    return y


# ================================================================== items

@sfx("collect", "Items", "picking up an item", 3, 0.34, tuned=True)
def _(c):
    lo, hi = [("A5", "D6"), ("F#5", "A5"), ("D6", "F#6")][c.v % 3]
    n = N(0.9)
    y = np.zeros(n)
    place(y, glow(lo, 0.25), 0)
    place(y, glow(hi, 0.4, glide=-0.02), 0.06)
    return y + shimmer(c, n, 3, 0.12)


@sfx("orb", "Items", "an experience orb flies into you", 6, 0.22, tuned=True)
def _(c):
    note = (PENTA + ["D"])[c.v % 6] + ("7" if c.v % 6 == 5 else "6")
    return glow(note, 0.3, glide=0.03)


@sfx("drop", "Items", "dropping an item", 2, 0.3, kind="out")
def _(c):
    n = N(0.28)
    return strike(c, n, "dirt", size=0.7, hard=1.5) + 0.4 * phism(c, n, env_exp(n, 0.03, 0.002), 1200, 2800, 0.0012)   # it lands in the grass


def _chomp(c, n, crisp, count):
    """One bite. Crisp food breaks in a burst of pulses about a millisecond long, broadband, dense at first and thinning:
    it is the rate of breaks that reads as crisp, and the energy above 2 kHz as fresh (Povey; the Pringles study).
    A closing mouth is a resonance sliding down, about 1500 to 700 Hz: that is what turns a crackle into "nom"."""
    y = np.zeros(n)
    for _ in range(count):
        g = N(c.u(0.0006, 0.0018))
        place(y, c.noise(g) * np.exp(-tt(g) / (g / SR / 3)) * c.u(0.3, 1), min(0.09, -np.log(1 - c.u(0, 0.97)) * 0.02))
    x = np.linspace(0, 1, n) ** 0.6
    crack = norm(fft_filter(y, bp(2000, 11000)))
    mouth = norm(fft_filter(y, bp(1100, 1900, 2)) * (1 - x) + fft_filter(y, bp(520, 950, 2)) * x)
    wet = texture(c, n, 400, 1800, 4, 25, 0.5) * np.clip(tt(n) / 0.004, 0, 1) * np.exp(-tt(n) / 0.035)
    return crisp * crack + 0.9 * mouth + 0.22 * wet


@sfx("eat", "Items", "eating: a crisp bite, then two chews", 3, 0.3, kind="out", change="new")
def _(c):
    n = N(0.75)
    y = np.zeros(n)
    at = 0.0
    for k, (crisp, count, amp) in enumerate(((1.0, 16, 1.0), (0.4, 10, 0.7), (0.3, 9, 0.55))):   # the bite is bright; the chews are in a closed mouth
        bn = N(0.13)
        one = _chomp(c, bn, crisp, count)
        if k == 0:
            one = one + 0.25 * strike(c, bn, "body", size=c.u(0.55, 0.7), hard=1.2)       # the teeth meeting
        place(y, one * amp, at)
        at += c.u(0.2, 0.23) if k == 0 else c.u(0.17, 0.19)
    return y


@sfx("loot", "Items", "a dropped item lands and bounces", 3, 0.25, kind="out")
def _(c):
    n = N(0.4)
    y = np.zeros(n)
    at, v = 0.0, 1.0
    for k in range(3):
        sn = N(0.07)
        place(y, (strike(c, sn, "dirt", size=0.6, hard=1.5) + 0.4 * phism(c, sn, env_exp(sn, 0.006, 0.001), 1500, 3000, 0.001)) * v, at)
        at += 0.11 * (0.6 ** k)
        v *= 0.45
    return y


@sfx("craft", "Items", "crafting something at a workbench", 2, 0.4, tuned=True)
def _(c):
    n = N(1.6)
    y = np.zeros(n)
    for k in range(3):                                                                    # tools on the bench
        place(y, strike(c, N(0.12), "plank", size=c.u(0.7, 0.9), hard=1.6) * 0.5, k * c.u(0.08, 0.1))
    notes = [("D5", "A5", "D6"), ("D5", "F#5", "A5")][c.v % 2]
    for k, note in enumerate(notes):
        place(y, glow(note, 0.5, 0.8 + 0.1 * k), 0.3 + k * 0.08)
    return y + shimmer(c, n, 5, 0.6)


# ================================================================== progress

@sfx("chime", "Progress", "a goal completed: the music's own melody cell, on its piano", 1, 0.4)
def _(c):
    n = N(2.6)
    y = np.zeros(n)
    for at, note, v in ((0, "F#5", 0.62), (0.15, "E5", 0.5), (0.3, "F#5", 0.56), (0.47, "A5", 0.68)):
        place(y, felt(note, 0.9, v), at)
        place(y, glow(note, 0.5, 0.35 * v, octave=1), at)
    return y


@sfx("levelup", "Progress", "you reach a new level", 1, 0.5)
def _(c):
    n = N(3.2)
    y = np.zeros(n)
    for k, note in enumerate(("D4", "A4", "D5", "F#5", "A5", "D6")):
        place(y, felt(note, 1.4, 0.5 + 0.04 * k), k * 0.085)
    for k, note in enumerate(("D5", "F#5", "A5")):                                        # the music's pad, opening
        t = tt(n)
        ph = 2 * np.pi * hz(note) * t
        y += 0.035 * sum(np.sin(j * ph) / j / (1 + (j * hz(note) / 1800) ** 2) for j in range(1, 8)) * np.sin(np.pi * np.clip((t - 0.3) / 2.6, 0, 1)) ** 2
    return y + shimmer(c, n, 10, 1.4)


@sfx("mail", "Progress", "a letter arrives in your mailbox", 1, 0.35)
def _(c):
    n = N(2.0)
    y = np.zeros(n)
    place(y, norm(texture(c, N(0.22), 2000, 7000, 5, 40) * np.sin(np.linspace(0, np.pi, N(0.22)))) * 0.3, 0)   # paper
    place(y, felt("A5", 0.8, 0.55), 0.0)
    place(y, felt("D6", 1.0, 0.6), 0.16)
    return y


# ================================================================== fights

@sfx("hit", "Fights", "landing a blow", 3, 0.5)
def _(c):
    n = N(0.25)
    slap = norm(fft_filter(c.noise(n), bp(700, 4500)) * env_exp(n, 0.012, 0.0005))
    return strike(c, n, "body", size=c.u(0.8, 1.1), hard=1.5) + 0.6 * slap + 0.2 * norm(texture(c, n, 1000, 5000, 5, 40) * env_exp(n, 0.04, 0.003))


@sfx("hurt", "Fights", "you take damage", 2, 0.45)
def _(c):
    n = N(0.4)
    t = tt(n)
    oof = voice(n, c.u(150, 180) * np.exp(-t / 0.35), lambda t: [(550, 1.0), (1000, 0.4)], 200, 30, c) * env_exp(n, 0.07, 0.01)   # a breath knocked out
    return strike(c, n, "body", size=c.u(1.3, 1.6), hard=1.2) + 0.25 * norm(oof)


@sfx("die", "Fights", "you die: a slow fall in B minor, sad but gentle", 1, 0.4, tuned=True)
def _(c):
    n = N(4.0)
    y = np.zeros(n)
    for k, (note, v) in enumerate((("F#4", 0.5), ("D4", 0.42), ("B3", 0.36))):            # a falling minor chord, each note softer and later
        place(y, felt(note, 2.2, v), k * 0.5 + 0.04 * k * k)
    place(y, felt("B2", 2.6, 0.3), 1.2)                                                    # it settles on the low root and stays there
    return fft_filter(y, lp(1800))


@sfx("poof", "Fights", "a creature vanishes in a small puff of smoke", 2, 0.28)
def _(c):
    n = N(0.32)
    t = tt(n)
    puff = norm(fft_filter(c.noise(n), bp(c.u(700, 900), 4500, 1))) * np.clip(t / 0.008, 0, 1) * np.exp(-t / 0.07)   # a soft breath of air: no boom, no sweep
    dust = phism(c, n, np.clip(t / 0.02, 0, 1) * np.exp(-t / 0.1), 600, 5000, 0.0006, 0.3)                          # a little dust settling
    return fft_filter(puff + 0.2 * dust, hp(350))                                                                  # nothing low: lows are what made it an explosion


@sfx("gloom", "Fights", "a gloom attacks at night: a ghostly, breathy sigh", 2, 0.34)
def _(c):
    dur = [0.55, 0.7][c.v % 2]
    n = N(dur)
    t = tt(n)
    k = [1.0, 0.85][c.v % 2] * c.u(0.95, 1.05)
    fall = np.clip(t / dur, 0, 1) ** 0.7                                                  # the mouth closing: "haaa-ooo", all air, no buzz
    mouth = sweep(c, n, 1100 * k, 600 * k, 0.3, curve=fall)
    throat = sweep(c, n, 2600 * k, 1500 * k, 0.3, curve=fall)
    waver = 1 + 0.25 * np.sin(2 * np.pi * c.u(6, 8) * t)                                  # a slight shiver
    env = np.clip(t / 0.04, 0, 1) * np.clip((dur - t) / (0.6 * dur), 0, 1) ** 1.3
    return fft_filter(mouth + 0.35 * throat, hp(250)) * waver * env


# ================================================================== animals

def _buk(c, dur, f_hi, drop):
    n = N(dur)
    t = tt(n)
    y = voice(n, f_hi * np.exp(-t / drop), lambda t: [(1300, 1.0), (2600, 0.6)], 350, 14, c)
    return norm(y) * np.sin(np.pi * np.clip(t / dur, 0, 1))


@sfx("cluck", "Animals", "a chicken clucks (petted, fed, laying)", 4, 0.3)
def _(c):
    n = N(0.55)
    y = np.zeros(n)
    at = 0.0
    for k in range(2 + c.v % 2):
        place(y, _buk(c, 0.07, c.u(650, 850), 0.12), at)
        at += c.u(0.1, 0.14)
    if c.v == 3:                                                                          # buk buk ba-KAW
        place(y, _buk(c, 0.16, c.u(900, 1000), 0.5) * 1.1, at)
    return y


@sfx("squawk", "Animals", "a chicken is hit or startled", 3, 0.32, change="new")
def _(c):
    dur = c.u(0.2, 0.28)
    n = N(dur)
    x = tt(n) / dur
    y = voice(n, c.u(780, 900) * (1 + 0.25 * np.sin(np.pi * x)) * (1 - 0.25 * x), lambda t: [(1500, 1.0), (2900, 0.7)], 400, 12, c)
    return norm(y) * (1 - 0.5 * (0.5 + 0.5 * np.sin(2 * np.pi * c.u(60, 80) * tt(n)))) * np.sin(np.pi * x) ** 0.6


@sfx("chirp", "Animals", "a chick peeps; an egg hatches", 4, 0.25)
def _(c):
    n = N(0.4)
    y = np.zeros(n)
    at = 0.0
    for k in range(2 + c.v % 2):
        bn = N(c.u(0.05, 0.07))
        t = tt(bn)
        ph = 2 * np.pi * np.cumsum(c.u(3200, 4000) * (1 - 0.12 * np.sin(np.pi * t / (bn / SR)))) / SR
        place(y, (np.sin(ph) + 0.15 * np.sin(2 * ph)) * np.sin(np.pi * t / (bn / SR)) ** 1.5, at)
        at += c.u(0.09, 0.13)
    return y


@sfx("moo", "Animals", "a cow moos (petted, milked, fed, hit)", 3, 0.4)
def _(c):
    dur = [1.25, 0.95, 1.45][c.v % 3]
    n = N(dur)
    t = tt(n)
    x = t / dur
    f0 = [105, 125, 92][c.v % 3] * c.u(0.97, 1.03) * (0.82 + 0.38 * np.sin(np.pi * np.clip(x * 1.15, 0, 1)) ** 1.5 - 0.12 * x)
    mouth = np.clip((x - 0.12) / 0.25, 0, 1) * (1 - 0.5 * np.clip((x - 0.8) / 0.2, 0, 1))   # "mm" -> "ooo" -> closing
    y = voice(n, f0, lambda t: [(250 + 230 * mouth, 1.0), (650 + 350 * mouth, 0.25 + 0.45 * mouth), (2300, 0.03 + 0.1 * mouth)], 120, 60, c)
    fry = (1 - np.clip(x / 0.18, 0, 1)) + np.clip((x - 0.85) / 0.15, 0, 1)                # rough at both ends
    y = norm(y) * (1 - 0.45 * fry * (0.5 + 0.5 * np.sin(np.pi * np.cumsum(f0) / SR)))
    breath = texture(c, n, 500, 3000, 5, 10) * (0.02 + 0.1 * np.clip((x - 0.75) / 0.25, 0, 1))
    return (y + breath) * np.clip(t / 0.06, 0, 1) * np.clip((dur - t) / 0.18, 0, 1) ** 0.7


@sfx("milk", "Animals", "milking a cow into a pail", 2, 0.35)
def _(c):
    n = N(0.95)
    y = np.zeros(n)
    at = 0.0
    for k in range(4):                                                                    # two hands in turn: psh-psh, psh-psh
        sn = N(c.u(0.11, 0.15))
        hand = 1.0 if k % 2 == 0 else 0.85
        jet = sweep(c, sn, 4200 * hand, 2200 * hand, 0.6) * env_exp(sn, 0.05, 0.006)      # a thin stream hitting the milk
        froth = np.zeros(sn)
        for _ in range(10):                                                               # a little foam
            place(froth, bubble(c, c.u(0.5, 1.4), amp=c.u(0.05, 0.15)), c.u(0.01, 0.09))
        body = norm(fft_filter(c.noise(sn), bp(500, 1300, 1)) * env_exp(sn, 0.03, 0.004)) # the pail, dull because it is part full
        place(y, norm(jet) + froth + 0.25 * body, at)
        at += c.u(0.19, 0.23) if k % 2 == 0 else c.u(0.24, 0.28)
    return y


@sfx("lay", "Animals", "a hen lays an egg", 1, 0.3)
def _(c):
    n = N(0.65)
    y = np.zeros(n)
    place(y, _buk(c, 0.07, 760, 0.12), 0)
    place(y, _buk(c, 0.09, 820, 0.2), 0.12)
    place(y, 0.8 * strike(c, N(0.15), "body", size=0.45, hard=1.3) + 0.3 * phism(c, N(0.15), env_exp(N(0.15), 0.02, 0.002), 900, 2500, 0.0015), 0.32)   # into the straw
    return y


@sfx("hatch", "Animals", "an egg hatches", 1, 0.3)
def _(c):
    n = N(0.7)
    y = 0.8 * _crack(c, n, 10, 0.2)                                                        # the shell, bit by bit
    t = tt(N(0.06))
    for k in range(2):
        ph = 2 * np.pi * np.cumsum(c.u(3400, 3900) * (1 - 0.12 * np.sin(np.pi * t / 0.06))) / SR
        place(y, 0.9 * np.sin(ph) * np.sin(np.pi * t / 0.06) ** 1.5, 0.25 + k * 0.11)
    return y


@sfx("love", "Animals", "an animal is happy: petting, love hearts, a calf is born", 2, 0.3, tuned=True)
def _(c):
    n = N(1.2)
    y = np.zeros(n)
    for k, note in enumerate([("A5", "D6"), ("F#5", "B5")][c.v % 2]):
        place(y, glow(note, 0.45, glide=0.015), k * 0.1)
    return y + shimmer(c, n, 4, 0.35)


# ================================================================== world

@sfx("water", "World", "a splash: boarding or mooring a boat, something falls in", 3, 0.4)
def _(c):
    return _splash(c, N(0.7))


@sfx("pour", "World", "watering crops: a gentle stream from the can", 2, 0.3, change="new")
def _(c):
    n = N(0.8)
    t = tt(n)
    env = np.clip(t / 0.05, 0, 1) * np.clip((0.8 - t) / 0.25, 0, 1)
    y = np.zeros(n)
    for _ in range(int(c.u(110, 150))):
        at = c.u(0, 0.7)
        place(y, bubble(c, min(3.0, 0.5 * c.u(0.03, 1) ** (-1 / 2.2)), amp=c.u(0.1, 0.5) * env[int(at * SR)]), at)
    return norm(y) + 0.1 * texture(c, n, 2500, 9000, 5, 30) * env + 0.25 * phism(c, n, env, 400, 700, 0.004)   # spray, drops on soil


@sfx("fill", "World", "filling a bucket at the water", 2, 0.4, change="new")
def _(c):
    n = N(0.9)
    y = np.zeros(n)
    place(y, sweep(c, N(0.25), 2500, 800, 0.5) * env_exp(N(0.25), 0.07, 0.004) * 0.5, 0)
    at = 0.08
    for k in range(int(c.u(4, 6))):                                                       # glug, glug: higher as it fills
        place(y, bubble(c, c.u(7, 10) * (1 - 0.08 * k), amp=0.9 - 0.1 * k), at)
        at += c.u(0.09, 0.14)
    return bubbles(c, y, 25, 0.8, 4, 0.7, alpha=1.8, amp=(0.05, 0.2))


@sfx("whoosh", "World", "lighting a fire: the flame catches", 2, 0.4)
def _(c):
    n = N(0.8)
    t = tt(n)
    swell = sweep(c, n, c.u(180, 260), c.u(1500, 2200), 0.45, curve=np.clip(t / c.u(0.25, 0.4), 0, 1) ** 0.6)
    flame = texture(c, n, 150, 1200, 6, 14, 0.8)
    return (swell + 0.4 * flame) * np.clip(t / 0.03, 0, 1) * np.clip((0.8 - t) / 0.45, 0, 1) ** 0.8


@sfx("crackle", "World", "fire burning, something burns", 3, 0.3)
def _(c):
    n = N(1.2)
    t = tt(n)
    lap = texture(c, n, 70, 500, 5, 9, 0.8)                                                    # flames lapping
    hiss = texture(c, n, 3000, 10000, 4, 6) * 0.05                                        # sap and steam
    pops = np.zeros(n)
    for _ in range(int(c.u(18, 32))):
        place(pops, _crack(c, N(0.012), 1, 0.003) * c.u(0.1, 1) ** 2, c.u(0, 1.1))
    return (0.3 * lap + hiss + norm(pops)) * np.clip(t / 0.01, 0, 1) * np.clip((1.2 - t) / 0.3, 0, 1)


@sfx("flood", "World", "water spreads over the ground", 1, 0.35)
def _(c):
    n = N(1.3)
    t = tt(n)
    env = np.clip(t / 0.08, 0, 1) * np.exp(-np.clip(t - 0.08, 0, None) / 0.45)
    y = 0.35 * norm(fft_filter(c.noise(n), bp(150, 1100))) * env                          # a low wash only: any hiss reads as steam on a fire
    for _ in range(90):                                                                   # mostly liquid: bubbles of all sizes, thinning out
        at = c.u(0.02, 1.1)
        place(y, bubble(c, min(8, 1.6 * c.u(0.05, 1) ** (-1 / 1.6)), amp=c.u(0.08, 0.3) * env[int(at * SR)]), at)
    return y


@sfx("grow", "World", "a crop or a sapling grows a stage", 2, 0.18, tuned=True)
def _(c):
    n = N(0.7)
    y = np.zeros(n)
    place(y, glow(["A6", "B6"][c.v % 2], 0.25, glide=-0.04), 0)                            # a tiny upward stretch
    place(y, 0.25 * norm(texture(c, N(0.12), 2500, 8000, 4, 60) * np.sin(np.linspace(0, np.pi, N(0.12)))), 0)   # a leaf unfolding
    return y


@sfx("descend", "World", "going down into a cave", 1, 0.4, kind="cave")
def _(c):
    n = N(1.2)
    y = sweep(c, n, 1500, 150, 0.5) * np.sin(np.pi * np.clip(tt(n) / 1.2, 0, 1)) * 0.6
    at = 0.0
    for k in range(8):                                                                    # loose stones going down with you
        place(y, strike(c, N(0.12), "stone", size=c.u(0.6, 1.8)) * c.u(0.3, 0.8), at)
        at += c.u(0.03, 0.09) * (1 + k * 0.1)
    return y


# ================================================================== people

VOWELS = {"a": (850, 1400), "e": (500, 1900), "i": (320, 2300), "o": (480, 900), "u": (350, 800)}


def _syllable(c, note, dur, bend=0.04, loud=False):
    n = N(dur)
    t = tt(n)
    f1, f2 = VOWELS[c.pick("aeiou")]
    f0 = np.full(n, hz(note)) * (1 + bend * np.sin(np.pi * t / dur))
    form = (lambda t: [(f1, 1.0), (f2, 0.5), (2600, 0.25)]) if loud else (lambda t: [(f1, 1.0), (f2, 0.5)])
    return norm(voice(n, f0, form, 300 if loud else 220, 30 if loud else 24, c)) * np.sin(np.pi * t / dur) ** (0.6 if loud else 0.8)


@sfx("say", "People", "someone nearby talks: a soft babble of two to four syllables", 5, 0.18, kind="out")
def _(c):
    y = np.zeros(N(0.6))
    at = 0.0
    for _ in range([3, 2, 4, 3, 2][c.v % 5]):
        dur = c.u(0.055, 0.08)
        place(y, _syllable(c, c.pick(PENTA) + "4", dur), at)
        at += dur + c.u(0.005, 0.02)
    return y


@sfx("shout", "People", "someone shouts", 2, 0.3, kind="out")
def _(c):
    y = np.zeros(N(0.4))
    for k, note in enumerate([("A4", "D5"), ("F#4", "B4")][c.v % 2]):                      # a call: two rising syllables
        place(y, _syllable(c, note, c.u(0.13, 0.16), 0.06, loud=True), k * c.u(0.13, 0.16))
    return y


@sfx("give", "People", "someone gives you something", 1, 0.35, tuned=True)
def _(c):
    n = N(1.5)
    y = np.zeros(n)
    place(y, norm(texture(c, N(0.2), 2500, 7000, 5, 40) * np.sin(np.linspace(0, np.pi, N(0.2)))) * 0.3, 0)
    for k, note in enumerate(("B5", "D6", "F#6")):
        place(y, glow(note, 0.4, 0.8), k * 0.07)
    return y


@sfx("join", "People", "someone arrives in the world", 1, 0.25, tuned=True)
def _(c):
    n = N(2.4)
    y = np.zeros(n)
    for k, note in enumerate(("D5", "A5", "F#6")):                                        # an open fifth, then the third on top
        place(y, glow(note, 0.9, 0.8 - 0.1 * k), k * 0.11)
    place(y, felt("D4", 1.2, 0.35), 0)
    return y


@sfx("leave", "People", "someone falls asleep (leaves)", 1, 0.22, tuned=True)
def _(c):
    n = N(2.2)
    y = np.zeros(n)
    for k, note in enumerate(("F#6", "A5", "D5")):
        place(y, glow(note, 0.9, 0.7 - 0.1 * k), k * 0.16)
    return fft_filter(y, lp(4000))


# ================================================================== interface

@sfx("ui", "Interface", "clicking a button, switching tabs or pages", 3, 0.2, kind="in")
def _(c):
    n = N(0.2)
    y = 0.5 * strike(c, n, "wood", size=c.u(0.35, 0.45), hard=1.5, damp=2.5)               # a small wooden key
    place(y, glow(["D6", "E6", "A6"][c.v % 3], 0.08, 0.6), 0)
    return y


# The user: "add a noise in the crafting menu or in the ui when switching selection. should be the default noise when
# switching things, less loud than the tab switch". The same small wooden key as `ui`, lighter, without its note, 4 dB under.
@sfx("pick", "Interface", "moving the selection: another recipe in the crafting list, another hotbar slot", 3, 0.12, kind="in", change="new")
def _(c):
    n = N(0.12)
    return 0.5 * strike(c, n, "wood", size=c.u(0.28, 0.36), hard=1.2, damp=3.5)


@sfx("open", "Interface", "opening a panel (crafting, mailbox, chest view)", 1, 0.25)
def _(c):
    n = N(0.8)
    y = 0.25 * sweep(c, n, 1500, 4000, 0.5) * np.sin(np.pi * np.clip(tt(n) / 0.2, 0, 1)) * (tt(n) < 0.2)
    place(y, glow("A5", 0.2, 0.7), 0.0)
    place(y, glow("D6", 0.3, 0.7), 0.07)
    return y


@sfx("close", "Interface", "closing a panel", 1, 0.22)
def _(c):
    n = N(0.8)
    y = 0.25 * sweep(c, n, 4000, 1500, 0.5) * np.sin(np.pi * np.clip(tt(n) / 0.2, 0, 1)) * (tt(n) < 0.2)
    place(y, glow("D6", 0.2, 0.7), 0.0)
    place(y, glow("A5", 0.3, 0.7), 0.07)
    return y


@sfx("buzz", "Interface", "something can't be done (soft, never harsh)", 1, 0.25)
def _(c):
    n = N(0.6)
    y = np.zeros(n)
    for k, note in enumerate(("D3", "B2")):                                               # two muted low piano notes, falling
        place(y, felt(note, 0.12, 0.5), k * 0.12)
    return fft_filter(y, lp(900))


# ================================================================== the first boss (mockup: Old Mossback and its sporelings)

@sfx("boss_wake", "Boss", "Old Mossback wakes: the hill stands up", 1, 0.5, change="new")
def _(c):
    dur = 1.9
    n = N(dur)
    t = tt(n)
    x = t / dur
    swell = np.sin(np.pi * x) ** 1.2
    rumble = norm(fft_filter(c.noise(n), bp(45, 160))) * swell                            # the ground giving
    earth = phism(c, n, swell ** 2, 900, 1400, 0.002)                                     # soil and pebbles sliding off
    soil = texture(c, n, 200, 1500, 5, 12, 0.3) * swell
    f0 = 62 - 14 * x
    groan = norm(voice(n, f0, lambda t: [(190, 1.0), (430, 0.4), (1700, 0.03)], 110, 50, c)) * np.clip((x - 0.35) / 0.3, 0, 1) * np.clip((1 - x) / 0.2, 0, 1)
    return rumble + 0.5 * earth + 0.3 * soil + 0.55 * groan


@sfx("boss_groan", "Boss", "Old Mossback is hurt, or bellows before an attack", 2, 0.45, change="new")
def _(c):
    dur = [0.9, 1.15][c.v % 2]
    n = N(dur)
    t = tt(n)
    x = t / dur
    f0 = [74, 66][c.v % 2] * c.u(0.97, 1.03) * (1.08 - 0.3 * x + 0.1 * np.sin(np.pi * x))
    mouth = np.clip(x / 0.2, 0, 1) * (1 - 0.6 * np.clip((x - 0.7) / 0.3, 0, 1))
    y = norm(voice(n, f0, lambda t: [(210 + 130 * mouth, 1.0), (540 + 220 * mouth, 0.5), (1900, 0.04 + 0.05 * mouth)], 110, 60, c))
    y = y * (1 - 0.5 * (0.5 + 0.5 * np.sin(np.pi * np.cumsum(f0) / SR)))                   # a rough old throat
    breath = texture(c, n, 300, 2500, 5, 10) * (0.05 + 0.1 * x)
    return (y + breath) * np.clip(t / 0.05, 0, 1) * np.clip((dur - t) / 0.2, 0, 1) ** 0.7


@sfx("boss_stomp", "Boss", "Old Mossback drops on the ground", 2, 0.6, change="new")
def _(c):
    n = N(1.0)
    t = tt(n)
    y = strike(c, n, "dirt", size=2.6, hard=0.7) + 0.9 * strike(c, n, "body", size=2.4, hard=0.8)
    y += 0.9 * norm(fft_filter(c.noise(n), bp(40, 110))) * env_exp(n, 0.16, 0.004)        # the weight of it
    late = np.clip((t - 0.05) / 0.02, 0, 1) * np.exp(-np.clip(t - 0.05, 0, None) / 0.22)
    y += 0.45 * phism(c, n, late, 700, 1800, 0.0015) + 0.25 * phism(c, n, late ** 2, 250, 4200, 0.001)   # earth and grit thrown out
    return y


@sfx("boss_snap", "Boss", "Old Mossback's head shoots out and its beak shuts", 2, 0.5, change="new")
def _(c):
    n = N(0.5)
    y = np.zeros(n)
    wn = N(0.16)
    place(y, 0.6 * sweep(c, wn, 350, 2200, 0.5) * np.sin(np.pi * np.linspace(0, 1, wn)) ** 1.5, 0)   # the neck through the air
    kn = N(0.2)
    clack = strike(c, kn, "stone", size=0.7, hard=1.5) + 0.5 * _crack(c, kn, 4, 0.01) + 0.4 * strike(c, kn, "body", size=0.6, hard=1.5)   # horn on horn: a dull clack, no ring
    place(y, clack, 0.13)
    place(y, 0.35 * clack, 0.13 + c.u(0.03, 0.04))
    return y


@sfx("boss_shake", "Boss", "Old Mossback shakes its shell: plates rattle, the tree thrashes", 2, 0.5, change="new")
def _(c):
    dur = 1.1
    n = N(dur)
    x = tt(n) / dur
    swell = np.sin(np.pi * np.clip(x * 1.1, 0, 1)) ** 0.8
    y = 0.5 * texture(c, n, 1800, 8000, 6, 18, 0.35) * swell                              # leaves
    y += 0.4 * norm(fft_filter(c.noise(n), bp(50, 140))) * swell                          # the body shuddering
    for k in range(12):                                                                   # shell plates knocking, never evenly
        at = 0.05 + k * 0.075 + c.u(-0.015, 0.015)
        amp = np.sin(np.pi * min(1, at / dur * 1.1)) ** 0.8 * c.u(0.6, 1)
        place(y, amp * strike(c, N(0.12), "stone" if k % 2 else "plank", size=c.u(1.3, 1.8), hard=1.2, damp=2), at)
    return y


@sfx("sporeling_land", "Boss", "a sporeling lands, tucked under its cap", 3, 0.25, change="new")
def _(c):
    n = N(0.25)
    return strike(c, n, "dirt", size=0.55, hard=1.2) + 0.5 * strike(c, n, "body", size=0.5) + 0.3 * phism(c, n, env_exp(n, 0.02, 0.002), 900, 2600, 0.0012)


@sfx("spore_puff", "Boss", "a sporecap or sporeling puffs its spores", 3, 0.25, change="new")
def _(c):
    n = N(0.4)
    t = tt(n)
    y = sweep(c, n, 2600, 700, 0.6) * np.clip(t / 0.012, 0, 1) * np.exp(-t / 0.09)        # a soft breath of air, falling
    return y + 0.3 * texture(c, n, 3000, 9000, 4, 30, 0.3) * np.exp(-t / 0.05)


# ================================================================== Nyxwing, the boss of Sugar rush
# One creature, one palette: "ensure all the sounds effect feels like they belong with each other". Every Nyxwing sound
# is made of the same few things, and of nothing else:
#   THROAT   one voice: the same formants, the same rasp, the same chest an octave under. Its pitches are one family:
#            the snarl and the roar about 110-160 Hz, the scream an octave over the roar, the takeoff climbing between.
#   CHORD    E flat and B flat (the song's key): every braam, every swell
#   boom()   the weight of a hit: a sub falling in pitch
#   riser()  air sucked into a hit
#   air      noise through moving bands: wings, wind, the spin, fire
#   nyx()    the same last stage on all: the top rolled off at 6 kHz and the same grit
#   "sky"    the same space on all: a three-second diffuse tail
# No bells, no chimes, no pings: those were the odd ones out (a music box beside a monster).
BEAT_S = 60 / 156
CHORD = ("Eb2", "Bb2", "Eb3")
ROAR_HZ = 112


def nyx(y):
    """The last stage every Nyxwing sound goes through: one top, one grit."""
    y = fft_filter(y, lambda f: 1 / np.sqrt(1 + (f / 6000) ** 4))
    return np.tanh(1.4 * norm(y)) / np.tanh(1.4)


def boom(n, f0=70.0, f1=30.0, tau=0.7, at=0.0):
    """A sub hit: a sine that falls from f0 to f1, a click on top."""
    t = tt(n) - at
    on = t >= 0
    tp = np.clip(t, 0, None)
    f = f1 + (f0 - f1) * np.exp(-tp / 0.12)
    y = np.sin(2 * np.pi * np.cumsum(f * on) / SR) * np.exp(-tp / tau) * np.clip(tp / 0.002, 0, 1) * on
    click = fft_filter(np.random.default_rng(int(f0)).standard_normal(n), bp(1500, 6000)) * np.exp(-tp / 0.004) * on
    return np.tanh(1.6 * y) / np.tanh(1.6) + 0.15 * norm(click)


def braam(n, notes=CHORD, attack=0.05, release=0.6, bright=1.0):
    """A deep brass chord: seven detuned saws a note, a filter that opens, saturation."""
    t = tt(n)
    y = np.zeros(n)
    for note in notes:
        f = hz(note)
        for d in np.linspace(-14, 14, 7):                                                  # cents
            ph = (f * 2 ** (d / 1200) * t + (d + 20) / 41) % 1
            y += 2 * ph - 1
    env = np.clip(t / attack, 0, 1) * np.clip((t[-1] - t) / release, 0, 1)
    cut = 300 + 2600 * bright * env ** 2                                                    # it opens as it swells
    lo, hi = fft_filter(y, lp(400)), fft_filter(y, lp(2900 * bright))
    mix = np.where(cut < 400, lo, lo + (hi - lo) * np.clip((cut - 400) / (2500 * bright), 0, 1))
    return np.tanh(2.2 * norm(mix) * env) / np.tanh(2.2)


def riser(c, n, f0=300, f1=4000):
    """Sucked in towards the hit at the end: air and a tone climbing, swelling to the last sample."""
    x = np.linspace(0, 1, n)
    air = sweep(c, n, f0, f1, 0.5, curve=x ** 2)
    tone = np.sin(2 * np.pi * np.cumsum(f0 / 4 * (f1 / f0) ** x) / SR)
    return (air + 0.4 * tone) * x ** 3


def nyx_throat(c, n, f0, mouth, rough=0.6):
    """THE voice: three throats a hair apart, a rasp, a chest an octave under, and air. Every cry of it is this."""
    y = np.zeros(n)
    for det in (0.985, 1.0, 1.017):
        y += norm(voice(n, f0 * det, lambda t: [(240 + 260 * mouth, 1.0), (620 + 500 * mouth, 0.6), (1500 + 900 * mouth, 0.25),
                                                  (2800, 0.06 + 0.1 * mouth)], 140, 70, c))
    rattle = 1 - rough * (0.5 + 0.5 * np.sin(np.pi * np.cumsum(f0) / SR))
    flutter = 1 + 0.3 * norm(fft_filter(c.noise(n), bp(18, 40)))
    y = norm(y * rattle * flutter)
    chest = norm(voice(n, f0 / 2, lambda t: [(160 + 120 * mouth, 1.0), (420, 0.4)], 90, 40, c))
    breath = norm(fft_filter(c.noise(n), bp(35, 110))) * np.clip(mouth, 0, 1)
    return y + 0.6 * chest + 0.4 * texture(c, n, 400, 5000, 6, 14, 0.4) * mouth + 0.4 * breath


def nyx_wings(c, n, at, near=1.0):
    """One beat of its wings: air pushed down and a thud of weight."""
    y = np.zeros(n)
    m = N(0.38)
    place(y, near * (sweep(c, m, 900, 150, 0.45) * np.sin(np.pi * np.linspace(0, 1, m)) ** 2 + 0.8 * boom(m, 85, 40, 0.09, 0.09)), at)
    return y


@sfx("drake_omen", "Boss", "far off in the night sky, before it is seen: a roar across the valley, the eclipse opening", 1, 0.4, kind="sky", change="new")
def _(c):
    dur = 3.2
    n = N(dur)
    t = tt(n)
    x = t / dur
    f0 = ROAR_HZ * 0.85 * (1 + 0.2 * np.sin(np.pi * np.clip(x / 0.4, 0, 1))) * (1 - 0.3 * x)
    far = fft_filter(nyx_throat(c, n, f0, np.clip(x / 0.2, 0, 1) * (1 - x), 0.65), lp(1400, 2))       # the air takes the highs away
    return nyx((0.8 * far + 0.6 * braam(n, CHORD[:2], attack=1.4, release=1.2, bright=0.5) + 0.5 * boom(n, 50, 28, 1.2)) * np.clip(t / 0.3, 0, 1))


@sfx("drake_descend", "Boss", "Nyxwing comes down out of the sky: falling wind, wings nearer on each beat, a brass swell sucked into the landing (sixteen beats)", 1, 0.5, kind="sky", change="new")
def _(c):
    dur = 16 * BEAT_S
    n = N(dur)
    t = tt(n)
    x = t / dur
    y = 0.5 * sweep(c, n, 2600, 380, 0.55, curve=x ** 1.5) * (0.15 + 0.85 * x ** 1.4) + 0.5 * norm(fft_filter(c.noise(n), bp(35, 110))) * x ** 2
    for k in range(16):                                                                    # a wing beat on each beat, each nearer
        y += nyx_wings(c, n, k * BEAT_S + 0.04, 0.1 + 0.8 * (k / 15) ** 1.4)
    y += 0.9 * braam(n, CHORD, attack=dur * 0.85, release=0.02) * x ** 2 + 1.1 * riser(c, n, 250, 5000) * np.clip((x - 0.75) / 0.25, 0, 1)
    return nyx(y * np.clip(t / 0.6, 0, 1))


@sfx("drake_roar", "Boss", "Nyxwing roars: when it lands on the drop, and when it blazes below half health", 1, 0.75, kind="sky", change="new")
def _(c):
    dur = 2.6
    n = N(dur)
    t = tt(n)
    x = t / dur
    f0 = ROAR_HZ * (1 + 0.28 * np.sin(np.pi * np.clip(x / 0.3, 0, 1))) * (1 - 0.38 * np.clip((x - 0.35) / 0.65, 0, 1))
    mouth = np.clip(x / 0.08, 0, 1) * (1 - 0.55 * np.clip((x - 0.55) / 0.45, 0, 1))
    y = nyx_throat(c, n, f0, mouth, 0.65) * np.clip(t / 0.02, 0, 1) * np.clip((dur - t) / 0.7, 0, 1) ** 0.8 + 0.8 * boom(n, 75, 30, 0.9)
    place(y, 0.75 * braam(N(1.6), CHORD, attack=0.01, release=1.3, bright=1.1), 0)
    return nyx(y)


@sfx("drake_scream", "Boss", "Nyxwing's mouth opens: a scream, the roar an octave up (every time its jaws open)", 4, 0.5, kind="sky", change="new")
def _(c):
    dur = [0.7, 0.85, 0.62, 0.95][c.v % 4]
    n = N(dur)
    t = tt(n)
    x = t / dur
    top = 2 * ROAR_HZ * [1.0, 0.92, 1.08, 0.97][c.v % 4]                                    # the roar an octave up: the same throat
    f0 = top * (0.8 + 0.3 * np.sin(np.pi * np.clip(x / 0.35, 0, 1))) * (1 - 0.2 * np.clip((x - 0.5) / 0.5, 0, 1))
    y = nyx_throat(c, n, f0, np.clip(x / 0.06, 0, 1) * (1 - 0.3 * x), 0.8) * np.clip(t / 0.015, 0, 1) * np.clip((dur - t) / 0.3, 0, 1)
    return nyx(y + 0.5 * boom(n, 70, 34, 0.25))


@sfx("drake_flap", "Boss", "one beat of Nyxwing's wings, on the kick", 4, 0.22, kind="sky", change="new")
def _(c):
    return nyx(nyx_wings(c, N(0.42), 0.0))


@sfx("drake_charge", "Boss", "dark light gathers at Nyxwing's jaws (the beat and a half before the breath)", 1, 0.45, kind="sky", change="new")
def _(c):
    dur = 1.5 * BEAT_S
    n = N(dur)
    x = tt(n) / dur
    return nyx(0.5 * nyx_throat(c, n, 0.7 * ROAR_HZ * (1 + 0.3 * x), 0.2 + 0.3 * x, 0.5) * x + riser(c, n, 400, 6000)
               + 0.6 * braam(n, CHORD[1:], attack=dur, release=0.01, bright=0.8))


@sfx("drake_breath", "Boss", "Nyxwing's void breath: a cone of dark fire (two beats)", 1, 0.6, kind="sky", change="new")
def _(c):
    dur = 2 * BEAT_S
    n = N(dur)
    t = tt(n)
    y = texture(c, n, 90, 5000, 9, 26, 0.95, tilt=-0.45) + 0.9 * boom(n, 70, 32, 0.5) + 0.5 * nyx_throat(c, n, 0.65 * ROAR_HZ * np.ones(n), 0.6, 0.7)
    return nyx(y * np.clip(t / 0.006, 0, 1) * np.clip((dur - t) / 0.25, 0, 1))


@sfx("drake_spin", "Boss", "Nyxwing spins in the starfall: its wings cut the air on every eighth note (three beats)", 1, 0.4, kind="sky", change="new")
def _(c):
    dur = 3 * BEAT_S
    n = N(dur)
    t = tt(n)
    x = t / dur
    passes = 0.5 + 0.5 * np.cos(2 * np.pi * t / (BEAT_S / 2))                               # a wing passes on each eighth
    air = sweep(c, n, 180, 900, 0.5, curve=0.3 + 0.7 * passes ** 2) * (0.25 + 0.75 * passes ** 3)
    hum = nyx_throat(c, n, 0.55 * ROAR_HZ * np.ones(n), 0.3, 0.6)
    beat = sum(boom(n, 75, 40, 0.07, k * BEAT_S / 2) for k in range(6)) * 0.35            # its weight on each turn
    return nyx((air + 0.6 * hum + beat) * np.clip(t / 0.05, 0, 1) * np.clip((dur - t) / 0.2, 0, 1) * (0.8 + 0.2 * x))


@sfx("drake_ring", "Boss", "a ring of stars thrown out of the spin (one on each of three beats)", 3, 0.45, kind="sky", change="new")
def _(c):
    n = N(0.7)
    t = tt(n)
    blast = sweep(c, n, 2400, 300, 0.5, curve=np.clip(t / 0.2, 0, 1)) * np.exp(-t / 0.09) * np.clip(t / 0.002, 0, 1)
    hit = braam(n, CHORD[[0, 1, 2][c.v % 3]:][:2] if c.v % 3 < 2 else CHORD, attack=0.005, release=0.5, bright=0.6 + 0.2 * (c.v % 3))
    return nyx(0.7 * blast + 1.1 * boom(n, 80 + 6 * (c.v % 3), 36, 0.3) + 0.45 * hit)


@sfx("drake_screech", "Boss", "Nyxwing tears itself off the ground and climbs out of sight (the eclipse begins)", 1, 0.6, kind="sky", change="new")
def _(c):
    dur = 1.6
    n = N(dur)
    t = tt(n)
    x = t / dur
    slam = nyx_wings(c, n, 0.0, 1.3)
    f0 = 0.7 * ROAR_HZ * (1 + 0.9 * np.clip(x / 0.55, 0, 1) ** 1.3) * (1 - 0.15 * np.clip((x - 0.6) / 0.4, 0, 1))
    cry = nyx_throat(c, n, f0, np.clip(x / 0.15, 0, 1) * (1 - 0.6 * x), 0.65) * np.clip((dur - t) / 0.6, 0, 1)
    away = sweep(c, n, 200, 2400, 0.5, curve=np.clip((x - 0.1) / 0.6, 0, 1)) * np.sin(np.pi * np.clip((x - 0.1) / 0.9, 0, 1)) ** 1.2
    return nyx(0.9 * slam + 1.0 * boom(n, 75, 28, 0.6) + 0.9 * cry + 0.5 * away + 0.4 * braam(n, CHORD[:2], attack=0.02, release=1.2, bright=0.8))


@sfx("drake_fall", "Boss", "Nyxwing falls out of the sky on you: air screaming down into the crash (the beat and a half before it)", 1, 0.5, kind="sky", change="new")
def _(c):
    dur = 1.5 * BEAT_S
    n = N(dur)
    x = tt(n) / dur
    return nyx(0.9 * sweep(c, n, 3400, 300, 0.5, curve=x ** 1.2) * x + riser(c, n, 120, 1500) + 0.5 * braam(n, CHORD[:2], attack=dur, release=0.01, bright=0.7))


@sfx("drake_crash", "Boss", "Nyxwing lands from the sky on the beat: a blow, a boom, a ring of light", 2, 0.8, kind="sky", change="new")
def _(c):
    n = N(1.6)
    t = tt(n)
    y = strike(c, n, "dirt", size=3.4, hard=1.0) + strike(c, n, "body", size=3.2, hard=1.0) + 1.3 * boom(n, 80, 26, 0.8)
    late = np.clip((t - 0.04) / 0.02, 0, 1) * np.exp(-np.clip(t - 0.04, 0, None) / 0.35)
    y += 0.5 * phism(c, n, late, 700, 1800, 0.0015) + 0.3 * phism(c, n, late ** 2, 300, 4200, 0.001)
    place(y, 0.6 * braam(N(1.0), CHORD, attack=0.005, release=0.8, bright=1.1), 0)
    return nyx(y)


@sfx("drake_whip", "Boss", "Nyxwing's tail sweeps round in a ring", 2, 0.55, kind="sky", change="new")
def _(c):
    n = N(0.7)
    t = tt(n)
    y = 0.8 * sweep(c, n, 180, 4200, 0.5, curve=np.clip(t / 0.25, 0, 1) ** 1.5) * np.sin(np.pi * np.clip(t / 0.3, 0, 1)) ** 2
    place(y, 0.8 * _crack(c, N(0.08), 6, 0.006), 0.24)
    return nyx(y + 1.0 * boom(n, 90, 34, 0.3, 0.24))


@sfx("drake_hurt", "Boss", "Nyxwing is hit: a short snarl", 3, 0.42, kind="sky", change="new")
def _(c):
    dur = c.u(0.4, 0.5)
    n = N(dur)
    t = tt(n)
    x = t / dur
    f0 = ROAR_HZ * c.u(1.25, 1.45) * (1.1 - 0.3 * x)
    y = nyx_throat(c, n, f0, np.clip(x / 0.12, 0, 1) * (1 - 0.4 * x), 0.65) * np.clip(t / 0.01, 0, 1) * np.clip((dur - t) / 0.15, 0, 1)
    return nyx(y + 0.6 * boom(n, 70, 35, 0.2))


# ================================================================== creatures: each one's own warning, blow and cry
# Picked by ear on the local creatures page (2026-11-25), out of three candidates a move. Each is reproduced sample-exactly:
# its own seed (`seed`: the candidate it was) and its own level, one variant.

def env(n, a, d, sustain=0.0):
    """Attack a seconds, then decay with time constant d (an optional floor)."""
    t = tt(n)
    return np.clip(t / max(a, 1e-4), 0, 1) * (sustain + (1 - sustain) * np.exp(-np.clip(t - a, 0, None) / d))


def swirl(n, f0, f1, depth=0.6):
    """Amplitude going round and round, faster and faster (a whirl)."""
    rate = np.geomspace(f0, f1, n)
    return 1 - depth * (0.5 + 0.5 * np.sin(2 * np.pi * np.cumsum(rate) / SR))


def snort(c, n, at, dur, lo=350, hi=2200, amp=1.0):
    """A blast of air through a snout: noise through nasal bands, a hard start, quick end."""
    k = N(dur)
    blast = (0.7 * norm(fft_filter(c.noise(k), bp(lo, hi))) + 0.5 * norm(fft_filter(c.noise(k), bp(lo * 0.5, lo * 1.4)))) * env(k, 0.008, dur / 3)
    y = np.zeros(n)
    return place(y, amp * blast, at)


def throat(c, n, f0, forms, bw=120, rough=0.0, harm=40):
    """voice() with an optional growl (the pitch pulses grouped in pairs: a rough old throat)."""
    y = norm(voice(n, f0, lambda t: forms, bw, harm, c))
    if rough:
        y *= 1 - rough * (0.5 + 0.5 * np.sin(np.pi * np.cumsum(f0) / SR))
    return y


def debris(c, n, at, rate=700, freq=1800, tau=0.18):
    t = tt(n)
    late = np.clip((t - at) / 0.02, 0, 1) * np.exp(-np.clip(t - at, 0, None) / tau)
    return phism(c, n, late, rate, freq, 0.0015)


@sfx("tusker_warn", "Creatures", "warning: it paws and snorts: a hoof scraping the earth twice, then one snort", 1, 0.38, seed="tusker_warn_B", change="new")
def _(c):
    n = N(0.8)
    y = np.zeros(n)
    for at in (0.0, 0.22):
        k = N(0.14)
        scrape = phism(c, k, env(k, 0.01, 0.05), 900, 1300, 0.002) + 0.7 * strike(c, k, "dirt", size=1.2, hard=0.8)
        place(y, scrape, at)
    return y + snort(c, n, 0.46, 0.2, amp=0.9)


@sfx("tusker_ram", "Creatures", "the charge lands: it rams you: four quick hoof beats close in, then the hit", 1, 0.48, seed="tusker_ram_B", change="new")
def _(c):
    n = N(0.6)
    y = np.zeros(n)
    for k, at in enumerate((0.0, 0.07, 0.14, 0.21)):
        place(y, (0.35 + 0.1 * k) * strike(c, N(0.08), "dirt", size=0.9, hard=1.3), at)
    place(y, strike(c, N(0.35), "body", size=1.5, hard=1.3), 0.28)
    return y


@sfx("tusker_hurt", "Creatures", "it is hit: two clipped grunts, offended more than hurt", 1, 0.36, seed="tusker_hurt_B", change="new")
def _(c):
    n = N(0.45)
    y = np.zeros(n)
    for at, f in ((0.0, 170), (0.2, 150)):
        g = N(0.14)
        place(y, throat(c, g, f * (1 - 0.2 * tt(g) / 0.14), [(450, 1.0), (1250, 0.5)], 160, rough=0.5) * env(g, 0.01, 0.05), at)
    return y


@sfx("pincer_warn", "Creatures", "warning: the big claw goes up: shell on shell, three quick clicks", 1, 0.3, seed="pincer_warn_A", change="new")
def _(c):
    n = N(0.4)
    y = np.zeros(n)
    for at in (0.0, 0.09, 0.15):
        place(y, strike(c, N(0.06), "ceramic", size=0.45, hard=2.2, damp=1.5), at)
    return y


@sfx("pincer_snap", "Creatures", "the snap: one hard chitin clack", 1, 0.42, seed="pincer_snap_A", change="new")
def _(c):
    n = N(0.25)
    return strike(c, n, "ceramic", size=0.55, hard=2.4) + 0.4 * _crack(c, n, 4, 0.006)


@sfx("pincer_hurt", "Creatures", "it is hit: a tiny high squeak", 1, 0.3, seed="pincer_hurt_B", change="new")
def _(c):
    n = N(0.18)
    return throat(c, n, 1400 - 500 * tt(n) / 0.18, [(2200, 1.0), (4200, 0.3)], 500, harm=8) * env(n, 0.01, 0.05)


@sfx("strawman_warn", "Creatures", "warning: its arms come up: dry straw crushed: a rustle with brittle snaps in it", 1, 0.34, seed="strawman_warn_A", change="new")
def _(c):
    n = N(0.5)
    x = tt(n) / 0.5
    sw = np.sin(np.pi * x) ** 0.8
    return 0.8 * texture(c, n, 1800, 9000, 6, 30, 0.3) * sw + 0.7 * phism(c, n, sw, 600, 3500, 0.001)


@sfx("strawman_swipe", "Creatures", "the swipe: the swipe throws a puff of hay", 1, 0.42, seed="strawman_swipe_C", change="new")
def _(c):
    n = N(0.45)
    t = tt(n)
    return sweep(c, n, 1500, 700, 0.6) * env(n, 0.01, 0.08) + 0.8 * phism(c, n, env(n, 0.01, 0.12), 900, 3000, 0.0012) + 0.4 * texture(c, n, 2000, 8000, 4, 25, 0.3) * np.exp(-t / 0.1)


@sfx("strawman_hurt", "Creatures", "it is hit: a blow into straw: a soft thud and bits flying", 1, 0.32, seed="strawman_hurt_A", change="new")
def _(c):
    n = N(0.35)
    return strike(c, n, "body", size=0.8, hard=0.7) + 0.6 * debris(c, n, 0.01, 800, 3200, 0.1)


@sfx("wyrm_warn", "Creatures", "warning: it rears up out of the water: water heaving and pouring off it, rising", 1, 0.38, seed="wyrm_warn_A", change="new")
def _(c):
    n = N(0.6)
    x = tt(n) / 0.6
    y = texture(c, n, 300, 4000, 8, 15, 0.9) * x ** 0.7 * np.clip((1 - x) / 0.15, 0, 1)
    return y + 0.5 * bubbles(c, np.zeros(n), 30, 1.5, 6, 0.55, amp=(0.1, 0.3), start=0.05)


@sfx("wyrm_lunge", "Creatures", "the lunge: it crashes through the water and bites", 1, 0.48, seed="wyrm_lunge_A", change="new")
def _(c):
    n = N(0.6)
    y = _splash(c, n, 1.4)
    return place(y, 0.8 * _chomp(c, N(0.12), 0.6, 12), 0.04)


@sfx("wyrm_hurt", "Creatures", "it is hit: it thrashes in the water", 1, 0.36, seed="wyrm_hurt_C", change="new")
def _(c):
    n = N(0.45)
    return _splash(c, n, 0.9) + 0.5 * _splash(c, n, 0.6)


@sfx("gustling_spin", "Creatures", "warning: it draws up and spins: a breathy whistle sliding up, like wind in a gap", 1, 0.34, seed="gustling_spin_C", change="new")
def _(c):
    n = N(0.6)
    x = tt(n) / 0.6
    centre = 700 * 2 ** (2 * x)
    tone = np.zeros(n)
    noise = c.noise(n)
    for lo, hi in zip(np.geomspace(400, 6000, 25), np.geomspace(400, 6000, 25)[1:]):
        band = fft_filter(noise, bp(lo, hi, 3))
        tone += band * np.exp(-((np.log(np.sqrt(lo * hi)) - np.log(centre)) / 0.08) ** 2)
    return norm(tone) * np.clip(x / 0.15, 0, 1) + 0.3 * sweep(c, n, 400, 2000, 0.6) * x


@sfx("gustling_snatch", "Creatures", "the snatch: your thing is gone: a little pop as it takes it, then a whoosh off", 1, 0.36, seed="gustling_snatch_A", change="new")
def _(c):
    n = N(0.45)
    y = 0.6 * strike(c, N(0.08), "body", size=0.4, hard=1.5)
    y = np.concatenate([y, np.zeros(n - len(y))])
    w = N(0.35)
    return place(y, sweep(c, w, 2200, 500, 0.5) * env(w, 0.02, 0.12), 0.05)


@sfx("gustling_scatter", "Creatures", "hit while it spins: it blows apart: the whistle falls and fades as it comes undone", 1, 0.34, seed="gustling_scatter_B", change="new")
def _(c):
    n = N(0.6)
    x = tt(n) / 0.6
    y = sweep(c, n, 2600, 300, 0.25, curve=x ** 0.6) * (1 - x) ** 1.5
    puff = norm(S["poof"](c))                                   # (the game's own poof, softly, under it)
    m = min(n, len(puff))
    y[:m] += 0.3 * puff[:m]
    return y


@sfx("grumblestump_warn", "Creatures", "warning: its arms go up: old wood straining, and a low voice inside it", 1, 0.4, seed="grumblestump_warn_A", change="new")
def _(c):
    n = N(0.8)
    x = tt(n) / 0.8
    creak = stickslip(c, n, 40 + 45 * x, [240, 560, 1150], 12) * np.sin(np.pi * x) ** 0.6
    groan = throat(c, n, 58 + 10 * x, [(200, 1.0), (450, 0.5)], 100, rough=0.5) * np.sin(np.pi * x) ** 0.8
    return creak + 0.5 * groan


@sfx("grumblestump_slam", "Creatures", "the slam: the ring of cracks: a heavy log hits the ground, earth thrown up", 1, 0.55, seed="grumblestump_slam_A", change="new")
def _(c):
    n = N(0.9)
    y = strike(c, n, "wood", size=2.4, hard=0.9) + strike(c, n, "dirt", size=2.4, hard=0.8)
    y += 0.8 * norm(fft_filter(c.noise(n), bp(40, 110))) * env_exp(n, 0.18, 0.004)
    return y + 0.45 * debris(c, n, 0.04, 700, 1800, 0.22)


@sfx("grumblestump_hurt", "Creatures", "it is hit: a blow on a trunk, and a short groan", 1, 0.38, seed="grumblestump_hurt_A", change="new")
def _(c):
    n = N(0.5)
    y = strike(c, n, "wood", size=1.5, hard=1.3)
    g = N(0.35)
    return place(y, 0.45 * throat(c, g, 70 - 12 * tt(g) / 0.35, [(220, 1.0), (500, 0.5)], 100, rough=0.5) * env(g, 0.02, 0.12), 0.04)


@sfx("snapbloom_warn", "Creatures", "warning: it rears back, mouth open: leaves rustle as it rears, a little hiss", 1, 0.3, seed="snapbloom_warn_A", change="new")
def _(c):
    n = N(0.6)
    x = tt(n) / 0.6
    return texture(c, n, 1800, 8000, 5, 25, 0.3) * np.sin(np.pi * x) ** 0.7 + 0.5 * norm(fft_filter(c.noise(n), bp(3500, 9000))) * np.clip((x - 0.4) / 0.2, 0, 1) * np.clip((1 - x) / 0.1, 0, 1)


@sfx("snapbloom_bite", "Creatures", "the bite: the bite, then its petals flutter back open", 1, 0.42, seed="snapbloom_bite_C", change="new")
def _(c):
    n = N(0.5)
    y = np.zeros(n)
    place(y, _chomp(c, N(0.18), 0.7, 22), 0)
    return place(y, 0.5 * texture(c, N(0.25), 1500, 6000, 5, 40, 0.4) * env(N(0.25), 0.02, 0.08), 0.15)


@sfx("snapbloom_hurt", "Creatures", "it is hit: a sigh, wilting", 1, 0.28, seed="snapbloom_hurt_C", change="new")
def _(c):
    n = N(0.45)
    return sweep(c, n, 2600, 700, 0.5) * env(n, 0.02, 0.15)


@sfx("hob_lit", "Creatures", "it is set down and catches: kindling pops twice, a soft roar settles in", 1, 0.38, seed="hob_lit_B", change="new")
def _(c):
    n = N(0.9)
    t = tt(n)
    roar = texture(c, n, 200, 2500, 8, 12, 0.8) * np.clip(t / 0.25, 0, 1) * np.exp(-np.clip(t - 0.3, 0, None) / 0.3)
    y = 0.7 * roar
    for at in (0.0, 0.27):
        place(y, _crack(c, N(0.05), 3, 0.004) * 0.8, at)
    return y


@sfx("hob_warn", "Creatures", "warning: it hunches, the fire draws in: air sucked into the firebox, rising, the flame going quiet", 1, 0.3, seed="hob_warn_A", change="new")
def _(c):
    n = N(0.55)
    x = tt(n) / 0.55
    return sweep(c, n, 300, 1800, 0.5, curve=x) * (0.45 + 0.55 * x) ** 1.3 * np.clip((1 - x) / 0.05, 0, 1)   # (heard at once: a game sound starts with its move)


@sfx("hob_burst", "Creatures", "the burst: its firebox blazes: a whoomp of flame, sparks flying out", 1, 0.52, seed="hob_burst_A", change="new")
def _(c):
    n = N(1.0)
    t = tt(n)
    whoomp = norm(fft_filter(c.noise(n), lambda f: lp(900, 2)(f) * hp(60, 2)(f))) * env(n, 0.015, 0.25)
    roar = texture(c, n, 200, 3000, 8, 15, 0.9) * env(n, 0.03, 0.35)
    sparks = phism(c, n, np.clip(t / 0.02, 0, 1) * np.exp(-t / 0.35), 500, 4500, 0.0008)
    return whoomp + 0.6 * roar + 0.5 * sparks


# ------------------------------------------------------------------ render all


def kweight(x):
    """ITU-R BS.1770 K-weighting in the frequency domain: +4 dB shelf above ~1.5 kHz, high-pass at 38 Hz."""
    n = len(x)
    f = np.fft.rfftfreq(n, 1 / SR)
    shelf = 1 + (10 ** (4 / 20) - 1) / (1 + (1681 / np.maximum(f, 1)) ** 2)
    low = 1 / np.sqrt(1 + (38 / np.maximum(f, 1e-3)) ** 4)
    return np.fft.irfft(np.fft.rfft(x) * shelf * low, n)


def loudness(st):
    """Loudest 100 ms as the ear weighs it, in dB."""
    k = kweight(st.mean(axis=0))
    w = min(len(k), N(0.1))
    c = np.cumsum(np.concatenate([[0], k ** 2]))
    return 10 * np.log10(np.max(c[w:] - c[:-w]) / w + 1e-12)


def render(name, v):
    """One finished variant of one sound: stereo float array at SR, levelled and ready to write."""
    m = META[name]
    raw = S[name](Ctx(m["seed"], v))
    if m["vary"]:
        raw = resize(raw, SIZES[v % len(SIZES)])
    st = finish(raw, m["kind"])
    want = 20 * np.log10(m["loud"]) - 9                                  # perceived level, per sound; every variant matches
    for _ in range(6):
        st *= 10 ** ((want - loudness(st)) / 20)
        if np.abs(st).max() <= 0.95:
            break
        st = 0.95 * np.tanh(st / 0.95)      # a soft ceiling. (Scaling the whole sound down to fit its peak left the sharpest
                                            # ones, chop, mine, snap, 1 to 4 dB under the level they were given.)
    return st * min(1, 0.95 / np.abs(st).max())


def write_wav(path, st):
    pcm = (np.clip(st, -1, 1) * 32767).round().astype("<i2").T.copy()
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("*.wav"):
        old.unlink()
    manifest = {}
    for name in S:
        m = META[name]
        files = []
        for v in range(m["variants"]):
            st = render(name, v)
            f = f"{name}_{v}.wav"
            write_wav(OUT / f, st)
            files.append(f)
        manifest[name] = {"category": m["cat"], "when": m["when"], "files": files, "change": m["change"]}
        print(f"  {name:16s} {m['cat']:10s} x{m['variants']}  {st.shape[1] / SR:.2f}s  {m['kind']}")
    (OUT / "sfx.json").write_text(json.dumps(manifest, indent=1))
    (OUT / "map.json").write_text(Path(__file__).with_name("sfx_map.json").read_text())
    print(f"{len(manifest)} sounds, {sum(len(v['files']) for v in manifest.values())} files")
