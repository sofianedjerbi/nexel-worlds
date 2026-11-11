"""Adventurous cozy loop to play under the game for 10-20 minutes. Cozy village x blocky meadow x setting out.

Pure numpy, 48 kHz, 80 BPM, 48 bars = 144 s, seamless. The theme starts in bar 1.

The theme (8 bars, D major with a borrowed C chord for the "setting out" colour):
    D    D5 A5 D6~~~~      climb to the octave: short-short-long
    C    C6~~ G5 E5~~      fall through the C chord: long-short-long (the mirror)
    G    G5 A5 B5~~~~      step up
    D    A5~~~~~~          breathe
    Bm   D5 A5 D6~~~~      climb again
    G    D6~~ B5 G5~~      fall again
    Em   G5 F#5 E5~~~~     step down (mirror of bar 3)
    A    E5~~ B4 C#5~~~~   leading tone, pulls home to D

Every part has its own timbre family, so the ear can tell them apart:
    ocarina (breathy lead), chip square (nasal, buzzy), harp (plucked ostinato), strings (bowed),
    pizzicato upright bass, glockenspiel (metal accents), felt piano (only in the breathers),
    soft frame drum + shaker, wind.

Checks: registers never overlap (bass < harp/strings < melody < glock), no clashing notes.
All effects are circular, so the loop has no seam.

    uv run python music/compose.py      # writes music/site/audio/*.wav + track.json
"""

from pathlib import Path
import json
import wave

import numpy as np

SR = 48000
BPM = 80
BEAT = 60 / BPM
BARS = 48
LOOP_S = BARS * 4 * BEAT
LOOP_N = int(round(LOOP_S * SR))
TAIL = 6 * SR
OUT = Path(__file__).with_name("site") / "audio"
rng = np.random.default_rng(8)

PC = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


def midi(name):
    pc, rest = PC[name[0]], name[1:]
    while rest and rest[0] in "#b":
        pc += 1 if rest[0] == "#" else -1
        rest = rest[1:]
    return 12 * (int(rest) + 1) + pc


def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def t_of(slot):  # eighth notes, 8 per bar
    return slot * BEAT / 2


def tt(n):
    return np.arange(n) / SR


def fft_filter(y, resp):
    n = len(y)
    m = 1 << int(np.ceil(np.log2(n + 2048)))
    return np.fft.irfft(np.fft.rfft(y, m) * resp(np.fft.rfftfreq(m, 1 / SR)), m)[:n]


def lp(fc, order=2):
    return lambda f: 1 / np.sqrt(1 + (f / fc) ** (2 * order))


def hp(fc, order=2):
    return lambda f: 1 / np.sqrt(1 + (fc / np.maximum(f, 1e-3)) ** (2 * order))


def bp(lo, hi):
    return lambda f: hp(lo)(f) * lp(hi)(f)


def peak(fc, q, gain):
    """A resonant bump (body / formant), as a gain curve."""
    return lambda f: 1 + gain / (1 + ((f - fc) / (fc / q)) ** 2)


def wobble(t_abs, depth=1.0):
    """Gentle tape wow in semitones; whole cycles per loop, so seamless."""
    return depth * (0.03 * np.sin(2 * np.pi * 41 / LOOP_S * t_abs) + 0.02 * np.sin(2 * np.pi * 13 / LOOP_S * t_abs + 1))


def phase(f, n, t0, semis=0.0, wob=1.0):
    return 2 * np.pi * np.cumsum(f * 2 ** ((wobble(t0 + tt(n), wob) + semis) / 12)) / SR


def vibrato(n, depth, rate, delay, jitter=0.0):
    t = tt(n)
    ramp = np.clip((t - delay) / 0.35, 0, 1)
    return depth * ramp * np.sin(2 * np.pi * rate * t + jitter)


def release(t, dur, r):
    return np.where(t > dur, np.exp(-(t - dur) / r), 1.0)


# ------------------------------------------------------------------ instruments (f, dur, vel, t0)

