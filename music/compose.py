"""Meadow Road: the main theme. Calm background music, ~4.9 min, seamless.

Fourth theme (2026-11-12). What the user rejected on the way, which this file must never do again:
  * a bright, hard piano, high up: "too aggressive, too high"
  * three even notes rising to a held one, on a pure tone: "the noise a pharmacy makes when you enter", "a notification"
  * ANY STAIRCASE: "you go slowly up note by note then slowly down note by note: it makes me sick". That was the left
    hand going up each chord and back a note at a time, and melodies moving by step up, then by step down.
So:
  * no arpeggio anywhere. Chords are struck together, softly, and held; a pad and a bass under them.
  * the melody never takes two steps in the same direction: it repeats a note, drops a third, leaps a fifth, holds.
  * it sits low (D4-D5), on a soft, dark felt piano that is still a piano (two strings, a felt thump), not a sine.
  * the key must be heard ("the scale looks off"): an earlier version began on the IV chord, put melody notes that were
    not in the chord on the strong beats, and had no leading note and no cadence.
  * it must not wander ("going anywhere, freestyling, typically AI-generated"): a line where every bar does something
    else, with leaps, is not a tune. The version the user once called perfect was one tiny cell repeated exactly.
So the theme is one head of three notes (A, up to B, back to A: long, short, long), said four times, exactly the same.
Only the note it lands on changes, and those four landings are the whole story: F#, E, F#, D (3, 2, 3, 1: a question,
its answer). Two bars a chord, the bass walking down, a full cadence at the end:
        D . | A over C# . | B minor 7 . | A, D        (I, V6, vi7, V-I)
Every melody note that starts on a beat is a note of the chord under it (`off_chord()` checks).
Then the user asked for more Animal Crossing. What that music is (Totaka's hourly themes: bossa nova and lounge, "electronic
but played as if acoustic", seventh chords, electric piano, light drums and bass), and what this file takes from it:
  * a light swing: the off-beat eighths come late (SWING)
  * a band, not a pad: a bass that bounces from the root to the fifth, an electric piano that puts the chord, all its
    notes together and short, on the off-beats, a shaker. The pad is nearly gone.
  * seventh chords, one a bar, all from the key: Dmaj7, Bm7, F#m7, Em7-A7 / Dmaj7, Bm7, A7sus, D6
  * the tune pushes: the long note of each phrase arrives an eighth early
The theme itself is unchanged in kind: one head (A, B, A) said four times, landing on F#, E, F#, D.
The night theme (night.py) and the boss fight (boss.py) reuse it over other chords. The Opus 5.5 version is frozen in music/opus/.

Pure numpy, 48 kHz, 84 BPM, 88 bars = 251 s. Melody from bar 1. Checks: registers, clashes, staircases, loudness.

    uv run python music/compose.py      # writes music/site/audio/*.wav + track.json
"""

from pathlib import Path
import json
import os
import wave

import numpy as np

SR = 48000
BPM = 84
SWING = 0.58       # where in the beat the off-beat eighth falls (0.5 straight, 0.67 a full shuffle)
BARS = 88


def fast_len(n):
    """The length nearest n whose only factors are 2, 3 and 5: whole-loop FFTs are several times faster on it
    (84 BPM gave a length with a big prime in it). It moves the tempo by less than one percent."""
    best = 1
    for a in range(25):
        for b in range(16):
            v = 2 ** a * 3 ** b
            while v < 2 * n:
                if abs(v - n) < abs(best - n):
                    best = v
                v *= 5
    return best


LOOP_N = fast_len(int(round(BARS * 4 * 60 / BPM * SR)))
LOOP_S = LOOP_N / SR
BEAT = LOOP_S / (BARS * 4)
TAIL = 7 * SR
OUT = Path(__file__).with_name("site") / "audio"
rng = np.random.default_rng(418)

PC = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


def midi(name):
    pc, rest = PC[name[0]], name[1:]
    while rest and rest[0] in "#b":
        pc += 1 if rest[0] == "#" else -1
        rest = rest[1:]
    return 12 * (int(rest) + 1) + pc


def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def t_of(slot):  # eighth notes, 8 per bar, swung
    beat, p = divmod(slot / 2, 1)
    return (beat + (p * 2 * SWING if p < 0.5 else SWING + (p - 0.5) * 2 * (1 - SWING))) * BEAT


def tt(n):
    return np.arange(n) / SR


def fft_filter(y, resp):
    n = y.shape[-1]
    m = 1 << int(np.ceil(np.log2(n + 2048)))
    return np.fft.irfft(np.fft.rfft(y, m, axis=-1) * resp(np.fft.rfftfreq(m, 1 / SR)), m, axis=-1)[..., :n]


