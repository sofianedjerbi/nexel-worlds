// Touch: the game on a phone. Only on touch screens (body.touch); the keyboard and mouse play stays as it was.
//   Left thumb: a joystick wherever it lands on the left of the screen (pushed far, you sprint).
//   Right thumb: the main button (E: act on what you face, or eat, wear what you hold; held it keeps going) and the
//   other one (X), each labelled with what it will do right now; jump and pick up show up when you can. Items (the inventory), craft, talk and the menu at the top.
//   Two fingers on the world pinch to zoom; a tap on a tile is a click (as with a mouse), on the stick's side too.

const TOUCH = matchMedia("(pointer: coarse)").matches || "ontouchstart" in window || new URLSearchParams(location.search).has("touch");
const STICK_DEAD = 12, STICK_RUN = 64;       // CSS px from where the thumb landed: below this nothing, beyond it sprint
let stick = null;                             // {id, x, y, dir}

function touchUI() {
  const el = (tag, id, html, parent = document.body) => { const e = document.createElement(tag); e.id = id; e.innerHTML = html; parent.appendChild(e); return e; };
  el("div", "pad", '<div id="stickbase"></div><div id="stickknob"></div>');
  const btns = el("div", "tbtns", "");
  for (const [id, label] of [["tA", "A"], ["tB", "B"]]) el("div", id, `<span class="cap"></span><span class="lbl">${label}</span>`, btns);
  const ctx_ = el("div", "tctx", "");
  // (the column stands on its foot (style.css #tctx: bottom): what is always there is at the foot, what comes and goes with the land (a step ahead, a hole, a thing on the ground) over it:
  // a button that comes never moves one that is there under the thumb. Jump, Dig and Pick were under Build: entering build mode by a step, Jump came 180 ms later where Build was, Build 52 px up: "Done" tapped was a jump)
  el("div", "tJump", "Jump", ctx_); el("div", "tDig", "Dig up", ctx_); el("div", "tPick", "Pick up", ctx_);
  el("div", "tUp", "Up", ctx_); el("div", "tDown", "Down", ctx_); el("div", "tBuild", "Build", ctx_);   // (build mode, build.js: a phone had no way into it, nor a layer up or down)
  const top = el("div", "ttop", "");
  el("div", "tBag", "Items", top); el("div", "tCraft", "Craft", top); el("div", "tTalk", "Talk", top); el("div", "tMenu", "Menu", top);   // (Menu: the settings, leaving: a phone has no Esc, and had no way to them once in the world)
  return {btns, ctx_};
}

// A disc cut in art px, n across: a dark rim, a face, a lighter px up and left, a lip under it (ring: only the rim, a
// faint face: the stick's base). The page shows it at three screen px an art px: no round thing is drawn smooth.
function padDisc(n, face, ring) {
  const c = document.createElement("canvas"), g = c.getContext("2d"), lip = ring ? 0 : 2, r = n / 2, R = r - lip / 2; c.width = n; c.height = n;
  const far = (x, y, cy) => Math.hypot(x + .5 - r, y + .5 - cy);
  for (let y = 0; y < n; y++) for (let x = 0; x < n; x++) {
    const d = far(x, y, R), core = d <= R - 1;
    if (d > R && far(x, y, R + lip) > R) continue;
    g.fillStyle = ring ? (core ? "rgba(40,28,24,.22)" : "rgba(255,248,232,.6)") : !core ? "#5b3f36" : d > R - 2 && x + y < n - lip ? "#fff8e6" : face;
    g.fillRect(x, y, 1, 1);
  }
  return `url(${c.toDataURL()})`;
}
const PAD_KEY = {N: "arrowup", S: "arrowdown", W: "arrowleft", E: "arrowright"};
let padDir = null;                            // (build mode: the way the cursor is being pushed)
function setDir(dir, run) {
  if (Build.on || padDir) {                   // build mode: the stick moves the cursor, as the arrows do (build.js)
    const to = Build.on ? dir : null;
    if (to !== padDir) { if (padDir) dispatchEvent(new KeyboardEvent("keyup", {key: PAD_KEY[padDir]})); padDir = to; if (to) Build.onKey(PAD_KEY[to], {}); }
    if (Build.on) return;
  }
  for (const k of ["arrowup", "arrowdown", "arrowleft", "arrowright"]) keys.delete(k);
  if (dir) keys.add({N: "arrowup", S: "arrowdown", W: "arrowleft", E: "arrowright"}[dir]);
  runKey = !!run;
  syncWalk();
}

