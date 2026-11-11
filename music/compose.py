"""Chill ambient town loop for playing: a cozy village crossed with a quiet, blocky meadow.

Pure numpy, 48 kHz, 80 BPM, 32 bars = 96 s, seamless.

Rules this track follows (best practice for background game music):
  * one key (D major), one 8-bar diatonic progression for the whole loop
  * one 2-bar pentatonic motif, repeated as A A' A B; no wandering lines
  * every part owns a register: bass < piano accompaniment < pad < melody < twinkles
  * a clash check: any melody note a semitone or a tritone from a sounding chord tone is reported
  * depth in three planes: near (piano), middle (pad, bass), far (twinkles: dark, wet, wide)
  * everything circular (reverb, echo, wind bed, tape wobble) so the loop has no seam

Sections, all on the same progression:
  1 morning   pad, bass, broken piano chords, far twinkles, wind
  2 stroll    + the piano melody, a soft shaker
  3 breeze    melody moves to a soft chip flute, piano answers, a heartbeat kick
  4 dusk      the piano melody once more, thinner, settling back into the morning

    uv run python music/compose.py      # writes music/site/audio/*.wav + track.json
"""

from pathlib import Path
import json
import wave

import numpy as np

SR = 48000
BPM = 80
BEAT = 60 / BPM
BARS = 32
LOOP_S = BARS * 4 * BEAT
LOOP_N = int(round(LOOP_S * SR))
TAIL = 8 * SR
OUT = Path(__file__).with_name("site") / "audio"
rng = np.random.default_rng(3)

PC = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


def midi(name):
    pc, rest = PC[name[0]], name[1:]
    while rest and rest[0] in "#b":
        pc += 1 if rest[0] == "#" else -1
        rest = rest[1:]
    return 12 * (int(rest) + 1) + pc


def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def t_of(slot):  # straight eighths, 8 per bar
    return slot * BEAT / 2


def tt(n):
    return np.arange(n) / SR


def fft_filter(y, resp):
    n = len(y)
    m = 1 << int(np.ceil(np.log2(n + 2048)))
    spec = np.fft.rfft(y, m) * resp(np.fft.rfftfreq(m, 1 / SR))
    return np.fft.irfft(spec, m)[:n]


def lp(fc, order=2):
    return lambda f: 1 / np.sqrt(1 + (f / fc) ** (2 * order))


def hp(fc, order=2):
    return lambda f: 1 / np.sqrt(1 + (fc / np.maximum(f, 1e-3)) ** (2 * order))


def bp(lo, hi):
    return lambda f: hp(lo)(f) * lp(hi)(f)


def wobble(t_abs, depth=1.0):
    """Tape wow in semitones; rates are whole cycles per loop, so it is seamless."""
    return depth * (0.05 * np.sin(2 * np.pi * 34 / LOOP_S * t_abs) + 0.03 * np.sin(2 * np.pi * 11 / LOOP_S * t_abs + 1))


def phase(f, n, t0, extra=0.0, wob=1.0):
    semis = wobble(t0 + tt(n), wob) + extra
    return 2 * np.pi * np.cumsum(f * 2 ** (semis / 12)) / SR


# ------------------------------------------------------------------ instruments (f, dur, vel, t0)

def felt_piano(f, dur, vel, t0):
    """Soft felt piano: slightly inharmonic partials, dark hammer, long ring, tiny stereo detune."""
    n = int((dur + 2.5) * SR)
    t = tt(n)
    bright = 1400 + 1800 * vel
    out = []
    for det in (-1.2, 1.2):  # cents, left / right
        ph = phase(f, n, t0, det / 100)
        y = np.zeros(n)
        for k in range(1, 14):
            fk = k * np.sqrt(1 + 0.00035 * k * k)
            if f * fk > 9000:
                break
            amp = (1 / k ** 1.3) / (1 + (f * fk / bright) ** 2)
            tau = 3.2 / k ** 0.75 * (220 / max(f, 110)) ** 0.35
            y += amp * np.sin(fk * ph) * (0.7 * np.exp(-t / (tau * 0.25)) + 0.3 * np.exp(-t / tau))
        out.append(y)
    thump = fft_filter(rng.standard_normal(n), lp(900)) * np.exp(-t / 0.015) * 0.15
    damper = np.where(t > dur, np.exp(-(t - dur) / 0.35), 1.0)
    env = np.clip(t / 0.004, 0, 1) * damper
    return 0.32 * vel * np.stack([out[0] + thump, out[1] + thump]) * env


