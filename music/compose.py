"""Cozy modern chiptune town theme, rendered as a seamless loop plus stems.

Pure numpy. 48 kHz, 120 BPM, 32 bars in four sections:
  A  cozy groove      kalimba theme, FM electric piano, light drums
  B  main theme       detuned stereo chip lead, 16th chip arps, full groove
  C  bridge           ocarina, pads, half-time drums, a wistful minor turn
  D  finale           chip lead + chord-aware harmony, glock doubling, big drums

Production: sub + plucky mid bass, kick sidechain on chords/bass, ping-pong echo and
a stereo room, all computed circularly (FFT), so the loop has no seam: tails at the end
wrap into the start. A look-ahead limiter gain is shared by the master and the stems,
so the stems add up to the master.

    uv run python music/compose.py      # writes music/site/audio/*.wav + track.json
"""

from pathlib import Path
import json
import wave

import numpy as np

SR = 48000
BPM = 120
BEAT = 60 / BPM
SWING = 0.58
BARS = 32
LOOP_N = int(round(BARS * 4 * BEAT * SR))
TAIL = 4 * SR
OUT = Path(__file__).with_name("site") / "audio"
rng = np.random.default_rng(11)

PC = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


def midi(name):
    pc, rest = PC[name[0]], name[1:]
    while rest and rest[0] in "#b":
        pc += 1 if rest[0] == "#" else -1
        rest = rest[1:]
    return 12 * (int(rest) + 1) + pc


def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def t_of(slot):
    """Eighth-note slot (8 per bar, fractions allowed) -> seconds, swung off-beats."""
    beat = np.floor(slot / 2)
    frac = slot / 2 - beat
    f = frac / 0.5 * SWING if frac < 0.5 else SWING + (frac - 0.5) / 0.5 * (1 - SWING)
    return float((beat + f) * BEAT)


# ------------------------------------------------------------------ dsp helpers

def tt(n):
    return np.arange(n) / SR


def adsr(n, dur, a, d, s, r):
    t = tt(n)
    e = np.where(t < a, t / a, s + (1 - s) * np.exp(-(t - a) / d))
    return e * np.where(t > dur, np.clip(1 - (t - dur) / r, 0, 1), 1.0)


def fft_filter(y, resp):
    """Zero-phase static filter, resp(freqs) -> gain. Padded, so not circular."""
    n = len(y)
    m = 1 << int(np.ceil(np.log2(n + 2048)))
    spec = np.fft.rfft(y, m)
    spec *= resp(np.fft.rfftfreq(m, 1 / SR))
    return np.fft.irfft(spec, m)[:n]


def lp(fc, order=2):
    return lambda f: 1 / np.sqrt(1 + (f / fc) ** (2 * order))


def hp(fc, order=2):
    return lambda f: 1 / np.sqrt(1 + (fc / np.maximum(f, 1e-3)) ** (2 * order))


def bp(lo, hi):
    return lambda f: hp(lo)(f) * lp(hi)(f)


def glide_vib_phase(f, n, glide=-0.3, depth=0.14, rate=5.5, delay=0.2, detune=0.0):
    t = tt(n)
    ramp = np.clip((t - delay) / 0.3, 0, 1)
    semis = glide * np.exp(-t / 0.018) + depth * ramp * np.sin(2 * np.pi * rate * t) + detune
    return 2 * np.pi * np.cumsum(f * 2 ** (semis / 12)) / SR


def additive(ph, f, coef, bright):
    y = np.zeros_like(ph)
    for k in range(1, 60):
        if k * f > min(bright * 4, 16000):
            break
        c = coef(k)
        if c:
            y += c * np.sin(k * ph) / (1 + (k * f / bright) ** 2)
    return y


def pulse_coef(duty):
    return lambda k: np.sin(np.pi * k * duty) / k


saw_coef = lambda k: 1 / k  # noqa: E731
square_coef = lambda k: (1 / k) if k % 2 else 0  # noqa: E731


