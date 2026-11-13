"""Side street, and eight ways of playing it.

The piece (4/4, F major): jazz harmony as Animal Crossing and city pop use it (ninths and thirteenths, a ii-V into
every new chord, the minor iv), rootless voicings that move by step, a bass that enters each root from a semitone
below. The lead is ONE cell repeated in every bar and only moved to fit the chord. The user called this "good", after
"naive, generic" (four plain chords) and "going anywhere" (a tune whose bars all differed).

The eight ways answer "make it cuter or sweeter, animal-crossing feeling or minecraft feeling. many propositions":
same lead cell and chords, other sounds, tempo, drums, bass and comping (PIECES below).

A check refuses any tune note a minor ninth above a note of its chord.

    uv run --no-project --python 3.11 --with dawdreamer --with numpy python music/pieces.py [id ...]
"""
from pathlib import Path
import json
import wave

import numpy as np

import surge
from directions import midi

SR = surge.SR
OUT = Path(__file__).with_name("site") / "audio"
rng = np.random.default_rng(23)

# ---------------------------------------------------------------- Side street (4/4: 16 steps a bar)
V1 = {"Fmaj9": "A3 C4 E4 G4", "Em7b5": "G3 Bb3 D4 E4", "A7b9": "G3 Bb3 C#4 E4", "Dm9": "F3 A3 C4", "Cm7": "G3 Bb3 C4 Eb4", "F13": "Eb3 G3 A3 D4",
      "Bbmaj9": "A3 C4 D4 F4", "Bbm6": "G3 Bb3 Db4 F4", "Am7": "G3 A3 C4 E4", "D9": "F#3 A3 C4 E4", "Gm9": "F3 Bb3 D4", "C13": "E3 Bb3 D4", "F69": "A3 C4 D4 G4"}
R1 = {"Fmaj9": "F2", "Em7b5": "E2", "A7b9": "A2", "Dm9": "D2", "Cm7": "C3", "F13": "F2", "Bbmaj9": "Bb2", "Bbm6": "Bb2", "Am7": "A2", "D9": "D3", "Gm9": "G2", "C13": "C3", "F69": "F2"}
H1 = ["Fmaj9", "Em7b5 A7b9", "Dm9", "Cm7 F13", "Bbmaj9", "Bbm6", "Am7 D9", "Gm9 C13",
      "Fmaj9", "Em7b5 A7b9", "Dm9", "Cm7 F13", "Bbmaj9", "Bbm6", "Gm9 C13", "F69"]
# The lead is ONE cell: two short notes up into a long one, then a fall (steps 2, 4, 6, 12). Every bar plays it; only
# the pitches move, to fit the chord. The fourth bar of each phrase is the cadence: three notes down to a held one.
# (The first version changed shape every bar: "a single thing going anywhere... the lead is doing bullshit".)
CELL = [(2, 2), (4, 2), (6, 5), (12, 4)]
CADENCE = [(0, 3), (3, 3), (6, 2), (8, 8)]
PITCH = [("cell", "A4 C5 E5 C5"), ("cell", "G4 Bb4 E5 C#5"), ("cell", "F4 A4 D5 A4"), ("cadence", "Eb5 D5 Bb4 A4"),
         ("cell", "A4 D5 F5 D5"), ("cell", "G4 Db5 F5 Db5"), ("cell", "G4 C5 E5 C5"), ("cadence", "D5 Bb4 A4 G4")]
PITCH = PITCH + PITCH[:6] + [("cadence", "D5 Bb4 A4 G4"), ("cadence", "A4 G4 F4 F4")]          # the same eight bars again, then home
T1 = [[(s, ln, n) for (s, ln), n in zip(CELL if kind == "cell" else CADENCE, notes.split())] for kind, notes in PITCH]
T1[-1] = [(0, 3, "A4"), (3, 3, "G4"), (6, 10, "F4")]
ACC = [1.0, 0.7, 0.8, 0.72, 0.9, 0.7, 0.84, 0.72, 0.95, 0.7, 0.8, 0.72, 0.9, 0.7, 0.86, 0.76]


