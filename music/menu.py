"""Five candidates for the first screen's music: "5 music for the start menu with their unique theme. cute and fast".

What the reading says a menu theme is for (sources on the page, site/menu.html): it is the appetizer, it says the
game's mood before anything is played; the tune must be caught in the first seconds; it loops for as long as someone
stays, so it loops without a seam; it runs a little faster than the music of play; cute and bright is a major key,
126 to 154 BPM in the title themes measured, short notes, a groove that bounces.

Each is its own theme, not one tune dressed five ways ("we should create 2-3 themes": a theme is its own cell, key,
rhythm and sounds): its own key and chord cycle, its own groove (a bounce, a kick on every beat, a shuffle, a waltz,
a 3+3+2), its own lead bar, and sounds no kept piece uses. What they share is the house recipe the user kept
(pieces.py): rich chords under a lead made of ONE bar played three times and a cadence, synth sounds being synths,
dry, every sound measured on the beat with no echo (surge.timing).

Second round. "please keep a sound engineer approach, because everyone of them sounds bad i think": the first five had
sounds picked by name. mixcheck.py soloed every part and found parts in the wrong register (sounds that speak an
octave under their key), a lead that was a click, a buzzing bass, no pad, flat or holed dynamics. Now every sound is
the measured nearest (attack, body, ring, brightness, width, tuning; 1,200 sounds scanned) to a sound of a kept piece
without being one, `shift` puts each part back in its register, each piece has its own pad, leads that hold are played
short (`gate`), and render() prints what is still out of the kept pieces' ranges.

    uv run --no-project --python 3.11 --with dawdreamer --with numpy python music/menu.py [id ...]
"""
from pathlib import Path
import json
import sys
import wave

import numpy as np

import master
import mixcheck
import pieces
from directions import midi

OUT = pieces.OUT
STRAIGHT = pieces.ACC
WALTZ = (1.0, 0.7, 0.78, 0.7, 0.88, 0.7, 0.8, 0.7, 0.86, 0.7, 0.8, 0.72)


def bars(cell, n=3):
    return [("cell", cell)] * n