def lp(fc, order=2):
    return lambda f: 1 / np.sqrt(1 + (f / fc) ** (2 * order))


def hp(fc, order=2):
    return lambda f: 1 / np.sqrt(1 + (fc / np.maximum(f, 1e-3)) ** (2 * order))


def bp(lo, hi, order=2):
    return lambda f: hp(lo, order)(f) * lp(hi, order)(f)


def loop_lfo(t_abs, cycles, ph=0.0):
    """0..1, a whole number of cycles per loop: seamless."""
    return 0.5 + 0.5 * np.sin(2 * np.pi * cycles / LOOP_S * t_abs + ph)


def wobble(t_abs, depth=1.0):
    return depth * (0.05 * np.sin(2 * np.pi * 67 / LOOP_S * t_abs) + 0.03 * np.sin(2 * np.pi * 19 / LOOP_S * t_abs + 1))


def phase(f, n, t0, semis=0.0, wob=1.0):
    return 2 * np.pi * np.cumsum(f * 2 ** ((wobble(t0 + tt(n), wob) + semis) / 12)) / SR


def release(t, dur, r):
    return np.where(t > dur, np.exp(-(t - dur) / r), 1.0)


def saw(ph, f, cutoff, kmax=40):
    return sum(np.sin(k * ph) / k / (1 + (k * f / cutoff) ** 2) for k in range(1, kmax) if k * f < 12000)


# ------------------------------------------------------------------ instruments (f, dur, vel, t0)

def nylon(f, dur, vel, t0):
    """The main instrument since 2026-11-13: a nylon-string guitar, plucked with the thumb. Three pianos were refused
    ("aggressive", then "unbearable": the last was nearly a sine, two strings beating slowly, pushed into a clipper).
    One string as its modes: a pluck at a fifth of its length, bright for a tenth of a second and then round as the
    high modes die first; a wooden body (two low resonances); the thumb's small knock. No detune, no clipping."""
    n = int((dur + 2.5) * SR)
    t = tt(n)
    ph = phase(f, n, t0, wob=0.25)
    tau1 = 1.5 * (196 / max(f, 98)) ** 0.5                      # lower strings ring longer
    y = np.zeros(n)
    for k in range(1, 25):
        fk = k * np.sqrt(1 + 0.00006 * k * k)
        if f * fk > 9000:
            break
        amp = np.sin(np.pi * k * 0.2) / k ** 1.5 / (1 + (f * fk / (2200 + 2600 * vel)) ** 2)
        y += amp * np.sin(fk * ph) * np.exp(-t * (1 + 0.09 * k * k) / tau1)
    y += fft_filter(rng.standard_normal(n), bp(120, 900, 1)) * np.exp(-t / 0.008) * 0.06 * vel      # the thumb on the string
    body = lambda fr: (bp(70, 7000, 1)(fr) * (1 + 0.9 / (1 + ((fr - 110) / 25) ** 2) + 0.6 / (1 + ((fr - 215) / 40) ** 2)
                                               + 0.25 / (1 + ((fr - 420) / 90) ** 2)))
    y = fft_filter(y, body)
    return 0.4 * vel * y * np.clip(t / 0.003, 0, 1) * release(t, dur, 0.35)


def rhodes(f, dur, vel, t0):
    """Candidate: an electric piano as a lead. A tine and its bar (FM): it barks a little at the start, then sings."""
    n = int((dur + 1.5) * SR)
    t = tt(n)
    ph = phase(f, n, t0, wob=0.25)
    idx = (0.35 + 1.5 * vel * np.exp(-t / 0.18)) * min(1.0, 500 / f)
    y = np.sin(ph + idx * np.sin(ph)) + 0.12 * vel * np.sin(14 * ph) * np.exp(-t / 0.05)
    return 0.3 * vel * y * np.clip(t / 0.004, 0, 1) * np.exp(-t / 2.2) * release(t, dur, 0.3)


def marimba(f, dur, vel, t0):
    """Candidate: a marimba, soft mallets. The bar (its modes at 1, 4 and 10 times the note) over its tube."""
    tau = 0.7 * (262 / max(f, 131)) ** 0.6
    n = int(max(1.5, 6 * tau) * SR)
    t = tt(n)
    ph = phase(f, n, t0, wob=0.0)
    y = np.sin(ph) * np.exp(-t / tau) + 0.3 * vel * np.sin(4 * ph) * np.exp(-t / (tau * 0.18)) \
        + 0.08 * vel * np.sin(10.1 * ph) * np.exp(-t / (tau * 0.05))
    y += fft_filter(rng.standard_normal(n), bp(200, 1500, 1)) * np.exp(-t / 0.006) * 0.08 * vel
    return 0.5 * vel * y * np.clip(t / 0.002, 0, 1)