def tune(cell, cadence, bars):
    return [[(s, ln, n) for (s, ln), n in zip(cell if kind == "cell" else cadence, notes.split())] for kind, notes in bars]


# Old Mossback, the boss: its own theme (the first reused the day's cell: "looks too much like the main theme").
# Two earlier candidates failed: "Chase B sounds off-rhythm" (measured: its lead sound spoke 65 ms late and its chord
# sound echoed between the beats) and "Mossback A sounds boring. not a boss".
# So: 160 BPM, C minor. Four bars of intro (riff, kick, crashes, a tom fill), then A A B A. The bass is a riff in
# sixteenths with the octave popping out in threes. The lead is a held synth lead, not a pluck: one cell of three notes
# in 3+3+2 (a long note, a step down, a leap down); each phrase ends on a held leading note (B over G7) that wants C.
# B lifts to the major side (Ab, Bb, Gm7, Cm), then a diminished bar and the dominant. Every sound passes
# surge.timing(): under 15 ms late, no echo.
VM = {"Cm": "Eb3 G3 C4", "Ab": "Eb3 Ab3 C4", "G7": "F3 B3 D4", "Fm": "Ab3 C4 Eb4", "Bb": "F3 Bb3 C4", "G7#5": "F3 B3 Eb4", "Gm7": "F3 Bb3 D4", "Dm7b5": "F3 Ab3 C4"}
RM = {"Cm": "C2", "Ab": "Ab2", "G7": "G2", "Fm": "F2", "Bb": "Bb2", "G7#5": "G2", "Gm7": "G2", "Dm7b5": "D2"}
# The lead, second version ("amazing !!! but the lead is a bit.. freestyling"): A is ONE bar played three times over
# changing chords, then the hanging cadence; B is one other bar three times, then a cadence. Before, five bars of
# eight differed.
_TMA = [("cell", "Eb5 D5 G4")] * 3 + [("cadence", "D5 B4")] + [("cell", "Eb5 D5 G4")] * 3 + [("cadence", "D5 B4")]
_TMB = [("cell", "G5 F5 C5")] * 3 + [("cadence", "Eb5 C5")] + [("cell", "G5 F5 C5")] * 3 + [("cadence", "D5 B4")]
_MA = ["Cm", "Cm", "Ab", "G7", "Cm", "Fm", "Ab Bb", "G7"]

# The third theme. Lantern fish on a flute-like lead, a kalimba and congas "sounds like those ugly midi songs":
# synth sounds imitating acoustic instruments are the MIDI sound. Everything the user liked is a synth being a synth.
# Two candidates, both on synth sounds:
#   Lantern fish  the same score (6/8, D Dorian) as a slow synth ballad: a soft synth lead, held analog chords,
#                 string-machine pad, kick on the first beat and clap on the second.
#   Far shore     4/4, A major from the IV with the Lydian chord (E over D): ONE lead bar that fits all seven chords,
#                 so the tune stays still while the harmony moves under it; a kick on every beat.
VL = {"Dm9": "F3 A3 C4", "G13": "F3 B3 E4", "Bbmaj7": "A3 D4 F4", "Am7": "G3 C4 E4", "Gm9": "F3 Bb3 D4", "A7sus": "G3 D4 E4", "A7b9": "G3 Bb3 C#4 E4"}
RL = {"Dm9": "D2", "G13": "G2", "Bbmaj7": "Bb2", "Am7": "A2", "Gm9": "G2", "A7sus": "A2", "A7b9": "A2"}
_TL = [("cell", "D5 C5 A4"), ("cell", "E5 D5 B4"), ("cell", "D5 C5 A4"), ("cadence", "E5 D5"),
       ("cell", "F5 E5 C5"), ("cell", "E5 D5 B4"), ("cell", "D5 C5 A4"), ("cadence", "D5 E5")]
