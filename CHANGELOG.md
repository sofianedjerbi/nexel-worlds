# Changelog

Written by [python-semantic-release](https://python-semantic-release.readthedocs.io) from the
[Conventional Commits](https://www.conventionalcommits.org) on main (see CONTRIBUTING.md).

<!-- version list -->

## v0.2.0 (2026-11-24)

### Bug Fixes

- **web**: Bodies are drawn as far as the land
  ([`fba426f`](https://github.com/sofianedjerbi/nexel-worlds/commit/fba426f397d83ef95e6632fd1a7826e3fb4883ed))

- **web**: The far sea patches lie at the sea's own face
  ([`925b012`](https://github.com/sofianedjerbi/nexel-worlds/commit/925b0125fff35ba4c1188a9a47cea07e0a0502e7))

- **web**: The HD look's land box is the one view extent; its north rows are asked for as land on
  the screen
  ([`f3666b7`](https://github.com/sofianedjerbi/nexel-worlds/commit/f3666b77a8104992d19321521b3c021c76da67ec))

- **web**: The water's depth tint is one function of distance: whole near you, the sea's one far
  tint by the horizon
  ([`3ac1dc9`](https://github.com/sofianedjerbi/nexel-worlds/commit/3ac1dc9ff9ebca575bfc170d1b58fe008034e79f))

- **web**: Water past the horizon is not drawn; the far water goes whole px by px
  ([`85fb320`](https://github.com/sofianedjerbi/nexel-worlds/commit/85fb320346d3873c316e29fc12178fc4c82c7373))

- **web**: Water seen along its face at the horizon is whole, in the sea's one far tint
  ([`d781451`](https://github.com/sofianedjerbi/nexel-worlds/commit/d781451f41d849f572d6bf196e6a3892642f573e))

### Features

- **web**: A view distance setting (Near, Normal, Far, Very far); the land made as wide as the
  picture at the horizon
  ([`df80242`](https://github.com/sofianedjerbi/nexel-worlds/commit/df80242c069ed16d275b1258c1e85626589f4528))

### Refactoring

- **web**: The fall is BodyPlace's: its state off the body, worked out in levels, asked once a frame
  (phase B, 1)
  ([`46770b0`](https://github.com/sofianedjerbi/nexel-worlds/commit/46770b0947eca498714e3bbfdff0b38d8e0effce))

- **web**: The hop's state is BodyPlace's (phase B, 2)
  ([`5e937f5`](https://github.com/sofianedjerbi/nexel-worlds/commit/5e937f54223e066159b27fcc31c78536f1607be3))

- **web**: The ladder's solver says a height in levels; its picture's px are the place's (phase B,
  3)
  ([`8957f62`](https://github.com/sofianedjerbi/nexel-worlds/commit/8957f6212c9295697edc1122fb95589862cc173a))


## v0.1.13 (2026-11-24)

### Bug Fixes

- **web**: A creature killed flashes white, lifts and fades in the HD look
  ([`0733155`](https://github.com/sofianedjerbi/nexel-worlds/commit/0733155dd3e0dd2b19034131b6510bbeeff8714e))

### Refactoring

- **web**: A frame's parts are called by name in one place; nothing wraps frame, drawTile or
  arriveBlock at load
  ([`6e2892f`](https://github.com/sofianedjerbi/nexel-worlds/commit/6e2892f9d56cb6f8903d94816f652d96a7f5d127))

- **web**: One place points the painters' canvas and pixel elsewhere (drawOn)
  ([`2110d5f`](https://github.com/sofianedjerbi/nexel-worlds/commit/2110d5fd0d8e9dffdbff68d9434f705b022c00f7))

- **web**: The classic picture's last painters are gone; without WebGL 2 a panel says so
  ([`4fde3d4`](https://github.com/sofianedjerbi/nexel-worlds/commit/4fde3d4e7a75053c5d33825488e73f0d2ae5ce2e))

- **web**: What moves on by itself has its own step a frame; the classic painters no longer run
  under the HD look
  ([`958a291`](https://github.com/sofianedjerbi/nexel-worlds/commit/958a2913eae20e01ac14cb18995c98715c743dee))

### Testing

- **e2e**: What a frame costs the script with things in the air, twelve creatures round you
  ([`56a19aa`](https://github.com/sofianedjerbi/nexel-worlds/commit/56a19aa8903fdafabdb3298302e045e86c95178a))


## v0.1.12 (2026-11-24)

### Bug Fixes

- A column's material is the world's word, kept through digging; a cut in stone is stone
  ([`44eb916`](https://github.com/sofianedjerbi/nexel-worlds/commit/44eb916412950d73025d6e2ec91cac85a428d2c4))

- **web**: Stone or earth is a column's own; a cut never recolours the tiles beside it
  ([`2e9efd9`](https://github.com/sofianedjerbi/nexel-worlds/commit/2e9efd98068bb2874317c40866eb70c443adcd2e))

- **web**: Stone under level 5 has stone's lowest top at any depth
  ([`2f8fc79`](https://github.com/sofianedjerbi/nexel-worlds/commit/2f8fc7903c0ef89791955de91ff412c8f8316244))

- **web**: The water's tint goes from a depth to the next in whole steps of 4 art px
  ([`5aaf50e`](https://github.com/sofianedjerbi/nexel-worlds/commit/5aaf50e876cd26d4a21c08ff2a7599318f3d2f78))

### Refactoring

- **web**: A bridge has one paint, its model's
  ([`527c7b2`](https://github.com/sofianedjerbi/nexel-worlds/commit/527c7b2c71f64fb352795d30ec4f0993bdedc47a))

- **web**: A built box's faces are lit as the land's faces that way
  ([`57139b6`](https://github.com/sofianedjerbi/nexel-worlds/commit/57139b6dcdf023576a7239bd1443e10bd48cf9b1))

- **web**: A wall's look is data the land's painter lays; drawWall is gone
  ([`ab04ad2`](https://github.com/sofianedjerbi/nexel-worlds/commit/ab04ad2cac48d1167bd8588d715c4e114cd39b1e))

- **web**: Cobbles join by the one mask rule
  ([`09fd0b6`](https://github.com/sofianedjerbi/nexel-worlds/commit/09fd0b6e93230bccba91f5a0a721b1ea2fe1c838))

- **web**: One rule for a surface's paint; what is laid on the ground is data
  ([`bc1aea1`](https://github.com/sofianedjerbi/nexel-worlds/commit/bc1aea101eead6b38345d7f18a58a65b06b2b1a4))

- **web**: Planks and roofs are px the land's painter lays, not a 2D canvas read back
  ([`1301335`](https://github.com/sofianedjerbi/nexel-worlds/commit/1301335928f97ef795c7ca48621c48c5e4d97450))

- **web**: Under sea level one tone by depth on the land's own paints, no dug sheets
  ([`6915b0e`](https://github.com/sofianedjerbi/nexel-worlds/commit/6915b0ed4c7caf3d6c2a7340e560ce1a91831442))

### Testing

- **e2e**: A body's place pinned frame by frame for each way it moves (phase A of the solvers' move)
  ([`e5732e7`](https://github.com/sofianedjerbi/nexel-worlds/commit/e5732e733f49f83d619cb1b1f408c2d3c7cd45a1))

- **web**: Drop the pit-floor-darker test, a rule e9aab4f removed; hd water read with room
  ([`979867c`](https://github.com/sofianedjerbi/nexel-worlds/commit/979867cd26b486ba5ee5f381b9d861fa43c2c4df))

- **web**: Hd_burst's light step has room for walls under sea level 3 % lighter
  ([`aef5290`](https://github.com/sofianedjerbi/nexel-worlds/commit/aef52908403cd3b6218dd864dc318db101a8587d))

- **web**: Hd_sheet compares the land alone (HdLook.landOnly), not a tree's sway
  ([`f7032cc`](https://github.com/sofianedjerbi/nexel-worlds/commit/f7032cc8afd76029e22aa31a89cc0228cec4848d))

- **web**: Hd_sun's shadow test says the frames round the one that lost it
  ([`28979df`](https://github.com/sofianedjerbi/nexel-worlds/commit/28979df038a36884b826cfe6e74ab31de9f5d1fd))


## v0.1.11 (2026-11-24)

### Bug Fixes

- **web**: On a phone a button that comes never moves Build under the thumb
  ([`47aef50`](https://github.com/sofianedjerbi/nexel-worlds/commit/47aef501d4b60ae5a1ae71e3465b8eac523e6c07))

### Testing

- **e2e**: The running water's darkest px are not read behind your own head
  ([`da12fe1`](https://github.com/sofianedjerbi/nexel-worlds/commit/da12fe1c4fcf78e6ffa02c2437c808636ae61ef4))


## v0.1.10 (2026-11-24)

### Bug Fixes

- **web**: A body's place says the tile it is drawn on; on a ladder that is the ladder's for the
  whole climb
  ([`b4260c9`](https://github.com/sofianedjerbi/nexel-worlds/commit/b4260c9687d15e3697d410ef36ca2a1b72583c45))

- **web**: The place's line keeps to the nearer tile across a fall's drop or a ladder
  ([`232f696`](https://github.com/sofianedjerbi/nexel-worlds/commit/232f696c526e93af9737a6dcb6aaf7c3767793b5))

- **web**: Two people on one row at two heights each have their name over their own head
  ([`bf4d46f`](https://github.com/sofianedjerbi/nexel-worlds/commit/bf4d46f8c0aee23afe655babfdd7bf8f4e30dd7c))

### Refactoring

- **web**: Climbing.js stands by the one rule (cells.js stand); its three leftovers go
  ([`6728a33`](https://github.com/sofianedjerbi/nexel-worlds/commit/6728a338bd2c2ed05799a2005717d82d86c7ad5e))

- **web**: One writer for the way a body faces; drawing a body turns nothing
  ([`8688526`](https://github.com/sofianedjerbi/nexel-worlds/commit/8688526f75860f453de336ac90e01477c519635e))

- **web**: The straight line's level is the place's (line); jump.js lineLift goes
  ([`4b7ce3d`](https://github.com/sofianedjerbi/nexel-worlds/commit/4b7ce3d9231589cd8fef590c01aa33ba5a93bc43))


## v0.1.9 (2026-11-24)

### Bug Fixes

- **web**: No lantern halo in the day's last and first minutes; the lantern comes on from the
  night's start, one line
  ([`5d1cba4`](https://github.com/sofianedjerbi/nexel-worlds/commit/5d1cba4f578f0933aaf3bda1a219962e3be80915))

- **web**: While the eye tilts the sky's line goes with it; the clouds drift with you, not with the
  camera
  ([`c91f8b1`](https://github.com/sofianedjerbi/nexel-worlds/commit/c91f8b1860d6b2b8633d844728f6363fc00392ed))

### Refactoring

- **sim**: One can_craft() and one take_pile(); the craft book asks the world
  ([`59c94ed`](https://github.com/sofianedjerbi/nexel-worlds/commit/59c94ed07b081a1c43ade42df85745a6d82dc37c))

- **sim**: One hears(listener, event) for agents and screens, one RANGE table
  ([`243ebc4`](https://github.com/sofianedjerbi/nexel-worlds/commit/243ebc4299894905fb4ad8106f0216c4f78e0a93))

- **sim**: One REACH table for the world's checks and a screen's offers
  ([`698c66d`](https://github.com/sofianedjerbi/nexel-worlds/commit/698c66dfc8446283190f33e539dbbeb4015c9822))

- **sim**: One stand() a side answers "can a body be there"
  ([`1401064`](https://github.com/sofianedjerbi/nexel-worlds/commit/14010644fdfe638942bf74ede2278cad8f6c9be1))

- **web**: Hd.js split along its records: the eye (hd_eye.js), the lamps (hd_lamps.js), the pointer
  (hd_pick.js)
  ([`b8b4892`](https://github.com/sofianedjerbi/nexel-worlds/commit/b8b489243edcc6cd8b91c16d5f6e08854af18bb3))

- **web**: The hour's light from one source (Light.now) and the lamps from one table (Light.lamp)
  ([`3f096af`](https://github.com/sofianedjerbi/nexel-worlds/commit/3f096afbdd823a7773796fdf4601600399ae5007))

### Testing

- **e2e**: The aim tests take the eye's pitch as the cover gives it (a nook, a dip a level deep: the
  surface's)
  ([`e60ef21`](https://github.com/sofianedjerbi/nexel-worlds/commit/e60ef216ffc0b926bd74a5103af7f83043537bc6))

- **e2e**: The cliff reach test reads the shared reach table
  ([`950ad60`](https://github.com/sofianedjerbi/nexel-worlds/commit/950ad609a035761a1cfe9f44183013e948564723))

- **e2e**: The fall test reads the camera a frame on, not from a second ask in the same frame
  ([`8e54669`](https://github.com/sofianedjerbi/nexel-worlds/commit/8e5466943aa51e76cfc4f94c15ba1a101f41e30c))

- **e2e**: Three waits that gave up without a word wait on their condition and say the state
  ([`ab6db4f`](https://github.com/sofianedjerbi/nexel-worlds/commit/ab6db4fda1b9a0934c87f9929ffbd6eaa3c37b0e))


## v0.1.8 (2026-11-24)

### Bug Fixes

- **web**: The eye's pitch comes from the cover alone; walking through a dip no longer tilts it and
  back
  ([`fd5cbda`](https://github.com/sofianedjerbi/nexel-worlds/commit/fd5cbda073f439036d4b8ff4526e3b2882b8c3fb))

### Code Style

- **tests**: Plain open mode in the rules test
  ([`23dd74b`](https://github.com/sofianedjerbi/nexel-worlds/commit/23dd74ba808180e90ee7526115723251b39c41ac))

### Refactoring

- **rules**: One rules table on the server, sent in hello; the client types no rule table again
  ([`7226a2c`](https://github.com/sofianedjerbi/nexel-worlds/commit/7226a2c616df60088983f341dab4087e5023047e))


## v0.1.7 (2026-11-24)

### Bug Fixes

- **web**: One body-place record a frame; a ladder climb no longer opens the window or lights the
  lantern
  ([`4dbad12`](https://github.com/sofianedjerbi/nexel-worlds/commit/4dbad12b7280995dab290287dd7256a6c62dc6b4))

- **web**: Under the land your lantern lights every floor of your space; no mouth shade on a walled
  floor
  ([`924cc5c`](https://github.com/sofianedjerbi/nexel-worlds/commit/924cc5c6057857ae251b70a262cc2591b06a6479))

### Refactoring

- **web**: BodyPlace, one record of where a body is a frame; its picture, name, camera and the HD
  look read it
  ([`0313a23`](https://github.com/sofianedjerbi/nexel-worlds/commit/0313a2316c8e813a46f6a3ab08b846e05ffeb434))

- **web**: The land over your body is its own record (HdLevel.cover), apart from where the body is
  ([`6b09790`](https://github.com/sofianedjerbi/nexel-worlds/commit/6b097906ff9516fec47cd217e82a2b6276cea15f))

- **web**: The two tiles a body is between are worked out once (Floors.between)
  ([`fa7d471`](https://github.com/sofianedjerbi/nexel-worlds/commit/fa7d4715bafcac68ff683e94df43c0ad22e57c8e))

### Testing

- **e2e**: A pit's floor is shaded darker along its walls by the land's own corner shade
  ([`3178c02`](https://github.com/sofianedjerbi/nexel-worlds/commit/3178c02db6ffd61430f18c53d2b4eae4f173102c))


## v0.1.6 (2026-11-23)

### Bug Fixes

- **sim**: A walk said after a flight's hard landing goes on; one rule for the ground under a body
  ([`62f61c0`](https://github.com/sofianedjerbi/nexel-worlds/commit/62f61c0a7aead3ff28a1f3656a3217fa7260118a))


## v0.1.5 (2026-11-23)

### Bug Fixes

- **web**: A chat bubble is as wide as its words; the name's tab is centred over a short one
  ([`55b9f06`](https://github.com/sofianedjerbi/nexel-worlds/commit/55b9f06ca8173bdea9c9f206ad1b692fb3bda15e))


## v0.1.4 (2026-11-23)

### Bug Fixes

- **web**: A dug cut is drawn by the land's own face rules, one art px
  ([`6641a98`](https://github.com/sofianedjerbi/nexel-worlds/commit/6641a986dde5e3e054a2bce2ae7e34baf5a49a4b))


## v0.1.3 (2026-11-23)

### Bug Fixes

- **web**: A chat bubble sits on the land's pixel grid, no 1 px wobble while walking
  ([`89eb861`](https://github.com/sofianedjerbi/nexel-worlds/commit/89eb8615369162bbf1599ff576baa43fae8eae89))

- **web**: Land on screen is asked for at once, not 3 s after a far ask (missing world)
  ([`9cdccef`](https://github.com/sofianedjerbi/nexel-worlds/commit/9cdccef366cc49c167d50a88d336e014439ca3b3))

- **web**: One whole-pixel scale at fractional screen density; overlays snapped to it
  ([`53110a7`](https://github.com/sofianedjerbi/nexel-worlds/commit/53110a7a2db77e0fed2617f339c4006733c88427))

- **web**: Your own name and bubble follow your drawn sprite, no wobble
  ([`fae2045`](https://github.com/sofianedjerbi/nexel-worlds/commit/fae2045658d64f6e1573646a3efd27b74615ba1b))


## v0.1.2 (2026-11-23)

### Bug Fixes

- **web**: A jump's arc carries you over water and wide holes
  ([`6974c9f`](https://github.com/sofianedjerbi/nexel-worlds/commit/6974c9f3c6ba81da7c257e637a32849a68726588))


## v0.1.1 (2026-11-23)

### Bug Fixes

- **web**: Running water is one see-through surface, no stacked tints, seams or navy slabs
  ([`f2687af`](https://github.com/sofianedjerbi/nexel-worlds/commit/f2687aff0ed403b0a4c09ca4ec1c0df5d28feffc))

### Documentation

- Readme is one animated banner, a line and the links
  ([`41eb354`](https://github.com/sofianedjerbi/nexel-worlds/commit/41eb354749fa6202579f5fc66298a10308053ac4))

- Showcase readme with banner, shots and play links; dev notes move to contributing
  ([`8d23305`](https://github.com/sofianedjerbi/nexel-worlds/commit/8d23305311158de72c82db068cc787fe84d86931))


## v0.1.0 (2026-11-23)

The first tagged version: the game as it was when the history was rewritten to Conventional Commits.
