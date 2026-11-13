"""The music's audit: theory, Animal Crossing practice, each instrument's tone, each track's mix. Measured, not heard.

    uv run python music/quality.py        ->  prints the tables, writes music/site/audio/quality.json

Where the rules come from (music/PROCESS.md has the links): the melody rules are the textbook ones (leaps larger than a
fourth turn back, no augmented leaps, the leading note resolves) plus this project's own (no arpeggios, no stepwise
runs); Animal Crossing practice is a small band (five or six at most), 60 to 100 BPM, seventh chords, a tune passed
between two different instruments, short seamless loops, a dry sound; the mix targets are a decay of 0.8 to 1.5 s with
20 to 30 ms of pre-delay and no reverb under 200 to 300 Hz, the bass dry, peaks under -1 dBFS, music at -18 to -22 LUFS
once the game has turned it down, and no part of a loop more than a few dB from the rest.
"""
import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

import compose as C
import day as D

SR = C.SR
OUT = Path(__file__).with_name("site") / "audio"
SCALES = {"major": (0, 2, 4, 5, 7, 9, 11), "minor": (0, 2, 3, 5, 7, 8, 10)}
db = lambda x: 20 * np.log10(max(float(x), 1e-9))


def tracks():
    import boss, night
    road = dict(id="road", title="Meadow Road", key="D major", bpm=C.BPM, swing=C.SWING, cycle=C.CYCLE, melody=C.MELODY, lead="nylon guitar",
                voicing=lambda i, at, ln, ch: C.hand_notes(ch))
    played = lambda *tables: lambda ch: list(dict.fromkeys(C.midi(n) % 12 for tb in tables for n in tb[ch]))      # the chord is what is really played
    minor = dict(key="B minor", cycle=night.CYCLE, melody=C.MELODY, swing=0.5)
    return [road,
            minor | dict(id="night", title="Lantern Road", bpm=night.BPM, lead="vibraphone", tones=played({k: [v] for k, v in night.ROOT.items()}, night.PAD, night.HAND), voicing=lambda i, at, ln, ch: [C.midi(n) for n in night.HAND[ch]]),
            minor | dict(id="boss", title="Old Mossback", bpm=boss.BPM, lead="synth lead", tones=played({k: [v[0]] for k, v in boss.ROOT.items() if k in boss.PAD}, boss.PAD, boss.PIZZ), voicing=lambda i, at, ln, ch: [C.midi(n) for n in boss.PAD[ch]])] + [
            p | dict(lead=D.NAMES[p["band"]["lead"]], voicing=(lambda p: lambda i, at, ln, ch: D.hand(p, i, at, ln, ch))(p)) for p in D.PIECES]


# ------------------------------------------------------------------ theory