_pad_cache = {}


def analog_pad(f, dur, vel, t0):
    """Four detuned saws, filter opening and closing over minutes (whole cycles per loop). The saws of a note are made
    once and kept: the pad plays the same few notes hundreds of times, and this was half of the rendering time."""
    n = int((dur + 4.0) * SR)
    t = tt(n)
    key = (round(f, 3), n)
    if key not in _pad_cache:
        dark, bright = np.zeros((2, n)), np.zeros((2, n))
        for j, d in enumerate((-9, -3, 4, 10)):
            ph = phase(f, n, 0.0, d / 100, wob=0.8)
            dark[j % 2] += saw(ph, f, 650)
            bright[j % 2] += saw(ph, f, 2600)
        _pad_cache[key] = (dark, bright)
    dark, bright = _pad_cache[key]
    w = loop_lfo(t0 + t, 3, 0.4)
    env = np.clip(t / 1.4, 0, 1) ** 2 * release(t, dur, 0.8)
    return 0.05 * vel * ((1 - w) * dark + w * bright) * env


def moog_bass(f, dur, vel, t0):
    """Round, warm synth bass: saw + square under a low filter, soft attack, held."""
    n = int((dur + 1.2) * SR)
    t = tt(n)
    ph = phase(f, n, t0, wob=0.3)
    y = 0.6 * saw(ph, f, 260) + 0.5 * sum(np.sin(k * ph) / k for k in (1, 3, 5)) * 0.8 + 0.5 * np.sin(ph)
    y = np.tanh(1.3 * y)
    env = np.clip(t / 0.08, 0, 1) * (0.8 + 0.2 * np.exp(-t / 0.5)) * release(t, dur, 0.22)      # (a 0.5 s release was cut 19 dB down, and blurred the bounce)
    return 0.3 * vel * y * env


def epiano(f, dur, vel, t0):
    """Electric piano, for the chords: a round tone with a small tine on top that dies at once. Short, soft."""
    n = int((dur + 0.5) * SR)
    t = tt(n)
    ph = phase(f, n, t0, wob=0.4)
    y = np.sin(ph) + 0.35 * np.sin(2 * ph) * np.exp(-t / 0.25) + 0.12 * np.sin(3 * ph) * np.exp(-t / 0.12) \
        + 0.1 * vel * np.sin(7.02 * ph) * np.exp(-t / 0.03)
    return 0.2 * vel * y * np.clip(t / 0.004, 0, 1) * np.exp(-t / 0.6) * release(t, dur, 0.12)


def shaker(f, dur, vel, t0):
    """A shaker, far back: a soft breath of high noise."""
    n = int(0.17 * SR)
    t = tt(n)
    y = fft_filter(rng.standard_normal(n), bp(3000, 8000, 2)) * np.clip(t / 0.012, 0, 1) * np.exp(-t / 0.025)
    return 0.22 * vel * y / (np.abs(y).max() + 1e-9)       # (0.4 was "a bit too loud")


def melodica(f, dur, vel, t0):
    """A melodica: a free reed, buzzy but small, speaking at once and held by the breath; a slow shake once it is held."""
    n = int((dur + 0.4) * SR)
    t = tt(n)
    vib = 0.07 * np.clip((t - 0.35) / 0.5, 0, 1) * np.sin(2 * np.pi * 5.2 * t)
    ph = phase(f, n, t0, vib, wob=0.2)
    y = saw(ph, f, 1500 + 900 * vel, kmax=24) + 0.35 * sum(np.sin(k * ph) / k for k in (1, 3, 5) if k * f < 6000)
    y += fft_filter(rng.standard_normal(n), bp(1500, 5000, 1)) * 0.012
    env = np.clip(t / 0.03, 0, 1) * (0.85 + 0.15 * np.exp(-t / 0.3)) * release(t, dur, 0.07)
    return 0.16 * vel * y * env


def clarinet(f, dur, vel, t0):
    """A clarinet, low and hollow: the odd harmonics, a soft start, a little breath."""
    n = int((dur + 0.5) * SR)
    t = tt(n)
    vib = 0.04 * np.clip((t - 0.5) / 0.6, 0, 1) * np.sin(2 * np.pi * 4.8 * t)
    ph = phase(f, n, t0, vib, wob=0.2)
    y = sum(np.sin(k * ph) / k ** 1.4 / (1 + (k * f / (1600 + 1400 * vel)) ** 2) for k in (1, 3, 5, 7, 9, 11) if k * f < 9000)
    y += 0.06 * np.sin(2 * ph) + fft_filter(rng.standard_normal(n), bp(900, 3500, 1)) * 0.01
    env = np.clip(t / 0.05, 0, 1) ** 1.5 * release(t, dur, 0.09)
    return 0.3 * vel * y * env


