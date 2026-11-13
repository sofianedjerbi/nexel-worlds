"""Plays recorded instruments (music/samples, fetched by fetch_samples.py) instead of synthesising them: the user heard
the synthesised ones as "MIDI default Windows samples". Each voice is called like the old ones: (f, dur, vel, t0).

A note picks the nearest recorded pitch and the dynamic layer nearest its velocity, is re-pitched by resampling
(a third at most for most instruments), and keeps the recording's own attack. Held instruments are looped inside
their steady part when the note is longer than the recording.      uv run python music/sampler.py   (builds the cache)"""
from pathlib import Path
import os
import pickle
import re
import wave

import numpy as np

SR = 48000
HERE = Path(__file__).with_name("samples")
RAW, CACHE = HERE / "raw", HERE / "cache"
PC = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
LAYER = {"soft": 1, "med": 2, "loud": 3, "pp": 1, "mp": 2, "mf": 2, "f": 3, "ff": 4}
# kind: "ring" rings out and is damped after the note; "held" lasts as long as the note; "hit" has no pitch
KIT = {  # name: (folders, kind, release s, gain, loop crossfade s, keep only files matching)
    "guitar": (["guitar"], "ring", 0.30, 1.0, 0, None),
    "marimba": (["marimba"], "ring", 0.25, 1.0, 0, None),
    "vibes": (["vibes"], "ring", 0.45, 1.0, 0, None),
    "harp": (["harp"], "ring", 0.35, 1.0, 0, None),
    "bass": (["bass"], "ring", 0.15, 1.0, 0, None),
    "cellopizz": (["cellopizz"], "ring", 0.20, 1.0, 0, None),
    "flute": (["flute"], "held", 0.10, 1.0, 0.15, None),
    "clarinet": (["clarinet"], "held", 0.09, 1.0, 0.15, None),
    "oboe": (["oboe"], "held", 0.09, 1.0, 0.15, None),
    "harmonica": (["harmonica"], "held", 0.08, 1.0, 0.12, None),
    "horn": (["horn"], "held", 0.18, 1.0, 0.25, None),
    "strings": (["viola", "cello"], "held", 0.60, 1.0, 0.6, None),
    "shaker": (["shaker"], "hit", 0, 1.0, 0, r"HighFaster"),
    "woodblock": (["woodblock"], "hit", 0, 1.0, 0, r"wood_click_(mp|f_)"),
    "bassdrum": (["bassdrum"], "hit", 0, 1.0, 0, r"_v5_"),
}


# Tone corrections the audit asked for, as (high-pass Hz, low-pass Hz), 12 dB an octave: the harmonica had as much
# sound above 4 kHz as below ("harsh"), the shaker rumbled under 40 Hz and was centred on 9 to 11 kHz (hiss).
EQ = {"harmonica": (0, 1900), "shaker": (300, 4000)}
FADE_IN = {}                       # seconds, where a recording starts on a click (attack under 1 ms)


def read_wav(path):
    with wave.open(str(path)) as w:
        ch, width, sr, n = w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getnframes()
        raw = w.readframes(n)
    if width == 3:
        b = np.frombuffer(raw, np.uint8).reshape(-1, 3).astype(np.int32)
        x = ((b[:, 0] | (b[:, 1] << 8) | (b[:, 2] << 16)) ^ 0x800000) - 0x800000
        x = x / 8388608.0
    else:
        x = np.frombuffer(raw, {2: np.int16, 4: np.int32}[width]) / float(1 << (8 * width - 1))
    return x.reshape(-1, ch).mean(axis=1), sr


def named(stem):
    m = re.search(r"(?<![A-Za-z#])([A-G])(#?)(-?\d)(?![0-9])", stem)
    note = None if not m else 12 * (int(m.group(3)) + 1) + PC[m.group(1)] + (1 if m.group(2) else 0)
    lay = re.search(r"_v(?:l)?(\d)", stem)
    layer = int(lay.group(1)) if lay else next((v for k, v in LAYER.items() if re.search(rf"_{k}(\d|_|$)", stem)), 2)
    return note, layer


def octave_vote(x, sr, guess):
    """How many octaves the sound is from the note in the file name: several libraries count octaves their own way.
    The vote is the highest octave of the named note whose period the wave really repeats at."""
    seg = x[int(0.03 * sr): int(0.9 * sr)]
    seg = seg - seg.mean()
    n = 1 << int(np.ceil(np.log2(2 * len(seg) + 2)))
    ac = np.fft.irfft(np.abs(np.fft.rfft(seg, n)) ** 2)
    best = []
    for octv in range(-2, 5):
        f = 440 * 2 ** ((guess + 12 * octv - 69) / 12)
        if 25 < f < 4200:
            lo, hi = int(sr / (f * 1.04)), int(np.ceil(sr / (f / 1.04)))
            best.append((float(ac[lo:hi + 1].max()), octv))
    top = max(v for v, _ in best)
    return max(o for v, o in best if v >= top - 0.15 * abs(top))