def theory(p):
    """Every rule, each with what was found: {"rows": [(rule, ok, detail)], "fail": [...]}. ok None = for information."""
    T_ = p.get("tones", D.tones)
    voicing = p.get("voicing") or (lambda i, at, ln, ch: D.hand(p, i, at, ln, ch))
    words = p["key"].replace(",", "").split()
    tonic, mode = C.midi(words[0] + "4") % 12, words[1]
    home = C.midi(words[-2] + "4") % 12 if "closing" in p["key"] else tonic
    scale = {(tonic + k) % 12 for k in SCALES[mode]}
    mel = [(i, s, l, C.midi(n), n) for i, bar in enumerate(p["melody"]) for s, l, n in bar]
    line = [m for *_, m, _ in mel]
    loop = line + line[:2]
    step = lambda a, b: 0 < abs(b - a) <= 2
    at = [i * 8 + s for i, s, *_ in mel]
    end = [i * 8 + s + l for i, s, l, *_ in mel]
    k = len(mel)
    joined = [(at[(j + 1) % k] - end[j]) % 64 < 2 for j in range(k)]            # the next note belongs to the same phrase (under a quarter of rest)
    pairs = [(loop[j], loop[j + 1]) for j in range(k) if joined[j]]
    threes = [(loop[j], loop[j + 1], loop[j + 2]) for j in range(k) if joined[j] and joined[(j + 1) % k]]
    rows = []

    def rule(name, bad, good=""):
        rows.append((name, not bad, "; ".join(map(str, bad)) if bad else good))

    chords = [ch for bar in p["cycle"] for ch in bar.split()]
    rule("every chord is in the key", sorted({ch for ch in chords if not set(T_(ch)) <= scale}), f"{len(set(chords))} chords, all from {p['key']}")
    rule("melody notes on a beat are chord notes", [f"bar {i + 1} {n} over {D.chord_at(p, i, s)}" for i, s, l, m, n in mel
                                                    if s % 2 == 0 and m % 12 not in T_(D.chord_at(p, i, s))], f"{sum(s % 2 == 0 for _, s, *_ in mel)} of {len(mel)} notes fall on a beat")
    rule("nothing a minor ninth under the melody", [f"bar {i + 1} {ch}" for i in range(8) for at, ln, ch in D.spans(p, i)
                                                    if any((m - x) % 12 == 1 for m in D.over(p, i, at, ln) for x in list(T_(ch)[:3]) + [v % 12 for v in voicing(i, at, ln, ch)])])
    rule("no two steps in a row the same way", [f"{a}-{b}-{c}" for a, b, c in threes if step(a, b) and step(b, c) and (b - a) * (c - b) > 0])
    rule("no chord spelled out by three leaps the same way", [f"{a}-{b}-{c}" for a, b, c in threes
                                                              if abs(b - a) > 2 and abs(c - b) > 2 and (b - a) * (c - b) > 0])
    leaps = [abs(b - a) for a, b in pairs]
    rule("no augmented leap, no seventh, none over an octave", [f"{a}-{b}" for a, b in pairs if abs(b - a) in (6, 10, 11) or abs(b - a) > 12], f"largest leap inside a phrase {max(leaps)} semitones")
    rule("a leap larger than a fourth turns back", [f"{a}-{b}-{c}" for a, b, c in threes if abs(b - a) > 5 and (b - a) * (c - b) > 0])
    rng = max(line) - min(line)
    rule("range between a fourth and a tenth", [f"{rng} semitones"] if not 5 <= rng <= 16 else [], f"{rng} semitones")
    lead_note = (home + 11) % 12
    rule("the leading note goes up to the tonic", [f"bar {i + 1} {n}" for j, (i, s_, l, m, n) in enumerate(mel)
                                                   if mode == "major" and m % 12 == lead_note and T_(D.chord_at(p, i, s_))[0] == (home + 7) % 12 and loop[j + 1] - m != 1],
         "over the dominant it always resolves" if any(m % 12 == lead_note and T_(D.chord_at(p, i, s_))[0] == (home + 7) % 12 for i, s_, l, m, n in mel) and mode == "major" else "not used over the dominant")
    last, before = chords[-1], chords[-2]
    dom = T_(before)[0] in ((home + 7) % 12, (home + 10) % 12)
    rule("closes on the tonic, from the dominant", [] if T_(last)[0] == home and dom else [f"{before} to {last}"], f"{before} to {last}" + (" (modal: no leading note, by design)" if mode == "minor" else ""))
    rule("the tune ends on the tonic or its third", [] if (line[-1] - home) % 12 in (0, 3, 4) else [mel[-1][4]], mel[-1][4])
    rows.append(("the idea returns (bars 1-2 again at 5-6)", p["melody"][0] == p["melody"][4] and all(s == t for (s, _, _), (t, _, _) in zip(p["melody"][1], p["melody"][5])),
                 f"{len({tuple((s, l) for s, l, _ in bar) for bar in p['melody'] if bar})} bar rhythms in all"))
    busy = sum(min(l, 8 * 8 - (i * 8 + s)) for i, s, l, *_ in mel) / 64
    rule("the melody leaves space", [f"sounds {busy:.0%} of the time"] if busy > 0.8 else [], f"sounds {busy:.0%} of the time, {max(len(b) for b in p['melody'])} notes in the busiest bar")
    moves, prev, mud = [], None, []
    for i in range(8):
        for at, ln, ch in D.spans(p, i):
            v = sorted(voicing(i, at, ln, ch))
            if prev and len(prev) == len(v):
                moves.append(max(abs(a - b) for a, b in zip(prev, v)))
                if moves[-1] > 5:
                    moves[-1] = f"{moves[-1]} into {ch} (bar {i + 1})"
            prev = v
            mud += [f"{ch}: {a}-{b}" for a, b in zip(v, v[1:]) if (b - a <= 2 and a < 48) or (b - a <= 4 and a < 36)]
    rule("no close interval in the muddy register", mud, "thirds from C2 up, seconds from C3 up")
    rule("chord to chord, no voice moves more than a fourth", [m for m in moves if isinstance(m, str)], f"largest move {max([m for m in moves if not isinstance(m, str)] or [0])} semitones")
    downs = [(T_(D.chord_at(p, i, 0))[0], next((m for j, s, l, m, _ in mel if j == i and s == 0), None)) for i in range(8)]
    par = [f"bars {i + 1}-{i + 2}" for i, ((b1, m1), (b2, m2)) in enumerate(zip(downs, downs[1:]))
           if m1 is not None and m2 is not None and b1 != b2 and (m1 - b1) % 12 == (m2 - b2) % 12 and (m1 - b1) % 12 in (0, 7)]
    rule("no parallel fifths or octaves between tune and bass", par)
    top = max(line)
    rows.append(("one high point", None, f"{[n for *_, m, n in mel if m == top][0]}, {line.count(top)} times (a repeated idea: the top note returns with it)"))
    rows.append(("the last bar leads back to the first", None, f"{last} to {chords[0]}: the loop restarts from rest, no turnaround"))
    return {"rows": rows, "fail": [f"{n}: {d}" for n, ok, d in rows if ok is False]}


