"""Render the game's sound effects into the web client: src/megastructure/web/audio/.

    uv run python tools/build_audio.py

Sources of truth:
  music/sfx.py         every sound's generator, category and level
  music/sfx_map.json   which sound an item makes when placed ("place") and a ground when laid ("ground")
Output (not committed: rebuild after changing either source):
  audio/<name>_<variant>.wav   16-bit stereo, 32 kHz
  audio/sfx.json               the manifest the client reads: sounds, place (by block name), ground, version
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


def version() -> str:
    h = hashlib.sha1()
    for f in ("sfx.py", "sfx_map.json"):
        h.update((MUSIC / f).read_bytes())
    return h.hexdigest()[:10]


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
    manifest = {"version": version(), "rate": RATE, "sounds": sounds, "place": blocks, "ground": grounds}
    (out / "sfx.json").write_text(json.dumps(manifest, indent=1))
    size = sum(f.stat().st_size for f in out.glob("*.wav")) / 1e6
    print(f"built {out.relative_to(ROOT)}: {len(sounds)} sounds, {sum(len(s['files']) for s in sounds.values())} files, {size:.1f} MB")
    return manifest


if __name__ == "__main__":
    sys.path.insert(0, str(ROOT / "src"))
    build()
