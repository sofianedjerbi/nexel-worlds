"""A chiptune set of instruments: the same scores, played on sound-chip voices (MUSIC_STYLE=chip, see compose.py).
The user, after the recorded instruments: "still sounds a bit midi cheap like.. how about chiptune ? ... imagine a
modern chiptune concept".

What is from the old chips: pulse waves at the NES duty cycles (12.5, 25, 50 %), the NES triangle with its 16 steps,
a Game Boy style 32-step wave channel, shift-register noise for percussion, a kick made of a triangle falling in
pitch, a two-operator FM bell (Mega Drive).
What is modern: no limit on the number of channels, so chords are real chords (no fast arpeggios: the user refuses
arpeggios), every wave is band-limited (no aliasing whine), duty cycles move while a note sounds, vibrato comes in
late on held notes, the top is rolled off, and the mix keeps its room and its stereo.
One lead voice per track, as before. Every voice is called like the others: (f, dur, vel, t0)."""
import numpy as np

SR = 48000
TOP = 11000                     # no harmonic above this
rng = np.random.default_rng(8)


def _t(n):
    return np.arange(n) / SR


def _phase(f, n, vib=0.0, rate=5.6, after=0.28, slide=0.0):
    """Phase of a note; vibrato of `vib` semitones that comes in after `after` s; `slide` semitones below at the start."""
    t = _t(n)
    semis = vib * np.clip((t - after) / 0.25, 0, 1) * np.sin(2 * np.pi * rate * t) - slide * np.exp(-t / 0.035)
    return 2 * np.pi * np.cumsum(f * 2 ** (semis / 12)) / SR


def _saw(ph, f, roll=None):
    k = np.arange(1, max(2, int(min(TOP / f, 60)) + 1))
    amp = 1 / k if roll is None else 1 / k / (1 + (k * f / roll) ** 2)
    return (2 / np.pi) * sum(a * np.sin(j * ph) for j, a in zip(k, amp))


def pulse(ph, f, duty, roll=None):
    """Band-limited pulse wave: two saws, one delayed by the duty cycle (which may move over the note)."""
    return _saw(ph, f, roll) - _saw(ph - 2 * np.pi * duty, f, roll)


def table(ph, f, steps, roll=None):
    """A wave channel: `steps` are the held values of one period (the NES triangle, a Game Boy wave). The steps
    themselves are what gives these channels their grain; it is kept, but nothing above TOP."""
    n = len(steps)
    spec = np.fft.rfft(np.asarray(steps, float) - np.mean(steps)) / n * 2
    out = 0.0
    for k in range(1, max(2, int(min(TOP / f, 96)) + 1)):
        c = spec[k % n] if k % n <= n // 2 else np.conj(spec[n - k % n])
        c = c * np.sinc(k / n)
        if roll is not None:
            c = c / (1 + (k * f / roll) ** 2)
        if abs(c) > 1e-5:
            out = out + c.real * np.cos(k * ph) - c.imag * np.sin(k * ph)
    return out


TRI = [(15 - i if i < 16 else i - 16) / 7.5 - 1 for i in range(32)]
WAVE_SOFT = np.round(7.5 + 7.5 * (0.8 * np.sin(2 * np.pi * np.arange(32) / 32) + 0.25 * np.sin(4 * np.pi * np.arange(32) / 32))) / 7.5 - 1
WAVE_REED = np.round(7.5 + 7.5 * np.clip(1.4 * np.sin(2 * np.pi * np.arange(32) / 32) + 0.5 * np.sin(6 * np.pi * np.arange(32) / 32), -1, 1)) / 7.5 - 1


def noise(n, rate, short=False):
    """The NES noise channel: a 15-bit shift register clocked `rate` times a second, each value held."""
    m = int(n * rate / SR) + 2
    reg, bits, tap = int(rng.integers(1, 1 << 15)), np.empty(m), 6 if short else 1
    for i in range(m):
        reg = (reg >> 1) | (((reg ^ (reg >> tap)) & 1) << 14)
        bits[i] = (reg & 1) * 2.0 - 1
    return bits[(np.arange(n) * rate / SR).astype(int)]


def _env(n, dur, attack, decay, sustain, release):
    t = _t(n)
    e = np.clip(t / attack, 0, 1) * (sustain + (1 - sustain) * np.exp(-t / decay))
    return e * np.where(t > dur, np.exp(-(t - dur) / release), 1.0)


def _n(dur, release):
    return int((dur + 7 * release) * SR)


# ------------------------------------------------------------------ leads, one per track