MENU = [
    dict(id="hop", title="Hop in", key="G major", feel="a bounce: the bass hops between octaves, the chords land off the beat", bpm=132, passes=2,
         H=["Gmaj9", "Cmaj9", "Gmaj9", "D13", "Em9", "Cmaj9", "Am9 D13", "G69"] * 2,
         V={"Gmaj9": "F#3 A3 B3 D4", "Cmaj9": "E3 G3 B3 D4", "D13": "F#3 B3 C4 E4", "Em9": "G3 B3 D4 F#4", "Am9": "G3 B3 C4 E4", "G69": "E3 A3 B3 D4"},
         R={"Gmaj9": "G2", "Cmaj9": "C3", "D13": "D3", "Em9": "E2", "Am9": "A2", "G69": "G2"},
         cell=[(0, 2), (3, 2), (6, 5), (12, 3)], cadence=[(0, 3), (3, 3), (6, 10)],       # the same note twice, a hop up, a drop: one bar that fits all seven chords
         tune=(bars("B4 B4 D5 A4") + [("cadence", "E5 D5 A4")] + bars("B4 B4 D5 A4") + [("cadence", "B4 A4 G4")]) * 2,
         comp=[(2, 1), (6, 1), (10, 1), (14, 1)], bass=[(0, 2, 0, 104), (4, 1.5, 12, 88), (8, 2, 0, 96), (12, 1.5, 12, 88)],
         beat=dict(kick=[(0, 110), (7, 88), (10, 98)], snare=[(4, 96), (12, 102)], clap=[(12, 90)], hat=[(s, 88) for s in range(0, 16, 2)]),
         fill=dict(snare=[(13, 70), (15, 92)]),
         gate=0.55, levels={"lead": -16.5}, lead="Kinsey Dulcet/Leads/Funk Feedback Lead", double="Damon Armani/Plucks/Daft Punk", chords="Plucks/Scrape Pluck", pad="Pads/Sawteeth", bass_sound="Basses/Rubber Bass",
         shift={"lead": 12, "double": 12}),
    dict(id="sugar", title="Sugar rush", key="E flat major", feel="a kick on every beat, the fastest of the five; the lead calls, a second synth answers", bpm=156, passes=1,
         H=["Abmaj9", "Bb13", "Gm7", "Cm9", "Abmaj9", "Bb13", "Ebmaj9", "Eb69", "Abmaj9", "Bb13", "Gm7", "Cm9", "Fm9", "Bb13", "Ebmaj9", "Eb69"] * 2,
         V={"Abmaj9": "G3 Bb3 C4 Eb4", "Bb13": "Ab3 C4 D4 G4", "Gm7": "F3 Bb3 D4", "Cm9": "Eb3 G3 Bb3 D4", "Fm9": "Ab3 C4 Eb4 G4", "Ebmaj9": "G3 Bb3 D4 F4", "Eb69": "G3 Bb3 C4 F4"},
         R={"Abmaj9": "Ab2", "Bb13": "Bb2", "Gm7": "G2", "Cm9": "C3", "Fm9": "F2", "Ebmaj9": "Eb2", "Eb69": "Eb2"},
         cell=[(0, 2), (2, 2), (4, 5)], cadence=[(0, 3), (3, 3), (6, 10)],                # two knocks and a leap of a fifth, held; then the answer
         tune=(bars("C5 C5 G5") + [("cadence", "D5 Bb4 G4")] + bars("C5 C5 G5") + [("cadence", "C5 Bb4 G4")]
               + bars("C5 C5 G5") + [("cadence", "D5 Bb4 G4")] + bars("C5 C5 G5") + [("cadence", "Bb4 C5 Eb5")]) * 2,
         answer=[(10, 2, "Bb4"), (12, 3, "G4")],
         comp=[(0, 2), (3, 2), (6, 2), (10, 2), (12, 2)], bass=[(s, 1.6, 12 if s % 4 == 2 else 0, 106 if s % 8 == 0 else 90) for s in range(0, 16, 2)],
         beat=dict(kick=[(0, 114), (4, 104), (8, 108), (12, 104)], snare=[(4, 100), (12, 106)], clap=[(4, 84), (12, 92)], open=[(2, 80), (6, 80), (10, 80), (14, 80)]),
         fill=dict(snare=[(13, 76), (14, 88), (15, 100)]),
         lead="Damon Armani/Plucks/Rattler", second="Damon Armani/Leads/Funky", chords="Polysynths/Phasey", pad="Polysynths/Xpander 2", bass_sound="Basses/Slow",
         shift={"pad": 12},
         kit={"kick": "TNMG/Drums/Kick - Classic", "snare": "TNMG/Drums/Snare - Classic"}),
    dict(id="skip", title="Skip rope", key="C major", feel="a shuffle: every second note comes late, the bass walks", bpm=120, swing=0.64, passes=2,
         H=["C69", "A7b9", "Dm9", "G13", "Em7", "A7b9", "Dm9 G13", "C69"] * 2,
         V={"C69": "E3 A3 D4 G4", "A7b9": "G3 Bb3 C#4 E4", "Dm9": "F3 A3 C4 E4", "G13": "F3 B3 E4", "Em7": "G3 B3 D4"},
         R={"C69": "C3", "A7b9": "A2", "Dm9": "D3", "G13": "G2", "Em7": "E2"},
         cell=[(0, 2), (2, 2), (4, 2), (6, 6)], cadence=[(0, 4), (4, 4), (8, 8)],          # long-short, long-short: the skip itself
         tune=(bars("E5 E5 G5 E5") + [("cadence", "E5 D5 B4")] + bars("E5 E5 G5 E5") + [("cadence", "A4 G4 C5")]) * 2,
         comp=[(0, 3), (6, 2), (14, 2)], bass=[(0, 3.5, 0, 104), (4, 3.5, 7, 90), (8, 3.5, 12, 96), (12, 3.5, 7, 90)],
         beat=dict(kick=[(0, 100), (8, 92)], clap=[(4, 88), (12, 92)], hat=[(s, 84) for s in range(0, 16, 2)], click=[(6, 70), (14, 76)]),
         fill=dict(snare=[(14, 90)]),
         lead="Polysynths/Quote", double="Dan Maurer/Plucks/Hidden Tiger", chords="Polysynths/MG", pad="Bluelight/Pads/Sawdust", bass_sound="Damon Armani/Basses/Satu Bass",
         shift={"pad": 12}),
    dict(id="carousel", title="Carousel", key="B flat major", feel="a fast waltz, three beats a bar: the bass on one, the chords on two and three", bpm=174, spb=12, passes=4,
         H=["Bbmaj9", "Dm7", "Ebmaj9", "F13", "Bbmaj9", "Dm7", "Ebm6", "F13", "Bbmaj9", "Dm7", "Ebmaj9", "F13", "Gm9", "Ebm6", "F13", "Bb69"],
         V={"Bbmaj9": "A3 C4 D4 F4", "Dm7": "F3 A3 C4", "Ebmaj9": "G3 Bb3 D4 F4", "F13": "Eb3 A3 D4", "Ebm6": "Gb3 Bb3 C4 Eb4", "Gm9": "F3 A3 Bb3 D4", "Bb69": "G3 C4 D4 F4"},
         R={"Bbmaj9": "Bb2", "Dm7": "D3", "Ebmaj9": "Eb3", "F13": "F2", "Ebm6": "Eb3", "Gm9": "G2", "Bb69": "Bb2"},
         cell=[(0, 4), (4, 2), (6, 2), (8, 4)], cadence=[(0, 4), (4, 8)],                  # down a third and back: round and round
         tune=bars("F5 D5 D5 F5") + [("cadence", "D5 C5")] + bars("F5 D5 D5 F5", 2) + [("cell", "F5 Eb5 Eb5 F5"), ("cadence", "A4 C5")]
              + bars("F5 D5 D5 F5") + [("cadence", "D5 C5"), ("cell", "F5 D5 D5 F5"), ("cell", "F5 Eb5 Eb5 F5"), ("cell", "F5 D5 D5 F5"), ("cadence", "C5 Bb4")],
         comp=[(4, 2), (8, 2)], bass=[(0, 4, 0, 104)],
         beat=dict(kick=[(0, 104)], hat=[(4, 84), (8, 88)]), even=dict(clap=[(8, 84)]), fill=dict(hat=[(6, 70), (10, 80)]),
         gate=0.4, levels={"bass": -15}, lead="Bluelight/Leads/Lead 3", double="Leads/Fuji", chords="Plucks/Woody", pad="Pads/Communication", bass_sound="Basses/Bass 1",
         shift={"lead": -12, "double": 12}),
    dict(id="tide", title="Tide pool", key="D major, with the C chord of its sunny side", feel="3+3+2: bass and kick push across the beat, one clap a bar", bpm=138, passes=2,
         H=["D69", "Cmaj9", "Gmaj9", "A13sus", "D69", "Cmaj9", "Gmaj9", "A13"] * 2,
         V={"D69": "F#3 B3 E4", "Cmaj9": "E3 G3 B3 D4", "Gmaj9": "F#3 A3 B3 D4", "A13sus": "G3 B3 D4 F#4", "A13": "G3 B3 C#4 F#4"},
         R={"D69": "D3", "Cmaj9": "C3", "Gmaj9": "G2", "A13sus": "A2", "A13": "A2"},
         cell=[(0, 5), (6, 5), (12, 2), (14, 2)], cadence=[(0, 6), (6, 10)],              # on the 3+3+2 itself: two long, a leap up, a step back
         tune=(bars("A4 A4 F#5 E5") + [("cadence", "E5 B4")] + bars("A4 A4 F#5 E5") + [("cadence", "E5 C#5")]) * 2,
         comp=[(3, 2), (10, 2), (14, 2)], bass=[(0, 3, 0, 106), (6, 3, 0, 96), (12, 2, 12, 92)],
         beat=dict(kick=[(0, 112), (6, 96), (12, 88)], clap=[(8, 96)], hat=[(s, 84) for s in range(0, 16, 2)], click=[(3, 76), (11, 70)]),
         fill=dict(snare=[(13, 72), (14, 84), (15, 96)]),
         gate=0.45, lead="Leads/Resofest 2", double="Leads/Generic", chords="Polysynths/Reset", pad="Argitoth/Pads/Subtle Pad", bass_sound="Bluelight/Basses/Bass 7",
         shift={"lead": 12, "double": 12, "pad": 12}),
]


