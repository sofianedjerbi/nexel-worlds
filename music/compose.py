"""Quiet ambient loop to play under the game for 10-20 minutes. Cozy village x blocky meadow.

Pure numpy, 48 kHz, 75 BPM, 48 bars = 154 s, seamless. The theme starts in bar 1.

  * one key (D major), one 8-bar progression, a chord per bar, never changes
  * a recognisable theme: a rising-fifth hook (D5 -> A5, short-long-short) heard three times per phrase,
    call and answer, one high point, ending open on a sus chord that pulls back home
  * a rolling left-hand ostinato (3+3+2 accents) that carries the identity even without the theme
  * the theme plays in half the cycles; once doubled by a soft chiptune bell
  * layers on different cycle lengths (theme 8 bars, music box 12, glass swell 16): each pass differs a little
  * no drums, just a soft off-beat shaker and a plucked bass pulse under the theme; moderate reverb, piano up front; registers never overlap; clash check; all FX circular (no seam)

    uv run python music/compose.py      # writes music/site/audio/*.wav + track.json
"""

from pathlib import Path
import json
import wave

import numpy as np

SR = 48000
BPM = 75
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
    bright = 1100 + 1800 * vel
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
    env = np.clip(t / 0.004, 0, 1) * np.where(t > dur, np.exp(-(t - dur) / 0.35), 1.0)
    return 0.34 * vel * np.stack([out[0] + thump, out[1] + thump]) * env


def pad(f, dur, vel, t0):
    """Slow warm pad: detuned soft saws, very dark, wide; breathes in and out."""
    n = int((dur + 5.0) * SR)
    t = tt(n)
    voices = []
    for d in (-6, 0, 6):
        ph = phase(f, n, t0, d / 100)
        voices.append(sum(np.sin(k * ph) / k / (1 + (k * f / 1000) ** 2) for k in range(1, 10) if k * f < 4000))
    l, r = voices[0] + 0.5 * voices[1], voices[2] + 0.5 * voices[1]
    r = np.roll(r, int(0.015 * SR))
    env = np.clip(t / 0.9, 0, 1) ** 2 * np.where(t > dur, np.exp(-(t - dur) / 0.7), 1.0)
    return 0.045 * vel * np.stack([l, r]) * env


def swell(f, dur, vel, t0):
    """High, airy glass swell: sines with a slow rise and fall, far away."""
    n = int((dur + 4.0) * SR)
    t = tt(n)
    ph = phase(f, n, t0, wob=0.5)
    y = np.sin(ph) + 0.25 * np.sin(2 * ph + 0.3)
    return 0.05 * vel * y * np.sin(np.pi * np.clip(t / (dur + 4.0), 0, 1)) ** 2


def sub_bass(f, dur, vel, t0):
    """Round plucked bass: sine body plus a little 2nd/3rd harmonic so it reads on small speakers."""
    n = int((dur + 0.6) * SR)
    t = tt(n)
    ph = phase(f, n, t0, wob=0.3)
    y = np.sin(ph) + 0.28 * np.sin(2 * ph) * np.exp(-t / 0.25) + 0.1 * np.sin(3 * ph) * np.exp(-t / 0.12)
    env = np.clip(t / 0.01, 0, 1) * np.exp(-t / 1.1) * np.where(t > dur, np.exp(-(t - dur) / 0.12), 1.0)
    return 0.4 * vel * y * env


def _shaker():
    n = int(0.1 * SR)
    t = tt(n)
    return fft_filter(rng.standard_normal(n), bp(4500, 10000)) * np.clip(t / 0.012, 0, 1) * np.exp(-t / 0.03) * 0.06


SHAKERS = [_shaker() for _ in range(8)]


def shaker(f, dur, vel, t0):
    return vel * SHAKERS[rng.integers(len(SHAKERS))]


def music_box(f, dur, vel, t0):
    n = int(4.0 * SR)
    t = tt(n)
    y = (np.sin(2 * np.pi * f * t) * np.exp(-t / 1.6)
         + 0.2 * np.sin(2 * np.pi * f * 3.0 * t) * np.exp(-t / 0.25)
         + 0.06 * np.sin(2 * np.pi * f * 5.95 * t) * np.exp(-t / 0.07))
    return 0.16 * vel * y * np.clip(t / 0.003, 0, 1)


def chip_bell(f, dur, vel, t0):
    """Soft chiptune bell: a 25% pulse, filtered warm, quick bloom then a gentle hold."""
    n = int((dur + 1.2) * SR)
    t = tt(n)
    vib = 0.08 * np.clip((t - 0.35) / 0.4, 0, 1) * np.sin(2 * np.pi * 4.8 * t)
    ph = phase(f, n, t0, vib, wob=0.4)
    y = np.zeros(n)
    for k in range(1, 30):
        if k * f > 6000:
            break
        y += np.sin(np.pi * k * 0.25) / k * np.sin(k * ph) / (1 + (k * f / 2000) ** 2)
    env = np.clip(t / 0.008, 0, 1) * (0.45 + 0.55 * np.exp(-t / 0.35)) * np.where(t > dur, np.exp(-(t - dur) / 0.3), 1.0)
    return 0.2 * vel * y * env