def nylon(f, dur, vel, t0):
    """Meadow Road's lead: a 25 % pulse that opens to 50 % as the note rings, plucked, vibrato late."""
    n = _n(dur, 0.09)
    duty = 0.25 + 0.2 * (1 - np.exp(-_t(n) / 0.5))
    return 0.2 * vel * pulse(_phase(f, n, 0.12), f, duty, roll=5200) * _env(n, dur, 0.004, 0.45, 0.5, 0.09)


def vibes(f, dur, vel, t0):
    """The night's lead: a two-operator FM bell, the modulator dying fast so the note ends as a pure tone."""
    n = _n(dur, 0.45)
    t = _t(n)
    ph = _phase(f, n)
    y = np.sin(ph + (0.5 + 1.1 * vel) * np.exp(-t / 0.22) * np.sin(4 * ph))
    return 0.3 * vel * y * np.clip(t / 0.004, 0, 1) * np.exp(-t / 1.3) * np.where(t > dur, np.exp(-(t - dur) / 0.45), 1.0)


def glide_lead(f, dur, vel, t0):
    """The boss's lead: a pulse whose width never stops moving (the C64 sound), sliding up into each note."""
    n = _n(dur, 0.1)
    duty = 0.3 + 0.17 * np.sin(2 * np.pi * 0.9 * (t0 + _t(n)))
    return 0.2 * vel * pulse(_phase(f, n, 0.15, slide=0.6), f, duty, roll=3800) * _env(n, dur, 0.012, 0.6, 0.75, 0.1)


def marimba(f, dur, vel, t0):
    """Market Morning's lead: a square wave struck and gone, with the octave above for the first instant."""
    n = _n(min(dur, 0.5), 0.08)
    t = _t(n)
    ph = _phase(f, n)
    y = pulse(ph, f, 0.5, roll=4500) + 0.5 * pulse(2 * ph, 2 * f, 0.5, roll=4500) * np.exp(-t / 0.018)
    return 0.22 * vel * y * np.clip(t / 0.003, 0, 1) * np.exp(-t / 0.2) * np.where(t > dur, np.exp(-(t - dur) / 0.08), 1.0)


def rhodes(f, dur, vel, t0):
    """Slow Afternoon's lead: a Game Boy wave channel, round, with a soft bell on the attack."""
    n = _n(dur, 0.18)
    t = _t(n)
    ph = _phase(f, n, 0.08)
    y = table(ph, f, WAVE_SOFT, roll=5000) + 0.25 * np.sin(3 * ph) * np.exp(-t / 0.08)
    return 0.3 * vel * y * _env(n, dur, 0.005, 0.7, 0.45, 0.18)


def clarinet(f, dur, vel, t0):
    """Overcast's lead: a 50 % square (only odd harmonics, like the clarinet), soft-edged, held, vibrato late."""
    n = _n(dur, 0.08)
    return 0.2 * vel * pulse(_phase(f, n, 0.14, 5.2), f, 0.5, roll=2600) * _env(n, dur, 0.03, 0.5, 0.8, 0.08)


def melodica(f, dur, vel, t0):
    """Picnic's lead: the thin 12.5 % pulse, reedy, held."""
    n = _n(dur, 0.07)
    duty = 0.125 + 0.05 * np.exp(-_t(n) / 0.06)
    return 0.2 * vel * pulse(_phase(f, n, 0.1, 6.0), f, duty, roll=3600) * _env(n, dur, 0.012, 0.4, 0.8, 0.07)


# ------------------------------------------------------------------ the band

def flute(f, dur, vel, t0):
    """The second voice: the NES triangle, high, where its steps give it a little breath."""
    n = _n(dur, 0.09)
    return 0.42 * vel * table(_phase(f, n, 0.12, 5.4), f, TRI) * _env(n, dur, 0.025, 0.5, 0.85, 0.09)


def epiano(f, dur, vel, t0):
    """The chords: the wave channel, short and soft, all the notes of the chord together."""
    n = _n(dur, 0.12)
    return 0.3 * vel * table(_phase(f, n), f, WAVE_SOFT, roll=3000) * _env(n, dur, 0.004, 0.35, 0.25, 0.12)


def analog_pad(f, dur, vel, t0):
    """The pad: two squares a few cents apart with the top taken off, slow to arrive."""
    n = _n(dur, 0.6)
    t = _t(n)
    y = sum(pulse(_phase(f * 2 ** (c / 1200), n), f, 0.5, roll=900) for c in (-6, 6))
    return 0.06 * vel * y * np.clip(t / 1.2, 0, 1) ** 2 * np.where(t > dur, np.exp(-(t - dur) / 0.6), 1.0)


