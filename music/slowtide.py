"""Slow tide, the music of the first screen, in full.

"go use slow tide for the menu !! but add more depth, make it longer, more details in the background, mastering, real
music. make a last demo out of it. i want real variations with different melodies". The take the user chose
(menu.py "tide", 16 bars, 53 s) is kept as site/audio/keep_slow_tide_first.wav and is the A of this piece, note for
note and on the same sounds. Around it, 64 bars (3 min 12 s at 80; first 3 min 33 s at 72), eight blocks of eight bars:

    1  A   the theme alone over pads and bass, no beat           5  C   the beat stops: a third tune of long notes, on a second voice
    2  A   the beat comes in (the chosen take), an inner voice   6  B   the second tune again, a second voice a sixth under it
    3  B   a second tune, on D minor: it leaps where A knocks    7  A   everything: theme, answer, inner voice, a ghost brush
    4  A   the theme, answered by a second voice                 8  A   the theme alone again; its last bar is the bar before bar 1

Three tunes, each made the house way (one bar three times, then a cadence): A knocks twice and rises a third; B comes
in after the beat, leaps a fifth and settles; C is two long notes, a sigh. Depth is layers, not echo ("lost in a puddle
of echoes"): a high quiet pad, an inner voice moving twice a bar inside the chords, a second voice. No arpeggio, no run,
no decoration that is not a note of the chord. Then the checks (mixcheck, "chill"), the master and the small-speaker
corrections (master.py, refit.py).

    uv run --no-project --python 3.11 --with dawdreamer --with numpy python music/slowtide.py
"""
import json
import wave

import numpy as np

import master
import mixcheck
import pieces
import refit
from directions import midi

OUT = pieces.OUT
V = {"Fmaj9": "E3 G3 A3 C4", "Am7": "G3 C4 E4", "Bbmaj9": "A3 C4 D4 F4", "C13sus": "Bb3 D4 F4", "Dm9": "F3 A3 C4 E4", "F69": "A3 D4 G4",
     "Dm7": "F3 A3 C4", "Gm9": "F3 Bb3 D4 A4", "C13": "Bb3 E4 A4"}
R = {"Fmaj9": "F2", "Am7": "A2", "Bbmaj9": "Bb2", "C13sus": "C3", "Dm9": "D3", "F69": "F2", "Dm7": "D3", "Gm9": "G2", "C13": "C3"}
INNER = {"Fmaj9": "A3 C4", "Am7": "C4 E4", "Bbmaj9": "D4 F4", "C13sus": "D4 G4", "Dm9": "A3 C4", "F69": "D4 C4", "Dm7": "A3 C4", "Gm9": "Bb3 D4", "C13": "Bb3 A3"}
HA = ["Fmaj9", "Am7", "Bbmaj9", "C13sus", "Dm9", "Am7", "Bbmaj9", "F69"]
HB = ["Dm7", "Bbmaj9", "Gm9", "C13sus", "Dm7", "Bbmaj9", "Gm9", "Gm9 C13"]
HC = ["Bbmaj9", "Am7", "Gm9", "Fmaj9", "Bbmaj9", "Am7", "Gm9", "C13sus"]
# A tune: the shape of its bar, the shape of its cadence, its bar three times, the two cadences.
A = dict(cell=[(0, 2), (3, 2), (6, 8)], cad=[(0, 6), (6, 10)], bar="A4 A4 C5", ends=("D5 G4", "C5 F5"))
B = dict(cell=[(2, 2), (4, 4), (10, 5)], cad=[(0, 8), (8, 8)], bar="D5 A5 F5", ends=("G5 D5", "D5 E5"), under="F4 C5 A4")      # (under: a sixth below)
C = dict(cell=[(0, 10), (12, 4)], cad=[(0, 15)], bar="A4 G4", ends=("C5", "D5"))
ANSWER = [(10, 2, "D5"), (12, 4, "C5")]
BEAT = {"half": dict(kick=[(0, 96)], brush=[(8, 84)], shaker=[(s, 58) for s in range(0, 16, 4)]),
        "push": dict(kick=[(0, 96), (10, 76)], brush=[(8, 84)], shaker=[(s, 54) for s in range(0, 16, 2)]),
        "ghost": dict(kick=[(0, 96), (10, 76)], brush=[(8, 86), (14, 58)], shaker=[(s, 58) for s in range(0, 16, 4)]),
        "air": dict(shaker=[(s, 44) for s in range(0, 16, 4)]),
        # The beats of the dynamic versions: the kit of the kept day pieces.
        "thin": dict(hat=[(s, 70) for s in (2, 6, 10, 14)]),
        "bounce": dict(kick=[(0, 108), (7, 86), (10, 96)], snare=[(4, 94), (12, 100)], clap=[(12, 88)], hat=[(s, 86) for s in range(0, 16, 2)]),
        "bounce2": dict(kick=[(0, 108), (8, 98), (10, 84)], snare=[(4, 94), (12, 100)], hat=[(s, 86) for s in range(0, 16, 2)], open=[(14, 76)]),
        "four": dict(kick=[(s, 110 if s == 0 else 100) for s in (0, 4, 8, 12)], snare=[(4, 90), (12, 96)], clap=[(4, 84), (12, 90)], open=[(s, 78) for s in (2, 6, 10, 14)]),
        "four2": dict(kick=[(s, 110 if s == 0 else 100) for s in (0, 4, 8, 12)], clap=[(4, 84), (12, 90)], hat=[(s, 80) for s in range(0, 16, 2)]),
        "half2": dict(kick=[(0, 108), (10, 90)], snare=[(8, 100)], hat=[(s, 84 if s % 4 == 0 else 62) for s in range(16)]),
        "half3": dict(kick=[(0, 108), (6, 84), (10, 90)], snare=[(8, 100)], clap=[(8, 86)], hat=[(s, 84 if s % 4 == 0 else 62) for s in range(16)], open=[(14, 74)])}
