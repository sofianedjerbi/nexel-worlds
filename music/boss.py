"""Boss fight mockup: "Old Mossback". Rendered to music/site/audio/boss.wav (+ boss.json) for the showcase page.

    uv run python music/boss.py

It is Meadow Road turned to face you: the same melody, note for note (compose.MELODY: its four notes belong to B minor
as much as to D major), on the same soft piano. What changes is underneath it:
  the harmony   the relative minor, as at night: B minor 7, A, F# minor, then A and B minor
  the tempo     96 BPM instead of 72, but no faster than a tortoise needs: weight, not speed
  the stomp     a heavy thud on beats 1 and 3 (its feet), a dull knock on 2 and 4 (its shell)
  the bass      an eighth-note ostinato on the root, climbing into each bar
  the call      a low horn rising a step at a time under everything (its voice)
Form (36 bars, a 90 s seamless loop): it stands up (4) / the fight (8) / everything in (8) / it braces: drums and bass drop
out, then stomp back in on every beat (8) / everything in again (8).
Rules kept from PROCESS.md: one key, three chords, one melody repeated exactly, variety only from texture, every part in
its own register, no toy sounds.
"""
import json
from pathlib import Path

import numpy as np

import compose as C
from compose import MAIN, SR, analog_pad, bp, fft_filter, glide_lead, hp, hz, lp, midi, moog_bass, phase, release, saw, tt

BPM, BARS = 96, 36
BEAT = 60 / BPM
BAR = 4 * BEAT
LOOP_N = int(round(BARS * BAR * SR))
TAIL = 6 * SR
OUT = Path(__file__).with_name("site") / "audio"
rng = np.random.default_rng(7)

CYCLE = ["Bm", "Bm", "A", "A", "F#m", "F#m", "A", "Bm"]
ROOT = {"Bm": ("B1", "F#2"), "F#m": ("F#1", "C#2"), "D": ("D2", "A2"), "G": ("G1", "D2"), "A": ("A1", "E2")}
PIZZ = {"Bm": ["B2", "F#3", "A3", "F#3"], "F#m": ["F#2", "C#3", "A2", "C#3"], "A": ["A2", "E3", "B2", "E3"]}     # A has no third (the tune lands on D over it)
PAD = {"Bm": ["B2", "D3", "F#3"], "F#m": ["F#2", "A2", "C#3"], "A": ["A2", "E3", "A3"]}
MELODY = C.MELODY                                                   # the day's melody, as it is
HORN = [(0, 2, "F#2"), (2, 2, "A2"), (4, 2, "F#2"), (6, 1, "A2"), (7, 1, "B2")]  # bar, bars long, note: each belongs to its chord
SECTIONS = [("it stands up", 4), ("the fight", 8), ("everything in", 8), ("it braces, then stomps back", 8), ("everything in again", 8)]


def stomp(f, dur, vel, t0):
    """A foot the size of a cart: a short drop in pitch, a low thud of noise, a little grit. Not a drum-machine kick."""
    n = int(0.6 * SR)
    t = tt(n)
    body = np.sin(2 * np.pi * np.cumsum(50 + 40 * np.exp(-t / 0.018)) / SR) * np.exp(-t / 0.13)
    thud = fft_filter(rng.standard_normal(n), lp(170)) * np.exp(-t / 0.06)
    grit = fft_filter(rng.standard_normal(n), bp(300, 1400)) * np.exp(-t / 0.012)
    return vel * (0.9 * body + 0.8 * thud / np.abs(thud).max() + 0.2 * grit / np.abs(grit).max()) * np.clip(t / 0.002, 0, 1)


def knock(f, dur, vel, t0):
    """Shell plate on shell plate: mostly contact noise, four heavily damped modes."""
    n = int(0.2 * SR)
    t = tt(n)
    y = fft_filter(rng.standard_normal(n), bp(700, 2600)) * np.exp(-t / 0.012)
    y = y / np.abs(y).max() + 0.5 * sum(np.sin(2 * np.pi * m * rng.uniform(0.97, 1.03) * t) * np.exp(-t / 0.02) for m in (410, 655, 980, 1370)) / 2
    return 0.5 * vel * y * np.clip(t / 0.001, 0, 1)


def shaker(f, dur, vel, t0):
    n = int(0.12 * SR)
    t = tt(n)
    y = fft_filter(rng.standard_normal(n), hp(5000)) * np.clip(t / 0.004, 0, 1) * np.exp(-t / 0.022)
    return 0.25 * vel * y / np.abs(y).max()


