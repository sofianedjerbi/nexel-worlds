"""Sugar rush, the boss cut: Nyxwing's fight. "improve sugar rush song to make it longer and more intense / epic (deep)".

The kept tune and chords of Sugar rush (menu.LATER, 156 BPM, E flat), note for note, set in a fight's form. What makes
it longer: six sections, 72 bars (111 s) instead of 32 (49 s). What makes it epic: a choir and a brass section over the
synths, the lead doubled by the brass an octave under and by a pluck an octave over. What makes it deep: a sub bass an
octave under the bass, toms, and a middle in C minor (the same notes, the relative minor's chords).
  rise    (8)  choir and sub on C minor, toms closing in, a snare roll
  fight   (16) Sugar rush as kept
  fight+  (16) the brass under the lead, the sub, sixteenth hats, a crash every eight bars
  break   (8)  C minor: no beat but one kick a bar, the choir in front, the tune played softly
  build   (8)  a kick on every beat, a snare roll from quarters to sixteenths, then two beats of silence
  rage    (16) everything: lead, brass, pluck over, choir, toms at the end of every fourth bar, a crash every four
It loops: the rise follows the rage. Beat 1 of bar 1 is at 0 s.

    uv run --no-project --python 3.11 --with dawdreamer --with numpy python music/rush.py [out.wav]
"""
import json
import sys
import wave

import numpy as np

import master
import menu
import mixcheck
import pieces
import surge
from directions import midi

SUGAR = next(m for m in menu.LATER if m["id"] == "sugar")
ACC = pieces.ACC
MINOR = ["Cm9", "Gm7", "Abmaj9", "Gm7", "Cm9", "Gm7", "Fm9", "Abmaj9"]                # the break: the relative minor's own cycle, the kept voicings
SECTIONS = [("rise", 8), ("fight", 16), ("fight+", 16), ("break", 8), ("build", 8), ("rage", 16)]
# Every added sound measured on the beat (surge.timing at 156 BPM, ms to half its peak): Main Brass 2, Brass N4 -1,
# Sub 3 0. The first choice for the brass (Big Brass) spoke 90 ms late, nearly a sixteenth (96 ms), and was heard as
# off the beat: "the deeper tone under the lead sounds off-rythm and ugly". ON_TIME refuses such a sound before rendering.
SOUNDS = dict(choir="Pads/Synth Choir MW O-Ah", brass="Damon Armani/Plucks/Main Brass", sub="Basses/Sub 3", over="Damon Armani/Plucks/Brass N4")
# The doubles sit under the lead, not beside it: the octave below 8 dB down, the octave above 10 dB down.
LEVELS = menu.LEVELS | {"choir": -23, "brass": -23, "sub": -20, "over": -25, "tom": -19, "crash": -24, "hat": -31, "open": -29}
ON_TIME = 15                                                    # ms: the most a rhythmic part may take to speak
SLOW_OK = ("pad", "choir")                                      # held chords may swell in


