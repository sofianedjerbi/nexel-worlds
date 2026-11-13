"""Other music for the day: four suggestions, each its own tune, in Meadow Road's sound (nylon guitar, bouncing bass,
off-beat electric piano, shaker, a far whistle), dry.

    uv run python music/day.py        ->  music/site/audio/day_<id>.wav and .json, days.json

The same rules as compose.py, checked here for every piece: chords are struck together (no arpeggios); the melody never
takes two steps in a row in the same direction; every melody note on a beat is a chord note; nothing sounds a semitone
or a minor ninth under the melody (a major seventh that belongs to the chord is fine). Each tune is one two-bar idea: said, answered, said again, closed on a cadence.
"""
import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

import compose as C
from compose import MAIN, SR, analog_pad, epiano, glide_lead, hp, lp, midi, moog_bass, shaker, tt

OUT = Path(__file__).with_name("site") / "audio"
TAIL = 6 * SR
QUAL = {"maj7": (0, 4, 7, 11), "m7": (0, 3, 7, 10), "7sus": (0, 5, 7, 10), "7": (0, 4, 7, 10), "6": (0, 4, 7, 9), "m": (0, 3, 7), "": (0, 4, 7)}
# who plays, block by block (8 bars each): the melody (g: guitar, w: whistle, gw: both, -: nobody), the band
# (0: pad and held chords, 1: bass and electric piano, 2: with the shaker)
FORM = [("the tune", "g", 1), ("with the shaker", "g", 2), ("the band alone", "-", 2), ("a far whistle", "w", 2),
        ("together", "gw", 2), ("open air", "-", 0)]

PIECES = [
    dict(id="market", title="Market Morning", key="G major", bpm=96, swing=0.6, mood="bouncy, on its toes",
         cycle=["Gmaj7", "Em7", "Cmaj7", "D7", "Gmaj7", "Em7", "Am7 D7", "G6"],
         melody=[[(0, 1, "D5"), (1, 1, "B4"), (3, 2, "D5"), (6, 2, "B4")], [(0, 4, "G4")],
                 [(0, 1, "E5"), (1, 1, "C5"), (3, 2, "E5"), (6, 2, "C5")], [(0, 4, "A4")],
                 [(0, 1, "D5"), (1, 1, "B4"), (3, 2, "D5"), (6, 2, "B4")], [(0, 4, "G4")],
                 [(0, 1, "E5"), (1, 1, "C5"), (3, 2, "D5"), (6, 2, "F#4")], [(0, 6, "G4")]]),
    dict(id="afternoon", title="Slow Afternoon", key="F major", bpm=72, swing=0.6, mood="lazy, long notes, waits for beat two",
         cycle=["Fmaj7", "Dm7", "Bbmaj7", "C7sus", "Fmaj7", "Am7", "Gm7 C7", "F6"],
         melody=[[(2, 1, "E5"), (3, 3, "C5"), (6, 2, "A4")], [(0, 5, "D5")],
                 [(2, 1, "D5"), (3, 3, "Bb4"), (6, 2, "F4")], [(0, 5, "G4")],
                 [(2, 1, "E5"), (3, 3, "C5"), (6, 2, "A4")], [(0, 5, "E5")],
                 [(2, 1, "D5"), (3, 2, "Bb4"), (6, 2, "C5")], [(0, 6, "A4")]]),
    dict(id="overcast", title="Overcast", key="A minor, closing in C major", bpm=80, swing=0.56, mood="bittersweet, a repeated note",
         cycle=["Am7", "Fmaj7", "Cmaj7", "G", "Am7", "Fmaj7", "Dm7 G7", "C6"],
         melody=[[(0, 1, "E5"), (1, 1, "E5"), (2, 2, "C5"), (5, 3, "E5")], [(0, 4, "A4")],
                 [(0, 1, "E5"), (1, 1, "E5"), (2, 2, "C5"), (5, 3, "G4")], [(0, 4, "B4")],
                 [(0, 1, "E5"), (1, 1, "E5"), (2, 2, "C5"), (5, 3, "E5")], [(0, 4, "A4")],
                 [(0, 1, "D5"), (1, 1, "D5"), (2, 3, "F5"), (6, 2, "B4")], [(0, 6, "C5")]]),
    dict(id="picnic", title="Picnic", key="A major", bpm=108, swing=0.62, mood="brisk and playful, call and answer",
         cycle=["Amaj7", "F#m7", "Dmaj7", "E7", "Amaj7", "F#m7", "Bm7 E7", "A6"],
         melody=[[(0, 1, "E5"), (1, 1, "C#5"), (2, 2, "E5"), (5, 3, "A4")], [(1, 1, "B4"), (2, 2, "A4"), (4, 3, "F#4")],
                 [(0, 1, "D5"), (1, 1, "A4"), (2, 2, "D5"), (5, 3, "F#4")], [(1, 1, "F#4"), (2, 2, "G#4"), (4, 3, "E4")],
                 [(0, 1, "E5"), (1, 1, "C#5"), (2, 2, "E5"), (5, 3, "A4")], [(1, 1, "B4"), (2, 2, "A4"), (4, 3, "F#4")],
                 [(0, 1, "D5"), (1, 1, "B4"), (2, 2, "D5"), (5, 1, "G#4"), (6, 2, "B4")], [(0, 6, "A4")]]),
]


