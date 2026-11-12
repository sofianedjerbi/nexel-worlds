"""Meadow Road: the main theme. Calm background music, ~4.9 min, seamless.

Fourth theme (2026-11-12). What the user rejected on the way, which this file must never do again:
  * a bright, hard piano, high up: "too aggressive, too high"
  * three even notes rising to a held one, on a pure tone: "the noise a pharmacy makes when you enter", "a notification"
  * ANY STAIRCASE: "you go slowly up note by note then slowly down note by note: it makes me sick". That was the left
    hand going up each chord and back a note at a time, and melodies moving by step up, then by step down.
So:
  * no arpeggio anywhere. Chords are struck together, softly, and held; a pad and a bass under them.
  * the melody never takes two steps in the same direction: it repeats a note, drops a third, leaps a fifth, holds.
  * it sits low (D4-D5), on a soft, dark felt piano that is still a piano (two strings, a felt thump), not a sine.
  * the key must be heard ("the scale looks off"): an earlier version began on the IV chord, put melody notes that were
    not in the chord on the strong beats, and had no leading note and no cadence. Now it is a plain period in D major:
        I  V6  vi  V   (D, A over C#, B minor, A: the bass walks down, the phrase stops on the leading note C#)
        I  V6  IV-V  I (D, A over C#, G then A, D: the melody closes E to D)
    and every melody note that starts on a beat is a note of the chord under it (`off_chord()` checks).
What stays from the research (C418, Undertale): few chords, a short melody repeated exactly, the same melody reused by
the night theme (night.py) and the boss fight (boss.py) over other chords, silence, no drums. Layers enter and leave;
the material never changes.
The Opus 5.5 version is frozen in music/opus/.

Pure numpy, 48 kHz, 72 BPM, 88 bars = 293 s. Melody from bar 1. Checks: registers, clashes, staircases, loudness.

    uv run python music/compose.py      # writes music/site/audio/*.wav + track.json
"""

from pathlib import Path
import json
import os
import wave

import numpy as np

SR = 48000
BPM = 72
BEAT = 60 / BPM
BARS = 88
LOOP_S = BARS * 4 * BEAT
LOOP_N = int(round(LOOP_S * SR))
TAIL = 7 * SR
OUT = Path(__file__).with_name("site") / "audio"
rng = np.random.default_rng(418)

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
    n = y.shape[-1]
    m = 1 << int(np.ceil(np.log2(n + 2048)))
    return np.fft.irfft(np.fft.rfft(y, m, axis=-1) * resp(np.fft.rfftfreq(m, 1 / SR)), m, axis=-1)[..., :n]


def lp(fc, order=2):
    return lambda f: 1 / np.sqrt(1 + (f / fc) ** (2 * order))


def hp(fc, order=2):
    return lambda f: 1 / np.sqrt(1 + (fc / np.maximum(f, 1e-3)) ** (2 * order))


def bp(lo, hi, order=2):
    return lambda f: hp(lo, order)(f) * lp(hi, order)(f)


def loop_lfo(t_abs, cycles, ph=0.0):
    """0..1, a whole number of cycles per loop: seamless."""
    return 0.5 + 0.5 * np.sin(2 * np.pi * cycles / LOOP_S * t_abs + ph)


def wobble(t_abs, depth=1.0):
    return depth * (0.05 * np.sin(2 * np.pi * 67 / LOOP_S * t_abs) + 0.03 * np.sin(2 * np.pi * 19 / LOOP_S * t_abs + 1))


def phase(f, n, t0, semis=0.0, wob=1.0):
    return 2 * np.pi * np.cumsum(f * 2 ** ((wobble(t0 + tt(n), wob) + semis) / 12)) / SR


def release(t, dur, r):
    return np.where(t > dur, np.exp(-(t - dur) / r), 1.0)


def saw(ph, f, cutoff, kmax=40):
    return sum(np.sin(k * ph) / k / (1 + (k * f / cutoff) ** 2) for k in range(1, kmax) if k * f < 12000)


# ------------------------------------------------------------------ instruments (f, dur, vel, t0)