def moog_bass(f, dur, vel, t0):
    """The bass: the NES triangle. No volume control on the real chip, so it is simply on, then off."""
    n = _n(dur, 0.05)
    return 0.6 * vel * table(_phase(f, n), f, TRI, roll=2500) * _env(n, dur, 0.004, 0.5, 0.85, 0.05)


upright = moog_bass


def shaker(f, dur, vel, t0):
    """A hi-hat: a short breath of shift-register noise."""
    n = int(0.12 * SR)
    t = _t(n)
    return 0.1 * vel * noise(n, 9000) * np.clip(t / 0.002, 0, 1) * np.exp(-t / 0.022)


def woodblock(f, dur, vel, t0):
    """A blip: a square that drops a fourth in 20 ms."""
    n = int(0.25 * SR)
    t = _t(n)
    ph = 2 * np.pi * np.cumsum(660 * 2 ** (5 / 12 * np.exp(-t / 0.012))) / SR
    return 0.14 * vel * pulse(ph, 900, 0.5, roll=4000) * np.clip(t / 0.001, 0, 1) * np.exp(-t / 0.03)


# ------------------------------------------------------------------ the boss's own

def stomp(f, dur, vel, t0):
    """The kick the old way: the triangle falling two octaves in a twentieth of a second, a grain of noise on top."""
    n = int(0.5 * SR)
    t = _t(n)
    fr = 70 + 150 * np.exp(-t / 0.03)             # (ending at 52 Hz put the boss track's sub-bass 10 dB too high)
    y = table(2 * np.pi * np.cumsum(fr) / SR, 110, TRI, roll=900) * np.exp(-t / 0.11) + 0.25 * noise(n, 1500) * np.exp(-t / 0.02)
    return 0.8 * vel * y * np.clip(t / 0.002, 0, 1)


def knock(f, dur, vel, t0):
    """The snare: low-clocked noise over a short triangle."""
    n = int(0.25 * SR)
    t = _t(n)
    y = noise(n, 5200) * np.exp(-t / 0.05) + 0.6 * table(2 * np.pi * 185 * t, 185, TRI) * np.exp(-t / 0.03)
    return 0.3 * vel * y * np.clip(t / 0.001, 0, 1)


def pizz(f, dur, vel, t0):
    """Plucked strings: the thin pulse, very short."""
    n = int(0.6 * SR)
    t = _t(n)
    return 0.22 * vel * pulse(_phase(f, n), f, 0.125, roll=3500) * np.clip(t / 0.002, 0, 1) * np.exp(-t / 0.11)


def horn(f, dur, vel, t0):
    """The low call: the reedy wave channel, swelling."""
    n = _n(dur, 0.3)
    t = _t(n)
    swell = 0.6 + 0.4 * np.sin(np.pi * np.clip(t / dur, 0, 1))
    return 0.3 * vel * swell * table(_phase(f, n, 0.1, 4.6, after=0.6), f, WAVE_REED, roll=1400) * _env(n, dur, 0.15, 1.0, 1.0, 0.3)


_kept = {}
STEADY = ("nylon", "marimba", "rhodes", "clarinet", "melodica", "flute", "epiano", "analog_pad", "moog_bass", "upright", "woodblock", "pizz", "horn")


def voice(name, gain=1.0):
    """The voice, at its level. Where velocity only sets the volume the note is made once and kept: the same few
    notes come back hundreds of times, and making each again took most of a four-minute render."""
    fn = globals()[name]

    def play(f, dur, vel, t0):
        if name not in STEADY:
            return gain * fn(f, dur, vel, t0)
        key = (name, round(f, 2), round(dur, 4))
        if key not in _kept:
            _kept[key] = fn(f, dur, 1.0, 0.0)
        return gain * vel * _kept[key]
    return play


# Each voice against the recorded one it stands in for (same note, same loudness): filled in by measuring.
LEVEL = {"nylon": 1.08, "rhodes": 1.21, "marimba": 2.45, "analog_pad": 0.56, "moog_bass": 0.66, "epiano": 0.75, "shaker": 1.21,
         "melodica": 1.35, "clarinet": 1.29, "flute": 1.2, "vibes": 1.95, "upright": 0.53, "woodblock": 1.44, "glide_lead": 1.2,
         "boss_stomp": 1.32, "boss_knock": 0.86, "boss_shaker": 1.45, "boss_pizz": 3.35, "boss_horn": 0.79}
