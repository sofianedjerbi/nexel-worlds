"""One piece in the direction the user found "better" (the bright plucks of directions.py), designed properly this
time, and rendered on three palettes of Surge XT sounds so that the sound and the writing can be judged apart.

What is designed (from research on programmed music that does not sound programmed, see PROCESS.md):
  form       intro (4 bars, no kick) / A (8) / B (8, new chords, higher tune, busier drums) / A again (4), then loops
  rhythm     the 3+3+2 bounce of the pluck, a kick that leaves beat 3 alone, claps, a shaker; fills into each section
  touch      every part has accents by position in the bar, small changes of length and timing; nothing at one velocity
  answer     the tune's phrase is answered by a second sound in the gaps (bars 4 and 8 of A)
  bass       an octave higher than before (82 to 130 Hz): it was inaudible on small speakers
  mix        the pad, chords and bass duck a little under each kick (sidechain), the top is left in

    uv run --no-project --python 3.11 --with dawdreamer --with numpy python music/bright.py
"""
from pathlib import Path
import json
import wave

import numpy as np

import surge
from directions import midi

SR = surge.SR
OUT = Path(__file__).with_name("site") / "audio"
BPM, BARS = 104, 24
STEP = 60 / BPM / 4
rng = np.random.default_rng(11)

V = {"G": ["G3", "B3", "D4"], "D/F#": ["F#3", "A3", "D4"], "Em7": ["G3", "B3", "D4", "E4"], "Cmaj7": ["G3", "B3", "C4", "E4"], "C": ["G3", "C4", "E4"],
     "D": ["F#3", "A3", "D4"], "Dsus": ["G3", "A3", "D4"], "Bm7": ["F#3", "A3", "B3", "D4"]}
ROOT = {"G": "G2", "D/F#": "F#2", "Em7": "E2", "Cmaj7": "C3", "C": "C3", "D": "D3", "Dsus": "D3", "Bm7": "B2"}
A = ["G", "D/F#", "Em7", "Cmaj7", "G", "D/F#", "Em7", "Dsus"]
B = ["C", "D", "Bm7", "Em7", "C", "D", "G", "Dsus"]
HARMONY = A[:4] + A + B + A[:3] + ["Dsus"]                    # 24 bars
SECTION = ["intro"] * 4 + ["A"] * 8 + ["B"] * 8 + ["A2"] * 4

MOTIF = [[(0, 2, "B4"), (3, 2, "D5"), (6, 2, "B4"), (10, 2, "G4"), (12, 4, "D5")], [(0, 2, "A4"), (3, 2, "D5"), (6, 2, "A4"), (10, 2, "F#4"), (12, 4, "D5")],
         [(0, 2, "G4"), (3, 2, "B4"), (6, 2, "G4"), (10, 2, "E4"), (12, 4, "B4")], [(0, 2, "G4"), (3, 2, "C5"), (6, 2, "E5"), (10, 5, "D5")]]
MOTIF2 = MOTIF[:3] + [[(0, 2, "A4"), (3, 2, "D5"), (6, 6, "A4")]]                                      # the second time it ends early: room for the answer
ANSWER = {3: [(12, 2, "E5"), (14, 2, "G5")], 7: [(10, 2, "D5"), (12, 2, "E5"), (14, 2, "F#5")]}         # bar of A: the other sound replies
TUNE_B = [[(0, 3, "E5"), (3, 3, "G5"), (6, 6, "E5"), (12, 4, "C5")], [(0, 3, "D5"), (3, 3, "F#5"), (6, 6, "D5"), (12, 4, "A4")],
          [(0, 3, "D5"), (3, 3, "F#5"), (6, 4, "B4"), (10, 6, "D5")], [(0, 6, "E5"), (6, 4, "D5"), (10, 6, "B4")],
          [(0, 3, "E5"), (3, 3, "G5"), (6, 6, "E5"), (12, 4, "C5")], [(0, 3, "D5"), (3, 3, "F#5"), (6, 4, "A5"), (10, 6, "F#5")],
          [(0, 6, "G5"), (6, 4, "D5"), (10, 6, "B4")], [(0, 8, "A4"), (8, 4, "D5"), (12, 4, "F#5")]]