def tones(ch):
    """Pitch classes of a chord name, root first."""
    root = ch[:2] if len(ch) > 1 and ch[1] in "#b" else ch[:1]
    return [(midi(root + "4") + k) % 12 for k in QUAL[ch[len(root):]]]


def spans(piece, i):
    """The chords of bar i: (first eighth, eighths long, chord)."""
    names = piece["cycle"][i].split()
    return [(k * 8 // len(names), 8 // len(names), ch) for k, ch in enumerate(names)]


def chord_at(piece, i, slot):
    return [ch for at, ln, ch in spans(piece, i) if at <= slot][-1]


def over(piece, i, at, ln):
    """Melody pitch classes sounding during these eighths of bar i (a note held from the bar before counts)."""
    out = set()
    for b, shift in ((i, 0), ((i - 1) % 8, -8)):
        out |= {midi(n) % 12 for s, l, n in piece["melody"][b] if s + shift < at + ln and s + shift + l > at}
    return out


def hand(piece, i, at, ln, ch):
    """The chord without its root, around E3..D#4, and without any note a semitone (a minor ninth) under the melody."""
    mel = over(piece, i, at, ln)
    return [52 + (pc - 52) % 12 for pc in tones(ch)[1:] if not any((m - pc) % 12 == 1 for m in mel)]


def checks(piece):
    bad, line = [], [midi(n) for bar in piece["melody"] for _, _, n in bar]
    for i, bar in enumerate(piece["melody"]):
        for s, l, n in bar:
            if s % 2 == 0 and midi(n) % 12 not in tones(chord_at(piece, i, s)):
                bad.append(f"bar {i + 1}: {n} on a beat is not in {chord_at(piece, i, s)}")
        for at, ln, ch in spans(piece, i):
            if any((m - pc) % 12 == 1 for m in over(piece, i, at, ln) for pc in tones(ch)[:3]):
                bad.append(f"bar {i + 1}: the melody is a semitone from the root, third or fifth of {ch}")
    line += line[:2]
    for a, b, c in zip(line, line[1:], line[2:]):
        if 0 < abs(b - a) <= 2 and 0 < abs(c - b) <= 2 and (b - a) * (c - b) > 0:
            bad.append(f"two steps the same way: {a} {b} {c}")
    return bad


def render(piece):
    rng = np.random.default_rng(len(piece["id"]) * 7 + piece["bpm"])
    bars = 8 * len(FORM)
    loop_n = C.fast_len(int(round(bars * 4 * 60 / piece["bpm"] * SR)))
    beat = loop_n / SR / (bars * 4)
    t_of = lambda slot: (slot // 2 + (piece["swing"] if slot % 2 >= 1 else 0.0) + (slot % 1) * 0.5) * beat
    n = loop_n + TAIL
    dry, rev = np.zeros((2, n)), np.zeros((2, n))

    def note(slot, ln, m, vel, inst, gain=1.0, pan=0.0, send=0.25, human=True):
        t0, dur = t_of(slot), ln * beat / 2
        if human:
            t0, vel = t0 + abs(rng.normal(0, 0.008)), vel * (1 + rng.normal(0, 0.06))
        y = np.atleast_2d(inst(C.hz(m), dur, vel, t0)) * gain
        y = np.vstack([y, y])[:2]
        k = int(round(t0 * SR))
        y = y[:, : n - k]
        a = (pan + 1) * np.pi / 4
        y = y * np.array([[np.cos(a)], [np.sin(a)]]) * np.sqrt(2)
        dry[:, k:k + y.shape[1]] += y
        rev[:, k:k + y.shape[1]] += send * y

    for b, (_, who, band) in enumerate(FORM):
        for i in range(8):
            s0 = (b * 8 + i) * 8
            for j, (s, ln, nm) in enumerate(piece["melody"][i]):
                touch = 1.0 if j == 0 or ln >= 3 else 0.82
                if "g" in who:
                    note(s0 + s, ln, midi(nm), 0.66 * touch, MAIN, pan=0.1, send=0.3)
                if "w" in who:
                    note(s0 + s, ln, midi(nm), (0.5 if "g" in who else 0.8) * touch, glide_lead, gain=0.6, pan=-0.15, send=0.4)
            for at, ln, ch in spans(piece, i):
                root, notes = 33 + (tones(ch)[0] - 33) % 12, hand(piece, i, at, ln, ch)
                for j, m in enumerate(notes):
                    if not band:                                   # open air: the chord on the guitar, held
                        note(s0 + at, ln, m, 0.4 - 0.03 * j, MAIN, pan=-0.3 + 0.3 * j, send=0.35)
                    else:                                          # the electric piano: together, short, off the beat
                        for off, v in ((2, 0.8), (5, 0.62)) if ln == 8 else ((1, 0.75),):
                            note(s0 + at + off, 1, m, v * (0.9 if who != "-" else 1.0), epiano, pan=-0.35 + 0.35 * j)
                for pc in tones(ch)[:3]:
                    note(s0 + at, ln, 50 + (pc - 50) % 12, 0.8 if not band else 0.35, analog_pad, gain=0.9, send=0.4, human=False)
                if band:                                           # the bass bounces: root, root, fifth
                    note(s0 + at, 1.6, root, 0.85, moog_bass, gain=0.55, send=0.05, human=False)
                    if ln == 8:
                        note(s0 + 3, 0.8, root, 0.5, moog_bass, gain=0.55, send=0.05, human=False)
                        note(s0 + 4, 1.6, root + 7, 0.72, moog_bass, gain=0.55, send=0.05, human=False)
            for k in range(8) if band == 2 else ():
                note(s0 + k, 1, 60, 0.9 if k in (2, 6) else 0.42 if k % 2 else 0.6, shaker, pan=0.3, send=0.15)

    fold = lambda x: x[:, :loop_n] + np.pad(x[:, loop_n:], ((0, 0), (0, loop_n - TAIL)))     # the tail comes back at the start
    dry, rev = fold(dry), fold(rev)
    f, t = np.fft.rfftfreq(loop_n, 1 / SR), tt(2 * SR)
    wet = []
    for c in range(2):                                             # the same small dry room as Meadow Road
        ir = rng.standard_normal(len(t)) * np.exp(-t / 0.25) * np.clip(t / 0.03, 0, 1)
        ir = np.pad(ir / np.sqrt(np.sum(ir ** 2)), (0, loop_n - len(ir)))
        wet.append(np.fft.irfft(np.fft.rfft(rev[c]) * np.fft.rfft(ir) * lp(5000, 1)(f) * hp(200, 1)(f), loop_n))
    mix = np.fft.irfft(np.fft.rfft(dry + 0.22 * np.stack(wet), axis=-1) * hp(30, 2)(f) * lp(15000, 2)(f), loop_n, axis=-1)
    mix *= 10 ** (-19 / 20) / np.sqrt(np.mean(mix ** 2))
    mix = np.tanh(1.4 * mix) / 1.4
    C.write_wav(OUT / f"day_{piece['id']}.wav", mix.astype(np.float32))
    meta = {k: piece[k] for k in ("id", "title", "key", "bpm", "mood")} | {
        "bars": bars, "seconds": loop_n / SR, "chords": " | ".join(piece["cycle"]),
        "sections": [{"name": name, "t": b * 32 * beat, "bars": 8} for b, (name, _, _) in enumerate(FORM)]}
    (OUT / f"day_{piece['id']}.json").write_text(json.dumps(meta, indent=1))
    return meta | {"peak": float(np.abs(mix).max()), "seam": float(np.abs(mix[:, 0] - mix[:, -1]).max())}


if __name__ == "__main__":
    wrong = {p["id"]: checks(p) for p in PIECES if checks(p)}
    if wrong:
        sys.exit(f"the rules are broken: {wrong}")
    OUT.mkdir(parents=True, exist_ok=True)
    with ProcessPoolExecutor(max_workers=len(PIECES)) as pool:
        done = list(pool.map(render, PIECES))
    for m in done:
        print(f"{m['title']}: {m['bpm']} BPM, {m['seconds']:.0f}s loop, peak {m['peak']:.2f}, seam step {m['seam']:.4f}, checks pass")
    (OUT / "days.json").write_text(json.dumps([{k: v for k, v in m.items() if k not in ("peak", "seam")} for m in done], indent=1))
