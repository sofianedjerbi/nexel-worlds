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
- context matters more than polish: the game used to give 21 different placeable things one "wood knock", so a rug, a bed or a pot
  sounded like knocking on a door. Building now has one sound per object family (post, planks, stone, furniture, soft, pot, fire,
  boat, floor, path, earth); `music/sfx_map.json` says which object plays which sound, and the page has a "by object" panel to check it.

## Footsteps and ground impacts (after "cobblestone sounds like a xylophone")

Research: L. Turchet, "Footstep sounds synthesis", Applied Acoustics 107 (2016); P. Cook's PhISM (physically informed stochastic models);
A. Farnell, "Marching onwards: procedural synthetic footsteps". What they agree on, and what `sfx.py` now does:
- a step is driven by the ground reaction force: a smooth heel bump, then a smaller toe bump 60-100 ms later (`grf`).
  Soft soles mean a smooth attack. Never hit the ground with a sub-millisecond impulse: that is a mallet, and it rings like a xylophone.
- solid floors (wood, cobble): about 6 heavily damped modes driven by the force (`force_modes`), plus a white-noise burst at heel and toe,
  proportional to the force (`contact_noise`). On cobble, the noise and the grit carry the sound; the stones barely ring.
- loose ground (grass, soil, gravel, a path being laid): no resonating body; Poisson particle collisions whose rate follows the force,
  each a very short resonance (`phism`), in two or three layers for different grain sizes.
- water: the force times low-passed noise, plus bubbles at f0 = 3/r rising as they decay, radii from a power law (`bubble`).
- stones and pots rest on something that soaks the ring up: high loss factor or `damp`.
- `uv run python music/ringcheck.py` flags any realistic sound whose energy after 30 ms sits in narrow peaks (a "xylophone" score).
  It must stay near 0 for footsteps, work, breaking and building; only chimes, voices, bubbles and hinges may be tonal.

## Fable 5.2 review of the Opus 5.5 work (2026-11-11)

The Opus versions are frozen in `music/opus/` (scripts) and rendered to `music/site/opus/`. The page plays both: A/B rows for the music
(same position, 40 ms crossfade, keys A and B) and two rows per sound effect. `uv run python music/review.py` measures both sets and
writes the "What the review found" card. Tools: `music/audit.py` (latency, K-weighted loudness, rumble, variant similarity), `music/ringcheck.py`.
- Music: same notes and form. Phrased melody (velocity and lateness per note), brighter stereo piano, +4 dB air shelf,
  arpeggio fades at block edges, soft left-hand answers, louder rests.
- Sounds: 55 Hz high-pass, trimmed lead-in, K-weighted levels, real variants (resize per variant plus random parameters),
  new eat / pour / fill / punch / squawk, reworked moo, talk babble, splash, fire.
- To re-render the Opus set: `uv run python music/opus/sfx.py` and `uv run python music/opus/compose.py`.

### Second Fable pass: the generators themselves (after "you fixed the dB and the start, not the sound")
A remaster is not an improvement the user can hear. `music/sfx.py` was rewritten from scratch:
`strike()` (per-material mode structure + noisy contact + chatter; dense irregular modes so knocks do not ring like bars),
`space()` (dry outdoors with a ground reflection; rooms only where there is one), `texture()` (bands swelling independently),
rewards and UI on the soundtrack's felt piano and synth pluck. Files are stereo. Lesson: when asked to improve a sound, change what makes the sound.
- Sine pings are water. Debris (grit, chips, pebbles, soil) must be tiny NOISE bursts; short decaying sines read as drops and bubbles
  ("cobblestone and chopping sound like water"). Stone gets a crowd of very short modes, never a few.
- Deep, slow, independent band swells (texture depth > 0.6) gurgle or creak ("crumble sounds like an old door"): use them only for water and fire.

## Sounds in the game (2026-11-11)

`uv run python tools/build_audio.py` renders `music/sfx.py` into `src/megastructure/web/audio/` (32 kHz stereo WAV + `sfx.json`; not committed).
The client (`web/js/audio.js`) loads the manifest on the first gesture, warms every file in the background, and plays samples with distance
volume, left/right pan, variant rotation, light pitch spread on physical sounds, per-sound throttles and a limiter. One table (`SOUND`) holds the mix.
`music/sfx_map.json` decides what each placed block or ground sounds like; the build fails if an item has none.
`tests/test_audio.py` fails if the client asks for a sound that does not exist; `tests/e2e/test_e2e_sound.py` plays the game in Chrome.
After changing the server's Python (e.g. `web_static.py`), restart the game server: a running one keeps the old code.

