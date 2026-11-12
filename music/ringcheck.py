"""Xylophone detector: how much of a sound's energy, after the first 30 ms, sits in a few sustained narrow peaks.
Real footsteps, impacts on the ground, gravel, soil and leaves are noise-like (low score). Bells, chimes and voices are tonal by design.
    uv run python music/ringcheck.py [music/site/sfx]"""
import sys, json, wave
import numpy as np

D = sys.argv[1] if len(sys.argv) > 1 else "music/site/sfx"
TONAL_OK = {"Progress", "People", "Interface"}
TONAL_NAMES = {"wade", "swim", "fill", "pour", "squawk", "hurt",  # bubbles are real tones (Minnaert)
               "collect", "orb", "craft", "chirp", "cluck", "moo", "gloom", "love", "grow", "creak", "gate", "chest", "die", "lay", "hatch", "milk", "boss_wake", "boss_groan"}


def ring(x, sr=48000):
    e = np.abs(x)
    start = np.argmax(e) + int(0.03 * sr)
    seg = x[start:start + int(0.25 * sr)]
    if len(seg) < 2048 or np.sqrt(np.mean(seg ** 2)) < 0.05 * np.abs(x).max() * 0.1:
        return 0.0
    frames = np.lib.stride_tricks.sliding_window_view(seg, 2048)[::512] * np.hanning(2048)
    S = np.mean(np.abs(np.fft.rfft(frames, axis=1)) ** 2, axis=0)
    f = np.fft.rfftfreq(2048, 1 / sr)
    band = (f > 150) & (f < 9000)
    S = S[band]
    # a tone stands far above its neighbourhood; noise does not. local median over +-12 bins (~280 Hz)
    pad = np.pad(S, 12, mode="edge")
    med = np.median(np.lib.stride_tricks.sliding_window_view(pad, 25), axis=1)
    peaky = S > 8 * med
    return float(S[peaky].sum() / S.sum())


if __name__ == "__main__":
    m = json.load(open(f"{D}/sfx.json"))
    rows = []
    for name, info in m.items():
        w = wave.open(f"{D}/{info['files'][0]}")
        x = (np.frombuffer(w.readframes(w.getnframes()), "<i2") / 32767).reshape(-1, w.getnchannels()).mean(axis=1)
        tonal_by_design = info["category"] in TONAL_OK or name in TONAL_NAMES
        rows.append((ring(x), name, info["category"], tonal_by_design))
    print("ring = share of energy (after 30 ms) in narrow peaks 8x above their neighbourhood: noise ~0, a xylophone > 0.3")
    for r, name, cat, ok in sorted(rows, reverse=True):
        flag = "" if ok else ("  <-- RINGS" if r > 0.2 else "")
        print(f"  {r:5.2f}  {name:16s} {cat:10s}{' (tonal by design)' if ok else ''}{flag}")
