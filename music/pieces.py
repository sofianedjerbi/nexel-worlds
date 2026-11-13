"""Two pieces written to answer "it still sounds too naive, too.. generic" (the user, on bright.py).
bright.py used the four chords of a thousand songs (G, D, Em, C), a pentatonic tune landing on chord notes, and the
same bar shape eight times. Here the writing is the subject; the sounds are the palette they found "a bit better".

  Side street   4/4, 96 BPM, F major. Jazz harmony as Animal Crossing and city pop use it: ninths and thirteenths,
                a ii-V into every new chord, the minor iv (Bbm6), rootless voicings that move by step. The tune uses
                the chromatic notes those chords bring (C#, Eb, Db, F#), starts off the beat, and no two bars of a
                phrase have the same shape. The bass approaches each new root from a semitone below.
  Paper boats   3/4, 132 BPM, D major. A waltz: the Lydian chord (E over D), dominants borrowed from other keys
                (F#7, B7), the minor iv (Gm6). Long tune notes on the colour notes of each chord (G#, A#, D#).

A check refuses any tune note a minor ninth above a note of its chord (the "wrong notes" of the first weeks).

    uv run --no-project --python 3.11 --with dawdreamer --with numpy python music/pieces.py
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


def side_street():
    p = {k: [] for k in ("lead", "chords", "pad", "bass", "kick", "snare", "hat", "open", "shaker")}
    roots = [(16 * b + (8 * j if len(bar.split()) == 2 else 0), ch) for b, bar in enumerate(H1) for j, ch in enumerate(bar.split())]
    for b, bar in enumerate(H1):
        s0, chs = 16 * b, bar.split()
        for s, ln, n in T1[b]:
            p["lead"].append((s0 + s, ln, midi(n), 100 * ACC[s]))
        for j, ch in enumerate(chs):
            at = s0 + 8 * j
            hits = [(0, 6)] if len(chs) == 2 else [(0, 5), (10, 4)] if b % 2 == 0 else [(0, 3), (7, 5)]      # the comping changes from bar to bar
            for i, n in enumerate(V1[ch].split()):
                for s, ln in hits:
                    p["chords"].append((at + s, ln, midi(n), (80 - 3 * i) * ACC[(8 * j + s) % 16]))
                if i >= 2:
                    p["pad"].append((at, 16 // len(chs), midi(n) + 12, 58))
    for k, (at, ch) in enumerate(roots):
        nxt_at, nxt = roots[(k + 1) % len(roots)]
        span = (nxt_at - at) % (16 * len(H1)) or 16
        r = midi(R1[ch])
        p["bass"].append((at, min(5, span - 2), r, 104))
        if span == 16:
            p["bass"] += [(at + 6, 1, r, 78), (at + 8, 4, r + (7 if r < 43 else -5), 92)]
        p["bass"].append((at + span - 2, 2, midi(R1[nxt]) - 1, 86))                 # into the next root from a semitone below
    for b in range(len(H1)):
        s0, end = 16 * b, b in (7, 15)
        p["kick"] += [(s0, 1, 48, 110), (s0 + 7, 1, 48, 88), (s0 + 10, 1, 48, 98)]
        p["snare"] += [(s0 + 4, 1, 60, 96), (s0 + 12, 1, 60, 102)] + ([(s0 + 13, 1, 60, 70), (s0 + 15, 1, 60, 92)] if end else [])
        p["hat"] += [(s0 + s, 1, 60, 90 * ACC[s]) for s in range(0, 16, 2) if not (b % 4 == 3 and s == 14)]
        p["open"] += [(s0 + 14, 2, 60, 80)] if b % 4 == 3 else []
        p["shaker"] += [(s0 + s, 1, 60, 60 * ACC[s]) for s in range(16)]
    return p, 96, 16 * len(H1), {s0 + s: (V1[ch].split() + [R1[ch]], ch) for b, bar in enumerate(H1) for j, ch in enumerate(bar.split())
                                 for s0 in [16 * b] for s in range(8 * j, 16 if j == len(bar.split()) - 1 else 8)}


# ---------------------------------------------------------------- Paper boats (3/4: 12 steps a bar)
V2 = {"Dmaj9": "F#3 A3 C#4 E4", "E/D": "E3 G#3 B3 E4", "C#m7": "E3 G#3 B3 C#4", "F#7": "E3 A#3 C#4", "Bm7": "D3 F#3 A3 B3", "Bm7/A": "D3 F#3 A3 B3",
      "Gmaj7": "D3 F#3 G3 B3", "Gm6": "D3 E3 G3 Bb3", "F#m7": "E3 F#3 A3 C#4", "B7": "D#3 F#3 A3 B3", "Em9": "D3 F#3 G3 B3", "A13": "C#3 F#3 G3 B3",
      "D69": "F#3 A3 B3 E4", "A7sus": "D3 E3 G3 A3"}
R2 = {"Dmaj9": "D2", "E/D": "D2", "C#m7": "C#3", "F#7": "F#2", "Bm7": "B2", "Bm7/A": "A2", "Gmaj7": "G2", "Gm6": "G2", "F#m7": "F#2", "B7": "B2",
      "Em9": "E2", "A13": "A2", "D69": "D2", "A7sus": "A2"}
H2 = ["Dmaj9", "Dmaj9", "E/D", "E/D", "C#m7", "F#7", "Bm7", "Bm7/A", "Gmaj7", "Gm6", "F#m7", "B7", "Em9", "A13", "D69", "A7sus"]
H2 = H2 + H2[:12] + ["Em9", "A13", "D69", "D69"]
T2 = [[(0, 8, "F#5"), (8, 4, "E5")], [(0, 8, "C#5"), (8, 4, "A4")], [(0, 8, "G#4"), (8, 4, "B4")], [(0, 8, "E5"), (8, 2, "C#5"), (10, 2, "D5")],
      [(0, 8, "E5"), (8, 4, "C#5")], [(0, 8, "A#4"), (8, 4, "C#5")], [(0, 8, "D5"), (8, 4, "C#5")], [(0, 8, "B4"), (8, 2, "A4"), (10, 2, "B4")],
      [(0, 8, "F#5"), (8, 4, "D5")], [(0, 8, "E5"), (8, 4, "D5")], [(0, 8, "C#5"), (8, 4, "A4")], [(0, 8, "D#5"), (8, 4, "F#5")],
      [(0, 8, "B4"), (8, 4, "D5")], [(0, 8, "E5"), (8, 4, "C#5")], [(0, 8, "D5"), (8, 4, "E5")], [(0, 8, "E5"), (8, 4, "A4")]]
T2 = T2 + T2[:14] + [[(0, 12, "D5")], [(4, 4, "E5"), (8, 4, "A4")]]


def paper_boats():
    p = {k: [] for k in ("lead", "answer", "chords", "pad", "bass", "kick", "snare", "hat", "shaker")}
    for b, ch in enumerate(H2):
        s0, again = 12 * b, b >= 16
        for s, ln, n in T2[b]:
            p["lead"].append((s0 + s, ln, midi(n), 96 if s == 0 else 82))
            if again and ln >= 4:
                p["answer"].append((s0 + s, 2, midi(n) + 12, 74))                    # the second time, a pluck doubles the tune an octave up
        for i, n in enumerate(V2[ch].split()):
            p["chords"].append((s0 + (4 if b % 4 != 3 else 3), 7, midi(n), 76 - 3 * i))        # the chord comes on beat 2 and is held; early before a new phrase
            if i >= 2:
                p["pad"].append((s0, 12, midi(n) + 12, 56))
        r, nxt = midi(R2[ch]), midi(R2[H2[(b + 1) % len(H2)]])
        p["bass"].append((s0, 9, r, 100))
        if nxt != r:
            p["bass"].append((s0 + 10, 2, nxt - 1 if nxt > r else nxt + 1, 80))      # into the next root by a semitone
        p["kick"].append((s0, 1, 48, 100))
        p["hat"] += [(s0 + 4, 1, 60, 80), (s0 + 8, 1, 60, 88)] + ([(s0 + 10, 1, 60, 64)] if b % 2 else [])
        p["snare"] += [(s0 + 8, 1, 60, 78)] if again and b % 2 else []
        p["shaker"] += [(s0 + s, 1, 60, 56 if s % 4 else 70) for s in range(0, 12, 2)] if again else []
    return p, 132, 12 * len(H2), {12 * b + s: (V2[ch].split() + [R2[ch]], ch) for b, ch in enumerate(H2) for s in range(12)}


LEVEL = {"lead": -15, "answer": -21, "chords": -21, "pad": -25, "bass": -18, "kick": -18, "snare": -21, "hat": -27, "open": -28, "shaker": -31}
DUCK = {"pad": 0.4, "chords": 0.2, "bass": 0.3}
SOUNDS = dict(chords="Vospi/Keys/The Softest", pad="Databroth/Pads/Warmbo", bass="Basses/Rubber Bass", kick="Vospi/Drums/Proper Kick", snare="Vospi/Drums/Simple Snare",
              hat="Emu/Drums/Hat Closed", open="Emu/Drums/Hat Open", shaker="Emu/Drums/Egg Shaker")
PIECES = [dict(id="street", title="Side street", write=side_street, lead="Nick Moritz/Keys/Dream Plucks",
               about="4/4 · F major · the lead is one small cell, the same rhythm and shape in every bar, moved to fit each chord; jazz chords underneath; a bass that walks into each chord")]


def clashes(score, under):
    """Tune notes a minor ninth (or a semitone) above a note sounding in their chord."""
    return [(int(s), m) for s, ln, m, _ in score["lead"] for v in under[int(s)][0] if (m - midi(v)) % 12 == 1
            and not ("b9" in under[int(s)][1] and v == under[int(s)][0][-1])]                   # (a b9 chord's own ninth over its root is the chord)


def render(piece):
    score, bpm, steps, under = piece["write"]()
    bad = clashes(score, under)
    if bad:
        raise SystemExit(f"{piece['title']}: tune notes clash with their chord: {bad}")
    step = 60 / bpm / 4
    n = int(round(steps * step * SR))
    stems = {}
    for part, notes in score.items():
        if not notes:
            continue
        ev = [(m, vel * (1 + rng.normal(0, 0.04)), max(0.0, s * step + (0.0 if part in ("kick", "bass") else rng.normal(0.004, 0.005))),
               ln * step * rng.uniform(0.86, 0.97)) for s, ln, m, vel in notes]
        y = surge.play(piece.get(part) or SOUNDS[part], ev, n / SR + 6.0)
        y = y[:, :n] + np.pad(y[:, n:2 * n], ((0, 0), (0, max(0, 2 * n - y.shape[1]))))[:, :n]
        f = np.fft.rfftfreq(n, 1 / SR)
        y = np.fft.irfft(np.fft.rfft(y, axis=1) / np.sqrt(1 + ((35 if part in ("kick", "bass") else 110) / np.maximum(f, 1e-3)) ** 4), n, axis=1)
        active = np.abs(y).max(axis=0) > 1e-4
        rms = np.sqrt((y[:, active] ** 2).mean()) if active.any() else 0.0
        if rms < 3e-4:
            raise SystemExit(f"{piece['title']}: the {part} is silent")
        stems[part] = y * 10 ** (LEVEL[part] / 20) / rms
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
    print(f"{piece['title']:12s} {n / SR:5.1f} s  peak {np.abs(mix).max():.2f}  parts {sorted(stems)}", flush=True)
    return dict(id=piece["id"], title=piece["title"], bpm=bpm, seconds=round(n / SR, 1), about=piece["about"])


if __name__ == "__main__":
    for p in PIECES:                       # the writing is checked before anything is rendered
        sc, _, _, under = p["write"]()
        print(p["title"], "clashes:", clashes(sc, under))
    (OUT / "pieces.json").write_text(json.dumps([render(p) for p in PIECES], indent=1))
