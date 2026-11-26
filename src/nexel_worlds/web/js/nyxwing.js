// Nyxwing, the boss of "Sugar rush" (sim/nyxwing.py; its sheet: design/enemies/roster/nyxwing.py): how it is drawn
// (drawWild hands it here), and, in the land (HdFx hands it a `put`), what is not on its body: the eclipse it comes out
// of, the speck it is far off and the dragon it grows into, its shadow while it is up in the sky, its body breaking into
// stars when it dies. Every time here is a count of beats of its song (156 BPM), as the server's are.
// Its sounds are music/sfx.py's drake_* set, all of one palette.
const Nyx = (() => {
  const BEAT = 60000 / 156, WARN = 1.5 * BEAT, SKY = 4.5 * BEAT, LOCK = BEAT;
  const FALL_FROM = 12, ARRIVE = 32;                        // beats into its entrance: it comes out of the eclipse; it lands (the drop)
  // From a sound's start to its loudest moment, in ms, measured on the renders of music/sfx.py: started that much before
  // the beat it is to land on (the descent's swell on the landing, the fall's on the crash, the dissolve's on the last star).
  const HIT = {drake_descend: 5422, drake_fall: 501, drake_dissolve: 1370};
  const GOLD = ["#ffcf5a", "#fff3c0", "#ffe08a", "#c77dff", "#7fb8ff"], FIRE = ["#fff3c0", "#ffcf5a", "#c77dff", "#7a4dd0", "#2a1c4a"];
  const ATTACKS = new Set(["breath", "storm", "sweep", "dive", "rush"]);
  const seen = new Map();                                    // id -> what this client knows of it (times, its last picture)
  const st = (id) => { if (!seen.has(id)) seen.set(id, {}); return seen.get(id); };
  const later = (ms, f) => setTimeout(f, Math.max(0, ms));
  const say = (name, e) => sfx(name, e.x, e.y, 30);         // (a dragon carries further than a tortoise: boss.js's 20)
  const owns = (e) => e.kind === "nyxwing" || ents.has("nyxwing" + e.id);
  // when its entrance began, on this page's clock (its song's start): the server's event, or, for a player who comes
  // when it is already here, how long ago the server says it came (views.py `came`); what is still to be heard of it is
  // played when it falls due
  function came(e, at) {
    const s = st(e.id);
    if (s.arriveAt !== undefined) return s.arriveAt;
    s.arriveAt = at;
    const due = (after, name) => { const ms = at + after - performance.now(); if (ms >= 0) later(ms, () => say(name, e)); };
    due(8 * BEAT, "drake_omen");                                            // a roar from far off; its swell lands on the landing
    due(ARRIVE * BEAT - HIT.drake_descend, "drake_descend");
    return at;
  }
  const began = (e) => e.came === undefined ? st(e.id).arriveAt : came(e, performance.now() - e.came * 1000);

  // ---- its body, on the creature's own canvas (drawWild)
  function frame(s, moving, now, id) {
    const A = WILD.nyxwing, t = now - (s.windAt ?? -1e9), warm = (k) => A[k][0] + (t < 192 ? 0 : t < 384 ? 1 : 2);
    if (s.crashAt && now - s.crashAt < 440) return A.dive[0] + 5 + Math.floor((now - s.crashAt) / 110);     // landed from the sky
    if (s.anim === "breath") {
      if (t < WARN) return warm("breath");
      if (t < WARN + 2 * BEAT) return A.breath[0] + 3 + Math.floor((t - WARN) / 96) % 3;                     // two beats of fire
      if (t < WARN + 2 * BEAT + 288) return A.breath[0] + (t < WARN + 2 * BEAT + 192 ? 6 : 7);
    } else if (s.anim === "storm") {
      if (t < WARN) return warm("storm");
      if (t < WARN + 3 * BEAT) return A.storm[0] + 3 + Math.floor((t - WARN) / 48) % 16;                     // the spin, a ring a beat
      if (t < WARN + 3 * BEAT + 288) return A.storm[0] + (t < WARN + 3 * BEAT + 192 ? 19 : 20);
    } else if (s.anim === "sweep") {
      if (t < WARN + 400) return t < WARN ? warm("sweep") : A.sweep[0] + Math.min(7, 3 + Math.floor((t - WARN) / 80));
    } else if (s.anim === "dive") {
      if (t < WARN) return warm("dive");
    } else if (s.anim === "rush") {
      if (t < 961) return wildFrame(A.rush, t, false);
    }
    return wildFrame(moving ? A.walk : A.idle, now + id * 137, true);
  }
  function draw(p, x, y, now) {
    const e = p.e, A = WILD.nyxwing, z = zoom, s = st(e.id);
    if (e.act !== s.act && ATTACKS.has(e.act) && s.anim !== e.act) { s.windAt = now; s.anim = e.act; }    // (a warning we did not hear of)
    s.act = e.act;
    if (e.act === "arrive") { s.arriveAt ??= now; return; }                  // coming down: drawn in the land (hd)
    if (e.act === "sky") return;                                             // up out of sight: its shadow is (hd)
    const moving = now - p.moved < 350 || Math.abs(p.x - p.tx) + Math.abs(p.y - p.ty) > .05;
    const acting = ATTACKS.has(s.anim) && now - s.windAt < WARN + 3 * BEAT + 288;
    const [fx, fy] = acting && e.dir ? e.dir : [p.fx, p.fy], row = fy > 0 ? 0 : fy < 0 ? 1 : fx < 0 ? 2 : 3;
    const col = frame(s, moving, now, e.id);
    s.last = {col, row, x: p.x, y: p.y};
    const blit = () => ctx.drawImage(IMG.nyxwing, col * A.cw, row * A.ch, A.cw, A.ch, x - (A.cw - 16) / 2 * z, y - (A.ch - 16) * z, A.cw * z, A.ch * z);
    blit();
    const fl = flashes.get("nyxwing" + e.id);
    if (fl && now - fl < 120) { ctx.globalCompositeOperation = "lighter"; blit(); ctx.globalCompositeOperation = "source-over"; }
    if (e.hp < A.hp) {                                                       // its health, over its wings
      const w = 48 * z, bx = Math.round(x + 8 * z - w / 2), by = y - (A.ch - 22) * z;
      ctx.fillStyle = "#2a1c4a"; ctx.fillRect(bx - z, by - z, w + 2 * z, 4 * z);
      ctx.fillStyle = e.hp * 2 > A.hp ? "#ffcf5a" : "#c77dff"; ctx.fillRect(bx, by, Math.max(0, w * e.hp / A.hp), 2 * z);
    }
  }

  // ---- pictures made once, in whole art px
  const made = new Map();
  const canvas = (k, w, h, paint) => { if (!made.has(k)) { const c = document.createElement("canvas"); c.width = w; c.height = h; const g = c.getContext("2d"); g.imageSmoothingEnabled = false; paint(g); made.set(k, c); } return made.get(k); };
  const cell = (col, row) => canvas(`c${col},${row}`, WILD.nyxwing.cw, WILD.nyxwing.ch, (g) => g.drawImage(IMG.nyxwing, col * WILD.nyxwing.cw, row * WILD.nyxwing.ch, WILD.nyxwing.cw, WILD.nyxwing.ch, 0, 0, WILD.nyxwing.cw, WILD.nyxwing.ch));
  // far off: its picture made smaller by whole px (each n x n block one px, the colour most of it has: ui.js smallArt),
  // and darker with the distance (the night between)
  const speck = (col, n) => canvas(`s${col},${n}`, Math.ceil(WILD.nyxwing.cw / n), Math.ceil(WILD.nyxwing.ch / n), (g) => {
    const A = WILD.nyxwing, im = smallArt(IMG.nyxwing, col * A.cw, 0, A.cw, A.ch, Math.ceil(A.cw / n)), d = im.data, dark = {1: 0, 2: .3, 3: .55, 4: .8}[n];
    for (let o = 0; o < d.length; o += 4) for (let k = 0; k < 3; k++) d[o + k] = Math.round(d[o + k] * (1 - dark) + [10, 6, 28][k] * dark);
    g.putImageData(im, 0, 0);
  });
  const oval = (w, h, col) => canvas(`o${w},${h},${col}`, w, h, (g) => {     // a shadow on the ground: the game's soft purple
    g.fillStyle = col;
    for (let j = 0; j < h; j++) { const k = Math.sqrt(1 - ((j + .5 - h / 2) / (h / 2)) ** 2), half = Math.round(w / 2 * k); g.fillRect(w / 2 - half, j, 2 * half, 1); }
  });
  const eclipse = (r) => canvas(`e${r}`, 2 * r + 25, 2 * r + 25, (g) => {   // a dark moon over a gold sun, its corona
    const c = r + 12;
    for (let j = 0; j < 2 * c + 1; j++) for (let i = 0; i < 2 * c + 1; i++) {
      const d = Math.hypot(i - c, j - c), h = (i * 7 + j * 13) % 9;
      const col = d <= r - 1 ? "#05030a" : d <= r + .5 ? "#ffffff" : d <= r + 2 ? "#ffcf5a" : d <= r + 11 && h < 4 - (d - r) / 3 ? "#ffe08a" : null;
      if (col) { g.fillStyle = col; g.fillRect(i, j, 1, 1); }
    }
  });
  const marker = (r, locked) => canvas(`m${r}${locked}`, 2 * r + 3, r + 3, (g) => {    // where it will fall: a ring closing on you
    for (let a = 0; a < 48; a++) { if (a % 4 === 3) continue; const t = a / 48 * Math.PI * 2; g.fillStyle = locked ? "#e8484f" : a % 2 ? "#ffffff" : "#ffcf5a";
      g.fillRect(Math.round(r + 1 + Math.cos(t) * r), Math.round(r / 2 + 1 + Math.sin(t) * r / 2), 2, 1); }
  });

  // ---- in the land (HdFx.add): its entrance, its shadow in the sky, its body breaking into stars
  function hd(put, groundAt, now) {
    const at = (x, y, c, high, fade = 1) => put({canvas: c, fx: Math.floor(c.width / 2), fy: c.height + Math.round(high), x, y, z: groundAt(x, y), fade});
    for (const p of ents.values()) {
      if (!p.e || p.e.kind !== "nyxwing" || !IMG.nyxwing) continue;
      const e = p.e, s = st(e.id), cx = p.x + .5;
      if (e.act === "arrive") {
        const u = (now - (began(e) ?? now)) / BEAT, open = Math.min(1, Math.max(0, (u - 1) / 5)), q = Math.min(1, Math.max(0, (u - FALL_FROM) / (ARRIVE - FALL_FROM)));
        if (open > 0 && q < 1) at(cx + 4, p.y, eclipse(Math.max(3, Math.round(16 * open))), 7 * 16, 1 - q * q);
        if (u < FALL_FROM) continue;
        const k = 1 - q, ang = q * 2.6 * Math.PI, gx = cx + 4 * k * Math.cos(ang), gy = p.y + 2 * k * Math.sin(ang), high = 7 * 16 * k ** 1.25;
        const n = q < .3 ? 4 : q < .55 ? 3 : q < .8 ? 2 : 1, col = wildFrame(WILD.nyxwing.walk, now, true);
        at(gx, gy, oval(Math.max(4, Math.round(56 * q)), Math.max(2, Math.round(14 * q)), "#50408a"), 0, .45 * q);    // (see-through: a fade, HdFx's dither)
        at(gx, gy, speck(col, n), high);
        if (Math.random() < .2 + .6 * q) parts.push({x: gx + (Math.random() - .5) * 3 * q, y: gy - high / 16 - 2 * q, floor: gy, vx: (Math.random() - .5) * .6, vy: .4, g: 0, life: .7, age: 0, c: GOLD[Math.floor(Math.random() * 5)], s: 1});
      } else if (e.act === "sky") {
        const t = now - (s.upAt ?? now), left = SKY - t, locked = left < LOCK;
        at(cx, p.y, oval(56, 14, "#50408a"), 0, .5);
        at(cx, p.y, marker(Math.round(locked ? 24 : 32 + 6 * Math.sin(t / 120)), locked), 0);
        if (t < 400) at(cx, p.y, cell(WILD.nyxwing.dive[0] + 3, 0), t * 1.6);                    // up and away
        if (left < 160) at(cx, p.y, cell(WILD.nyxwing.dive[0] + 4, 0), left * 4);               // and down on you
        if (Math.random() < .6) parts.push({x: cx + (Math.random() - .5) * 2, y: p.y - 6, floor: p.y, vx: 0, vy: 14, g: 0, life: .4, age: 0, c: GOLD[Math.floor(Math.random() * 5)], s: 1});
      }
    }
    for (const [id, d] of dying) {                                           // its body, its pixels leaving it, and the sky taking them
      const u = (now - d.at) / BEAT;
      if (u > 7.5) { dying.delete(id); continue; }
      if (u < 6.5) at(d.x + .5, d.y, eclipse(16), 7 * 16, Math.min(1, u / 1.5) * Math.min(1, (6.5 - u) / .8));
      if (u < 2) at(d.x + .5 + (Math.random() - .5) * .2 * u, d.y, Math.floor(u * 6) % 2 ? d.white : d.body, 0);
      else if (d.left.length) {
        while (d.left.length && d.left[d.left.length - 1].rel <= u) {        // edges first, its heart last
          const q = d.left.pop();
          d.g.clearRect(q.i, q.j, 2, 2);
          const high = (WILD.nyxwing.ch - q.j - 8) / 16, t = 1.35;
          parts.push({x: d.x + .5 + (q.i - WILD.nyxwing.cw / 2) / 16, y: d.y - high, floor: d.y, vx: (-(q.i - WILD.nyxwing.cw / 2) / 16) / t, vy: -.5, g: -2 * (7 - high) / (t * t), life: t, age: 0, c: Math.random() < .35 ? "#ffffff" : q.c, s: 2});
        }
        at(d.x + .5, d.y, d.canvas, 0);
      }
    }
  }

  // ---- what it does, as the server says (boss.js hands its "boss" events here; world_decor.js its warnings; state.js its death)
  function windup(e) {
    const s = st(e.id);
    s.windAt = performance.now(); s.anim = e.move; s.crashAt = 0;
    if (e.move !== "rush") say("drake_scream", e);                           // its jaws open (the rush: its roar, at the strike)
    if (e.move === "breath") say("drake_charge", e);
  }
  function event(e) {
    const s = st(e.id), now = performance.now();
    if (e.what === "arrive") {
      came(e, now);
    } else if (e.what === "land") {
      say("drake_roar", e); say("drake_crash", e);
      blast(e, 1);
      floats.push({x: e.x, y: e.y - 4, text: "NYXWING", color: "#ffcf5a", t: now / 1000});
    } else if (e.what === "breath") {
      say("drake_breath", e);
      const [fx, fy] = e.dir || [0, 1];
      for (let k = 0; k < 10; k++) later(k * BEAT / 5, () => { for (let i = 0; i < 10; i++) { const sp = 6 + Math.random() * 5, side = (Math.random() - .5) * .9;
        parts.push({x: e.x + .5 + fx * 1.5, y: e.y + .5 + fy * 1.5 - 2.5, floor: e.y + fy * 1.5, vx: (fx + (fy ? side : 0)) * sp, vy: (fy + (fx ? side : 0)) * sp, g: 0, life: .45 + Math.random() * .15, age: 0, c: FIRE[Math.floor(Math.random() * 5)], s: 2 + (Math.random() < .4 ? 1 : 0)}); } });
    } else if (e.what === "ring") {
      if (!e.ring) say("drake_spin", e);
      say("drake_ring", e);
      for (let i = 0; i < 18; i++) { const t = (e.ring || 0) * Math.PI / 18 + i * Math.PI * 2 / 18;
        parts.push({x: e.x + .5, y: e.y + .5 - 3, floor: e.y + .5, vx: Math.cos(t) * 5.2, vy: Math.sin(t) * 5.2, g: 0, life: 1.5, age: 0, c: i % 2 ? "#ffffff" : "#ffcf5a", s: 3}); }
      burst(e.x, e.y - 3, "spark", 14, {up: 2, spread: 4, g: 2, life: .5});
    } else if (e.what === "sweep") {
      say("drake_whip", e);
      for (let i = 0; i < 40; i++) { const t = i / 40 * Math.PI * 2; parts.push({x: e.x + .5, y: e.y + .5, floor: e.y + .5, vx: Math.cos(t) * 9, vy: Math.sin(t) * 9, g: 0, life: .45, age: 0, c: GOLD[i % 5], s: 2}); }
    } else if (e.what === "roar") {
      say("drake_roar", e);
      burst(e.x, e.y - 3, "spark", 50, {up: 4, spread: 7, g: 3, life: 1.2});
    } else if (e.what === "up") {
      s.upAt = now;
      say("drake_screech", e);
      later(SKY - HIT.drake_fall, () => say("drake_fall", e));
      burst(e.x, e.y, "dust", 18, {up: 1.5, spread: 5, g: 3});
    } else if (e.what === "crash") {
      s.crashAt = now;
      say("drake_crash", e); say("drake_scream", e);
      blast(e, .7);
    } else if (e.what === "leave") {
      say("drake_screech", e);
      burst(e.x, e.y - 3, "spark", 40, {up: 6, spread: 3, g: -2, life: 1});
    }
  }
  function blast(e, k) {                                                      // a ring of light and dust thrown out on the ground
    for (let i = 0; i < 48; i++) { const t = i / 48 * Math.PI * 2; parts.push({x: e.x + .5, y: e.y + .5, floor: e.y + .5, vx: Math.cos(t) * 11 * k, vy: Math.sin(t) * 11 * k, g: 0, life: .6, age: 0, c: i % 3 ? GOLD[i % 5] : "#ffffff", s: 2}); }
    burst(e.x, e.y, "dust", Math.round(30 * k), {up: 1.5, spread: 8, g: 3});
    burst(e.x, e.y - 3, "spark", Math.round(60 * k), {up: 5, spread: 8, g: 4, life: 1.2});
  }
  // its death: a cry, two beats of its body shaking and flashing, then its pixels leave it, edges first, and go up into
  // an eclipse that opens over it; the sky closes when the last is home. (Its Eclipse Core falls as any drop does: loot.js)
  const dying = new Map();
  function died(e) {
    const s = st(e.id), L = s.last, A = WILD.nyxwing;
    say("drake_death", e);
    later(6 * BEAT - HIT.drake_dissolve, () => say("drake_dissolve", e));
    later(6 * BEAT, () => say("drake_vanish", e));
    seen.delete(e.id);
    if (!L || !IMG.nyxwing) return;
    const body = cell(L.col, L.row), c = document.createElement("canvas"); c.width = A.cw; c.height = A.ch;
    const g = c.getContext("2d", {willReadFrequently: true}); g.drawImage(body, 0, 0);
    const white = canvas(`w${L.col},${L.row}`, A.cw, A.ch, (w) => { w.drawImage(body, 0, 0); w.globalCompositeOperation = "source-atop"; w.fillStyle = "#fff8e8"; w.fillRect(0, 0, A.cw, A.ch); });
    const d = g.getImageData(0, 0, A.cw, A.ch).data, left = [];
    for (let j = 0; j < A.ch; j += 2) for (let i = 0; i < A.cw; i += 2) {
      const k = (j * A.cw + i) * 4;
      if (d[k + 3] < 200) continue;                                          // (not its ground shadow)
      const far = Math.min(1, Math.hypot((i - A.cw / 2) / (A.cw / 2), (j - A.ch * .55) / (A.ch / 2)));
      left.push({i, j, c: `rgb(${d[k]},${d[k + 1]},${d[k + 2]})`, rel: 2 + 2.2 * (1 - far) + Math.random() * .2});
    }
    left.sort((a, b) => b.rel - a.rel);                                      // (the soonest last: popped first)
    dying.set(e.id, {at: performance.now(), x: L.x, y: L.y, body, white, canvas: c, g, left});
  }
  // every beat, its wings (between its moves)
  setInterval(() => { for (const p of ents.values()) if (p.e && p.e.kind === "nyxwing" && !p.e.act) sfx("drake_flap", p.x, p.y, 20); }, BEAT);
  return {draw, hd, windup, event, died, owns, began};
})();
