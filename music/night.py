"""The night theme: "Lantern Road". Rendered to music/site/audio/night.wav (+ night.json) for the showcase page.

    uv run python music/night.py

It is Meadow Road after dark: the same melody, note for note (compose.MELODY), and nothing added to it. What changes:
  the harmony    the day's notes over minor chords: E minor, B minor, G, A (no third), and it ends on B minor
  the tempo      60 BPM instead of 72, and about 4 dB quieter
  the left hand  one held chord a bar, struck together (never a note at a time: see compose.py)
  the air        a breath of wind; no drums; a short, dry room, so it stays awake and does not turn into a lullaby
Form (48 bars, a 192 s seamless loop): the melody alone (8) / the left hand (8) / pad and bass (8) / the piano rests,
a far whistle carries the melody (8) / everything (8) / thinning out (8).
(A first version had crickets and high plucked "fireflies": the user found both very bad. Nothing decorative now.)
"""
import json
from pathlib import Path

import numpy as np

import compose as C
from compose import SR, analog_pad, bp, fft_filter, glide_lead, hp, hz, lofi_piano, lp, midi, moog_bass, tt

BPM, BARS = 60, 48
BEAT = 60 / BPM
BAR = 4 * BEAT
LOOP_S = BARS * BAR
LOOP_N = int(round(LOOP_S * SR))
TAIL = 8 * SR
OUT = Path(__file__).with_name("site") / "audio"
rng = np.random.default_rng(11)

CYCLE = ["Em", "Bm", "G", "Asus", "Em", "Bm", "G", "Bm"]            # 8 bars, a chord a bar
ROOT = {"Em": "E2", "Bm": "B1", "G": "G1", "Asus": "A1"}
HAND = {"Em": ["E2", "B2", "G3"], "Bm": ["B2", "F#3"], "G": ["G2", "D3", "B3"], "Asus": ["A2", "E3", "B3"]}      # struck together, held
PAD = {"Em": ["E3", "B3"], "Bm": ["B2", "F#3"], "G": ["G3", "D3"], "Asus": ["A2", "E3"]}       # root and fifth only: nothing to rub
MELODY = C.MELODY                                                   # the day's, as it is
SECTIONS = [("the melody alone", 8), ("the left hand", 8), ("pad and bass", 8), ("the piano rests: a far whistle", 8), ("everything", 8), ("thinning out", 8)]


def whistle(f, dur, vel, t0):
    """The day's lead, heard from far off: softer."""
    return 0.6 * glide_lead(f, dur, vel, t0)


events = []      # (seconds, instrument, note, seconds long, velocity, pan, reverb send, stem)


def add(bar, slot, inst, name, slots, vel, stem, pan=0.0, rev=0.2):
    events.append(((bar * 8 + slot) * BEAT / 2, inst, name, slots * BEAT / 2, vel, pan, rev, stem))


def block(first, piano=1.0, roll=0.0, pad=0.0, bass=False, far=False):
    for k in range(8):
        bar, ch = first + k, CYCLE[k]
        for s, length, nm in MELODY[k]:
            if piano:
                add(bar, s, lofi_piano, nm, length, piano * (0.8 if s else 0.7), "piano", pan=0.08, rev=0.3)
            if far:
                add(bar, s, whistle, nm, length, 0.75, "whistle", pan=0.2, rev=0.45)
        for j, nm in enumerate(HAND[ch]) if roll else ():
            add(bar, 0, lofi_piano, nm, 8, roll * (0.46 - 0.04 * j), "piano", pan=-0.3 + 0.2 * j, rev=0.3)
        for i, nm in enumerate(PAD[ch]) if pad else ():
            add(bar, 0, analog_pad, nm, 8, pad, "pad", pan=(-0.4, 0.4)[i], rev=0.35)
        if bass:
            add(bar, 0, moog_bass, ROOT[ch], 7.5, 0.8, "bass", rev=0.0)


block(0)
block(8, roll=1.0)
block(16, roll=1.0, pad=0.8, bass=True)
block(24, piano=0.0, roll=0.9, pad=0.9, bass=True, far=True)
block(32, roll=1.0, pad=0.9, bass=True, far=True)
block(40, piano=0.9, pad=0.7)

GAIN = {"piano": 1.0, "whistle": 0.8, "pad": 0.75, "bass": 0.5, "air": 1.0}


