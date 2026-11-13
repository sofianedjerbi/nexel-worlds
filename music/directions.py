"""Five short pieces in five different directions, all on Surge XT factory sounds (music/surge.py), to find out which
direction is worth pursuing before writing anything long. Everything differs from the earlier music on purpose: the
rhythms (no shuffle with a bouncing bass), the sounds (a synthesizer played as a synthesizer, nothing imitating a
guitar or a flute), the tone (the top is left in).

    uv run --no-project --python 3.11 --with dawdreamer --with numpy python music/directions.py
"""
from pathlib import Path
import json
import wave

import numpy as np

import surge

SR = surge.SR
OUT = Path(__file__).with_name("site") / "audio"
PC = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
rng = np.random.default_rng(5)


def midi(name):
    pc, rest = PC[name[0]], name[1:]
    while rest[0] in "#b":
        pc += 1 if rest[0] == "#" else -1
        rest = rest[1:]
    return 12 * (int(rest) + 1) + pc


def hits(pattern, note, vel=100, length=0.5, accents=None):
    """'x...x...' (16 steps a bar, any number of bars) -> [(step, steps long, note, velocity)]; 'o' is a soft hit."""
    return [(i, length, note, vel if c == "x" else int(vel * 0.55)) for i, c in enumerate(pattern.replace(" ", "")) if c in "xo"]


def chords(bars, rhythm, voicings, vel=84):
    """Each bar's chord struck on the steps of `rhythm` [(step, steps long)], all its notes together."""
    return [(16 * b + s, ln, midi(n), vel - 5 * j) for b, ch in enumerate(bars) for s, ln in rhythm for j, n in enumerate(voicings[ch])]