// A button here acts when the finger lands (no wait for it to lift). The click the browser sends after that same touch
// belongs to the button: it went to whatever had come up under the finger (held upright, the inventory's and the
// book's "x" open right under Items and Craft: they opened and shut on one tap). That one click is taken out.
let tapEat = null;                            // {id: the pointer that pressed a button, until: once lifted, its click is due before this}
addEventListener("pointerup", (e) => { if (tapEat && e.pointerId === tapEat.id) tapEat.until = performance.now() + 120; }, true);
addEventListener("pointercancel", (e) => { if (tapEat && e.pointerId === tapEat.id) tapEat = null; }, true);
addEventListener("click", (e) => { const t = tapEat; if (!t || !t.until) return; tapEat = null; if (performance.now() < t.until) { e.stopPropagation(); e.preventDefault(); } }, true);
function holdButton(e, fn) {                  // a press acts at once; held, it acts again once done (chopping on)
  let t = null;
  e.addEventListener("pointerdown", (ev) => {
    ev.preventDefault(); e.setPointerCapture(ev.pointerId); e.classList.add("down"); tapEat = {id: ev.pointerId, until: 0};
    inputMode = "keys"; fn(false); clearInterval(t);
    t = setInterval(() => { if (!myAction && !pendingAct) fn(true); }, 220);   // (never cutting short work in progress)
  });
  const up = () => { clearInterval(t); t = null; e.classList.remove("down"); };
  for (const ev of ["pointerup", "pointercancel", "lostpointercapture"]) e.addEventListener(ev, up);
}
function tapButton(e, fn) {
  e.addEventListener("pointerdown", (ev) => { ev.preventDefault(); ev.stopPropagation(); e.classList.add("down"); tapEat = {id: ev.pointerId, until: 0}; fn(); });
  for (const ev of ["pointerup", "pointercancel", "pointerleave"]) e.addEventListener(ev, () => e.classList.remove("down"));
}