def ocarina(f, dur, vel, t0):
    """Breathy vessel flute: nearly pure tone, a chiff of air on the attack, singing vibrato."""
    n = int((dur + 0.5) * SR)
    t = tt(n)
    ph = phase(f, n, t0, -0.25 * np.exp(-t / 0.03) + vibrato(n, 0.2, 5.4, 0.25), wob=0.3)
    tone = np.sin(ph) + 0.07 * np.sin(2 * ph) + 0.12 * np.sin(3 * ph)
    breath = fft_filter(rng.standard_normal(n), bp(f * 0.8, f * 3)) * (0.05 + 0.25 * np.exp(-t / 0.04))
    env = np.clip(t / 0.05, 0, 1) * release(t, dur, 0.12) * (0.9 + 0.1 * np.exp(-t / 0.2))
    return 0.36 * vel * (tone + breath) * env


def chip_square(f, dur, vel, t0):
    """Nasal 12.5% pulse, slides in from below, quick vibrato: unmistakably a chip."""
    n = int((dur + 0.25) * SR)
    t = tt(n)
    ph = phase(f, n, t0, -0.6 * np.exp(-t / 0.018) + vibrato(n, 0.15, 6.2, 0.2), wob=0.2)
    y = np.zeros(n)
    for k in range(1, 50):
        if k * f > 9000:
            break
        y += np.sin(np.pi * k * 0.125) / k * np.sin(k * ph) / (1 + (k * f / 5500) ** 2)
    env = np.clip(t / 0.004, 0, 1) * (0.7 + 0.3 * np.exp(-t / 0.15)) * release(t, dur, 0.06)
    return 0.3 * vel * y * env


def harp(f, dur, vel, t0):
    """Plucked string: plucked near the end (bright), upper partials die fast, a small wooden body."""
    n = int(2.6 * SR)
    t = tt(n)
    ph = phase(f, n, t0, wob=0.3)
    y = np.zeros(n)
    for k in range(1, 24):
        fk = k * np.sqrt(1 + 0.0001 * k * k)
        if f * fk > 9000:
            break
        y += np.sin(np.pi * k * 0.18) / k * np.sin(fk * ph) * np.exp(-t * (0.9 + 0.55 * k * k ** 0.5))
    y += fft_filter(rng.standard_normal(n), bp(2000, 7000)) * np.exp(-t / 0.004) * 0.15
    y = fft_filter(y, peak(260, 2.0, 0.8))
    return 0.3 * vel * y * np.clip(t / 0.0015, 0, 1)


def strings(f, dur, vel, t0):
    """Bowed ensemble: three players with their own vibrato, a bright bow, a slow bow-in."""
    n = int((dur + 1.0) * SR)
    t = tt(n)
    out = np.zeros((2, n))
    for j, (det, pan) in enumerate(((-8, 0.15), (0, 0.5), (9, 0.85))):
        ph = phase(f, n, t0, det / 100 + vibrato(n, 0.12, 5.0 + 0.4 * j, 0.15, j * 2.1))
        y = sum(np.sin(k * ph) / k / (1 + (k * f / 2600) ** 2) for k in range(1, 26) if k * f < 9000)
        out[0] += np.cos(pan * np.pi / 2) * y
        out[1] += np.sin(pan * np.pi / 2) * y
    out = np.stack([fft_filter(c, lambda fr: peak(1100, 1.5, 1.2)(fr) * peak(2800, 2.5, 0.6)(fr)) for c in out])
    env = np.clip(t / 0.45, 0, 1) ** 1.5 * release(t, dur, 0.45)
    return 0.035 * vel * out * env


def pizz_bass(f, dur, vel, t0):
    """Upright bass pizzicato: a woody thump, round fundamental, short."""
    n = int((dur + 0.5) * SR)
    t = tt(n)
    ph = phase(f, n, t0, wob=0.2)
    y = sum(np.sin(np.pi * k * 0.25) / k * np.sin(k * ph) * np.exp(-t * (3 + 6 * k)) for k in range(1, 12))
    y += 0.6 * np.sin(ph) * np.exp(-t / 0.6)
    thump = fft_filter(rng.standard_normal(n), lp(400)) * np.exp(-t / 0.012) * 0.3
    env = np.clip(t / 0.003, 0, 1) * release(t, dur, 0.1)
    return 0.5 * vel * (y + thump) * env


def glock(f, dur, vel, t0):
    n = int(2.4 * SR)
    t = tt(n)
    y = (np.sin(2 * np.pi * f * t) * np.exp(-t / 0.9)
         + 0.45 * np.sin(2 * np.pi * f * 2.76 * t) * np.exp(-t / 0.3)
         + 0.2 * np.sin(2 * np.pi * f * 5.40 * t) * np.exp(-t / 0.1)
         + 0.08 * np.sin(2 * np.pi * f * 8.93 * t) * np.exp(-t / 0.04))
    return 0.13 * vel * y * np.clip(t / 0.0008, 0, 1)