PIECES = [
    dict(id="tape", title="Tape keys", bpm=76, swing=0.56, mood="lo-fi: soft keys on tape, lazy drums, a round bass",
         parts=[
             ("keys", "Cybersoda/Keys/Tape Keys", -19, chords(["Bb", "Am", "Gm", "C"] * 2, [(0, 5), (6, 3), (11, 4)],
                                                             {"Bb": ["Bb3", "D4", "F4", "A4"], "Am": ["A3", "C4", "E4", "G4"], "Gm": ["G3", "Bb3", "D4", "F4"], "C": ["Bb3", "D4", "E4", "G4"]})),
             ("bass", "Basses/Mellow", -17, [(16 * b + s, ln, midi(n), 96) for b, n in enumerate(["Bb1", "A1", "G1", "C2"] * 2) for s, ln in ((0, 5), (10, 2), (12, 3))]),
             ("kick", "Altenberg/Drums/Kick Lo-Fi", -15, hits("x.....x...x....." * 8, 48)),
             ("snare", "Cybersoda/Drums/Old Snare", -19, hits("....x.......x..o" * 8, 60)),
             ("hat", "Cybersoda/Drums/Old Hat", -27, hits("x.o.x.o.x.o.x.oo" * 8, 60, 90)),
             ("lead", "Plucks/Lo-Fi Pluck", -17, [(16 * b + s, ln, midi(n), 92) for b, bar in enumerate(
                 [[(2, 2, "A4"), (4, 3, "C5"), (8, 2, "A4"), (11, 5, "G4")], [(2, 2, "A4"), (4, 3, "C5"), (8, 2, "D5"), (11, 5, "C5")],
                  [(2, 2, "G4"), (4, 3, "Bb4"), (8, 2, "D5"), (11, 5, "Bb4")], [(2, 2, "G4"), (4, 3, "A4"), (8, 2, "G4"), (11, 5, "E4")]] * 2) for s, ln, n in bar]),
         ]),
    dict(id="pads", title="Warm pads", bpm=64, swing=0.5, mood="ambient: three chords, no drums, one small figure repeated exactly",
         parts=[
             ("pad", "Bluelight/Pads/Another Warm", -20, chords(["C", "Am", "F", "F"] * 2, [(0, 16)],
                                                                {"C": ["C3", "G3", "E4"], "Am": ["A2", "E3", "C4"], "F": ["F2", "C3", "A3"]}, 70)),
             ("air", "Pads/Winter Warmer", -27, chords(["C", "Am", "F", "F"] * 2, [(0, 16)], {"C": ["G4", "C5"], "Am": ["E4", "C5"], "F": ["F4", "C5"]}, 60)),
             ("bass", "Basses/Sub 1", -19, [(16 * b, 15, midi(n), 90) for b, n in enumerate(["C2", "A1", "F1", "F1"] * 2)]),
             ("keys", "Vospi/Keys/The Softest", -16, [(16 * b + s, ln, midi(n), 86) for b in range(8) for s, ln, n in
                                                       ([(0, 3, "E4"), (3, 3, "G4"), (8, 6, "C5")] if b % 2 == 0 else [(2, 4, "B4"), (8, 8, "G4")])]),
         ]),
    dict(id="poly", title="Analog poly", bpm=100, swing=0.5, mood="synthwave, mellow: a steady kick, eighth-note bass, analog chords, a singing lead",
         parts=[
             ("stabs", "Polysynths/Jupiter-8", -19, chords(["Am", "F", "C", "G"] * 2, [(0, 3), (3, 3), (6, 4), (10, 2), (12, 4)],
                                                           {"Am": ["A3", "C4", "E4"], "F": ["A3", "C4", "F4"], "C": ["G3", "C4", "E4"], "G": ["G3", "B3", "D4"]}, 88)),
             ("pad", "Polysynths/Juno-60 Strings", -25, chords(["Am", "F", "C", "G"] * 2, [(0, 16)], {"Am": ["E4", "A4"], "F": ["F4", "A4"], "C": ["E4", "G4"], "G": ["D4", "G4"]}, 70)),
             ("bass", "Basses/Bass 1", -17, [(16 * b + s, 1.6, midi(n), 100 if s % 4 == 0 else 84) for b, n in enumerate(["A1", "F1", "C2", "G1"] * 2) for s in range(0, 16, 2)]),
             ("kick", "TNMG/Drums/Kick - Classic", -14, hits("x...x...x...x..." * 8, 48)),
             ("snare", "TNMG/Drums/Snare - Classic", -19, hits("....x.......x..." * 8, 60)),
             ("hat", "Emu/Drums/Hat Closed", -27, hits("..x...x...x...xo" * 8, 60, 92)),
             ("lead", "Leads/Smoothy Hollow", -17, [(16 * b + s, ln, midi(n), 96) for b, bar in enumerate(
                 [[(0, 6, "E5"), (6, 2, "D5"), (8, 6, "C5")], [(0, 6, "A4"), (8, 4, "C5"), (12, 4, "D5")],
                  [(0, 6, "E5"), (6, 2, "G5"), (8, 6, "E5")], [(0, 6, "D5"), (8, 8, "B4")]] * 2) for s, ln, n in bar]),
         ]),
    dict(id="wurli", title="Wurli groove", bpm=88, swing=0.5, mood="laid-back funk: an electric piano comping off the beat, a fingered bass that moves, tight drums",
         parts=[
             ("keys", "Cybersoda/Keys/Wurli", -18, chords(["D", "Bm", "G", "A"] * 2, [(0, 2), (3, 1), (6, 2), (10, 1), (13, 2)],
                                                          {"D": ["F#3", "A3", "C#4", "E4"], "Bm": ["F#3", "A3", "B3", "D4"], "G": ["F#3", "A3", "B3", "D4"], "A": ["G3", "B3", "D4", "E4"]}, 90)),
             ("bass", "Basses/Fingered", -16, [(16 * b + s, ln, midi(r) + o, v) for b, r in enumerate(["D2", "B1", "G1", "A1"] * 2)
                                                for s, ln, o, v in ((0, 2, 0, 104), (3, 1, 0, 80), (6, 1, 12, 92), (8, 2, 0, 100), (11, 1, 7, 84), (14, 1, 12, 90))]),
             ("kick", "Cybersoda/Drums/Acoustic Kick", -15, hits("x..x......x..x.." * 8, 48)),
             ("snare", "Cybersoda/Drums/Acoustic Snare", -18, hits("....x..o....x..." * 8, 60)),
             ("hat", "Cybersoda/Drums/Acoustic HiHat", -27, hits("xoxoxoxoxoxoxoxo" * 8, 60, 88)),
             ("lead", "Cybersoda/Brass/Soft 80s Brass", -19, [(16 * b + s, ln, midi(n), 92) for b, bar in enumerate(
                 [[(4, 2, "F#4"), (6, 2, "A4"), (9, 5, "E5")], [(4, 2, "F#4"), (6, 2, "A4"), (9, 5, "D5")],
                  [(4, 2, "D4"), (6, 2, "G4"), (9, 5, "B4")], [(4, 2, "E4"), (6, 2, "A4"), (9, 3, "C#5"), (13, 3, "B4")]] * 2) for s, ln, n in bar]),
         ]),
    dict(id="dream", title="Dream plucks", bpm=108, swing=0.5, mood="bright and light: plucks that bounce, a soft pad, a rubber bass, small drums",
         parts=[
             ("pluck", "Nick Moritz/Keys/Dream Plucks", -16, [(16 * b + s, ln, midi(n), 96) for b, bar in enumerate(
                 [[(0, 2, "B4"), (3, 2, "D5"), (6, 2, "B4"), (10, 2, "G4"), (12, 4, "D5")], [(0, 2, "A4"), (3, 2, "D5"), (6, 2, "A4"), (10, 2, "F#4"), (12, 4, "D5")],
                  [(0, 2, "G4"), (3, 2, "B4"), (6, 2, "G4"), (10, 2, "E4"), (12, 4, "B4")], [(0, 2, "G4"), (3, 2, "C5"), (6, 2, "E5"), (10, 6, "D5")]] * 2) for s, ln, n in bar]),
             ("chords", "Plucks/Nice Pluck 1", -22, chords(["G", "D", "Em", "C"] * 2, [(2, 2), (8, 2), (14, 2)],
                                                            {"G": ["G3", "B3", "D4"], "D": ["F#3", "A3", "D4"], "Em": ["G3", "B3", "E4"], "C": ["G3", "C4", "E4"]}, 80)),
             ("pad", "Databroth/Pads/Warmbo", -25, chords(["G", "D", "Em", "C"] * 2, [(0, 16)], {"G": ["D4", "G4"], "D": ["D4", "F#4"], "Em": ["E4", "G4"], "C": ["E4", "G4"]}, 66)),
             ("bass", "Basses/Rubber Bass", -17, [(16 * b + s, ln, midi(n), 98) for b, n in enumerate(["G1", "F#1", "E1", "C2"] * 2) for s, ln in ((0, 3), (6, 2), (10, 2), (13, 2))]),
             ("kick", "Vospi/Drums/Proper Kick", -15, hits("x.....x..x......" * 8, 48)),
             ("snare", "Vospi/Drums/Simple Snare", -20, hits("....x.......x..." * 8, 60)),
             ("hat", "Malfunction/Drums/Hi-Hat", -28, hits("..x...x...x.x.x." * 8, 60, 90)),
         ]),
]