BASS = {"long": [(0, 13, 0, 100)], "two": [(0, 7, 0, 100), (8, 6, 0, 88)], "fifth": [(0, 9, 0, 100), (10, 5, 7, 84)],
        "bounce": [(0, 2, 0, 104), (4, 1.5, 12, 88), (8, 2, 0, 96), (12, 1.5, 12, 88)], "sync": [(0, 3, 0, 104), (6, 2, 0, 90), (8, 3, 12, 94), (14, 2, 0, 88)],
        "drive": [(s, 1.6, 12 if s % 4 == 2 else 0, 104 if s % 8 == 0 else 90) for s in range(0, 16, 2)]}
OFF, PUSH, SYNC = [(2, 1), (6, 1), (10, 1), (14, 1)], [(0, 2), (3, 2), (6, 2), (10, 2), (12, 2)], [(0, 2), (3, 2), (6, 2), (11, 2)]
BLOCKS = [dict(h=HA, tune=A), dict(h=HA, tune=A, beat="half", inner=True), dict(h=HB, tune=B, beat="push", air=True, twice=True, bass="two"),
          dict(h=HA, tune=A, beat="half", answer=True, air=True, inner=True, bass="fifth"), dict(h=HC, tune=C, voice="second", beat="air", air=True),
          dict(h=HB, tune=B, beat="push", sixth=True, air=True, twice=True, bass="two", inner=True),
          dict(h=HA, tune=A, beat="ghost", answer=True, air=True, inner=True, bass="fifth"), dict(h=HA, tune=A, air=True)]
PIECE = dict(id="menu_slow_tide", title="Slow tide", bpm=80,          # ("can you make it a bit faster": 72, the chosen take's pace, to 80)
             swing=0.5, sync=True, lead="Jacky Ligon/Keys/Corporealities", chords="Pads/Chowning",
             pad="LinnStrument MPE/Pads/Warm Pad", bass_sound="Rozzer/Basses/Nu Skool Bass 2", double=None,
             kit={"second": "Giana Brotherz/Keys/Sin Ring", "under": "Giana Brotherz/Keys/Sin Ring", "answer": "Giana Brotherz/Keys/Sin Ring",
                  "inner": "Polysynths/Uni Saw FB", "air": "Jacky Ligon/Pads/Closer Still", "stab": "Giana Brotherz/Keys/Glass Tick"},
             levels={"kick": -22, "brush": -27, "shaker": -34, "chords": -20, "pad": -22, "bass": -17, "lead": -15, "second": -16, "under": -24, "answer": -23,
                     "inner": -27, "air": -30})