def cents_off(x, sr, m):
    """How far the recording is from concert pitch, read on its strongest low harmonic."""
    seg = x[int(0.05 * sr): int(1.5 * sr)]
    n = 1 << 18
    S = np.abs(np.fft.rfft(seg * np.hanning(len(seg)), n))
    f0, found = 440 * 2 ** ((m - 69) / 12), []
    for h in (1, 2, 3):
        lo, hi = int(h * f0 * 2 ** (-50 / 1200) * n / sr), int(h * f0 * 2 ** (50 / 1200) * n / sr) + 1
        k = lo + int(np.argmax(S[lo:hi + 1]))
        y0, y1, y2 = np.log(S[k - 1:k + 2] + 1e-30)
        k = k + float(np.clip(0.5 * (y0 - y2) / (y0 - 2 * y1 + y2 - 1e-20), -1, 1))
        found.append((S[int(round(k))], 1200 * np.log2(k * sr / n / (h * f0))))
    return float(np.clip(max(found)[1], -35, 35))


def build():
    CACHE.mkdir(parents=True, exist_ok=True)
    for name, (folders, kind, *_rest, keep) in KIT.items():
        zones = []
        for folder in folders:
            for path in sorted((RAW / folder).glob("*.wav")):
                if keep and not re.search(keep, path.stem):
                    continue
                x, sr = read_wav(path)
                pk = np.abs(x).max()
                start = max(0, int(np.argmax(np.abs(x) > pk * (0.03 if kind == "held" else 0.01))) - int(0.004 * sr))
                x = x[start: start + 14 * sr]
                note, layer = named(path.stem)
                pitch = 60.0 if kind == "hit" else octave_vote(x, sr, note)
                loud = np.sqrt(np.sort(x ** 2)[-int(0.3 * sr):].mean()) if kind != "hit" else pk       # the loudest 0.3 s
                zones.append(dict(file=path.name, folder=folder, pitch=float(pitch), named=note, layer=layer, sr=sr,
                                  data=np.round(x / np.abs(x).max() * 32767).astype(np.int16), loud=float(loud / np.abs(x).max())))
        if kind != "hit":
            for folder in folders:                       # one octave rule per library folder, then each file's own tuning
                mine = [z for z in zones if z["folder"] == folder]
                octv = int(np.median([z["pitch"] for z in mine]))
                for z in mine:
                    m = z["named"] + 12 * octv
                    z["pitch"] = m + cents_off(z["data"] / 32767.0, z["sr"], m) / 100
        pickle.dump(zones, open(CACHE / f"{name}.pkl", "wb"))
        ps = sorted({round(z["pitch"]) for z in zones})
        off = [z["pitch"] - round(z["pitch"]) for z in zones]
        moved = sum(1 for z in zones if z["named"] is not None and abs(z["pitch"] - z["named"]) > 6)
        if kind == "hit":
            print(f"{name:10s} {len(zones):3d} files: " + ", ".join(f"{z['file']} {len(z['data']) / z['sr']:.2f}s" for z in zones))
            continue
        print(f"{name:10s} {len(zones):3d} files, notes {ps[0]}..{ps[-1]}, {moved} octave names corrected, "
              f"tuning {np.min(off) * 100:+.0f}..{np.max(off) * 100:+.0f} cents, {np.mean([len(z['data']) / z['sr'] for z in zones]):.1f} s")


# ------------------------------------------------------------------ playing

_kits, _shifted, _turn = {}, {}, {}


def kit(name):
    if name not in _kits:
        if not (CACHE / f"{name}.pkl").exists():
            raise SystemExit("no recorded instruments yet: run  uv run python music/fetch_samples.py  then  uv run python music/sampler.py")
        _kits[name] = pickle.load(open(CACHE / f"{name}.pkl", "rb"))
    return _kits[name]


def hermite(x, pos):
    i = np.floor(pos).astype(np.int64)
    u = pos - i
    xm, x0, x1, x2 = x[i - 1], x[i], x[i + 1], x[i + 2]
    c1, c2, c3 = 0.5 * (x1 - xm), xm - 2.5 * x0 + 2 * x1 - 0.5 * x2, 0.5 * (x2 - xm) + 1.5 * (x0 - x1)
    return ((c3 * u + c2) * u + c1) * u + x0


