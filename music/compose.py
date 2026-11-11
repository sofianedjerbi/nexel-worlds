"""Meadow Road: calm, neutral background music in the spirit of early sandbox-game ambient. ~4.9 min, seamless.

Fable 5.2 pass over the Opus 5.5 version (frozen in music/opus/). Same notes, same form. What changed:
  * touch: the melody is phrased (weight on arrivals, lighter passing notes, long notes placed a hair late)
  * tone: brighter felt piano with an audible hammer, two "mics" for real stereo, a more open pad, a +4 dB air shelf
  * motion: the arpeggio drifts in and out over two bars; the left hand answers softly under the melody's long notes
  * rests: about 3 dB louder, so they do not vanish at game volume

What the research on that style says, and how this file applies it:
  * music that "doesn't explain anything": no story sections, no marches, no climax
      -> one texture that slowly changes; layers enter and leave, the material never changes
  * very few chords on a soft synth pad, a simple melody that resolves and loops back
      -> three chords, two bars each (D, G, Bm, G); one melody of two 2-bar cells in a fifth (D5..A5),
         repeated exactly; variation only from instrument, register and presence
  * mostly electronic, piano recorded through a poor mic and heavily processed, analog synths
      -> lo-fi felt piano (band-limited, saturated, wobbly), detuned analog pad with a slowly breathing
         filter, a round Moog-style bass, a soft delayed synth arpeggio, a warm glide lead, tape hiss
  * silence and space matter -> the melody sits out regularly; no drums

Pure numpy, 48 kHz, 72 BPM, 88 bars = 293 s. Melody from bar 1. Checks: registers, clashes, loudness.

    uv run python music/compose.py      # writes music/site/audio/*.wav + track.json
"""

from pathlib import Path
import json
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
    """Felt piano through two cheap microphones: warm and a little gritty, but with the hammer and upper partials audible."""
    n = int((dur + 3.0) * SR)
    t = tt(n)
    bright = 2000 + 2600 * vel
    cents = rng.normal(0, 2.5)
    y = np.zeros(n)
    for k in range(1, 16):
        fk = k * np.sqrt(1 + 0.0004 * k * k)
        if f * fk > 9000:
            break
        tau = 4.5 / k ** 0.7 * (220 / max(f, 110)) ** 0.35
        y += (1 / k ** 1.1) / (1 + (f * fk / bright) ** 2) * np.sin(fk * phase(f, n, t0, cents / 100, wob=1.4)) \
            * (0.55 * np.exp(-t / (tau * 0.3)) + 0.45 * np.exp(-t / tau))
    y += fft_filter(rng.standard_normal(n), bp(250, 2500, 1)) * np.exp(-t / 0.01) * 0.07 * (0.5 + vel)   # felt hammer
    y = np.tanh(1.8 * y) / 1.8
    mic = lambda centre: (lambda fr: bp(110, 7000, 1)(fr) * (1 + 0.3 / (1 + ((fr - centre) / 500) ** 2)))
    left, right = fft_filter(y, mic(800)), np.roll(fft_filter(y, mic(1150)), 12)
    return 0.42 * vel * np.stack([left, right]) * np.clip(t / 0.004, 0, 1) * release(t, dur, 0.5)


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

CHORDS = {"Dmaj9": "D F# A C# E", "Gmaj9": "G B D F# A", "Bm7": "B D F# A"}
CYCLE = ["Dmaj9", "Dmaj9", "Gmaj9", "Gmaj9", "Bm7", "Bm7", "Gmaj9", "Gmaj9"]   # 8 bars, 3 chords