def air():
    """A breath of wind, low and far: circular noise, swelling a whole number of times per loop."""
    f = np.fft.rfftfreq(LOOP_N, 1 / SR)
    t = np.arange(LOOP_N) / SR
    out = []
    for ch in range(2):
        y = np.fft.irfft(np.fft.rfft(rng.standard_normal(LOOP_N)) * bp(180, 900, 1)(f), LOOP_N)
        out.append(y / np.sqrt(np.mean(y ** 2)) * (0.55 + 0.45 * np.sin(2 * np.pi * (11 + 2 * ch) * t / LOOP_S + ch)))
    return 0.006 * np.stack(out)


def render():
    n = LOOP_N + TAIL
    stems = {s: (np.zeros((2, n)), np.zeros((2, n))) for s in GAIN if s != "air"}
    for t, inst, name, dur, vel, pan, rev, stem in events:
        y = np.atleast_2d(inst(hz(midi(name)), dur, vel, t))
        if y.shape[0] == 1:
            y = np.vstack([y, y])
        i = int(round(t * SR))
        y = y[:, : n - i]
        a = (pan + 1) * np.pi / 4
        y = y * np.array([[np.cos(a)], [np.sin(a)]]) * np.sqrt(2)
        stems[stem][0][:, i:i + y.shape[1]] += y
        stems[stem][1][:, i:i + y.shape[1]] += rev * y

    def fold(x):                                                   # what rings past the end comes back at the start: a seamless loop
        out = x[:, :LOOP_N].copy()
        out[:, :TAIL] += x[:, LOOP_N:]
        return out

    f = np.fft.rfftfreq(LOOP_N, 1 / SR)
    ir_t = tt(int(3.5 * SR))
    irs = []
    for _ in range(2):                                             # open air at night: a little longer than the boss's room, still not a hall
        ir = rng.standard_normal(len(ir_t)) * np.exp(-ir_t / 0.55) * np.clip(ir_t / 0.03, 0, 1)
        ir = fft_filter(ir, lambda fr: lp(5000, 1)(fr) * hp(250, 1)(fr))
        irs.append(np.fft.rfft(np.pad(ir / np.sqrt(np.sum(ir ** 2)), (0, LOOP_N - len(ir)))))
    out = {}
    for s, (dry, rev) in stems.items():
        dry, rev = fold(dry), fold(rev)
        wet = np.stack([np.fft.irfft(np.fft.rfft(rev[c]) * irs[c], LOOP_N) for c in range(2)])
        x = GAIN[s] * (dry + 0.8 * wet)
        cut = hp(30, 2)(f) if s == "bass" else hp(110, 1)(f)
        out[s] = np.fft.irfft(np.fft.rfft(x, axis=-1) * cut * lp(13000, 2)(f), LOOP_N, axis=-1)
    music = sum(out.values())
    scale = 10 ** (-21 / 20) / np.sqrt(np.mean(music ** 2))        # quieter than the day (-17): it is night
    out = {s: x * scale for s, x in out.items()}
    out["air"] = GAIN["air"] * air()
    mix = sum(out.values())
    return np.tanh(1.4 * mix) / 1.4 * 1.05, out


def clashes():
    """Melody notes a semitone or a minor 9th from a note sounding with them."""
    bad = []
    for k in range(8):
        chord = {midi(nm) for nm in PAD[CYCLE[k]] + HAND[CYCLE[k]]} | {midi(ROOT[CYCLE[k]])}
        bad += [(k, nm) for _, _, nm in MELODY[k] if any((max(midi(nm), c) - min(midi(nm), c)) % 12 == 1 for c in chord)]
    return bad


if __name__ == "__main__":
    print("clashes:", clashes())
    master, stems = render()
    OUT.mkdir(parents=True, exist_ok=True)
    C.write_wav(OUT / "night.wav", master.astype(np.float32))
    t = 0.0
    secs = []
    for name, bars in SECTIONS:
        secs.append({"name": name, "t": t, "bars": bars})
        t += bars * BAR
    (OUT / "night.json").write_text(json.dumps({"title": "Lantern Road", "bpm": BPM, "key": "E minor (the day's notes)", "bars": BARS, "seconds": LOOP_S,
                                                "sections": secs}, indent=1))
    rms = lambda x: 20 * np.log10(np.sqrt(np.mean(x ** 2)) + 1e-9)
    print(f"{len(events)} notes, {LOOP_S:.1f}s loop, peak {np.abs(master).max():.3f}, rms {rms(master):.1f} dBFS")
    edges = np.cumsum([0] + [b for _, b in SECTIONS]) * BAR * SR
    for s, x in stems.items():
        print(f"  {s:9s}", " ".join(f"{rms(x[:, int(a):int(b)]):6.1f}" for a, b in zip(edges, edges[1:])))
    print(f"  seam step {np.abs(master[:, 0] - master[:, -1]).max():.4f}")
