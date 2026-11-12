"""Four short sketches for the main theme, to choose from by ear (the assistant cannot hear; two blind tries at a
melody both came out "naive, like the chime of a pharmacy door"). Each is a seamless loop of sixteen bars: the piano
alone, then the same again with pad and bass. Rendered to music/site/audio/sketch_<n>.wav + sketches.json.

    uv run python music/sketches.py

What the two failures had in common, and what every sketch here avoids: a bright major pentatonic tune of even notes that
lands on plain chord notes. So: the melody comes in after the beat, rests on sevenths and ninths, moves little and mostly
down, sits low (around D4-B4), and the harmony has colour (major sevenths, minor sevenths, suspensions).
"""
import json
from pathlib import Path

import numpy as np

import compose as C
from compose import SR, analog_pad, fft_filter, hp, hz, lofi_piano, lp, midi, moog_bass, tt

OUT = Path(__file__).with_name("site") / "audio"
rng = np.random.default_rng(5)


def rows(text):
    """'F#4 2 6, E4 8 3' -> [(note, start beat in the phrase, beats long)]"""
    return [(n, float(a), float(b)) for n, a, b in (x.split() for x in text.split(",") if x.strip())]


# Each sketch: bpm, beats per bar, and per chord of the 8-bar cycle: (bars, left hand notes (one a beat, then ringing), pad notes, bass).
# The melody is written against the whole 8 bars: note, beat it starts on (0 = first beat of bar 1), beats long.
SKETCHES = [
    dict(id=1, name="The earlier melody, lower and softer", bpm=72, beats=4,
         why="The melody you once called perfect (F#, E, F#, A; F#, E, D, E), an octave lower on the softer piano, over its own three chords. A baseline.",
         chords=[(2, "D2 A2 E3 F#3", "D3 A3", "D2"), (2, "G2 D3 A3 B3", "G3 D3", "G1"), (2, "B2 F#3 A3", "B2 F#3", "B1"), (2, "G2 D3 A3 B3", "G3 D3", "G1")],
         melody="F#4 0 2, E4 2 1, F#4 3 1, A4 4 3.5, F#4 8 2, E4 10 1, D4 11 1, E4 12 3.5, F#4 16 2, E4 18 1, F#4 19 1, A4 20 3.5, F#4 24 2, E4 26 1, D4 27 1, D4 28 3.5"),
    dict(id=2, name="Wistful", bpm=66, beats=4,
         why="Each phrase comes in after the beat and hangs on a colour note (the major seventh of G, the seventh of B minor, the ninth of E minor), then steps down. The last chord is left hanging, then resolves by a half step.",
         chords=[(2, "G2 D3 F#3 B3", "G3 D3", "G1"), (2, "B2 F#3 A3", "B2 F#3", "B1"), (2, "E2 B2 D3 G3", "E3 B3", "E2"), (2, "A2 E3 A3", "A2 E3", "A1")],
         melody="F#4 1 3, E4 4 1.5, D4 5.5 2.5, A4 9 3, F#4 12 1.5, D4 13.5 2.5, F#4 17 3, G4 20 1, F#4 21 1, D4 22 2, E4 25 3, D4 28 1.5, C#4 29.5 2.5"),
    dict(id=3, name="Rolling", bpm=76, beats=4,
         why="No tune to speak of: the left hand rolls through open chords without stopping, and now and then two notes sigh on top of it. Closest to the quiet piano pieces of the first Minecraft album.",
         roll=True,
         chords=[(2, "D3 A3 E4 F#4 A4 F#4 E4 A3", "D3 A3", "D2"), (2, "G2 D3 A3 B3 D4 B3 A3 D3", "G3 D3", "G1"),
                 (2, "B2 F#3 A3 D4 F#4 D4 A3 F#3", "B2 F#3", "B1"), (2, "A2 E3 B3 D4 E4 D4 B3 E3", "A2 E3", "A1")],
         melody="B4 4 1.5, A4 5.5 2.5, D5 12 1.5, B4 13.5 2.5, D5 20 1.5, A4 21.5 2.5, B4 28 1.5, E4 29.5 2.5"),
    dict(id=4, name="Slow waltz", bpm=96, beats=3,
         why="Three beats a bar, in B minor turning to D: a low note, then two higher ones, under a melody of long notes. Nearest to Undertale's quiet house and town music.",
         chords=[(2, "B2 F#3 B3", "B2 F#3", "B1"), (2, "G2 D3 B3", "G3 D3", "G1"), (2, "D3 A3 F#3", "D3 A3", "D2"), (2, "A2 E3 A3", "A2 E3", "A1")],
         waltz=True,
         melody="F#4 0 3, D4 3 1, E4 4 1, F#4 5 1, B4 6 2, A4 8 1, F#4 9 3, A4 12 2, F#4 14 1, E4 15 1, F#4 16 1, A4 17 1, E4 18 3, E4 21 2, C#4 23 1"),
]


