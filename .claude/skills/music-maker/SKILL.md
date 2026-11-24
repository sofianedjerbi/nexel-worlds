---
name: music-maker
description: Compose, render, master and wire background music and sound effects for Nexel Worlds the way past sessions did (Surge XT driven from Python for music, pure-numpy synthesis for SFX, local only), to the owner's recorded taste. Use when composing or changing background music, menu/boss themes or sound effects, or when the owner gives a verdict on how something sounds.
---

# Music maker (Nexel Worlds)

The full history is `music/PROCESS.md` (read the sections for the kind of piece you touch) and the owner's verdicts
are in `~/.claude/projects/-Users-sdjerbi/memory/megastructure-music.md`. `reference.md` beside this file lists the
kept set, its sounds and the dated verdicts. **You cannot hear.** Meters passing is not proof it sounds good: say so.

## Hard rules (owner's words)
- Local only, code only. **No text-to-music models** ("DONT TEXT TO MUSIC", 2026-11-13), no online audio APIs, no
  local "audio quality" model as ears (rated the hated tracks 7-8/10). "people do sounds with programming... use tools".
- Original music only: never imitate an existing game's themes. Earlier research borrowed *principles* (C418,
  Animal Crossing, Undertale, menu-theme practice), never notes.
- Never re-render, remix or replace an approved piece without the owner's yes. Process the approved file (`master.py`,
  `refit.py`); save a `keep_<name>.wav` copy before changing anything near a liked take.
- Never pick a timbre blind and never pick a sound by its name. Put several unlike candidates on the local page and
  let the owner choose by ear ("do not guess a fourth time"). Ask before downloading recordings.

## Pipeline: music (Surge XT via DawDreamer)
Surge XT is installed (`/Library/Audio/Plug-Ins/VST3/Surge XT.vst3`, patches in `/Library/Application Support/Surge XT`;
`~/Documents/Surge XT` is only the user data folder, unused). `music/surge.py` loads a factory patch by name and plays
notes offline: `play(name, notes, seconds, bpm)`, `probe(name, note)`, `timing(name, bpm)`. All Surge scripts run with:

    uv run --no-project --python 3.11 --with dawdreamer --with numpy python music/<script>.py [id ...]

1. **Score** in `music/pieces.py` (`SCORES` + `PIECES` dicts: bpm, swing, drums, bass, comp, lead/chords/pad/bass
   patch, levels) or a sibling script (`menu.py`, `slowtide.py`). Each piece renders from its own seed (repeatable),
   four at a time. Output: `music/site/audio/piece_<id>.wav`, 48 kHz 16-bit stereo, plus `pieces.json`.
2. **Check sounds** before using them: `python music/surge.py timing <bpm> "Leads/Light" ...` (rhythmic parts under
   15 ms late, no echo; pads exempt) and `probe` (octave it really speaks in, attack, decay, brightness).
3. **Check the mix by stems**: `python music/mixcheck.py` holds every part against the kept day pieces (or the
   "chill" reference = days + nights). Fix everything out of range before showing it.
4. **Master**: `uv run python music/master.py` (add the piece to `SET`): 30 Hz high-pass, lows under 170 Hz centred,
   2:1 glue ~1.5 dB (not on night), **-20 LUFS for every piece**, true peak under -1 dBFS. Writes `final_<name>.wav`.
   Corrections on approved files: `uv run --no-project --python 3.11 --with numpy python music/refit.py` -> `fixed_<name>.wav`.
5. **Into the game**: add `name: role` to `TRACKS` (and `SOURCE` if the file is not `final_<name>`) in
   `tools/build_audio.py`, then `uv run python tools/build_audio.py`. It prefers `fixed_<name>.wav`, resamples to
   32 kHz, cuts music into 8 s lossless FLAC pieces with 0.05 s of the neighbours at each end (the loop's other end
   for first/last) and writes `src/nexel_worlds/web/audio/` + `sfx.json` (git-ignored; about 30 MB in all).

Roles (`src/nexel_worlds/web/js/audio.js`, tune only the `SOUND` table): `day`/`night` = "moments" picked at random for the hour, never
the same twice running, looped `passes` times (day 6, night 4: about 3.5-4 min), 50-140 s of silence between; `boss`
loops while a fight is on (x1.4 of `music`); `menu` loops on the first screen. Pieces always arrive and recede with
volume **and** low-pass (`swell`: day 10 s, night 14 s, boss 2.5 s, menu 6 s in, 5 s out). A fade-in belongs to the
player, never in the file. Relative loudness lives in `SOUND` (music .64), not in the files.

## Pipeline: sound effects (pure numpy)
- `music/sfx.py`: one generator per sound, registered with `@sfx(name, category, when, variants, loud, tuned=...)`.
  Physical categories get size/pitch variants; `tuned=True` sounds are never resized. Render to the review folder with
  `uv run python music/sfx.py` (48 kHz WAV in `music/site/sfx/` + `sfx.json`).
- Building sounds: `music/sfx_map.json` maps each placed item (`place`) and laid ground (`ground`) to a sound; the build
  fails if a placeable item or ground has none, or a name does not exist.