def felt_piano(f, dur, vel, t0):
    """Muffled felt piano for the quiet breathers."""
    n = int((dur + 3.0) * SR)
    t = tt(n)
    bright = 800 + 1400 * vel
    out = []
    for det in (-1.5, 1.5):
        ph = phase(f, n, t0, det / 100, wob=1.2)
        y = np.zeros(n)
        for k in range(1, 12):
            fk = k * np.sqrt(1 + 0.0003 * k * k)
            if f * fk > 7000:
                break
            tau = 4.0 / k ** 0.7 * (220 / max(f, 110)) ** 0.35
            y += (1 / k ** 1.2) / (1 + (f * fk / bright) ** 2) * np.sin(fk * ph) * (0.6 * np.exp(-t / (tau * 0.3)) + 0.4 * np.exp(-t / tau))
        out.append(y)
    env = np.clip(t / 0.005, 0, 1) * release(t, dur, 0.4)
    return 0.34 * vel * np.stack(out) * env


def _frame_drum():
    n = int(0.5 * SR)
    t = tt(n)
    body = np.sin(2 * np.pi * np.cumsum(85 + 70 * np.exp(-t / 0.025)) / SR) * np.exp(-t / 0.16)
    skin = fft_filter(rng.standard_normal(n), bp(300, 2500)) * np.exp(-t / 0.02) * 0.25
    return (body + skin) * np.clip(t / 0.002, 0, 1) * 0.35


def _shaker():
    n = int(0.1 * SR)
    t = tt(n)
    return fft_filter(rng.standard_normal(n), bp(4500, 10000)) * np.clip(t / 0.012, 0, 1) * np.exp(-t / 0.03) * 0.2


HITS = {"drum": [_frame_drum() for _ in range(3)], "shaker": [_shaker() for _ in range(8)]}


def hit(kind):
    def play(f, dur, vel, t0):
        v = HITS[kind]
        return vel * v[rng.integers(len(v))]
    play.unpitched = True
    return play


DRUM, SHAKER = hit("drum"), hit("shaker")

# ------------------------------------------------------------------ harmony: one 8-bar cycle

CHORDS = {"Dadd9": "D F# A E", "Cadd9": "C E G D", "Gadd9": "G B D A", "Bm7": "B D F# A",
          "Em9": "E G B D F#", "Aadd9": "A C# E B"}
PROG = ["Dadd9", "Cadd9", "Gadd9", "Dadd9", "Bm7", "Gadd9", "Em9", "Aadd9"]


def chord_at_bar(bar):
    return PROG[bar % 8]


def pcs(ch):
    return [midi(p + "4") % 12 for p in CHORDS[ch].split()]


def place(pc, lo):
    return lo + (pc - lo) % 12


def lh_notes(ch):
    """root, fifth, colour (add9 / 7th), third an octave up: G2..G4."""
    p = pcs(ch)
    r = place(p[0], 43)
    fifth = place(p[2], r + 1)
    color = place(p[3], fifth + 1)
    third = place(p[1], color + 1)
    return r, fifth, color, third


def string_voicing(ch):
    p = pcs(ch)
    return sorted(place(x, 57) for x in (p[1], p[2], p[3]))   # rootless, A3..G#4


# ------------------------------------------------------------------ the theme

THEME = [
    [(0, 2, "D5"), (2, 1, "A5"), (3, 5, "D6")],
    [(0, 3, "C6"), (3, 1, "G5"), (4, 4, "E5")],
    [(0, 2, "G5"), (2, 2, "A5"), (4, 4, "B5")],
    [(0, 6, "A5")],
    [(0, 2, "D5"), (2, 1, "A5"), (3, 5, "D6")],
    [(0, 3, "D6"), (3, 1, "B5"), (4, 4, "G5")],
    [(0, 2, "G5"), (2, 2, "F#5"), (4, 4, "E5")],
    [(0, 3, "E5"), (3, 1, "B4"), (4, 4, "C#5")],
]
OSTINATO = [(0, "r", 1.0), (1, "fifth", 0.7), (2, "color", 0.65), (3, "third", 0.85),
            (4, "color", 0.6), (5, "fifth", 0.6), (6, "third", 0.8), (7, "color", 0.55)]
