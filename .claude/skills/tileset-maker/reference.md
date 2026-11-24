# Tileset maker: the owner's words and what was decided

Quotes are the owner's, verbatim (typos kept), from sessions a90f7f26 (Nov 8-20) and fa29ccbd (Nov 15-24), 2026.

## Tileset and 2D paint
- 11-08 "still .. ugly ... imrpove your tileset". He then supplied Sprout Lands (premium): "i have the premium
  tileset so use it", "do you leverage every frame provided by the tileset?"
- 11-09 hills: "this part of the tileset is so ugly ... i want natural slopes that really feels like going up"
- 11-09 "the 'trail path' is soo ugly. the pebble and flowers looks like weird artifacts. the grass one is good. the
  default one is good too"
- 11-10 "you sohuld leverage border/corner tiles instead of weird cropping"; 11-11 "you should use the sameb orders
  as provided by the tileset !!!"
- 11-15 "the pavement (stones on the floor) looks bad , glitchy, textures arent connected"; "bridges are creating
  black ugly borders". The lesson: the pack had the right cells and the game drew the wrong ones (dump the sheet first).

## Voxel land
- 11-18 "i think we should go for the full voxel rendering ... it will make the xray view more intuitive and easy.
  well keep the other sprites 2d-facing camera"; "make this a voxel world viewed as a top down in animal crossing style"
- 11-18 "design a high quality side that respect the tileset and they audit what they do. blocks should be 3d, every
  single one"
- 11-19 "the 3d worls still look very flat. that is very very ugly. be critic"
- 11-19 side shapes on the mockup page: the owner took **side 4** (the thin side: the block stays 16 px wide and shows a lit
  or shaded wall). Same day, "this wall look so weird" (a diagonal cliff as a grid of crates, stone over earth in a
  staircase, foam brackets per tile). That gave one material per wall and one tone per rock.
- 11-20 "Some tiles should be turned 3d: bed, etc". Bed, chest, table, workbench, well and sign became box models.
  Trees, bushes, flowers, creatures and the cat stay flat cards.
- 11-21 "i just want to have 1 block = player size or player size = 2 blocks but no player = 1/2 block things ...
  block is block". The pick was one block = one player: a level is a cube (`H = 1`).
- 11-21 "Block icons look like textures put in inventory": `cube_icons.js` draws three faces of the block's own paint.
- 11-21 "the quality of the rendering SUCKS ... see the sides etc ?": sides use the pack's cliff px (`test_e2e_hd_sides.py`).
- 11-21 phone: "there's some line artefacts everywhere" (mediump). Fixed with highp.
- 11-22 "that xray you did created awful borders" (a 4x4 dither strip). Now solid steps in whole px.
- 11-23 "all textures are fucked up when i sprint up the spawn hill" (the paint atlas spilled). Now `AW = 2048`.

## Water
- 11-19 "I wanted it transparent like those Minecraft shaders so we can see the depth. What we have right now is good
  for water". He took look **10** (bed under clear water, clearer near you). His colours, ripple and shore stay.
- 11-23 "water propagation tiles are ugly and glitchy" (stacked see-through boxes). Running water became one surface
  with one tint, and placed blocks dam it.

## One rule, not many
- 11-23 "rook digged this. textures are a mess. fix that. there are many many many small bugs which suggest you duped
  logic and avoided abstractions to create many many little rules. dont like that." Then: "same for textures. many
  many many little bugs." The fix (commit message "a dug cut is drawn by the land's own face rules, one art px")
  deleted the trench-only lighting and shading, net -32 lines. It then moved every surface to one painting rule
  (`test_e2e_hd_surfaces.py`).

## Earth, stone, under the land
- 11-24 "Earth on top stone underneath should only be a matter of world generation. Grass shouldn't turn into stone."
  Built as `chunks.py stone_at`: mountains (5 high and up) are stone, and elsewhere stone starts 2 cells under the
  lowest ground around. The live save was backed up and migrated on a copy first.
- 11-24 "The 3d voxel style isn't respected. Man, that 3d engine need more rigour !", "The wall inside underground
  looks bad", "Keep in mind that x-ray should not allow to see ores in wall". The cutaway was held back. Four
  options went on the mockup page (`#under`), and the owner took "go with high walls then" (option 2: the box cut at your
  head, with the land just south of you lowered so it never hides you).

## Mockup page habits the owner set
- 11-11 "showcase me different design so i validate them on a webpage"; 11-18 "if you dont know how to decide create
  a html mockup page"; 11-19 "If you need choices from me, create mockup pages on the GitHub"; never a new page each
  time ("do not recreate page everytime.. just update the existing").
- 11-24 "Do you need me to decide something? Show mockups ?": the owner expects pictures of real builds, not descriptions.
