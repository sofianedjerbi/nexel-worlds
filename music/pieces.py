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


# Old Mossback, the boss: the day's cell (same rhythm, same rise into a long note) in D minor, the relative minor.
# A: the bass walks down under one chord (D, C, B, Bb: a line cliche), then iv, a ii-V, and an augmented dominant.
# B: eight bars of relief in the major (Bb, C, Am, Dm), ending on the dominant. Form A A B A, 32 bars.
VB = {"Dm9": "F3 A3 C4", "Dm9/C": "F3 A3 C4", "Bm7b5": "A3 D4 F4", "Bbmaj7": "A3 D4 F4", "Gm9": "F3 Bb3 D4", "Em7b5": "G3 Bb3 D4 E4", "A7b9": "G3 Bb3 C#4 E4",
      "A7#5": "G3 C#4 F4", "C9": "E3 Bb3 D4", "Am7": "G3 C4 E4"}
RB = {"Dm9": "D3", "Dm9/C": "C3", "Bm7b5": "B2", "Bbmaj7": "Bb2", "Gm9": "G2", "Em7b5": "E2", "A7b9": "A2", "A7#5": "A2", "C9": "C3", "Am7": "A2"}
_A = ["Dm9", "Dm9/C", "Bm7b5", "Bbmaj7", "Gm9", "Em7b5 A7b9", "Dm9", "A7#5"]
_TA = [("cell", "A4 D5 F5 E5"), ("cell", "A4 D5 F5 E5"), ("cell", "A4 D5 F5 D5"), ("cadence", "F5 D5 C5 A4"),
       ("cell", "G4 Bb4 D5 Bb4"), ("cell", "G4 Bb4 E5 C#5"), ("cell", "A4 D5 F5 D5"), ("cadence", "F5 E5 C#5 A4")]
_TB = [("cell", "A4 D5 F5 D5"), ("cell", "G4 Bb4 E5 C5"), ("cell", "G4 C5 E5 C5"), ("cadence", "F5 E5 C5 A4"),
       ("cell", "A4 D5 F5 D5"), ("cell", "G4 Bb4 E5 C5"), ("cell", "G4 Bb4 D5 Bb4"), ("cadence", "E5 C#5 Bb4 A4")]

# Kite weather, a second day and night tune. A major, starting on the IV (D, C#m, Bm, E; then home to A).
# Its own cell: two notes down onto a long one, and a pickup into the next bar (steps 0, 3, 6, 14).
VK = {"Dmaj9": "F#3 A3 C#4 E4", "C#m7": "E3 G#3 B3", "Bm9": "A3 D4 F#4", "E13": "D3 G#3 C#4", "Amaj9": "G#3 B3 C#4 E4"}
RK = {"Dmaj9": "D3", "C#m7": "C#3", "Bm9": "B2", "E13": "E2", "Amaj9": "A2"}
_TK = [("cell", "E5 C#5 A4 B4"), ("cell", "E5 B4 G#4 B4"), ("cell", "D5 A4 F#4 A4"), ("cadence", "B4 G#4 B4"),
       ("cell", "E5 C#5 A4 B4"), ("cell", "E5 B4 G#4 B4"), ("cell", "D5 A4 F#4 G#4"), ("cadence", "B4 C#5 E5")]

SCORES = {
    "street": dict(H=H1, V=V1, R=R1, T=T1),
    "boss": dict(H=_A + _A + ["Bbmaj7", "C9", "Am7", "Dm9", "Bbmaj7", "C9", "Em7b5", "A7b9"] + _A, V=VB, R=RB, T=tune(CELL, CADENCE, _TA + _TA + _TB + _TA)),
    "kite": dict(H=["Dmaj9", "C#m7", "Bm9", "E13", "Dmaj9", "C#m7", "Bm9 E13", "Amaj9"] * 2, V=VK, R=RK,
                 T=tune([(0, 3), (3, 3), (6, 6), (14, 2)], [(0, 3), (3, 3), (6, 10)], _TK * 2)),
}


