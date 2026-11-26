// Clothes and armor (sim/wear.py): how each piece looks on the player. Nothing is redrawn: each frame of the character
// sheet is read once (where the skull starts, where the collar is, where the feet are) and the pieces are painted there,
// so they follow every bob, step and swing. Designed in local/design/clothes.html; a test keeps LOOK's pieces the world's (tiles.py WEAR).

// item -> the look it has in the tables below (its slot is the world's: RULES.wear)
const LOOK = {
  straw_hat: "straw", sporecap_hat: "sporecap", wizard_hat: "wizard", gold_crown: "crown", iron_helmet: "iron", mossback_helm: "shell", wool_beanie: "beanie", flower_crown: "flowers", bandana: "bandana", sprout: "sprout",
  linen_shirt: "linen", red_scarf: "scarf", wool_sweater: "wool", overalls: "overalls", leather_vest: "leather", wizard_robe: "robe", iron_chestplate: "iron", gold_chestplate: "gold", mossback_plate: "moss",
  linen_shorts: "linen", denim: "denim", red_trousers: "red", leather_chaps: "leather", robe_skirt: "robe", iron_greaves: "iron", gold_greaves: "gold", moss_kilt: "moss",
  leather_boots: "leather", red_sneakers: "red", rain_boots: "rain", blue_slippers: "blue", iron_boots: "iron", gold_boots: "gold", moss_slippers: "moss",
  sparkle_charm: "sparkle", firefly_charm: "fireflies", leaf_charm: "leaves", heart_charm: "hearts", flame_charm: "flame", frost_charm: "frost", halo_charm: "halo", spore_charm: "spores", flower_charm: "flowers",
};
const WearParts = (() => {
  const {analyse, dress, rgb} = WearFit;   // (the pieces and how they are fitted to a frame: wear_look.js)
  // The sheet for one person: their tinted sheet (sprites.js) with what they wear painted on, built once per outfit.
  // It carries, per frame, the pixels just outside the dressed player (for the auras) and the top of the head.
  // (made a few frames a step, between frames (pump): `ready` says null until it is done, and a body is drawn once its sheet is there. Made in one go,
  // a person's first sight held a slow phone still for over a second: the first screen's islanders, each one coming into view)
  const sheets = new Map(), jobs = new Map();
  let analysis = null, measuring = null, pumping = false;
  function made(tint, worn, race = "cat", bot = false, now = true) {      // bot: an AI player, drawn as its race's robot
    if (!worn) { const plain = Races.made(race, tint, bot, now); if (!plain && !pumping) pump(); return plain; }   // (races.js; the cat's is sprites.js characterSheet)
    const o = {head: "none", top: "none", pants: "none", shoes: "none"};
    for (const [slot, item] of Object.entries(worn)) if (LOOK[item] && slot in o) o[slot] = LOOK[item];
    const key = tint + race + (bot ? "bot" : "") + Object.values(o).join();
    if (sheets.has(key)) return sheets.get(key);
    let job = jobs.get(key); if (!job) { jobs.set(key, job = steps(tint, o, race, bot, key)); if (!pumping) pump(); }
    if (!now) return null; while (!job.next().done); return sheets.get(key);
  }
  function* steps(tint, o, race, bot, key) {
    let plain; while (!(plain = Races.made(race, tint, bot, false))) { Races.work(performance.now() + 2); yield; }
    const W = plain.width, H = plain.height, cols = W / CELL, rows = H / CELL;
    const frame = (data, r, c) => { const d = new Uint8ClampedArray(CELL * CELL * 4);
      for (let y = 0; y < CELL; y++) d.set(data.subarray(((r * CELL + y) * W + c * CELL) * 4, ((r * CELL + y) * W + c * CELL + CELL) * 4), y * CELL * 4);
      return d; };
    if (!analysis && !plain.an) {                  // (the cat's own frames measured, once: a race's sheet carries its own)
      measuring = measuring || (function* () { const b = document.createElement("canvas"); b.width = W; b.height = H;
        const bg = b.getContext("2d"); bg.drawImage(IMG.character, 0, 0);
        const data = bg.getImageData(0, 0, W, H).data, a = [];
        for (let r = 0; r < rows; r++) for (let c = 0; c < cols; c++) { a.push(analyse(frame(data, r, c), r)); if (a.length % 8 === 0) yield; } analysis = a; })();
      while (!analysis && !measuring.next().done) yield;
    }
    const out = document.createElement("canvas"); out.width = W; out.height = H;
    const g = out.getContext("2d", {willReadFrequently: true}); g.drawImage(plain, 0, 0);
    const img = g.getImageData(0, 0, W, H);
    out.edges = []; out.tops = [];
    for (let r = 0; r < rows; r++) for (let c = 0; c < cols; c++) {
      const i = r * cols + c, d = frame(img.data, r, c), A = plain.an ? plain.an[i] : analysis[i];
      dress(d, A, o, plain.grids && plain.grids[i], race === "bunny");
      for (let y = 0; y < CELL; y++) img.data.set(d.subarray(y * CELL * 4, (y + 1) * CELL * 4), ((r * CELL + y) * W + c * CELL) * 4);
      const edge = [], solid = (x, y) => x >= 0 && y >= 0 && x < CELL && y < CELL && d[(y * CELL + x) * 4 + 3];
      for (let y = 0; y < CELL; y++) for (let x = 0; x < CELL; x++)
        if (!solid(x, y) && (solid(x - 1, y) || solid(x + 1, y) || solid(x, y - 1) || solid(x, y + 1))) edge.push([x, y]);
      out.edges.push(edge); out.tops.push(A.top);
      if (i % 8 === 7) yield;
    }
    g.putImageData(img, 0, 0);
    sheets.set(key, out); jobs.delete(key);
  }
  // the steps of the sheets asked for, when the page is idle (at most 8 ms at a time: never a long task), until none is left
  function pump(dl) {
    pumping = true; const until = performance.now() + (dl && !dl.didTimeout ? Math.max(1, Math.min(8, dl.timeRemaining())) : 8);
    if (dl !== undefined) { for (const [k, job] of jobs) { while (performance.now() < until) if (job.next().done) { jobs.delete(k); break; } if (performance.now() >= until) break; } Races.work(until); }
    if (jobs.size || Races.work(0)) { if (window.requestIdleCallback) requestIdleCallback(pump, {timeout: 100}); else setTimeout(() => pump(null), 16); } else pumping = false;
  }
  return {TOPS: WEAR_TOPS, PANTS: WEAR_PANTS, SHOES: WEAR_SHOES, HEADS: WEAR_HEADS, rgb, wornSheet: (tint, worn, race, bot) => made(tint, worn, race, bot), ready: (tint, worn, race, bot) => made(tint, worn, race, bot, false)};
})();
const wornSheet = WearParts.wornSheet, wornReady = WearParts.ready;
