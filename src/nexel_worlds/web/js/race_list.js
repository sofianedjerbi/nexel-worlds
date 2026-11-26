// The player races' table (races.js makes their sheets): each race's colours, head and words, the AI players' robot
// of each, and the colours the races add to the cat's own. Designed in local/design/races.html.
//   RaceList -> {RACES, robot, rgb, BASE, DIRS, classes, EXTRA}

const RaceList = (() => {
  const rgb0 = (h) => [parseInt(h.slice(1, 3), 16), parseInt(h.slice(3, 5), 16), parseInt(h.slice(5, 7), 16)];
  const RGB = new Map(), rgb = (h) => { let v = RGB.get(h); if (!v) RGB.set(h, v = rgb0(h)); return v; };   // (a colour's numbers, parsed once and kept, not for every px painted)
  const BASE = {a: "#5c4e92", b: "#f3f2c0", c: "#e8b5ac", d: "#ddd5de", e: "#f3d8c5", f: "#766daa", g: "#eae178"};
  const CLASS = Object.fromEntries(Object.entries(BASE).map(([k, h]) => [rgb(h).join(), k]));
  const DIRS = ["down", "up", "right", "left"];
  const classes = (d) => { const o = new Array(CELL * CELL); for (let i = 0; i < CELL * CELL; i++) o[i] = d[i * 4 + 3] ? CLASS[d[i * 4] + "," + d[i * 4 + 1] + "," + d[i * 4 + 2]] || "?" : null; return o; };   // (a frame's px as colour classes: null empty, "?" none of the cat's)
  const RACES = [
    {key: "cat", name: "Cat", col: {},
      text: "The player as it is today: pointed ears with pink inside, whiskers, a collar with a bell.", head() {}},
    {key: "bunny", name: "Bunny", col: {a: "#8a6f8f", b: "#fbf3ee", d: "#e6d9dc", c: "#f2a9b4", e: "#f6cfd0"},
      text: "Two long, straight ears with rounded tips, pink inside, the same width down to the head and joined to it with no line across the foot. Side on, the far ear shows as a shaded edge behind the near one. From behind, a white tuft of a tail. It keeps the whiskers.",
      head(H, A) {
        H.round();
        // An ear: nine rows, straight, a rounded tip, pink down the inside. `out` says which side the pink is on (-1 left, 1 right).
        const SHAPE = [".aa.", "abba", "abca", "abca", "abca", "abca", "abca", "abca", "abba"];      // the same width all the way down
        const ear = (x0, out, fill = "b", pink = true, dy = 0) => SHAPE.forEach((row, i) => {
          [...(out > 0 ? row : [...row].reverse().join(""))].forEach((ch, j) => {
            if (ch !== "." && A.sy - 9 + i + 1 + dy <= A.sy) H.put(x0 + j, A.sy - 9 + i + 1 + dy, ch === "c" ? (pink ? "c" : fill) : ch === "b" ? fill : "a"); });
        });
        if (A.side) {                              // side on, the far ear shows behind the near one, in shade. The near ear's pink
          const back = A.facing === "right" ? -1 : 1;      // inside faces the way the bunny faces (it faced backwards: "rabbit ears are
          ear(A.cx - 2 + back, back, "d", false, 1); ear(A.cx - 2, -back, "b", true);      // backwards"); the far one a pixel back and lower: only its edge shows
          H.put(A.cx - 1, A.sy, "b"); H.put(A.cx, A.sy, "b");                              // the near ear runs into the head: no line across its foot
        } else for (const [x0, out] of [[A.cx - 5, -1], [A.cx + 1, 1]]) {
          ear(x0, out, "b", A.facing !== "up");
          H.put(x0 + 1, A.sy, "b"); H.put(x0 + 2, A.sy, "b");
        }
        if (A.facing === "up") for (const [x, y] of [[-1, 0], [0, 0], [-1, 1], [0, 1]]) H.put(A.cx + x, A.k + 3 + y, "w");
      }},
    {key: "bear", name: "Bear", col: {a: "#6b4a3a", b: "#d6a878", d: "#b98958", c: "#b98958", e: "#e0b58c"},
      text: "Small round ears set wide, a pale muzzle with a dark nose, no whiskers. The stockiest outline of the four.",
      head(H, A) {
        H.round(); H.whiskers();
        const ear = (x0) => { H.put(x0, A.sy - 2, "a"); H.put(x0 + 1, A.sy - 2, "a"); H.put(x0 - 1, A.sy - 1, "a"); H.put(x0, A.sy - 1, "c"); H.put(x0 + 1, A.sy - 1, "c"); H.put(x0 + 2, A.sy - 1, "a");
          H.put(x0, A.sy, "b"); H.put(x0 + 1, A.sy, "b"); };
        if (A.side) ear(A.cx - (A.facing === "right" ? 2 : -1)); else { ear(A.hmin + 2); ear(A.hmax - 3); }
        if (A.facing === "down") { for (let y = 6; y <= 7; y++) for (let x = -2; x <= 1; x++) H.put(A.cx + x, A.sy + y, "m", "bde"); H.put(A.cx - 1, A.sy + 6, "n"); H.put(A.cx, A.sy + 6, "n"); }
        if (A.side) { const f = A.facing === "right" ? A.hmax - 1 : A.hmin + 1, s = A.facing === "right" ? -1 : 1;
          for (let y = 6; y <= 7; y++) for (let x = 0; x < 2; x++) H.put(f + s * x, A.sy + y, "m", "bde"); H.put(f, A.sy + 6, "n"); }
      }},
    {key: "frog", name: "Frog", col: {a: "#2f6672", b: "#74c9bd", d: "#4aa3a0", c: "#74c9bd", e: "#74c9bd"},
      text: "Built like the game's own hopper, in its colours: a round head with two low bumps on top and a dark eye in each, a soft wide mouth, pink cheeks, a pale belly, spots down its back. No ears, no whiskers.",
      head(H, A) {
        H.round(); H.whiskers(); H.eyes(); H.plain();
        // A bump: four wide, two tall, part of the head's own outline (not a stalk), with the eye in it: two dark pixels, one above the other.
        const bump = (x0, ex) => {
          H.put(x0 + 1, A.sy - 2, "a"); H.put(x0 + 2, A.sy - 2, "a"); H.put(x0, A.sy - 1, "a"); H.put(x0 + 3, A.sy - 1, "a");
          for (const j of [1, 2]) { H.put(x0 + j, A.sy - 1, "b"); H.put(x0 + j, A.sy, "b"); }
          if (A.facing !== "up") { H.put(x0 + ex, A.sy - 1, "n"); H.put(x0 + ex, A.sy, "n"); }
        };
        if (!A.side) {
          bump(A.hmin + 1, 2); bump(A.hmax - 4, 1);
          if (A.facing === "down") {
            for (let x = A.hmin + 4; x <= A.hmax - 4; x++) H.put(x, A.sy + 5, "d", "b");                      // the mouth: a shade, not a line
            H.put(A.hmin + 2, A.sy + 4, "p", "b"); H.put(A.hmax - 2, A.sy + 4, "p", "b");                     // cheeks
          } else for (const [x, y] of [[-3, 3], [-2, 3], [1, 5], [2, 5], [-1, 7], [3, 2]]) H.put(A.cx + x, A.sy + y, "d", "b");   // spots
        } else {
          const right = A.facing === "right", f = right ? A.hmax - 1 : A.hmin + 1, s = right ? -1 : 1;        // f: the front of the face
          bump(right ? A.hmax - 5 : A.hmin + 2, right ? 2 : 1);                                               // one bump, just behind the brow
          for (let x = 0; x < 3; x++) H.put(f + s * x, A.sy + 5, "d", "b");                                   // the mouth, from the front of the face
        }
        H.belly();
      }},
    {key: "duck", name: "Duck", col: {a: "#9a6a2e", b: "#f9dd6e", d: "#e6c355", c: "#f9dd6e", e: "#f7c98a"},
      text: "A yellow duckling: a round head with one curl of down on top, an orange bill that sticks out in front when seen from the side, and orange feet. No ears, no whiskers.",
      head(H, A) {
        H.round(); H.whiskers(); H.plain();
        const curl = (x) => { H.put(x, A.sy - 2, "a"); H.put(x + 1, A.sy - 3, "a"); H.put(x - 1, A.sy - 1, "a"); H.put(x, A.sy - 1, "b"); H.put(x + 1, A.sy - 2, "b"); H.put(x + 2, A.sy - 2, "a"); H.put(x + 1, A.sy - 1, "a"); H.put(x, A.sy, "b"); };
        if (!A.side) {
          curl(A.cx - 1);
          if (A.facing === "down") for (let x = -2; x <= 1; x++) { H.put(A.cx + x, A.sy + 6, "o"); H.put(A.cx + x, A.sy + 7, x === -2 || x === 1 ? "B" : "O"); }     // the bill, from the front
        } else {
          const right = A.facing === "right", f = right ? A.hmax : A.hmin, out = right ? 1 : -1;            // f: the front edge of the face
          curl(A.cx - 1 - out);
          for (let j = 0; j <= 2; j++) H.put(f + out * j, A.sy + 6, "o");                                    // the bill sticks out past the face
          for (let j = 0; j <= 1; j++) H.put(f + out * j, A.sy + 7, "O");
          H.put(f + out * 3, A.sy + 6, "B"); H.put(f + out * 2, A.sy + 7, "B");
          for (let j = 1; j <= 2; j++) H.put(f + out * j, A.sy + 5, "B"); H.put(f + out, A.sy + 8, "B");
        }
        H.feet();
      }},
  ];
  // The AI players are robots ("go with tin cat", chosen from eleven on local/design/robots.html; a dark visor
  // across the face was refused): the race as it is, in steel. The same head, face and dark eyes; grey bolts where
  // the blush was; the ears' lining and the bell lit in the race's own light; the duck keeps its orange bill and feet;
  // the frog's eyes, up in its two bumps where a dark eye is lost in the dark edge, are lit.
  const LIGHT = {cat: "#6fe9ff", bunny: "#ff8fd6", bear: "#ffb44a", frog: "#8cff7a", duck: "#ffe75a"};
  const robot = (race) => ({...race, mix: {b: .18, d: .15},
    col: {a: "#39414f", b: "#d5dbe3", d: "#a2acb9", e: "#a2acb9", c: LIGHT[race.key], f: "#566070", g: LIGHT[race.key],
          w: "#eef2f6", m: "#b7c0cb", n: race.key === "frog" ? LIGHT.frog : "#39414f", y: "#c3cbd5", p: "#a2acb9"}});
  const EXTRA = {w: "#fffdf4", m: "#f1dfbd", n: "#3a2a30", y: "#f4f3c4", p: "#f2a9b4", o: "#f59a4a", O: "#e07f38", B: "#a85a2a"};     // ... and the bill and feet        // white, muzzle, nose and pupil, belly
  return {RACES, robot, rgb, BASE, DIRS, classes, EXTRA};
})();