def events_of(sk):
    """(seconds, instrument, note, seconds long, velocity, pan, reverb send), the cycle played twice."""
    beat, per = 60 / sk["bpm"], sk["beats"]
    ev = []
    for rep in (0, 1):
        t0 = rep * 8 * per * beat
        for n, a, b in rows(sk["melody"]):
            ev.append((t0 + a * beat + 0.012, lofi_piano, n, b * beat, 0.7 if b >= 2 else 0.6, 0.1, 0.32))
        bar = 0
        for bars, left, pad, bass in sk["chords"]:
            notes = left.split()
            for k in range(bars):
                at = t0 + (bar + k) * per * beat
                if sk.get("roll"):                                  # eighths, without stopping
                    for j, n in enumerate(notes):
                        ev.append((at + j * beat / 2, lofi_piano, n, 1.5 * beat, 0.4 if j == 0 else 0.3, -0.25 + 0.06 * j, 0.3))
                elif sk.get("waltz"):                               # low, high, high
                    for j, n in enumerate(notes):
                        ev.append((at + j * beat, lofi_piano, n, (per - j) * beat, 0.42 if j == 0 else 0.3, -0.2 + 0.1 * j, 0.3))
                elif k == 0:                                        # the chord once, a note a beat, left to ring
                    for j, n in enumerate(notes):
                        ev.append((at + j * beat, lofi_piano, n, (bars * per - j) * beat, 0.44 - 0.04 * j, -0.3 + 0.12 * j, 0.32))
            if rep:
                for i, n in enumerate(pad.split()):
                    ev.append((t0 + bar * per * beat, analog_pad, n, bars * per * beat, 0.8, (-0.4, 0.4)[i], 0.35))
                ev.append((t0 + bar * per * beat, moog_bass, bass, (bars * per - 0.25) * beat, 0.8, 0.0, 0.0))
            bar += bars
    return ev, 16 * per * beat


def render(sk):
    ev, seconds = events_of(sk)
    loop, tail = int(round(seconds * SR)), 8 * SR
    dry, wet = np.zeros((2, loop + tail)), np.zeros((2, loop + tail))
    for t, inst, name, dur, vel, pan, rev in ev:
        y = np.atleast_2d(inst(hz(midi(name)), dur, vel, t)) * (0.5 if inst is moog_bass else 0.75 if inst is analog_pad else 1.0)
        if y.shape[0] == 1:
            y = np.vstack([y, y])
        i = int(round(t * SR))
        y = y[:, : loop + tail - i]
        a = (pan + 1) * np.pi / 4
        y = y * np.array([[np.cos(a)], [np.sin(a)]]) * np.sqrt(2)
        dry[:, i:i + y.shape[1]] += y
        wet[:, i:i + y.shape[1]] += rev * y
    fold = lambda x: x[:, :loop] + np.pad(x[:, loop:], ((0, 0), (0, loop - tail)))      # what rings past the end comes back at the start
    dry, wet = fold(dry), fold(wet)
    ir_t = tt(int(3.5 * SR))
    for c in range(2):
        ir = rng.standard_normal(len(ir_t)) * np.exp(-ir_t / 0.6) * np.clip(ir_t / 0.03, 0, 1)
        ir = fft_filter(ir, lambda fr: lp(5000, 1)(fr) * hp(250, 1)(fr))
        dry[c] += 0.8 * np.fft.irfft(np.fft.rfft(wet[c]) * np.fft.rfft(np.pad(ir / np.sqrt(np.sum(ir ** 2)), (0, loop - len(ir)))), loop)
    f = np.fft.rfftfreq(loop, 1 / SR)
    mix = np.fft.irfft(np.fft.rfft(dry, axis=-1) * hp(35, 2)(f) * lp(13000, 2)(f), loop, axis=-1)
    mix *= 10 ** (-19 / 20) / np.sqrt(np.mean(mix ** 2))
    return np.tanh(1.4 * mix) / 1.4 * 1.05, seconds


def rubs(sk):
    """Melody notes with a note a semitone under them (or a minor ninth) sounding in the same chord."""
    per, out, bar = sk["beats"], [], 0
    for bars, left, pad, bass in sk["chords"]:
        under = {midi(n) for n in (left + " " + pad + " " + bass).split()}
        for n, a, b in rows(sk["melody"]):
            if a < (bar + bars) * per and a + b > bar * per:
                out += [(n, c) for c in under if (max(midi(n), c) - min(midi(n), c)) % 12 == 1 and b >= 1.5]
        bar += bars
    return out


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    meta = []
    for sk in SKETCHES:
        y, seconds = render(sk)
        C.write_wav(OUT / f"sketch_{sk['id']}.wav", y.astype(np.float32))
        meta.append({"id": sk["id"], "name": sk["name"], "why": sk["why"], "bpm": sk["bpm"], "seconds": seconds,
                     "sections": [{"name": "piano alone", "t": 0, "bars": 8}, {"name": "with pad and bass", "t": seconds / 2, "bars": 8}]})
        print(f"sketch {sk['id']} {sk['name']}: {seconds:.1f}s, peak {np.abs(y).max():.2f}, seam {np.abs(y[:, 0] - y[:, -1]).max():.4f}, long rubs {rubs(sk)}")
    (OUT / "sketches.json").write_text(json.dumps(meta, indent=1))
