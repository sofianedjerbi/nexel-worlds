# Music maker: reference

## The set in the game (approved by ear; never re-render)
| game name | source take | role | what it is |
|---|---|---|---|
| side_street_day | piece_cute1 (fixed_) | day | F major jazz chords, 108 BPM, lead A.Liv/Plucks/Cute 1, chords Cute 2, bass Nick Moritz Plastic Dream, Vospi kick/snare, Emu hats, T8 clap, Warmbo pad |
| far_shore_day | piece_shore | day | A major from the IV, 112 BPM four-on-the-floor, one lead bar E5 C#5 B4 C#5 over seven chords, Dream Plucks lead, Smooth Stabs, Juno-60 Strings |
| side_street_night | piece_mc1 (fixed_) | night | same score at 66 BPM, no drums, Vospi The Softest over Another Warm + MKS-70 Warm Pad, Sub 1 bass |
| far_shore_night_c | piece_shore_night_c (fixed_) | night | 66 BPM, no drums, Cybersoda Wurli over Film + Still pads, Sub 2 (candidate D, EP Middle, never picked) |
| old_mossback | piece_mossback2 | boss | 160 BPM C minor, intro 4 + A A B A, Leads/Light (lead -19 dB), Anthemish 1 stabs, Bass 3 riff, TNMG kit, crashes, tom fills |
| high_tide | menu_tide_high (slowtide.py "high") | menu | 104 BPM, kick every beat, two thin bars then the drop, 66 bars, 2:32 |

Kept for later, not in the game (`site/audio/keep_*.wav`, scores in `menu.LATER`): Sugar rush (156 BPM, "fits a
high energy moment, not a menu"), Welcome mat, Porch light, Jam jar, Paper boat ("great ideas but they do not fit
main menu"). Door: `gate` = one wooden knock, `door_close` = a lower, fuller knock (2026-11-16).

## Owner verdicts, dated
- 2026-11-11: SNES retro refused (modern and cozy wanted); chill ambient, Animal Crossing x Minecraft, repetition,
  no wrong notes; too much reverb/pad = "enveloping, sleepy"; chip square and ocarina/glock = "naive".
  Cobblestone step "sounds like a xylophone": base SFX on the literature.
- 2026-11-12: lead "too aggressive, too high, weird"; rising three-note hook = "pharmacy", "notification";
  crickets/fireflies in music "very very very bad"; staircases and arpeggios "make me SICK"; "the scale looks off".
- 2026-11-13: "going anywhere, freestyling, AI-generated typically"; "lost in a puddle of echoes"; "you're taking
  too much time"; third piano "unbearable"; "do not reuse the same instrument"; synthesised and recorded
  instruments "MIDI default windows sample"; chiptune "awful"; "DONT TEXT TO MUSIC", "use tools" -> Surge XT.
  "Dream plucks is better"; "too naive, too generic"; "the lead is doing bullshit"; one-cell Side street "good";
  "cuter 1 = amazing, really boosty, beautiful-day thingy"; "minecraft feeling 1 = very nice night song";
  boss from the main cell "looks too much like the main theme... create 2-3 themes"; "Chase B sounds off-rythm";
  "lantern fish sounds like those ugly midi songs"; "Old Mossback 2: brighter lead = amazing !!! but a bit..
  freestyling"; "make old mossback background more prominent by reducing the lead"; "Far shore = really good";
  "db should be normalized (w/ sound effect db also!)"; -16 LUFS "louder than all the other sounds" -> -20 LUFS;
  "musics must have transitions... they just spawn out of nowhere"; "make the transition long enough to not be noticed".
- 2026-11-15: menu "cute and fast" first five "everyone of them sounds bad", "keep a sound engineer approach";
  "try a slower more chill beat... ambiant almost"; long Slow tide "nah it sucks. i want something more dynamic.
  with just a gradient at the beginning"; "High tide is good but it takes a lil bit of time to settle... make the
  drop appear sooner"; "Great !! Make that the home screen song". "i agree with the corrections on existing songs".
- 2026-11-15/16 door: pulse train "weird noise", latch "a clic that does not sound like a door", gliding creak "an
  old person moaning"; "just like other sound effect, create it. do a showcase html page in local"; "go with one knock".

## Sound-design lessons (SFX)
- Sine pings read as water; debris is tiny noise bursts. Stone = a crowd of very short modes, never a few.
- Deep slow band swells (texture depth > 0.6) gurgle or creak: only for water and fire.
- A slow pulse train (20-110/s) through low resonances = a raspberry/fart; a gliding tone through formants = a voice;
  sparse noise grains = clicks.
- A bite = millisecond fracture pulses through a mouth resonance sliding ~1500 -> 700 Hz (`_chomp`).
- One sound per object family when building (post, planks, stone, furniture, soft, pot, fire, boat, floor, path, earth).
