"""Meadow Road: an adventurous, cozy loop to play under the game. About 4.8 minutes, seamless.

Pure numpy, 48 kHz, 80 BPM, 96 bars = 288 s. The theme starts in bar 1.

Form, in 8-bar blocks (A = theme, B = contrast in B minor, rest = no melody):
    A piano | A flute | B piano | A flute+strings, march | rest piano | B flute
    A solo strings | rest guitar | A flute, march | B solo strings | A piano | rest
The theme comes back six times, each time on a different voice; the B section gives it a story.

Harmony: D major with 9ths, 7ths and sus chords; B borrows C major 7 for the "road ahead" colour.
The melody rests on chord colours (9ths, 7ths) instead of spelling out triads.

Voices, each from its own family: concert flute, felt piano, nylon guitar (ostinato),
string ensemble, solo strings, pizzicato upright bass, frame drum + shaker, wind.

Checks: registers never overlap (bass < guitar/strings pad < melody), no clashing notes,
per-section loudness printed. All effects circular, so the loop has no seam.

    uv run python music/compose.py      # writes music/site/audio/*.wav + track.json
"""

from pathlib import Path
import json
import wave

import numpy as np

SR = 48000
BPM = 80
BEAT = 60 / BPM
BARS = 96
LOOP_S = BARS * 4 * BEAT
LOOP_N = int(round(LOOP_S * SR))
TAIL = 6 * SR
OUT = Path(__file__).with_name("site") / "audio"
rng = np.random.default_rng(21)

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
    return lambda f: 1 + gain / (1 + ((f - fc) / (fc / q)) ** 2)


def wobble(t_abs, depth=1.0):
    return depth * (0.03 * np.sin(2 * np.pi * 61 / LOOP_S * t_abs) + 0.02 * np.sin(2 * np.pi * 23 / LOOP_S * t_abs + 1))


def phase(f, n, t0, semis=0.0, wob=1.0):
    return 2 * np.pi * np.cumsum(f * 2 ** ((wobble(t0 + tt(n), wob) + semis) / 12)) / SR


def vibrato(n, depth, rate, delay, jitter=0.0):
    t = tt(n)
    return depth * np.clip((t - delay) / 0.4, 0, 1) * np.sin(2 * np.pi * rate * t + jitter)


def release(t, dur, r):
    return np.where(t > dur, np.exp(-(t - dur) / r), 1.0)


# ------------------------------------------------------------------ instruments (f, dur, vel, t0)

def flute(f, dur, vel, t0):
    """Concert flute: airy but full, a soft chiff, vibrato that blooms on long notes."""
    n = int((dur + 0.5) * SR)
    t = tt(n)
    ph = phase(f, n, t0, -0.12 * np.exp(-t / 0.04) + vibrato(n, 0.16, 5.0, 0.3), wob=0.3)
    tone = np.sin(ph) + 0.32 * np.sin(2 * ph) + 0.12 * np.sin(3 * ph) + 0.05 * np.sin(4 * ph)
    air = fft_filter(rng.standard_normal(n), bp(f * 1.5, 9000)) * (0.035 + 0.18 * np.exp(-t / 0.05))
    swell = 0.85 + 0.15 * np.clip(t / 0.8, 0, 1)
    env = np.clip(t / 0.07, 0, 1) * release(t, dur, 0.15) * swell
    return 0.3 * vel * (tone + air) * env


def felt_piano(f, dur, vel, t0):
    """Felt piano: warm, slightly inharmonic, long ring, tiny stereo detune."""
    n = int((dur + 3.0) * SR)
    t = tt(n)
    bright = 900 + 1800 * vel
    out = []
    for det in (-1.5, 1.5):
        ph = phase(f, n, t0, det / 100, wob=1.0)
        y = np.zeros(n)
        for k in range(1, 14):
            fk = k * np.sqrt(1 + 0.0003 * k * k)
            if f * fk > 8000:
                break
            tau = 4.0 / k ** 0.7 * (220 / max(f, 110)) ** 0.35
            y += (1 / k ** 1.15) / (1 + (f * fk / bright) ** 2) * np.sin(fk * ph) * (0.6 * np.exp(-t / (tau * 0.3)) + 0.4 * np.exp(-t / tau))
        out.append(y)
    thump = fft_filter(rng.standard_normal(n), lp(600)) * np.exp(-t / 0.015) * 0.08
    env = np.clip(t / 0.004, 0, 1) * release(t, dur, 0.35)
    return 0.34 * vel * np.stack([out[0] + thump, out[1] + thump]) * env