# "nah it sucks. i want something more dynamic. with just a gradient at the beginning to avoid it popping out of
# nowhere" (on the full version, at 72 then 80: every block within 1 dB of the others, pads in front, hardly a beat).
# Dynamic, three ways, on the theme and the sounds the user chose: a real kit (the kept day pieces'), a bass that moves,
# short chords, and blocks that differ: a thin first block (it is also where the loop comes back to breathe), the
# groove, the second tune, everything. The gradient is the player's (the page, then audio.js): the first seconds rise
# in level and open in tone; it is not in the file, which loops.
def form(groove, groove2, bass, bass2, stab):
    return [dict(name="A · the theme, thin", h=HA, tune=A, beat="thin", bass="long", air=True),
            dict(name="A · the groove comes in", h=HA, tune=A, beat=groove, bass=bass, stab=stab, answer=True, fill=True),
            dict(name="B · the second tune", h=HB, tune=B, beat=groove2, bass=bass2, stab=stab, twice=True, air=True, fill=True),
            dict(name="A · everything", h=HA, tune=A, beat=groove, bass=bass, stab=stab, answer=True, inner=True, air=True, fill=True)]


DAY = {"lead": -15, "second": -16, "under": -24, "answer": -22, "inner": -27, "air": -31, "stab": -21, "chords": -25, "pad": -26, "bass": -18.5,
       "kick": -18, "snare": -21, "clap": -26, "hat": -26.5, "open": -28}
VARIANTS = [
    dict(id="full", title="Slow tide in full (refused)", feel="64 bars, pads in front", bpm=80, blocks=[b | dict(name=str(i + 1)) for i, b in enumerate(BLOCKS)], ref="chill"),
    dict(id="bounce", title="Rising tide", feel="a bounce: the bass hops between octaves, short chords off the beat, snare on two and four", bpm=96, levels=DAY,
         blocks=form("bounce", "bounce2", "bounce", "sync", OFF)),
    dict(id="four", title="High tide", feel="a kick on every beat, open hats between, a bass that drives in eighths, pushed chords", bpm=104, levels=DAY,
         blocks=form("four", "four2", "drive", "drive", PUSH)),
    dict(id="half", title="Spring tide", feel="half time under running hats: one snare a bar, a bass that leans across the beat", bpm=88, levels=DAY,
         blocks=form("half2", "half3", "sync", "bounce", SYNC)),
]
TUNES = ("lead", "second", "under", "answer", "inner")