def lofi_piano(f, dur, vel, t0):
    """The main instrument: a felt piano played softly. Two strings a hair apart (they beat slowly), stretched partials
    that die at their own rates, a soft thump of felt. Darker and rounder than the first one (heard as "aggressive"),
    but not a pure tone: the second try was close to a sine with a clean attack, and sounded like a door chime."""
    n = int((dur + 3.0) * SR)
    t = tt(n)
    bright = 1700 + 1900 * vel
    cents = rng.normal(0, 2.5)
    y = np.zeros(n)
    for string in (-1.6, 1.9):
        ph = phase(f, n, t0, (cents + string) / 100, wob=0.5)       # (little tape wobble: the pitch must be sure)
        for k in range(1, 14):
            fk = k * np.sqrt(1 + 0.0005 * k * k)
            if f * fk > 7500:
                break
            tau = 4.0 / k ** 0.75 * (220 / max(f, 110)) ** 0.35
            y += 0.5 * (1 / k ** 1.25) / (1 + (f * fk / bright) ** 2) * np.sin(fk * ph) * (0.5 * np.exp(-t / (tau * 0.25)) + 0.5 * np.exp(-t / tau))
    y += fft_filter(rng.standard_normal(n), bp(180, 1400, 1)) * np.exp(-t / 0.012) * 0.05 * (0.5 + vel)   # the felt on the strings
    y = np.tanh(1.2 * y) / 1.2
    mic = lambda centre: (lambda fr: bp(90, 6000, 1)(fr) * (1 + 0.15 / (1 + ((fr - centre) / 600) ** 2)))
    left, right = fft_filter(y, mic(500)), np.roll(fft_filter(y, mic(700)), 10)
    return 0.46 * vel * np.stack([left, right]) * np.clip(t / 0.007, 0, 1) * release(t, dur, 0.55)


def analog_pad(f, dur, vel, t0):
    """Four detuned saws, filter opening and closing over minutes (whole cycles per loop)."""
    n = int((dur + 3.0) * SR)
    t = tt(n)
    out = np.zeros((2, n))
    for j, d in enumerate((-9, -3, 4, 10)):
        ph = phase(f, n, t0, d / 100, wob=0.8)
        dark, bright = saw(ph, f, 650), saw(ph, f, 2600)
        w = loop_lfo(t0 + t, 3, 0.4)
        y = (1 - w) * dark + w * bright
        out[j % 2] += y
    env = np.clip(t / 1.4, 0, 1) ** 2 * release(t, dur, 1.6)
    return 0.05 * vel * out * env


def moog_bass(f, dur, vel, t0):
    """Round, warm synth bass: saw + square under a low filter, soft attack, held."""
    n = int((dur + 1.0) * SR)
    t = tt(n)
    ph = phase(f, n, t0, wob=0.3)
    y = 0.6 * saw(ph, f, 260) + 0.5 * sum(np.sin(k * ph) / k for k in (1, 3, 5)) * 0.8 + 0.5 * np.sin(ph)
    y = np.tanh(1.3 * y)
    env = np.clip(t / 0.08, 0, 1) * (0.8 + 0.2 * np.exp(-t / 0.5)) * release(t, dur, 0.5)
    return 0.3 * vel * y * env