def pizz(f, dur, vel, t0):
    """Plucked strings: bright for an instant, then only the body of the note."""
    n = int(0.7 * SR)
    t = tt(n)
    ph = phase(f, n, t0, wob=0.3)
    y = saw(ph, f, 2400) * np.exp(-t / 0.045) + 0.8 * saw(ph, f, 750) * np.exp(-t / 0.2)
    return 0.3 * vel * y * np.clip(t / 0.002, 0, 1)


def horn(f, dur, vel, t0):
    """A low horn: slow to speak, brighter as it swells, a little unsteady."""
    n = int((dur + 0.8) * SR)
    t = tt(n)
    swell = 0.55 + 0.45 * np.sin(np.pi * np.clip(t / dur, 0, 1))
    ph = phase(f, n, t0, 0.06 * np.sin(2 * np.pi * 4.6 * t) * np.clip((t - 0.5) / 0.8, 0, 1), wob=0.5)
    y = sum(np.sin(k * ph) / k ** 1.2 * swell ** (0.6 * k) for k in range(1, 11) if k * f < 2400)
    return 0.26 * vel * y * np.clip(t / 0.2, 0, 1) * release(t, dur, 0.35)


events = []      # (seconds, instrument, note, seconds long, velocity, pan, reverb send, stem)


def add(bar, slot, inst, name, slots, vel, stem, pan=0.0, rev=0.15):
    events.append(((bar * 8 + slot) * BEAT / 2, inst, name, slots * BEAT / 2, vel, pan, rev, stem))


def chords(k):
    """The chord under each eighth of bar k of a cycle."""
    ch = CYCLE[k % 8]
    return ["G"] * 4 + ["A"] * 4 if ch == "GA" else [ch] * 8


def block(first, drums=True, bass=True, strings=0, horn_on=False, lead=False, pad=False, shake=False, every_beat=False, mel=1.0):
    for k in range(8):
        bar, ch = first + k, chords(k)
        if drums:
            for s in (0, 2, 4, 6) if every_beat else (0, 4):
                add(bar, s, stomp, "B1", 1, 1.0 if s in (0, 4) else 0.7, "drums", rev=0.08)
            for s in (2, 6):
                add(bar, s, knock, "B1", 1, 0.8, "drums", pan=0.25 if s == 2 else -0.25)
        if shake:
            for s in (1, 3, 5, 7):
                add(bar, s, shaker, "B1", 1, 0.8 if s in (3, 7) else 0.55, "drums", pan=-0.3)
        if bass:
            for s, which, v in ((0, 0, 1.0), (2, 0, 0.7), (3, 0, 0.8), (4, 0, 0.9), (6, 1, 0.8), (7, 0, 0.75)):
                add(bar, s, moog_bass, ROOT[ch[s]][which], 0.75, v, "bass", rev=0.0)
        for s in range(0, 8, 2 if strings == 1 else 1) if strings else ():
            add(bar, s, pizz, PIZZ[ch[s]][s % 4], 1, 0.8 if s % 4 == 0 else 0.6, "strings", pan=0.35, rev=0.2)
        if pad:
            for half in (0, 4) if CYCLE[k] == "GA" else (0,):
                for i, nm in enumerate(PAD[ch[half]]):
                    add(bar, half, analog_pad, nm, 4 if CYCLE[k] == "GA" else 8, 0.8, "pad", pan=(-0.4, 0, 0.4)[i], rev=0.4)
        for s, length, nm in MELODY[k]:
            add(bar, s, MAIN, nm, length, 0.85 * mel, "piano", pan=-0.1, rev=0.3)
            if lead:
                add(bar, s, glide_lead, nm, length, 0.5, "lead", pan=0.15, rev=0.3)
    for b, bars, nm in HORN if horn_on else ():
        add(first + b, 0, horn, nm, bars * 8 - 0.5, 0.9, "horn", pan=-0.2, rev=0.35)


for bar in range(4):                                               # it stands up: feet first, then the bass, then its voice
    for s in (0,) if bar < 2 else (0, 4):
        add(bar, s, stomp, "B1", 1, 1.0, "drums", rev=0.08)
    if bar >= 2:
        for s, which, v in ((0, 0, 1.0), (2, 0, 0.7), (3, 0, 0.8), (4, 0, 0.9), (6, 1, 0.8), (7, 0, 0.75)):
            add(bar, s, moog_bass, ROOT["Bm"][which], 0.75, v, "bass", rev=0.0)
    if bar == 3:
        for s in (2, 6, 7):
            add(bar, s, knock, "B1", 1, 0.8, "drums", pan=0.25)