def chip_flute(f, dur, vel, t0):
    """Soft triangle-ish chip voice with delayed vibrato: the cozy village part of the blend."""
    n = int((dur + 0.6) * SR)
    t = tt(n)
    vib = 0.13 * np.clip((t - 0.3) / 0.4, 0, 1) * np.sin(2 * np.pi * 5.0 * t)
    ph = phase(f, n, t0, vib, wob=0.5)
    y = np.sin(ph) + 0.18 * np.sin(2 * ph) + 0.1 * np.sin(3 * ph) + 0.04 * np.sin(5 * ph)
    env = np.clip(t / 0.06, 0, 1) * np.where(t > dur, np.exp(-(t - dur) / 0.18), 1.0) * (0.85 + 0.15 * np.exp(-t / 0.3))
    return 0.22 * vel * y * env


def pad(f, dur, vel, t0):
    """Warm slow pad: three detuned soft saws, dark, wide (haas)."""
    n = int((dur + 3.0) * SR)
    t = tt(n)
    voices = []
    for d in (-7, 0, 7):
        ph = phase(f, n, t0, d / 100)
        y = sum(np.sin(k * ph) / k / (1 + (k * f / 900) ** 2) for k in range(1, 12) if k * f < 6000)
        voices.append(y)
    l, r = voices[0] + 0.5 * voices[1], voices[2] + 0.5 * voices[1]
    r = np.roll(r, int(0.013 * SR))
    env = np.clip(t / 1.6, 0, 1) ** 2 * np.where(t > dur, np.exp(-(t - dur) / 1.2), 1.0)
    return 0.07 * vel * np.stack([l, r]) * env


def sub_bass(f, dur, vel, t0):
    n = int((dur + 1.0) * SR)
    t = tt(n)
    ph = phase(f, n, t0, wob=0.3)
    y = np.sin(ph) + 0.12 * np.sin(2 * ph) + 0.03 * np.sin(3 * ph)
    env = np.clip(t / 0.08, 0, 1) * (0.75 + 0.25 * np.exp(-t / 0.6)) * np.where(t > dur, np.exp(-(t - dur) / 0.4), 1.0)
    return 0.45 * vel * y * env


def music_box(f, dur, vel, t0):
    n = int(3.0 * SR)
    t = tt(n)
    y = (np.sin(2 * np.pi * f * t) * np.exp(-t / 1.1)
         + 0.25 * np.sin(2 * np.pi * f * 3.0 * t) * np.exp(-t / 0.2)
         + 0.08 * np.sin(2 * np.pi * f * 5.95 * t) * np.exp(-t / 0.06))
    return 0.2 * vel * y * np.clip(t / 0.002, 0, 1)


def _shaker():
    n = int(0.12 * SR)
    t = tt(n)
    return fft_filter(rng.standard_normal(n), bp(4000, 9000)) * np.clip(t / 0.02, 0, 1) * np.exp(-t / 0.04) * 0.07


def _soft_kick():
    n = int(0.6 * SR)
    t = tt(n)
    fr = 52 + 40 * np.exp(-t / 0.04)
    return np.sin(2 * np.pi * np.cumsum(fr) / SR) * np.exp(-t / 0.25) * np.clip(t / 0.004, 0, 1) * 0.35


def _tick():
    n = int(0.1 * SR)
    t = tt(n)
    y = np.sin(2 * np.pi * 1800 * t) * 0.5 + fft_filter(rng.standard_normal(n), bp(2000, 6000)) * 0.4
    return y * np.exp(-t / 0.012) * 0.1


DRUMS = {"shaker": [_shaker() for _ in range(8)], "kick": [_soft_kick() for _ in range(2)], "tick": [_tick() for _ in range(3)]}


def drum(kind):
    def play(f, dur, vel, t0):
        v = DRUMS[kind]
        return vel * v[rng.integers(len(v))]
    return play


# ------------------------------------------------------------------ harmony

CHORDS = {  # all diatonic to D major
    "Dmaj9": "D F# A C# E", "Gmaj9": "G B D F# A", "Bm9": "B D F# A C#", "Gmaj7": "G B D F#",
    "Em9": "E G B D F#", "A7sus": "A D E G",
}
PROG = ["Dmaj9", "Gmaj9", "Bm9", "Gmaj7", "Dmaj9", "Gmaj9", "Em9", "A7sus"]


