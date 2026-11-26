// Nyxwing's body on the creature's own canvas (nyxwing.js, drawWild): its frame of the sheet, by what it does.
//   NyxBody(K) -> {frame, draw}
const NyxBody = (K) => {
  const {BEAT, WARN, ATTACKS, began, st} = K;
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
    if (e.act === "arrive") { began(e, now); return; }                       // coming down: drawn in the land (hd), timed from when it came
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
  return {frame, draw};
};