add(2, 0, horn, "F#2", 15.5, 0.9, "horn", pan=-0.2, rev=0.35)
block(4, strings=1)
block(12, strings=2, horn_on=True, lead=True, shake=True)
block(20, drums=False, bass=False, horn_on=True, pad=True, mel=0.8)     # it braces: no feet, no bass; then, from bar 24, every beat
for bar in range(24, 28):
    for s in (0, 2, 4, 6):
        add(bar, s, stomp, "B1", 1, 0.55 + 0.11 * (bar - 24) + (0.1 if s in (0, 4) else 0), "drums", rev=0.08)
    for s, which, v in ((0, 0, 1.0), (2, 0, 0.7), (3, 0, 0.8), (4, 0, 0.9), (6, 1, 0.8), (7, 0, 0.75)):
        add(bar, s, moog_bass, ROOT[chords(bar - 20)[s]][which], 0.75, v, "bass", rev=0.0)
    for s in range(8):
        add(bar, s, pizz, PIZZ[chords(bar - 20)[s]][s % 4], 1, 0.5 + 0.08 * (bar - 24), "strings", pan=0.35, rev=0.2)
for s in (5, 6, 7):
    add(27, s, knock, "B1", 1, 0.9, "drums", pan=-0.25)
block(28, strings=2, horn_on=True, lead=True, shake=True, pad=True)

GAIN = {"drums": 1.15, "bass": 0.9, "strings": 1.3, "horn": 0.9, "piano": 0.9, "lead": 0.9, "pad": 1.0}


def render():
    n = LOOP_N + TAIL
    stems = {s: (np.zeros((2, n)), np.zeros((2, n))) for s in GAIN}
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
    ir_t = tt(int(2.5 * SR))
    irs = []
    for _ in range(2):                                             # a smaller, drier room than Meadow Road's: a fight is close
        ir = rng.standard_normal(len(ir_t)) * np.exp(-ir_t / 0.25) * np.clip(ir_t / 0.03, 0, 1)
        ir = fft_filter(ir, lambda fr: lp(4500, 1)(fr) * hp(250, 1)(fr))
        irs.append(np.fft.rfft(np.pad(ir / np.sqrt(np.sum(ir ** 2)), (0, LOOP_N - len(ir)))))
    out = {}
    for s, (dry, rev) in stems.items():
        dry, rev = fold(dry), fold(rev)
        wet = np.stack([np.fft.irfft(np.fft.rfft(rev[c]) * irs[c], LOOP_N) for c in range(2)])
        x = GAIN[s] * (dry + 0.3 * wet)
        cut = hp(30, 2)(f) if s in ("bass", "drums") else hp(120, 1)(f)
        out[s] = np.fft.irfft(np.fft.rfft(x, axis=-1) * cut * lp(15000, 2)(f), LOOP_N, axis=-1)
    mix = sum(out.values())
    mix *= 10 ** (-17 / 20) / np.sqrt(np.mean(mix ** 2))
    return np.tanh(1.4 * mix) / 1.4 * 1.05, out


if __name__ == "__main__":
    master, stems = render()
    OUT.mkdir(parents=True, exist_ok=True)
    C.write_wav(OUT / "boss.wav", master.astype(np.float32))
    t = 0.0
    secs = []
    for name, bars in SECTIONS:
        secs.append({"name": name, "t": t, "bars": bars})
        t += bars * BAR
    (OUT / "boss.json").write_text(json.dumps({"title": "Old Mossback", "bpm": BPM, "key": "B minor", "bars": BARS, "seconds": BARS * BAR,
                                               "sections": secs}, indent=1))
    rms = lambda x: 20 * np.log10(np.sqrt(np.mean(x ** 2)) + 1e-9)
    print(f"{len(events)} notes, {BARS * BAR:.1f}s loop, peak {np.abs(master).max():.3f}, rms {rms(master):.1f} dBFS")
    edges = np.cumsum([0] + [b for _, b in SECTIONS]) * BAR * SR
    for s, x in stems.items():
        print(f"  {s:8s}", " ".join(f"{rms(x[:, int(a):int(b)]):6.1f}" for a, b in zip(edges, edges[1:])))
    seam = np.abs(master[:, 0] - master[:, -1]).max()
    print(f"  seam step {seam:.4f}")