def pcs(ch):
    return [midi(p + "4") % 12 for p in CHORDS[ch].split()]


def place(pc, lo):
    return lo + (pc - lo) % 12


# broken-chord accompaniment, low register: root, fifth, colour, third-an-octave-up.
# colour = the 9th on major chords; on minor/sus chords the 7th (a 9th there sits a semitone from the 3rd)
def accomp_notes(ch):
    p = pcs(ch)
    major = (p[1] - p[0]) % 12 == 4
    r = place(p[0], 43)            # G2..F#3
    fifth = place(p[2], r + 1)
    color = place(p[4] if major and len(p) == 5 else p[3], fifth + 1)
    third = place(p[1], color + 1)
    return r, fifth, color, third


def accomp_clashes():
    out = []
    for ch in set(PROG):
        v = sorted(accomp_notes(ch) + tuple(pad_voicing(ch)))
        out += [(ch, a, b) for a, b in zip(v, v[1:]) if b - a == 1]
    return out


def pad_voicing(ch):
    return sorted(place(p, 62) for p in pcs(ch)[1:4])   # D4..C#5, rootless


# ------------------------------------------------------------------ melody: one motif, A A' A B

MOTIF = [  # (slot in bar, length, note) per bar of the 8-bar progression
    [(2, 1, "F#5"), (3, 1, "A5"), (4, 2, "B5"), (6, 2, "A5")],            # Dmaj9   A
    [(0, 4, "F#5"), (4, 2, "E5"), (6, 2, "D5")],                          # Gmaj9
    [(2, 1, "F#5"), (3, 1, "A5"), (4, 2, "B5"), (6, 2, "A5")],            # Bm9     A'
    [(0, 2, "E5"), (2, 2, "F#5"), (4, 4, "D5")],                          # Gmaj7
    [(2, 1, "F#5"), (3, 1, "A5"), (4, 2, "B5"), (6, 2, "A5")],            # Dmaj9   A
    [(0, 4, "D6"), (4, 2, "B5"), (6, 2, "A5")],                           # Gmaj9   (lifts)
    [(0, 2, "B5"), (2, 2, "A5"), (4, 2, "F#5"), (6, 2, "E5")],            # Em9     B
    [(0, 6, "E5")],                                                       # A7sus   (rests on E)
]
# the piano's answer in the breeze section: the motif's tail, an octave down, in the gaps
ANSWER = {1: [(4, 2, "A4"), (6, 2, "F#4")], 3: [(4, 2, "B4"), (6, 2, "A4")],
          5: [(4, 2, "B4"), (6, 2, "D5")], 7: [(4, 2, "D5"), (6, 2, "A4")]}

# ------------------------------------------------------------------ arrangement

STEMS = ["piano", "lead", "pad", "bass", "twinkles", "texture"]
SECTIONS = [("1", "morning", 0), ("2", "stroll", 8), ("3", "breeze", 16), ("4", "dusk", 24)]
events = []  # (t, dur, midi, vel, inst, pan, stem, rev, echo)


def note(slot, length, m, vel, inst, stem, pan=0.0, rev=0.3, echo=0.0, human=True):
    t0, dur = t_of(slot), t_of(slot + length) - t_of(slot)
    if human:
        t0 += abs(rng.normal(0, 0.006))
        vel *= 1 + rng.normal(0, 0.05)
    events.append((t0, dur, m, vel, inst, pan, stem, rev, echo))


# twinkles: one sparse 8-bar pattern, reused every pass (repetition), pentatonic chord tones only
PENTA = {midi(n) % 12 for n in "D4 E4 F#4 A4 B4".split()}
twinkle_pattern = []
for i, ch in enumerate(PROG):
    good = [m for m in range(midi("D6"), midi("B6") + 1) if m % 12 in PENTA and m % 12 in pcs(ch)]
    for slot in sorted(rng.choice([1, 3, 5, 6, 7], size=2, replace=False)):
        twinkle_pattern.append((i, int(slot), int(rng.choice(good)), float(rng.uniform(-0.8, 0.8))))

