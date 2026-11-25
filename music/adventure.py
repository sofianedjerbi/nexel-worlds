"""Trailblazer, the adventure piece: by day, while you sail or are far from your bed (audio.js `farFromHome`, role
`adventure`). Played by pieces.py's engine, from its own script so that adding it renders it alone (music/renders.py
fingerprints a script's code: a new score in pieces.py would render every approved piece again).

How it came (2026-11-24/25, ~/nexel/local/music/gaps.html): round 1 (caves, sea, dusk, threat, win) refused; a Wind
Waker-like shanty: "wrong notes" (the sounds were out of tune: their loudest partial a third or a fifth off, or 25-30
cents out), then "off-rythm, repetitive" (a held note on an off-beat; the same four notes every bar), then "too much
like side streets... i want a different feeling". Three new feelings; this one picked: "Trailblazer is good but some
notes sound off". Those were a held C# over D and F# over G (a major seventh on the root), and the engine's bass
leading into every bar from a semitone below (A#, D#, G#, C#: outside E minor). Now every held note is a chord tone and
the bass stays on roots and octaves; nothing in any part is outside the key (`audit`).

E minor, 132. ONE cell: two eighths on 1, a quarter on 2, a held note on 3: a note twice, up a fourth, down a step;
its pitches follow the chord. A held synth lead (no day piece has one), doubled an octave below the second time.
Four bars of drums, bass and chords, then A A B A of eight bars. Every sound passed surge.timing and a tuning check
(within 12 cents, loudest partial at the octave, under 10 ms late, no echo).

    uv run --no-project --python 3.11 --with dawdreamer --with numpy python music/adventure.py
"""
import json
import sys

import pieces
from directions import midi

VT = {"Em9": "G3 B3 D4 F#4", "Cmaj9": "E3 G3 B3 D4", "D6": "F#3 A3 B3 D4", "Bsus": "A3 E4 F#4", "Am9": "G3 C4 E4", "Gmaj9": "F#3 A3 B3 D4"}
RT = {"Em9": "E2", "Cmaj9": "C3", "D6": "D3", "Bsus": "B2", "Am9": "A2", "Gmaj9": "G2"}
_E, _C = ("cell", "B4 B4 E5 D5"), ("cell", "E5 E5 A5 G5")          # (over D6 and Gmaj9 the cell is the Em9 bar's)
_A = [_E, _C, _E, ("cadence", "F#5 E5"), _E, _C, _E, ("cadence", "D5 B4")]
_B = [_C, _E, _E, ("cadence", "F#5 E5"), _C, _E, _C, ("cadence", "D5 B4")]
_HA = ["Em9", "Cmaj9", "D6", "Bsus"] * 2
_HB = ["Am9", "D6", "Gmaj9", "Bsus", "Am9", "D6", "Cmaj9", "Bsus"]
pieces.SCORES["trail"] = dict(H=["Em9", "Cmaj9", "D6", "Bsus"] + _HA * 2 + _HB + _HA, V=VT, R=RT,
                              T=[[]] * 4 + pieces.tune([(0, 2), (2, 2), (4, 3), (8, 3)], [(0, 3), (4, 8)], _A * 2 + _B + _A))
KEY = {4, 6, 7, 9, 11, 0, 2}                                          # E natural minor

PIECES = [
    dict(id="trail", title="Trailblazer (adventure)", score="trail", bpm=132, intro=4, drums="chase", bass="drive", comp="stab5", sync=True,
         levels={"lead": -19, "double": -27, "hat": -31, "open": -33}, lead="Leads/Butter", double="Leads/Fundament", double_shift=-12,
         chords="Polysynths/Simplistic", pad="Polysynths/Jupiter-8", bass_sound="Basses/Bass 2",
         about="the adventure piece: 132, E minor, a held synth lead, a kick on every beat, eighth-note bass; four bars in, then A A B A"),
]
_engine = pieces.side_street


def arrange(st):
    """The engine's arrangement, with its drive bass in eighths to the end of each chord: no note into the next root
    from a semitone below (made for Side street's jazz; in a minor key it falls outside the key)."""
    p, steps, under = _engine(st)
    if st.get("score") != "trail":
        return p, steps, under
    H, R = (pieces.SCORES["trail"][k] for k in "HR")
    p["bass"] = [(16 * b + s, 1.6, midi(R[ch]) + (12 if s % 4 == 2 else 0), 106 if s % 8 == 0 else 90) for b, ch in enumerate(H) for s in range(0, 16, 2)]
    return p, steps, under


pieces.side_street = arrange


def audit(st):
    """What "sounds off" was: tune notes that clash, held notes a major seventh above a note under them, any note
    outside the key, three steps in a row one way."""
    sc, steps, under = arrange(st)
    held7 = sorted({s // 16 for s, ln, m, _ in sc["lead"] for n in under[s % steps][0] if ln >= 3 and (m - midi(n)) % 12 == 11})
    off = sorted({m % 12 for part in ("bass", "lead", "double", "chords", "pad") for _, _, m, _ in sc.get(part, [])} - KEY)
    line = [m for _, _, m, _ in sc["lead"]]; line += line[:2]
    stairs = [line[i:i + 3] for i in range(len(line) - 2) if 0 < abs(line[i + 1] - line[i]) <= 2 and 0 < abs(line[i + 2] - line[i + 1]) <= 2
              and (line[i + 1] - line[i]) * (line[i + 2] - line[i + 1]) > 0]
    return dict(clashes=pieces.clashes(sc, under), held_sevenths=held7, outside_key=off, staircases=stairs)


if __name__ == "__main__":
    for p in PIECES:
        if sys.argv[1:] and p["id"] not in sys.argv[1:]:
            continue
        bad = {k: v for k, v in audit(pieces.BASE | p).items() if v}
        if bad:
            raise SystemExit(f"{p['title']}: {bad}")
        print(json.dumps(pieces.render(p)))