_TL2 = _TL[:6] + [("cell", "D5 C5 A4"), ("cadence", "Bb4 A4")]

# Kite weather, a second day and night tune. A major, starting on the IV (D, C#m, Bm, E; then home to A).
# Its own cell: two notes down onto a long one, and a pickup into the next bar (steps 0, 3, 6, 14).
VK = {"Dmaj9": "F#3 A3 C#4 E4", "C#m7": "E3 G#3 B3", "Bm9": "A3 D4 F#4", "E13": "D3 G#3 C#4", "Amaj9": "G#3 B3 C#4 E4"}
RK = {"Dmaj9": "D3", "C#m7": "C#3", "Bm9": "B2", "E13": "E2", "Amaj9": "A2"}
_TK = [("cell", "E5 C#5 A4 B4"), ("cell", "E5 B4 G#4 B4"), ("cell", "D5 A4 F#4 A4"), ("cadence", "B4 G#4 B4"),
       ("cell", "E5 C#5 A4 B4"), ("cell", "E5 B4 G#4 B4"), ("cell", "D5 A4 F#4 G#4"), ("cadence", "B4 C#5 E5")]

VF = {"Dmaj9": "F#3 A3 C#4 E4", "E/D": "E3 G#3 B3 E4", "C#m7": "E3 G#3 B3", "F#m9": "E3 A3 C#4", "Bm9": "A3 D4 F#4", "E11": "A3 B3 D4", "Amaj9": "G#3 B3 C#4 E4",
      "A69": "F#3 B3 C#4 E4"}
RF = {"Dmaj9": "D3", "E/D": "D3", "C#m7": "C#3", "F#m9": "F#2", "Bm9": "B2", "E11": "E2", "Amaj9": "A2", "A69": "A2"}
_TF = [("cell", "E5 C#5 B4 C#5")] * 3 + [("cadence", "C#5 A4")] + [("cell", "E5 C#5 B4 C#5")] * 3 + [("cadence", "B4 A4")]

SCORES = {
    "street": dict(H=H1, V=V1, R=R1, T=T1),
    "mossback": dict(H=["Cm"] * 4 + _MA + _MA + ["Ab", "Bb", "Gm7", "Cm", "Ab", "Bb", "Dm7b5", "G7"] + _MA, V=VM, R=RM,
                     T=[[]] * 4 + tune([(0, 6), (6, 6), (12, 4)], [(0, 6), (6, 10)], _TMA + _TMA + _TMB + _TMA)),
    "shore": dict(H=["Dmaj9", "E/D", "C#m7", "F#m9", "Bm9", "E11", "Amaj9", "A69"] * 2, V=VF, R=RF,
                  T=tune([(0, 4), (6, 2), (8, 2), (10, 6)], [(0, 4), (6, 10)], _TF * 2)),
    "lantern": dict(spb=12, H=(["Dm9", "G13", "Dm9", "G13", "Bbmaj7", "Am7", "Gm9", "A7sus"] + ["Dm9", "G13", "Dm9", "G13", "Bbmaj7", "Am7", "Gm9", "A7b9"]) * 2,
                    V=VL, R=RL, T=tune([(0, 6), (6, 2), (8, 4)], [(0, 6), (6, 6)], (_TL + _TL2) * 2)),
    "kite": dict(H=["Dmaj9", "C#m7", "Bm9", "E13", "Dmaj9", "C#m7", "Bm9 E13", "Amaj9"] * 2, V=VK, R=RK,
                 T=tune([(0, 3), (3, 3), (6, 6), (14, 2)], [(0, 3), (3, 3), (6, 10)], _TK * 2)),
}


