"""Objective audit of a rendered SFX folder: latency, perceived loudness, rumble, clipping, variant distinctness.
    uv run python music/audit.py music/site/sfx"""
import sys, json, wave
import numpy as np

D = sys.argv[1] if len(sys.argv) > 1 else "music/site/sfx"
SR = 48000


def load(f):
    w = wave.open(f)
    return np.frombuffer(w.readframes(w.getnframes()), "<i2") / 32767


def kweight(x):
    """ITU-R BS.1770 K-weighting, applied in the frequency domain (shelf +4 dB above ~1.5 kHz, high-pass ~38 Hz)."""
    n = len(x)
    f = np.fft.rfftfreq(n, 1 / SR)
    shelf = 1 + (10 ** (4 / 20) - 1) / (1 + (1681 / np.maximum(f, 1)) ** 2)
    hp = 1 / np.sqrt(1 + (38 / np.maximum(f, 1e-3)) ** 4)
    return np.fft.irfft(np.fft.rfft(x) * shelf * hp, n)


def loud(x):
    """Loudest 100 ms, K-weighted, in dB."""
    y = kweight(x)
    w = min(len(y), int(0.1 * SR))
    c = np.cumsum(np.concatenate([[0], y ** 2]))
    return 10 * np.log10(np.max(c[w:] - c[:-w]) / w + 1e-12)


def latency_ms(x):
    e = np.abs(x)
    return 1000 * np.argmax(e > 0.1 * e.max()) / SR


def band_spec(x, bands=24):
    S = np.abs(np.fft.rfft(x, 1 << 16)) ** 2
    f = np.fft.rfftfreq(1 << 16, 1 / SR)
    edges = np.geomspace(60, 12000, bands + 1)
    v = np.array([S[(f >= a) & (f < b)].sum() for a, b in zip(edges, edges[1:])])
    return np.log10(v + 1e-12)


if __name__ == "__main__":
    m = json.load(open(f"{D}/sfx.json"))
    cats = {}
    rows = []
    for name, info in m.items():
        xs = [load(f"{D}/{f}") for f in info["files"]]
        L = [loud(x) for x in xs]
        lat = max(latency_ms(x) for x in xs)
        rumble = max(10 * np.log10((np.abs(np.fft.rfft(x))[: int(40 * len(x) / SR)] ** 2).sum() / (np.abs(np.fft.rfft(x)) ** 2).sum() + 1e-12) for x in xs)
        clip = sum(int((np.abs(x) > 0.985).sum()) for x in xs)
        if len(xs) > 1:
            sp = [band_spec(x) for x in xs]
            sim = np.mean([np.corrcoef(sp[i], sp[j])[0, 1] for i in range(len(sp)) for j in range(i + 1, len(sp))])
            ldiff = max(L) - min(L)
        else:
            sim, ldiff = float("nan"), 0.0
        rows.append((info["category"], name, np.mean(L), ldiff, lat, rumble, clip, sim, max(len(x) for x in xs) / SR))
        cats.setdefault(info["category"], []).append(np.mean(L))
    print(f"{'category':10s} {'sound':16s} {'LKdB':>6s} {'vs cat':>6s} {'varΔ':>5s} {'lat ms':>6s} {'<40Hz':>6s} {'clip':>4s} {'varsim':>6s} {'len':>5s}  flags")
    for cat, name, L, ld, lat, rum, clip, sim, ln in rows:
        med = np.median(cats[cat])
        flags = []
        if lat > 12: flags.append("LATE")
        if ld > 2.5: flags.append("UNEVEN")
        if rum > -12: flags.append("RUMBLE")
        if clip: flags.append("CLIP")
        if sim == sim and sim > 0.995: flags.append("SAMEY")
        print(f"{cat:10s} {name:16s} {L:6.1f} {L - med:+6.1f} {ld:5.1f} {lat:6.1f} {rum:6.1f} {clip:4d} {sim:6.3f} {ln:5.2f}  {' '.join(flags)}")
