"""Other music for the day: four suggestions, each its own tune and its own instruments, in Meadow Road's manner
(bouncing bass, chords off the beat, a light swing), dry.

    uv run python music/day.py        ->  music/site/audio/day_<id>.wav and .json, days.json

The rules, checked for every piece by music/quality.py (the day theme, night and boss go through the same audit):
chords are struck together (no arpeggios); the melody never takes two steps in a row in the same direction, never
outlines a chord with three leaps the same way, and has no augmented leap; a leap larger than a fourth turns back; every
melody note on a beat is a chord note; nothing sounds a minor ninth under the melody. Each tune is one two-bar idea:
said, answered, said again, closed on a cadence. No two tracks share a lead instrument, and at most five play at once.
"""
import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

import compose as C
from compose import SR, analog_pad, hp, lp, midi, tt

OUT = C.OUT
TAIL = 6 * SR
QUAL = {"maj7": (0, 4, 7, 11), "m7": (0, 3, 7, 10), "7sus": (0, 5, 7, 10), "7": (0, 4, 7, 10), "6": (0, 4, 7, 9), "m": (0, 3, 7), "": (0, 4, 7)}
# who plays, block by block (8 bars each): the melody (1: the lead, 2: the second voice, 12: the lead says it, the
# second answers, -: nobody), the band (0: pad and held chords, 1: bass and chords, 2: with the percussion)
FORM = [("the tune", "1", 1), ("with the band", "1", 2), ("the band alone", "-", 2), ("handed over", "2", 2),
        ("call and answer", "12", 2), ("open air", "-", 0)]
GAIN = dict.fromkeys(["lead", "second", "chords", "pad", "bass", "perc"], 1.0)
# How loud each part is against the lead, in dB of loudness while it plays. render() sets every part to this, whatever
# the instruments are: the tune ends up 1 to 2 dB over the whole band, the bass felt, the chords behind, the rest far.
BALANCE = {"lead": 0.0, "second": 0.0, "chords": -7.0, "bass": -4.0, "pad": -13.0, "perc": -13.0}

