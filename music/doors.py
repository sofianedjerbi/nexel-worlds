"""Six doors to choose from by ear: each an opening and a closing sound, made as the other effects are (sfx.py's
strikes, friction and noise), written to site/audio/door_<id>_open.wav and _close.wav for site/door.html.

Five doors made without hearing them were refused, each for its own fault: a slow pulse train ("a weird noise"), a
lone latch ("a clic that does not sound like a door"), two knocks ("not a toctoc"), a swing of noise grains ("still a
click"), a gliding note ("an old person moaning"). Then: "just like other sound effect, create it. do a showcase html
page in local". So not one more guess: six, as unlike each other as a door allows, and the user's ear picks.

    uv run python music/doors.py
"""
import json

import numpy as np

import sfx
from sfx import N, SR, norm, phism, place, stickslip, strike, texture, tt

OUT = sfx.OUT.parent / "audio"
LOUD = 0.55                                            # as loud as the game's door is now


def swish(c, seconds, lo=250, hi=1000, power=1.3):
    """The air a board pushes: smooth noise, swelling and dying."""
    n = N(seconds)
    return norm(texture(c, n, lo, hi, 5, 12, 0.3) * np.sin(np.pi * tt(n) / seconds) ** power)


def thunk(c, size, hard=0.8, body=0.6):
    """A big board meeting something: the knock of the wood and the board's low body under it, as one sound."""
    return strike(c, N(0.3), "wood", size=size, hard=hard) + body * strike(c, N(0.3), "plank", size=size * 1.15, hard=hard)


def clunk_open(c):
    y = np.zeros(N(0.5))
    place(y, 0.25 * strike(c, N(0.06), "metal", size=0.9, damp=3.0), 0.0)
    place(y, 0.9 * thunk(c, 1.25), 0.022)                            # 22 ms after the handle: heard as one clunk
    place(y, 0.3 * swish(c, 0.3), 0.06)
    return y


def clunk_close(c):
    y = np.zeros(N(0.6))
    place(y, 0.35 * swish(c, 0.22), 0.0)
    place(y, thunk(c, 1.45, 0.7), 0.19)
    place(y, 0.2 * strike(c, N(0.06), "metal", size=0.9, damp=3.0), 0.23)
    return y


def hinge(c, seconds):
    """An old hinge: slips you can count, quickening as the door gathers way and slowing as it stops, in dull wood."""
    n = N(seconds)
    e = np.sin(np.pi * tt(n) / seconds)
    return stickslip(c, n, 22 + 75 * e ** 2, (350, 800, 1500), 5) * e ** 0.7


def hinge_open(c):
    y = np.zeros(N(0.65))
    place(y, 0.7 * hinge(c, 0.55), 0.0)
    return y


def hinge_close(c):
    y = np.zeros(N(0.7))
    place(y, 0.6 * hinge(c, 0.36), 0.0)
    place(y, 0.9 * thunk(c, 1.4, 0.7), 0.33)
    return y


def scrape(c, seconds, up, rough=0.0, pitch=1.0):
    """Wood dragged on wood: a dry hiss whose colour moves as the door does (no note, no grains). rough: how much it
    judders, as old wood does (the hiss itself swelling 18 to 48 times a second, faster as the door moves faster:
    smooth swells, not pulses); pitch: its colour, lower under 1."""
    n = N(seconds)
    t = tt(n)
    u = t / seconds if up else 1 - t / seconds
    bell = np.sin(np.pi * t / seconds)
    low, high = norm(texture(c, n, 300 * pitch, 750 * pitch, 4, 14, 0.25)), norm(texture(c, n, 650 * pitch, 1500 * pitch, 4, 14, 0.25))
    judder = 1 - rough * 0.5 * (1 + np.cos(2 * np.pi * np.cumsum(18 + 30 * bell) / SR))
    return norm((low * (1 - u) + high * u) * bell ** 1.2 * judder)


def scrape_open(c):
    y = np.zeros(N(0.6))
    place(y, scrape(c, 0.5, True), 0.0)
    return y


def scrape_close(c):
    y = np.zeros(N(0.6))
    place(y, 0.8 * scrape(c, 0.3, False), 0.0)
    place(y, 0.7 * thunk(c, 1.3, 0.65), 0.27)
    return y


# "make it more like a door that open old door. wood on wood but faster": the third, in half the time, three ways:
# as it was; juddering as old wood does; juddering and lower.
def fast(rough, pitch):
    def opening(c):
        y = np.zeros(N(0.4))
        place(y, scrape(c, 0.27, True, rough, pitch), 0.0)
        return y

    def closing(c):
        y = np.zeros(N(0.45))
        place(y, 0.8 * scrape(c, 0.17, False, rough, pitch), 0.0)
        place(y, 0.7 * thunk(c, 1.3, 0.65), 0.15)
        return y
    return opening, closing