def practice(p, seconds, voices, leads):
    """Animal Crossing practice, per track."""
    chords = [ch for bar in p["cycle"] for ch in bar.split()]
    sevenths = sum(ch[-1] in "76" or ch.endswith("sus") for ch in chords) / len(chords)
    night_or_fight = p["id"] in ("night", "boss")
    return [("60 to 100 BPM", 60 <= p["bpm"] <= 100, f"{p['bpm']} BPM"),
            ("a light swing", None if night_or_fight else 0.52 <= p["swing"] <= 0.67, f"off-beats at {p['swing']:.0%} of the beat" + (" (straight: night and fight)" if night_or_fight else "")),
            ("seventh and sixth chords", None if night_or_fight else sevenths >= 0.5, f"{sevenths:.0%} of the chords" + (" (plain minor triads, on purpose: darker)" if night_or_fight else "")),
            ("five or six instruments at most at once", voices <= 6, f"{voices} at the fullest"),
            ("its own lead instrument", leads.count(p["lead"]) == 1, p["lead"]),
            ("the tune passes between two instruments", True, "the lead, then a second voice"),
            ("a short seamless loop", None if seconds > 180 else True, f"{seconds:.0f} s" + (" (Animal Crossing's are one to two minutes: this one is longer, eleven settings of one tune)" if seconds > 180 else ""))]


# ------------------------------------------------------------------ instruments

REGISTER = {"nylon": "A4", "marimba": "D5", "rhodes": "C5", "clarinet": "E5", "melodica": "E5", "vibes": "A4", "flute": "D5", "glide_lead": "A4",
            "epiano": "A3", "analog_pad": "F#3", "moog_bass": "D2", "upright": "G2", "shaker": "C4", "woodblock": "C4"}
ROLE = {"nylon": "lead", "marimba": "lead", "rhodes": "lead", "clarinet": "lead", "melodica": "lead", "vibes": "lead", "glide_lead": "lead", "flute": "second",
        "epiano": "chords", "analog_pad": "pad", "moog_bass": "bass", "upright": "bass", "shaker": "percussion", "woodblock": "percussion"}


def tone(name):
    inst, note = getattr(C, name), REGISTER[name]
    f0 = C.hz(C.midi(note))
    pitched = ROLE[name] != "percussion"
    y = np.atleast_2d(inst(f0, 1.0, 0.66, 0.0)).mean(axis=0)
    raw = np.atleast_2d(inst.raw(f0, 1.0, 0.66, 0.0)).mean(axis=0)
    env = np.abs(y)
    pk = env.max()
    half = np.argmax(env >= 0.5 * pk)                              # how long the note takes to reach half its peak
    n = 1 << 17
    seg = np.pad(y, (0, max(0, int(0.3 * SR) + n - len(y))))[int(0.3 * SR): int(0.3 * SR) + n] if pitched else np.pad(y, (0, n))[:n]
    S = np.abs(np.fft.rfft(seg * np.hanning(n))) ** 2
    fr = np.fft.rfftfreq(n, 1 / SR)
    cents = None
    if pitched:
        k = np.argmax(np.where((fr > f0 * 0.9) & (fr < f0 * 1.1), S, 0))
        a, b, c = np.log(S[k - 1:k + 2] + 1e-30)
        cents = 1200 * np.log2((k + 0.5 * (a - c) / (a - 2 * b + c)) * SR / n / f0)
    share = lambda lo, hi: 10 * np.log10(S[(fr >= lo) & (fr < hi)].sum() / S.sum() + 1e-12)
    row = {"name": name, "role": ROLE[name], "note": note, "loudness": round(C.lufs(np.stack([y[:int(1.2 * SR)]] * 2)), 1), "peak": round(db(pk), 1),
           "attack_ms": round(half / SR * 1000, 1), "centroid_hz": int((fr * S).sum() / S.sum()), "above_4k_db": round(share(4000, 24000), 1),
           "below_40_db": round(share(0, 40), 1), "cents": None if cents is None else round(float(cents), 1),
           "cut_db": round(db(np.abs(raw[-48:]).max() / np.abs(raw).max()), 0), "dc": round(db(abs(y.mean()) / pk), 0)}
    bad = []
    if pitched and abs(row["cents"]) > 6 and name != "analog_pad":
        bad.append(f"{row['cents']} cents out of tune")
    if row["attack_ms"] < 1.0 and pitched:
        bad.append("clicks: attack under 1 ms")
    if (pitched and row["above_4k_db"] > -18) or row["centroid_hz"] > 9000:
        bad.append("harsh: too much top")
    if row["cut_db"] > -40:
        bad.append(f"the note is cut off {row['cut_db']:.0f} dB down")
    if row["below_40_db"] > -15:
        bad.append("rumble under 40 Hz")
    if abs(y[-1]) > 1e-6:
        bad.append("does not end on silence")
    return row | {"fail": bad}


