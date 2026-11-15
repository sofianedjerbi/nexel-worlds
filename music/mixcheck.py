"""A mix engineer's checks, stem by stem, against the two day pieces the user kept (Side street, Far shore).

"please keep a sound engineer approach, because everyone of them sounds bad" (the first five menu pieces). I cannot
hear; what can be done without ears is what an engineer does with meters: solo every part, see which register it
really sounds in, how much room it takes, and hold the mix against a reference that is known to be liked.

What the first five got wrong, measured here:
  - several sounds speak an octave under the key that is pressed, so "the lead an octave down" and some chords were
    playing in the bass's register (60-250 Hz) on top of the bass and the kick: mud;
  - one lead was a click with no body (it filled 19 % of the time; the kept leads fill 41 and 71 %);
  - one bass buzzed (as loud at 2-8 kHz as the chords); the kept basses have next to nothing up there;
  - no pad: both kept pieces stand on a wide, quiet pad that fills 250 Hz - 2 kHz all the time;
  - the level over 100 ms moved 5 to 8 dB (a wall) or 21 dB (holes); the kept pieces move about 11 dB.

    uv run --no-project --python 3.11 --with dawdreamer --with numpy python music/mixcheck.py        # the references
"""
import numpy as np

import pieces
import surge

SR = surge.SR
EDGES = [30, 60, 120, 250, 500, 1000, 2000, 4000, 8000, 20000]
TONAL = ("lead", "double", "answer", "chords", "pad")
# The two kept day pieces, by band (dB of the whole mix), from this file's own report: the envelope a new day mix must sit in.
KEPT = np.array([[-11.8, -7.7, -10.6, -9.9, -4.9, -7.1, -13.8, -19.8, -21.8], [-14.0, -8.6, -5.5, -4.4, -10.5, -13.5, -15.3, -20.1, -23.0]])
ROOM = 3.0
# The two kept night pieces (Side street night, Far shore night): slow, no drums, dark on top. A slow, near-ambient
# piece is held against days and nights together: anywhere between the two is a balance the user has kept.
NIGHT = np.array([[-5.3, -8.5, -11.9, -11.4, -7.1, -6.3, -45.9, -54.2, -60.3], [-9.8, -7.7, -12.0, -7.3, -3.7, -13.4, -21.8, -47.4, -55.3]])
RANGES = {"day": dict(bands=KEPT, lead=(0.35, 0.85), spread=(8, 14), crest=(14.5, 21)),
          "chill": dict(bands=np.vstack([KEPT, NIGHT]), lead=(0.35, 0.95), spread=(6, 14), crest=(13.5, 21))}


def stems(st, arrange):
    """Every part of a piece alone, at its mix level: the stem stage of pieces.render(), note for note (the same
    random seed), so that what is measured here is what that function mixes."""
    rng = np.random.default_rng(sum(map(ord, st["id"])))
    score, steps, _ = arrange(st)
    step = 60 / st["bpm"] / 4
    n = int(round(steps * step * SR))

    def when(s):
        if st["swing"] == 0.5:
            return s * step
        beat, f = divmod(s / 4, 1)
        return (beat + (f * 2 * st["swing"] if f < 0.5 else st["swing"] + (f - 0.5) * 2 * (1 - st["swing"]))) * 4 * step

    sounds = pieces.KIT | st.get("kit", {}) | {"lead": st["lead"], "double": st.get("double"), "chords": st["chords"], "pad": st["pad"], "bass": st["bass_sound"]}
    out = {}
    for part, notes in score.items():
        ev = [(m, vel * (1 + rng.normal(0, 0.04)), max(0.0, when(s) + (0.0 if part in ("kick", "bass") else rng.normal(0.004, 0.005))),
               ln * step * rng.uniform(0.86, 0.97)) for s, ln, m, vel in notes]
        y = surge.play(sounds[part], ev, n / SR + 6.0, st["bpm"] if st.get("sync") else None)
        y = y[:, :n] + np.pad(y[:, n:2 * n], ((0, 0), (0, max(0, 2 * n - y.shape[1]))))[:, :n]
        f = np.fft.rfftfreq(n, 1 / SR)
        y = np.fft.irfft(np.fft.rfft(y, axis=1) / np.sqrt(1 + ((35 if part in ("kick", "bass") else 110) / np.maximum(f, 1e-3)) ** 4), n, axis=1)
        active = np.abs(y).max(axis=0) > 1e-4
        rms = np.sqrt((y[:, active] ** 2).mean()) if active.any() else 0.0
        if rms < 3e-4:
            raise SystemExit(f"{st['id']}: the {part} ({sounds[part]}) is silent")
        out[part] = y * 10 ** ((pieces.LEVEL | st.get("levels", {}))[part] / 20) / rms
    return out