def shifted(name, k, semis):
    """Zone k of an instrument, re-pitched by semis and at 48 kHz, level-matched (kept: the same notes come back)."""
    key = (name, k, round(semis, 3))
    if key not in _shifted:
        z = kit(name)[k]
        x = z["data"].astype(np.float64) / 32767 / z["loud"]
        step = 2 ** (semis / 12) * z["sr"] / SR
        n = len(x)
        m = 1 << int(np.ceil(np.log2(n + 8)))
        X = np.fft.rfft(x, m)
        X[np.fft.rfftfreq(m, 1 / z["sr"]) > 0.47 * min(z["sr"], SR / max(step * SR / z["sr"], 1e-9) * 1.0) ] = 0     # nothing folds back
        if name in EQ:
            fr, (lo, hi) = np.fft.rfftfreq(m, 1 / z["sr"]), EQ[name]
            X = X / np.sqrt(1 + (fr / hi) ** 4) / np.sqrt(1 + (lo / np.maximum(fr, 1e-3)) ** 4)
        up = np.fft.irfft(np.concatenate([X, np.zeros(m // 2)]), 2 * m)[: 2 * n] * 2                                     # twice the rate
        pos = np.arange(1, int((n - 3) / step)) * step * 2
        _shifted[key] = hermite(np.concatenate([[0.0], up, [0.0, 0.0, 0.0]]), pos + 1).astype(np.float32)
    return _shifted[key]


def pick(name, m, vel):
    zs = kit(name)
    near = min(abs(z["pitch"] - m) for z in zs)
    if os.environ.get("MUSIC_RANGE_LOG"):              # the audit reads how far each note was re-pitched
        with open(os.environ["MUSIC_RANGE_LOG"], "a") as f:
            f.write(f"{name} {m:.0f} {near:.2f}\n")
    cand = [(k, z) for k, z in enumerate(zs) if abs(z["pitch"] - m) <= near + 0.6]
    layers = sorted({z["layer"] for _, z in cand})
    want = layers[min(len(layers) - 1, int(np.clip(vel, 0, 0.999) * len(layers)))]
    cand = [(k, z) for k, z in cand if z["layer"] == want]
    turn = _turn[name] = _turn.get(name, 0) + 1
    k, z = cand[turn % len(cand)]
    return k, m - z["pitch"]


def sustain(x, need, xf):
    """x made at least `need` long by repeating its steady middle with crossfades."""
    env = np.sqrt(np.convolve(x ** 2, np.ones(2400) / 2400, "same"))
    steady = np.median(env[len(x) // 5: len(x) // 2])
    live = np.nonzero(env > 0.5 * steady)[0]
    end = int(live[-1]) if len(live) else len(x)
    if need <= end:
        return x[:need + 1]
    a, b = int(0.35 * end), int(0.92 * end)
    xf = min(xf, (b - a) // 3)
    w = np.sin(np.linspace(0, np.pi / 2, xf))
    out = x[:b].copy()
    while len(out) < need + 1:
        piece = x[a:b].copy()
        out[-xf:] = out[-xf:] * w[::-1] + piece[:xf] * w
        out = np.concatenate([out, piece[xf:]])
    return out


def voice(name, gain=1.0, attack=0.0, octave=0):
    folders, kind, rel, kgain, xf, _ = KIT[name]

    def play(f, dur, vel, t0=0.0):
        m = 69 + 12 * np.log2(f / 440) + 12 * octave
        if kind == "hit":
            zs = kit(name)
            turn = _turn[name] = _turn.get(name, 0) + 1
            x = shifted(name, turn % len(zs), 0.0)
            y = x[: int(1.0 * SR)].astype(float)
            y[len(y) // 2:] *= np.linspace(1, 0, len(y) - len(y) // 2) ** 2
        else:
            k, semis = pick(name, m, vel)
            x = shifted(name, k, semis)
            need = int((dur + 7 * rel) * SR)
            y = (sustain(x, need, int(xf * SR)) if kind == "held" else x)[:need].astype(float)
            t = np.arange(len(y)) / SR
            y = y * np.where(t > dur, np.exp(-(t - dur) / rel), 1.0)
            if attack:
                y = y * np.clip(t / attack, 0, 1) ** 2
        k = min(len(y), int(FADE_IN.get(name, 0.001) * SR))
        y[:k] *= np.linspace(0, 1, k)
        k = min(len(y), 480)
        y[-k:] *= np.linspace(1, 0, k)
        return gain * kgain * 0.12 * (0.25 + 0.75 * vel) * vel ** 0.3 * y

    play.__name__ = name
    return play


if __name__ == "__main__":
    build()
