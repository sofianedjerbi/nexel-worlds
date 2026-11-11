"""Quiet ambient loop to play under the game for 10-20 minutes. Cozy village x blocky meadow, mostly meadow.

Pure numpy, 48 kHz, 60 BPM, 48 bars = 192 s, seamless.

How it stays calm over a long session:
  * one key (D major), four chords, two bars each: an 8-bar harmonic cycle that never changes
  * the piano melody is ten notes in a minor-sixth range, mostly steps, with long holds,
    and it only plays in half of the cycles; the rest is space
  * layers repeat on different cycle lengths (melody 8 bars, music box 12, high swell 16),
    so each pass lines up a little differently, yet the whole loop still repeats exactly
  * no drums, no lead synth; soft dynamics at -20 dBFS RMS
  * registers never overlap: bass < piano chords < pad < melody < music box (checked below)
  * depth: piano up front, pad and bass in the middle, a dark wet music box far away;
    a long hall, ping-pong echo, a wind bed and a slow tape wobble, all circular (no seam)

    uv run python music/compose.py      # writes music/site/audio/*.wav + track.json
"""

from pathlib import Path
import json
import wave

import numpy as np

SR = 48000
BPM = 60
BEAT = 60 / BPM
BARS = 48
LOOP_S = BARS * 4 * BEAT
LOOP_N = int(round(LOOP_S * SR))
TAIL = 10 * SR
OUT = Path(__file__).with_name("site") / "audio"
rng = np.random.default_rng(5)

PC = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


def midi(name):
    pc, rest = PC[name[0]], name[1:]
    while rest and rest[0] in "#b":
        pc += 1 if rest[0] == "#" else -1
        rest = rest[1:]
    return 12 * (int(rest) + 1) + pc


def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def t_of(slot):  # eighth notes, 8 per bar
    return slot * BEAT / 2


def tt(n):
    return np.arange(n) / SR


def fft_filter(y, resp):
    n = len(y)
    m = 1 << int(np.ceil(np.log2(n + 2048)))
    return np.fft.irfft(np.fft.rfft(y, m) * resp(np.fft.rfftfreq(m, 1 / SR)), m)[:n]


def lp(fc, order=2):
    return lambda f: 1 / np.sqrt(1 + (f / fc) ** (2 * order))


def hp(fc, order=2):
    return lambda f: 1 / np.sqrt(1 + (fc / np.maximum(f, 1e-3)) ** (2 * order))


def bp(lo, hi):
    return lambda f: hp(lo)(f) * lp(hi)(f)


def wobble(t_abs, depth=1.0):
    """Tape wow in semitones; whole cycles per loop, so seamless."""
    return depth * (0.06 * np.sin(2 * np.pi * 41 / LOOP_S * t_abs) + 0.035 * np.sin(2 * np.pi * 13 / LOOP_S * t_abs + 1))


def phase(f, n, t0, extra=0.0, wob=1.0):
    return 2 * np.pi * np.cumsum(f * 2 ** ((wobble(t0 + tt(n), wob) + extra) / 12)) / SR


# ------------------------------------------------------------------ instruments (f, dur, vel, t0)

def felt_piano(f, dur, vel, t0):
    """Muffled felt piano: dark, slightly inharmonic, long natural ring, tiny stereo detune."""
    n = int((dur + 3.5) * SR)
    t = tt(n)
    bright = 700 + 1100 * vel
    out = []
    for det in (-1.5, 1.5):
        ph = phase(f, n, t0, det / 100, wob=1.2)
        y = np.zeros(n)
        for k in range(1, 12):
            fk = k * np.sqrt(1 + 0.0003 * k * k)
            if f * fk > 7000:
                break
            amp = (1 / k ** 1.2) / (1 + (f * fk / bright) ** 2)
            tau = 4.0 / k ** 0.7 * (220 / max(f, 110)) ** 0.35
            y += amp * np.sin(fk * ph) * (0.6 * np.exp(-t / (tau * 0.3)) + 0.4 * np.exp(-t / tau))
        out.append(y)
    thump = fft_filter(rng.standard_normal(n), lp(500)) * np.exp(-t / 0.02) * 0.08
    env = np.clip(t / 0.006, 0, 1) * np.where(t > dur, np.exp(-(t - dur) / 0.6), 1.0)
    return 0.34 * vel * np.stack([out[0] + thump, out[1] + thump]) * env