# ------------------------------------------------------------------ instruments
# each returns mono (n,) or stereo (2, n)

def chip_lead(f, dur, vel):
    n = int((dur + 0.35) * SR)
    env = adsr(n, dur, 0.004, 0.18, 0.72, 0.14)
    a = additive(glide_vib_phase(f, n, detune=+0.07), f, pulse_coef(0.25), 3800)
    b = additive(glide_vib_phase(f, n, detune=-0.07), f, pulse_coef(0.125), 3400)
    body = np.sin(glide_vib_phase(f, n))
    l, r = 0.75 * a + 0.35 * b + 0.3 * body, 0.35 * a + 0.75 * b + 0.3 * body
    return 0.42 * vel * np.stack([l, r]) * env


def chip_harm(f, dur, vel):
    n = int((dur + 0.3) * SR)
    y = additive(glide_vib_phase(f, n, glide=0, delay=0.25), f, pulse_coef(0.5), 2600)
    return 0.32 * vel * y * adsr(n, dur, 0.006, 0.2, 0.6, 0.12)


def chip_arp(f, dur, vel):
    n = int(0.22 * SR)
    t = tt(n)
    y = additive(2 * np.pi * f * t, f, pulse_coef(0.5), 4200)
    return 0.3 * vel * y * np.exp(-t / 0.07) * np.clip(t / 0.002, 0, 1)


def ocarina(f, dur, vel):
    n = int((dur + 0.3) * SR)
    ph = glide_vib_phase(f, n, glide=-0.2, depth=0.2, rate=5.0, delay=0.15)
    breath = fft_filter(rng.standard_normal(n), bp(800, 4000)) * 0.03
    y = np.sin(ph) + 0.16 * np.sin(2 * ph) + 0.05 * np.sin(3 * ph) + breath
    return 0.55 * vel * y * adsr(n, dur, 0.04, 0.25, 0.85, 0.16)


def kalimba(f, dur, vel):
    n = int(1.8 * SR)
    t = tt(n)
    y = (np.sin(2 * np.pi * f * t) * np.exp(-t / 0.6)
         + 0.3 * np.sin(2 * np.pi * f * 3.98 * t) * np.exp(-t / 0.09)
         + 0.12 * np.sin(2 * np.pi * f * 9.9 * t) * np.exp(-t / 0.03)
         + 0.05 * np.sin(2 * np.pi * f * 2.0 * t) * np.exp(-t / 0.3))
    return 0.5 * vel * y * np.clip(t / 0.0015, 0, 1)


def glock(f, dur, vel):
    n = int(2.2 * SR)
    t = tt(n)
    y = (np.sin(2 * np.pi * f * t) * np.exp(-t / 0.8)
         + 0.35 * np.sin(2 * np.pi * f * 2.76 * t) * np.exp(-t / 0.25)
         + 0.12 * np.sin(2 * np.pi * f * 5.40 * t) * np.exp(-t / 0.09))
    return 0.3 * vel * y * np.clip(t / 0.001, 0, 1)


def epiano(f, dur, vel):
    n = int((dur + 0.6) * SR)
    t = tt(n)
    ph = 2 * np.pi * f * t
    index = 1.1 * vel * np.exp(-t / 0.22) + 0.25
    y = np.sin(ph + index * np.sin(ph)) + 0.12 * np.sin(2 * np.pi * f * 7.0 * t) * np.exp(-t / 0.04)
    env = np.exp(-t / 1.8) * np.where(t > dur, np.clip(1 - (t - dur) / 0.35, 0, 1), 1) * np.clip(t / 0.003, 0, 1)
    trem = 0.22 * np.sin(2 * np.pi * 4.2 * t)
    y = 0.3 * vel * y * env
    return np.stack([y * (1 + trem), y * (1 - trem)])