def arrange(st):
    """The parts of one candidate: the whole score once per pass; from the second pass on the lead is doubled an
    at the same pitch by a second sound. Returns what pieces.side_street() returns."""
    spb, H, n = st.get("spb", 16), st["H"], len(st["H"])
    acc = (lambda s: STRAIGHT[int(s) % 16]) if spb == 16 else (lambda s: WALTZ[int(s) % 12])
    shapes = {"cell": st["cell"], "cadence": st["cadence"]}
    p = {k: [] for k in ("lead", "double", "answer", "chords", "pad", "bass", "kick", "snare", "clap", "hat", "open", "click")}
    under = {}
    for k in range(st["passes"]):
        for b, bar in enumerate(H):
            s0, chs = spb * (k * n + b), bar.split()
            kind, notes = st["tune"][b]
            for (s, ln), note in zip(shapes[kind], notes.split()):
                p["lead"].append((s0 + s, ln * st.get("gate", 1), midi(note), 100 * acc(s)))        # (gate: a sound that holds is played short)
                if k % 2 and "double" in st:
                    p["double"].append((s0 + s, ln, midi(note), 80 * acc(s)))
            if kind == "cell":
                p["answer"] += [(s0 + s, ln, midi(note), 92) for s, ln, note in st.get("answer", [])]
            half = spb // len(chs)
            for j, ch in enumerate(chs):
                at = s0 + half * j
                for s in range(half):
                    under[at + s] = (st["V"][ch].split() + [st["R"][ch]], ch)
                if st.get("pad"):                               # the chord held an octave above the stabs: the floor the kept pieces stand on
                    p["pad"] += [(at, half, midi(v) + 12, 70) for v in st["V"][ch].split()[-3:]]
                for s, ln in st["comp"]:
                    if s < half:
                        p["chords"] += [(at + s, ln, midi(v), (80 - 3 * i) * acc(s)) for i, v in enumerate(st["V"][ch].split())]
                p["bass"] += [(at + s, ln, midi(st["R"][ch]) + up, vel) for s, ln, up, vel in st["bass"] if s < half]
            fill = b % 8 == 7
            for src in (st["beat"], st.get("even", {}) if b % 2 else {}, st.get("fill", {}) if fill else {}):
                for part, hits in src.items():
                    p[part] += [(s0 + s, 1, 48 if part == "kick" else 60, vel * (acc(s) if part == "hat" else 1)) for s, vel in hits]
    shift = st.get("shift", {})                                 # a sound that speaks an octave under its key is played an octave up
    p = {k: [(s, ln, m + shift.get(k, 0), v) for s, ln, m, v in notes] for k, notes in p.items() if notes}
    return p, spb * n * st["passes"], under