def pad(f, dur, vel, t0):
    """Slow warm pad: detuned soft saws, very dark, wide; breathes in and out."""
    n = int((dur + 5.0) * SR)
    t = tt(n)
    voices = []
    for d in (-6, 0, 6):
        ph = phase(f, n, t0, d / 100)
        voices.append(sum(np.sin(k * ph) / k / (1 + (k * f / 650) ** 2) for k in range(1, 10) if k * f < 4000))
    l, r = voices[0] + 0.5 * voices[1], voices[2] + 0.5 * voices[1]
    r = np.roll(r, int(0.015 * SR))
    env = np.clip(t / 3.0, 0, 1) ** 2 * np.where(t > dur, np.exp(-(t - dur) / 2.0), 1.0)
    return 0.06 * vel * np.stack([l, r]) * env


def swell(f, dur, vel, t0):
    """High, airy glass swell: sines with a slow rise and fall, far away."""
    n = int((dur + 4.0) * SR)
    t = tt(n)
    ph = phase(f, n, t0, wob=0.5)
    y = np.sin(ph) + 0.25 * np.sin(2 * ph + 0.3)
    return 0.05 * vel * y * np.sin(np.pi * np.clip(t / (dur + 4.0), 0, 1)) ** 2


def sub_bass(f, dur, vel, t0):
    n = int((dur + 2.0) * SR)
    t = tt(n)
    ph = phase(f, n, t0, wob=0.3)
    y = np.sin(ph) + 0.1 * np.sin(2 * ph)
    env = np.clip(t / 0.6, 0, 1) * np.where(t > dur, np.exp(-(t - dur) / 0.9), 1.0)
    return 0.32 * vel * y * env


def music_box(f, dur, vel, t0):
    n = int(4.0 * SR)
    t = tt(n)
    y = (np.sin(2 * np.pi * f * t) * np.exp(-t / 1.6)
         + 0.2 * np.sin(2 * np.pi * f * 3.0 * t) * np.exp(-t / 0.25)
         + 0.06 * np.sin(2 * np.pi * f * 5.95 * t) * np.exp(-t / 0.07))
    return 0.16 * vel * y * np.clip(t / 0.003, 0, 1)


# ------------------------------------------------------------------ harmony: one 8-bar cycle

CHORDS = {"Dmaj9": "D F# A C# E", "Gmaj7": "G B D F#", "Bm7": "B D F# A", "Gmaj9": "G B D F# A"}
CYCLE = ["Dmaj9", "Gmaj7", "Bm7", "Gmaj9"]   # two bars each


