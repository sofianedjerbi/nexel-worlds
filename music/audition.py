"""Short clips of the theme (8 bars with the band) with each candidate for the main instrument, for the page.
uv run python music/audition.py  ->  music/site/audio/try_<name>.wav"""
import os

import numpy as np

import compose as C

CANDIDATES = {"guitar": C.nylon, "rhodes": C.rhodes, "marimba": C.marimba, "piano": C.lofi_piano}


def clip(inst, bars=8, first_bar=24):
    """Bars 24..31: the melody with bass, electric piano and shaker."""
    t0, t1 = C.t_of(first_bar * 8), C.t_of((first_bar + bars) * 8)
    n = int((t1 - t0 + 3) * C.SR)
    dry, rev = np.zeros((2, n)), np.zeros((2, n))
    for t, dur, m, vel, i, pan, stem, rs, es in C.events:
        if not t0 <= t < t1 or stem == "pad":
            continue
        y = np.atleast_2d((inst if i is C.MAIN else i)(C.hz(m), dur, vel, t))
        y = np.vstack([y, y])[:2] * C.GAINS[stem]
        k = int((t - t0) * C.SR)
        y = y[:, : n - k]
        a = (pan + 1) * np.pi / 4
        y = y * np.array([[np.cos(a)], [np.sin(a)]]) * np.sqrt(2)
        dry[:, k:k + y.shape[1]] += y
        rev[:, k:k + y.shape[1]] += rs * y
    ir = [np.fft.irfft(r, C.LOOP_N)[: 2 * C.SR] for r in C.make_ir(np.random.default_rng(3))]
    wet = np.stack([np.convolve(rev[c], ir[c])[:n] for c in range(2)])
    out = dry + 0.22 * wet
    return out * 10 ** (-19 / 20) / np.sqrt(np.mean(out ** 2))


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    for name, inst in CANDIDATES.items():
        x = clip(inst)
        C.write_wav(os.path.join(here, "site", "audio", f"try_{name}.wav"), np.clip(x, -1, 1))
        print(name, "peak", round(float(np.abs(x).max()), 2))