for bar in range(BARS):
    sec, i = bar // 8, bar % 8
    ch = PROG[i]
    s0 = bar * 8

    # melody
    if sec in (1, 3):
        for slot, ln, n in MOTIF[i]:
            v = 0.62 if sec == 1 else 0.52
            note(s0 + slot, ln + 1.5, midi(n), v, felt_piano, "piano", 0.05, rev=0.35, echo=0.12)
    if sec == 2:
        for slot, ln, n in MOTIF[i]:
            note(s0 + slot, ln, midi(n), 0.9, chip_flute, "lead", -0.05, rev=0.4, echo=0.3)
        for slot, ln, n in ANSWER.get(i, []):
            note(s0 + slot, ln + 1, midi(n), 0.4, felt_piano, "piano", 0.3, rev=0.4, echo=0.1)

    # piano accompaniment: pedal held through the bar; thinner at dusk
    r, fifth, color, third = accomp_notes(ch)
    pattern = [(0, r, 0.5), (1, fifth, 0.38), (2, color, 0.34), (3, third, 0.32), (5, fifth + 12 if fifth + 12 < 72 else fifth, 0.26)]
    if sec == 3 and i % 2:
        pattern = pattern[:3]
    for slot, m, v in pattern:
        note(s0 + slot, 8 - slot, m, v, felt_piano, "piano", -0.25 + 0.1 * slot, rev=0.4)

    # pad, every bar, crossfading through its slow release
    for j, m in enumerate(pad_voicing(ch)):
        note(s0, 8, m, 0.8 if sec != 3 else 0.65, pad, "pad", 0.0, rev=0.5, human=False)

    # bass: one deep root per bar, a soft fifth on beat 3 in the middle sections
    root = place(pcs(ch)[0], 33)   # A1..G#2
    note(s0, 5 if sec in (1, 2) else 8, root, 0.85, sub_bass, "bass", 0.0, rev=0.05, human=False)
    if sec in (1, 2):
        note(s0 + 5, 3, root + 7, 0.5, sub_bass, "bass", 0.0, rev=0.05, human=False)

    # far twinkles: same pattern each pass, quiet; a little more in morning and breeze
    for bi, slot, m, pan in twinkle_pattern:
        if bi == i:
            v = 0.5 if sec in (0, 2) else 0.32
            note(s0 + slot, 1, m, v, music_box, "twinkles", pan, rev=0.7, echo=0.45)

    # texture: soft shaker in stroll + breeze, heartbeat kick and ticks in breeze
    if sec in (1, 2):
        for s in range(8):
            note(s0 + s, 1, 60, 0.9 if s % 2 else 0.55, drum("shaker"), "texture", 0.4, rev=0.2)
    if sec == 2:
        note(s0, 1, 60, 0.9, drum("kick"), "texture", 0.0, rev=0.05)
        note(s0 + 4, 1, 60, 0.6, drum("kick"), "texture", 0.0, rev=0.05)
        for s in (2, 6):
            note(s0 + s, 1, 60, 0.8, drum("tick"), "texture", -0.3, rev=0.4)


# ------------------------------------------------------------------ clash check

def clash_report():
    """Melody/lead notes vs everything sounding at the same moment from pad + accompaniment."""
    held = [(t, t + d, m) for t, d, m, v, inst, *_ in events if inst in (pad, felt_piano) and m < 72]
    bad = []
    for t, d, m, v, inst, pan, stem, *_ in events:
        if stem != "lead" and not (inst is felt_piano and m >= 72):
            continue
        for a, b, h in held:
            if a <= t < b - 0.05:
                iv = (m - h) % 12
                in_chord = m % 12 in pcs(PROG[int(t / (4 * BEAT)) % 8])
                if iv == 1 or (iv in (11, 6) and not in_chord):   # b9 always sours; others only off-chord
                    bad.append((round(t, 2), m, h, iv))
    return bad


# ------------------------------------------------------------------ render

def fold(x):
    out = x[:, :LOOP_N].copy()
    out[:, :TAIL] += x[:, LOOP_N:LOOP_N + TAIL]
    return out


def circ(x, resp):
    spec = np.fft.rfft(x, axis=-1)
    return np.fft.irfft(spec * resp(np.fft.rfftfreq(LOOP_N, 1 / SR)), LOOP_N, axis=-1)


def echo_fx(mono, beats=0.75, fb=0.45):
    d = int(beats * BEAT * SR)
    f = np.fft.rfftfreq(LOOP_N, 1 / SR)
    k = np.arange(len(f))
    z = fb * lp(2800, 1)(f) * hp(300, 1)(f) * np.exp(-2j * np.pi * k * d / LOOP_N)
    x = np.fft.rfft(mono)
    return 0.55 * np.stack([np.fft.irfft(x * z / (1 - z ** 2), LOOP_N), np.fft.irfft(x * z ** 2 / (1 - z ** 2), LOOP_N)])


