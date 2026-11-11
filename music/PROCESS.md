# How the music got here

The game music is rendered by `music/compose.py` (pure numpy) into `music/site/audio/`, and showcased on `music/site/index.html`
(`uv run python -m http.server 8099 -d music/site`). Sound effects come from `music/sfx.py`, in the same style.

## Iterations and what each one taught

1. **SNES-style town theme.** Rejected: the brief is not retro hardware, it is modern and cozy.
2. **Modern cute chiptune, 120 BPM, A/B/C/D sections.** Liked the production. Too much "main theme", the melody wandered, and some notes were wrong
   (borrowed chords, parts colliding in the same register, a 9th against a minor 3rd).
3. **Chill ambient, 80 BPM, one key, one progression, a repeated motif.** Better. Still busy, and the main instrument still wandered.
4. **60 BPM, ten-note theme, phasing layers (8/12/16 bars), no drums.** Calm enough, but not recognisable, and a bit sleepy.
5. **A rising-fifth hook and an ostinato, at 64 then 75 BPM.** Recognisable, but the reverb and pad felt "enveloping, sleepy". Bringing the theme in from bar 1 helped.
6. **"Meadow Road" with an adventurous climb-and-fall hook, distinct timbres and a chip square.** The user disliked the chip, and the result sounded naive.
7. **4.8 min, A/B form, flute, piano, guitar, strings.** The melody "went anywhere again", still naive.
8. **Research on C418's approach** (Red Bull Music Academy and Vice interviews, Wikipedia on Volume Alpha):
   music that "doesn't explain anything", ambient roots (Aphex Twin), about 80% electronic, piano recorded through a poor mic and
   heavily processed, few chords on a pad, a simple melody that resolves and loops back, and silence.
   **Current version:** three chords (D, G, Bm, G), two bars each; one melody of two 2-bar cells in a fifth, repeated exactly;
   variation only from instrument and presence; lo-fi felt piano, an analog pad with a slowly breathing filter,
   Moog-style bass, a soft echoing synth arpeggio and a glide lead; 72 BPM; a 293 s seamless loop.

## Rules that stuck

- One key. Few chords. The melody is a small cell, repeated exactly. Never add new melodic material to create variety; vary the texture.
- Every part owns a register (bass < chords/pad/arpeggio < melody). The scripts check registers and clashes (minor 9ths, off-chord semitones/tritones).
- Each instrument comes from a different timbre family. Avoid toy sounds (chip, ocarina, glockenspiel) and orchestral cuteness (marches).
- No drums, or almost none. Moderate reverb: too much reads as sleepy.
- Bring the theme in from bar 1. Leave rests where the melody sits out.
- Measure loudness per section and per stem; fix balance from numbers, then by ear.
- Everything circular (FFT reverb and echo, LFOs with whole cycles per loop), so the loop is seamless.

## Sound effects review (how to check them without trusting your ears alone)

`uv run python music/spectro.py music/site/sfx sheet.png` draws a spectrogram per sound. What to look for:
- thin vertical lines in the middle of a sound = a click (a tail cut mid-decay). Every component now ends on a smooth tail.
- 2-3 clean horizontal lines ringing for 0.3 s on a knock = it sounds like a xylophone, not wood or stone.
  Impacts use modal synthesis instead: a short noise contact exciting ~30 resonances, each decaying as tau = 1/(pi f eta),
  with a per-material loss factor and a contact brightness (dirt and flesh dull, stone and metal bright).
- long sine sweeps under a thump = a drum-machine kick, not a body or a log. Use damped "body" and "dirt" materials.
- animal voices need pitch jitter and amplitude shimmer; perfectly steady harmonics sound synthetic.