def render(piece):
    step = 60 / piece["bpm"] / 4
    bars = 8
    n = int(round(bars * 16 * step * SR))
    mix, stems, quiet = np.zeros((2, n)), {}, {}
    for name, sound, level, notes in piece["parts"]:
        ev = []
        for s, ln, m, vel in notes:
            late = (piece["swing"] - 0.5) * 2 * step if int(s) % 2 else 0.0            # swing: the off sixteenths come late
            human = 0.0 if name in ("kick", "bass") else abs(rng.normal(0, 0.006))
            ev.append((m, vel * (1 + rng.normal(0, 0.05)), s * step + late + human, ln * step * 0.95))
        y = surge.play(sound, ev, n / SR + 6.0)
        y = y[:, :n] + np.pad(y[:, n:2 * n], ((0, 0), (0, max(0, 2 * n - y.shape[1]))))[:, :n]      # what rings past the end comes back at the start: a loop
        rms = np.sqrt((y ** 2).mean()) + 1e-12
        if rms < 1e-4:
            raise SystemExit(f"{piece['title']}: {sound} is silent on these notes")
        level -= 3 if name in ("kick", "bass") else 0          # (the first render had as much under 60 Hz as in the whole midrange)
        Y = np.fft.rfft(y, axis=1)
        y = np.fft.irfft(Y / np.sqrt(1 + (35 / np.maximum(np.fft.rfftfreq(n, 1 / SR), 1e-3)) ** 4), n, axis=1)       # nothing useful under 35 Hz
        quiet[name] = round(float(20 * np.log10(rms)), 1)
        stems[name] = y * 10 ** (level / 20) / rms
        mix += stems[name]
    mix *= 10 ** (-17 / 20) / np.sqrt((mix ** 2).mean())
    env = np.abs(mix).max(axis=0)
    win = 240
    peak = np.array([env[max(0, i - win): i + win].max() for i in range(0, n, 48)])
    gain = np.interp(np.arange(n), np.arange(0, n, 48), np.minimum(1.0, 0.89 / np.maximum(peak, 1e-9)))
    gain = np.convolve(np.pad(gain, 240, mode="edge"), np.ones(481) / 481, "valid")
    mix = np.clip(mix * gain, -0.95, 0.95)
    with wave.open(str(OUT / f"dir_{piece['id']}.wav"), "wb") as w:
        w.setnchannels(2), w.setsampwidth(2), w.setframerate(SR)
        w.writeframes((mix.T * 32767).astype(np.int16).tobytes())
    S = np.abs(np.fft.rfft(mix.mean(axis=0))) ** 2
    fr = np.fft.rfftfreq(n, 1 / SR)
    share = {k: round(float(10 * np.log10(S[(fr >= lo) & (fr < hi)].sum() / S.sum() + 1e-12)), 1) for k, lo, hi in
             (("under 60", 0, 60), ("60-250", 60, 250), ("250-1k", 250, 1000), ("1-4k", 1000, 4000), ("over 4k", 4000, 24000))}
    print(f"{piece['title']:14s} {n / SR:5.1f} s  peak {np.abs(mix).max():.2f}  limiter worked {100 * (gain < 0.99).mean():.0f}% of the time  {share}\n   raw levels {quiet}", flush=True)
    return dict(id=piece["id"], title=piece["title"], bpm=piece["bpm"], seconds=round(n / SR, 1), mood=piece["mood"],
                sounds=", ".join(s.split("/")[-1] for _, s, _, _ in piece["parts"]))


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "directions.json").write_text(json.dumps([render(p) for p in PIECES], indent=1))