def pad(f, dur, vel):
    n = int((dur + 0.9) * SR)
    voices = [additive(2 * np.pi * np.cumsum(np.full(n, f * 2 ** (d / 1200))) / SR, f, saw_coef, 1500)
              for d in (-11, 0, 12)]
    env = adsr(n, dur, 0.35, 1.0, 1.0, 0.8)
    l, r = voices[0] + 0.6 * voices[1], voices[2] + 0.6 * voices[1]
    r = np.roll(r, int(0.011 * SR))  # haas width
    return 0.09 * vel * np.stack([l, r]) * env


def bass(f, dur, vel):
    n = int((dur + 0.08) * SR)
    t = tt(n)
    ph = 2 * np.pi * f * t
    mid = np.zeros(n)
    for k in range(1, 30):
        if k * f > 5000:
            break
        # higher harmonics decay faster: a natural filter-envelope pluck
        mid += pulse_coef(0.3)(k) * np.sin(k * ph) * np.exp(-t * (2 + 9 * k))
    mid = np.tanh(2.2 * mid) * 0.45
    sub = np.sin(ph) * 0.75 + 0.08 * np.sin(2 * ph)
    env = np.clip(t / 0.003, 0, 1) * np.where(t > dur, np.clip(1 - (t - dur) / 0.05, 0, 1), 1)
    env *= 0.8 + 0.2 * np.exp(-t / 0.15)
    return 0.62 * vel * (sub + mid) * env


def _kick(tone=48, top=190):
    n = int(0.45 * SR)
    t = tt(n)
    fr = tone + (top - tone) * np.exp(-t / 0.032)
    body = np.sin(2 * np.pi * np.cumsum(fr) / SR) * np.exp(-t / 0.22) * np.clip(t / 0.0008, 0, 1)
    click = fft_filter(rng.standard_normal(n), bp(1500, 9000)) * np.exp(-t / 0.003) * 0.35
    return np.tanh(2.0 * (body + click)) * 0.85


def _snare():
    n = int(0.4 * SR)
    t = tt(n)
    body = np.sin(2 * np.pi * np.cumsum(170 + 60 * np.exp(-t / 0.02)) / SR) * np.exp(-t / 0.07) * 0.55
    noise = fft_filter(rng.standard_normal(n), bp(1400, 10000)) * np.exp(-t / 0.13) * 0.6
    return np.tanh(1.5 * (body + noise)) * 0.7


def _clap():
    n = int(0.35 * SR)
    t = tt(n)
    noise = fft_filter(rng.standard_normal(n), bp(900, 5000))
    env = sum(np.exp(-np.clip(t - o, 0, None) / 0.008) * (t >= o) for o in (0, 0.009, 0.019))
    env += np.exp(-np.clip(t - 0.028, 0, None) / 0.11) * (t >= 0.028)
    return noise * env * 0.55


def _hat(open_=False):
    n = int((0.45 if open_ else 0.08) * SR)
    t = tt(n)
    metal = sum(np.sign(np.sin(2 * np.pi * fr * t)) for fr in (3150, 4380, 5470, 6810, 8120))
    noise = rng.standard_normal(n) + 0.25 * metal
    y = fft_filter(noise, hp(7500, 3))
    return y * np.exp(-t / (0.14 if open_ else 0.022)) * 0.22


def _shaker():
    n = int(0.1 * SR)
    t = tt(n)
    return fft_filter(rng.standard_normal(n), hp(6000)) * np.clip(t / 0.015, 0, 1) * np.exp(-t / 0.035) * 0.16


def _crash():
    n = int(2.6 * SR)
    t = tt(n)
    metal = sum(np.sin(2 * np.pi * fr * t + p) for fr, p in zip((3810, 5230, 6930, 8370, 9850), (0, 1, 2, 3, 4)))
    y = fft_filter(rng.standard_normal(n) + 0.3 * metal, hp(4500, 2))
    return y * np.exp(-t / 0.9) * 0.18


