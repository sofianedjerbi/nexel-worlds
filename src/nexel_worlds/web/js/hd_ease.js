// The HD look (hd.js): what the x-ray window takes out of the picture goes, and comes back, over 120 ms (the painter draws
// that much of it, a 2x2 dither in whole art px, vox_style_glsl.js SF): the plants on the land over your room, a tree over it.
// (Not there one frame and gone the next when the window opens on their tile: a pop on every stair.)
//   HdEase.frame(now): once a frame, before the things are asked
//   HdEase.of(key, on) -> 0..1: how much of the thing named key is drawn this frame; on: it is wanted whole
// A thing first met while it is not wanted starts at 0: nothing fades out that was never seen.
const HdEase = (() => {
  const T = 120, part = new Map(); let was = new Set(), cur = new Set(), last = 0, dt = 0;
  function frame(now) { was = cur; cur = new Set(); dt = Math.max(0, Math.min(100, now - last)) / T; last = now; if (part.size > 600) part.clear(); }
  function of(key, on) {
    let a = part.get(key);
    if (a === undefined) { if (on) { cur.add(key); return 1; } a = was.has(key) ? 1 : 0; }
    a = Math.max(0, Math.min(1, a + (on ? dt : -dt)));
    if (a >= 1) { part.delete(key); cur.add(key); return 1; }
    part.set(key, a); return a;
  }
  return {frame, of, T};
})();