def side_street(st):
    """The score, in the manner `st` asks for: drums full / light / bossa / brush / none, bass walk / bounce / long,
    comp (the keys) comp / stab / hold; for the boss: drums boss, bass drive, comp stab5. The score is SCORES[st["score"]]."""
    H1, V1, R1, T1 = (SCORES[st.get("score", "street")][k] for k in "HVRT")
    spb = SCORES[st.get("score", "street")].get("spb", 16)                       # sixteenths in a bar: 16 is 4/4, 12 is 6/8
    acc = (lambda s: ACC[int(s) % 16]) if spb == 16 else (lambda s: (1.0, 0.7, 0.8, 0.7, 0.84, 0.7, 0.94, 0.7, 0.8, 0.7, 0.86, 0.72)[int(s) % 12])
    p = {k: [] for k in ("lead", "double", "chords", "pad", "bass", "kick", "snare", "clap", "hat", "open", "shaker", "conga", "click", "brush", "crash", "tom")}
    roots = [(spb * b + (spb // 2 * j if len(bar.split()) == 2 else 0), ch) for b, bar in enumerate(H1) for j, ch in enumerate(bar.split())]
    for b, bar in enumerate(H1):
        s0, chs = spb * b, bar.split()
        for s, ln, n in T1[b]:
            p["lead"].append((s0 + s, ln, midi(n) + st.get("lead_up", 0), 100 * acc(s)))
            if st.get("double") and b >= len(H1) // 2:
                p["double"].append((s0 + s, ln, midi(n) + st.get("double_shift", 12), 76 * acc(s)))               # the second time through, a second sound an octave up
        for j, ch in enumerate(chs):
            at, split = s0 + spb // 2 * j, len(chs) == 2
            hits = {"comp": [(0, 6)] if split else [(0, 5), (10, 4)] if b % 2 == 0 else [(0, 3), (7, 5)],
                    "stab": [(2, 1), (6, 1)] if split else [(2, 1), (6, 1), (10, 1), (14, 1)],
                    "stab5": [(0, 2), (3, 2), (6, 1)] if split else [(0, 2), (3, 2), (6, 2), (10, 1), (12, 2)],
                    "lilt": [(0, 3), (4, 2)] if split else [(0, 3), (4, 2), (6, 3), (10, 2)],      # 6/8: on 1, 3, 4 and 6
                    "hold": [(0, spb // 2 if split else spb)]}[st["comp"]]
            for i, n in enumerate(V1[ch].split()):
                for s, ln in hits:
                    p["chords"].append((at + s, ln, midi(n) + st.get("chords_up", 0), (80 - 3 * i) * acc(at + s - s0)))
                if i >= 1:
                    p["pad"].append((at, spb // len(chs), midi(n) + 12, 58))
    for k, (at, ch) in enumerate(roots):
        nxt_at, nxt = roots[(k + 1) % len(roots)]
        span = (nxt_at - at) % (spb * len(H1)) or spb
        r = midi(R1[ch])
        if st["bass"] == "long":
            p["bass"].append((at, span - 1, r, 96))
            continue
        if st["bass"] == "riff":                    # sixteenths on the root, the octave popping out in threes (3+3+2+3+3+2): no approach note
            p["bass"] += [(at + s, 0.9, r + (12 if s % 8 in (3, 6) else 0), 108 if s % 8 == 0 else 96 if s % 8 in (3, 6) else 84) for s in range(span)]
            continue
        if st["bass"] == "lilt":                    # 6/8: the root, then the fifth on the second beat
            p["bass"] += [(at, 5, r, 100)] + ([(at + 6, 4, r + 7, 86)] if span == 12 else [])
        elif st["bass"] == "drive":                   # eighth notes, the octave on the off-beats
            p["bass"] += [(at + s, 1.6, r + (12 if s % 4 == 2 else 0), 106 if s % 8 == 0 else 90) for s in range(0, span - 2, 2)]
        elif st["bass"] == "bounce":
            p["bass"] += [(at + s, 1.5, r + (12 if s % 8 == 4 else 0), 104 if s == 0 else 88) for s in range(0, span - 2, 4)]
        else:
            p["bass"].append((at, min(5, span - 2), r, 104))
            if span == 16:
                p["bass"] += [(at + 6, 1, r, 78), (at + 8, 4, r + (7 if r < 43 else -5), 92)]
        p["bass"].append((at + span - 2, 2, midi(R1[nxt]) - 1, 86))                 # into the next root from a semitone below
    d = st["drums"]
    intro = st.get("intro", 0)                                  # bars before the tune comes in
    for b in range(len(H1)):
        s0, end = spb * b, b % 8 == 7
        if d == "bossfast":                          # kick on 1, before 3, on 3 and before 1; snare on 2 and 4; a crash at each new part; tom fills
            fill, start = (b - intro) % 8 == 7 or b == intro - 1, b == 0 or (b - intro) % 8 == 0
            p["crash"] += [(s0, 4, 60, 100)] if start else []
            p["kick"] += [(s0 + s, 1, 48, 118 if s in (0, 8) else 100) for s in ((0, 8) if b < intro // 2 else (0, 6, 8, 14))]
            if b >= intro // 2:
                p["snare"] += [(s0 + 4, 1, 60, 108), (s0 + 12, 1, 60, 112)] if not fill else [(s0 + 4, 1, 60, 108)]
                p["clap"] += [(s0 + 12, 1, 60, 96)] if not fill else []
                p["hat"] += [(s0 + s, 1, 60, 88 * ACC[s]) for s in range(0, 8 if fill else 16, 2)]
            if fill:                                 # eight sixteenths down the toms into the next part
                p["tom"] += [(s0 + 8 + k, 1, 57 - 2 * (k // 2), 86 + 4 * k) for k in range(8)]
        if d == "ballad":                            # 6/8 on a drum machine: kick on the first beat, clap on the second, hats on the eighths
            p["kick"] += [(s0, 1, 48, 104)] + ([(s0 + 10, 1, 48, 80)] if b % 4 == 3 else [])
            p["clap"] += [(s0 + 6, 1, 60, 92)]
            p["hat"] += [(s0 + s, 1, 60, 78 * acc(s)) for s in range(0, 12, 2)]
        if d == "four":                              # a kick on every beat, closed hats between, claps on 2 and 4
            p["kick"] += [(s0 + s, 1, 48, 110 if s == 0 else 100) for s in (0, 4, 8, 12)]
            p["clap"] += [(s0 + 4, 1, 60, 86), (s0 + 12, 1, 60, 92)]
            p["hat"] += [(s0 + s, 1, 60, 88) for s in (2, 6, 10, 14)] + [(s0 + 15, 1, 60, 56)]
            p["snare"] += [(s0 + 13, 1, 60, 76), (s0 + 14, 1, 60, 88), (s0 + 15, 1, 60, 100)] if end else []
        if d == "lilt":                              # 6/8, no kit: a low and a high conga on the two beats, a shaker on every eighth, clicks between
            p["conga"] += [(s0, 1, 55, 90), (s0 + 6, 1, 60, 76)] + ([(s0 + 10, 1, 60, 64)] if b % 2 else [])
            p["shaker"] += [(s0 + s, 1, 60, 62 * acc(s)) for s in range(0, 12, 2)]
            p["click"] += [(s0 + 4, 1, 60, 76), (s0 + 10, 1, 60, 70)] if b >= 4 else []
        if d == "full":
            p["kick"] += [(s0, 1, 48, 110), (s0 + 7, 1, 48, 88), (s0 + 10, 1, 48, 98)]
            p["snare"] += [(s0 + 4, 1, 60, 96), (s0 + 12, 1, 60, 102)] + ([(s0 + 13, 1, 60, 70), (s0 + 15, 1, 60, 92)] if end else [])
            p["clap"] += [(s0 + 12, 1, 60, 90)] if st.get("claps") else []
            p["hat"] += [(s0 + s, 1, 60, 90 * ACC[s]) for s in range(0, 16, 2) if not (b % 4 == 3 and s == 14)]
            p["open"] += [(s0 + 14, 2, 60, 80)] if b % 4 == 3 else []
            p["shaker"] += [(s0 + s, 1, 60, 60 * ACC[s]) for s in range(16)]
        if d == "boss":                              # its feet on 1 and 3, a push before 4, sixteenth hats, a fill every eight bars
            fill = b % 8 == 7
            p["kick"] += [(s0, 1, 48, 118), (s0 + 8, 1, 48, 112), (s0 + 11, 1, 48, 92)]
            p["snare"] += [(s0 + 4, 1, 60, 106), (s0 + 12, 1, 60, 110)] + ([(s0 + s, 1, 60, 70 + 10 * (s - 12)) for s in (13, 14, 15)] if fill else [])
            p["clap"] += [(s0 + 12, 1, 60, 96)]
            p["hat"] += [(s0 + s, 1, 60, 86 * ACC[s]) for s in range(16) if not (fill and s >= 12)]
            p["open"] += [(s0 + 6, 2, 60, 78)] if b % 2 else []
        if d == "chase":                             # a kick on every beat, an open hat between, snare and clap on 2 and 4
            fill = b % 8 == 7
            p["kick"] += [(s0 + s, 1, 48, 114 if s == 0 else 104) for s in (0, 4, 8, 12)]
            p["snare"] += [(s0 + 4, 1, 60, 100), (s0 + 12, 1, 60, 106)] + ([(s0 + 14, 1, 60, 84), (s0 + 15, 1, 60, 98)] if fill else [])
            p["clap"] += [(s0 + 4, 1, 60, 84), (s0 + 12, 1, 60, 92)]
            p["open"] += [(s0 + s, 2, 60, 82) for s in (2, 6, 10, 14) if not (fill and s == 14)]
            p["hat"] += [(s0 + s, 1, 60, 70 * ACC[s]) for s in range(0, 16, 4)]
        if d == "light":
            p["kick"] += [(s0, 1, 48, 96), (s0 + 10, 1, 48, 84)]
            p["hat"] += [(s0 + s, 1, 60, 80 * ACC[s]) for s in (2, 6, 10, 14)]
            p["clap"] += [(s0 + 12, 1, 60, 80)] if st.get("claps") else []
            p["shaker"] += [(s0 + s, 1, 60, 58 * ACC[s]) for s in range(0, 16, 2)]
        if d == "bossa":
            p["conga"] += [(s0 + s, 1, n, v) for s, n, v in ((0, 55, 92), (3, 60, 76), (6, 60, 88), (8, 55, 80), (10, 60, 84), (13, 60, 74), (14, 55, 86))]
            p["click"] += [(s0 + s, 1, 60, 84) for s in (0, 3, 6, 10, 12)]
            p["shaker"] += [(s0 + s, 1, 60, 64 * ACC[s]) for s in range(0, 16, 2)]
        if d == "brush":
            p["kick"] += [(s0, 1, 48, 86)]
            p["brush"] += [(s0 + 4, 2, 60, 80), (s0 + 12, 2, 60, 86)]
            p["shaker"] += [(s0 + s, 1, 60, 56 * ACC[s]) for s in range(0, 16, 2)]
    under = {s0 + s: (V1[ch].split() + [R1[ch]], ch) for b, bar in enumerate(H1) for j, ch in enumerate(bar.split())
             for s0 in [spb * b] for s in range(spb // 2 * j, spb if j == len(bar.split()) - 1 else spb // 2)}
    return {k: v for k, v in p.items() if v}, spb * len(H1), under


LEVEL = {"lead": -15, "double": -22, "chords": -21, "pad": -25, "bass": -18, "kick": -18, "snare": -21, "clap": -25, "hat": -27, "open": -28, "shaker": -31,
         "conga": -22, "click": -27, "brush": -23, "crash": -24, "tom": -20}
DUCK = {"pad": 0.4, "chords": 0.2, "bass": 0.3}
KIT = dict(kick="Vospi/Drums/Proper Kick", snare="Vospi/Drums/Simple Snare", clap="Emu/Drums/T8 Clap", hat="Emu/Drums/Hat Closed", open="Emu/Drums/Hat Open",
           shaker="Emu/Drums/Egg Shaker", crash="Emu/Drums/T8 Cymbal", tom="Emu/Drums/T8 Tom", conga="Emu/Drums/T8 Conga", click="Vospi/Drums/Nice Clicks Perc", brush="Malfunction/Drums/Brush")
BASE = dict(bpm=96, swing=0.5, drums="full", bass="walk", comp="comp", lead="Nick Moritz/Keys/Dream Plucks", chords="Vospi/Keys/The Softest",
            pad="Databroth/Pads/Warmbo", bass_sound="Basses/Rubber Bass")
HEAVY = {"kick": -15, "snare": -18, "bass": -16, "chords": -20}
PIECES = [
    dict(id="cute1", title="Side street, day (kept: was Cuter 1)", bpm=108, bass="bounce", comp="stab", claps=True, lead="A.Liv/Plucks/Cute 1", chords="A.Liv/Plucks/Cute 2",
         bass_sound="Nick Moritz/Basses/Plastic Dream", about="kept for random day moments: 108 BPM, a bass that hops between octaves, short chords off the beat, claps"),
    dict(id="mc1", title="Side street, night (kept: was Minecraft feeling 1)", bpm=66, drums="none", bass="long", comp="hold", lead="Vospi/Keys/The Softest",
         chords="Bluelight/Pads/Another Warm", pad="Pads/MKS-70 Warm Pad", bass_sound="Basses/Sub 1",
         about="kept for random night moments: 66 BPM, no drums, a soft key over warm pads and a long low bass"),
    dict(id="mossback2", title="Old Mossback (boss, kept; lead tightened)", score="mossback", bpm=160, intro=4, drums="bossfast", bass="riff", comp="stab5", sync=True,
         levels=HEAVY | {"lead": -15, "double": -20}, lead="Leads/Light", double="Leads/Classic Lead 2", double_shift=-12, chords="Polysynths/Anthemish 1",
         bass_sound="Basses/Bass 3", kit={"kick": "TNMG/Drums/Kick - Classic", "snare": "TNMG/Drums/Snare - Classic"},
         about="the version you called amazing, same sounds and arrangement; the lead now repeats one bar three times then closes, in every phrase"),
    dict(id="lantern", title="Third theme A: Lantern fish, as a synth ballad", score="lantern", bpm=90, drums="ballad", bass="lilt", comp="hold", sync=True, lead="Leads/Fluff",
         chords="Polysynths/Oberheim Dreams", pad="Polysynths/Juno-60 Strings", bass_sound="Basses/Bass 3", levels={"chords": -22},
         about="the same tune without the imitation instruments: a soft synth lead, held analog chords, a string-machine pad, drum machine (kick, clap, hats), two slow beats a bar"),
    dict(id="shore", title="Third theme B: Far shore", score="shore", bpm=112, drums="four", bass="drive", comp="stab5", sync=True, lead="Nick Moritz/Keys/Dream Plucks",
         double="Leads/Classic Lead 2", chords="Polysynths/Smooth Stabs", pad="Polysynths/Juno-60 Strings", bass_sound="Basses/Bass 3",
         about="new: 112 BPM, a kick on every beat; one lead bar that never changes while seven chords move under it; pluck lead, a synth lead joining an octave up the second time, analog stabs"),
]


def clashes(score, under):
    """Tune notes a minor ninth (or a semitone) above a note sounding in their chord."""
    return [(int(s), m) for s, ln, m, _ in score["lead"] for v in under[int(s)][0] if (m - midi(v)) % 12 == 1
            and not ("b9" in under[int(s)][1] and v == under[int(s)][0][-1])]                   # (a b9 chord's own ninth over its root is the chord)


def render(piece):
    st = BASE | piece
    score, steps, under = side_street(st)
    bad = clashes(score, under)
    if bad:
        raise SystemExit(f"{piece['title']}: tune notes clash with their chord: {bad}")
    step = 60 / st["bpm"] / 4
    n = int(round(steps * step * SR))

    def when(s):                                       # swing: the second eighth of each beat comes late
        if st["swing"] == 0.5:
            return s * step
        beat, f = divmod(s / 4, 1)
        return (beat + (f * 2 * st["swing"] if f < 0.5 else st["swing"] + (f - 0.5) * 2 * (1 - st["swing"]))) * 4 * step

    sounds = KIT | st.get("kit", {}) | {"lead": st["lead"], "double": st.get("double"), "chords": st["chords"], "pad": st["pad"], "bass": st["bass_sound"]}
    stems = {}
    for part, notes in score.items():
        ev = [(m, vel * (1 + rng.normal(0, 0.04)), max(0.0, when(s) + (0.0 if part in ("kick", "bass") else rng.normal(0.004, 0.005))),
               ln * step * rng.uniform(0.86, 0.97)) for s, ln, m, vel in notes]
        y = surge.play(sounds[part], ev, n / SR + 6.0, st["bpm"] if st.get("sync") else None)
        y = y[:, :n] + np.pad(y[:, n:2 * n], ((0, 0), (0, max(0, 2 * n - y.shape[1]))))[:, :n]
        f = np.fft.rfftfreq(n, 1 / SR)
        y = np.fft.irfft(np.fft.rfft(y, axis=1) / np.sqrt(1 + ((35 if part in ("kick", "bass") else 110) / np.maximum(f, 1e-3)) ** 4), n, axis=1)
        active = np.abs(y).max(axis=0) > 1e-4
        rms = np.sqrt((y[:, active] ** 2).mean()) if active.any() else 0.0
        if rms < 3e-4:
            raise SystemExit(f"{piece['title']}: the {part} ({sounds[part]}) is silent")
        stems[part] = y * 10 ** ((LEVEL | st.get("levels", {}))[part] / 20) / rms
    env = np.zeros(n)
    if "kick" in stems:
        env = np.abs(stems["kick"]).max(axis=0)
        env = np.convolve(env, np.exp(-np.arange(int(0.25 * SR)) / (0.09 * SR)), "full")[:n]
        env = np.clip(env / (np.percentile(env, 99.5) + 1e-9), 0, 1)
    mix = sum(y * (1 - DUCK.get(part, 0) * env) for part, y in stems.items())
    mix *= 10 ** (-17 / 20) / np.sqrt((mix ** 2).mean())
    pk = np.abs(mix).max(axis=0)
    blocks = np.array([pk[max(0, i - 240): i + 288].max() for i in range(0, n, 48)])
    gain = np.interp(np.arange(n), np.arange(0, n, 48), np.minimum(1.0, 0.89 / np.maximum(blocks, 1e-9)))
    mix = np.clip(mix * np.convolve(np.pad(gain, 240, mode="edge"), np.ones(481) / 481, "valid"), -0.95, 0.95)
    with wave.open(str(OUT / f"piece_{piece['id']}.wav"), "wb") as w:
        w.setnchannels(2), w.setsampwidth(2), w.setframerate(SR)
        w.writeframes((mix.T * 32767).astype(np.int16).tobytes())
    print(f"{piece['title']:40s} {n / SR:5.1f} s  peak {np.abs(mix).max():.2f}  parts {sorted(stems)}", flush=True)
    return dict(id=piece["id"], title=piece["title"], bpm=st["bpm"], seconds=round(n / SR, 1), about=piece["about"])


if __name__ == "__main__":
    import sys
    from multiprocessing import get_context
    todo = [p for p in PIECES if not sys.argv[1:] or p["id"] in sys.argv[1:]]
    with get_context("spawn").Pool(4) as pool:                 # one synthesizer per process: four pieces at a time
        done = {d["id"]: d for d in pool.map(render, todo)}
    old = {d["id"]: d for d in json.loads((OUT / "pieces.json").read_text())} if (OUT / "pieces.json").exists() else {}
    (OUT / "pieces.json").write_text(json.dumps([(old | done)[p["id"]] for p in PIECES if p["id"] in old | done], indent=1))