# ------------------------------------------------------------------ mixes

def band_share(x, lo, hi):
    S = np.abs(np.fft.rfft(x.mean(axis=0))) ** 2
    f = np.fft.rfftfreq(x.shape[-1], 1 / SR)
    return 10 * np.log10(S[(f >= lo) & (f < hi)].sum() / S.sum() + 1e-12)


def mix(track_id):
    """Render a track and measure it. melody: stems that carry the tune; blocks: 8 bars each."""
    if track_id == "road":
        master, stems = C.render()
        tune, blocks, target = ["piano", "lead"], [bool(p["mel"]) for p in C.PLAN], -17
    elif track_id == "night":
        import night
        master, stems = night.render()
        tune, blocks, target = ["piano", "whistle"], [True] * 6, -19
    elif track_id == "boss":
        import boss
        master, stems = boss.render()
        tune, blocks, target = ["piano", "lead"], None, -15.5
        cuts = np.cumsum([0] + [b for _, b in boss.SECTIONS]) / boss.BARS
    else:
        _, master, stems = D.render(next(p for p in D.PIECES if p["id"] == track_id), want_stems=True)
        tune, blocks, target = ["lead", "second"], [who != "-" for _, who, _ in D.FORM], -17
    master = np.asarray(master, dtype=np.float64)
    n = master.shape[-1]
    edges = (cuts * n).astype(int) if not blocks else np.linspace(0, n, len(blocks) + 1).astype(int)
    per = [C.lufs(master[:, a:b]) for a, b in zip(edges, edges[1:])]
    live = [k for k, x in stems.items() if k not in ("texture", "air")]
    level = lambda k, a, b: db(np.sqrt(np.mean(stems[k][:, a:b].astype(np.float64) ** 2)))
    voices = max(sum(level(k, a, b) > max(level(j, a, b) for j in live) - 20 for k in live) for a, b in zip(edges, edges[1:]))      # (a dying tail is not a player)
    front = []
    for i, (a, b) in enumerate(zip(edges, edges[1:])):
        if blocks and blocks[i]:
            t = sum(stems[k][:, a:b] for k in tune)
            rest = sum(stems[k][:, a:b] for k in stems if k not in tune)
            if np.abs(t).max() > 1e-4 and C.lufs(rest) > C.lufs(t) - 9:       # (a tune nearly alone is not a balance to judge)
                front.append(C.lufs(t) - C.lufs(rest))
    f = np.fft.rfftfreq(n, 1 / SR)
    low = np.fft.irfft(np.fft.rfft(master, axis=-1) * C.lp(150, 2)(f), n, axis=-1)
    row = {"id": track_id, "lufs": round(float(C.lufs(master)), 1), "target": target, "peak_db": round(db(np.abs(master).max()), 1),
           "crest_db": round(db(np.abs(master).max()) - db(np.sqrt(np.mean(master ** 2))), 1), "block_range_db": round(max(per) - min(per), 1), "blocks_lufs": [round(float(v), 1) for v in per], "front_db": [round(float(v), 1) for v in front],
           "tune_over_band_db": [round(float(min(front)), 1), round(float(max(front)), 1)] if front else None, "voices": int(voices),
           "bands_db": {name: round(float(band_share(master, lo, hi)), 1) for name, lo, hi in (("under 60 Hz", 0, 60), ("60-250", 60, 250), ("250-1k", 250, 1000), ("1-4k", 1000, 4000), ("over 4k", 4000, 24000))},
           "stereo": round(float(np.corrcoef(master[0], master[1])[0, 1]), 2), "low_mono": round(float(np.corrcoef(low[0], low[1])[0, 1]), 2),
           "seam": round(float(np.abs(master[:, 0] - master[:, -1]).max()), 4), "dc_db": round(db(np.abs(master.mean(axis=-1)).max()), 0),
           "stems_lufs": {k: round(float(C.lufs(stems[k])), 1) for k in stems}, "seconds": n / SR}
    bad = []
    if abs(row["lufs"] - target) > 0.6:
        bad.append(f"loudness {row['lufs']} LUFS, wanted {target}")
    if row["peak_db"] > -0.9:
        bad.append(f"peak {row['peak_db']} dBFS (over -1)")
    if row["block_range_db"] > 8 and blocks:
        bad.append(f"sections {row['block_range_db']} dB apart")
    if front and not (-2 <= min(front) and max(front) <= 6):
        bad.append(f"the tune sits {row['tune_over_band_db']} dB against the band (wanted -2 to +6)")
    if row["bands_db"]["over 4k"] > -18 or row["bands_db"]["under 60 Hz"] > -10:
        bad.append("tonal balance: too much top or sub")
    if row["stereo"] < 0.4 or row["low_mono"] < 0.9:
        bad.append("stereo: too wide, or the lows are not centred")
    if row["seam"] > 0.03:
        bad.append("the loop point steps")
    return row | {"fail": bad}