- Game: `uv run python tools/build_audio.py` (FLAC, 32 kHz). Play from JS with `sfx(name, x, y)` (world) or `sfx(name)`.
- Every sound is levelled on K-weighting (loudest 100 ms, -13 dB for the boss's biggest to -30 dB for the softest step),
  55 Hz high-pass, instant start, smooth tail.
- Physical models, not guesses: footsteps from a ground-reaction-force bump (`grf`, heel then toe 60-100 ms later),
  solid floors = few damped `force_modes` + contact noise, loose ground = `phism` particle collisions, water =
  `bubble` (Minnaert), knocks = `strike()` with a per-material mode structure; outdoors dry (`space`), rooms only where
  there is one. UI/reward sounds use the music's pluck/key in D major pentatonic.
- A sound with a strong real-world identity (the door) was refused five times blind: make about six unlike
  candidates on a local page (`music/doors.py` + `site/door.html` is the pattern) and let the ear pick; the chosen
  file must be reproduced sample-exactly in `sfx.py` (own seed).

## Composition rules (each one came from a refusal)
- Rich harmony underneath (7ths, 9ths, 13ths, ii-V into chords, rootless voicings moving by step, bass entering roots
  from a semitone below) **and ONE lead cell on top**: one bar played three times, then a cadence bar; only its pitches
  move to fit the chord. Plain 4 chords + pentatonic tune = "naive, generic"; a tune whose bars differ = "going
  anywhere, freestyling, AI-generated typically". Check both before rendering.
- Establish the key: start on I, chord tones on every beat, a leading note and a cadence. No tune note a semitone or
  minor ninth above a sounding chord note (`pieces.clashes` refuses it).
- **No arpeggios, no rolled chords, no stepwise runs up then down** ("it makes me SICK, sounds like pharmacy").
  No three even notes rising to a held one on a pure tone (door chime / notification).
- A new theme = its own cell, key, meter, rhythm section and sounds. Re-dressing a cell, or swapping only the lead, is
  a variation ("kite is just the same thing... with different lead = sucks").
- Each piece its own lead and pad patch, night pieces included ("do not reuse the same instrument").
- Synths being synths: plucks, saw/PWM leads, analog polys, warm pads, drum machines. **Never** patches imitating
  acoustic instruments (flute, kalimba, conga, harp, harmonica, clarinet = "MIDI"), bells, pure tones, bare pulse waves,
  chiptune, synthesised pianos. Leads plucked (14 dB or more down after 0.7 s held); slow ballad leads = "ghosty".
- Dry and close: no echo/delay, little reverb (Surge patches bring their own). No decorative nature sounds in music.
- Humanise: velocity jitter, +4 ms +-5 ms timing (not kick/bass), note lengths 86-97 %, accents by position.
- Moods that worked: day = bright, bouncy, 108-112 BPM, claps or four-on-the-floor; night = 66 BPM, no drums, soft key
  over warm pads, long low bass; boss = 160 BPM minor, sixteenth bass riff, stabs, crashes, tom fills, lead kept low
  in the mix; menu = 104 BPM groove reaching the drums within two bars (a long thin intro "takes time to settle").
- Short, groove-led pieces with contrast between sections beat long, layered, pad-heavy "full versions".

## Seamless loops
- Every effect circular: render with a tail, fold the tail back onto the start (`pieces.render`: `y[:, :n] + y[:, n:2n]`),
  filter with FFTs over the whole loop, LFOs with whole cycles per loop, loop length rounded to a 2-3-5 size for speed.
- The loop's last bar must lead into bar 1 (it plays as the bar before it).

## QA before showing anything
1. Seam and loudness (read-only, any rendered or mastered file):

       cd music && uv run --no-project --with numpy python -c "import sys,numpy as np,master as M; x=M.read(sys.argv[1]); print('LUFS %.1f TP %.1f seam %.4f typical step %.4f'%(M.lufs(x),M.true_peak(x),np.abs(x[:,0]-x[:,-1]).max(),np.percentile(np.abs(np.diff(x,axis=1)),99.9)))" site/audio/final_old_mossback.wav

   Want -20.0 LUFS, true peak <= -1 dBFS, seam step no bigger than the typical step. Also listen-test the join on the
   page: play the last 4 s into the first 4 s.
2. `mixcheck.py` all in range; `surge.py timing` on every rhythmic sound; clash/staircase checks pass.
3. SFX: `uv run python music/ringcheck.py music/site/sfx` (xylophone score near 0 for steps, work, breaking, building),
   `uv run python music/audit.py music/site/sfx` (latency, loudness, rumble, clipping, variants),
   `uv run python music/spectro.py music/site/sfx sheet.png` (look for clicks = vertical lines, ringing lines on knocks).
4. Tests: `uv run pytest tests/test_audio.py` and `uv run pytest tests/e2e/test_e2e_sound.py -m e2e -n 0`.
   Restart the game server after changing its Python.

## Showcase (how the owner listens)
`uv run python -m http.server 8099 -d music/site`, then http://127.0.0.1:8099/ (music + SFX, "by object" panel),
`/menu.html` (menu candidates), `/door.html`. Update the existing page in place, numbered candidates, old against new
where it applies; never a new page per round. The online demo page is `tools/pages/music.html` (`tools/publish_demo.sh`).

## Pitfalls seen
- `music/site/audio/` is git-ignored: the approved takes (`piece_*`, `final_*`, `fixed_*`, `keep_*`, `menu_tide_high`)
  exist only on this Mac. Never delete or overwrite them; `master.py` rewrites every `final_*` in `SET`.
- `music/render_all.py` and `compose.py`/`night.py`/`boss.py`/`day.py`/`quality.py` are the retired numpy/sample
  pipeline (Meadow Road era); do not use them for new music.
- Many Surge patches speak an octave under the key pressed: doubles and chords end up in the bass register (mud).
- Some patches are late or echo (Dreams And Sweets 65 ms late, Come Closer echoing); one hung the synth (likely
  Kalimba Hang Drum). Screen first.
- When fixing one complaint, re-read all earlier ones: fixes kept re-breaking older rules (wandering came back three times).
- Changing loading/format is allowed only losslessly with identical samples; a lossy codec or a note change needs the owner.
- When the owner is angry about time spent, keep replies short and skip audit numbers as proof of quality.
