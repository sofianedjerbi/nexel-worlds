# Owner verdicts on sprites (dated, the owner's words in quotes)

From past sessions 97b45604, a90f7f26, fa29ccbd and the owner memory. Newest decisions win.

## Settled looks (do not change without a new pick on the mockup page)
| Date | Thing | Verdict / what was built |
|---|---|---|
| 2026-11-11 | Enemies | "all your enemies look the same": restart with distinct body plans, every direction, "as high quality as we got right now" |
| 2026-11-11 | Animation | "animation looks weird" (2-frame flips): 4-pose walks, quadrupeds keep the body level, legs in diagonal pairs; attacks = wind-up held ~0.4-0.5 s, one fast strike frame, hold, recover; idle a small twitch on a long pause |
| 2026-11-11 | Coherence | "see player and existing animated mobs to make it coherent" |
| 2026-11-11 | Pincer | "animation are too simple and ugly. pincer should be a lot smaller" |
| 2026-11-11 | Wyrm | "rework wyrm vertical sprite: it should be more impressive!", then "PERFECT" |
| 2026-11-12 | Mossback boss | mouth must not smile ("just a turtle mouth": one flat line); shake needed more animation |
| 2026-11-12 | Races | bunny: "remove the weird tilt on top of rabbit ears"; "frog still looks ugly" (no stalk eyes, no hard mouth line); then "amazing", clothes on every race |
| 2026-11-13 | Items | "the pixelization of them does not match the pixelization of the game", "wayyy too big !!", "more pixelated in the inventory bar": 11 px by whole px, land's px |
| 2026-11-13 | Sprites audit | "head popping off while using tool animation, rabbit ears are backwards when walking" |
| 2026-11-14 | Sword attack | "looks like breaking a bloc... not like attacking": own attack sheet (swing_art.js) |
| 2026-11-16 | Robots (AI players) | dark visor refused: "black thing on their face is ugly. suggest 5 robotic design for the cat, before generalizing to everyone"; 11 designs shown; "go with tin cat": race unchanged, in steel, own face and dark eyes, grey bolts where the blush was, ear lining + collar bell lit in the race's colour |
| 2026-11-18 | Voxel land | land is voxel blocks; "keep the other sprites 2d-facing camera" |
| 2026-11-21 | Scale | "go with 1 block = player" |
| 2026-11-21 | Block icons | "look like textures put in inventory": cube icons, three faces, block's own paint, ink outline; selected item shown in the paw |
| 2026-11-21 | Inventory frames | "Use dark border everywhere and light for selected" |
| 2026-11-22 | Aim | "lets do that, face rotation and paw rotation": up/ahead/down poses, whole px (aim_art.js); box drawn over the character unless the cell is under it |
| 2026-11-22/23 | Sword held | "sword handling does not look natural at all"; options A low at the side / B shoulder / C back; "go with A. Low at the side": hand at the hip, blade down and forward, sways with steps, one pose standing/aiming/walking, the cut starts from it. Spear: upright like a staff |
| 2026-11-23 | Player halo | "remove the halo around the player. its ugly especially in daylight" (caves still lit round you) |
| 2026-11-24 | Voxel rigour | "The 3d voxel style isn't respected": every face reads as a block, pixel art never stretched |

## Recurring dislikes
- Blob shapes with dot eyes facing the camera; stick legs; an anus on a boar's back view; a hunched scarecrow.
- A cap that pulses like another creature (sporecap vs wisp): keep each creature's motion distinct.
- Anything dark over a face; see-through overlays; glow halos in daylight; long hard lines across the picture.
- Things on the ground too big beside a body; pixel sizes that do not match the land's.
- Designs built without being shown, and mockups whose options look the same.

## Open (check before acting)
- 2026-11-24: "tools not in the paw" report: proposed one grip rule (hand ring touching the body outline at one paw
  point per facing, the state only changes the angle). Waiting on the owner's go; before/after on the mockup first.
- Sporecap, Hopper, Burrow: kept "in mind", designs only. Stilt, adder, lampwing, snapjaw: off the page, files kept.