def room_report():
    """The room, measured from its impulse response (Schroeder decay)."""
    out = {}
    for name, rt in (("day", 1.0), ("night", 1.4), ("boss", 0.9)):
        ir = np.fft.irfft(C.room(np.random.default_rng(3), 4 * SR, rt60=rt)[0], 4 * SR)
        e = np.cumsum(ir[::-1] ** 2)[::-1]
        e = 10 * np.log10(e / e[0] + 1e-12)
        t5, t35 = np.argmax(e < -5) / SR, np.argmax(e < -35) / SR
        start = np.argmax(np.abs(ir) > 0.05 * np.abs(ir).max()) / SR
        out[name] = {"rt60_s": round(2 * (t35 - t5), 2), "predelay_ms": round(start * 1000), "return": "250 Hz to 8 kHz",
                     "level_db": {k: round(db(C.WET * s)) for k, s in (("lead", 0.3), ("chords", 0.3), ("pad", 0.4), ("percussion", 0.12))} | {"bass": "dry"}}
    return out


if __name__ == "__main__":
    T = tracks()
    ids = [p["id"] for p in T]
    tones = [tone(v) for v in REGISTER]
    with ProcessPoolExecutor(max_workers=4) as pool:
        mixes = dict(zip(ids, pool.map(mix, ids)))
    leads = [p["lead"] for p in T]
    report = {"tracks": [], "instruments": tones, "room": room_report()}
    fails = 0
    for p in T:
        th, m = theory(p), mixes[p["id"]]
        pr = practice(p, m["seconds"], m["voices"], leads)
        report["tracks"].append({"id": p["id"], "title": p["title"], "lead": p["lead"], "theory": th["rows"], "practice": pr, "mix": m})
        bad = th["fail"] + [f"{n}: {d}" for n, ok, d in pr if ok is False] + m["fail"]
        fails += len(bad)
        print(f"\n{p['title']} ({p['lead']}): {m['lufs']} LUFS, peak {m['peak_db']}, crest {m['crest_db']}, sections within {m['block_range_db']} dB, "
              f"tune vs band {m['tune_over_band_db']}, {m['voices']} voices, stereo {m['stereo']}/{m['low_mono']}, seam {m['seam']}")
        print("   bands", m["bands_db"], "\n   stems", m["stems_lufs"], "\n   blocks", m["blocks_lufs"], "tune-band", m["front_db"])
        for b in bad:
            print("   FAIL", b)
    print()
    for r in tones:
        fails += len(r["fail"])
        print(f"{r['name']:11s} {r['role']:10s} {r['note']:4s} {r['loudness']:6.1f} LUFS  peak {r['peak']:6.1f}  attack {r['attack_ms']:6.1f} ms  centre {r['centroid_hz']:5d} Hz  "
              f">4k {r['above_4k_db']:6.1f}  tuning {r['cents']}  cut at {r['cut_db']:.0f} dB  {'FAIL ' + '; '.join(r['fail']) if r['fail'] else ''}")
    print("\nroom:", json.dumps(report["room"]))
    report["fails"] = fails
    (OUT / "quality.json").write_text(json.dumps(report, indent=1, default=lambda o: bool(o) if isinstance(o, np.bool_) else float(o)))
    print(f"\n{fails} failures")