GLOCK = {1: (4, "E6"), 3: (2, "F#6"), 5: (4, "G6"), 7: (4, "A6")}   # accents echoing each phrase end

PLAN = ["theme", "theme+march", "breather", "chip", "full", "fragments"]
SECTION_NAMES = ["theme", "march", "breather", "chip theme", "all together", "fragments"]

STEMS = ["lead", "chip", "harp", "strings", "bass", "keys", "perc"]
events = []  # (t, dur, midi, vel, inst, pan, stem, rev, echo)


def note(slot, length, m, vel, inst, stem, pan=0.0, rev=0.25, echo=0.0, human=True):
    t0, dur = t_of(slot), t_of(slot + length) - t_of(slot)
    if human:
        t0 += abs(rng.normal(0, 0.008))
        vel *= 1 + rng.normal(0, 0.05)
    events.append((t0, dur, m, vel, inst, pan, stem, rev, echo))


for bar in range(BARS):
    cyc, i = bar // 8, bar % 8
    ch = chord_at_bar(bar)
    s0 = bar * 8
    plan = PLAN[cyc]
    lh = dict(zip(("r", "fifth", "color", "third"), lh_notes(ch)))
    root = place(pcs(ch)[0], 33)

    # --- melody
    for slot, ln, n in THEME[i]:
        m = midi(n)
        if plan in ("theme", "theme+march", "full"):
            note(s0 + slot, ln, m, 0.9, ocarina, "lead", 0.0, rev=0.25, echo=0.1)
        if plan == "chip":
            note(s0 + slot, ln, m, 0.9, chip_square, "chip", 0.0, rev=0.2, echo=0.25)
        if plan == "full":
            note(s0 + slot, ln, m, 0.45, chip_square, "chip", 0.3, rev=0.2, echo=0.15)
        if plan == "fragments" and i in (0, 1, 4, 5):
            note(s0 + slot, ln + (2 if slot >= 3 else 0), m, 1.3, glock, "keys", 0.2, rev=0.4, echo=0.35)
    if plan in ("theme+march", "full", "chip") and i in GLOCK:
        slot, n = GLOCK[i]
        note(s0 + slot, 2, midi(n), 0.7, glock, "keys", 0.45, rev=0.4, echo=0.3)

    # --- accompaniment: harp ostinato, or slow felt piano in the breather
    if plan == "breather":
        note(s0, 8, lh["r"], 0.42, felt_piano, "keys", -0.3, rev=0.45)
        note(s0 + 0.2, 8, lh["fifth"], 0.32, felt_piano, "keys", -0.2, rev=0.45)
        note(s0 + 3, 5, lh["color"], 0.28, felt_piano, "keys", 0.0, rev=0.5)
        note(s0 + 5, 3, lh["third"], 0.26, felt_piano, "keys", 0.15, rev=0.5)
        if i in (1, 5):   # the hook, remembered, on the piano, once in a while
            for slot, ln, n in THEME[i - 1]:
                note(s0 + slot, ln, midi(n), 0.45, felt_piano, "keys", 0.1, rev=0.5, echo=0.2)
    else:
        for slot, which, acc in OSTINATO:
            if plan == "fragments" and slot % 2:
                continue
            note(s0 + slot, 8 - slot, lh[which], 0.75 * acc, harp, "harp", -0.4 + 0.1 * slot, rev=0.28)

    # --- strings: bowed chord each bar; louder in the march and the finale
    if plan != "fragments" or i < 4:
        sv = {"theme": 0.6, "theme+march": 0.9, "breather": 0.55, "chip": 0.5, "full": 1.0, "fragments": 0.5}[plan]
        for m in string_voicing(ch):
            note(s0, 8, m, sv, strings, "strings", 0.0, rev=0.45, human=False)

    # --- pizzicato bass on 1 and 3
    note(s0, 3, root, 0.85, pizz_bass, "bass", 0.0, rev=0.08)
    if plan != "breather":
        note(s0 + 4, 3, root + 7 if i % 2 else root, 0.65, pizz_bass, "bass", 0.0, rev=0.08)

    # --- percussion: a gentle march (boom . . b boom . b .) in march and finale, shaker under any theme
    if plan in ("theme+march", "full"):
        for slot, v in ((0, 1.0), (3, 0.55), (4, 0.8), (6, 0.5)):
            note(s0 + slot, 1, 60, v, DRUM, "perc", 0.0, rev=0.15)
    if plan in ("theme", "theme+march", "chip", "full"):
        for slot in (1, 3, 5, 7):
            note(s0 + slot, 1, 60, 0.9 if slot in (3, 7) else 0.6, SHAKER, "perc", 0.35, rev=0.1)


