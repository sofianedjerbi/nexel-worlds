window.CREATURES = [
 {
  "key": "hob",
  "name": "Hob",
  "role": "ally",
  "cell": [
   32,
   42
  ],
  "move": "waddle",
  "side": "ally",
  "beats": {
   "flare": "wwsssrr"
  },
  "hit": {
   "flare": "burn"
  },
  "ms": {
   "idle": [
    260,
    220,
    220,
    260,
    300,
    260,
    140,
    260
   ],
   "walk": [
    110,
    110,
    110,
    110,
    110,
    110,
    110,
    110
   ],
   "flare": [
    260,
    320,
    80,
    140,
    180,
    220,
    260
   ],
   "sit": [
    160,
    200,
    300,
    520,
    520,
    520,
    200,
    160
   ]
  },
  "where": "wherever you build one: a dome of clay, a hearthstone and a coal",
  "when": "always; it matters at night",
  "behaviour": "A hearth that walks. Feed it wood and it follows you, or tell it to stay and it sits by your door. At night it keeps a ring of light round itself; anything that comes into it, it <b>flares</b> at: it hunches, the fire draws in, then the firebox bursts in a blaze of light, a flame leaps from the chimney and sparks fly: what is close is burnt and thrown back, and night creatures flee and do not come near again for a while. It never chases, and never hurts a player or their animals. It also cooks what you put in its firebox.",
  "stats": {
   "hp": 60,
   "damage": "3, burns (night creatures only)",
   "speed": "slow",
   "eats": "wood, coal"
  },
  "sheet": "sheets/hob.png",
  "anims": {
   "idle": [
    0,
    1,
    2,
    3,
    4,
    5,
    6,
    7
   ],
   "walk": [
    8,
    9,
    10,
    11,
    12,
    13,
    14,
    15
   ],
   "flare": [
    16,
    17,
    18,
    19,
    20,
    21,
    22
   ],
   "sit": [
    23,
    24,
    25,
    26,
    27,
    28,
    29,
    30
   ]
  },
  "palette": [
   "6f3f33",
   "de8f5f",
   "f0ac78",
   "fcd4a2",
   "bf6e4b",
   "a35a3f",
   "93503b",
   "4d2b2e",
   "fff09a",
   "ffb54c",
   "ee6b45",
   "ffe38a",
   "ffffff",
   "f59a7a",
   "f7b98a"
  ],
  "frames": 31,
  "tall": 162
 },
 {
  "key": "grumblestump",
  "name": "Grumblestump",
  "role": "night bruiser",
  "cell": [
   40,
   44
  ],
  "move": "shuffle",
  "side": "night",
  "ms": {
   "idle": [
    400,
    300,
    260,
    300,
    400,
    300,
    260,
    300
   ],
   "walk": [
    130,
    130,
    130,
    130,
    130,
    130,
    130,
    130
   ],
   "slam": [
    180,
    260,
    200,
    200,
    80,
    160,
    200,
    260
   ],
   "sleep": [
    600,
    600,
    600,
    600,
    600,
    600,
    600,
    600
   ]
  },
  "beats": {
   "slam": "wwwwsssr"
  },
  "hit": {
   "slam": "knock"
  },
  "where": "where trees were cut: clearings, the edge of your wood pile",
  "when": "night; a plain stump by day",
  "behaviour": "By day it is a stump, the kind you chopped. At night its eyes open and it pulls its roots out and shuffles after whoever cut trees near it. It is slow; what it has is the <b>slam</b>: both arms go up and its embers flare (held long: that is your time), then it brings them down and a ring of cracks runs out two tiles. Step clear. Hit it from behind while it pulls its arms back. Beaten, it is firewood, a lot of it.",
  "stats": {
   "hp": 24,
   "damage": "4, knocked down",
   "speed": "slow",
   "drops": "old wood, a seedling"
  },
  "sheet": "sheets/grumblestump.png",
  "anims": {
   "idle": [
    0,
    1,
    2,
    3,
    4,
    5,
    6,
    7
   ],
   "walk": [
    8,
    9,
    10,
    11,
    12,
    13,
    14,
    15
   ],
   "slam": [
    16,
    17,
    18,
    19,
    20,
    21,
    22,
    23
   ],
   "sleep": [
    24,
    25,
    26,
    27,
    28,
    29,
    30,
    31
   ]
  },
  "palette": [
   "4d3022",
   "c48d5e",
   "a6724a",
   "875a3a",
   "6b4430",
   "f0d29c",
   "d8b27a",
   "c79a62",
   "8cc25e",
   "6aa048",
   "4e7f36",
   "3a2620",
   "ffcf5a",
   "fff6c8",
   "e0574a",
   "fff3e0",
   "8fd06a",
   "d9c49a",
   "a89a8a"
  ],
  "frames": 32,
  "tall": 161
 },
 {
  "key": "gustling",
  "name": "Gustling",
  "role": "rare, day",
  "cell": [
   32,
   40
  ],
  "move": "drift",
  "side": "day",
  "beats": {
   "snatch": "wwwwwsssrrr"
  },
  "hit": {
   "snatch": "steal"
  },
  "ms": {
   "idle": [
    110,
    110,
    110,
    110,
    110,
    110,
    110,
    110
   ],
   "walk": [
    70,
    70,
    70,
    70,
    70,
    70,
    70,
    70
   ],
   "snatch": [
    170,
    130,
    100,
    100,
    100,
    80,
    160,
    160,
    130,
    130,
    160
   ]
  },
  "where": "open hills and fields on a windy day",
  "when": "day, wind only; rare",
  "behaviour": "A breeze that wanders against the wind. It drifts up to whoever is busiest and <b>snatches</b>: it draws up thin and spins hard (the leaves tighten round it), then pops wide and takes whatever is in your free hand, then runs. Hit it during the spin and it scatters into a harmless breeze. Catch it after a snatch and it drops everything it took that day, which is sometimes a lot.",
  "stats": {
   "hp": 4,
   "damage": "0 (steals)",
   "speed": "as fast as you",
   "drops": "what it stole"
  },
  "sheet": "sheets/gustling.png",
  "anims": {
   "idle": [
    0,
    1,
    2,
    3,
    4,
    5,
    6,
    7
   ],
   "walk": [
    8,
    9,
    10,
    11,
    12,
    13,
    14,
    15
   ],
   "snatch": [
    16,
    17,
    18,
    19,
    20,
    21,
    22,
    23,
    24,
    25,
    26
   ]
  },
  "palette": [
   "c4dfe4",
   "ffffff",
   "9cc4cc",
   "45566a",
   "ffffff",
   "86c45c",
   "5f9a45",
   "f0a050",
   "c9733a",
   "e6d7ad",
   "e8574a",
   "b23a3c",
   "7fbf5a",
   "5a6e86"
  ],
  "frames": 27,
  "tall": 150
 },
 {
  "key": "snapbloom",
  "name": "Snapbloom",
  "role": "rare, day",
  "cell": [
   36,
   40
  ],
  "move": "shuffle",
  "side": "day",
  "ms": {
   "idle": [
    220,
    220,
    220,
    220,
    220,
    220,
    220,
    220
   ],
   "walk": [
    110,
    110,
    110,
    110,
    110,
    110,
    110,
    110
   ],
   "bite": [
    160,
    180,
    220,
    150,
    150,
    70,
    110,
    140,
    140,
    140,
    200
   ]
  },
  "beats": {
   "bite": "wwwwwssrrrr"
  },
  "hit": {
   "bite": "knock"
  },
  "where": "among flowers, at the edge of gardens",
  "when": "day, in bloom season; rare",
  "behaviour": "A flower a little too big, among the others, its eyes shut. It does not move while you look at it. Turn your back and it shuffles a step closer on its roots. Close enough, it <b>bites</b>: its eyes snap open, the petals fold back and a mouth of little teeth opens where the heart was (that is the warning), then it lunges a tile and snaps. Cut it while its petals are back. Beaten, it drops a seed that grows into a tame one.",
  "stats": {
   "hp": 6,
   "damage": 2,
   "speed": "slow, only when unseen",
   "drops": "snap seed"
  },
  "sheet": "sheets/snapbloom.png",
  "anims": {
   "idle": [
    0,
    1,
    2,
    3,
    4,
    5,
    6,
    7
   ],
   "walk": [
    8,
    9,
    10,
    11,
    12,
    13,
    14,
    15
   ],
   "bite": [
    16,
    17,
    18,
    19,
    20,
    21,
    22,
    23,
    24,
    25,
    26
   ]
  },
  "palette": [
   "7d3d56",
   "f7a8bf",
   "e07a9a",
   "ffdbe6",
   "ffd45c",
   "e09a32",
   "5a2838",
   "fff6ea",
   "ff8fa8",
   "7cc35a",
   "5a9a44",
   "3f6e30",
   "b07a4f",
   "8a5a3a"
  ],
  "frames": 27,
  "tall": 154
 }
];