ACCENT = [1.0, 0.7, 0.8, 0.72, 0.9, 0.7, 0.82, 0.72, 0.95, 0.7, 0.8, 0.72, 0.9, 0.7, 0.84, 0.76]       # how hard a step is played, by its place in the bar


def score():
    """{part: [(step, steps long, midi note, velocity)]}"""
    p = {k: [] for k in ("lead", "answer", "chords", "pad", "bass", "kick", "snare", "clap", "hat", "open", "shaker")}
    for bar, (ch, sec) in enumerate(zip(HARMONY, SECTION)):
        s0, k = 16 * bar, bar - {"intro": 0, "A": 4, "B": 12, "A2": 20}[sec]
        tune = MOTIF[k] if sec in ("intro", "A2") else (MOTIF + MOTIF2)[k] if sec == "A" else TUNE_B[k]
        for s, ln, n in tune:
            p["lead"].append((s0 + s, ln, midi(n), (78 if sec == "intro" else 100) * ACCENT[s]))
        if sec == "A":
            for s, ln, n in ANSWER.get(k, []):
                p["answer"].append((s0 + s, ln, midi(n), 92 * ACCENT[s]))
        for j, n in enumerate(V[ch]):
            p["pad"].append((s0, 16, midi(n) + (12 if j else 0), 62))
            for s in ((2, 8, 14) if sec != "B" else (0, 3, 6, 10, 13)) if sec != "intro" else ():
                p["chords"].append((s0 + s, 2, midi(n), (84 - 4 * j) * ACCENT[s]))
        r = midi(ROOT[ch])
        if sec in ("A", "A2"):
            p["bass"] += [(s0, 3, r, 104), (s0 + 6, 2, r, 88), (s0 + 10, 2, r, 92), (s0 + 13, 2, r + 12, 84)]
        if sec == "B":
            p["bass"] += [(s0 + s, 1.7, r + (12 if s == 14 else 7 if s == 6 else 0), 100 * ACCENT[s]) for s in range(0, 16, 2)]
        if sec == "intro":
            p["shaker"] += [(s0 + s, 1, 60, 70 * ACCENT[s]) for s in range(16)] if bar >= 2 else []
            p["snare"] += [(s0 + 13, 1, 60, 70), (s0 + 14, 1, 60, 86), (s0 + 15, 1, 60, 104)] if bar == 3 else []       # fill into A
            continue
        last = bar in (11, 19, 23)                                                                                   # the bar before a new section
        for s in ((0, 6, 9) if sec != "B" else (0, 3, 6, 10, 13)):
            p["kick"].append((s0 + s, 1, 48, 112 if s == 0 else 96))
        p["snare"] += [(s0 + 4, 1, 60, 104), (s0 + 12, 1, 60, 108)] + ([(s0 + 14, 1, 60, 80), (s0 + 15, 1, 60, 96)] if last else [])
        p["clap"] += [(s0 + 4, 1, 60, 90), (s0 + 12, 1, 60, 96)] if sec == "B" else []
        for s in ((2, 6, 10, 12, 14) if sec != "B" else range(0, 16, 2)):
            if sec == "B" and s == 14:
                p["open"].append((s0 + s, 2, 60, 84))
            else:
                p["hat"].append((s0 + s, 1, 60, 92 * ACCENT[s]))
        p["shaker"] += [(s0 + s, 1, 60, 62 * ACCENT[s]) for s in range(16)]
    return p


