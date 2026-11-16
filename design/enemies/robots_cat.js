// Robots for the cat (five, then six more), to choose from before one is made for every race (design/enemies/site/robots.html).
// The first design put a dark visor across the face: "black thing on their face is ugly". None of these covers the
// face: each says "machine" another way. A design is {id, name, text, make(race)}: make() returns the race to draw
// (web/js/races.js raceSheet(key, tint, design)); robots.py loads this file into the game's page to draw the sheets.

const CATBOTS = (() => {
  const LIGHT = "#6fe9ff";                           // the cat's light
  const STEEL = {a: "#39414f", b: "#d5dbe3", d: "#a2acb9", e: "#a2acb9", c: LIGHT, f: "#566070", g: LIGHT, L: LIGHT};
  // The eyes: the dark pixels inside the face.
  const eyes = (H, A) => { const out = [];
    if (A.facing !== "up") for (let y = A.sy + 3; y < A.k - 1; y++) for (let x = A.hmin + 1; x < A.hmax; x++)
      if (H.get(x, y) === "a" && H.get(x - 1, y) && H.get(x + 1, y) && H.get(x, y - 1) && H.get(x, y + 1) && H.get(x - 1, y) !== "a" && H.get(x + 1, y) !== "a") out.push([x, y]);
    return out; };
  const aerial = (H, A) => { H.put(A.cx, A.sy - 1, "a"); H.put(A.cx, A.sy - 2, "a"); H.put(A.cx, A.sy - 3, "L"); };
  const back = (H, A, y) => { let x = A.facing === "right" ? 0 : 47; const s = A.facing === "right" ? 1 : -1;      // side on: the edge of its back
    while (x >= 0 && x < 48 && !H.get(x, y)) x += s; return [x, s]; };
  return [
    {id: "tin", name: "Tin cat", text: "The cat as it is, in steel: the same face and the same dark eyes, a darker plate on the brow, grey bolts where the blush was, the ears lined in light and the bell a lamp. The gentlest of the five.",
      make: (race) => ({...race, mix: {b: .18, d: .15}, col: {...STEEL}, head() {}})},
    {id: "lamp", name: "Lamp eyes", text: "Steel, with the eyes themselves lit: two tall lamps, no screen around them. An aerial with a lit tip stands between the ears, and the cheeks glow. It shows at night from far away.",
      make: (race) => ({...race, mix: {b: .18, d: .15}, col: {...STEEL, e: "#b9f3fb"},
        head(H, A) { for (const [x, y] of eyes(H, A)) { H.put(x, y, "L"); H.put(x, y - 1, "L", "bde"); } aerial(H, A); }})},
    {id: "screen", name: "Screen face", text: "A darker steel body with a face that is a pale, lit screen: the eyes are drawn on it in deep blue. The opposite of the visor: the face is the brightest thing on it.",
      make: (race) => ({...race, mix: {b: .2, d: .15}, col: {...STEEL, b: "#aab4c2", d: "#8793a3", e: "#aab4c2", s: "#dffaff", S: "#1f6f86"},
        head(H, A) {
          const es = eyes(H, A); if (!es.length) return;
          const y0 = es[0][1] - 1, front = A.facing === "right" ? 1 : -1;
          for (let y = y0; y <= y0 + 2; y++) for (let x = A.hmin + 2; x <= A.hmax - 2; x++) {
            if (A.side && (x - A.cx) * front < -1) continue;
            if ("bde".includes(H.get(x, y) || "?")) H.put(x, y, "s");
          }
          for (const [x, y] of es) H.put(x, y, "S");
        }})},
    {id: "paint", name: "Painted", text: "Enamel in the player's own colour, strongly, with bare steel where a machine shows: the brow plate, the arms and the feet. Lit eyes and lit cheeks. The one where you still know whose robot it is by its colour.",
      make: (race) => ({...race, mix: {b: .8, d: 0}, col: {...STEEL, b: "#eef1f4", e: LIGHT},
        head(H, A) { for (const [x, y] of eyes(H, A)) H.put(x, y, "L"); }})},
    {id: "brass", name: "Brass wind-up", text: "A clockwork toy in warm brass, with the cat's own dark eyes and a wind-up key in its back (seen from the side and from behind). The only one that is not grey: it cannot be taken for stone or iron.",
      make: (race) => ({...race, mix: {b: .12, d: .1}, col: {a: "#5e3b22", b: "#e6b866", d: "#bd8a45", e: "#f3d691", c: LIGHT, f: "#7a4a2a", g: LIGHT, K: "#8a5a2c"},
        head(H, A) {
          if (A.facing === "up") { for (const dy of [2, 3, 4]) { H.put(A.cx - 1, A.k + dy, "e"); H.put(A.cx, A.k + dy, "a"); } return; }      // from behind, the key is seen edge on
          if (!A.side) return;
          const [x, s] = back(H, A, A.k + 2);            // side on: a stem, and a ring to turn it by
          H.put(x - s, A.k + 2, "a");
          for (let i = 2; i <= 4; i++) for (const dy of [1, 2, 3]) if (i !== 3 || dy !== 2) H.put(x - i * s, A.k + dy, "a");
        }})},
    // "more concepts": six more, further from the first five (one changes the head's shape, one is dark, one is scrap).
    {id: "eye", name: "One eye", text: "Steel, with one big round lit lens in the middle of the face in place of the two eyes. The least cat-like face: nobody takes it for a person.",
      make: (race) => ({...race, mix: {b: .18, d: .15}, col: {...STEEL},
        head(H, A) {
          const es = eyes(H, A); if (!es.length) return;
          H.eyes();
          const y = es[0][1], f = A.facing === "right" ? 1 : -1;
          if (!A.side) { for (let dy = -2; dy <= 1; dy++) for (let dx = -2; dx <= 1; dx++) if ((dx === -2 || dx === 1) + (dy === -2 || dy === 1) < 2) H.put(A.cx + dx, y + dy, dx === -2 || dx === 1 || dy === -2 || dy === 1 ? "d" : "L", "bde"); return; }
          const ex = es[0][0];
          for (const [dx, dy] of [[-1, -1], [-1, 0], [0, -2], [1, -2], [0, 1], [1, 1]]) H.put(ex + dx * f, y + dy, "d", "bde");
          for (const [dx, dy] of [[0, -1], [0, 0], [1, -1], [1, 0]]) H.put(ex + dx * f, y + dy, "L");
        }})},
    {id: "box", name: "Box head", text: "The head is a square box with a pale lit screen for a face and two aerials where the ears were. The only one whose outline is not the cat's: a machine from across a field, but the other races would look alike.",
      make: (race) => ({...race, mix: {b: .18, d: .15}, col: {...STEEL, s: "#dffaff", S: "#1f6f86"},
        head(H, A) {
          const es = eyes(H, A), f = A.facing === "right" ? 1 : -1;
          for (let y = A.top - 1; y < A.sy; y++) for (let x = A.hmin - 4; x <= A.hmax + 4; x++) H.put(x, y, null);
          const x0 = A.hmin - (A.side ? 0 : 1), x1 = A.hmax + (A.side ? 0 : 1);
          for (let y = A.sy; y < A.k; y++) for (let x = x0 - 3; x <= x1 + 3; x++) {
            if (x < x0 || x > x1) H.put(x, y, null);
            else if (x === x0 || x === x1 || y === A.sy) H.put(x, y, "a");
            else if (!"bde".includes(H.get(x, y) || "?")) H.put(x, y, "b");
          }
          if (es.length) { const y0 = es[0][1] - 1;
            for (let y = y0; y <= y0 + 2; y++) for (let x = x0 + 2; x <= x1 - 2; x++) if (!A.side || (x - A.cx) * f >= -1) H.put(x, y, "s");
            for (const [x, y] of es) H.put(x, y, "S"); }
          for (const [x, s] of A.side ? [[A.cx, 0]] : [[A.hmin + 2, -1], [A.hmax - 2, 1]]) { H.put(x, A.sy - 1, "a"); H.put(x + s, A.sy - 2, "a"); H.put(x + s, A.sy - 3, "L"); }
        }})},
    {id: "scrap", name: "Scrap", text: "Built from what was lying around: a rust plate on the brow, one ear patched in copper, a patch of old green paint on the belly, one eye lit and the other dark. The one with the most character, and the least tidy.",
      make: (race) => ({...race, mix: {b: .18}, col: {...STEEL, d: "#c9824f", e: "#8793a3", r: "#c9824f", R: "#8f5a36", q: "#9fb59a"},
        head(H, A) {
          const es = eyes(H, A).sort((p, q) => p[0] - q[0]), f = A.facing === "right" ? 1 : -1;
          if (es.length && (A.side ? f > 0 : true)) H.put(es[0][0], es[0][1], "L");                // its right eye is the lit one
          const mine = (x) => A.side ? f < 0 : A.facing === "up" ? x < A.cx : x >= A.cx;           // its left side: the copper ear, the green patch
          for (let y = A.top - 1; y < A.sy + 3; y++) for (let x = 0; x < 48; x++) if (mine(x)) { if (H.get(x, y) === "b") H.put(x, y, "r"); else if (H.get(x, y) === "c") H.put(x, y, "R"); }
          for (let y = A.k + 2; y <= A.k + 4; y++) for (let x = 0; x < 48; x++) if (mine(x) && H.get(x, y) === "b") H.put(x, y, "q");
        }})},
    {id: "shell", name: "White shell", text: "A smooth white shell with its trim in the player's own colour: the ear lining, the cheeks, the collar, the arms and feet. Grey eyes. Clean and new, like a household machine, and you know whose it is.",
      make: (race) => ({...race, mix: {c: .85, e: .7, f: .8, d: .75}, col: {a: "#566070", b: "#f6f8fa", d: "#8a93a0", e: "#c5ccd4", c: "#8a93a0", f: "#7a8494", g: LIGHT, L: LIGHT, S: "#566070"},
        head() {}})},
    {id: "neon", name: "Neon", text: "The whole body in dark blue steel, with everything else lit: tall eyes, ear lining, cheeks, bell. The reverse of the visor (the face is not covered, the body is dark). Easiest to see at night, hardest on a dark floor.",
      make: (race) => ({...race, mix: {b: .12, d: .1}, col: {a: "#141a2b", b: "#46557a", d: "#35415f", e: LIGHT, c: LIGHT, f: "#232b44", g: LIGHT, L: LIGHT},
        head(H, A) { for (const [x, y] of eyes(H, A)) { H.put(x, y, "L"); H.put(x, y - 1, "L", "bde"); } }})},
    {id: "core", name: "Heart light", text: "Plain steel with nothing lit on the head: the cat's own eyes, grey ears. Its one light is a core in its chest, where the bell was. The face stays the cat's; the machine is in the body.",
      make: (race) => ({...race, mix: {b: .18, d: .15}, col: {...STEEL, c: "#a2acb9"},
        head(H, A) { if (A.facing === "down") for (const dy of [2, 3]) for (const dx of [-1, 0]) H.put(A.cx + dx, A.k + dy, "L", "bdgfy"); }})},
  ];
})();
