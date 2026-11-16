// Five robots for the cat, to choose from before one is made for every race (design/enemies/site/robots.html).
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
      make: (race) => ({...race, mix: [.18, .15], col: {...STEEL}, head() {}})},
    {id: "lamp", name: "Lamp eyes", text: "Steel, with the eyes themselves lit: two tall lamps, no screen around them. An aerial with a lit tip stands between the ears, and the cheeks glow. It shows at night from far away.",
      make: (race) => ({...race, mix: [.18, .15], col: {...STEEL, e: "#b9f3fb"},
        head(H, A) { for (const [x, y] of eyes(H, A)) { H.put(x, y, "L"); H.put(x, y - 1, "L", "bde"); } aerial(H, A); }})},
    {id: "screen", name: "Screen face", text: "A darker steel body with a face that is a pale, lit screen: the eyes are drawn on it in deep blue. The opposite of the visor: the face is the brightest thing on it.",
      make: (race) => ({...race, mix: [.2, .15], col: {...STEEL, b: "#aab4c2", d: "#8793a3", e: "#aab4c2", s: "#dffaff", S: "#1f6f86"},
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
      make: (race) => ({...race, mix: [.8, 0], col: {...STEEL, b: "#eef1f4", e: LIGHT},
        head(H, A) { for (const [x, y] of eyes(H, A)) H.put(x, y, "L"); }})},
    {id: "brass", name: "Brass wind-up", text: "A clockwork toy in warm brass, with the cat's own dark eyes and a wind-up key in its back (seen from the side and from behind). The only one that is not grey: it cannot be taken for stone or iron.",
      make: (race) => ({...race, mix: [.12, .1], col: {a: "#5e3b22", b: "#e6b866", d: "#bd8a45", e: "#f3d691", c: LIGHT, f: "#7a4a2a", g: LIGHT, K: "#8a5a2c"},
        head(H, A) {
          if (A.facing === "up") { for (const dy of [2, 3, 4]) { H.put(A.cx - 1, A.k + dy, "e"); H.put(A.cx, A.k + dy, "a"); } return; }      // from behind, the key is seen edge on
          if (!A.side) return;
          const [x, s] = back(H, A, A.k + 2);            // side on: a stem, and a ring to turn it by
          H.put(x - s, A.k + 2, "a");
          for (let i = 2; i <= 4; i++) for (const dy of [1, 2, 3]) if (i !== 3 || dy !== 2) H.put(x - i * s, A.k + dy, "a");
        }})},
  ];
})();