def guitar(f, dur, vel, t0):
    """Nylon string: plucked in the middle (round), warm body, short sweet ring."""
    n = int(2.2 * SR)
    t = tt(n)
    ph = phase(f, n, t0, wob=0.3)
    y = np.zeros(n)
    for k in range(1, 20):
        fk = k * np.sqrt(1 + 0.00008 * k * k)
        if f * fk > 7000:
            break
        y += np.sin(np.pi * k * 0.13) / k * np.sin(fk * ph) * np.exp(-t * (1.3 + 0.9 * k ** 1.3))
    y += fft_filter(rng.standard_normal(n), bp(1500, 5000)) * np.exp(-t / 0.003) * 0.08
    y = fft_filter(y, lambda fr: peak(110, 1.5, 1.2)(fr) * peak(220, 2.0, 0.6)(fr) * lp(4500, 1)(fr))
    env = np.clip(t / 0.002, 0, 1) * release(t, dur + 0.3, 0.25)
    return 0.32 * vel * y * env


def _bowed(f, n, t0, players, bright, vib_depth):
    out = np.zeros((2, n))
    for j, (det, pan) in enumerate(players):
        ph = phase(f, n, t0, det / 100 + vibrato(n, vib_depth, 5.0 + 0.35 * j, 0.12, j * 2.1))
        y = sum(np.sin(k * ph) / k / (1 + (k * f / bright) ** 2) for k in range(1, 28) if k * f < 9000)
        out[0] += np.cos(pan * np.pi / 2) * y
        out[1] += np.sin(pan * np.pi / 2) * y
    return np.stack([fft_filter(c, lambda fr: peak(1000, 1.4, 1.0)(fr) * peak(2900, 2.5, 0.5)(fr) * hp(180, 1)(fr)) for c in out])


def strings(f, dur, vel, t0):
    """String ensemble pad: three players, slow bow."""
    n = int((dur + 1.0) * SR)
    t = tt(n)
    out = _bowed(f, n, t0, ((-8, 0.15), (0, 0.5), (9, 0.85)), 2400, 0.12)
    return 0.03 * vel * out * np.clip(t / 0.5, 0, 1) ** 1.5 * release(t, dur, 0.5)


def solo_strings(f, dur, vel, t0):
    """A small violin section carrying the melody: brighter, expressive vibrato, quicker bow."""
    n = int((dur + 0.8) * SR)
    t = tt(n)
    out = _bowed(f, n, t0, ((-4, 0.4), (5, 0.6)), 3400, 0.2)
    bow = np.clip(t / 0.12, 0, 1) * (0.85 + 0.15 * np.clip(t / 1.0, 0, 1)) * release(t, dur, 0.25)
    return 0.14 * vel * out * bow


def pizz_bass(f, dur, vel, t0):
    n = int((dur + 0.5) * SR)
    t = tt(n)
    ph = phase(f, n, t0, wob=0.2)
    y = sum(np.sin(np.pi * k * 0.25) / k * np.sin(k * ph) * np.exp(-t * (3 + 6 * k)) for k in range(1, 12))
    y += 0.6 * np.sin(ph) * np.exp(-t / 0.6)
    thump = fft_filter(rng.standard_normal(n), lp(400)) * np.exp(-t / 0.012) * 0.3
    return 0.5 * vel * (y + thump) * np.clip(t / 0.003, 0, 1) * release(t, dur, 0.1)


