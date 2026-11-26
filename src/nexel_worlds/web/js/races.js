// Player races (sim: Agent.race): the cat is the sheet as drawn; the others are the cat's own frames with the head
// rebuilt (ears off, the top rounded, the race's own ears, eyes, muzzle or bill put on), so every race has every
// animation. Designed in local/design/races.html. Clothes are painted on afterwards (wear.js).

// The races and their colours: race_list.js; a frame remade as a race: race_art.js; the picker: race_pick.js.

const Races = (() => {
  const {RACES, robot, rgb, BASE, classes} = RaceList, {analyse, remake} = RaceArt;
  // One person's sheet: their race, with their own tint mixed into its body colour. It carries, per frame, the grid of
  // colour classes and the measurements of the head, for the clothes.
  // (made a few frames a step: `made(..., false)` starts it and says null until it is done (wear.js works the steps between frames); raceSheet makes it at once)
  const sheets = new Map(), jobs = new Map();
  let baseData = null, analysis = null, measuring = null;
  const blend = (h, tint, k) => "#" + rgb(h).map((v, i) => Math.round(v * (1 - k) + rgb(tint)[i] * k).toString(16).padStart(2, "0")).join("");
  function made(key, tint, bot, now = true) {             // bot: the race's robot (an AI player)
    const found = RACES.find((r) => r.key === key), race = found && bot ? robot(found) : found, id = (bot ? "bot:" : "") + key + tint;
    if (!race || (key === "cat" && !bot)) return characterSheet(tint);
    if (sheets.has(id)) return sheets.get(id);
    let job = jobs.get(id); if (!job) jobs.set(id, job = steps(race, tint, id));
    if (!now) return null; while (!job.next().done); return sheets.get(id);
  }
  function* steps(race, tint, id) {
    const W = IMG.character.width, H = IMG.character.height, cols = W / CELL, rows = H / CELL;
    const frame = (r, c) => { const d = new Uint8ClampedArray(CELL * CELL * 4);
      for (let y = 0; y < CELL; y++) d.set(baseData.subarray(((r * CELL + y) * W + c * CELL) * 4, ((r * CELL + y) * W + c * CELL + CELL) * 4), y * CELL * 4);
      return d; };
    if (!baseData) {
      const b = document.createElement("canvas"); b.width = W; b.height = H;
      const g = b.getContext("2d"); g.drawImage(IMG.character, 0, 0);
      baseData = g.getImageData(0, 0, W, H).data;
    }
    if (!analysis) {                               // (the cat's frames measured once, whoever's sheet asks first: the others wait for it)
      measuring = measuring || (function* () { const a = []; for (let r = 0; r < rows; r++) for (let c = 0; c < cols; c++) { a.push(analyse(frame(r, c), r, c)); if (a.length % 8 === 0) yield; } analysis = a; })();
      while (!analysis && !measuring.next().done) yield;
    }
    const mix = race.mix || {b: .35, d: .3};     // a little of the person's colour, in the body and its shade (a robot: less, it is steel)
    const mine = {...race, col: {...race.col, ...Object.fromEntries(Object.entries(mix).map(([k, m]) => [k, blend(race.col[k] || BASE[k], tint, m)]))}};
    for (const k of ["c", "e"]) if (race.col[k] === race.col.b) mine.col[k] = mine.col.b;
    const out = document.createElement("canvas"); out.width = W; out.height = H;
    const img = new ImageData(W, H);
    out.grids = []; out.an = analysis;
    for (let r = 0; r < rows; r++) for (let c = 0; c < cols; c++) {
      const d = frame(r, c);
      out.grids.push(remake(d, analysis[r * cols + c], mine));
      for (let y = 0; y < CELL; y++) img.data.set(d.subarray(y * CELL * 4, (y + 1) * CELL * 4), ((r * CELL + y) * W + c * CELL) * 4);
      if (out.grids.length % 8 === 0) yield;
    }
    out.getContext("2d", {willReadFrequently: true}).putImageData(img, 0, 0);
    sheets.set(id, out); jobs.delete(id);
  }
  // the sheets asked for and not made: worked on until `until` (performance.now) -> are there more
  function work(until) { for (const [id, job] of jobs) { while (performance.now() < until) if (job.next().done) { jobs.delete(id); break; } if (performance.now() >= until) break; } return jobs.size > 0; }
  return {RACES, raceSheet: (key, tint, bot) => made(key, tint, bot), made, work};
})();
const raceSheet = Races.raceSheet;