## Boss fight mockup and boss sounds (2026-11-12)

`uv run python music/boss.py` renders "Old Mossback" (96 BPM, B minor, 36 bars, a 90 s loop) to `music/site/audio/boss.wav`; the page has its own player card.
It is Meadow Road's melody and instruments over a stomp (beats 1 and 3), a shell knock (2 and 4), a root ostinato in the bass and a slowly climbing low horn.
Research note: a first boss in a calm game gets its tension from the bass, the rhythm and the texture, and from weight, not from speed or chromatic notes.
`music/sfx.py` has a "Boss" family (wake, groan, stomp, snap, shake, sporeling_land, spore_puff): mockups, not played by the game yet.
- Eating was three bursts of hiss with a thud. A bite is a burst of millisecond fracture pulses, dense then thinning, bright above 2 kHz,
  heard through a mouth that closes (a resonance sliding from about 1500 to 700 Hz): `_chomp`. The first bite is crisp, the two chews duller.
- A slow pulse train (20-110 per second) through low, wide resonances sounds like a raspberry: the falling tree's creak used one. Use separate cracks instead.

## New main theme, night theme (2026-11-12)

The user disliked the main instrument in every track ("too aggressive, too high, weird"), then asked for a new main theme, after research
on iconic game themes, C418 and Undertale. What the research gave (principles, hardly any note-level analysis): the first seconds decide a
theme; one theme reused everywhere, changed by tempo, instrument and harmony rather than by new notes (Undertale); an accompaniment figure
that is itself recognisable (Undertale's overworld ostinato: a tonic-chord group and a rising 1-2-3); few chords, a rolling left hand, space (C418).
- Theme: one eight-bar line around A4-E5 over G, D/F#, Em7, A (no third), ..., D; the bass walks down. `compose.THEMES`, `THEME=b` renders a candidate.
- The night theme (`music/night.py`, "Lantern Road") and the boss fight use `compose.MELODY` note for note, over other chords, at other tempos.
- **A hook of three even notes rising to a held note, repeated every two bars, on a pure tone, is a door chime** ("the noise a pharmacy makes
  when someone enters", "a notification", "a phone call theme"). Use long-short-long rhythms, lines that fall, phrases that run over the bar.
- **A piano dulled to nearly a sine with a clean attack is a chime too.** Soft must still be a piano: two strings beating, stretched partials, a felt thump.
- **No decorative nature sounds in the music**: crickets and high plucked "fireflies" in the night theme were "very very very bad".
- The assistant cannot hear. When a melody is a guess, put a second candidate on the page so the user can choose by ear.

### The staircase (same day)
The second melody and four sketches were rejected too: "you go slowly up note by note then slowly down note by note: it makes me SICK,
sounds like pharmacy entering". That was every arpeggio (the left hand going up a chord and back, a chord rolled a note a beat) and every
melody moving by step in one direction and then back.
- **No arpeggios, no chords played a note at a time.** Chords are struck together and held.
- **The melody never takes two steps in the same direction**: repeated notes, thirds, a fifth, long holds. `compose.staircases()` checks it.
- `music/sketches.py` (four sketches) was removed; the main, night and boss tracks all use `compose.MELODY`.

### The key must be heard (same day)
"Are you really using music theory? The scale looks off." The clash checks only forbade semitones; they said nothing about function.
That version began on the IV chord, put non-chord notes (the 9th and major 7th of G) on the strong beats of bar 1, had no leading
note and no cadence, so D major was never established.
- Write a period: I V6 vi V (half cadence, melody on the leading note) then I V6 IV-V I (full cadence, melody 2 to 1).
- Every melody note that starts on a beat is a chord note (`compose.off_chord()`); the night and boss versions check the same.
- Night and boss reharmonise the same tune in the relative minor (Bm7, F#m, D, F#m / Bm7, F#m, G-A, Bm).

### It must not wander (2026-11-13)
"The theme feels like it's going anywhere, freestyling: AI-generated typically." A through-composed line with a different shape and a
leap in every bar is not a tune, however correct its harmony. Back to the discipline of the version the user called perfect:
- **One head (A, B, A: long, short, long), repeated four times exactly; only the landing note changes (F#, E, F#, D).**
- Two bars a chord (D, A/C#, Bm7, then A and D). Night and boss: Bm7, A, F#m, then A and Bm.
- When fixing one complaint, re-read all the earlier ones: this one had been made, and solved, a day before.
