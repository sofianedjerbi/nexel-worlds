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

### More Animal Crossing (2026-11-13)
The user asked to take more from Animal Crossing. That music (Totaka's hourly themes) is bossa nova and lounge: seventh chords, electric
piano, light drums and bass, "electronic but played as if acoustic". Taken: a light swing (`SWING` 0.58), 84 BPM, a bass bouncing root to
fifth, an electric piano playing the whole chord short and off the beat, a shaker, diatonic seventh chords one a bar
(Dmaj7, Bm7, F#m7, Em7-A7 / Dmaj7, Bm7, A7sus, D6), landings an eighth early. The pad is nearly gone. The theme is the same head and landings.
This drops the old "no drums" rule on purpose; the night theme stays without the band.
- "The sound seems lost in a puddle of echoes everywhere and reverb too much": no echo on anything, reverb level 0.7 -> 0.22, the room's
  tail 5 s -> 2 s (decay 0.65 s -> 0.28 s); night and boss cut the same way. Keep it dry: this style is close and clear.

### Rendering fast (2026-11-13)
The user: "you're taking too much time on this process", then "keep the full rendering, just make it faster". A profile showed where the
3 minutes went: the pad re-synthesising the same few notes 297 times (now cached per pitch), whole-loop FFTs on a length with a big prime
factor (`fast_len`: the loop is rounded to a 2-3-5 length), and stems rendered one after another (now one process each).
`uv run python music/render_all.py` renders day, night and boss at once and rebuilds the game's audio: about 40 s instead of about 5 minutes.

## 2026-11-13: the piano is out

Verdict on the Animal Crossing version: "shaker is a bit too loud and the main theme instrument sound is unbearable".
Measured, the felt piano was nearly a sine (second harmonic 11 dB down, nothing above 1.5 kHz), with two strings beating
slowly and a clipper on top. Three pianos refused in a row: stop making pianos.

- The melody is now on `nylon` (a nylon guitar: one string as its modes, bright at the pluck then round, a wooden body).
  `MAIN` in `compose.py` names the melody instrument; night and boss use it too.
- Shaker 5 dB lower.
- `music/audition.py` renders the same 8 bars with each candidate (guitar, electric piano, marimba, the old piano) for
  the page's "pick by ear" card. The user picks; do not guess a fourth time.

## 2026-11-13: other music for the day

The user asked for other day musics as suggestions, published with the demo. `music/day.py` holds four (Market Morning,
Slow Afternoon, Overcast, Picnic): same band and rules as Meadow Road, each one two-bar idea said, answered, said again
and closed. None is in the game. The demo build makes `music.html` from the rendered tracks (AAC, `tools/build_pages.py`).

## 2026-11-13: one lead per track, and a measured audit

The user: "do not reuse the same instrument", then an audit of all the music against theory, Animal Crossing practice,
each instrument's tone, the volume and the effects, with research, shown on the GitHub Pages music page.

- Leads, one each: Meadow Road nylon guitar, Lantern Road vibraphone, Old Mossback synth voice, Market Morning marimba,
  Slow Afternoon electric piano, Overcast clarinet, Picnic melodica. New instruments in `compose.py`: melodica,
  clarinet, flute, vibraphone, double bass, woodblock. The refused piano and the audition clips are gone.
- `music/quality.py` is the audit (about a minute). It renders every track and writes `site/audio/quality.json`, which
  both pages show. The first run found 26 failures; all are fixed:
  notes cut off 19 to 23 dB down on the synth lead, the bass and the pad (a tick each); the tune 5 to 9 dB under the
  band in four tracks; a parallel octave between tune and bass (Overcast); a leading note left hanging (Picnic);
  three-note chord outlines in two melodies; tritone leaps in two; too much sub-bass and seven voices in the boss
  track; lows panned apart; a shaker centred at 11 kHz; `tanh` clipping on three masters; a reverb that took 1.9 s to
  die (now 1.0 s, 20 ms pre-delay, kept between 250 Hz and 8 kHz, bass dry).
- Every track now goes through `C.room()` and `C.master()` (loudness in LUFS, limiter under -1 dBFS, lows centred).
  The day pieces set each part's level against the lead automatically (`BALANCE` in `day.py`).
- Two things the audit reports but does not fail: the top note returns with the repeated idea (no single high point),
  and the last bar rests on the tonic without a turnaround.

Sources: melody rules https://musictheory.pugetsound.edu/mt21c/RulesOfMelody.html ; Animal Crossing practice
https://gameplay.co/animal-crossing-music-new-horizons-scruffy-youtube/ and https://splice.com/blog/animal-crossing-pocket-camp-music-analysis ;
cozy game music https://www.orchestraltools.com/tips-for-cozy-game-music ; reverb
https://www.izotope.com/en/learn/essential-tips-for-mixing-reverb.html and https://www.soundonsound.com/techniques/sympathetic-mixing-how-set-good-mix ;
loudness https://blog.audiokinetic.com/loudness-processing-best-practices-series-chapter1-loudness-measurement-part2 and
https://designingsound.org/2013/02/20/different-loudness-ranges-for-console-and-mobile-games ; low interval limits
https://www.sweetwater.com/insync/low-interval-limit/


## Recorded instruments (2026-11-13)

The user: "Instruments sounds like Midi default windows sample.. so ugly". Every instrument was synthesised from sines
and filtered saws; no amount of tuning made that sound like an instrument.

- Every instrument is now a recording of a real one, from public-domain (CC0) libraries: VCSL and VSCO 2 Community
  Edition by Versilian Studios, and the FreePats Spanish classical guitar. `music/fetch_samples.py` downloads them
  (about 600 MB, into `music/samples/`, not committed); `music/sampler.py` builds a cache and plays them.
- Who plays what: nylon guitar (Meadow Road), vibraphone (night), oboe (boss, was the synth voice), marimba, concert
  harp (was the electric piano: a recorded 1980s synth piano was tried and dropped as the likeliest to still sound
  "MIDI"), clarinet, harmonica (was the melodica), flute, plucked double bass (both basses), violas and cellos (the
  pad), a real shaker and woodblock. Boss: concert bass drum for the stomps, plucked cellos, French horn.
- The sampler takes the nearest recorded pitch (3 semitones away at most in the current scores) and the dynamic layer
  for the velocity, corrects each recording's own tuning, and loops held notes inside their steady part. File names
  count octaves differently per library, so the octave is read from the sound.
- Each recording is set to the loudness its synthesised version had (`LEVEL` in `compose.py`), so the mixes moved little.
  The audit then asked for: the harmonica and the shaker darker (`EQ` in `sampler.py`), the night band up 2 to 4 dB.
  Final audit: 0 failures.
- Not judged by ear. Still synthesised on purpose: the tape hiss, the night air, and all sound effects (`sfx.py`).

## Chiptune set: rejected and removed (2026-11-13)

A chiptune set of all seven tracks (pulse leads, FM bell, triangle bass, noise drums) was tried and removed the same
day. The user: "that chiptune is awful", the main instrument and "the noise of each instrument" were hated; the night
track (FM bell) and Market Morning (struck square) were "pharmacy", the boss "sounds like those MIDI samples".
Lesson: bells, pure tones and bare pulse waves all read as "pharmacy" here. And three sets of instruments chosen
without hearing them (synthesised, recorded, chip) have all been refused: stop choosing timbres blind.

## A real synthesizer, driven from Python (2026-11-13)

The user rejected every sound so far (the recorded harp, harmonica and clarinet by name), refused text-to-music
models ("DONT TEXT TO MUSIC"), and asked for music generated from code with real tools: "people do sounds with
programming... use tools". They want everything rethought: "the rhythm, the sounds themselves, that tone".

- `music/surge.py` plays Surge XT (open-source synthesizer, installed by the user with `brew install --cask surge-xt`)
  through DawDreamer, offline. It loads any of the ~3000 factory sounds by name and sends notes. I no longer design
  instruments. Run with: `uv run --no-project --python 3.11 --with dawdreamer --with numpy python music/directions.py`.
- `music/directions.py`: five 8-bar loops in five directions (lo-fi tape keys, ambient pads, mellow synthwave, electric
  piano funk, bright plucks), each with its own rhythm; none uses the old shuffle. Shown first on both pages.
  The point is to learn which direction is worth a full track before writing one.
- My own diagnosis of the "tone": the old mixes had almost nothing above 4 kHz (-20 to -35 dB) because the audit
  called anything brighter harsh. That rule is not applied here.
- Dead ends this evening: a local text-to-music model (stopped at the user's word, deleted); a local audio-quality
  model as a stand-in for ears (it rated the hated tracks 7 to 8 out of 10: useless).
- Not judged by ear.

## Bright plucks, designed further (2026-11-13)

The user on the five directions: "Dream plucks is better but it isn't ... worth continuing. do more research on surge
xt and more design."

- Research: every Surge XT control is reachable from Python by name (2855 parameters: macros, filters, envelopes, the
  16 effect slots), so sounds can be adjusted and automated, not only picked. The sound they found better (Nick
  Moritz's Dream Plucks) carries its designer's own reverb, EQ, delay and drive. On programmed music sounding
  programmed: one velocity, one note length and exact timing are the giveaways; fix with accents by position, varied
  lengths, small timing offsets, automation, and room for the lead.
- `music/bright.py`: one 24-bar piece (intro, A, B, A) at 104 BPM in G, with fills, an answering second sound, bass
  an octave higher (audible on small speakers), sidechain ducking under the kick; rendered on three palettes
  (Dream, Cute, Sweets) to separate the sounds from the writing. About 10 minutes to render (33 synth parts).
- Not judged by ear.

Sources: https://surge-synthesizer.github.io/manual-xt/ ; https://www.kvraudio.com/forum/viewtopic.php?p=8899142 ;
https://www.rogerlinndesign.com/support/ls-surge ; https://www.musicradar.com/tuition/tech/how-to-humanise-your-music-in-a-daw-632072 ;
https://unison.audio/how-to-humanize-midi/

## Richer writing (2026-11-13)

The user on bright.py: "instruments are a bit better but it still sounds too naive, too.. generic."
My reading: the sounds are now acceptable enough that the writing shows. bright.py used G, D, Em, C (the commonest
loop there is), a pentatonic tune landing only on chord notes, and one bar shape repeated.

- `music/pieces.py`: two pieces on the Bright A sounds.
  Side street: 4/4, 96 BPM, F major; Fmaj9, Em7b5-A7b9, Dm9, Cm7-F13, Bbmaj9, Bbm6, Am7-D9, Gm9-C13; rootless
  voicings moving by step; the tune uses C#, Eb, Db, F# as those chords bring them, starts off the beat, bars of a
  phrase differ; the bass enters each root from a semitone below; comping changes bar to bar.
  Paper boats: a waltz, 132 BPM, D major; E over D (Lydian), F#7 and B7 (borrowed dominants), Gm6 (minor iv); long
  tune notes on colour notes (G#, A#, D#); second time through a pluck doubles the tune an octave up.
- A check refuses tune notes a minor ninth above any note of their chord (several were caught and fixed by thinning
  voicings). This is the old "wrong notes" guard, needed again because the harmony is chromatic.
- Not judged by ear.

## Side street, second version: the lead as one cell (2026-11-13)

The user on pieces.py: "now it sounds like a single thing going anywhere. You're doing the same error again and again.
The lead is doing bullshit." It was their oldest complaint (wandering, "freestyling") come back: making the harmony
richer, I had also given every bar of the tune a different shape.
- The lead is now one cell (steps 2, 4, 6, 12: two short notes up into a long one, then a fall) played in every bar,
  only its pitches moved to fit the chord; the fourth bar of each phrase is a cadence (three notes down to a held one).
  Eight bars, played twice exactly, the last bar going home. Harmony, bass, drums and sounds unchanged.
- Paper boats (the waltz) is removed: same fault.
- Rule for every later tune: rich harmony below, ONE repeated cell above. Plain harmony plus a simple tune was
  "naive, generic"; a tune that changes shape was "going anywhere".

## Side street, eight ways (2026-11-13)

The user on the one-cell version of Side street: "good. now make it cuter or sweeter, animal-crossing feeling or
minecraft feeling. many propositions". First "good" since the C418 round.
- `music/pieces.py` now renders one score in a manner given by a dict (tempo, swing, drums full / light / bossa /
  brush / none, bass walk / bounce / long, chords comp / stab / hold, sounds). Lead cell and chords never change.
- Nine files: the reference, Cuter 1 and 2, Sweeter 1 and 2, Animal Crossing feeling 1 (day: swing, congas, clicks,
  no kit) and 2 (evening: kalimba over electric piano, brushes), Minecraft feeling 1 and 2 (slow, no drums, pads).
  Four render at a time (about 3 minutes for all).
- Not judged by ear. Unknown to me: how the kalimba, Moon Piano, Cute and conga sounds really sound.

## Kept pieces; boss and a second tune (2026-11-13)

The user: "cuter 1 = amazing, really boosty, beautiful-day thingy. really like it. minecraft feeling 1 = very nice
night song. keep those two for random day / night moments. now start to rework on the boss theme and other musics".
- Kept, files untouched since they heard them: `piece_cute1.wav` (day) and `piece_mc1.wav` (night). The other six
  manners are deleted.
- `pieces.py` now holds several scores (`SCORES`): street, boss, kite.
- Old Mossback (boss): the day's lead cell in D minor, 32 bars A A B A. A: bass walking down under D minor
  (D, C, B, Bb), then Gm9, Em7b5-A7b9, Dm9, A7#5. B: eight bars in the major (Bb, C9, Am7, Dm9), ending on A7b9.
  Drums "boss" (kick on 1 and 3, a push before 4, sixteenth hats, claps, a fill every eight bars), bass in driving
  eighths with the octave on the off-beats, chord stabs. Two versions: on the day piece's sounds at 132 BPM; heavier
  at 140 (Jupiter-8 stabs, TNMG kick and snare, Dream Plucks lead with a soft brass an octave below).
- Kite weather: a second tune, A major from the IV (Dmaj9, C#m7, Bm9, E13 ... Amaj9), its own cell (two notes down
  onto a long one, a pickup into the next bar); rendered in the kept day manner and the kept night manner.
- Not judged by ear. Not in the game yet: the game should play day and night pieces at random moments, not loop them.

## Three themes; the boss gets its own (2026-11-13)

The user on the boss built from the day's cell: "the old mossback theme looks too much like the main theme. i believe
we should create 2-3 themes for this game".
- Theme 1, Side street: the kept day and night pieces. Theme 2, Old Mossback: its own tune. Theme 3: Kite weather is
  the candidate (not yet judged).
- Two boss candidates in `pieces.py`, both 32 bars A A B A, sharing nothing with Side street:
  Stomp: E minor, the Phrygian chord (F over... Fadd9) a semitone above home, D9, Am9, C6, F#m7b5-B7b9; cell of two
  hammered notes on the beat, a long one, two pickups; 116 BPM; low brass lead, Jupiter-8 stabs, TNMG kick and snare.
  Chase: G minor (Gm9, Ebmaj7, D7b9, Bbmaj9, Am7b5; B section Cm9, F9); cell of a long note then three quick ones
  around it; 150 BPM; kick on every beat with open hats between; Dreams And Sweets lead, 808-style drums.
- The first boss versions (boss1, boss2) are deleted.
- Lesson: a theme is its own cell, key and rhythm. Re-dressing one cell in another mode is a variation, not a theme.

## Boss and third theme, second attempt; a timing check (2026-11-13)

The user: "Chase B sounds off-rythm. Mossback A sounds boring. not a boss. kite is just the same thing as the 2 theme
we kept but with different lead = sucks. change instruments etc".
- Off-rhythm, measured: `surge.timing(name, bpm)` plays one short note and reports how late the sound reaches half its
  peak and whether it echoes. Chase's lead (Dreams And Sweets) was 65 ms late (a sixteenth at 150 BPM is 100 ms) and
  its chord sound (Come Closer) echoed at -7 dB between the beats. The kept day piece's lead and drums are within
  1 ms. Rule: every rhythmic sound under 15 ms late and without echo; pads exempt. The synth is now told the tempo
  (`sync`), so tempo-synced effects follow it. One patch hung the synth during screening (probably Kalimba Hang Drum).
- Old Mossback, third version (score "mossback"): 160 BPM, C minor, intro 4 bars then A A B A; sixteenth-note bass
  riff with octave pops in 3+3+2; a held synth lead (Classic Lead 2, or Light), three notes a bar, phrases ending on
  the leading note; crashes, tom fills, chord stabs; a second lead an octave below from the middle. Two sound sets.
- Lantern fish, third theme (score "lantern"): 6/8 at 90, D Dorian, no kit (congas, shaker, clicks), Cyber Flute
  lead, kalimba chords as short hits and doubling the tune the second time, fingered bass root-fifth, warm pad.
  The engine now takes any bar length (`spb`).
- Stomp, Chase and Kite weather are deleted. A theme differs in meter, rhythm section and instruments, not in lead.
- Not judged by ear; timing is measured.

## Boss kept; third theme again (2026-11-13)

The user: "lantern fish sounds like those ugly midi songs. bad. Old Mossback (boss, new) 2: brighter lead = amazing
!!! but the lead is a bit.. freestyling".
- Boss: mossback2 is kept (Light lead, Anthemish 1 stabs, Bass 3 riff, TNMG kick and snare, 160 BPM). Its lead now
  plays one bar three times and then a cadence, in every phrase (A: Eb5 D5 G4 x3, then D5 B4; B: G5 F5 C5 x3, then
  a cadence); before, five bars of eight differed. Nothing else changed. The first render is saved beside it as
  `keep_mossback2_first.wav` (not published). mossback1 is deleted.
- Lesson on sound: a flute-like synth, a kalimba and congas are synths imitating acoustic instruments, and that is
  what the user hears as MIDI. The three things they liked are synths being synths (Cute plucks; a soft key and
  pads; a bright saw lead with analog stabs). No imitation instruments from now on.
- Third theme, two candidates on synth sounds: "lantern" (same 6/8 score: Fluff lead, Oberheim Dreams held chords,
  Juno-60 Strings pad, drum machine) and "shore" (Far shore: 112 BPM, four-on-the-floor, A major from the IV with
  E over D; one lead bar, E5 C#5 B4 C#5, that fits all seven chords, so the tune stays while the harmony moves).
- Not judged by ear.