def _frame_drum():
    n = int(0.5 * SR)
    t = tt(n)
    body = np.sin(2 * np.pi * np.cumsum(85 + 70 * np.exp(-t / 0.025)) / SR) * np.exp(-t / 0.16)
    skin = fft_filter(rng.standard_normal(n), bp(300, 2500)) * np.exp(-t / 0.02) * 0.25
    return (body + skin) * np.clip(t / 0.002, 0, 1) * 0.35


def _shaker():
    n = int(0.1 * SR)
    t = tt(n)
    return fft_filter(rng.standard_normal(n), bp(4500, 10000)) * np.clip(t / 0.012, 0, 1) * np.exp(-t / 0.03) * 0.4


HITS = {"drum": [_frame_drum() for _ in range(3)], "shaker": [_shaker() for _ in range(8)]}


def hit(kind):
    def play(f, dur, vel, t0):
        v = HITS[kind]
        return vel * v[rng.integers(len(v))]
    play.unpitched = True
    return play


DRUM, SHAKER = hit("drum"), hit("shaker")

# ------------------------------------------------------------------ harmony

CHORDS = {
    "Dmaj9": "D F# A C# E", "Dadd9": "D F# A E", "Bm9": "B D F# A C#", "Gmaj9": "G B D F# A",
    "Gmaj7": "G B D F#", "F#m7": "F# A C# E", "Em9": "E G B D F#", "A7sus": "A D E G", "A7": "A C# E G",
    "Cmaj7": "C E G B",
}
# a bar is one chord, or two (first half, second half)
PROG = {
    "A": ["Dmaj9", "Bm9", "Gmaj9", ("A7sus", "A7"), "Dmaj9", "F#m7", "Gmaj9", ("Em9", "A7sus")],
    "B": ["Bm9", "Gmaj7", "Dadd9", "Em9", "Bm9", "Gmaj7", "Cmaj7", ("A7sus", "A7")],
}

THEME = {
    "A": [
        [(0, 2, "A4"), (2, 1, "D5"), (3, 5, "E5")],                 # rises to the 9th and hangs there
        [(0, 2, "F#5"), (2, 1, "E5"), (3, 1, "D5"), (4, 4, "C#5")], # falls to the 9th of Bm
        [(0, 2, "B4"), (2, 1, "E5"), (3, 5, "F#5")],                # same rise, a step higher: maj7 of G
        [(0, 2, "E5"), (2, 2, "D5"), (4, 4, "C#5")],                # sus to its resolution
        [(0, 2, "A4"), (2, 1, "D5"), (3, 3, "E5"), (6, 1, "F#5"), (7, 1, "A5")],
        [(0, 3, "C#6"), (3, 1, "B5"), (4, 4, "A5")],                # the one high point
        [(0, 3, "B5"), (3, 1, "A5"), (4, 4, "F#5")],
        [(0, 4, "E5"), (4, 4, "D5")],                               # D over the sus: home, open
    ],
    "B": [
        [(0, 6, "F#5"), (6, 1, "E5"), (7, 1, "F#5")],
        [(0, 6, "B5"), (6, 2, "A5")],
        [(0, 4, "F#5"), (4, 2, "E5"), (6, 2, "D5")],
        [(0, 6, "G5"), (6, 2, "F#5")],
        [(0, 3, "F#5"), (3, 1, "A5"), (4, 4, "B5")],
        [(0, 3, "D6"), (3, 1, "B5"), (4, 4, "A5")],
        [(0, 4, "G5"), (4, 2, "E5"), (6, 2, "G5")],                 # over C major 7: the road opens
        [(0, 4, "A5"), (4, 4, "E5")],
    ],
}

# (part, melody voice, accompaniment, extras)
FORM = [
    ("A", "piano", "guitar", ""),
    ("A", "flute", "guitar", "shaker"),
    ("B", "piano", "guitar-light", ""),
    ("A", "flute+strings", "guitar", "march"),
    ("A", None, "piano", "rest"),
    ("B", "flute", "guitar", "shaker"),
    ("A", "solo strings", "piano", ""),
    ("B", None, "guitar", "rest"),
    ("A", "flute", "guitar", "march"),
    ("B", "solo strings", "guitar-light", ""),
    ("A", "piano", "guitar", ""),
    ("A", None, "piano", "rest"),
]
SECTION_NAMES = ["theme · piano", "theme · flute", "B · piano", "theme · march", "rest", "B · flute",
                 "theme · strings", "rest · guitar", "theme · march", "B · strings", "theme · piano", "rest"]
