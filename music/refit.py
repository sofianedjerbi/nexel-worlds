"""Corrected versions of the five pieces in the game, beside the originals, for the user to compare by ear.

"also fix the existing songs and add them into showcase for validation". The pieces were approved by ear and are never
rendered again: each correction is made on the approved stereo file (site/audio/final_<name>.wav) and written to
site/audio/fixed_<name>.wav. The game keeps playing the originals until the user says otherwise.

What the meters found (mixcheck.py on the parts, this file on the finished files), and what is done about each:
  - a bass that lives under 75 Hz with little above it (the two night pieces): a laptop or a phone plays
    none of it. Its octaves (2x, 4x) are made from the low band and added quietly at 80-300 Hz, where small
    speakers still work; the low band itself is not touched.
  - a middle that is as wide as it is loud (Side street night): on one speaker the pad drops 3 dB. The difference
    between left and right is turned down between 150 Hz and 5 kHz until one speaker loses 1.5 dB at most.
  - left and right not equally loud (Side street day, 0.4 dB): balanced.
Then the game's level again (-20 LUFS, true peak under -1 dB).

    uv run --no-project --python 3.11 --with numpy python music/refit.py
"""
import json
import wave

import numpy as np

import master

OUT = master.OUT
NAMES = ["side_street_day", "far_shore_day", "side_street_night", "far_shore_night_c", "old_mossback"]
TITLES = {"side_street_day": "Side street, day", "far_shore_day": "Far shore, day", "side_street_night": "Side street, night",
          "far_shore_night_c": "Far shore, night", "old_mossback": "Old Mossback"}
OCTAVES_DB = -3.0                # the added octaves against the low band they are made from
FOLD_DB = 1.5                    # the most the middle may lose on one speaker


def band(x, lo, hi, order=8):
    return master.spectrum_gain(x, lambda f: 1 / np.sqrt((1 + (lo / np.maximum(f, 1e-3)) ** (2 * order)) * (1 + (f / hi) ** (2 * order))))


def rms(x):
    return float(np.sqrt((x ** 2).mean()) + 1e-12)


def measure(x):
    mid, side = x.mean(axis=0, keepdims=True), (x[:1] - x[1:]) / 2
    two = lambda y: np.concatenate([y, y])
    small = band(x, 120, 30000)                                   # a laptop: little under 120 Hz
    m, s = band(mid, 150, 5000), band(side, 150, 5000)
    return dict(lufs=round(master.lufs(x), 1), true_peak=round(master.true_peak(x), 1),
                laptop=round(master.lufs(small) - master.lufs(x), 1), one_speaker=round(master.lufs(two(mid)) - master.lufs(x), 1),
                sub_over_bass=round(20 * np.log10(rms(band(mid, 20, 75)) / rms(band(mid, 90, 300))), 1), bass_90_300=round(20 * np.log10(rms(band(mid, 90, 300))), 1),
                fold=round(10 * np.log10(1 + (rms(s) / rms(m)) ** 2), 1),      # what the middle loses when left and right are summed
                left_right=round(20 * np.log10(rms(x[0]) / rms(x[1])), 2))


def refit(x):
    did = []
    before = measure(x)
    if abs(before["left_right"]) > 0.25:
        g = 10 ** (before["left_right"] / 40)
        x = np.stack([x[0] / g, x[1] * g])
        did.append(f"left and right balanced ({abs(before['left_right']):.1f} dB apart)")
    mid, side = x.mean(axis=0, keepdims=True), (x[:1] - x[1:]) / 2
    if before["sub_over_bass"] > 0:                                # (the days and the boss have basses with their own overtones)
        low = band(mid, 20, 75)
        octs = band(np.abs(low), 80, 300)                          # a rectified wave is its octaves: 2x, 4x
        mid = mid + octs * rms(low) / rms(octs) * 10 ** (OCTAVES_DB / 20)
        did.append("the bass's octaves added at 80-300 Hz, for small speakers")
    if before["fold"] > FOLD_DB:
        keep = np.sqrt((10 ** (FOLD_DB / 10) - 1) / (10 ** (before["fold"] / 10) - 1))
        side = side - band(side, 150, 5000) * (1 - keep)
        did.append(f"the middle narrowed by {-20 * np.log10(keep):.1f} dB, for one speaker")
    x = np.concatenate([mid + side, mid - side])
    if did:
        x = x * 10 ** ((-20.0 - master.lufs(x)) / 20)
        x, _ = master.limit(x, -1.0)
    return x, did, before, measure(x)


if __name__ == "__main__":
    rows = []
    for name in NAMES:
        y, did, before, after = refit(master.read(OUT / f"final_{name}.wav").astype(np.float64))
        with wave.open(str(OUT / f"fixed_{name}.wav"), "wb") as w:
            w.setnchannels(2), w.setsampwidth(2), w.setframerate(master.SR)
            w.writeframes(np.round(np.clip(y, -1, 1).T * 32767).astype(np.int16).tobytes())
        before, after = ({k: float(v) for k, v in d.items()} for d in (before, after))
        rows.append(dict(id=name, title=TITLES[name], seconds=round(y.shape[1] / master.SR, 1), did=did, before=before, after=after))
        print(f"{name}\n   did    {did or 'nothing'}\n   before {before}\n   after  {after}", flush=True)
    (OUT / "fixed.json").write_text(json.dumps(rows, indent=1))