# the whole melody: two 2-bar cells. "ask" over D (and Bm), "settle" over G.
ASK = [[(0, 4, "F#5"), (4, 2, "E5"), (6, 2, "F#5")], [(0, 7, "A5")]]
SETTLE_OPEN = [[(0, 4, "F#5"), (4, 2, "E5"), (6, 2, "D5")], [(0, 7, "E5")]]
SETTLE_HOME = [[(0, 4, "F#5"), (4, 2, "E5"), (6, 2, "D5")], [(0, 7, "D5")]]
MELODY = ASK + SETTLE_OPEN + ASK + SETTLE_HOME   # 8 bars
PHRASE = [   # per bar, per note: (velocity x, seconds late). The notes never change; only the touch does.
    [(1.00, 0.0), (0.78, 0.004), (0.90, 0.0)], [(1.06, 0.022)],
    [(0.95, 0.0), (0.75, 0.004), (0.84, 0.006)], [(0.82, 0.030)],
    [(1.04, 0.0), (0.80, 0.004), (0.94, 0.0)], [(1.10, 0.022)],
    [(0.92, 0.0), (0.74, 0.004), (0.80, 0.008)], [(0.78, 0.040)],
]


def pcs(ch):
    return [midi(p + "4") % 12 for p in CHORDS[ch].split()]


def place(pc, lo):
    return lo + (pc - lo) % 12


def piano_chord(ch):
    """Open voicing under the melody: low root, fifth, then 3rd and colour (9th, or 7th on minor)."""
    p = pcs(ch)
    major = (p[1] - p[0]) % 12 == 4
    r = place(p[0], 38)                  # D2..C#3
    fifth = place(p[2], r + 1)
    third = place(p[1], 57)              # A3..G#4
    colour = place(p[4] if major and len(p) == 5 else p[3], 57)
    return [r, fifth] + sorted([third, colour])


def pad_voicing(ch):
    p = pcs(ch)
    return sorted(place(x, 59) for x in (p[0], p[1], p[2]))   # a plain triad, B3..A#4


def arp_notes(ch):
    p = pcs(ch)
    major = (p[1] - p[0]) % 12 == 4
    tones = [place(p[0], 50), place(p[2], 55), place(p[4] if major and len(p) == 5 else p[3], 60), place(p[1], 62)]
    return sorted(tones)


# ------------------------------------------------------------------ the plan (11 blocks of 8 bars)
# keys: melody voice, piano chords, pad, arp, bass
PLAN = [
    dict(name="piano", mel="piano", chords=True, pad=0.7, arp=0, bass=0),
    dict(name="piano + bass", mel="piano", chords=True, pad=0.8, arp=0, bass=1),
    dict(name="arpeggio", mel=None, chords=False, pad=0.9, arp=1, bass=1),
    dict(name="arpeggio + piano", mel="piano", chords=False, pad=0.8, arp=1, bass=1),
    dict(name="synth lead", mel="lead", chords=True, pad=0.8, arp=1, bass=1),
    dict(name="space", mel=None, chords=True, pad=0.9, arp=0, bass=0),
    dict(name="piano, close", mel="piano", chords=True, pad=0.5, arp=0, bass=1),
    dict(name="arpeggio", mel=None, chords=False, pad=0.9, arp=1, bass=1),
    dict(name="piano + lead", mel="both", chords=False, pad=0.8, arp=1, bass=1),
    dict(name="fragments", mel="fragments", chords=True, pad=0.8, arp=0, bass=1),
    dict(name="space", mel=None, chords=True, pad=0.9, arp=0, bass=0),
]
assert len(PLAN) * 8 == BARS

STEMS = ["piano", "lead", "pad", "arp", "bass", "texture"]
events = []  # (t, dur, midi, vel, inst, pan, stem, rev, echo)


def note(slot, length, m, vel, inst, stem, pan=0.0, rev=0.25, echo=0.0, human=True, late=0.0):
    t0, dur = t_of(slot) + late, t_of(slot + length) - t_of(slot)
    if human:
        t0 += abs(rng.normal(0, 0.01))
        vel *= 1 + rng.normal(0, 0.06)
    events.append((t0, dur, m, vel, inst, pan, stem, rev, echo))


def edge_fade(blk, i, slot, key):
    """Layers drift in and out over two bars instead of switching on at a block edge."""
    f = 1.0
    if not PLAN[(blk - 1) % len(PLAN)][key] and i < 2:
        f *= 0.35 + 0.65 * (i * 8 + slot) / 16
    if not PLAN[(blk + 1) % len(PLAN)][key] and i >= 6:
        f *= 0.35 + 0.65 * ((8 - i) * 8 - slot) / 16
    return f