def render(m):
    """One candidate: its parts alone, the engineer's checks on them (mixcheck), the kept pieces' mix bus, the game's level."""
    st = pieces.BASE | dict(m, id="menu_" + m["id"], sync=True, levels={"answer": -19} | m.get("levels", {}),
                            kit=m.get("kit", {}) | ({"answer": m["second"]} if "second" in m else {}))
    score, steps, under = arrange(st)
    bad = pieces.clashes(score, under) + [(int(s), note) for s, _, note, _ in score.get("answer", []) for v in under[int(s)][0] if (note - midi(v)) % 12 == 1]
    if bad:
        raise SystemExit(f"{m['title']}: notes clash with their chord: {bad}")
    parts = mixcheck.stems(st, arrange)
    lines = []
    wrong = mixcheck.check(parts, lines.append)
    x = mixcheck.bus(parts)
    y, _ = master.master(x, "day")                           # the game's level for music: -20 LUFS, true peak under -1 dB
    with wave.open(str(OUT / f"menu_{m['id']}.wav"), "wb") as w:
        w.setnchannels(2), w.setsampwidth(2), w.setframerate(pieces.SR)
        w.writeframes((np.clip(y, -1, 1).T * 32767).astype(np.int16).tobytes())
    print(f"\n== {m['title']}  {x.shape[1] / pieces.SR:.1f} s\n" + "\n".join(lines) + f"\n   out of range: {wrong or 'nothing'}", flush=True)
    sounds = {k: m[k].split("/")[-1] for k in ("lead", "second", "double", "chords", "pad", "bass_sound") if k in m}
    return dict(id=m["id"], title=m["title"], key=m["key"], feel=m["feel"], bpm=m["bpm"], meter="3/4" if m.get("spb") == 12 else "4/4",
                seconds=round(x.shape[1] / pieces.SR, 1), lufs=round(master.lufs(y), 1), sounds=sounds, out_of_range=wrong)


if __name__ == "__main__":
    from multiprocessing import get_context
    todo = [m for m in MENU if not sys.argv[1:] or m["id"] in sys.argv[1:]]
    with get_context("spawn").Pool(5) as pool:
        done = {d["id"]: d for d in pool.map(render, todo)}
    old = {d["id"]: d for d in json.loads((OUT / "menu.json").read_text())} if (OUT / "menu.json").exists() else {}
    (OUT / "menu.json").write_text(json.dumps([(old | done)[m["id"]] for m in MENU if m["id"] in old | done], indent=1))