# ------------------------------------------------------------------ checks

def held_notes():
    return [(t, t + d, m) for t, d, m, v, inst, *_ in events
            if inst in (harp, strings, pizz_bass) or (inst is felt_piano and m < 69)]


def clash_report():
    """Melody voices vs sounding accompaniment: minor 9ths always, off-chord semitones / tritones."""
    held = held_notes()
    bad = []
    for t, d, m, v, inst, *_ in events:
        if getattr(inst, "unpitched", False) or (t, t + d, m) in held:
            continue
        ch = chord_at_bar(int(t / (4 * BEAT)))
        for a, b, h in held:
            if a <= t < b - 0.05 and h != m:
                iv = (m - h) % 12
                if iv == 1 or (iv in (11, 6) and m % 12 not in pcs(ch)):
                    bad.append((round(t, 2), m, h, iv))
    return bad


def accomp_clashes():
    out = []
    for ch in set(PROG):
        v = sorted(set(lh_notes(ch) + tuple(string_voicing(ch))))
        out += [(ch, a, b) for a, b in zip(v, v[1:]) if b - a == 1]
    return out


def registers():
    return {"lowest melody": min(midi(n) for bar in THEME for *_, n in bar),
            "highest accompaniment": max(max(lh_notes(c)) for c in PROG),
            "highest strings": max(max(string_voicing(c)) for c in PROG)}


# ------------------------------------------------------------------ render

def fold(x):
    out = x[:, :LOOP_N].copy()
    out[:, :TAIL] += x[:, LOOP_N:LOOP_N + TAIL]
    return out


def circ(x, resp):
    return np.fft.irfft(np.fft.rfft(x, axis=-1) * resp(np.fft.rfftfreq(LOOP_N, 1 / SR)), LOOP_N, axis=-1)


def echo_fx(mono, beats=0.75, fb=0.4):
    d = int(beats * BEAT * SR)
    f = np.fft.rfftfreq(LOOP_N, 1 / SR)
    k = np.arange(len(f))
    z = fb * lp(3000, 1)(f) * hp(300, 1)(f) * np.exp(-2j * np.pi * k * d / LOOP_N)
    x = np.fft.rfft(mono)
    return 0.5 * np.stack([np.fft.irfft(x * z / (1 - z ** 2), LOOP_N), np.fft.irfft(x * z ** 2 / (1 - z ** 2), LOOP_N)])


def make_ir(seconds=4.5, tau_dark=0.5, tau_bright=0.2, predelay=0.022):
    n = int(seconds * SR)
    t = tt(n)
    irs = []
    for _ in range(2):
        dark = fft_filter(rng.standard_normal(n), lp(2000)) * np.exp(-t / tau_dark)
        bright = fft_filter(rng.standard_normal(n), hp(2000)) * np.exp(-t / tau_bright) * 0.45
        ir = (dark + bright) * np.clip(t / 0.06, 0, 1)
        ir[: int(predelay * SR)] = 0
        ir /= np.sqrt(np.sum(ir ** 2))
        padded = np.zeros(LOOP_N)
        padded[:n] = ir
        irs.append(np.fft.rfft(padded))
    return irs


def wind_bed():
    t = np.arange(LOOP_N) / SR
    air = circ(rng.standard_normal((2, LOOP_N)), lambda f: bp(150, 1100)(f) / np.sqrt(np.maximum(f, 20) / 150))
    breathe = 0.5 + 0.5 * np.sin(2 * np.pi * 4 / LOOP_S * t) * np.sin(2 * np.pi * 9 / LOOP_S * t + 0.7)
    return 0.01 * air / np.abs(air).max() * breathe