# ------------------------------------------------------------------ harmony: one 8-bar cycle, a chord per bar

CHORDS = {"Dmaj9": "D F# A C# E", "Gmaj9": "G B D F# A", "Bm7": "B D F# A", "Gmaj7": "G B D F#",
          "Em9": "E G B D F#", "A7sus": "A D E G"}
PROG = ["Dmaj9", "Gmaj9", "Bm7", "Gmaj7", "Dmaj9", "Gmaj9", "Em9", "A7sus"]


def chord_at_bar(bar):
    return PROG[bar % 8]


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
    """Rootless 3rd, 5th, colour (9th on major, 7th otherwise): never the major 7th, which rubs under the theme."""
    p = pcs(ch)
    major = (p[1] - p[0]) % 12 == 4
    return sorted(place(x, 57) for x in (p[1], p[2], p[4] if major and len(p) == 5 else p[3]))


# ------------------------------------------------------------------ the theme
# Hook: a rising fifth D5 -> A5 in a short-long-short rhythm, three times. Call (bars 1-4) answers low,
# the second call (5-8) reaches once to B5, then rests on E over the sus chord, which pulls home to D.

THEME = [  # per bar: (slot, length in eighths, note)
    [(0, 2, "D5"), (2, 4, "A5"), (6, 2, "F#5")],     # Dmaj9   hook
    [(0, 3, "G5"), (3, 1, "F#5"), (4, 4, "D5")],     # Gmaj9
    [(0, 2, "D5"), (2, 4, "A5"), (6, 2, "F#5")],     # Bm7     hook again
    [(0, 3, "E5"), (3, 1, "D5"), (4, 4, "B4")],      # Gmaj7   answer, low
    [(0, 2, "D5"), (2, 4, "A5"), (6, 2, "F#5")],     # Dmaj9   hook
    [(0, 3, "B5"), (3, 1, "A5"), (4, 4, "G5")],      # Gmaj9   the one high point
    [(0, 3, "F#5"), (3, 1, "E5"), (4, 4, "D5")],     # Em9
    [(0, 8, "E5")],                                  # A7sus   open, leads home
]
# left-hand ostinato: one rolling figure per bar, accents in 3+3+2 (slots 0, 3, 6)
OSTINATO = [(0, "r", 1.0), (1, "fifth", 0.7), (2, "color", 0.65), (3, "third", 0.85),
            (4, "color", 0.6), (5, "fifth", 0.6), (6, "third", 0.8), (7, "color", 0.55)]

PLAN = ["theme", "theme+chip", "open", "theme", "chip solo", "fragments"]   # one entry per 8-bar cycle
SECTION_NAMES = ["theme", "theme + chip", "breather", "theme", "chip solo", "fragments"]

# ------------------------------------------------------------------ arrangement

STEMS = ["piano", "chip", "pad", "bass", "musicbox", "texture"]
events = []  # (t, dur, midi, vel, inst, pan, stem, rev, echo)


def note(slot, length, m, vel, inst, stem, pan=0.0, rev=0.3, echo=0.0, human=True):
    t0, dur = t_of(slot), t_of(slot + length) - t_of(slot)
    if human:
        t0 += abs(rng.normal(0, 0.01))
        vel *= 1 + rng.normal(0, 0.05)
    events.append((t0, dur, m, vel, inst, pan, stem, rev, echo))


for bar in range(BARS):
    cyc, i = bar // 8, bar % 8
    ch = chord_at_bar(bar)
    s0 = bar * 8
    plan = PLAN[cyc]

    # theme
    themed = plan in ("theme", "theme+chip", "chip solo")
    if themed or (plan == "fragments" and i in (0, 2, 4)):
        for slot, ln, n in THEME[i]:
            if plan == "fragments" and slot > 2:
                ln = ln + 2   # let the hook ring out, then nothing
            if plan != "chip solo":
                note(s0 + slot, ln, midi(n), 0.7 if plan != "fragments" else 0.5, felt_piano, "piano", 0.1,
                     rev=0.22, echo=0.08)
            if plan in ("theme+chip", "chip solo"):
                note(s0 + slot, ln, midi(n), 0.75 if plan == "theme+chip" else 1.0, chip_bell, "chip", 0.2,
                     rev=0.25, echo=0.22)
            if plan == "fragments" and slot > 2:
                break

    # left-hand ostinato, pedal held through the bar; softer under the theme and in the open section
    lh = dict(zip(("r", "fifth", "color", "third"), lh_notes(ch)))
    level = {"theme": 0.27, "theme+chip": 0.26, "chip solo": 0.3, "open": 0.32, "fragments": 0.3}[plan]
    for slot, which, acc in OSTINATO:
        if plan == "open" and slot % 2:
            continue   # half the notes: the figure breathes
        note(s0 + slot, 8 - slot, lh[which], level * acc, felt_piano, "piano", -0.35 + 0.08 * slot, rev=0.25)

    for m in pad_voicing(ch):
        note(s0, 8, m, 0.8, pad, "pad", 0.0, rev=0.35, human=False)

    # bass: a gentle pulse on beats 1 and 3 (root, then fifth on the chord's way out)
    root = place(pcs(ch)[0], 33)
    note(s0, 3, root, 0.8, sub_bass, "bass", 0.0, rev=0.05, human=False)
    if plan != "open":
        note(s0 + 4, 2, root + 7 if i % 2 else root, 0.6, sub_bass, "bass", 0.0, rev=0.05, human=False)

    # a soft off-beat shaker while the theme plays: a little bounce, nothing more
    if themed:
        for slot in (1, 3, 5, 7):
            note(s0 + slot, 1, 60, 0.9 if slot in (3, 7) else 0.6, shaker, "texture", 0.35, rev=0.1)

