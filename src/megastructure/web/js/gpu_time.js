// The GPU's own ms a frame, for the debug screen (f3.js) and tools/phone_sim.py. Script ms say what the page asked
// for; a phone's GPU is slow at filling px, and that time is the GPU's: only its own clock tells it.
// Every WebGL 2 canvas the page makes is kept (the land's, the bodies', the one under ground): getContext is
// watched from the first script on. Each frame (F3.each: only while the debug screen is open) the query of
// every context opened at the last frame is closed and a new one opened, so one query holds one frame's work
// on that canvas; the frame's GPU ms are their sum, read when the GPU has them (a frame or three later).
// EXT_disjoint_timer_query_webgl2: Chrome on Android, Chrome on this Mac (Metal and SwiftShader); not Safari
// (iPhone): there "n/a". A result the GPU marks disjoint (its clock jumped) is dropped.
//   GpuTime.ms       the mean of the last half second, or null; GpuTime.ok: a context has the timer
//   GpuTime.take()   the frames' GPU ms since the last take (phone_sim.py), oldest first

const GpuTime = (() => {
  const all = [], got = [], recent = [];
  let ok = false, want = false, at = -1;
  const make = HTMLCanvasElement.prototype.getContext;
  HTMLCanvasElement.prototype.getContext = function (kind, ...a) {
    const gl = make.call(this, kind, ...a);
    if (gl && kind === "webgl2" && !all.some((c) => c.gl === gl)) all.push({gl, ext: undefined, open: null, wait: [], spare: [], res: []});
    return gl;
  };
  function each(c) {
    const gl = c.gl;
    if (c.ext === undefined) { c.ext = gl.getExtension("EXT_disjoint_timer_query_webgl2") || null; ok = ok || !!c.ext; }
    if (!c.ext || gl.isContextLost()) return false;
    if (c.open) { gl.endQuery(c.ext.TIME_ELAPSED_EXT); c.wait.push(c.open); c.open = null; }
    const jumped = gl.getParameter(c.ext.GPU_DISJOINT_EXT);
    while (c.wait.length && gl.getQueryParameter(c.wait[0], gl.QUERY_RESULT_AVAILABLE)) {
      const q = c.wait.shift(); c.res.push(jumped ? NaN : gl.getQueryParameter(q, gl.QUERY_RESULT) / 1e6); c.spare.push(q);
    }
    if (want && c.wait.length < 6) { c.open = c.spare.pop() || gl.createQuery(); gl.beginQuery(c.ext.TIME_ELAPSED_EXT, c.open); }
    return true;
  }
  // the n-th result of each context is the same frame (each opens one query a frame): a frame's ms is their sum
  function frame(now) {
    if (now === at) return;                                     // (once a frame, whoever asks: f3.js, phone_sim.py)
    at = now; want = true;
    const live = all.filter(each);
    while (live.length && live.every((c) => c.res.length)) {
      const ms = live.reduce((s, c) => s + c.res.shift(), 0);
      if (ms !== ms) continue;                                  // (NaN: disjoint)
      got.push(ms); recent.push([now, ms]);
    }
    while (recent.length && now - recent[0][0] > 500) recent.shift();
    if (got.length > 3000) got.splice(0, got.length - 3000);
  }
  function stop() { want = false; for (const c of all) if (c.open && c.ext && !c.gl.isContextLost()) { c.gl.endQuery(c.ext.TIME_ELAPSED_EXT); c.wait.push(c.open); c.open = null; } }
  return {frame, stop, take: () => got.splice(0, got.length), get ok() { return ok; }, get contexts() { return all.length; },
    get ms() { return recent.length ? recent.reduce((s, r) => s + r[1], 0) / recent.length : null; }};
})();