def flute(f, dur, vel, t0):
    """A whistled, flute-like voice: nearly a pure tone with breath around it; it scoops into the note and shakes slowly."""
    n = int((dur + 0.5) * SR)
    t = tt(n)
    vib = 0.09 * np.clip((t - 0.3) / 0.5, 0, 1) * np.sin(2 * np.pi * 5.0 * t)
    ph = phase(f, n, t0, vib - 0.3 * np.exp(-t / 0.04), wob=0.2)
    y = np.sin(ph) + 0.16 * np.sin(2 * ph) + 0.05 * np.sin(3 * ph)
    breath = fft_filter(rng.standard_normal(n), lambda fr: bp(f * 1.5, f * 5, 1)(fr))
    y += 0.05 * breath / (np.abs(breath).max() + 1e-9) * (1 + 2 * np.exp(-t / 0.05))
    env = np.clip(t / 0.06, 0, 1) * release(t, dur, 0.1)
    return 0.3 * vel * y * env


def vibes(f, dur, vel, t0):
    """A vibraphone, soft mallets, motor on slow: a metal bar that rings for seconds, gently pulsing."""
    n = int((dur + 2.0) * SR)
    t = tt(n)
    ph = phase(f, n, t0, wob=0.0)
    tau = 2.6 * (262 / max(f, 131)) ** 0.4
    y = np.sin(ph) * np.exp(-t / tau) + 0.22 * vel * np.sin(4 * ph) * np.exp(-t / (tau * 0.2)) + 0.05 * vel * np.sin(10 * ph) * np.exp(-t / (tau * 0.04))
    y *= 1 + 0.12 * np.sin(2 * np.pi * 4.3 * (t0 + t))
    return 0.4 * vel * y * np.clip(t / 0.004, 0, 1) * release(t, dur, 0.5)


def upright(f, dur, vel, t0):
    """A plucked double bass: a round thump, the string's low modes, gone within a second."""
    n = int((dur + 0.8) * SR)
    t = tt(n)
    ph = phase(f, n, t0, -0.25 * np.exp(-t / 0.03), wob=0.1)
    y = sum(np.sin(k * ph) / k ** 1.7 * np.exp(-t * (1.1 + 0.9 * k)) for k in range(1, 9) if k * f < 1800)
    thump = fft_filter(rng.standard_normal(n), bp(60, 400, 1)) * np.exp(-t / 0.01)
    y += 0.12 * vel * thump / (np.abs(thump).max() + 1e-9)
    return 0.5 * vel * y * np.clip(t / 0.006, 0, 1) * release(t, dur, 0.12)


def woodblock(f, dur, vel, t0):
    """A small wooden block, far back: two damped modes and the stick."""
    n = int(0.2 * SR)
    t = tt(n)
    y = np.sin(2 * np.pi * 880 * t) * np.exp(-t / 0.022) + 0.5 * np.sin(2 * np.pi * 1420 * t) * np.exp(-t / 0.012)
    y += 0.2 * fft_filter(rng.standard_normal(n), bp(1500, 5000, 1)) * np.exp(-t / 0.003)
    return 0.16 * vel * y * np.clip(t / 0.001, 0, 1)


def glide_lead(f, dur, vel, t0):
    """Warm monophonic synth lead: filtered saw + sine, slides up into each note, slow vibrato."""
    n = int((dur + 1.5) * SR)                # (0.6 s cut the release 21 dB down)
    t = tt(n)
    vib = 0.1 * np.clip((t - 0.4) / 0.6, 0, 1) * np.sin(2 * np.pi * 4.2 * t)
    ph = phase(f, n, t0, -0.5 * np.exp(-t / 0.06) + vib, wob=0.5)
    y = 0.55 * saw(ph, f, 1700) + 0.6 * np.sin(ph)
    env = np.clip(t / 0.06, 0, 1) * release(t, dur, 0.25)
    return 0.22 * vel * y * env


def _ends_silent(fn):
    """What an instrument returns ends on zero (the audit found notes cut 25 to 40 dB down: a faint tick each)."""
    def voiced(f, dur, vel, t0):
        y = np.array(fn(f, dur, vel, t0), dtype=float)
        k = min(y.shape[-1], 480)
        y[..., -k:] *= np.linspace(1, 0, k)
        return y
    voiced.__name__, voiced.__doc__, voiced.raw = fn.__name__, fn.__doc__, fn
    return voiced