KINDS = ["A", "A", "B", "A", "rest", "B", "A", "rest", "A", "B", "A", "rest"]

OSTINATO = [(0, "r", 1.0), (1, "fifth", 0.7), (2, "color", 0.65), (3, "third", 0.85),
            (4, "color", 0.6), (5, "fifth", 0.6), (6, "third", 0.8), (7, "color", 0.55)]


def pcs(ch):
    return [midi(p + "4") % 12 for p in CHORDS[ch].split()]


def place(pc, lo):
    return lo + (pc - lo) % 12


def colour(ch):
    p = pcs(ch)
    major = (p[1] - p[0]) % 12 == 4
    return p[4] if major and len(p) == 5 else p[3]


def lh_notes(ch):
    """root, fifth, colour (9th on major chords, else the 7th), third an octave up: E2..G4."""
    p = pcs(ch)
    r = place(p[0], 40)
    fifth = place(p[2], r + 1)
    c = place(colour(ch), fifth + 1)
    return r, fifth, c, place(p[1], c + 1)


def pad_voicing(ch):
    p = pcs(ch)
    return sorted(place(x, 57) for x in (p[1], p[2], colour(ch)))   # rootless, A3..G#4


def segments(entry):
    return [(entry, 0, 8)] if isinstance(entry, str) else [(entry[0], 0, 4), (entry[1], 4, 4)]