def bus(st):
    """The stems summed as pieces.render() sums them: the kick ducks pad, chords and bass; level; a peak limiter."""
    n = next(iter(st.values())).shape[1]
    env = np.zeros(n)
    if "kick" in st:
        env = np.abs(st["kick"]).max(axis=0)
        env = np.convolve(env, np.exp(-np.arange(int(0.25 * SR)) / (0.09 * SR)), "full")[:n]
        env = np.clip(env / (np.percentile(env, 99.5) + 1e-9), 0, 1)
    mix = sum(y * (1 - pieces.DUCK.get(part, 0) * env) for part, y in st.items())
    mix *= 10 ** (-17 / 20) / np.sqrt((mix ** 2).mean())
    pk = np.abs(mix).max(axis=0)
    blocks = np.array([pk[max(0, i - 240): i + 288].max() for i in range(0, n, 48)])
    gain = np.interp(np.arange(n), np.arange(0, n, 48), np.minimum(1.0, 0.89 / np.maximum(blocks, 1e-9)))
    return np.clip(mix * np.convolve(np.pad(gain, 240, mode="edge"), np.ones(481) / 481, "valid"), -0.95, 0.95)


def bands(y):
    S = np.abs(np.fft.rfft(y.mean(axis=0))) ** 2
    fr = np.fft.rfftfreq(y.shape[1], 1 / SR)
    return np.array([S[(fr >= a) & (fr < b)].sum() for a, b in zip(EDGES, EDGES[1:])]) / y.shape[1] ** 2 * 2


def fills(y):
    """The share of the time a part is within 20 dB of its own loudest 50 ms."""
    e = np.sqrt(np.convolve(y.mean(axis=0) ** 2, np.ones(2400) / 2400, "same")[::2400])
    return float((e > e.max() * 0.1).mean())


def check(st, say=print, ref="day"):
    """Prints the mix part by part and returns what is out of the kept pieces' range, as sentences."""
    r = RANGES[ref]
    kept = r["bands"]
    mix = sum(st.values())
    whole = bands(mix).sum()
    db = lambda v: 10 * np.log10(v / whole + 1e-12)
    prof = db(bands(mix))
    say("   part     level   " + " ".join(f"{a:>6d}" for a in EDGES[:-1]) + "   width  fills")
    say("   MIX              " + " ".join(f"{v:6.1f}" for v in prof))
    bad = []
    for part, y in sorted(st.items(), key=lambda kv: -float((kv[1] ** 2).mean())):
        b, mid, side = db(bands(y)), y.mean(axis=0), (y[0] - y[1]) / 2
        say(f"   {part:7s} {10 * np.log10((y ** 2).mean() / (mix ** 2).mean()):6.1f}   " + " ".join(f"{v:6.1f}" for v in b)
            + f"   {10 * np.log10((side ** 2).mean() / (mid ** 2).mean() + 1e-9):5.1f}   {fills(y):.2f}")
        if part in TONAL and 10 * np.log10((10 ** (b[:2] / 10)).sum()) > -30:
            bad.append(f"the {part} sounds under 120 Hz, in the bass's register")
        if part == "bass" and 10 * np.log10((10 ** (b[6:] / 10)).sum()) > -24:
            bad.append("the bass buzzes over 2 kHz")
        if part == "bass" and 10 * np.log10((10 ** (b[:3] / 10)).sum()) < -12:
            bad.append("the bass is thin under 250 Hz")
    if "lead" in st and not r["lead"][0] <= fills(st["lead"]) <= r["lead"][1]:
        bad.append(f"the lead fills {fills(st['lead']):.0%} of the time (kept days: 41 and 71 %; nights: 73 and 91 %)")
    if "pad" not in st:
        bad.append("no pad under the piece")
    for i, v in enumerate(prof):
        if not kept[:, i].min() - ROOM <= v <= kept[:, i].max() + ROOM:
            bad.append(f"{EDGES[i]}-{EDGES[i + 1]} Hz is at {v:.1f} dB of the mix (kept: {kept[:, i].min():.1f} to {kept[:, i].max():.1f})")
    m = mix.mean(axis=0)
    e = np.sqrt(np.convolve(m ** 2, np.ones(4800) / 4800, "same")[::4800])
    spread = 20 * np.log10(np.percentile(e, 95) / np.percentile(e, 10))
    crest = 20 * np.log10(np.abs(m).max() / np.sqrt((m ** 2).mean()))
    say(f"   level over 100 ms moves {spread:.1f} dB (kept 10.8, 10.6)   crest {crest:.1f} dB (kept 18.9, 16.3)")
    if not r["spread"][0] <= spread <= r["spread"][1]:
        bad.append(f"the level moves {spread:.1f} dB over 100 ms (kept days: about 11; nights: about 8)")
    if not r["crest"][0] <= crest <= r["crest"][1]:
        bad.append(f"crest {crest:.1f} dB (kept: 15 to 19)")
    return bad


if __name__ == "__main__":
    for p in pieces.PIECES:
        if p["id"] in ("cute1", "shore"):
            st = pieces.BASE | p
            print(f"\n== {st['title']}")
            print("   out of range:", check(stems(st, pieces.side_street)) or "nothing")