VOICES = ["nylon", "rhodes", "marimba", "analog_pad", "moog_bass", "epiano", "shaker", "melodica", "clarinet",
          "flute", "vibes", "upright", "woodblock", "glide_lead"]
for _name in VOICES:
    globals()[_name] = _ends_silent(globals()[_name])
MAIN = nylon            # who plays Meadow Road's melody (night.py and boss.py use it too)


# ------------------------------------------------------------------ material

CHORDS = {"Dmaj7": "D F# A C#", "Bm7": "B D F# A", "F#m7": "F# A C# E", "Em7": "E G B D", "A7": "A C# E G",
          "A7sus": "A D E G", "D6": "D F# A B"}                    # (first note: the bass)
CYCLE = ["Dmaj7", "Bm7", "F#m7", "Em7 A7", "Dmaj7", "Bm7", "A7sus", "D6"]       # 8 bars; "Em7 A7": two beats of each


def chords_in(i):
    """The chords of bar i of the cycle: (first eighth, eighths long, chord)."""
    names = CYCLE[i].split()
    return [(k * 8 // len(names), 8 // len(names), ch) for k, ch in enumerate(names)]


# The melody, per bar: (eighth slot, length in eighths, note). One head, four landings; each landing comes an eighth
# early (on the last off-beat of the head's bar) and is held into the next bar. Nothing else, ever.
def head(land):
    return [(0, 1.5, "A4"), (3, 1, "B4"), (4, 2, "A4"), (7, 6, land)]


MELODY = [head("F#4"), [], head("E4"), [], head("F#4"), [], head("D4"), []]
PHRASE = [[(1.0, 0.0), (0.78, 0.0), (0.88, 0.0), (0.96, 0.0)] if bar else [] for bar in MELODY]     # (velocity x, seconds late)
# The chord as the electric piano plays it: all its notes together, short, under the melody. Never one note after another.
HAND = {"Dmaj7": "F#3 A3 C#4", "Bm7": "D3 F#3 A3", "F#m7": "E3 A3 C#4", "Em7": "D3 G3 B3", "A7": "E3 G3 C#4", "A7sus": "D3 E3 G3", "D6": "F#3 A3 B3"}


def pcs(ch):
    return [midi(p + "4") % 12 for p in CHORDS[ch].split()]


def place(pc, lo):
    return lo + (pc - lo) % 12


def hand_notes(ch):
    return [midi(n) for n in HAND[ch].split()]


def pad_voicing(ch):
    p = pcs(ch)
    return sorted(place(x, 50) for x in p[:3])   # three notes of the chord, D3..C#4: under the melody


# ------------------------------------------------------------------ the plan (11 blocks of 8 bars)
# keys: who plays the melody; the band (0: held chords only, 1: bass and electric piano, 2: with the shaker); pad level
PLAN = [
    dict(name="the theme", mel="piano", band=1, pad=0.35),
    dict(name="with the shaker", mel="piano", band=2, pad=0.35),
    dict(name="the band alone", mel=None, band=2, pad=0.45),
    dict(name="piano", mel="piano", band=2, pad=0.35),
    dict(name="synth lead", mel="lead", band=2, pad=0.35),
    dict(name="space", mel=None, band=0, pad=0.8),
    dict(name="piano, close", mel="piano", band=1, pad=0.3),
    dict(name="the band alone", mel=None, band=2, pad=0.45),
    dict(name="piano + lead", mel="both", band=2, pad=0.35),
    dict(name="fragments", mel="fragments", band=1, pad=0.4),
    dict(name="space", mel=None, band=0, pad=0.8),
]
assert len(PLAN) * 8 == BARS

STEMS = ["piano", "lead", "comp", "pad", "bass", "drums", "texture"]
events = []  # (t, dur, midi, vel, inst, pan, stem, rev, echo)


def note(slot, length, m, vel, inst, stem, pan=0.0, rev=0.25, echo=0.0, human=True, late=0.0):
    t0, dur = t_of(slot) + late, t_of(slot + length) - t_of(slot)
    if human:
        t0 += abs(rng.normal(0, 0.01))
        vel *= 1 + rng.normal(0, 0.06)
    events.append((t0, dur, m, vel, inst, pan, stem, rev, echo))


for bar in range(BARS):
    blk, i = bar // 8, bar % 8
    plan = PLAN[blk]
    ch = CYCLE[i]
    s0 = bar * 8

    # melody: always the same eight bars
    mel = plan["mel"]
    for (slot, ln, n), (touch, late) in zip(MELODY[i], PHRASE[i]):
        m = midi(n)
        if mel in ("piano", "both") or (mel == "fragments" and i in (0, 1, 4, 5)):
            note(s0 + slot, ln, m, 0.9 * touch, MAIN, "piano", 0.1, rev=0.3, late=late)      # (0.66 left the tune 2 to 5 dB under the band)
        if mel in ("lead", "both"):
            note(s0 + slot, ln, m, (0.9 if mel == "lead" else 0.55) * touch, glide_lead, "lead", -0.1, rev=0.3, late=late)

    band = plan["band"]
    for slot, ln, ch in chords_in(i):
        hand, root = hand_notes(ch), place(pcs(ch)[0], 33)
        for j, m in enumerate(hand):
            if not band:                        # space: the chord on the piano, held
                note(s0 + slot, ln, m, 0.42 - 0.03 * j, MAIN, "piano", -0.3 + 0.3 * j, rev=0.35)
            else:                               # the electric piano, short, off the beat: after beat 2 and on the "and" of 3
                for at, v in ((2, 0.8), (5, 0.62)) if ln == 8 else ((1, 0.75),):
                    note(s0 + slot + at, 1, m, v * (0.9 if mel else 1.0), epiano, "comp", -0.35 + 0.35 * j, rev=0.25)
        for m in pad_voicing(ch):
            note(s0 + slot, ln, m, plan["pad"], analog_pad, "pad", 0.0, rev=0.4, human=False)
        if band:                                # the bass bounces: root, then fifth (a split bar: just the roots)
            note(s0 + slot, 1.6, root, 0.85, moog_bass, "bass", 0.0, rev=0.05, human=False)
            if ln == 8:
                note(s0 + 3, 0.8, root, 0.5, moog_bass, "bass", 0.0, rev=0.05, human=False)
                note(s0 + 4, 1.6, root + 7, 0.72, moog_bass, "bass", 0.0, rev=0.05, human=False)
    if band == 2:
        for k in range(8):
            note(s0 + k, 1, 60, (0.9 if k in (2, 6) else 0.42 if k % 2 else 0.6), shaker, "drums", 0.3, rev=0.15)


# ------------------------------------------------------------------ checks

def chord_at_time(t):
    bar, slot = divmod(t / (BEAT / 2) + 1e-6, 8)
    return [ch for a, n, ch in chords_in(int(bar) % 8) if a <= slot][-1]


def off_chord():
    """Melody notes that start on a beat and are not a note of the chord under them."""
    out = [(i, n) for i in range(8) for slot, ln, n in MELODY[i] if slot % 2 == 0
           and midi(n) % 12 not in pcs([ch for a, _, ch in chords_in(i) if a <= slot][-1])]
    return out + [(i, n, "landing") for i in range(8) for slot, ln, n in MELODY[i] if slot == 7      # (held into the next bar)
                  and midi(n) % 12 not in pcs(chords_in((i + 1) % 8)[0][2])]


def clash_report():
    """Melody notes against everything held under them: a semitone or a minor 9th, or a tritone or major 7th that is not in the chord."""
    low = min(midi(n) for bar in MELODY for *_, n in bar)
    held = [(t, t + d, m) for t, d, m, v, inst, *_ in events if m < low and inst is not shaker]
    bad = []
    for t, d, m, v, inst, *_ in events:
        if m < low:
            continue
        ch = chord_at_time(t)
        for a, b, h in held:
            if a <= t < b - 0.05:
                iv = (m - h) % 12
                if iv == 1 or (iv in (11, 6) and m % 12 not in pcs(ch)):
                    bad.append((round(t, 2), ch, m, h, iv))
    return bad


def accomp_clashes():
    out = []
    for ch in CHORDS:
        v = sorted(set(hand_notes(ch) + pad_voicing(ch)))
        out += [(ch, a, b) for a, b in zip(v, v[1:]) if b - a == 1]
    return out


def registers():
    return {"lowest melody": min(midi(n) for bar in MELODY for *_, n in bar),
            "highest accompaniment": max(max(hand_notes(c) + pad_voicing(c)) for c in CHORDS)}


def staircases():
    """Three melody notes in a row going the same way by step (a second): what the user cannot stand."""
    line = [midi(n) for bar in MELODY for *_, n in bar]
    line += line[:2]                                                   # (it loops)
    return [(k, line[k:k + 3]) for k in range(len(line) - 2)
            if 0 < abs(line[k + 1] - line[k]) <= 2 and 0 < abs(line[k + 2] - line[k + 1]) <= 2 and (line[k + 1] - line[k]) * (line[k + 2] - line[k + 1]) > 0]


# ------------------------------------------------------------------ render, one stem at a time

def circ(x, resp):
    return np.fft.irfft(np.fft.rfft(x, axis=-1) * resp(np.fft.rfftfreq(x.shape[-1], 1 / SR)), x.shape[-1], axis=-1)


def echo_fx(mono, beats=0.75, fb=0.45):
    d = int(beats * BEAT * SR)
    f = np.fft.rfftfreq(LOOP_N, 1 / SR)
    k = np.arange(len(f))
    z = fb * lp(2500, 1)(f) * hp(300, 1)(f) * np.exp(-2j * np.pi * k * d / LOOP_N)
    x = np.fft.rfft(mono)
    return 0.5 * np.stack([np.fft.irfft(x * z / (1 - z ** 2), LOOP_N), np.fft.irfft(x * z ** 2 / (1 - z ** 2), LOOP_N)])


WET = 0.22          # the room's level against the dry sound (with sends of 0 to 0.4 a voice: 15 to 25 dB under it)


def room(rng, n, rt60=1.0, predelay=0.02):
    """One small room for everything: its sound is gone in a second (60 dB down in rt60), it starts 20 ms after the
    note so the attack stays clear, and it is kept out of the lows (under 250 Hz) and the highs (over 8 kHz).
    Mixing references: decay 0.8 to 1.5 s, pre-delay 20 to 30 ms, a 200 to 300 Hz cut on the return, the bass dry."""
    t = tt(int(1.6 * rt60 * SR))
    f = np.fft.rfftfreq(n, 1 / SR)
    irs = []
    for _ in range(2):
        ir = rng.standard_normal(len(t)) * np.exp(-t * 6.91 / rt60) * np.clip(t / 0.01, 0, 1)
        ir = np.concatenate([np.zeros(int(predelay * SR)), ir])
        ir /= np.sqrt(np.sum(ir ** 2))
        irs.append(np.fft.rfft(np.pad(ir, (0, n - len(ir)))) * hp(250, 1)(f) * lp(8000, 1)(f))
    return irs


def lufs(x):
    """Loudness as the ear weighs it (ITU-R BS.1770 K-weighting, done in the frequency domain; no gating;
    the constant is set so that a 997 Hz tone at -20 dBFS in both channels reads -20.0)."""
    x = np.atleast_2d(x).astype(np.float64)
    f = np.fft.rfftfreq(x.shape[-1], 1 / SR)
    k = (1 + (10 ** (4 / 20) - 1) / (1 + (1681 / np.maximum(f, 1)) ** 2)) / np.sqrt(1 + (38 / np.maximum(f, 1e-3)) ** 4)
    return -1.23 + 10 * np.log10(np.sum(np.abs(np.fft.rfft(x, axis=-1) * k) ** 2) * 2 / x.shape[-1] ** 2 + 1e-12)


def master(stems, target_db, ceil=0.89):
    """The stems at the target loudness (LUFS) and their sum, with peaks held under -1 dBFS by a limiter that
    only turns the level down for an instant (no clipper: the audit found tanh on three masters)."""
    pre = sum(stems.values())
    norm = 10 ** ((target_db - lufs(pre)) / 20)
    g = limiter_gain(pre * norm, ceil)
    f = np.fft.rfftfreq(pre.shape[-1], 1 / SR)

    def centred(x):                                                # under 150 Hz everything is in the middle (lows panned apart cancel on small speakers)
        mid, side = (x[0] + x[1]) / 2, (x[0] - x[1]) / 2
        side = np.fft.irfft(np.fft.rfft(side) * hp(150, 2)(f), x.shape[-1])
        return np.stack([mid + side, mid - side])
    stems = {k: (centred(x.astype(np.float64)) * norm * g).astype(np.float32) for k, x in stems.items()}
    return stems, sum(stems.values())


def texture_bed():
    """Tape hiss and a breath of wind, both very low, slowly breathing."""
    t = np.arange(LOOP_N) / SR
    hiss = circ(rng.standard_normal((2, LOOP_N)), lambda f: bp(2000, 12000, 1)(f))
    wind = circ(rng.standard_normal((2, LOOP_N)), lambda f: bp(150, 900)(f) / np.sqrt(np.maximum(f, 20) / 150))
    return (0.006 * hiss / np.abs(hiss).max() + 0.012 * wind / np.abs(wind).max() * loop_lfo(t, 5)).astype(np.float32)


def limiter_gain(x, ceil=0.9, block=48):
    pk = np.abs(x).max(axis=0)
    n = x.shape[-1]
    nb = n // block
    pb = pk[: nb * block].reshape(nb, block).max(axis=1)
    g = np.minimum(1, ceil / np.maximum(pb, 1e-9))
    w = 8
    gm = np.min([np.roll(g, s) for s in range(-w, w + 1)], axis=0)
    gs = np.mean([np.roll(gm, s) for s in range(-w // 2, w // 2 + 1)], axis=0)
    full = np.repeat(gs, block)
    return np.concatenate([full, np.full(n - len(full), full[-1])]).astype(np.float32)


PLANE = {"piano": (1.0, 9000), "lead": (0.95, 8000), "pad": (0.8, 6000), "comp": (1.0, 7000), "drums": (1.0, 12000),
         "bass": (1.0, 2500), "texture": (1.0, 14000)}
GAINS = {"piano": 1.0, "lead": 1.0, "pad": 0.9, "comp": 0.85, "bass": 0.5, "drums": 1.0, "texture": 1.0}


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
    send = rev + 0.4 * echo
    wet = np.stack([np.fft.irfft(np.fft.rfft(send[c]) * irs[c], LOOP_N) for c in range(2)])
    dry_amt, dark = PLANE[stem]
    out = dry_amt * circ(dry, lp(dark, 1)) + echo + WET * wet       # a small, dry room (0.7 with a 5 s tail was "a puddle of echoes")
    if stem == "texture":
        out = out + texture_bed()
    out = circ(out, hp(35, 2) if stem == "bass" else hp(90, 1))
    air = lambda f: 1 + (10 ** (2 / 20) - 1) / (1 + (2500 / np.maximum(f, 1)) ** 2)   # +2 dB shelf above 2.5 kHz (4 was harsh)
    out = circ(out * GAINS[stem], lambda f: hp(25, 2)(f) * lp(15000, 2)(f) * air(f))
    return out.astype(np.float32)


def _stem_job(stem):
    return stem, render_stem(stem, room(np.random.default_rng(3), LOOP_N))


def render():
    """Every stem in its own process, at once (they do not depend on each other)."""
    from concurrent.futures import ProcessPoolExecutor
    with ProcessPoolExecutor(max_workers=min(len(STEMS), os.cpu_count() or 2)) as pool:
        stems = dict(pool.map(_stem_job, STEMS))
    stems = {s: stems[s] for s in STEMS}
    stems, mix = master(stems, -17)
    return mix, stems


def write_wav(path, x):
    pcm = (np.clip(x, -1, 1) * 32767).round().astype("<i2").T.copy()
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


if __name__ == "__main__":
    print("registers:", registers())
    print("staircases in the melody:", staircases())
    print("melody notes on a beat that are not in the chord:", off_chord())
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
    meta = {"title": "Meadow Road", "by": "Fable 5.2", "bpm": BPM, "key": "D major", "mood": "calm ambient", "bars": BARS,
            "seconds": LOOP_S, "beats_per_hop": 2,
            "sections": [{"id": str(k + 1), "name": p["name"], "kind": "A" if p["mel"] else "rest",
                          "bar": k * 8, "t": k * 32 * BEAT} for k, p in enumerate(PLAN)],
            "stems": STEMS}
    (OUT / "track.json").write_text(json.dumps(meta, indent=1))
    rms = np.sqrt(np.mean(master.astype(np.float64) ** 2))
    print(f"{len(events)} notes, {LOOP_S:.0f}s loop, peak {np.abs(master).max():.3f}, rms {20 * np.log10(rms):.1f} dBFS")
    mono = master.mean(axis=0).astype(np.float64)
    nfft = 1 << 16
    fr = np.fft.rfftfreq(nfft, 1 / SR)
    P = sum(np.abs(np.fft.rfft(mono[k:k + nfft] * np.hanning(nfft))) ** 2 for k in range(0, len(mono) - nfft, nfft))
    print("  octave bands (dB of total):", "  ".join(f"{lo}:{10 * np.log10(P[(fr >= lo / 1.414) & (fr < lo * 1.414)].sum() / P.sum()):.0f}"
                                                       for lo in (63, 125, 250, 500, 1000, 2000, 4000, 8000)))
    blk = 8 * 4 * BEAT
    for s, x in list(stems.items()) + [("master", master)]:
        per = [20 * np.log10(np.sqrt(np.mean(x[:, int(k * blk * SR):int((k + 1) * blk * SR)].astype(np.float64) ** 2)) + 1e-9)
               for k in range(len(PLAN))]
        print(f"  {s:8s}", " ".join(f"{v:6.1f}" for v in per))
