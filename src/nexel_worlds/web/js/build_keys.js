// Build mode's keys (build.js): the arrows move the cursor (held: at its own pace), and the mode's other keys.
//   BuildKeys(S, K) -> {move, held, onKey}
const BuildKeys = (S, K) => {
  const {REACH, FIRST_MS, STEP_MS} = K;
  const drop = (...a) => K.drop(...a), lift = (...a) => K.lift(...a), plan = (...a) => K.plan(...a), take = (...a) => K.take(...a), todo = (...a) => K.todo(...a), toggle = (...a) => K.toggle(...a);   // (another part's, looked up when called: build.js K)
  function move(dir) {
    const s = myPos(), [dx, dy] = DIRV[dir], x = S.at.x + dx, y = S.at.y + dy;
    if (!s || !tile(x, y) || Math.max(Math.abs(x - s.x), Math.abs(y - s.y)) > REACH) { sfx("buzz"); return false; }      // (as far as it goes: said, not silent)
    S.at = {x, y};
    if (S.hold === " ") plan(S.at); else if (S.hold === "x") take(S.at);
    return true;
  }
  // An arrow held: a step at once, then, after a short wait, at the cursor's own pace (not the keyboard's repeat,
  // which starts late and differs from one machine to the next)
  function held(dir) {
    clearTimeout(S.timer); S.dir = dir;
    if (!dir) return;
    move(dir);
    const again = () => { if (S.on && S.dir === dir && move(dir)) S.timer = setTimeout(again, STEP_MS); };
    S.timer = setTimeout(again, FIRST_MS);
  }
  // A key in build mode -> true when the mode takes it (the rest, the bar's numbers among them, go on as ever)
  function onKey(k, e) {
    if (!S.on) return false;
    if (k === "b" || k === keyOf("build")) { if (!e.repeat) toggle(false); return true; }
    if (k === "escape") { if (!e.repeat) { if (todo().length) drop(); else toggle(false); } return true; }
    if (KEYDIR[k]) { if (!e.repeat) held(KEYDIR[k]); return true; }
    if (k === " " || k === "x") { if (!e.repeat) { S.hold = k; S.row = undefined; if (k === " ") plan(S.at); else take(S.at); } return true; }
    if (k === "e" || k === "keyq" || k === "q" || k === "pageup" || k === "pagedown") { if (!e.repeat) lift(k === "e" || k === "pageup" ? 1 : -1); return true; }
    return false;
  }
  addEventListener("keyup", (e) => { const k = keyId(e); if (k === S.hold) S.hold = null; if (KEYDIR[k] === S.dir) held(null); });
  addEventListener("blur", () => { S.hold = null; held(null); });
  return {move, held, onKey};
};