PIECES = [
    dict(id="market", title="Market Morning", key="G major", bpm=96, swing=0.6, mood="bouncy, on its toes",
         band=dict(lead="marimba", second="flute", chords="nylon", bass="upright", perc=["shaker"]),
         cycle=["Gmaj7", "Em7", "Cmaj7", "D7", "Gmaj7", "Em7", "Am7 D7", "G6"],
         melody=[[(0, 1, "D5"), (1, 1, "B4"), (3, 2, "D5"), (6, 2, "B4")], [(0, 4, "E5")],
                 [(0, 1, "E5"), (1, 1, "C5"), (3, 2, "E5"), (6, 2, "C5")], [(0, 4, "D5")],
                 [(0, 1, "D5"), (1, 1, "B4"), (3, 2, "D5"), (6, 2, "B4")], [(0, 4, "E5")],
                 [(0, 1, "E5"), (1, 1, "C5"), (3, 2, "D5"), (6, 2, "F#4")], [(0, 6, "G4")]]),
    dict(id="afternoon", title="Slow Afternoon", key="F major", bpm=72, swing=0.6, mood="lazy, long notes, waits for beat two",
         band=dict(lead="rhodes", second="clarinet", chords="vibes", bass="moog_bass", perc=[], held=True),
         cycle=["Fmaj7", "Dm7", "Bbmaj7", "C7sus", "Fmaj7", "Am7", "Gm7 C7", "F6"],
         melody=[[(2, 1, "E5"), (3, 3, "C5"), (6, 2, "F5")], [(0, 5, "D5")],
                 [(2, 1, "D5"), (3, 3, "Bb4"), (6, 2, "D5")], [(0, 5, "C5")],
                 [(2, 1, "E5"), (3, 3, "C5"), (6, 2, "F5")], [(0, 5, "C5")],
                 [(2, 1, "D5"), (3, 2, "Bb4"), (6, 2, "C5")], [(0, 6, "A4")]]),
    dict(id="overcast", title="Overcast", key="A minor, closing in C major", bpm=80, swing=0.56, mood="bittersweet, a repeated note",
         band=dict(lead="clarinet", second="vibes", chords="epiano", bass="upright", perc=["shaker"]),
         cycle=["Am7", "Fmaj7", "Cmaj7", "G", "Am7", "Fmaj7", "Dm7 G7", "C6"],
         melody=[[(0, 1, "E5"), (1, 1, "E5"), (2, 2, "C5"), (5, 3, "E5")], [(0, 4, "A4")],
                 [(0, 1, "E5"), (1, 1, "E5"), (2, 2, "C5"), (5, 3, "D5")], [(0, 4, "B4")],
                 [(0, 1, "E5"), (1, 1, "E5"), (2, 2, "C5"), (5, 3, "E5")], [(0, 4, "A4")],
                 [(0, 1, "F5"), (1, 1, "F5"), (2, 3, "D5"), (6, 2, "D5")], [(0, 6, "C5")]]),
    dict(id="picnic", title="Picnic", key="A major", bpm=100, swing=0.62, mood="brisk and playful, call and answer",
         band=dict(lead="melodica", second="nylon", chords="marimba", bass="moog_bass", perc=["shaker", "woodblock"]),
         cycle=["Amaj7", "F#m7", "Dmaj7", "E7", "Amaj7", "F#m7", "Bm7 E7", "A6"],
         melody=[[(0, 1, "E5"), (1, 1, "C#5"), (2, 2, "E5"), (5, 2, "A4")], [(1, 1, "B4"), (2, 2, "A4"), (4, 3, "F#4")],
                 [(0, 1, "D5"), (1, 1, "A4"), (2, 2, "D5"), (5, 2, "F#4")], [(1, 1, "F#4"), (2, 2, "B4"), (4, 3, "E4")],
                 [(0, 1, "E5"), (1, 1, "C#5"), (2, 2, "E5"), (5, 2, "A4")], [(1, 1, "B4"), (2, 2, "A4"), (4, 3, "F#4")],
                 [(0, 1, "D5"), (1, 1, "B4"), (2, 2, "D5"), (4, 2, "E5"), (6, 2, "B4")], [(0, 6, "A4")]]),
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
    """The chord as it is played: without its root, without any note a minor ninth under the melody, between C3 and
    D4 (under the tune), each note in the octave nearest the chord before it, so that no voice jumps."""
    key = (piece["id"], i, at)
    if key not in _hands:
        centre = 56.0
        for _ in range(2):                                         # twice round the cycle: the first bar follows the last
            for b in range(8):
                for a_, l_, c_ in spans(piece, b):
                    mel = over(piece, b, a_, l_)
                    pcs = [pc for pc in tones(c_)[1:] if not any((m - pc) % 12 == 1 for m in mel)]
                    v = sorted(min((n for n in range(48, 63) if n % 12 == pc), key=lambda n: abs(n - centre)) for pc in pcs)
                    _hands[(piece["id"], b, a_)] = v
                    centre = sum(v) / len(v) if v else centre
    return _hands[key]


_hands = {}


def render(piece, want_stems=False):
    rng = np.random.default_rng(len(piece["id"]) * 7 + piece["bpm"])
    band = piece["band"]
    lead, second, chords, bass = (getattr(C, band[k]) for k in ("lead", "second", "chords", "bass"))
    bars = 8 * len(FORM)
    loop_n = C.fast_len(int(round(bars * 4 * 60 / piece["bpm"] * SR)))
    beat = loop_n / SR / (bars * 4)
    t_of = lambda slot: (slot // 2 + (piece["swing"] if slot % 2 >= 1 else 0.0) + (slot % 1) * 0.5) * beat
    n = loop_n + TAIL
    dry, rev = ({k: np.zeros((2, n)) for k in GAIN} for _ in range(2))

    def note(stem, slot, ln, m, vel, inst, pan=0.0, send=0.25, human=True):
        t0, dur = t_of(slot), ln * beat / 2
        if human:
            t0, vel = t0 + abs(rng.normal(0, 0.008)), vel * (1 + rng.normal(0, 0.06))
        y = np.atleast_2d(inst(C.hz(m), dur, vel, t0)) * GAIN[stem]
        y = np.vstack([y, y])[:2]
        k = int(round(t0 * SR))
        y = y[:, : n - k]
        a = (pan + 1) * np.pi / 4
        y = y * np.array([[np.cos(a)], [np.sin(a)]]) * np.sqrt(2)
        dry[stem][:, k:k + y.shape[1]] += y
        rev[stem][:, k:k + y.shape[1]] += send * y

    for b, (_, who, level) in enumerate(FORM):
        for i in range(8):
            s0 = (b * 8 + i) * 8
            for j, (s, ln, nm) in enumerate(piece["melody"][i]):
                touch = 1.0 if j == 0 or ln >= 3 else 0.82
                first = who == "1" or (who == "12" and i % 4 < 2)        # call and answer: two bars each
                if who != "-" and first:
                    note("lead", s0 + s, ln, midi(nm), 0.66 * touch, lead, pan=0.1, send=0.3)
                elif who != "-":
                    note("second", s0 + s, ln, midi(nm), 0.66 * touch, second, pan=-0.15, send=0.35)
            for at, ln, ch in spans(piece, i):
                root, notes = 33 + (tones(ch)[0] - 33) % 12, hand(piece, i, at, ln, ch)
                for j, m in enumerate(notes):
                    if not level or band.get("held"):              # the chord held, struck once, all its notes together
                        note("chords", s0 + at, ln, m, (0.6 if not level else 0.36) - 0.03 * j, chords, pan=-0.3 + 0.3 * j, send=0.35)
                    else:                                          # short, off the beat
                        for off, v in ((2, 0.8), (5, 0.62)) if ln == 8 else ((1, 0.75),):
                            note("chords", s0 + at + off, 1, m, v * (0.9 if who != "-" else 1.0), chords, pan=-0.35 + 0.35 * j)
                for pc in tones(ch)[:3]:
                    note("pad", s0 + at, ln, 50 + (pc - 50) % 12, 1.6 if not level else 0.35, analog_pad, send=0.4, human=False)
                if level and band.get("held"):                     # a held bass: the root, then the fifth late in the bar
                    note("bass", s0 + at, ln - 0.5 if ln < 8 else 5.5, root, 0.8, bass, send=0.0, human=False)
                    if ln == 8:
                        note("bass", s0 + 6, 1.6, root + 7, 0.6, bass, send=0.0, human=False)
                elif level:                                        # the bass bounces: root, root, fifth
                    note("bass", s0 + at, 1.6, root, 0.85, bass, send=0.0, human=False)
                    if ln == 8:
                        note("bass", s0 + 3, 0.8, root, 0.5, bass, send=0.0, human=False)
                        note("bass", s0 + 4, 1.6, root + 7, 0.72, bass, send=0.0, human=False)
            if level == 2 and "shaker" in band["perc"]:
                for k in range(8):
                    note("perc", s0 + k, 1, 60, 0.9 if k in (2, 6) else 0.42 if k % 2 else 0.6, C.shaker, pan=0.3, send=0.12)
            if level == 2 and "woodblock" in band["perc"]:
                for k in (3, 7):
                    note("perc", s0 + k, 1, 60, 0.7, C.woodblock, pan=-0.3, send=0.2)

    fold = lambda x: x[:, :loop_n] + np.pad(x[:, loop_n:], ((0, 0), (0, loop_n - TAIL)))     # the tail comes back at the start
    f = np.fft.rfftfreq(loop_n, 1 / SR)
    irs = C.room(rng, loop_n)
    stems = {}
    for k in GAIN:
        d, r = fold(dry[k]), fold(rev[k])
        wet = np.stack([np.fft.irfft(np.fft.rfft(r[c]) * irs[c], loop_n) for c in range(2)])
        stems[k] = np.fft.irfft(np.fft.rfft(d + C.WET * wet, axis=-1) * hp(30, 2)(f) * lp(15000, 2)(f), loop_n, axis=-1)
    edges = np.linspace(0, loop_n, len(FORM) + 1).astype(int)
    on = {"lead": lambda who, lv: "1" in who, "second": lambda who, lv: "2" in who, "perc": lambda who, lv: lv == 2}
    loud = {}
    for k in GAIN:                                                 # each part's loudness over the blocks where it plays
        parts = [stems[k][:, a:b] for (_, who, lv), a, b in zip(FORM, edges, edges[1:]) if on.get(k, lambda who, lv: lv >= 1)(who, lv)]
        loud[k] = C.lufs(np.concatenate(parts, axis=-1)) if parts and np.abs(stems[k]).max() > 1e-6 else None
    for k in GAIN:
        if loud[k] is not None:
            stems[k] = stems[k] * 10 ** ((loud["lead"] + BALANCE[k] - loud[k]) / 20)
    stems, mix = C.master(stems, -17)
    C.write_wav(OUT / f"day_{piece['id']}.wav", mix.astype(np.float32))
    meta = {k: piece[k] for k in ("id", "title", "key", "bpm", "mood")} | {
        "bars": bars, "seconds": loop_n / SR, "chords": " | ".join(piece["cycle"]),
        "band": ", ".join(NAMES[band[k]] for k in ("lead", "second", "chords", "bass")) + "".join(", " + p for p in band["perc"]),
        "sections": [{"name": name, "t": b * 32 * beat, "bars": 8} for b, (name, _, _) in enumerate(FORM)]}
    (OUT / f"day_{piece['id']}.json").write_text(json.dumps(meta, indent=1))
    out = meta | {"peak": float(np.abs(mix).max()), "seam": float(np.abs(mix[:, 0] - mix[:, -1]).max())}
    return (out, mix, stems) if want_stems else out


NAMES = {"marimba": "marimba", "flute": "flute", "nylon": "nylon guitar", "upright": "double bass", "rhodes": "concert harp",
         "clarinet": "clarinet", "vibes": "vibraphone", "moog_bass": "double bass", "epiano": "harp", "melodica": "harmonica"}


if __name__ == "__main__":
    import quality
    wrong = {p["id"]: quality.theory(p)["fail"] for p in PIECES if quality.theory(p)["fail"]}
    if wrong:
        sys.exit(f"the rules are broken: {wrong}")
    OUT.mkdir(parents=True, exist_ok=True)
    with ProcessPoolExecutor(max_workers=len(PIECES)) as pool:
        done = list(pool.map(render, PIECES))
    for m in done:
        print(f"{m['title']}: {m['bpm']} BPM, {m['seconds']:.0f}s loop, peak {m['peak']:.2f}, seam step {m['seam']:.4f}, checks pass")
    (OUT / "days.json").write_text(json.dumps([{k: v for k, v in m.items() if k not in ("peak", "seam")} for m in done], indent=1))