def chord_at(bar, slot):
    part = FORM[bar // 8][0]
    for ch, start, length in segments(PROG[part][bar % 8]):
        if start <= slot < start + length:
            return ch


# ------------------------------------------------------------------ arrangement

STEMS = ["flute", "piano", "guitar", "strings", "bass", "perc"]
events = []  # (t, dur, midi, vel, inst, pan, stem, rev, echo)


def note(slot, length, m, vel, inst, stem, pan=0.0, rev=0.25, echo=0.0, human=True):
    t0, dur = t_of(slot), t_of(slot + length) - t_of(slot)
    if human:
        t0 += abs(rng.normal(0, 0.008))
        vel *= 1 + rng.normal(0, 0.05)
    events.append((t0, dur, m, vel, inst, pan, stem, rev, echo))


for bar in range(BARS):
    blk, i = bar // 8, bar % 8
    part, voice, accomp, extra = FORM[blk]
    s0 = bar * 8
    segs = segments(PROG[part][i])

    # --- melody
    for slot, ln, n in THEME[part][i]:
        m = midi(n)
        if voice == "piano":
            note(s0 + slot, ln, m, 0.82, felt_piano, "piano", 0.1, rev=0.25, echo=0.08)
        elif voice in ("flute", "flute+strings"):
            note(s0 + slot, ln, m, 0.9, flute, "flute", 0.0, rev=0.25, echo=0.12)
            if voice == "flute+strings":
                note(s0 + slot, ln, m, 0.45, solo_strings, "strings", 0.15, rev=0.35)
        elif voice == "solo strings":
            note(s0 + slot, ln, m, 0.9, solo_strings, "strings", 0.0, rev=0.3, echo=0.06)
    if voice is None and i in (0, 4):   # in the rests, the piano remembers the opening bar of the tune
        for slot, ln, n in THEME[part][i]:
            note(s0 + slot, ln, midi(n), 0.42, felt_piano, "piano", 0.15, rev=0.45, echo=0.2)

    # --- accompaniment
    for ch, start, length in segs:
        lh = dict(zip(("r", "fifth", "color", "third"), lh_notes(ch)))
        if accomp.startswith("guitar"):
            for slot, which, acc in OSTINATO:
                if not (start <= slot < start + length):
                    continue
                if accomp == "guitar-light" and slot % 2:
                    continue
                v = 0.7 * acc * (0.85 if extra == "rest" else 1.0)
                note(s0 + slot, start + length - slot, lh[which], v, guitar, "guitar", -0.35 + 0.08 * slot, rev=0.28)
        else:   # felt piano chords, slow and spread
            note(s0 + start, length, lh["r"], 0.42, felt_piano, "piano", -0.3, rev=0.4)
            note(s0 + start + 0.2, length - 0.2, lh["fifth"], 0.32, felt_piano, "piano", -0.2, rev=0.4)
            note(s0 + start + min(3, length - 1), length - min(3, length - 1), lh["color"], 0.27, felt_piano, "piano", 0.0, rev=0.45)
            if length == 8:
                note(s0 + 5, 3, lh["third"], 0.25, felt_piano, "piano", 0.15, rev=0.45)

        # string pad
        sv = {"": 0.6, "shaker": 0.6, "march": 0.9, "rest": 0.55}[extra]
        for m in pad_voicing(ch):
            note(s0 + start, length, m, sv, strings, "strings", 0.0, rev=0.45, human=False)

        # pizzicato bass: root on the chord, fifth on beat 3 when the chord lasts the bar
        root = place(pcs(ch)[0], 33)
        note(s0 + start, 3, root, 0.85, pizz_bass, "bass", 0.0, rev=0.08)
        if length == 8 and extra != "rest":
            note(s0 + 4, 3, root + 7 if i % 2 else root, 0.62, pizz_bass, "bass", 0.0, rev=0.08)

    # --- percussion
    if extra == "march":
        for slot, v in ((0, 1.0), (3, 0.55), (4, 0.8), (6, 0.5)):
            note(s0 + slot, 1, 60, v, DRUM, "perc", 0.0, rev=0.15)
    if extra in ("shaker", "march"):
        for slot in (1, 3, 5, 7):
            note(s0 + slot, 1, 60, 0.9 if slot in (3, 7) else 0.6, SHAKER, "perc", 0.35, rev=0.1)


# ------------------------------------------------------------------ checks

def clash_report():
    """Melody voices vs sounding accompaniment: minor 9ths always, off-chord semitones / tritones."""
    held = [(t, t + d, m) for t, d, m, v, inst, *_ in events
            if inst in (guitar, strings, pizz_bass) or (inst is felt_piano and m < 69)]
    bad = []
    for t, d, m, v, inst, *_ in events:
        if getattr(inst, "unpitched", False) or m < 69:
            continue
        bar = int(t / (4 * BEAT))
        ch = chord_at(bar, int((t - bar * 4 * BEAT) / (BEAT / 2)))
        for a, b, h in held:
            if a <= t < b - 0.05:
                iv = (m - h) % 12
                if iv == 1 or (iv in (11, 6) and m % 12 not in pcs(ch)):
                    bad.append((round(t, 2), ch, m, h, iv))
    return bad


def accomp_clashes():
    out = []
    for ch in CHORDS:
        v = sorted(set(lh_notes(ch) + tuple(pad_voicing(ch))))
        out += [(ch, a, b) for a, b in zip(v, v[1:]) if b - a == 1]
    return out


def registers():
    return {"lowest melody": min(midi(n) for part in THEME.values() for bar in part for *_, n in bar),
            "highest accompaniment": max(max(lh_notes(c)) for c in CHORDS),
            "highest pad": max(max(pad_voicing(c)) for c in CHORDS)}


# ------------------------------------------------------------------ render (one stem at a time, to save memory)

def circ(x, resp):
    return np.fft.irfft(np.fft.rfft(x, axis=-1) * resp(np.fft.rfftfreq(x.shape[-1], 1 / SR)), x.shape[-1], axis=-1)


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
    breathe = 0.5 + 0.5 * np.sin(2 * np.pi * 7 / LOOP_S * t) * np.sin(2 * np.pi * 17 / LOOP_S * t + 0.7)
    return 0.012 * air / np.abs(air).max() * breathe


def limiter_gain(x, ceil=0.9, block=48):
    pk = np.abs(x).max(axis=0)
    nb = LOOP_N // block
    pb = pk[: nb * block].reshape(nb, block).max(axis=1)
    g = np.minimum(1, ceil / np.maximum(pb, 1e-9))
    w = 8
    gm = np.min([np.roll(g, s) for s in range(-w, w + 1)], axis=0)
    gs = np.mean([np.roll(gm, s) for s in range(-w // 2, w // 2 + 1)], axis=0)
    full = np.repeat(gs, block)
    return np.concatenate([full, np.full(LOOP_N - len(full), full[-1])]).astype(np.float32)


PLANE = {"flute": (1.0, 10000), "piano": (1.0, 9000), "guitar": (0.9, 8000), "strings": (0.8, 7000),
         "bass": (1.0, 3000), "perc": (0.95, 9000)}
GAINS = {"flute": 1.0, "piano": 1.0, "guitar": 0.85, "strings": 0.9, "bass": 0.85, "perc": 0.9}


def render_stem(stem, irs):
    n = LOOP_N + TAIL
    dry, rev, ech = np.zeros((2, n)), np.zeros((2, n)), np.zeros(n)
    for t, dur, m, vel, inst, pan, s, rs, es in events:
        if s != stem:
            continue
        y = np.atleast_2d(inst(hz(m), dur, vel, t))
        if y.shape[0] == 1:
            y = np.vstack([y, y])
        i = int(round(t * SR)) % LOOP_N
        y = y[:, : n - i]
        a = (pan + 1) * np.pi / 4
        y = y * np.array([[np.cos(a)], [np.sin(a)]]) * np.sqrt(2)
        dry[:, i:i + y.shape[1]] += y
        rev[:, i:i + y.shape[1]] += rs * y
        if es:
            ech[i:i + y.shape[1]] += es * y.mean(axis=0)

    def fold(x):
        out = x[..., :LOOP_N].copy()
        out[..., :TAIL] += x[..., LOOP_N:LOOP_N + TAIL]
        return out

    dry, rev, ech = fold(dry), fold(rev), fold(ech)
    echo = echo_fx(ech) if ech.any() else 0.0
    send = circ(rev + 0.4 * echo, hp(200, 1))
    wet = np.stack([np.fft.irfft(np.fft.rfft(send[c]) * irs[c], LOOP_N) for c in range(2)])
    dry_amt, dark = PLANE[stem]
    out = dry_amt * circ(dry, lp(dark, 1)) + echo + 0.75 * wet
    if stem == "perc":
        out = out + wind_bed()
    out = circ(out, hp(35, 2) if stem == "bass" else hp(120, 1))
    out = circ(out * GAINS[stem], lambda f: hp(25, 2)(f) * lp(16000, 2)(f))
    return out.astype(np.float32)


def render():
    irs = make_ir()
    stems = {}
    for s in STEMS:
        stems[s] = render_stem(s, irs)
        print(f"  rendered {s}", flush=True)
    pre = sum(stems.values())
    norm = np.float32(10 ** (-18 / 20) / np.sqrt(np.mean(pre.astype(np.float64) ** 2)))
    g = limiter_gain(pre * norm)
    for s in STEMS:
        stems[s] *= norm * g
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
            "sections": [{"id": str(k + 1), "name": nm, "kind": KINDS[k], "bar": k * 8, "t": k * 32 * BEAT}
                         for k, nm in enumerate(SECTION_NAMES)],
            "stems": STEMS}
    (OUT / "track.json").write_text(json.dumps(meta, indent=1))
    rms = np.sqrt(np.mean(master.astype(np.float64) ** 2))
    print(f"{len(events)} notes, {LOOP_S:.0f}s loop, peak {np.abs(master).max():.3f}, rms {20 * np.log10(rms):.1f} dBFS")
    blk = 8 * 4 * BEAT
    for s, x in list(stems.items()) + [("master", master)]:
        per = [20 * np.log10(np.sqrt(np.mean(x[:, int(k * blk * SR):int((k + 1) * blk * SR)].astype(np.float64) ** 2)) + 1e-9)
               for k in range(BARS // 8)]
        print(f"  {s:8s}", " ".join(f"{v:6.1f}" for v in per))
