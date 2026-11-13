"""The final mix of the kept pieces (the user: "mix all of these new songs nicely with effects if needed").

It works on the finished stereo files the user approved, so the pieces cannot change: no note is re-rendered.
What it does, in order, and why:
  1. removes what is under 30 Hz (inaudible, eats headroom)
  2. centres the lows: under 120 Hz the two channels are made equal (bass and kick in the middle, also on one speaker)
  3. glue: a gentle bus compressor (2:1, slow attack so the hits pass, about 1.5 dB on average); not on night pieces
  4. the same loudness for the same role, measured in LUFS (how loud it is heard, not its peaks):
     day -16, boss -14.5, night -18 (a night piece is meant to sit a little lower)
  5. a limiter that keeps the true peak under -1 dBFS (peaks measured four times oversampled)
No reverb is added: every Surge sound brings its own, and the user's standing complaint is too much of it.

    uv run python music/master.py        # writes site/audio/final_*.wav and final.json, prints before and after
"""
from pathlib import Path
import json
import wave

import numpy as np

SR = 48000
OUT = Path(__file__).with_name("site") / "audio"
SET = [  # file in, name out, title, role, where it plays
    ("piece_cute1", "side_street_day", "Side street, day", "day", "random moments in the day"),
    ("piece_shore", "far_shore_day", "Far shore, day", "day", "random moments in the day"),
    ("piece_mc1", "side_street_night", "Side street, night", "night", "random moments at night"),
    ("piece_shore_night", "far_shore_night", "Far shore, night", "night", "random moments at night"),
    ("piece_mossback2", "old_mossback", "Old Mossback", "boss", "the boss fight, looped"),
]
TARGET = {"day": -16.0, "night": -18.0, "boss": -14.5}


def read(path):
    with wave.open(str(path)) as w:
        return np.frombuffer(w.readframes(w.getnframes()), np.int16).reshape(-1, 2).T / 32768.0


def spectrum_gain(x, gain):
    """x filtered by gain(frequencies); the file is a loop, so the circular FFT has no edge."""
    n = x.shape[-1]
    return np.fft.irfft(np.fft.rfft(x, axis=-1) * gain(np.fft.rfftfreq(n, 1 / SR)), n, axis=-1)


def lufs(x):
    """Integrated loudness (ITU-R BS.1770): K-weighting, 400 ms blocks, the two gates."""
    def k(f):
        z = np.exp(-2j * np.pi * f / SR)
        shelf = (1.53512485958697 - 2.69169618940638 * z + 1.19839281085285 * z ** 2) / (1 - 1.69065929318241 * z + 0.73248077421585 * z ** 2)
        high = (1 - 2 * z + z ** 2) / (1 - 1.99004745483398 * z + 0.99007225036621 * z ** 2)
        return shelf * high
    y = spectrum_gain(x, k)
    hop, size = int(0.1 * SR), int(0.4 * SR)
    p = np.array([(y[:, i:i + size] ** 2).mean(axis=1).sum() for i in range(0, y.shape[1] - size, hop)])
    loud = -0.691 + 10 * np.log10(p + 1e-12)
    p = p[loud > -70]
    p = p[-0.691 + 10 * np.log10(p) > -0.691 + 10 * np.log10(p.mean()) - 10]
    return float(-0.691 + 10 * np.log10(p.mean()))