DRUMS = {"kick": [_kick() for _ in range(3)], "tom": [_kick(110, 260) for _ in range(2)],
         "snare": [_snare() for _ in range(4)], "clap": [_clap() for _ in range(3)],
         "hat": [_hat() for _ in range(6)], "ohat": [_hat(True) for _ in range(3)],
         "shaker": [_shaker() for _ in range(6)], "crash": [_crash()]}
DRUMS["revcrash"] = [DRUMS["crash"][0][::-1][-int(1.0 * SR):] * np.linspace(0, 1, int(1.0 * SR)) ** 2]


def drum(kind):
    def play(f, dur, vel):
        v = DRUMS[kind]
        return vel * v[rng.integers(len(v))]
    return play


# ------------------------------------------------------------------ harmony

CHORDS = {
    "Fmaj9": "F A C E G", "Em7b5": "E G Bb D", "A7": "A C# E G", "Dm9": "D F A C E",
    "Cm7": "C Eb G Bb", "F7": "F A C Eb", "Bbmaj9": "Bb D F A C", "Bbm6": "Bb Db F G",
    "Am7": "A C E G", "D7": "D F# A C", "Gm7": "G Bb D F", "C7": "C E G Bb",
    "Bbmaj7": "Bb D F A", "Gm9": "G Bb D F A", "A7sus": "A D E G", "C7sus": "C F G Bb",
}
MAIN = [["Fmaj9"], ["Em7b5", "A7"], ["Dm9"], ["Cm7", "F7"],
        ["Bbmaj9"], ["Bbm6"], ["Am7", "D7"], ["Gm7", "C7"]]
BRIDGE = [["Dm9"], ["Bbmaj7"], ["Gm9"], ["A7sus", "A7"],
          ["Dm9"], ["Bbmaj7"], ["Gm7"], ["C7sus", "C7"]]


def pcs(ch):
    return [midi(p + "4") % 12 for p in CHORDS[ch].split()]


def voicing(ch, lo=57):
    tones = pcs(ch)
    if len(tones) >= 4:
        tones = tones[1:]  # rootless: the bass has the root
    return sorted(lo + (p - lo) % 12 for p in tones)


def root(ch, lo=33):
    return lo + (pcs(ch)[0] - lo) % 12


def harmony_below(m, ch):
    """Highest chord tone 3..9 semitones under the melody note."""
    for gap in (3, 4, 5, 8, 9, 7, 6):
        if (m - gap) % 12 in pcs(ch):
            return m - gap
    return m - 12


def segments(bar_chords):
    """[(chord, start_slot, length_slots)] inside one bar."""
    if len(bar_chords) == 1:
        return [(bar_chords[0], 0, 8)]
    return [(bar_chords[0], 0, 4), (bar_chords[1], 4, 4)]


def chord_at(bar_chords, slot):
    return bar_chords[0] if len(bar_chords) == 1 or slot < 4 else bar_chords[1]


# ------------------------------------------------------------------ melody

def parse(text):
    return [[(p, float(l)) for p, l in (tok.split(":") for tok in bar.split())]
            for bar in text.replace("\n", "|").split("|") if bar.strip()]


THEME = parse("""
A5:2 G5:1 A5:1 C6:2 A5:2 | G5:2 E5:1 G5:1 C#6:2 Bb5:2 | D6:2 C6:1 A5:1 F5:2 E5:1 F5:1 | G5:2 Eb5:1 G5:1 A5:2 C6:2
D6:3 C6:1 A5:2 F5:2 | Db6:3 C6:1 Bb5:2 G5:2 | C6:2 A5:1 C6:1 F#5:2 A5:2 | Bb5:2 A5:1 G5:1 E5:3 G5:1
""")
THEME_TO_BRIDGE = parse("C6:2 D6:1 C6:1 A5:2 F#5:2 | G5:3 E5:1 C5:2 r:2")
BRIDGE_MEL = parse("""
F5:4 E5:2 D5:2 | D5:2 F5:2 A5:4 | Bb5:4 A5:2 G5:2 | A5:3 G5:1 E5:2 C#5:2
D5:2 F5:2 A5:3 D6:1 | C6:4 A5:2 F5:2 | G5:2 Bb5:2 D6:3 C6:1 | C6:4 Bb5:2 G5:2
""")