def knock_open(c):
    y = np.zeros(N(0.35))
    place(y, thunk(c, 0.85, 1.1, 0.4), 0.0)                          # one knock, the higher of the two
    return y


def knock_close(c):
    y = np.zeros(N(0.4))
    place(y, thunk(c, 1.25, 0.9, 0.7), 0.0)                          # one knock, lower and fuller
    return y


def heavy_open(c):
    y = np.zeros(N(0.65))
    place(y, swish(c, 0.5, 70, 260, 1.0), 0.0)                       # a big door moving: a low rumble
    place(y, 0.3 * swish(c, 0.4, 300, 900), 0.05)
    return y


def heavy_close(c):
    y = np.zeros(N(0.75))
    place(y, 0.8 * swish(c, 0.32, 70, 260, 1.0), 0.0)
    place(y, strike(c, N(0.4), "plank", size=2.0, hard=0.5) + 0.7 * strike(c, N(0.4), "wood", size=1.6, hard=0.6), 0.28)
    return y


def latch_open(c):
    y = np.zeros(N(0.45))
    place(y, 0.3 * strike(c, N(0.06), "metal", size=0.8, damp=3.0), 0.0)         # the handle, the bolt, the door let go:
    place(y, 0.45 * strike(c, N(0.1), "wood", size=0.7, hard=1.5), 0.03)         # three sounds in 75 ms, the last the biggest
    place(y, 0.9 * thunk(c, 1.15, 0.9), 0.075)
    return y


def latch_close(c):
    y = np.zeros(N(0.5))
    place(y, thunk(c, 1.45, 0.75), 0.0)
    place(y, 0.4 * strike(c, N(0.15), "wood", size=0.75, hard=1.3), 0.06)        # it shudders in its frame
    place(y, 0.25 * strike(c, N(0.06), "metal", size=0.8, damp=3.0), 0.09)       # the bolt drops
    return y


DOORS = [
    ("fast", "Wood on wood, faster", "the third below in half the time: a quarter of a second to open; closing: quicker still, then a soft thunk", *fast(0, 1)),
    ("fastold", "Faster, an old door", "the same, juddering as old dry wood does when it is forced", *fast(0.75, 1)),
    ("fastlow", "Faster, old and lower", "the same judder, lower in colour: a thicker, heavier old door", *fast(0.75, 0.7)),
    ("clunk", "Clunk and swish", "the handle and the board as one clunk, then the air; closing: the air, a full thunk, the bolt", clunk_open, clunk_close),
    ("hinge", "Old hinge", "slips you can count that quicken and slow, in dull wood; closing ends in a thunk (close to the very first door, slower and softer)", hinge_open, hinge_close),
    ("scrape", "Wood on wood", "a dry hiss of wood dragged on wood whose colour rises; closing: it falls, then a soft thunk", scrape_open, scrape_close),
    ("knock", "One knock", "a single wooden knock, higher to open, lower and fuller to close (one each: not a knock-knock)", knock_open, knock_close),
    ("heavy", "Heavy door", "a low rumble of a big door moving; closing: the rumble, then a deep thud", heavy_open, heavy_close),
    ("latch", "Latch works", "handle, bolt, door: three sounds in a blink, the last the biggest; closing: thunk, a shudder, the bolt", latch_open, latch_close),
]


def sharp(st):
    """How far the loudest 2 ms stand over the 50 ms around them, in dB (a knock: about 10; a swish: about 5)."""
    x = st.mean(axis=0)
    fast, slow = np.sqrt(np.convolve(x ** 2, np.ones(96) / 96, "same")), np.sqrt(np.convolve(x ** 2, np.ones(2400) / 2400, "same")) + 1e-9
    return round(float(20 * np.log10((fast / slow)[slow > slow.max() * 0.2].max())), 1)


if __name__ == "__main__":
    rows = []
    for key, title, what, opening, closing in DOORS:
        row = dict(id=key, title=title, what=what)
        for way, fn in (("open", opening), ("close", closing)):
            st = sfx.finish(fn(sfx.Ctx(f"door_{key}_{way}", 0)), "out")
            want = 20 * np.log10(LOUD) - 9                           # (levelled as sfx.render levels the game's sounds)
            for _ in range(6):
                st *= 10 ** ((want - sfx.loudness(st)) / 20)
                if np.abs(st).max() <= 0.95:
                    break
                st = 0.95 * np.tanh(st / 0.95)
            sfx.write_wav(OUT / f"door_{key}_{way}.wav", st)
            row[way] = dict(seconds=round(st.shape[1] / SR, 2), sharp=sharp(st))
        rows.append(row)
        print(f"{title:16s} open {row['open']}  close {row['close']}", flush=True)
    (OUT / "doors.json").write_text(json.dumps(rows, indent=1))