def make_ir(seconds=6.0, tau_dark=0.85, tau_bright=0.3, predelay=0.035):
    n = int(seconds * SR)
    t = tt(n)
    irs = []
    for _ in range(2):
        dark = fft_filter(rng.standard_normal(n), lp(1800)) * np.exp(-t / tau_dark)
        bright = fft_filter(rng.standard_normal(n), hp(1800)) * np.exp(-t / tau_bright) * 0.5
        ir = (dark + bright) * np.clip(t / 0.08, 0, 1)   # soft build: diffuse, no slap
        ir[: int(predelay * SR)] = 0
        ir /= np.sqrt(np.sum(ir ** 2))
        padded = np.zeros(LOOP_N)
        padded[:n] = ir
        irs.append(np.fft.rfft(padded))
    return irs


def wind_bed():
    """Quiet outdoor air: band-limited noise breathing slowly (whole cycles per loop)."""
    t = np.arange(LOOP_N) / SR
    noise = rng.standard_normal((2, LOOP_N))
    air = circ(noise, lambda f: bp(180, 1400)(f) / np.sqrt(np.maximum(f, 20) / 180))
    swell = 0.55 + 0.45 * np.sin(2 * np.pi * 3 / LOOP_S * t) * np.sin(2 * np.pi * 7 / LOOP_S * t + 0.7)
    air = air / np.abs(air).max()
    return 0.035 * air * swell


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
    # depth planes: how much dry signal survives and how dark it is (far = dark + wet)
    plane = {"piano": (1.0, 9000), "lead": (0.9, 7000), "pad": (0.8, 3500), "bass": (1.0, 2000),
             "twinkles": (0.35, 4500), "texture": (0.8, 8000)}
    stems = {}
    for s in STEMS:
        b = {k: fold(v) for k, v in buses[s].items()}
        echo = echo_fx(b["echo"].mean(axis=0))
        send = circ(b["rev"] + 0.5 * echo, hp(200, 1))
        wet = np.stack([np.fft.irfft(np.fft.rfft(send[c]) * irs[c], LOOP_N) for c in range(2)])
        dry_amt, dark = plane[s]
        dry = circ(b["dry"], lp(dark, 1))
        stems[s] = dry_amt * dry + echo + 1.1 * wet
    stems["texture"] = stems["texture"] + wind_bed()

    stems["bass"] = circ(stems["bass"], lambda f: hp(30, 2)(f) * lp(1500, 2)(f))
    for s in ("piano", "lead", "pad", "twinkles"):
        stems[s] = circ(stems[s], hp(90, 1))
    gains = {"piano": 1.0, "lead": 0.95, "pad": 0.7, "bass": 0.85, "twinkles": 0.8, "texture": 0.8}
    for s in STEMS:
        stems[s] = circ(stems[s] * gains[s], lambda f: hp(25, 2)(f) * lp(15000, 2)(f))

    pre = sum(stems.values())
    norm = 10 ** (-18 / 20) / np.sqrt(np.mean(pre ** 2))   # chill level: -18 dBFS RMS, room to breathe
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
    bad = clash_report()
    print("accompaniment semitone clusters:", accomp_clashes())
    print(f"clash check: {len(bad)} melody notes a semitone/tritone from a sounding chord tone", bad[:10])
    master, stems = render()
    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("stem_*.wav"):
        old.unlink()
    write_wav(OUT / "master.wav", master)
    for s, x in stems.items():
        write_wav(OUT / f"stem_{s}.wav", x)
    meta = {"title": "Meadow Afternoon", "bpm": BPM, "key": "D major", "mood": "chill ambient", "bars": BARS,
            "seconds": LOOP_S, "beats_per_hop": 2,
            "sections": [{"id": a, "name": b, "bar": c, "t": c * 4 * BEAT} for a, b, c in SECTIONS],
            "stems": STEMS}
    (OUT / "track.json").write_text(json.dumps(meta, indent=1))
    rms = np.sqrt(np.mean(master ** 2))
    print(f"{len(events)} notes, {LOOP_S:.0f}s loop, peak {np.abs(master).max():.3f}, rms {20 * np.log10(rms):.1f} dBFS")
    for s, x in stems.items():
        print(f"  {s:9s} rms {20 * np.log10(np.sqrt(np.mean(x ** 2)) + 1e-12):6.1f} dBFS")
