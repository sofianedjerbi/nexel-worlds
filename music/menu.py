"""Five candidates for the first screen's music: "5 music for the start menu with their unique theme. cute and fast".

What the reading says a menu theme is for (sources on the page, local/music/menu.html): it is the appetizer, it says the
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


# "keep sugar rush somewhere for later its pretty good. but does not fit main menu"; "sugar rush was too fast. it fit
# well a high energy moment not a menu". Kept as site/audio/keep_sugar_rush.wav; the four of the third round, kept
# too ("great ideas but they do not fit main menu"), as site/audio/keep_menu_<id>.wav. None is rendered again.
LATER = [
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
    dict(id="mat", title="Welcome mat", key="A major", feel="a bounce: the bass hops between octaves, short chords off the beat; the lead calls, a second pluck answers", bpm=120, passes=1,
         H=["A69", "F#m7", "Dmaj9", "E13", "A69", "F#m7", "Dmaj9", "E13 A69"] * 2,
         V={"A69": "F#3 B3 C#4 E4", "F#m7": "E3 A3 C#4", "Dmaj9": "F#3 A3 C#4 E4", "E13": "D3 G#3 C#4"},
         R={"A69": "A2", "F#m7": "F#2", "Dmaj9": "D3", "E13": "E2"},
         cell=[(0, 2), (4, 2), (6, 2), (10, 2)], cadence=[(0, 4), (4, 4), (8, 8)],          # down a third and back, then the drop to the keynote
         tune=(bars("E5 C#5 E5 A4") + [("cadence", "B4 G#4 E5")] + bars("E5 C#5 E5 A4") + [("cadence", "B4 G#4 A4")]) * 2,
         answer=[(12, 2, "C#5"), (14, 2, "E5")],
         comp=[(2, 2), (6, 2), (10, 2), (14, 2)], bass=[(0, 3, 0, 104), (4, 2, 12, 88), (8, 3, 0, 96), (12, 2, 12, 88)],
         beat=dict(kick=[(0, 104), (10, 92)], clap=[(4, 84), (12, 90)], hat=[(s, 84) for s in range(0, 16, 2)]), fill=dict(snare=[(13, 70), (15, 88)]),
         lead="Giana Brotherz/Keys/Table Morph", second="Polysynths/Metal Chonk", chords="Giana Brotherz/Keys/Harmonic Ring", pad="Polysynths/Xpander 1",
         bass_sound="Luna/Basses/Synthwave", shift={"lead": -12, "answer": 12, "pad": 12}),
    dict(id="porch", title="Porch light", key="E major", feel="a light shuffle: the bass walks root and fifth, the chords are held", bpm=112, swing=0.58, passes=1,
         H=["Emaj9", "G#m7", "Amaj9", "B13", "C#m9", "G#m7", "Amaj9 B13", "E69"] * 2,
         V={"Emaj9": "G#3 B3 D#4 F#4", "G#m7": "F#3 B3 D#4", "Amaj9": "G#3 B3 C#4 E4", "B13": "A3 D#4 G#4", "C#m9": "E3 G#3 B3 D#4", "E69": "G#3 B3 C#4 F#4"},
         R={"Emaj9": "E2", "G#m7": "G#2", "Amaj9": "A2", "B13": "B2", "C#m9": "C#3", "E69": "E2"},
         cell=[(0, 2), (2, 2), (6, 4), (12, 3)], cadence=[(0, 3), (3, 3), (6, 10)],         # one note knocked twice, down a third, back
         tune=(bars("B4 B4 G#4 B4") + [("cadence", "F#5 F#5 D#5")] + bars("B4 B4 G#4 B4") + [("cadence", "B4 B4 E5")]) * 2,
         comp=[(0, 3), (6, 2), (11, 2)], bass=[(0, 3.5, 0, 104), (8, 3.5, 7, 92)],
         beat=dict(kick=[(0, 100), (8, 90)], clap=[(4, 86), (12, 90)], hat=[(s, 84) for s in range(0, 16, 2)], click=[(6, 70), (14, 74)]), fill=dict(snare=[(14, 86)]),
         lead="Plucks/Man Machine", chords="Jacky Ligon/Keys/Midnightly", pad="Polysynths/Korg Triton", bass_sound="Giana Brotherz/Basses/Tech Cabinet", shift={"pad": 12}),
    dict(id="jam", title="Jam jar", key="C major", feel="half time: one kick, one clap a bar under quick hats; the lead calls, a second pluck answers", bpm=126, passes=1,
         H=["Fmaj9", "Em7", "Dm9", "G13", "Fmaj9", "Em7", "G13", "C69"] * 2,
         V={"Fmaj9": "E3 G3 A3 C4", "Em7": "D3 G3 B3", "Dm9": "F3 A3 C4 E4", "G13": "F3 B3 E4", "C69": "E3 G3 A3 D4"},
         R={"Fmaj9": "F2", "Em7": "E2", "Dm9": "D3", "G13": "G2", "C69": "C3"},
         cell=[(0, 3), (3, 3), (6, 2), (10, 3)], cadence=[(0, 6), (6, 10)],                 # up a third and back, a step down: on the 3+3 of the bar
         tune=(bars("E5 G5 E5 D5") + [("cadence", "B4 D5")] + bars("E5 G5 E5 D5") + [("cadence", "E5 C5")]) * 2,
         answer=[(13, 1, "E5"), (14, 2, "G5")],
         comp=[(0, 2), (3, 2), (6, 2), (11, 2)], bass=[(0, 3, 0, 104), (6, 2, 0, 90), (8, 3, 12, 94), (14, 2, 0, 88)],
         beat=dict(kick=[(0, 106), (14, 86)], clap=[(8, 94)], snare=[(8, 84)], hat=[(s, 84) for s in range(0, 16, 2)]), fill=dict(snare=[(12, 72), (13, 80)]),
         lead="Emu/Keys/SoftSaw", second="Kyurumi/Plucks/Bandpass Pluck", chords="Plucks/80s Gliss", pad="Cybersoda/Pads/Lush",
         bass_sound="Kinsey Dulcet/Basses/Everybody Needs A 303, Really", shift={"answer": -12}),
    dict(id="boat", title="Paper boat", key="G major", feel="a plain backbeat: the lead comes in after the beat, the chords are long", bpm=116, passes=1,
         H=["G69", "Em9", "Cmaj9", "D13", "G69", "Bm7", "Cmaj9 D13", "G69"] * 2,
         V={"G69": "E3 A3 B3 D4", "Em9": "G3 B3 D4 F#4", "Cmaj9": "E3 G3 B3 D4", "D13": "F#3 B3 C4 E4", "Bm7": "A3 D4 F#4"},
         R={"G69": "G2", "Em9": "E2", "Cmaj9": "C3", "D13": "D3", "Bm7": "B2"},
         cell=[(2, 2), (4, 2), (8, 2), (10, 4)], cadence=[(0, 4), (4, 4), (8, 8)],          # late on purpose: twice the same note, a third under, back
         tune=(bars("D5 D5 B4 D5") + [("cadence", "A4 F#4 A4")] + bars("D5 D5 B4 D5") + [("cadence", "A4 B4 G4")]) * 2,
         comp=[(0, 6), (8, 6)], bass=[(0, 3, 0, 104), (4, 3, 0, 90), (8, 3, 0, 98), (12, 3, 7, 90)],
         beat=dict(kick=[(0, 106), (8, 98), (10, 84)], snare=[(4, 92), (12, 96)], hat=[(s, 84) for s in range(0, 16, 2)]), fill=dict(snare=[(14, 80), (15, 90)]),
         levels={"lead": -17}, lead="Nick Moritz/Keys/Angel Pluck", chords="Jacky Ligon/Keys/Fiftyish", pad="Giana Brotherz/Pads/Back Texture", bass_sound="Slowboat/Basses/Happy Bass 2",
         shift={"lead": 12, "pad": -12}),
]

# Third round. "i don't like the other ones.. redesign other ones and audit them". What the one that was liked had and
# the refused ones had not: a lead that is plucked (it dies away under the finger; the refused leads held their note
# and were cut short), and nothing out of the kept pieces' ranges. So: plucked leads only (measured: 14 dB or more
# down after 0.7 s held, as Cute 1 and Rattler are), a menu's pace (112 to 126, no kick on every beat), 16 bars once
# (32 s, the length of the kept day pieces), new tunes, and no sound of a refused piece.
# Fourth round. "keep all the other menu songs, they have great ideas but they do not fit main menu. try a slower more
# chill beat for the welcome menu. ambiant almost". The four above are kept for later (site/audio/keep_menu_<id>.wav).
# Now the manner of the kept night pieces (slow, pads in front, a soft lead with room around it) with a beat so soft it
# is nearly not one: a low kick, a brush or a shaker, no clap, no hat. Held against days and nights together
# (mixcheck "chill"). Three depths of calm, for the user to place the cursor.
SOFT = {"kick": -22, "brush": -27, "shaker": -34, "click": -31, "chords": -20, "pad": -22, "bass": -17, "lead": -15}
MENU = [
    dict(id="window", title="Morning window", key="D major", feel="a slow soft beat: a low kick, a brush on two and four, a shaker; pads in front, a lead of three notes", bpm=80, passes=1, ref="chill", levels=SOFT,
         H=["Dmaj9", "Bm9", "Gmaj9", "A13sus", "Dmaj9", "Bm9", "Gmaj9", "D69"] * 2,
         V={"Dmaj9": "F#3 A3 C#4 E4", "Bm9": "D3 F#3 A3 C#4", "Gmaj9": "F#3 A3 B3 D4", "A13sus": "G3 B3 D4 F#4", "D69": "F#3 B3 E4"},
         R={"Dmaj9": "D3", "Bm9": "B2", "Gmaj9": "G2", "A13sus": "A2", "D69": "D3"},
         cell=[(0, 3), (6, 2), (8, 6)], cadence=[(0, 6), (6, 10)],                           # down a sixth and back up: a slow nod
         tune=(bars("F#5 A4 F#5") + [("cadence", "E5 B4")] + bars("F#5 A4 F#5") + [("cadence", "F#5 D5")]) * 2,
         comp=[(0, 15)], bass=[(0, 9, 0, 100), (10, 5, 0, 84)],
         beat=dict(kick=[(0, 96), (10, 80)], brush=[(4, 80), (12, 86)], shaker=[(s, 60) for s in range(0, 16, 2)]),
         lead="Giana Brotherz/Keys/Sin Ring", chords="Bluelight/Pads/Wool 2", pad="Landosonic/Pads/Washing The Podium 2", bass_sound="Altenberg/Basses/Boog"),
    dict(id="tide", title="Slow tide", key="F major", feel="half time, slower: one low kick and one brush a bar; the lead knocks twice and rises", bpm=72, passes=1, ref="chill", levels=SOFT,
         H=["Fmaj9", "Am7", "Bbmaj9", "C13sus", "Dm9", "Am7", "Bbmaj9", "F69"] * 2,
         V={"Fmaj9": "E3 G3 A3 C4", "Am7": "G3 C4 E4", "Bbmaj9": "A3 C4 D4 F4", "C13sus": "Bb3 D4 F4", "Dm9": "F3 A3 C4 E4", "F69": "A3 D4 G4"},
         R={"Fmaj9": "F2", "Am7": "A2", "Bbmaj9": "Bb2", "C13sus": "C3", "Dm9": "D3", "F69": "F2"},
         cell=[(0, 2), (3, 2), (6, 8)], cadence=[(0, 6), (6, 10)],                           # the same note twice, up a third, held
         tune=(bars("A4 A4 C5") + [("cadence", "D5 G4")] + bars("A4 A4 C5") + [("cadence", "C5 F5")]) * 2,
         comp=[(0, 15)], bass=[(0, 13, 0, 100)],
         beat=dict(kick=[(0, 96)], brush=[(8, 84)], shaker=[(s, 58) for s in range(0, 16, 4)]),
         lead="Jacky Ligon/Keys/Corporealities", chords="Pads/Chowning", pad="LinnStrument MPE/Pads/Warm Pad", bass_sound="Rozzer/Basses/Nu Skool Bass 2"),
    dict(id="still", title="Still water", key="A major", feel="almost ambient: a kick like a heartbeat and a far click, two notes and a long one over still pads", bpm=66, passes=1, ref="chill", levels=SOFT | {"lead": -17, "bass": -15.5, "click": -34},
         H=["A69", "F#m7", "Dmaj9", "E13sus", "A69", "C#m7", "Dmaj9", "A69"] * 2,
         V={"A69": "F#3 B3 C#4 E4", "F#m7": "E3 A3 C#4", "Dmaj9": "F#3 A3 C#4 E4", "E13sus": "D3 F#3 A3 C#4", "C#m7": "E3 G#3 B3"},
         R={"A69": "A2", "F#m7": "F#2", "Dmaj9": "D3", "E13sus": "E2", "C#m7": "C#3"},
         cell=[(0, 4), (8, 8)], cadence=[(0, 16)],                                           # two notes a third apart, then one note for the whole bar
         tune=(bars("E5 C#5") + [("cadence", "B4")] + bars("E5 C#5") + [("cadence", "A4")]) * 2,
         comp=[(0, 15)], bass=[(0, 14, 0, 96)],
         beat=dict(kick=[(0, 90), (6, 70)], click=[(12, 70)]),
         lead="Plucks/Frog", chords="Dan Maurer/Pads/Muted Square Pad", pad="Pads/Sparkly", bass_sound="Basses/Bass 2", shift={"lead": 12}),
]


def arrange(st):
    """The parts of one candidate: the whole score once per pass; from the second pass on the lead is doubled an
    at the same pitch by a second sound. Returns what pieces.side_street() returns."""
    spb, H, n = st.get("spb", 16), st["H"], len(st["H"])
    acc = (lambda s: STRAIGHT[int(s) % 16]) if spb == 16 else (lambda s: WALTZ[int(s) % 12])
    shapes = {"cell": st["cell"], "cadence": st["cadence"]}
    p = {k: [] for k in ("lead", "double", "answer", "chords", "pad", "bass", "kick", "snare", "clap", "hat", "open", "click", "brush", "shaker")}
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


# Against the kept pieces' mix these sparser, slower pieces came out bright on top (hats, claps) and light under 60 Hz.
LEVELS = {"answer": -22, "bass": -16, "hat": -30, "clap": -27, "click": -29}


def render(m):
    """One candidate: its parts alone, the engineer's checks on them (mixcheck), the kept pieces' mix bus, the game's level."""
    st = pieces.BASE | dict(m, id="menu_" + m["id"], sync=True, levels=LEVELS | m.get("levels", {}),
                            kit=m.get("kit", {}) | ({"answer": m["second"]} if "second" in m else {}))
    score, steps, under = arrange(st)
    bad = pieces.clashes(score, under) + [(int(s), note) for s, _, note, _ in score.get("answer", []) for v in under[int(s)][0] if (note - midi(v)) % 12 == 1]
    if bad:
        raise SystemExit(f"{m['title']}: notes clash with their chord: {bad}")
    parts = mixcheck.stems(st, arrange)
    lines = []
    wrong = mixcheck.check(parts, lines.append, m.get("ref", "day"))
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
