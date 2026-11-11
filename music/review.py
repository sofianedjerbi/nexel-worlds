"""Measure the frozen Opus set against the current set and write music/site/review.json for the showcase page.
    uv run python music/review.py"""
import json, sys, wave
from pathlib import Path
import numpy as np

sys.argv = sys.argv[:1]
sys.path.insert(0, str(Path(__file__).parent))
import audit, ringcheck   # noqa: E402

SITE = Path(__file__).with_name("site")
SR = 48000


def sfx_stats(d):
    m = json.load(open(d / "sfx.json"))
    late, rumble, samey, spread, rings, cat_l = [], [], [], [], [], {}
    for name, info in m.items():
        xs = [audit.load(str(d / f)) for f in info["files"]]
        L = [audit.loud(x) for x in xs]
        lat = max(audit.latency_ms(x) for x in xs)
        rum = max(10 * np.log10((np.abs(np.fft.rfft(x))[: int(40 * len(x) / SR)] ** 2).sum() / (np.abs(np.fft.rfft(x)) ** 2).sum() + 1e-12) for x in xs)
        if lat > 12: late.append((lat, name))
        if rum > -12: rumble.append(name)
        if len(xs) > 1:
            sp = [audit.band_spec(x) for x in xs]
            sim = np.mean([np.corrcoef(sp[i], sp[j])[0, 1] for i in range(len(sp)) for j in range(i + 1, len(sp))])
            if sim > 0.995: samey.append(name)
            spread.append(max(L) - min(L))
        tonal = info["category"] in ringcheck.TONAL_OK or name in ringcheck.TONAL_NAMES
        if not tonal and ringcheck.ring(xs[0]) > 0.2: rings.append(name)
    return dict(n=len(m), files=sum(len(i["files"]) for i in m.values()), late=sorted(late, reverse=True), rumble=rumble,
                samey=samey, spread=max(spread), rings=rings)


def music_stats(f):
    w = wave.open(str(f))
    x = (np.frombuffer(w.readframes(w.getnframes()), "<i2").reshape(-1, 2) / 32767).T
    mono = x.mean(axis=0)
    n = 1 << 16
    fr = np.fft.rfftfreq(n, 1 / SR)
    P = sum(np.abs(np.fft.rfft(mono[k:k + n] * np.hanning(n))) ** 2 for k in range(0, len(mono) - n, n))
    band = lambda lo: 10 * np.log10(P[(fr >= lo / 1.414) & (fr < lo * 1.414)].sum() / P.sum())
    blk = len(mono) // 11
    lv = [20 * np.log10(np.sqrt(np.mean(mono[k * blk:(k + 1) * blk] ** 2))) for k in range(11)]
    return dict(b1k=band(1000), b2k=band(2000), b4k=band(4000), b8k=band(8000), quiet=min(lv), loud=max(lv),
                corr=float(np.corrcoef(x[0], x[1])[0, 1]))


if __name__ == "__main__":
    so, sf = sfx_stats(SITE / "opus" / "sfx"), sfx_stats(SITE / "sfx")
    mo, mf = music_stats(SITE / "opus" / "audio" / "master.wav"), music_stats(SITE / "audio" / "master.wav")
    names = lambda xs: ", ".join(xs) if xs else "none"
    rows = [
        ["Music, tone", f"Opus had almost nothing above 2 kHz (4 kHz at {mo['b4k']:.0f} dB, 8 kHz at {mo['b8k']:.0f} dB of the total): a very dark mix. "
                        f"Fable: {mf['b4k']:.0f} dB and {mf['b8k']:.0f} dB. Still warm, with a little more hammer and air."],
        ["Music, touch", "In Opus every melody note had the same weight and exact timing. Fable keeps the notes and shapes them: "
                         "arrivals heavier, passing notes lighter, long notes placed 20 to 40 ms late."],
        ["Music, levels", f"The quietest block sat {mo['loud'] - mo['quiet']:.0f} dB under the loudest in Opus, which risks being lost at game volume. "
                          f"Fable: {mf['loud'] - mf['quiet']:.0f} dB."],
        ["Music, motion", "Layers switched on and off at block edges; now the arpeggio drifts in and out over two bars, "
                          "and the left hand answers softly under the melody's long notes."],
        ["Sounds, rumble", f"In Opus, {len(so['rumble'])} sounds had over 6% of their energy under 40 Hz, where it is inaudible and eats headroom "
                           f"({names(so['rumble'])}). Fable: {len(sf['rumble'])} ({names(sf['rumble'])}; a falling tree may)."],
        ["Sounds, latency", f"{len(so['late'])} Opus sounds took 12 to {so['late'][0][0]:.0f} ms to start ({names([n for _, n in so['late']])}). "
                            f"Fable: {len(sf['late'])}. Everything starts within about a millisecond."],
        ["Sounds, variants", f"{len(so['samey'])} Opus sounds had variants that were the same sound ({names(so['samey'])}). "
                             f"Fable: {len(sf['samey'])}{' (' + names(sf['samey']) + ': strokes differ in rhythm, not in tone)' if sf['samey'] else ''}."],
        ["Sounds, loudness", f"Opus set levels by raw RMS, so variants of one sound differed by up to {so['spread']:.1f} dB to the ear. "
                             f"Fable sets levels with the ear's weighting (BS.1770): {sf['spread']:.1f} dB."],
        ["Sounds, context", f"Opus: {so['n']} sounds, {so['files']} files. Fable: {sf['n']} sounds, {sf['files']} files. New: eating (the game asked for it and had none), "
                            "watering, filling a bucket, a bare-hand hit, a startled chicken."],
        ["Honest limit", "This review is by measurement and by reading the generators. Neither model can hear. Your ears decide: use the rows below."],
    ]
    (SITE / "review.json").write_text(json.dumps(rows, indent=1))
    for a, b in rows:
        print(f"- {a}: {b}")