for bar in range(BARS):
    blk, i = bar // 8, bar % 8
    plan = PLAN[blk]
    ch = CYCLE[i]
    s0 = bar * 8
    chord_start = i % 2 == 0

    # melody: always the same eight bars
    mel = plan["mel"]
    for (slot, ln, n), (touch, late) in zip(MELODY[i], PHRASE[i]):
        m = midi(n)
        if mel in ("piano", "both") or (mel == "fragments" and i in (0, 1, 4, 5)):
            note(s0 + slot, ln, m, 0.62 * touch, lofi_piano, "piano", 0.1, rev=0.3, echo=0.1, late=late)
        if mel in ("lead", "both"):
            note(s0 + slot, ln, m, (0.9 if mel == "lead" else 0.55) * touch, glide_lead, "lead", -0.1, rev=0.3, echo=0.25, late=late)

    # piano chords, struck softly and rolled, held two bars
    if plan["chords"] and chord_start:
        base = 0.38 if mel else 0.46          # a little more piano when it is alone, so the rests do not vanish
        for j, m in enumerate(piano_chord(ch)):
            note(s0 + j * 0.25, 16 - j * 0.25, m, base - 0.04 * j, lofi_piano, "piano", -0.3 + 0.15 * j, rev=0.35)
    if plan["chords"] and mel and i in (3, 7):   # under the melody's long note, the left hand answers softly
        top = piano_chord(ch)[2:]
        note(s0 + 4, 4, top[0], 0.2, lofi_piano, "piano", -0.05, rev=0.4)
        note(s0 + 4.3, 3.7, top[1], 0.18, lofi_piano, "piano", 0.1, rev=0.4)

    # pad: one triad per chord
    if chord_start:
        for m in pad_voicing(ch):
            note(s0, 16, m, plan["pad"] * (1.0 if mel else 1.25), analog_pad, "pad", 0.0, rev=0.4, human=False)

    # arpeggio: up and down the chord in eighths, quiet, through a dotted-eighth echo
    if plan["arp"]:
        a = arp_notes(ch)
        order = [0, 1, 2, 3, 2, 1, 2, 3]
        for slot in range(8):
            note(s0 + slot, 1, a[order[slot]], (0.55 if slot % 4 == 0 else 0.38) * edge_fade(blk, i, slot, "arp"), synth_arp, "arp",
                 -0.45 if slot % 2 else 0.45, rev=0.25, echo=0.4)

    # bass: one long root per chord
    if plan["bass"] and chord_start:
        note(s0, 15.5, place(pcs(ch)[0], 33), 0.85, moog_bass, "bass", 0.0, rev=0.05, human=False)


# ------------------------------------------------------------------ checks

def chord_at_time(t):
    return CYCLE[int(t / (4 * BEAT)) % 8]


def clash_report():
    held = [(t, t + d, m) for t, d, m, v, inst, *_ in events if m < 72]
    bad = []
    for t, d, m, v, inst, *_ in events:
        if m < 72:
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
        v = sorted(set(piano_chord(ch) + pad_voicing(ch) + arp_notes(ch)))
        out += [(ch, a, b) for a, b in zip(v, v[1:]) if b - a == 1]
    return out


def registers():
    return {"lowest melody": min(midi(n) for bar in MELODY for *_, n in bar),
            "highest accompaniment": max(max(piano_chord(c) + pad_voicing(c) + arp_notes(c)) for c in CHORDS)}


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


PLANE = {"piano": (1.0, 9000), "lead": (0.95, 8000), "pad": (0.8, 6000), "arp": (0.7, 6000),
         "bass": (1.0, 2500), "texture": (1.0, 14000)}
GAINS = {"piano": 1.0, "lead": 1.0, "pad": 0.9, "arp": 2.0, "bass": 0.5, "texture": 1.0}


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
    air = lambda f: 1 + (10 ** (4 / 20) - 1) / (1 + (2500 / np.maximum(f, 1)) ** 2)   # +4 dB shelf above 2.5 kHz: lifts the blanket
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
