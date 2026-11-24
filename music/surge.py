"""Plays the Surge XT synthesizer from Python (DawDreamer hosts the plugin and renders offline).

The user, after three sets of instruments I had built myself without being able to hear them: "I want that music to be
generated from python scripts, or whatever language or library that fits... people do sounds with programming... use
tools". Surge XT (GPL-3, `brew install --cask surge-xt`; on Linux its .deb) comes with about 3000 sounds made by sound designers; this
module only sends them notes.

    uv run --no-project --python 3.11 --with dawdreamer --with numpy python music/surge.py probe "Keys/EP 1" ...
"""
from pathlib import Path
import os
import struct
import sys
import tempfile

import numpy as np

SR = 48000
# where Surge XT is: macOS (the cask), then Linux (the .deb: a CI runner), or SURGE_PLUGIN / SURGE_DATA
_PLUGINS = ["/Library/Audio/Plug-Ins/VST3/Surge XT.vst3", "/usr/lib/vst3/Surge XT.vst3", "/usr/local/lib/vst3/Surge XT.vst3"]
_DATAS = ["/Library/Application Support/Surge XT", "/usr/share/surge-xt", "/usr/local/share/surge-xt"]
PLUGIN = os.environ.get("SURGE_PLUGIN") or next((p for p in _PLUGINS if Path(p).exists()), _PLUGINS[0])
DATA = Path(os.environ.get("SURGE_DATA") or next((p for p in _DATAS if Path(p).exists()), _DATAS[0]))
TABLE = ".ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+"
_engine, _count = None, 0


def find(name):
    """'Keys/EP 1' is a factory sound, 'Cybersoda/Keys/Wurli' one of the third-party banks."""
    for base in (DATA / "patches_factory", DATA / "patches_3rdparty"):
        p = base / (name + ".fxp")
        if p.exists():
            return p
    raise SystemExit(f"no Surge XT sound called {name}")


def _state(patch):
    """A .fxp holds Surge's patch after a 60-byte header; a VST3 host hands it over wrapped in XML, in JUCE's own base64."""
    data = patch.read_bytes()[60:]
    bits = int.from_bytes(data, "little")
    text = f"{len(data)}." + "".join(TABLE[(bits >> (6 * i)) & 63] for i in range((len(data) * 8 + 5) // 6))
    xml = f'<?xml version="1.0" encoding="UTF-8"?> <VST3PluginState><IComponent>{text}</IComponent></VST3PluginState>'.encode()
    return b"VC2!" + struct.pack("<I", len(xml)) + xml + b"\x00"


def play(name, notes, seconds, bpm=None):
    """Stereo audio of `notes` [(midi note, velocity 1-127, start s, length s)] on the sound `name`.
    `bpm` is the tempo the synthesizer is told: sounds with a tempo-synced echo or LFO follow it (untold, it assumes 120)."""
    import dawdreamer as daw
    global _engine
    if _engine is None:
        _engine = daw.RenderEngine(SR, 256)
    global _count
    _count += 1
    _engine.set_bpm(float(bpm or 120))
    synth = _engine.make_plugin_processor(f"s{_count}", PLUGIN)
    with tempfile.NamedTemporaryFile(suffix=".bin") as f:
        f.write(_state(find(name)))
        f.flush()
        synth.load_state(f.name)
    for m, vel, start, length in notes:
        synth.add_midi_note(int(m), int(np.clip(vel, 1, 127)), float(start), float(length))
    _engine.load_graph([(synth, [])])
    _engine.render(seconds)
    return np.array(_engine.get_audio(), dtype=np.float64)


def probe(name, note=60):
    """What can be measured of a sound without hearing it: level, how fast it speaks, how long it rings after the key
    is let go (a long ring on a short note is an echo or a big reverb), how bright it is."""
    y = play(name, [(note, 96, 0.25, 1.0)], 8.0).mean(axis=0)
    env = np.sqrt(np.convolve(y ** 2, np.ones(960) / 960, "same")) + 1e-12
    pk = env.max()
    on = np.argmax(env > 0.1 * pk) / SR - 0.25
    half = np.argmax(env > 0.7 * pk) / SR - 0.25
    off = int(1.25 * SR)
    live = np.nonzero(env[off:] > pk * 10 ** (-40 / 20))[0]
    ring = (live[-1] / SR) if len(live) else 0.0
    held = env[int(1.15 * SR)] / pk
    S = np.abs(np.fft.rfft(y[int(0.25 * SR): int(1.25 * SR)])) ** 2
    fr = np.fft.rfftfreq(SR, 1 / SR)
    top = 10 * np.log10(S[fr > 4000].sum() / S.sum() + 1e-12)
    return dict(name=name, rms=float(np.sqrt((y[int(0.25 * SR): int(1.25 * SR)] ** 2).mean())), speaks_ms=round(on * 1000), full_ms=round(half * 1000),
                held=round(float(held), 2), ring_s=round(float(ring), 2), centre=int((fr * S).sum() / S.sum()), top_db=round(float(top), 1))


def timing(name, bpm, note=60):
    """Is the sound on the beat? One short note: how late it reaches half its peak, and whether it repeats itself
    (an echo), how loud, and after how many sixteenths at this tempo. An echo that is not a whole number of
    sixteenths, or a slow attack on a rhythmic part, is heard as playing off the beat."""
    y = play(name, [(note, 100, 0.5, 0.12)], 4.0, bpm).mean(axis=0)
    env = np.sqrt(np.convolve(y ** 2, np.ones(240) / 240, "same"))
    pk = env.max() + 1e-12
    late = (np.argmax(env > 0.5 * pk) - 0.5 * SR) / SR * 1000
    first = int(np.argmax(env)) 
    step = 60 / bpm / 4
    echoes = []
    k = first + int(0.07 * SR)
    while k < len(env) - 2400 and len(echoes) < 3:
        seg = env[k: k + int(1.2 * SR)]
        j = k + int(np.argmax(seg))
        before = env[max(k, j - int(0.05 * SR)): j].min() if j - k > 480 else env[j]
        if env[j] > 0.06 * pk and env[j] > 1.5 * before:           # a bump that rises again: a repeat, not the decay
            echoes.append((round(20 * np.log10(env[j] / pk), 1), round((j - first) / SR / step, 2)))
            k = j + int(0.07 * SR)
        else:
            break
    return dict(name=name, late_ms=round(float(late), 1), echoes=echoes)


if __name__ == "__main__" and sys.argv[1:2] == ["timing"]:
    for n in sys.argv[3:]:
        r = timing(n.split("@")[0], float(sys.argv[2]), int(n.split("@")[1]) if "@" in n else 60)
        print(f"{r['name']:40s} late {r['late_ms']:6.1f} ms   echoes (dB, sixteenths later): {r['echoes']}", flush=True)

if __name__ == "__main__" and sys.argv[1:2] == ["probe"]:
    for n in sys.argv[2:]:
        r = probe(*(n.split("@")[0], int(n.split("@")[1])) if "@" in n else (n,))
        print(f"{r['name']:38s} level {20 * np.log10(r['rms'] + 1e-9):6.1f} dB  speaks {r['speaks_ms']:4d} ms  full {r['full_ms']:4d} ms  held {r['held']:.2f}  rings {r['ring_s']:.2f} s  centre {r['centre']:5d} Hz  over 4k {r['top_db']:6.1f} dB", flush=True)