# ------------------------------------------------------------------ arrangement

STEMS = ["melody", "keys", "sparkle", "bass", "drums"]
events = []  # (t, dur, midi, vel, inst, pan, stem, rev, echo)


def note(slot, length, m, vel, inst, stem, pan=0.0, rev=0.2, echo=0.0, gate=0.95, human=True):
    t0, t1 = t_of(slot), t_of(slot + length)
    if human:
        t0 += rng.normal(0, 0.0025)
        vel *= 1 + rng.normal(0, 0.05)
    events.append((t0, (t1 - t0) * gate, m, vel, inst, pan, stem, rev, echo))


def hit(slot, kind, vel, pan=0.0, rev=0.08):
    note(slot, 1, 60, vel, drum(kind), "drums", pan, rev=rev)


kicks = []
SECTIONS = [("A", "cozy groove", 0), ("B", "main theme", 8), ("C", "bridge", 16), ("D", "finale", 24)]

for bar in range(BARS):
    sec, i = "ABCD"[bar // 8], bar % 8
    prog = BRIDGE if sec == "C" else MAIN
    chords = prog[i]
    s0 = bar * 8
    nxt_chord = (BRIDGE if bar + 1 in range(16, 24) else MAIN)[(i + 1) % 8][0]

    # ---- melody
    if sec == "C":
        mel = BRIDGE_MEL[i]
    elif sec == "B" and i >= 6:
        mel = THEME_TO_BRIDGE[i - 6]
    else:
        mel = THEME[i]
    pos = 0.0
    for p, ln in mel:
        if p != "r":
            m = midi(p)
            ch = chord_at(chords, pos)
            if sec == "A":
                note(s0 + pos, ln, m - 12, 0.95, kalimba, "melody", 0.1, rev=0.25, echo=0.3)
            elif sec == "C":
                note(s0 + pos, ln, m - 12, 0.9, ocarina, "melody", 0.0, rev=0.35, echo=0.25)
            else:
                note(s0 + pos, ln, m, 0.9 if sec == "B" else 1.0, chip_lead, "melody", 0.0, rev=0.18, echo=0.22)
                note(s0 + pos, ln, m - 12, 0.35, kalimba, "melody", 0.35, rev=0.2)
                if sec == "D":
                    note(s0 + pos, ln, harmony_below(m, ch), 0.55, chip_harm, "melody", -0.35, rev=0.2, echo=0.15)
                    note(s0 + pos, ln, m + 12, 0.22, glock, "sparkle", 0.45, rev=0.3)
        pos += ln

    # ---- keys: FM piano comping (A, B, D), pads (B, C, D)
    for ch, start, length in segments(chords):
        v = voicing(ch)
        if sec != "C":
            hits = [(0, 1.5, 0.75), (3, 0.9, 0.5)] if length == 4 else [(0, 1.5, 0.75), (3, 0.9, 0.5), (4, 1.5, 0.6), (7, 0.8, 0.45)]
            for off, ln, vel in hits:
                for j, m in enumerate(v):
                    note(s0 + start + off + j * 0.02, ln, m, vel, epiano, "keys", -0.15 + 0.1 * j, rev=0.3)
        else:
            for j, m in enumerate(v):
                note(s0 + start, length, m, 0.6, epiano, "keys", -0.2 + 0.13 * j, rev=0.45, gate=1.0)
        if sec in "BCD":
            pv = {"B": 0.6, "C": 1.0, "D": 0.8}[sec]
            for m in v:
                note(s0 + start, length, m, pv, pad, "keys", 0.0, rev=0.5, gate=1.0, human=False)

    # ---- sparkle: 16th chip arps (B, D), kalimba eighth arps (C), glock bells (A)
    for ch, start, length in segments(chords):
        v = [m + 12 for m in voicing(ch)]
        pattern = v + v[-2:0:-1]
        if sec in "BD":
            for k in range(int(length * 2)):
                m = pattern[k % len(pattern)]
                note(s0 + start + k * 0.5, 0.5, m, 0.5 if k % 2 == 0 else 0.35, chip_arp, "sparkle",
                     0.55 if k % 2 else -0.55, rev=0.15, echo=0.2)
        elif sec == "C":
            for k in range(int(length)):
                note(s0 + start + k, 1, pattern[k % len(pattern)] - 12, 0.35, kalimba, "sparkle",
                     -0.5 if k % 2 else 0.5, rev=0.35, echo=0.25)
        elif sec == "A" and start == 0:
            note(s0 + 0.0, 2, v[-1] + 12, 0.35, glock, "sparkle", 0.4, rev=0.4, echo=0.35)

    # ---- bass
    for ch, start, length in segments(chords):
        r = root(ch)
        nr = root(nxt_chord) if start + length == 8 else root(chords[1])
        approach = nr - 1 if nr - 1 != r else nr + 2
        if sec == "C":
            pat = [(0, 3, r), (3, 1, r + 7), (4, 3, r), (7, 1, approach)] if length == 8 else [(0, 3, r), (3, 1, approach)]
        else:
            half = [(0, 1.5, r), (1.5, 0.5, r + 12), (2, 1, r + 7), (3, 1, approach)]
            pat = half if length == 4 else [(0, 1.5, r), (1.5, 0.5, r + 12), (2, 1, r + 7), (3, 1, r + 12),
                                            (4, 1.5, r), (5.5, 0.5, r + 12), (6, 1, r + 7), (7, 1, approach)]
            if sec == "A":
                pat = [p for p in pat if p[1] != 0.5]
        for off, ln, m in pat:
            note(s0 + start + off, ln, m, 0.9, bass, "bass", 0.0, rev=0.02, gate=0.8)

    # ---- drums
    fill = i == 7
    if sec == "C":
        kick_slots = [0, 5] if i % 2 else [0]
        for s in kick_slots:
            hit(s0 + s, "kick", 0.85)
        hit(s0 + 4, "snare", 0.7, rev=0.25)
        for s in range(8):
            hit(s0 + s, "hat", 0.35 if s % 2 else 0.5, 0.3)
        hit(s0 + 7, "ohat", 0.35, -0.3)
    else:
        kick_slots = [0, 4] if sec == "A" else [0, 3, 4] + ([7] if sec == "D" and i % 2 else [])
        if fill:
            kick_slots = [s for s in kick_slots if s < 6]
        for s in kick_slots:
            hit(s0 + s, "kick", 0.95)
        for s in (2, 6):
            if fill and s == 6:
                continue
            if sec == "A":
                hit(s0 + s, "clap", 0.5, 0.1, rev=0.25)
            else:
                hit(s0 + s, "snare", 0.75, 0.05, rev=0.2)
                if sec == "D":
                    hit(s0 + s, "clap", 0.45, -0.1, rev=0.25)
        if sec == "A":
            for s in range(16):
                hit(s0 + s * 0.5, "shaker", 0.45 if s % 2 == 0 else 0.3, 0.35)
        else:
            for s in range(8):
                hit(s0 + s, "ohat" if (sec == "D" and s % 2) else "hat",
                    (0.3 if sec == "D" else 0.55) if s % 2 else 0.4, 0.3)
            for s in range(16):
                hit(s0 + s * 0.5, "shaker", 0.25, -0.35)
    if fill:
        for k in range(8):
            kind = "tom" if sec == "C" else "snare"
            hit(s0 + 6 + k * 0.25, kind, 0.35 + 0.08 * k, -0.4 + 0.1 * k, rev=0.2)
    for s in kick_slots:
        kicks.append(t_of(s0 + s))

    # ---- fx: crash on each section start, reverse crash into B and D
    if i == 0:
        hit(s0, "crash", 0.55 if sec in "BD" else 0.3, 0.2, rev=0.3)
    if i == 7 and sec in "AC":
        events.append((t_of(s0 + 8) - 1.0, 1.0, 60, 0.45, drum("revcrash"), -0.2, "drums", 0.3, 0.0))

    # cute glock glissando into the finale
    if bar == 23:
        for k, m in enumerate([midi(n) for n in "F6 G6 A6 Bb6 C7 D7 E7 F7".split()]):
            note(s0 + 6 + k * 0.25, 0.5, m, 0.25 + 0.04 * k, glock, "sparkle", -0.4 + 0.1 * k, rev=0.4)


# ------------------------------------------------------------------ render

def fold(x):
    out = x[:, :LOOP_N].copy()
    out[:, :TAIL] += x[:, LOOP_N:]
    return out


def circ_lin(x, resp):
    spec = np.fft.rfft(x, axis=-1)
    return np.fft.irfft(spec * resp(np.fft.rfftfreq(LOOP_N, 1 / SR)), LOOP_N, axis=-1)


def echo_fx(mono):
    """Infinite ping-pong echo, darker every repeat, computed in the frequency domain (circular)."""
    d = int(0.75 * BEAT * SR)
    f = np.fft.rfftfreq(LOOP_N, 1 / SR)
    k = np.arange(len(f))
    z = 0.42 * lp(3500, 1)(f) * hp(250, 1)(f) * np.exp(-2j * np.pi * k * d / LOOP_N)
    x = np.fft.rfft(mono)
    left = np.fft.irfft(x * z / (1 - z ** 2), LOOP_N)
    right = np.fft.irfft(x * z ** 2 / (1 - z ** 2), LOOP_N)
    return 0.6 * np.stack([left, right])


def make_ir():
    n = int(2.8 * SR)
    t = tt(n)
    irs = []
    for _ in range(2):
        dark = fft_filter(rng.standard_normal(n), lp(2500)) * np.exp(-t / 0.42)
        bright = fft_filter(rng.standard_normal(n), hp(2500)) * np.exp(-t / 0.16) * 0.6
        ir = dark + bright
        ir[: int(0.02 * SR)] = 0
        for delay, g in ((0.011, 0.5), (0.017, 0.4), (0.023, 0.35), (0.031, 0.3)):
            ir[int((delay + rng.uniform(0, 0.004)) * SR)] += g * 3
        ir /= np.sqrt(np.sum(ir ** 2))
        pad_ = np.zeros(LOOP_N)
        pad_[:n] = ir
        irs.append(np.fft.rfft(pad_))
    return irs


def sidechain():
    """Kick-driven ducking envelope 0..1 (circular)."""
    env = np.zeros(LOOP_N)
    shape_n = int(0.35 * SR)
    t = tt(shape_n)
    shape = np.clip(t / 0.006, 0, 1) * np.exp(-t / 0.11)
    for tk in kicks:
        i = int(tk * SR) % LOOP_N
        idx = (np.arange(shape_n) + i) % LOOP_N
        env[idx] = np.maximum(env[idx], shape)
    return env


def limiter_gain(x, ceil=0.94, block=48):
    peak = np.abs(x).max(axis=0)
    nb = LOOP_N // block
    pb = peak[: nb * block].reshape(nb, block).max(axis=1)
    g = np.minimum(1, ceil / np.maximum(pb, 1e-9))
    w = 6  # look-ahead / hold, in blocks (6 ms)
    gm = np.min([np.roll(g, s) for s in range(-w, w + 1)], axis=0)
    gs = np.mean([np.roll(gm, s) for s in range(-w // 2, w // 2 + 1)], axis=0)
    full = np.repeat(gs, block)
    return np.concatenate([full, np.full(LOOP_N - len(full), full[-1])])


def render():
    n = LOOP_N + TAIL
    buses = {s: {k: np.zeros((2, n)) for k in ("dry", "rev", "echo")} for s in STEMS}
    for t, dur, m, vel, inst, pan, stem, rs, es in events:
        y = inst(hz(m), dur, vel)
        y = np.atleast_2d(y)
        if y.shape[0] == 1:
            y = np.vstack([y, y])
        i = int(round(t * SR)) % LOOP_N
        y = y[:, : n - i]
        a = (pan + 1) * np.pi / 4
        y = y * np.array([[np.cos(a)], [np.sin(a)]]) * np.sqrt(2)
        b = buses[stem]
        b["dry"][:, i:i + y.shape[1]] += y
        if rs:
            b["rev"][:, i:i + y.shape[1]] += rs * y
        if es:
            b["echo"][:, i:i + y.shape[1]] += es * y

    irs = make_ir()
    duck = sidechain()
    depth = {"melody": 0.1, "keys": 0.45, "sparkle": 0.3, "bass": 0.6, "drums": 0.0}
    stems = {}
    for s in STEMS:
        b = {k: fold(v) for k, v in buses[s].items()}
        echo = echo_fx(b["echo"].mean(axis=0))
        send = circ_lin(b["rev"] + 0.35 * echo, hp(220, 1))
        wet = np.stack([np.fft.irfft(np.fft.rfft(send[c]) * irs[c], LOOP_N) for c in range(2)])
        mix = b["dry"] + echo + 0.85 * wet
        mix = mix * (1 - depth[s] * duck)
        stems[s] = mix

    # per-stem tone shaping: tight lows on everything but bass and kick, silky top
    stems["bass"] = circ_lin(stems["bass"], lambda f: hp(28, 2)(f) * lp(6000, 1)(f))
    for s in ("melody", "keys", "sparkle"):
        stems[s] = circ_lin(stems[s], hp(140, 1))
    gains = {"melody": 1.0, "keys": 0.75, "sparkle": 0.95, "bass": 1.0, "drums": 0.9}
    for s in STEMS:
        stems[s] = circ_lin(stems[s] * gains[s], lambda f: hp(22, 2)(f) * lp(17000, 2)(f))

    pre = sum(stems.values())
    norm = 0.2 / np.sqrt(np.mean(pre ** 2))  # loudness target, then limit the peaks
    g = limiter_gain(pre * norm)
    for s in STEMS:
        stems[s] = stems[s] * norm * g
    master = sum(stems.values())
    return master, stems


def write_wav(path, x):
    pcm = (np.clip(x, -1, 1) * 32767).round().astype("<i2").T.copy()
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


if __name__ == "__main__":
    master, stems = render()
    OUT.mkdir(parents=True, exist_ok=True)
    write_wav(OUT / "master.wav", master)
    for s, x in stems.items():
        write_wav(OUT / f"stem_{s}.wav", x)
    meta = {"title": "Pocketful of Sunshine Town", "bpm": BPM, "bars": BARS, "seconds": LOOP_N / SR,
            "sections": [{"id": a, "name": b, "bar": c, "t": c * 4 * BEAT} for a, b, c in SECTIONS],
            "stems": STEMS}
    (OUT / "track.json").write_text(json.dumps(meta, indent=1))
    rms = np.sqrt(np.mean(master ** 2))
    print(f"{len(events)} notes, {LOOP_N / SR:.1f}s loop, peak {np.abs(master).max():.3f}, "
          f"rms {20 * np.log10(rms):.1f} dBFS, seam {np.abs(master[:, 0] - master[:, -1]).max():.4f}, "
          f"max step {np.abs(np.diff(master, axis=1)).max():.4f}")
    for s, x in stems.items():
        print(f"  {s:8s} rms {20 * np.log10(np.sqrt(np.mean(x ** 2)) + 1e-12):6.1f} dBFS")