def arrange(st):
    s = SUGAR
    p = {k: [] for k in ("lead", "over", "brass", "answer", "chords", "pad", "choir", "bass", "sub", "kick", "snare", "clap", "hat", "open", "tom", "crash")}
    under, bar0 = {}, 0
    shapes = {"cell": s["cell"], "cadence": s["cadence"]}

    def hit(part, at, vel, note=None, ln=1):
        p[part].append((at, ln, note or (48 if part == "kick" else 60), vel))

    def tune(s0, i, parts, vel=1.0):
        kind, notes = s["tune"][i % 32]
        for (st_, ln), note in zip(shapes[kind], notes.split()):
            for part, up, v in parts:
                p[part].append((s0 + st_, ln, midi(note) + up, v * vel * ACC[st_ % 16]))
        return kind

    for name, n in SECTIONS:
        for b in range(n):
            s0, last = 16 * (bar0 + b), b == n - 1
            if name == "rise":
                ch = "Cm9" if b < 4 else ("Abmaj9" if b < 6 else "Bb13")
            elif name == "break":
                ch = MINOR[b]
            elif name == "build":
                ch = ("Abmaj9", "Bb13")[b % 2]
            else:
                ch = s["H"][b % 32]
            voice, root = s["V"][ch].split(), s["R"][ch]
            for k in range(16):
                under[s0 + k] = (voice + [root], ch)
            fight = name in ("fight", "fight+", "rage")
            # tune
            if fight:
                parts = [("lead", 0, 100)] + ([("brass", -12, 92)] if name != "fight" else []) + ([("over", 12, 78)] if name == "rage" else [])
                if tune(s0, b, parts) == "cell":
                    p["answer"] += [(s0 + a, ln, midi(nt), 92 if name != "fight" else 86) for a, ln, nt in s["answer"]]
            elif name == "break" and b % 2 == 1:
                tune(s0, 4 * (b // 2) + 3, [("lead", 0, 70)])        # the four cadences only, softly, one every other bar
            elif name == "build":
                tune(s0, 0, [("lead", 0, 64 + 5 * b)] + ([("brass", -12, 60 + 6 * b)] if b >= 4 else []))   # the cell, again and again, rising
            # harmony
            if fight or name == "build":
                for a, ln in s["comp"]:
                    p["chords"] += [(s0 + a, ln, midi(v), (80 - 3 * i) * ACC[a]) for i, v in enumerate(voice)]
            if name in ("rise", "fight+", "break", "rage"):
                p["pad"] += [(s0, 16, midi(v) + 12, 70) for v in voice[-3:]]
            if name in ("rise", "break", "rage") or (name == "fight+" and b >= 8):
                p["choir"] += [(s0, 16, midi(v) + 12, 72 if name == "rage" else 64) for v in voice[-3:]]
            # bass
            if fight or name == "build":
                p["bass"] += [(s0 + a, ln, midi(root) + up, vel) for a, ln, up, vel in s["bass"]]
            elif name == "break":
                p["bass"] += [(s0, 14, midi(root), 96)]
            # the sub: an octave under the bass, on the bass's own root notes and with its rhythm, so it moves with the
            # kick instead of holding through it; in the rise and the break, where the bass holds, it holds too
            if name in ("fight+", "rage", "build"):
                p["sub"] += [(s0 + a, ln, midi(root) - 12, vel) for a, ln, up, vel in s["bass"] if up == 0]
            elif name in ("rise", "break"):
                p["sub"] += [(s0, 14, midi(root) - 12, 96)]
            # drums
            if name == "rise":
                if b < 4:
                    hit("tom", s0, 96, 52), hit("tom", s0 + 8, 84, 52)
                elif b < 6:
                    for a in (0, 4, 8, 12):
                        hit("tom", s0 + a, 88 + 2 * a, (52, 55, 57, 60)[a // 4])
                else:
                    for a in range(0, 16, 2 if b == 6 else 1):
                        hit("snare", s0 + a, 56 + 3 * a + 12 * (b - 6))
                hit("kick", s0, 110)
            elif fight:
                beat = s["beat"]
                for part in ("kick", "snare", "clap", "open"):
                    for a, v in beat[part]:
                        hit(part, s0 + a, v)
                if name != "fight":
                    for a in range(16):
                        hit("hat", s0 + a, 72 * ACC[a])
                if b % 8 == 7:
                    for a, v in s["fill"]["snare"]:
                        hit("snare", s0 + a, v)
                every = 4 if name == "rage" else 8
                if b % every == 0:
                    hit("crash", s0, 104 if b == 0 else 90, ln=8)
                if name == "rage" and b % 4 == 3:
                    for a, t in zip((12, 13, 14, 15), (60, 57, 55, 52)):
                        hit("tom", s0 + a, 100, t)
            elif name == "break":
                hit("kick", s0, 100)
                if b == 0:
                    hit("crash", s0, 96, ln=8)
            elif name == "build":
                for a in (0, 4, 8, 12):
                    if not (last and a >= 8):
                        hit("kick", s0 + a, 96 + b * 2)
                step = 4 if b < 4 else (2 if b < 6 else 1)
                for a in range(0, 8 if last else 16, step):
                    hit("snare", s0 + a, 60 + 5 * b + a)
        bar0 += n
    p = {k: [(a, ln, m + SUGAR.get("shift", {}).get(k, 0), v) for a, ln, m, v in notes] for k, notes in p.items() if notes}
    return p, 16 * bar0, under


def render(out):
    s = SUGAR
    pieces.DUCK = pieces.DUCK | {"sub": 0.45, "choir": 0.3, "brass": 0.15}
    st = pieces.BASE | dict(id="rush", bpm=s["bpm"], sync=True, levels=LEVELS, lead=s["lead"], chords=s["chords"], pad=s["pad"],
                            bass_sound=s["bass_sound"], kit=s["kit"] | SOUNDS | {"answer": s["second"]})
    score, steps, under = arrange(st)
    sounds = pieces.KIT | st["kit"] | {"lead": st["lead"], "chords": st["chords"], "pad": st["pad"], "bass": st["bass_sound"]}
    for part, notes in score.items():
        if part in SLOW_OK:
            continue
        note = int(np.median([m for _, _, m, _ in notes]))
        t = surge.timing(sounds[part], s["bpm"], note)
        echoes = [e for e in t["echoes"] if e[1] * 15 / s["bpm"] > .13]   # a repeat after the 120 ms test note ends (a bump inside it is its body)
        if t["late_ms"] > ON_TIME or echoes:
            raise SystemExit(f"the {part} ({sounds[part]}) is not on the beat: {t}")
    bad = pieces.clashes(score, under)
    if bad:
        raise SystemExit(f"notes clash with their chord: {bad[:12]}")
    parts = mixcheck.stems(st, arrange)
    wrong = mixcheck.check(parts)
    print("out of the kept pieces' range:", wrong or "nothing")
    y, _ = master.master(mixcheck.bus(parts), "day")
    with wave.open(str(out), "wb") as w:
        w.setnchannels(2), w.setsampwidth(2), w.setframerate(pieces.SR)
        w.writeframes((np.clip(y, -1, 1).T * 32767).astype(np.int16).tobytes())
    t, secs = 0.0, []
    for name, n in SECTIONS:
        secs.append(dict(name=name, t=round(t, 3), bars=n))
        t += n * 4 * 60 / s["bpm"]
    print(json.dumps(dict(seconds=round(y.shape[1] / pieces.SR, 2), lufs=round(master.lufs(y), 1), sections=secs)))


if __name__ == "__main__":
    render(sys.argv[1] if sys.argv[1:] else pieces.OUT / "boss_rush.wav")