if (TOUCH) {
  document.body.classList.add("touch"); hudTall = .26;       // (the HUD: a quarter of the height at most, ui.js)
  if (Math.min(innerWidth, innerHeight) < 520 && !new URLSearchParams(location.search).get("zoom") && !localStorage.getItem("megastructure-zoom")) zoom = 2;
  const {btns} = touchUI(), pad = $("pad"), base = $("stickbase"), knob = $("stickknob");

  // Two fingers on the world pinch. One of them often lands on the stick's side (it is the left of the screen, most of
  // a phone held upright: that pinch walked you away and did not zoom): two fingers down within 0.3 s of each other,
  // the stick not yet pushed, are a pinch, and the stick stays out of it.
  const fingers = new Map(), PINCH_MS = 300; let pinch = null, worldAt = -1e9;
  const pinched = (e) => {
    if (!fingers.has(e.pointerId)) return;
    fingers.set(e.pointerId, e);
    if (fingers.size !== 2) { pinch = null; return; }
    const [a, b] = [...fingers.values()], d = Math.hypot(a.clientX - b.clientX, a.clientY - b.clientY);
    if (!pinch) pinch = d;
    else if (d / pinch > 1.35 || d / pinch < 1 / 1.35) { zoomBy(d > pinch ? 1 : -1); pinch = d; }
  };
  pad.addEventListener("pointerdown", (e) => {
    if (!me || stick) return;
    e.preventDefault(); pad.setPointerCapture(e.pointerId);
    stick = {id: e.pointerId, x: e.clientX, y: e.clientY, dir: null, t: performance.now(), pinch: fingers.size === 1 && performance.now() - worldAt < PINCH_MS};
    if (stick.pinch) { fingers.set(e.pointerId, e); return; }
    base.style.left = knob.style.left = e.clientX + "px"; base.style.top = knob.style.top = e.clientY + "px";
    pad.classList.add("on"); inputMode = "keys";
  });
  pad.addEventListener("pointermove", (e) => {
    if (!stick || e.pointerId !== stick.id) return;
    if (stick.pinch) return pinched(e);
    let dx = e.clientX - stick.x, dy = e.clientY - stick.y;
    const d = Math.hypot(dx, dy), max = STICK_RUN + 10;
    if (d > max) { dx *= max / d; dy *= max / d; }
    knob.style.left = stick.x + dx + "px"; knob.style.top = stick.y + dy + "px";
    // four ways: the bigger axis wins, with a little stickiness so a thumb on the diagonal doesn't flicker
    let dir = null;
    if (d > STICK_DEAD) {
      const h = Math.abs(dx) > Math.abs(dy) * (stick.dir === "N" || stick.dir === "S" ? 1.3 : 1 / 1.3);
      dir = h ? (dx > 0 ? "E" : "W") : (dy > 0 ? "S" : "N");
    }
    const run = d > (runKey ? STICK_RUN - 14 : STICK_RUN);     // (sticky: a thumb resting on the line doesn't flick between the two)
    if (dir) stick.went = true;
    if (dir !== stick.dir || run !== runKey) { stick.dir = dir; setDir(dir, run); }
  });
  const release = (e) => {
    if (!stick || e.pointerId !== stick.id) return;
    const s = stick; stick = null; pad.classList.remove("on"); setDir(null, false); fingers.delete(e.pointerId); pinch = null;
    // a short touch that pushed nothing: a tap on the tile under it, as anywhere else on the world (the stick's side is
    // the left of the screen: held upright, no tile left of you could be tapped)
    if (me && e.type === "pointerup" && !s.pinch && !s.went && performance.now() - s.t < 350) { const q = tileAtScreen(s.x, s.y); if (!q) { /* (the sky: nothing) */ } else if (Build.on) Build.click(q, false); else clickTile(q, "tap"); }      // (a tap: what A does there, else what B does: intent.js clickIntent)
  };
  for (const ev of ["pointerup", "pointercancel"]) pad.addEventListener(ev, release);

  // (build mode: A held while the stick moves the cursor is a row, as Space held is: it was a tap a block. Held still it places once: a second one would go on top of the first)
  holdButton($("tA"), (again) => { if (!me) return; if (!Build.on) useFacing(false, again); else if (!again) { Build.click(Build.S.at, false); Build.S.hold = " "; } });
  for (const ev of ["pointerup", "pointercancel"]) $("tA").addEventListener(ev, () => { if (Build.S.hold === " ") Build.S.hold = null; });
  holdButton($("tB"), () => { if (!me) return; if (Build.on) Build.click(Build.S.at, true); else useFacing(true); });
  tapButton($("tBuild"), () => Build.toggle()); tapButton($("tUp"), () => Build.onKey("e", {})); tapButton($("tDown"), () => Build.onKey("q", {}));
  $("tA").style.backgroundImage = padDisc(28, "#f7e7c6"); $("tB").style.backgroundImage = padDisc(22, "#e3d3b8"); knob.style.backgroundImage = padDisc(20, "#f7e7c6"); base.style.backgroundImage = padDisc(50, "", true);
  $("craftfind").placeholder = "Search"; $("say").placeholder = "Say something…";                     // (no Enter, no Esc: the keyboard's own key sends, a tap elsewhere gives up)
  for (const ev of ["gesturestart", "dblclick"]) document.addEventListener(ev, (e) => e.preventDefault(), {passive: false});   // (no pinch or double tap of the page itself)
  document.addEventListener("contextmenu", (e) => { if (!/^(INPUT|TEXTAREA)$/.test(e.target.tagName)) e.preventDefault(); });      // (a long press: no menu of the browser's)
  holdButton($("tDig"), () => DigUp.run());      // (digup.js: the way out of a hole)
  tapButton($("tPick"), () => act("pick_up", {}));
  tapButton($("tJump"), () => jumpKey());                  // (walk.js: up the step in front; shown when there is one, held stick and all)
  tapButton($("tBag"), () => toggleBag());
  // (on its side Talk and Menu stand beside the goals, phone.css: where the goals end, known as soon as they are laid out: measured five times a second, Menu moved under the finger that was coming down on it)
  const beside = () => { const r = Math.round($("goalhint").getBoundingClientRect().right); if (r > 0) document.body.style.setProperty("--goalsr", r + "px"); };      // (the goals shut, a window open over them: they stay where they were)
  new ResizeObserver(beside).observe($("goalhint"));
  tapButton($("tCraft"), () => toggleCraft());
  tapButton($("tTalk"), () => openChat());
  tapButton($("tMenu"), () => openMenu());

  cv.addEventListener("pointerdown", (e) => {
    if (e.pointerType !== "touch") return;
    fingers.set(e.pointerId, e); worldAt = performance.now();
    if (stick && !stick.pinch && !stick.dir && worldAt - stick.t < PINCH_MS) { stick.pinch = true; pad.classList.remove("on"); fingers.set(stick.id, {clientX: stick.x, clientY: stick.y}); }
  });
  cv.addEventListener("pointermove", pinched);
  for (const ev of ["pointerup", "pointercancel"]) cv.addEventListener(ev, (e) => { fingers.delete(e.pointerId); pinch = null; });

  // The buttons say what they'll do, and the HUD fits the screen (the controls go above it when it's narrow)
  let sig = "";
  setInterval(() => {
    if (!me) return;
    const rows = availableActions(), get = (k) => rows.find((r) => r[0] === k);
    const a = Build.on ? rows[1] : get(capOf("use")), b = get(Build.on ? "X" : capOf("alt")), up = !Build.on && rows.find((r) => r[0] === capOf("up") && r[3]), bd = true, s = [a && a[1], a && a[2], b && b[1], up && up[1], !!get(capOf("pick")), Build.on, !!bd, !!get(capOf("jump"))].join("|");
    if (s !== sig) {
      sig = s;
      $("tA").querySelector(".cap").textContent = a ? a[1] : "";
      $("tA").classList.toggle("bad", !!(a && a[2])); $("tA").classList.toggle("idle", !a);
      $("tB").querySelector(".cap").textContent = b ? b[1] : "";
      $("tB").classList.toggle("idle", !b);
      $("tDig").style.display = up ? "flex" : "none"; $("tDig").textContent = up ? up[1] : "Dig up";
      $("tPick").style.display = get(capOf("pick")) ? "flex" : "none"; $("tJump").style.display = get(capOf("jump")) ? "flex" : "none";
      $("tBuild").style.display = bd ? "flex" : "none"; $("tBuild").textContent = Build.on ? "Done" : "Build"; $("tUp").style.display = $("tDown").style.display = Build.on ? "flex" : "none";
    }
    if (hudFit()) return;                                      // (the bar's pixel changed: measured at the next turn)
    const hud = $("hud"), w = Math.max(hud.scrollWidth, $("vitals").scrollWidth), h = hud.offsetHeight;
    const k = Math.min(1, (innerWidth - 16) / (w || 1));       // (the vitals alone too wide: a very narrow screen)
    hud.style.transform = k < 1 ? `translateX(${(innerWidth - w * k) / 2}px) scale(${k})` : "";   // (wider than the screen, it starts at its left)
    const narrow = !hudSide && innerWidth - w * k < 2 * 190;               // no room for the thumbs beside the hotbar
    document.body.style.setProperty("--tbot", (narrow ? h * k + 18 : 12) + "px");
  }, 200);
}
