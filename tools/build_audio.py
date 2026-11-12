"""Render the game's sound effects into the web client: src/megastructure/web/audio/.

    uv run python tools/build_audio.py

Sources of truth:
  music/sfx.py         every sound's generator, category and level
  music/sfx_map.json   which sound an item makes when placed ("place") and a ground when laid ("ground")
Output (not committed: rebuild after changing either source):
  audio/<name>_<variant>.wav   16-bit stereo, 32 kHz
  audio/music.wav              the background loop, from music/site/audio/master.wav (render it with music/compose.py)
  audio/boss.wav               the boss fight's loop, from music/site/audio/boss.wav (music/boss.py)
  audio/sfx.json               the manifest the client reads: sounds, place (by block name), ground, music, version
The build fails if a placeable item or a fillable ground has no sound, or the map names a sound that does not exist.
"""

import hashlib
import importlib.util
import json
import sys
import wave
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
MUSIC = ROOT / "music"
OUT = ROOT / "src" / "megastructure" / "web" / "audio"
RATE = 32000          # the sounds are low-passed at 12 kHz, so nothing audible is lost and files are a third smaller


def load_sfx():
    spec = importlib.util.spec_from_file_location("megastructure_sfx", MUSIC / "sfx.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def sound_names() -> set[str]:
    """The names music/sfx.py defines, read without importing it (fast, no numpy)."""
    import re
    return set(re.findall(r'^@sfx\("([a-z_]+)"', (MUSIC / "sfx.py").read_text(), re.M))


def place_maps(names: set[str]) -> tuple[dict, dict]:
    """(block name -> sound, ground name -> sound), checked against the game's own tables."""
    from megastructure import tiles as T
    table = json.loads((MUSIC / "sfx_map.json").read_text())
    blocks = {}
    for item, block in T.PLACEABLE.items():
        if item not in table["place"]:
            raise SystemExit(f"music/sfx_map.json: no sound for placing '{item}'")
        blocks[block] = table["place"][item]
    grounds = {}
    for results in T.FILLERS.values():
        for ground in set(results.values()):
            if ground not in table["ground"]:
                raise SystemExit(f"music/sfx_map.json: no sound for laying '{ground}' ground")
            grounds[ground] = table["ground"][ground]
    missing = sorted((set(blocks.values()) | set(grounds.values())) - names)
    if missing:
        raise SystemExit(f"music/sfx_map.json names sounds that music/sfx.py does not define: {missing}")
    return blocks, grounds


def resample(st: np.ndarray, sr: int, to: int) -> np.ndarray:
    """Band-limited resampling: keep the spectrum below the new Nyquist, drop the rest."""
    if sr == to:
        return st
    n = st.shape[1]
    m = int(round(n * to / sr))
    spec = np.fft.rfft(st, axis=1)[:, : m // 2 + 1]
    return np.fft.irfft(spec, m, axis=1) * (m / n)


def write_wav(path: Path, st: np.ndarray, rate: int):
    pcm = (np.clip(st, -1, 1) * 32767).round().astype("<i2").T.copy()
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(pcm.tobytes())


MASTER = MUSIC / "site" / "audio" / "master.wav"      # the rendered soundtrack (music/compose.py)
BOSS = MUSIC / "site" / "audio" / "boss.wav"          # the boss fight's loop (music/boss.py)


def version() -> str:
    h = hashlib.sha1()
    for f in ("sfx.py", "sfx_map.json"):
        h.update((MUSIC / f).read_bytes())
    for f in (MASTER, BOSS):
        if f.exists():
            h.update(f"{f.stat().st_size}:{f.stat().st_mtime_ns}".encode())
    return h.hexdigest()[:10]


def build_music(out: Path, src: Path = None, name: str = "music.wav") -> dict | None:
    """A music loop (the background one, or the boss fight's), resampled like the effects. None (and a note) when it
    has not been rendered."""
    src = src or MASTER
    if not src.exists():
        print(f"no {name}: render it first with `uv run python music/{'boss' if src == BOSS else 'compose'}.py`")
        return None
    with wave.open(str(src)) as w:
        sr, ch = w.getframerate(), w.getnchannels()
        st = (np.frombuffer(w.readframes(w.getnframes()), "<i2").reshape(-1, ch).T / 32768).astype(np.float64)
    st = resample(st, sr, RATE)
    write_wav(out / name, st, RATE)
    return {"file": name, "seconds": st.shape[1] / RATE}


def build(out: Path = OUT) -> dict:
    blocks, grounds = place_maps(sound_names())       # fail before the slow part
    sfx = load_sfx()
    out.mkdir(parents=True, exist_ok=True)
    for old in list(out.glob("*.wav")) + list(out.glob("sfx.json")):
        old.unlink()
    sounds = {}
    for name in sfx.S:
        m = sfx.META[name]
        files = []
        for v in range(m["variants"]):
            f = f"{name}_{v}.wav"
            write_wav(out / f, resample(sfx.render(name, v), sfx.SR, RATE), RATE)
            files.append(f)
        sounds[name] = {"files": files, "category": m["cat"], "pitch": bool(m["vary"])}   # tuned sounds are never re-pitched
    manifest = {"version": version(), "rate": RATE, "sounds": sounds, "place": blocks, "ground": grounds,
                "music": build_music(out), "boss": build_music(out, BOSS, "boss.wav")}
    (out / "sfx.json").write_text(json.dumps(manifest, indent=1))
    size = sum(f.stat().st_size for f in out.glob("*.wav") if f.name not in ("music.wav", "boss.wav")) / 1e6
    music = f", music {(out / 'music.wav').stat().st_size / 1e6:.0f} MB" if manifest["music"] else ""
    print(f"built {out.relative_to(ROOT)}: {len(sounds)} sounds, {sum(len(s['files']) for s in sounds.values())} files, {size:.1f} MB{music}")
    return manifest


if __name__ == "__main__":
    sys.path.insert(0, str(ROOT / "src"))
    build()
