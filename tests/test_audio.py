"""Sound effects stay wired: every sound the client asks for exists, every placeable thing has a sound,
and the build's own checks pass. (The audio files themselves are built by tools/build_audio.py, not committed.)"""

import importlib.util
import json
import re
from pathlib import Path

ROOT = Path(__file__).parent.parent
JS = ROOT / "src" / "nexel_worlds" / "web" / "js"

spec = importlib.util.spec_from_file_location("build_audio", ROOT / "tools" / "build_audio.py")
build_audio = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build_audio)

NAMES = build_audio.sound_names()
# strings that appear inside sfx(...) calls or the audio tables but are not sound names
NOT_SOUNDS = {"wood", "stone", "plant", "soil", "cow", "calf", "chicken", "chick", "say", "shout", "join", "leave", "a gloom",
              "n", ":", "_", "~", "default"}


def first_arg(text: str, start: int) -> str:
    """The first argument of the call whose '(' is at start."""
    depth, i = 0, start
    while i < len(text):
        c = text[i]
        if c in "([{":
            depth += 1
        elif c in ")]}":
            depth -= 1
            if depth == 0:
                break
        elif c == "," and depth == 1:
            break
        i += 1
    return text[start + 1:i]


def asked_for() -> dict[str, set[str]]:
    """Every string literal passed as a sound name anywhere in the client, by file."""
    found = {}
    for path in sorted(JS.glob("*.js")):
        text = path.read_text()
        names = set()
        for m in re.finditer(r"\bsfx\(", text):
            names |= set(re.findall(r'"([a-z_~:]+|a gloom)"', first_arg(text, m.end() - 1)))
        if path.name == "sound_of.js":    # the lookup tables: STRIKE, BREAK, STEP, VOICE, and the fallback in sfxPlaced
            for table in re.findall(r"const (?:STRIKE|BREAK|STEP|VOICE) = \{([^}]*)\}", text):
                names |= set(re.findall(r':\s*"([a-z_]+)"', table))
        if path.name == "audio.js":
            names |= set(re.findall(r"^\s*minGap: \{([^}]*)\}", text, re.M) and
                         re.findall(r"(\w+):", re.search(r"minGap: \{([^}]*)\}", text).group(1)))
        if names - NOT_SOUNDS:
            found[path.name] = names - NOT_SOUNDS
    return found


def test_the_client_only_asks_for_sounds_that_exist():
    unknown = {f: sorted(n - NAMES) for f, n in asked_for().items() if n - NAMES}
    assert not unknown, f"the client plays sounds that music/sfx.py does not define: {unknown}"


def test_the_client_plays_sounds():
    used = set().union(*asked_for().values())
    assert len(used) > 40, "the scan found too few sfx() calls: did the call sites change shape?"


def test_event_names_used_as_sounds_exist():
    assert {"say", "shout", "join", "leave"} <= NAMES          # state.js plays sfx(e.type) for these events


def test_every_placeable_thing_and_ground_has_a_sound():
    blocks, grounds = build_audio.place_maps(NAMES)            # raises SystemExit with the missing item otherwise
    from nexel_worlds import tiles as T
    assert set(blocks) == set(T.PLACEABLE.values())
    assert grounds and set(blocks.values()) | set(grounds.values()) <= NAMES


def test_the_showcase_map_only_names_real_sounds():
    table = json.loads((ROOT / "music" / "sfx_map.json").read_text())
    named = {s for section in table.values() for s in section.values()}
    assert named <= NAMES, sorted(named - NAMES)


def test_resampling_keeps_length_and_level():
    import numpy as np
    t = np.arange(48000) / 48000
    st = np.stack([np.sin(2 * np.pi * 440 * t)] * 2) * 0.5
    out = build_audio.resample(st, 48000, 32000)
    assert out.shape == (2, 32000)
    assert abs(np.abs(out).max() - 0.5) < 0.02


def test_static_server_serves_audio():
    from nexel_worlds import web_static
    assert "audio" in web_static.STATIC and web_static.CONTENT_TYPES[".wav"] == "audio/wav"
    assert web_static.CONTENT_TYPES[".flac"] == "audio/flac"   # (the music's pieces)
    assert web_static.CONTENT_TYPES[".webp"] == "image/webp"   # (the first screen's still picture of its island)
    assert web_static.CONTENT_TYPES[".json"] == "application/json"


def test_a_music_loop_is_cut_into_lossless_pieces_that_join_exactly(tmp_path):
    """The player streams the loop (audio.js): the build cuts it into pieces, the same samples as the one long file
    they replace, each with a little of its neighbours at both ends (round the loop for the first and the last)."""
    import wave

    import numpy as np
    import soundfile
    rate, n = build_audio.RATE, int(build_audio.RATE * 19.3)
    t = np.arange(n) / rate
    build_audio.write_wav(tmp_path / "master.wav", np.stack([np.sin(2 * np.pi * 220 * t) * .4, np.sin(2 * np.pi * 331 * t) * .3]), rate)
    with wave.open(str(tmp_path / "master.wav")) as w:
        whole = build_audio.pcm16((np.frombuffer(w.readframes(n), "<i2").reshape(-1, 2).T / 32768).astype(np.float64))
    m = build_audio.build_music(tmp_path, tmp_path / "master.wav", "music")
    pad = round(m["pad"] * rate)
    parts = [soundfile.read(str(tmp_path / f), dtype="int16")[0] for f in m["files"]]
    assert len(parts) == 3 and np.array_equal(np.concatenate([p[pad:-pad] for p in parts]), whole)
    assert np.array_equal(parts[0][:pad], whole[-pad:]) and np.array_equal(parts[-1][-pad:], whole[:pad])
    assert abs(m["seconds"] - n / rate) < 1e-9 and abs(m["last"] - (n / rate - 2 * m["seg"])) < 1e-9
    for secs in (m["seg"], m["pad"]):                        # whole samples at every rate a browser plays at
        assert all(abs(secs * r - round(secs * r)) < 1e-9 for r in (32000, 44100, 48000))



def test_the_adventure_piece_is_built_for_its_role_and_has_no_note_that_sounds_off():
    """Trailblazer plays by day far from home (audio.js farFromHome(), play.adventure). "Some notes sound off" (2026-11-25):
    a held major seventh on the chord's root, and a bass leading in from outside the key. Its score must keep none:
    no clash, no held seventh, nothing outside E minor, no staircase (music/adventure.py audit)."""
    import sys
    assert build_audio.TRACKS["trailblazer"] == "adventure"
    sys.path.insert(0, str(ROOT / "music"))
    try:
        import adventure
        import pieces
        assert adventure.audit(pieces.BASE | adventure.PIECES[0]) == dict(clashes=[], held_sevenths=[], outside_key=[], staircases=[])
    finally:
        sys.path.remove(str(ROOT / "music"))