def chord_at_bar(bar):
    return CYCLE[(bar % 8) // 2]


def pcs(ch):
    return [midi(p + "4") % 12 for p in CHORDS[ch].split()]


def place(pc, lo):
    return lo + (pc - lo) % 12


def lh_notes(ch):
    """Left hand: root, fifth, colour (9th on major, 7th otherwise), third an octave up."""
    p = pcs(ch)
    major = (p[1] - p[0]) % 12 == 4
    r = place(p[0], 43)
    fifth = place(p[2], r + 1)
    color = place(p[4] if major and len(p) == 5 else p[3], fifth + 1)
    third = place(p[1], color + 1)
    return r, fifth, color, third


def pad_voicing(ch):
    return sorted(place(p, 57) for p in pcs(ch)[1:4])   # rootless, kept under the melody


# ------------------------------------------------------------------ the melody: ten notes

THEME = [  # per bar of the 8-bar cycle: (slot, length, note)
    [(2, 4, "F#5"), (6, 2, "E5")],
    [(0, 8, "A4")],
    [(2, 4, "B4"), (6, 2, "D5")],
    [(0, 8, "E5")],
    [(2, 4, "F#5"), (6, 2, "E5")],
    [(0, 2, "D5"), (2, 6, "B4")],
    [(2, 4, "D5"), (6, 10, "A4")],
    [],
]
MELODY_PLAN = ["rest", "theme", "theme", "rest", "theme", "fragments"]   # one entry per 8-bar cycle
SECTION_NAMES = ["still", "theme", "theme, echo", "open space", "theme", "fragments"]

# ------------------------------------------------------------------ arrangement

STEMS = ["piano", "pad", "bass", "musicbox", "air"]
events = []  # (t, dur, midi, vel, inst, pan, stem, rev, echo)


def note(slot, length, m, vel, inst, stem, pan=0.0, rev=0.3, echo=0.0, human=True):
    t0, dur = t_of(slot), t_of(slot + length) - t_of(slot)
    if human:
        t0 += abs(rng.normal(0, 0.012))
        vel *= 1 + rng.normal(0, 0.06)
    events.append((t0, dur, m, vel, inst, pan, stem, rev, echo))


for bar in range(BARS):
    cyc, i = bar // 8, bar % 8
    ch = chord_at_bar(bar)
    s0 = bar * 8
    first_of_chord = i % 2 == 0

    plan = MELODY_PLAN[cyc]
    if plan != "rest":
        for slot, ln, n in THEME[i]:
            if plan == "fragments" and i not in (0, 1, 4, 5):
                continue
            echo = 0.28 if cyc == 2 else 0.12
            note(s0 + slot, ln, midi(n), 0.5, felt_piano, "piano", 0.08, rev=0.4, echo=echo)

    # left hand: a soft dyad when the chord arrives, one colour tone, then the third in bar 2
    r, fifth, color, third = lh_notes(ch)
    if first_of_chord:
        note(s0, 16, r, 0.4, felt_piano, "piano", -0.3, rev=0.4)
        note(s0 + 0.15, 16, fifth, 0.3, felt_piano, "piano", -0.2, rev=0.4)
        if cyc not in (0, 5) or i == 0:
            note(s0 + 3, 13, color, 0.24, felt_piano, "piano", -0.1, rev=0.45)
    else:
        note(s0 + 4, 4, third, 0.22, felt_piano, "piano", -0.15, rev=0.45)

    if first_of_chord:
        for m in pad_voicing(ch):
            note(s0, 16, m, 0.85, pad, "pad", 0.0, rev=0.55, human=False)
        note(s0, 15, place(pcs(ch)[0], 33), 0.8, sub_bass, "bass", 0.0, rev=0.05, human=False)

# music box: a 12-bar cycle against the 8-bar harmony; only notes that sit well on every chord
BOX = [(0, 3, "A5"), (3, 5, "F#6"), (5, 1, "D6"), (8, 6, "F#6"), (10, 2, "A5")]   # (bar in 12, slot, note)
for rep in range(BARS // 12):
    for b, slot, n in BOX:
        note((rep * 12 + b) * 8 + slot, 2, midi(n), 0.55, music_box, "musicbox", rng.uniform(-0.8, 0.8), rev=0.8, echo=0.5)

# high swell: a 16-bar cycle, floating very far away
for rep in range(BARS // 16):
    note(rep * 128 + 64, 48, midi("F#5"), 0.9, swell, "air", -0.4, rev=0.9, human=False)
    note(rep * 128 + 68, 44, midi("A5"), 0.7, swell, "air", 0.4, rev=0.9, human=False)


# ------------------------------------------------------------------ checks

def clash_report():
    """Melody / music box / swell vs sounding chord tones: flag minor 9ths, and off-chord semitones or tritones."""
    held = [(t, t + d, m) for t, d, m, v, inst, *_ in events if inst in (pad, felt_piano, sub_bass) and m < 69]
    bad = []
    for t, d, m, v, inst, pan, stem, *_ in events:
        if not (stem in ("musicbox", "air") or (inst is felt_piano and m >= 69)):
            continue
        in_chord = m % 12 in pcs(chord_at_bar(int(t / (4 * BEAT))))
        for a, b, h in held:
            if a <= t < b - 0.05:
                iv = (m - h) % 12
                if iv == 1 or (iv in (11, 6) and not in_chord):
                    bad.append((round(t, 2), m, h, iv))
    return bad


def register_overlap():
    low_mel = min(midi(n) for bar in THEME for _, _, n in bar)
    return {"lowest melody": low_mel, "highest left hand": max(max(lh_notes(c)) for c in CYCLE),
            "highest pad": max(max(pad_voicing(c)) for c in CYCLE)}


# ------------------------------------------------------------------ render

def fold(x):
    out = x[:, :LOOP_N].copy()
    out[:, :TAIL] += x[:, LOOP_N:LOOP_N + TAIL]
    return out


def circ(x, resp):
    return np.fft.irfft(np.fft.rfft(x, axis=-1) * resp(np.fft.rfftfreq(LOOP_N, 1 / SR)), LOOP_N, axis=-1)


def echo_fx(mono, beats=1.5, fb=0.5):
    d = int(beats * BEAT * SR)
    f = np.fft.rfftfreq(LOOP_N, 1 / SR)
    k = np.arange(len(f))
    z = fb * lp(2200, 1)(f) * hp(300, 1)(f) * np.exp(-2j * np.pi * k * d / LOOP_N)
    x = np.fft.rfft(mono)
    return 0.5 * np.stack([np.fft.irfft(x * z / (1 - z ** 2), LOOP_N), np.fft.irfft(x * z ** 2 / (1 - z ** 2), LOOP_N)])


def make_ir(seconds=9.0, tau_dark=1.3, tau_bright=0.4, predelay=0.04):
    n = int(seconds * SR)
    t = tt(n)
    irs = []
    for _ in range(2):
        dark = fft_filter(rng.standard_normal(n), lp(1500)) * np.exp(-t / tau_dark)
        bright = fft_filter(rng.standard_normal(n), hp(1500)) * np.exp(-t / tau_bright) * 0.4
        ir = (dark + bright) * np.clip(t / 0.15, 0, 1)
        ir[: int(predelay * SR)] = 0
        ir /= np.sqrt(np.sum(ir ** 2))
        padded = np.zeros(LOOP_N)
        padded[:n] = ir
        irs.append(np.fft.rfft(padded))
    return irs


def wind_bed():
    t = np.arange(LOOP_N) / SR
    air = circ(rng.standard_normal((2, LOOP_N)), lambda f: bp(150, 1100)(f) / np.sqrt(np.maximum(f, 20) / 150))
    breathe = 0.5 + 0.5 * np.sin(2 * np.pi * 4 / LOOP_S * t) * np.sin(2 * np.pi * 9 / LOOP_S * t + 0.7)
    return 0.025 * air / np.abs(air).max() * breathe


def limiter_gain(x, ceil=0.9, block=48):
    peak = np.abs(x).max(axis=0)
    nb = LOOP_N // block
    pb = peak[: nb * block].reshape(nb, block).max(axis=1)
    g = np.minimum(1, ceil / np.maximum(pb, 1e-9))
    w = 8
    gm = np.min([np.roll(g, s) for s in range(-w, w + 1)], axis=0)
    gs = np.mean([np.roll(gm, s) for s in range(-w // 2, w // 2 + 1)], axis=0)
    full = np.repeat(gs, block)
    return np.concatenate([full, np.full(LOOP_N - len(full), full[-1])])


def render():
    n = LOOP_N + TAIL
    buses = {s: {k: np.zeros((2, n)) for k in ("dry", "rev", "echo")} for s in STEMS}
    for t, dur, m, vel, inst, pan, stem, rs, es in events:
        y = np.atleast_2d(inst(hz(m), dur, vel, t))
        if y.shape[0] == 1:
            y = np.vstack([y, y])
        i = int(round(t * SR)) % LOOP_N
        y = y[:, : n - i]
        a = (pan + 1) * np.pi / 4
        y = y * np.array([[np.cos(a)], [np.sin(a)]]) * np.sqrt(2)
        b = buses[stem]
        b["dry"][:, i:i + y.shape[1]] += y
        b["rev"][:, i:i + y.shape[1]] += rs * y
        if es:
            b["echo"][:, i:i + y.shape[1]] += es * y

    irs = make_ir()
    plane = {"piano": (1.0, 7000), "pad": (0.75, 2500), "bass": (1.0, 1200), "musicbox": (0.3, 3800), "air": (0.4, 5000)}
    stems = {}
    for s in STEMS:
        b = {k: fold(v) for k, v in buses[s].items()}
        echo = echo_fx(b["echo"].mean(axis=0))
        send = circ(b["rev"] + 0.5 * echo, hp(180, 1))
        wet = np.stack([np.fft.irfft(np.fft.rfft(send[c]) * irs[c], LOOP_N) for c in range(2)])
        dry_amt, dark = plane[s]
        stems[s] = dry_amt * circ(b["dry"], lp(dark, 1)) + echo + 1.15 * wet
    stems["air"] = stems["air"] + wind_bed()

    stems["bass"] = circ(stems["bass"], lambda f: hp(30, 2)(f) * lp(900, 2)(f))
    for s in ("piano", "pad", "musicbox"):
        stems[s] = circ(stems[s], hp(80, 1))
    gains = {"piano": 1.0, "pad": 0.8, "bass": 0.7, "musicbox": 0.85, "air": 0.9}
    for s in STEMS:
        stems[s] = circ(stems[s] * gains[s], lambda f: hp(25, 2)(f) * lp(13000, 2)(f))

    pre = sum(stems.values())
    norm = 10 ** (-20 / 20) / np.sqrt(np.mean(pre ** 2))
    g = limiter_gain(pre * norm)
    for s in STEMS:
        stems[s] = stems[s] * norm * g
    return sum(stems.values()), stems


def write_wav(path, x):
    pcm = (np.clip(x, -1, 1) * 32767).round().astype("<i2").T.copy()
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


if __name__ == "__main__":
    print("registers:", register_overlap())
    bad = clash_report()
    print(f"clash check: {len(bad)}", bad[:10])
    master, stems = render()
    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("stem_*.wav"):
        old.unlink()
    write_wav(OUT / "master.wav", master)
    for s, x in stems.items():
        write_wav(OUT / f"stem_{s}.wav", x)
    meta = {"title": "Meadow Afternoon", "bpm": BPM, "key": "D major", "mood": "quiet ambient", "bars": BARS,
            "seconds": LOOP_S, "beats_per_hop": 4,
            "sections": [{"id": str(k + 1), "name": nm, "bar": k * 8, "t": k * 32 * BEAT} for k, nm in enumerate(SECTION_NAMES)],
            "stems": STEMS}
    (OUT / "track.json").write_text(json.dumps(meta, indent=1))
    rms = np.sqrt(np.mean(master ** 2))
    print(f"{len(events)} notes, {LOOP_S:.0f}s loop, peak {np.abs(master).max():.3f}, rms {20 * np.log10(rms):.1f} dBFS")
    for s, x in stems.items():
        print(f"  {s:9s} rms {20 * np.log10(np.sqrt(np.mean(x ** 2)) + 1e-12):6.1f} dBFS")