def limiter_gain(x, ceil=0.9, block=48):
    pk = np.abs(x).max(axis=0)
    nb = LOOP_N // block
    pb = pk[: nb * block].reshape(nb, block).max(axis=1)
    g = np.minimum(1, ceil / np.maximum(pb, 1e-9))
    w = 8
    gm = np.min([np.roll(g, s) for s in range(-w, w + 1)], axis=0)
    gs = np.mean([np.roll(gm, s) for s in range(-w // 2, w // 2 + 1)], axis=0)
    full = np.repeat(gs, block)
    return np.concatenate([full, np.full(LOOP_N - len(full), full[-1])])


def render():
    n = LOOP_N + TAIL
    buses = {s: {k: np.zeros((2, n)) for k in ("dry", "rev", "echo")} for s in STEMS}
    for t, dur, m, vel, inst, pan, stem, rs, es in events:
        y = np.atleast_2d(inst(hz(m), dur, vel, t))
        if y.shape[0] == 1:
            y = np.vstack([y, y])
        i = int(round(t * SR)) % LOOP_N
        y = y[:, : n - i]
        a = (pan + 1) * np.pi / 4
        y = y * np.array([[np.cos(a)], [np.sin(a)]]) * np.sqrt(2)
        b = buses[stem]
        b["dry"][:, i:i + y.shape[1]] += y
        b["rev"][:, i:i + y.shape[1]] += rs * y
        if es:
            b["echo"][:, i:i + y.shape[1]] += es * y

    irs = make_ir()
    # (dry amount, dry darkness): lead and chip up front, harp middle, strings and keys a step back
    plane = {"lead": (1.0, 9000), "chip": (1.0, 10000), "harp": (0.9, 8000), "strings": (0.75, 5000),
             "bass": (1.0, 3000), "keys": (0.8, 8000), "perc": (0.95, 9000)}
    stems = {}
    for s in STEMS:
        b = {k: fold(v) for k, v in buses[s].items()}
        echo = echo_fx(b["echo"].mean(axis=0))
        send = circ(b["rev"] + 0.4 * echo, hp(200, 1))
        wet = np.stack([np.fft.irfft(np.fft.rfft(send[c]) * irs[c], LOOP_N) for c in range(2)])
        dry_amt, dark = plane[s]
        stems[s] = dry_amt * circ(b["dry"], lp(dark, 1)) + echo + 0.75 * wet
    stems["perc"] = stems["perc"] + wind_bed()

    stems["bass"] = circ(stems["bass"], lambda f: hp(35, 2)(f))
    for s in ("lead", "chip", "harp", "strings", "keys"):
        stems[s] = circ(stems[s], hp(120, 1))
    gains = {"lead": 1.0, "chip": 1.7, "harp": 0.8, "strings": 0.8, "bass": 0.85, "keys": 0.9, "perc": 0.9}
    for s in STEMS:
        stems[s] = circ(stems[s] * gains[s], lambda f: hp(25, 2)(f) * lp(16000, 2)(f))

    pre = sum(stems.values())
    norm = 10 ** (-18 / 20) / np.sqrt(np.mean(pre ** 2))
    g = limiter_gain(pre * norm)
    for s in STEMS:
        stems[s] = stems[s] * norm * g
    return sum(stems.values()), stems


def write_wav(path, x):
    pcm = (np.clip(x, -1, 1) * 32767).round().astype("<i2").T.copy()
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


if __name__ == "__main__":
    print("registers:", registers())
    print("accompaniment semitone clusters:", accomp_clashes())
    bad = clash_report()
    print(f"clash check: {len(bad)}", bad[:12])
    master, stems = render()
    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("stem_*.wav"):
        old.unlink()
    write_wav(OUT / "master.wav", master)
    for s, x in stems.items():
        write_wav(OUT / f"stem_{s}.wav", x)
    meta = {"title": "Meadow Road", "bpm": BPM, "key": "D major", "mood": "cozy adventure", "bars": BARS,
            "seconds": LOOP_S, "beats_per_hop": 1,
            "sections": [{"id": str(k + 1), "name": nm, "bar": k * 8, "t": k * 32 * BEAT} for k, nm in enumerate(SECTION_NAMES)],
            "stems": STEMS}
    (OUT / "track.json").write_text(json.dumps(meta, indent=1))
    rms = np.sqrt(np.mean(master ** 2))
    print(f"{len(events)} notes, {LOOP_S:.0f}s loop, peak {np.abs(master).max():.3f}, rms {20 * np.log10(rms):.1f} dBFS")
    for s, x in stems.items():
        print(f"  {s:8s} rms {20 * np.log10(np.sqrt(np.mean(x ** 2)) + 1e-12):6.1f} dBFS")
