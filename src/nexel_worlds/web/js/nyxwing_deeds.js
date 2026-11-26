// What Nyxwing does, as the server says (nyxwing.js): its wind-ups, its attacks and their sounds on the beat, a blast.
//   NyxDeeds(K) -> {windup, event, blast}
const NyxDeeds = (K) => {
  const {BEAT, FIRE, GOLD, HIT, SKY, came, later, say, st} = K;
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
  return {windup, event, blast};
};