# music box: a 12-bar cycle against the 8-bar harmony, answering the hook from far away
BOX = [(1, 4, "A5"), (1, 6, "D6"), (5, 4, "A5"), (9, 2, "D6"), (9, 4, "B5")]   # (bar in 12, slot, note)
for rep in range(BARS // 12):
    for b, slot, n in BOX:
        bar = rep * 12 + b
        if PLAN[bar // 8] in ("theme", "theme+chip", "chip solo") and slot >= 4:
            continue   # keep out of the theme's way
        note(bar * 8 + slot, 2, midi(n), 0.55, music_box, "musicbox", rng.uniform(-0.8, 0.8), rev=0.8, echo=0.5)

# high glass swell, far away
for start in (16, 40):   # only in the breathers
    note(start * 8, 40, midi("F#5"), 0.9, swell, "texture", -0.4, rev=0.7, human=False)
    note(start * 8 + 4, 36, midi("A5"), 0.7, swell, "texture", 0.4, rev=0.7, human=False)


# ------------------------------------------------------------------ checks

def clash_report():
    """Melody / music box / swell vs sounding chord tones: flag minor 9ths, and off-chord semitones or tritones."""
    held = [(t, t + d, m) for t, d, m, v, inst, *_ in events if inst in (pad, felt_piano, sub_bass) and m < 69]
    bad = []
    for t, d, m, v, inst, pan, stem, *_ in events:
        if inst is shaker or not (stem in ("musicbox", "texture", "chip") or (inst is felt_piano and m >= 69)):
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
    return {"lowest melody": low_mel, "highest left hand": max(max(lh_notes(c)) for c in PROG),
            "highest pad": max(max(pad_voicing(c)) for c in PROG)}


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


def make_ir(seconds=5.0, tau_dark=0.55, tau_bright=0.22, predelay=0.025):
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
    return 0.012 * air / np.abs(air).max() * breathe


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
    plane = {"piano": (1.0, 7000), "chip": (0.85, 6000), "pad": (0.75, 3500), "bass": (1.0, 1200), "musicbox": (0.45, 4500), "texture": (0.9, 10000)}
    stems = {}
    for s in STEMS:
        b = {k: fold(v) for k, v in buses[s].items()}
        echo = echo_fx(b["echo"].mean(axis=0))
        send = circ(b["rev"] + 0.5 * echo, hp(180, 1))
        wet = np.stack([np.fft.irfft(np.fft.rfft(send[c]) * irs[c], LOOP_N) for c in range(2)])
        dry_amt, dark = plane[s]
        stems[s] = dry_amt * circ(b["dry"], lp(dark, 1)) + echo + 0.7 * wet
    stems["texture"] = stems["texture"] + wind_bed()

    stems["bass"] = circ(stems["bass"], lambda f: hp(30, 2)(f) * lp(900, 2)(f))
    for s in ("piano", "chip", "pad", "musicbox"):
        stems[s] = circ(stems[s], hp(110, 1))
    gains = {"piano": 1.0, "chip": 1.3, "pad": 0.8, "bass": 0.7, "musicbox": 0.8, "texture": 0.9}
    for s in STEMS:
        stems[s] = circ(stems[s] * gains[s], lambda f: hp(25, 2)(f) * lp(13000, 2)(f))

    pre = sum(stems.values())
    norm = 10 ** (-19 / 20) / np.sqrt(np.mean(pre ** 2))
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
    meta = {"title": "Meadow Afternoon", "bpm": BPM, "key": "D major", "mood": "cozy ambient", "bars": BARS,
            "seconds": LOOP_S, "beats_per_hop": 2,
            "sections": [{"id": str(k + 1), "name": nm, "bar": k * 8, "t": k * 32 * BEAT} for k, nm in enumerate(SECTION_NAMES)],
            "stems": STEMS}
    (OUT / "track.json").write_text(json.dumps(meta, indent=1))
    rms = np.sqrt(np.mean(master ** 2))
    print(f"{len(events)} notes, {LOOP_S:.0f}s loop, peak {np.abs(master).max():.3f}, rms {20 * np.log10(rms):.1f} dBFS")
    for s, x in stems.items():
        print(f"  {s:9s} rms {20 * np.log10(np.sqrt(np.mean(x ** 2)) + 1e-12):6.1f} dBFS")