def synth_arp(f, dur, vel, t0):
    """Soft plucked synth: triangle-ish body, the brightness falls quickly (filter envelope)."""
    n = int(1.2 * SR)
    t = tt(n)
    ph = phase(f, n, t0, wob=0.6)
    y = sum(((-1) ** ((k - 1) // 2)) / k ** 2 * np.sin(k * ph) * np.exp(-t * (4 + 10 * k)) for k in (1, 3, 5, 7, 9))
    y += 0.25 * saw(ph, f, 1500) * np.exp(-t / 0.05)
    return 0.32 * vel * y * np.clip(t / 0.003, 0, 1) * np.exp(-t / 0.5)


def glide_lead(f, dur, vel, t0):
    """Warm monophonic synth lead: filtered saw + sine, slides up into each note, slow vibrato."""
    n = int((dur + 0.6) * SR)
    t = tt(n)
    vib = 0.1 * np.clip((t - 0.4) / 0.6, 0, 1) * np.sin(2 * np.pi * 4.2 * t)
    ph = phase(f, n, t0, -0.5 * np.exp(-t / 0.06) + vib, wob=0.5)
    y = 0.55 * saw(ph, f, 1700) + 0.6 * np.sin(ph)
    env = np.clip(t / 0.06, 0, 1) * release(t, dur, 0.25)
    return 0.22 * vel * y * env


# ------------------------------------------------------------------ material

CHORDS = {"D": "D F# A", "A/C#": "C# E A", "Bm": "B D F#", "A": "A C# E", "G": "G B D"}     # (first note: the bass)
CYCLE = ["D", "A/C#", "Bm", "A", "D", "A/C#", "G A", "D"]           # 8 bars; "G A": two beats of each


def chords_in(i):
    """The chords of bar i of the cycle: (first eighth, eighths long, chord)."""
    names = CYCLE[i].split()
    return [(k * 8 // len(names), 8 // len(names), ch) for k, ch in enumerate(names)]


# The melody, per bar: (eighth slot, length in eighths, note). A note said twice, then up a third; down to a long note
# and a leap back; the same from F#, leaping a sixth; one step down onto the leading note, and it waits there.
# The second half starts the same and closes: B, B, down to E, home to D.
SAY = [(0, 3, "F#4"), (3, 1, "F#4"), (4, 4, "A4")]
MELODY = [SAY, [(0, 6, "E4"), (6, 2, "A4")], [(0, 3, "F#4"), (3, 1, "F#4"), (4, 4, "D5")], [(0, 6, "C#5")],
          SAY, [(0, 6, "E4"), (6, 2, "A4")], [(0, 3, "B4"), (3, 1, "B4"), (4, 4, "E4")], [(0, 7, "D4")]]
PHRASE = [[(1.0 if s == 0 else 0.78 if n == 1 else 0.9, 0.012 if n >= 4 else 0.0) for s, n, _ in bar] for bar in MELODY]   # (velocity x, seconds late)
# The left hand: the chord, all its notes together, held. Never one note after another.
HAND = {"D": "D3 F#3 A3", "A/C#": "C#3 E3 A3", "Bm": "B2 D3 F#3", "A": "A2 E3 A3", "G": "G2 D3 B3"}


def pcs(ch):
    return [midi(p + "4") % 12 for p in CHORDS[ch].split()]


def place(pc, lo):
    return lo + (pc - lo) % 12


def hand_notes(ch):
    return [midi(n) for n in HAND[ch].split()]


def pad_voicing(ch):
    p = pcs(ch)
    return sorted(place(x, 50) for x in p[:3])   # three notes of the chord, D3..C#4: under the melody


# ------------------------------------------------------------------ the plan (11 blocks of 8 bars)
# keys: who plays the melody, pad level, bass
PLAN = [
    dict(name="the theme", mel="piano", pad=0.6, bass=0),
    dict(name="piano + bass", mel="piano", pad=0.8, bass=1),
    dict(name="chords alone", mel=None, pad=0.9, bass=1),
    dict(name="piano", mel="piano", pad=0.8, bass=1),
    dict(name="synth lead", mel="lead", pad=0.8, bass=1),
    dict(name="space", mel=None, pad=0.9, bass=0),
    dict(name="piano, close", mel="piano", pad=0.5, bass=1),
    dict(name="chords alone", mel=None, pad=0.9, bass=1),
    dict(name="piano + lead", mel="both", pad=0.8, bass=1),
    dict(name="fragments", mel="fragments", pad=0.8, bass=1),
    dict(name="space", mel=None, pad=0.9, bass=0),
]
assert len(PLAN) * 8 == BARS

STEMS = ["piano", "lead", "pad", "bass", "texture"]
events = []  # (t, dur, midi, vel, inst, pan, stem, rev, echo)


def note(slot, length, m, vel, inst, stem, pan=0.0, rev=0.25, echo=0.0, human=True, late=0.0):
    t0, dur = t_of(slot) + late, t_of(slot + length) - t_of(slot)
    if human:
        t0 += abs(rng.normal(0, 0.01))
        vel *= 1 + rng.normal(0, 0.06)
    events.append((t0, dur, m, vel, inst, pan, stem, rev, echo))


for bar in range(BARS):
    blk, i = bar // 8, bar % 8
    plan = PLAN[blk]
    ch = CYCLE[i]
    s0 = bar * 8

    # melody: always the same eight bars
    mel = plan["mel"]
    for (slot, ln, n), (touch, late) in zip(MELODY[i], PHRASE[i]):
        m = midi(n)
        if mel in ("piano", "both") or (mel == "fragments" and i in (0, 1, 4, 5)):
            note(s0 + slot, ln, m, 0.66 * touch, lofi_piano, "piano", 0.1, rev=0.3, echo=0.1, late=late)
        if mel in ("lead", "both"):
            note(s0 + slot, ln, m, (0.9 if mel == "lead" else 0.55) * touch, glide_lead, "lead", -0.1, rev=0.3, echo=0.25, late=late)

    for slot, ln, ch in chords_in(i):
        # the left hand: the whole chord at once, held; in a bar of one chord, its two upper notes again, softer, on the third beat
        hand = hand_notes(ch)
        for j, m in enumerate(hand):
            note(s0 + slot, ln, m, (0.4 if mel else 0.48) - 0.03 * j, lofi_piano, "piano", -0.3 + 0.15 * j, rev=0.35)
        if ln == 8 and (plan["bass"] or mel):
            for j, m in enumerate(hand[-2:]):
                note(s0 + 4, 4, m, 0.24, lofi_piano, "piano", -0.1 + 0.2 * j, rev=0.35)
        # pad: the triad
        for m in pad_voicing(ch):
            note(s0 + slot, ln, m, plan["pad"] * (1.0 if mel else 1.25), analog_pad, "pad", 0.0, rev=0.4, human=False)
        # bass: the chord's bass note, held
        if plan["bass"]:
            note(s0 + slot, ln - 0.5, place(pcs(ch)[0], 33), 0.85, moog_bass, "bass", 0.0, rev=0.05, human=False)


# ------------------------------------------------------------------ checks

def chord_at_time(t):
    bar, slot = divmod(t / (BEAT / 2) + 1e-6, 8)
    return [ch for a, n, ch in chords_in(int(bar) % 8) if a <= slot][-1]


def off_chord():
    """Melody notes that start on a beat and are not a note of the chord under them."""
    return [(i, n) for i in range(8) for slot, ln, n in MELODY[i] if slot % 2 == 0
            and midi(n) % 12 not in pcs([ch for a, _, ch in chords_in(i) if a <= slot][-1])]


def clash_report():
    """Melody notes against everything held under them: a semitone or a minor 9th, or a tritone or major 7th that is not in the chord."""
    low = min(midi(n) for bar in MELODY for *_, n in bar)
    held = [(t, t + d, m) for t, d, m, v, inst, *_ in events if m < low]
    bad = []
    for t, d, m, v, inst, *_ in events:
        if m < low:
            continue
        ch = chord_at_time(t)
        for a, b, h in held:
            if a <= t < b - 0.05:
                iv = (m - h) % 12
                if iv == 1 or (iv in (11, 6) and m % 12 not in pcs(ch)):
                    bad.append((round(t, 2), ch, m, h, iv))
    return bad


def accomp_clashes():
    out = []
    for ch in CHORDS:
        v = sorted(set(hand_notes(ch) + pad_voicing(ch)))
        out += [(ch, a, b) for a, b in zip(v, v[1:]) if b - a == 1]
    return out


def registers():
    return {"lowest melody": min(midi(n) for bar in MELODY for *_, n in bar),
            "highest accompaniment": max(max(hand_notes(c) + pad_voicing(c)) for c in CHORDS)}


def staircases():
    """Three melody notes in a row going the same way by step (a second): what the user cannot stand."""
    line = [midi(n) for bar in MELODY for *_, n in bar]
    line += line[:2]                                                   # (it loops)
    return [(k, line[k:k + 3]) for k in range(len(line) - 2)
            if 0 < abs(line[k + 1] - line[k]) <= 2 and 0 < abs(line[k + 2] - line[k + 1]) <= 2 and (line[k + 1] - line[k]) * (line[k + 2] - line[k + 1]) > 0]


# ------------------------------------------------------------------ render, one stem at a time

def circ(x, resp):
    return np.fft.irfft(np.fft.rfft(x, axis=-1) * resp(np.fft.rfftfreq(x.shape[-1], 1 / SR)), x.shape[-1], axis=-1)


def echo_fx(mono, beats=0.75, fb=0.45):
    d = int(beats * BEAT * SR)
    f = np.fft.rfftfreq(LOOP_N, 1 / SR)
    k = np.arange(len(f))
    z = fb * lp(2500, 1)(f) * hp(300, 1)(f) * np.exp(-2j * np.pi * k * d / LOOP_N)
    x = np.fft.rfft(mono)
    return 0.5 * np.stack([np.fft.irfft(x * z / (1 - z ** 2), LOOP_N), np.fft.irfft(x * z ** 2 / (1 - z ** 2), LOOP_N)])


def make_ir(seconds=5.0, tau_dark=0.65, tau_bright=0.22, predelay=0.03):
    n = int(seconds * SR)
    t = tt(n)
    irs = []
    for _ in range(2):
        dark = fft_filter(rng.standard_normal(n), lp(1800)) * np.exp(-t / tau_dark)
        bright = fft_filter(rng.standard_normal(n), hp(1800)) * np.exp(-t / tau_bright) * 0.4
        ir = (dark + bright) * np.clip(t / 0.08, 0, 1)
        ir[: int(predelay * SR)] = 0
        ir /= np.sqrt(np.sum(ir ** 2))
        padded = np.zeros(LOOP_N)
        padded[:n] = ir
        irs.append(np.fft.rfft(padded))
    return irs


def texture_bed():
    """Tape hiss and a breath of wind, both very low, slowly breathing."""
    t = np.arange(LOOP_N) / SR
    hiss = circ(rng.standard_normal((2, LOOP_N)), lambda f: bp(2000, 12000, 1)(f))
    wind = circ(rng.standard_normal((2, LOOP_N)), lambda f: bp(150, 900)(f) / np.sqrt(np.maximum(f, 20) / 150))
    return (0.006 * hiss / np.abs(hiss).max() + 0.012 * wind / np.abs(wind).max() * loop_lfo(t, 5)).astype(np.float32)


def limiter_gain(x, ceil=0.9, block=48):
    pk = np.abs(x).max(axis=0)
    nb = LOOP_N // block
    pb = pk[: nb * block].reshape(nb, block).max(axis=1)
    g = np.minimum(1, ceil / np.maximum(pb, 1e-9))
    w = 8
    gm = np.min([np.roll(g, s) for s in range(-w, w + 1)], axis=0)
    gs = np.mean([np.roll(gm, s) for s in range(-w // 2, w // 2 + 1)], axis=0)
    full = np.repeat(gs, block)
    return np.concatenate([full, np.full(LOOP_N - len(full), full[-1])]).astype(np.float32)


PLANE = {"piano": (1.0, 9000), "lead": (0.95, 8000), "pad": (0.8, 6000),
         "bass": (1.0, 2500), "texture": (1.0, 14000)}
GAINS = {"piano": 1.0, "lead": 1.0, "pad": 0.9, "bass": 0.5, "texture": 1.0}


def render_stem(stem, irs):
    n = LOOP_N + TAIL
    dry, rev, ech = np.zeros((2, n)), np.zeros((2, n)), np.zeros(n)
    for t, dur, m, vel, inst, pan, s, rs, es in events:
        if s != stem:
            continue
        y = np.atleast_2d(inst(hz(m), dur, vel, t))
        if y.shape[0] == 1:
            y = np.vstack([y, y])
        i = int(round(t * SR)) % LOOP_N
        y = y[:, : n - i]
        a = (pan + 1) * np.pi / 4
        y = y * np.array([[np.cos(a)], [np.sin(a)]]) * np.sqrt(2)
        dry[:, i:i + y.shape[1]] += y
        rev[:, i:i + y.shape[1]] += rs * y
        if es:
            ech[i:i + y.shape[1]] += es * y.mean(axis=0)

    def fold(x):
        out = x[..., :LOOP_N].copy()
        out[..., :TAIL] += x[..., LOOP_N:LOOP_N + TAIL]
        return out

    dry, rev, ech = fold(dry), fold(rev), fold(ech)
    echo = echo_fx(ech) if ech.any() else 0.0
    send = circ(rev + 0.4 * echo, hp(200, 1))
    wet = np.stack([np.fft.irfft(np.fft.rfft(send[c]) * irs[c], LOOP_N) for c in range(2)])
    dry_amt, dark = PLANE[stem]
    out = dry_amt * circ(dry, lp(dark, 1)) + echo + 0.7 * wet
    if stem == "texture":
        out = out + texture_bed()
    out = circ(out, hp(35, 2) if stem == "bass" else hp(90, 1))
    air = lambda f: 1 + (10 ** (2 / 20) - 1) / (1 + (2500 / np.maximum(f, 1)) ** 2)   # +2 dB shelf above 2.5 kHz (4 was harsh)
    out = circ(out * GAINS[stem], lambda f: hp(25, 2)(f) * lp(15000, 2)(f) * air(f))
    return out.astype(np.float32)


def render():
    irs = make_ir()
    stems = {}
    for s in STEMS:
        stems[s] = render_stem(s, irs)
        print(f"  rendered {s}", flush=True)
    pre = sum(stems.values())
    norm = np.float32(10 ** (-19 / 20) / np.sqrt(np.mean(pre.astype(np.float64) ** 2)))
    g = limiter_gain(pre * norm)
    for s in STEMS:
        stems[s] *= norm * g
    return sum(stems.values()), stems


def write_wav(path, x):
    pcm = (np.clip(x, -1, 1) * 32767).round().astype("<i2").T.copy()
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


if __name__ == "__main__":
    print("registers:", registers())
    print("staircases in the melody:", staircases())
    print("melody notes on a beat that are not in the chord:", off_chord())
    print("accompaniment semitone clusters:", accomp_clashes())
    bad = clash_report()
    print(f"clash check: {len(bad)}", bad[:12])
    master, stems = render()
    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("stem_*.wav"):
        old.unlink()
    write_wav(OUT / "master.wav", master)
    for s, x in stems.items():
        write_wav(OUT / f"stem_{s}.wav", x)
    meta = {"title": "Meadow Road", "by": "Fable 5.2", "bpm": BPM, "key": "D major", "mood": "calm ambient", "bars": BARS,
            "seconds": LOOP_S, "beats_per_hop": 2,
            "sections": [{"id": str(k + 1), "name": p["name"], "kind": "A" if p["mel"] else "rest",
                          "bar": k * 8, "t": k * 32 * BEAT} for k, p in enumerate(PLAN)],
            "stems": STEMS}
    (OUT / "track.json").write_text(json.dumps(meta, indent=1))
    rms = np.sqrt(np.mean(master.astype(np.float64) ** 2))
    print(f"{len(events)} notes, {LOOP_S:.0f}s loop, peak {np.abs(master).max():.3f}, rms {20 * np.log10(rms):.1f} dBFS")
    mono = master.mean(axis=0).astype(np.float64)
    nfft = 1 << 16
    fr = np.fft.rfftfreq(nfft, 1 / SR)
    P = sum(np.abs(np.fft.rfft(mono[k:k + nfft] * np.hanning(nfft))) ** 2 for k in range(0, len(mono) - nfft, nfft))
    print("  octave bands (dB of total):", "  ".join(f"{lo}:{10 * np.log10(P[(fr >= lo / 1.414) & (fr < lo * 1.414)].sum() / P.sum()):.0f}"
                                                       for lo in (63, 125, 250, 500, 1000, 2000, 4000, 8000)))
    blk = 8 * 4 * BEAT
    for s, x in list(stems.items()) + [("master", master)]:
        per = [20 * np.log10(np.sqrt(np.mean(x[:, int(k * blk * SR):int((k + 1) * blk * SR)].astype(np.float64) ** 2)) + 1e-9)
               for k in range(len(PLAN))]
        print(f"  {s:8s}", " ".join(f"{v:6.1f}" for v in per))