def arrange(st=None):
    p = {k: [] for k in ("lead", "second", "under", "answer", "inner", "air", "stab", "chords", "pad", "bass", "kick", "snare", "clap", "hat", "open", "brush", "shaker")}
    under = {}
    blocks = (st or {}).get("blocks", BLOCKS)
    for k, blk in enumerate(blocks):
        t = blk["tune"]
        for b, bar in enumerate(blk["h"]):
            s0, chs = 16 * (8 * k + b), bar.split()
            cadence = b % 4 == 3
            notes = (t["ends"][b // 4] if cadence else t["bar"]).split()
            for (s, ln), note in zip(t["cad"] if cadence else t["cell"], notes):
                p[blk.get("voice", "lead")].append((s0 + s, ln, midi(note), 100 if s % 4 == 0 else 88))
            if blk.get("sixth") and not cadence:
                p["under"] += [(s0 + s, ln, midi(note), 80) for (s, ln), note in zip(t["cell"], t["under"].split())]
            if blk.get("answer") and not cadence:
                p["answer"] += [(s0 + s, ln, midi(note), 84) for s, ln, note in ANSWER]
            half = 16 // len(chs)
            for j, ch in enumerate(chs):
                at = s0 + half * j
                for s in range(half):
                    under[at + s] = V[ch].split() + [R[ch]]
                for s, ln in ([(0, 7), (8, 7)] if blk.get("twice") else [(0, 15)]):
                    if s < half:
                        p["chords"] += [(at + s, min(ln, half - 1), midi(v), 80 - 3 * i) for i, v in enumerate(V[ch].split())]
                p["stab"] += [(at + s, ln, midi(v) - 12, 80 - 3 * i)       # (this sound speaks an octave over its key)
                              for s, ln in blk.get("stab", []) if s < half for i, v in enumerate(V[ch].split())]
                p["pad"] += [(at, half, midi(v) + 12, 70) for v in V[ch].split()[-3:]]
                if blk.get("air"):
                    p["air"] += [(at, half, midi(v) + 24, 60) for v in V[ch].split()[-2:]]
                if blk.get("inner"):
                    p["inner"] += [(at + i * half // 2, half // 2, midi(v), 76) for i, v in enumerate(INNER[ch].split())]
                p["bass"] += [(at + s, min(ln, half - 1), midi(R[ch]) + up, vel) for s, ln, up, vel in BASS[blk.get("bass", "long")] if s < half]
            for part, hits in BEAT.get(blk.get("beat"), {}).items():
                p[part] += [(s0 + s, 1, 48 if part == "kick" else 60, vel) for s, vel in hits]
            if blk.get("fill") and b == 7:
                p["snare"] += [(s0 + 13, 1, 60, 70), (s0 + 15, 1, 60, 90)]
    return {k: v for k, v in p.items() if v}, 16 * 8 * len(blocks), under


def clashes(score, under):
    """Notes a semitone (or a minor ninth) above a note of the chord sounding under them."""
    return [(part, int(s) // 16 + 1, m) for part in TUNES for s, _, m, _ in score.get(part, []) for v in under[int(s)] if m - midi(v) in (1, 13)]


def render(v):
    st = pieces.BASE | PIECE | v | dict(id="menu_tide_" + v["id"], levels=PIECE["levels"] | v.get("levels", {}))
    score, steps, under = arrange(st)
    bad = clashes(score, under)
    if bad:
        raise SystemExit(f"{v['id']}: notes that clash with their chord (part, bar, note): {bad}")
    parts = mixcheck.stems(st, arrange)
    lines = []
    wrong = mixcheck.check(parts, lines.append, v.get("ref", "day"))
    wrong += [f"the {part} sounds under 120 Hz" for part in ("second", "under", "inner", "air", "stab")
              if part in parts and 10 * np.log10(mixcheck.bands(parts[part])[:2].sum() / mixcheck.bands(sum(parts.values())).sum() + 1e-12) > -30]
    x, did = master.master(mixcheck.bus(parts), "day")              # glue, lows to the centre, -20 LUFS, true peak under -1 dB
    y, fixes, before, after = refit.refit(x)                        # then what a laptop and a single speaker need
    with wave.open(str(OUT / f"menu_tide_{v['id']}.wav"), "wb") as w:
        w.setnchannels(2), w.setsampwidth(2), w.setframerate(pieces.SR)
        w.writeframes(np.round(np.clip(y, -1, 1).T * 32767).astype(np.int16).tobytes())
    blocks = []
    for k in range(len(st["blocks"])):                              # each block's own level, to see the piece breathe
        i, j = (int(round(n * 128 * 60 / st["bpm"] / 4 * pieces.SR)) for n in (k, k + 1))
        blocks.append(round(master.lufs(y[:, i:j]) - after["lufs"], 1))
    print(f"\n== {v['title']}  {y.shape[1] / pieces.SR:.0f} s\n" + "\n".join(lines) + f"\n   out of range: {wrong or 'nothing'}\n   master {did}; small speakers {fixes or 'nothing'}\n   blocks against the whole (dB): {blocks}", flush=True)
    return dict(id=v["id"], title=v["title"], feel=v["feel"], bpm=st["bpm"], seconds=round(y.shape[1] / pieces.SR, 1), out_of_range=wrong, blocks=blocks,
                names=[b["name"] for b in st["blocks"]], lufs=float(after["lufs"]), true_peak=float(after["true_peak"]))


if __name__ == "__main__":
    import sys
    from multiprocessing import get_context
    todo = [v for v in VARIANTS if (v["id"] in sys.argv[1:] if sys.argv[1:] else v["id"] != "full")]
    with get_context("spawn").Pool(4) as pool:
        done = {d["id"]: d for d in pool.map(render, todo)}
    old = {d["id"]: d for d in json.loads((OUT / "tide.json").read_text())} if (OUT / "tide.json").exists() else {}
    (OUT / "tide.json").write_text(json.dumps([(old | done)[v["id"]] for v in VARIANTS if v["id"] in old | done], indent=1))