def side_street(st):
    """The score, in the manner `st` asks for: drums full / light / bossa / brush / none, bass walk / bounce / long,
    comp (the keys) comp / stab / hold; for the boss: drums boss, bass drive, comp stab5. The score is SCORES[st["score"]]."""
    H1, V1, R1, T1 = (SCORES[st.get("score", "street")][k] for k in "HVRT")
    p = {k: [] for k in ("lead", "double", "chords", "pad", "bass", "kick", "snare", "clap", "hat", "open", "shaker", "conga", "click", "brush")}
    roots = [(16 * b + (8 * j if len(bar.split()) == 2 else 0), ch) for b, bar in enumerate(H1) for j, ch in enumerate(bar.split())]
    for b, bar in enumerate(H1):
        s0, chs = 16 * b, bar.split()
        for s, ln, n in T1[b]:
            p["lead"].append((s0 + s, ln, midi(n) + st.get("lead_up", 0), 100 * ACC[s]))
            if st.get("double") and b >= len(H1) // 2:
                p["double"].append((s0 + s, ln, midi(n) + st.get("double_shift", 12), 76 * ACC[s]))               # the second time through, a second sound an octave up
        for j, ch in enumerate(chs):
            at, split = s0 + 8 * j, len(chs) == 2
            hits = {"comp": [(0, 6)] if split else [(0, 5), (10, 4)] if b % 2 == 0 else [(0, 3), (7, 5)],
                    "stab": [(2, 1), (6, 1)] if split else [(2, 1), (6, 1), (10, 1), (14, 1)],
                    "stab5": [(0, 2), (3, 2), (6, 1)] if split else [(0, 2), (3, 2), (6, 2), (10, 1), (12, 2)],
                    "hold": [(0, 8 if split else 16)]}[st["comp"]]
            for i, n in enumerate(V1[ch].split()):
                for s, ln in hits:
                    p["chords"].append((at + s, ln, midi(n), (80 - 3 * i) * ACC[(8 * j + s) % 16]))
                if i >= 1:
                    p["pad"].append((at, 16 // len(chs), midi(n) + 12, 58))
    for k, (at, ch) in enumerate(roots):
        nxt_at, nxt = roots[(k + 1) % len(roots)]
        span = (nxt_at - at) % (16 * len(H1)) or 16
        r = midi(R1[ch])
        if st["bass"] == "long":
            p["bass"].append((at, span - 1, r, 96))
            continue
        if st["bass"] == "drive":                   # eighth notes, the octave on the off-beats
            p["bass"] += [(at + s, 1.6, r + (12 if s % 4 == 2 else 0), 106 if s % 8 == 0 else 90) for s in range(0, span - 2, 2)]
        elif st["bass"] == "bounce":
            p["bass"] += [(at + s, 1.5, r + (12 if s % 8 == 4 else 0), 104 if s == 0 else 88) for s in range(0, span - 2, 4)]
        else:
            p["bass"].append((at, min(5, span - 2), r, 104))
            if span == 16:
                p["bass"] += [(at + 6, 1, r, 78), (at + 8, 4, r + (7 if r < 43 else -5), 92)]
        p["bass"].append((at + span - 2, 2, midi(R1[nxt]) - 1, 86))                 # into the next root from a semitone below
    d = st["drums"]
    for b in range(len(H1)):
        s0, end = 16 * b, b % 8 == 7
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
             for s0 in [16 * b] for s in range(8 * j, 16 if j == len(bar.split()) - 1 else 8)}
    return {k: v for k, v in p.items() if v}, 16 * len(H1), under


LEVEL = {"lead": -15, "double": -22, "chords": -21, "pad": -25, "bass": -18, "kick": -18, "snare": -21, "clap": -25, "hat": -27, "open": -28, "shaker": -31,
         "conga": -22, "click": -27, "brush": -23}
DUCK = {"pad": 0.4, "chords": 0.2, "bass": 0.3}
KIT = dict(kick="Vospi/Drums/Proper Kick", snare="Vospi/Drums/Simple Snare", clap="Emu/Drums/T8 Clap", hat="Emu/Drums/Hat Closed", open="Emu/Drums/Hat Open",
           shaker="Emu/Drums/Egg Shaker", conga="Emu/Drums/T8 Conga", click="Vospi/Drums/Nice Clicks Perc", brush="Malfunction/Drums/Brush")
BASE = dict(bpm=96, swing=0.5, drums="full", bass="walk", comp="comp", lead="Nick Moritz/Keys/Dream Plucks", chords="Vospi/Keys/The Softest",
            pad="Databroth/Pads/Warmbo", bass_sound="Basses/Rubber Bass")
HEAVY = {"kick": -15, "snare": -18, "bass": -16, "chords": -20}
PIECES = [
    dict(id="cute1", title="Side street, day (kept: was Cuter 1)", bpm=108, bass="bounce", comp="stab", claps=True, lead="A.Liv/Plucks/Cute 1", chords="A.Liv/Plucks/Cute 2",
         bass_sound="Nick Moritz/Basses/Plastic Dream", about="kept for random day moments: 108 BPM, a bass that hops between octaves, short chords off the beat, claps"),
    dict(id="mc1", title="Side street, night (kept: was Minecraft feeling 1)", bpm=66, drums="none", bass="long", comp="hold", lead="Vospi/Keys/The Softest",
         chords="Bluelight/Pads/Another Warm", pad="Pads/MKS-70 Warm Pad", bass_sound="Basses/Sub 1",
         about="kept for random night moments: 66 BPM, no drums, a soft key over warm pads and a long low bass"),
    dict(id="boss1", title="Old Mossback 1 (boss)", score="boss", bpm=132, drums="boss", bass="drive", comp="stab5", levels=HEAVY, lead="A.Liv/Plucks/Cute 1",
         chords="A.Liv/Plucks/Cute 2", bass_sound="Nick Moritz/Basses/Plastic Dream",
         about="the day's lead cell turned to D minor, on the day's own sounds: 132 BPM, a bass in driving eighths, kick on 1 and 3, sixteenth hats, a relief in the major in the middle"),
    dict(id="boss2", title="Old Mossback 2 (boss, heavier)", score="boss", bpm=140, drums="boss", bass="drive", comp="stab5", levels=HEAVY, lead="Nick Moritz/Keys/Dream Plucks",
         chords="Polysynths/Jupiter-8", bass_sound="Basses/Bass 1", double="Cybersoda/Brass/Soft 80s Brass", double_shift=-12,
         kit={"kick": "TNMG/Drums/Kick - Classic", "snare": "TNMG/Drums/Snare - Classic"},
         about="the same score at 140 BPM on other sounds: analog chord stabs, a harder kick and snare, a soft brass doubling the tune an octave below from the middle on"),
    dict(id="kite_day", title="Kite weather, day (new tune)", score="kite", bpm=108, bass="bounce", comp="stab", claps=True, lead="A.Liv/Plucks/Cute 1", chords="A.Liv/Plucks/Cute 2",
         bass_sound="Nick Moritz/Basses/Plastic Dream", about="a second day tune in the manner of the kept one: A major, its own lead cell (two notes down onto a long one, a pickup into the next bar)"),
    dict(id="kite_night", title="Kite weather, night (new tune)", score="kite", bpm=66, drums="none", bass="long", comp="hold", lead="Vospi/Keys/The Softest",
         chords="Bluelight/Pads/Another Warm", pad="Pads/MKS-70 Warm Pad", bass_sound="Basses/Sub 1", about="the same new tune in the manner of the kept night piece: slow, no drums, pads"),
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
        beat, f = divmod(s / 4, 1)
        return (beat + (f * 2 * st["swing"] if f < 0.5 else st["swing"] + (f - 0.5) * 2 * (1 - st["swing"]))) * 4 * step

    sounds = KIT | st.get("kit", {}) | {"lead": st["lead"], "double": st.get("double"), "chords": st["chords"], "pad": st["pad"], "bass": st["bass_sound"]}
    stems = {}
    for part, notes in score.items():
        ev = [(m, vel * (1 + rng.normal(0, 0.04)), max(0.0, when(s) + (0.0 if part in ("kick", "bass") else rng.normal(0.004, 0.005))),
               ln * step * rng.uniform(0.86, 0.97)) for s, ln, m, vel in notes]
        y = surge.play(sounds[part], ev, n / SR + 6.0)
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