def true_peak(x):
    n = x.shape[1]
    X = np.fft.rfft(x, axis=1)
    up = np.fft.irfft(np.concatenate([X, np.zeros((2, 3 * (n // 2)))], axis=1), 4 * n, axis=1) * 4
    return float(20 * np.log10(np.abs(up).max() + 1e-12))


def glue(x, ratio=2.0, attack=0.03, release=0.25, aim=1.5):
    """A bus compressor: the threshold is found so that it takes `aim` dB off on average. Returns audio and that average."""
    block = 64
    level = np.sqrt((x ** 2).mean(axis=0))
    env = np.sqrt(np.convolve(level ** 2, np.ones(480) / 480, "same"))[::block] + 1e-9
    db = 20 * np.log10(env)
    a, r = np.exp(-block / SR / attack), np.exp(-block / SR / release)

    def reduction(th):
        want, g, out = np.maximum(0, db - th) * (1 - 1 / ratio), 0.0, np.empty(len(db))
        for i, w in enumerate(want):
            g = a * g + (1 - a) * w if w > g else r * g + (1 - r) * w
            out[i] = g
        return out
    lo, hi = db.min(), db.max()
    for _ in range(18):                     # the threshold that gives the wanted average
        th = (lo + hi) / 2
        lo, hi = (th, hi) if reduction(th).mean() > aim else (lo, th)
    red = reduction(th)
    gain = 10 ** (-np.interp(np.arange(x.shape[1]), np.arange(len(red)) * block, red) / 20)
    return x * gain, float(red.mean()), float(red.max())


def limit(x, ceil_db=-1.0):
    ceil = 10 ** (ceil_db / 20) * 0.97          # a margin for what lies between the samples
    pk = np.abs(x).max(axis=0)
    blocks = np.array([pk[max(0, i - 240): i + 288].max() for i in range(0, x.shape[1], 48)])
    gain = np.interp(np.arange(x.shape[1]), np.arange(0, x.shape[1], 48), np.minimum(1.0, ceil / np.maximum(blocks, 1e-9)))
    return x * np.convolve(np.pad(gain, 240, mode="edge"), np.ones(481) / 481, "valid"), float(100 * (gain < 0.999).mean())


def measure(x):
    S, fr = np.abs(np.fft.rfft(x.mean(axis=0))) ** 2, np.fft.rfftfreq(x.shape[1], 1 / SR)
    band = lambda lo, hi: round(float(10 * np.log10(S[(fr >= lo) & (fr < hi)].sum() / S.sum() + 1e-12)), 1)
    low = spectrum_gain(x, lambda f: (f < 120).astype(float))
    return dict(lufs=round(lufs(x), 1), true_peak=round(true_peak(x), 1), under_60=band(0, 60), b60_250=band(60, 250), b250_1k=band(250, 1000), b1_4k=band(1000, 4000),
                over_4k=band(4000, 24000), lows_apart=round(float(20 * np.log10(np.sqrt(((low[0] - low[1]) ** 2).mean()) / (np.sqrt(((low[0] + low[1]) ** 2).mean()) + 1e-12) + 1e-9)), 0))


def master(x, role):
    x = spectrum_gain(x, lambda f: 1 / np.sqrt(1 + (30 / np.maximum(f, 1e-3)) ** 4))
    mid, side = (x[0] + x[1]) / 2, (x[0] - x[1]) / 2
    side = spectrum_gain(side, lambda f: 1 / np.sqrt(1 + (120 / np.maximum(f, 1e-3)) ** 8))
    x = np.stack([mid + side, mid - side])
    took = (0.0, 0.0)
    if role != "night":
        x, *took = glue(x)
    ceil = -1.0
    for _ in range(5):                           # loudness, then the limiter; lower its ceiling while the true peak is over -1 dBFS
        y = x * 10 ** ((TARGET[role] - lufs(x)) / 20)
        y, worked = limit(y, ceil)
        y = y * 10 ** ((TARGET[role] - lufs(y)) / 20) if worked < 0.05 else y
        over = true_peak(y) + 1.0
        if over <= 0:
            break
        ceil -= over + 0.1
    x = y
    return x, dict(glue_avg_db=round(took[0], 1), glue_max_db=round(took[1], 1), limiter_percent=round(worked, 1))


if __name__ == "__main__":
    rows = []
    for src, name, title, role, where in SET:
        x = read(OUT / f"{src}.wav")
        before = measure(x)
        y, did = master(x, role)
        after = measure(y)
        with wave.open(str(OUT / f"final_{name}.wav"), "wb") as w:
            w.setnchannels(2), w.setsampwidth(2), w.setframerate(SR)
            w.writeframes(np.round(np.clip(y, -1, 1).T * 32767).astype(np.int16).tobytes())
        rows.append(dict(id=name, title=title, role=role, where=where, seconds=round(x.shape[1] / SR, 1), before=before, after=after, did=did))
        print(f"{title:20s} {role:5s} {x.shape[1] / SR:5.1f} s\n   before {before}\n   after  {after}\n   {did}", flush=True)
    (OUT / "final.json").write_text(json.dumps(rows, indent=1))