LEVEL = {"lead": -15, "answer": -18, "chords": -22, "pad": -24, "bass": -18, "kick": -17, "snare": -20, "clap": -24, "hat": -27, "open": -28, "shaker": -31}
DUCK = {"pad": 0.4, "chords": 0.25, "bass": 0.3}                     # how far a part dips under each kick
PALETTES = [
    dict(id="dream", title="Bright A: Dream", lead="Nick Moritz/Keys/Dream Plucks", answer="Vospi/Keys/The Softest", chords="Plucks/Nice Pluck 1",
         pad="Databroth/Pads/Warmbo", bass="Basses/Rubber Bass", kick="Vospi/Drums/Proper Kick", snare="Vospi/Drums/Simple Snare", clap="Emu/Drums/T8 Clap",
         hat="Emu/Drums/Hat Closed", open="Emu/Drums/Hat Open", shaker="Emu/Drums/Egg Shaker"),
    dict(id="cute", title="Bright B: Cute", lead="A.Liv/Plucks/Cute 1", answer="Rozzer/Keys/Cute", chords="A.Liv/Plucks/Cute 2",
         pad="Bluelight/Pads/Rainy Day Dreamaway", bass="Nick Moritz/Basses/Plastic Dream", kick="Emu/Drums/T8 Kick 1", snare="Emu/Drums/T8 Snare", clap="Emu/Drums/T8 Clap",
         hat="Emu/Drums/Hat", open="Emu/Drums/Hat Open", shaker="Emu/Drums/Egg Shaker"),
    dict(id="sweets", title="Bright C: Sweets", lead="Kyurumi/Plucks/Dreams And Sweets", answer="Vospi/Keys/EP Forest", chords="Vospi/Plucks/Come Closer",
         pad="Bluelight/Pads/Wool 1", bass="Basses/Fingered", kick="Cybersoda/Drums/Acoustic Kick", snare="Cybersoda/Drums/Acoustic Snare", clap="Emu/Drums/T8 Clap",
         hat="Cybersoda/Drums/Acoustic HiHat", open="Emu/Drums/Hat Open", shaker="Emu/Drums/Egg Shaker"),
]


def render(pal):
    n = int(round(BARS * 16 * STEP * SR))
    stems, raw = {}, {}
    for part, notes in score().items():
        ev = []
        for s, ln, m, vel in notes:
            loose = 0.0 if part in ("kick", "bass") else rng.normal(0.004, 0.005)                 # a few ms late, never the same
            ev.append((m, vel * (1 + rng.normal(0, 0.04)), max(0.0, s * STEP + loose), ln * STEP * rng.uniform(0.86, 0.97)))
        y = surge.play(pal[part], ev, n / SR + 6.0)
        y = y[:, :n] + np.pad(y[:, n:2 * n], ((0, 0), (0, max(0, 2 * n - y.shape[1]))))[:, :n]      # the tail comes back at the start: a loop
        f = np.fft.rfftfreq(n, 1 / SR)
        y = np.fft.irfft(np.fft.rfft(y, axis=1) / np.sqrt(1 + ((35 if part in ("kick", "bass") else 110) / np.maximum(f, 1e-3)) ** 4), n, axis=1)
        active = np.abs(y).max(axis=0) > 1e-4
        rms = np.sqrt((y[:, active] ** 2).mean()) if active.any() else 0.0
        raw[part] = round(float(20 * np.log10(rms + 1e-12)), 1)
        if rms < 3e-4:
            raise SystemExit(f"{pal['title']}: {pal[part]} is silent as the {part}")
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
    with wave.open(str(OUT / f"bright_{pal['id']}.wav"), "wb") as w:
        w.setnchannels(2), w.setsampwidth(2), w.setframerate(SR)
        w.writeframes((mix.T * 32767).astype(np.int16).tobytes())
    S, fr = np.abs(np.fft.rfft(mix.mean(axis=0))) ** 2, np.fft.rfftfreq(n, 1 / SR)
    share = {k: round(float(10 * np.log10(S[(fr >= lo) & (fr < hi)].sum() / S.sum() + 1e-12)), 1) for k, lo, hi in
             (("under 60", 0, 60), ("60-250", 60, 250), ("250-1k", 250, 1000), ("1-4k", 1000, 4000), ("over 4k", 4000, 24000))}
    print(f"{pal['title']:18s} {n / SR:5.1f} s  peak {np.abs(mix).max():.2f}  {share}\n   raw {raw}", flush=True)
    return dict(id=pal["id"], title=pal["title"], bpm=BPM, seconds=round(n / SR, 1),
                sounds=", ".join(f"{k}: {pal[k].split('/')[-1]}" for k in ("lead", "answer", "chords", "pad", "bass")))


if __name__ == "__main__":
    import sys
    done = {d["id"]: d for d in (render(p) for p in PALETTES if not sys.argv[1:] or p["id"] in sys.argv[1:])}   # (names: those alone, music/renders.py)
    old = {d["id"]: d for d in json.loads((OUT / "bright.json").read_text())} if (OUT / "bright.json").exists() else {}
    (OUT / "bright.json").write_text(json.dumps([(old | done)[p["id"]] for p in PALETTES if p["id"] in old | done], indent=1))
