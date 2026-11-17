// The demo build (GitHub Pages): no server to connect to, so the real Python server runs in this tab, in a worker of
// its own (local_worker.js: the page only draws), and the two sockets are messages to it. The world is saved in
// IndexedDB, so it's still there after a reload.
// Only the Pages build has this file (tools/build_pages.py), written into the page itself, first: the world starts
// to come with the page, not once every script has (it is the longest wait of all: six megabytes of Python on a first
// visit), and what makes noise waits for it (audio.js: bootWait). With a real server, openSocket() uses WebSockets.

let booted = null, worker = null, localId = 0, bootDone = null;
window.bootWait = new Promise((ok) => { bootDone = ok; });      // (the world has come, or could not: what makes noise waits for it, audio.js)
const localSocks = new Map(), localSaves = new Map();

function bootLocal() {
  if (booted) return booted;
  document.body.classList.add("booting");                    // (the first screen says so: title.css, title.js)
  booted = new Promise((ok, fail) => {
    worker = new Worker("js/local_worker.js", {type: "module"});
    worker.onerror = (e) => fail(new Error(e.message || "the world couldn't start"));
    worker.onmessage = (e) => {
      const m = e.data, s = localSocks.get(m.id);
      if (m.t === "say") { const c = document.getElementById("clock"); if (c) c.textContent = m.text; }
      else if (m.t === "ready") ok();
      else if (m.t === "error") fail(new Error(m.message));
      else if (m.t === "msg") { if (s && s.onmessage) s.onmessage({data: m.raw}); }
      else if (m.t === "closed") { if (s) s.closed(); }
      else if (m.t === "saved") { const done = localSaves.get(m.id); localSaves.delete(m.id); if (done) done(); }
    };
  });
  booted.then(() => {
    const save = () => new Promise((ok) => { const id = ++localId; localSaves.set(id, ok); worker.postMessage({t: "save", id}); });
    window.saveWorld = save;                         // (the worker also saves every 15 s)
    addEventListener("pagehide", save);
    addEventListener("visibilitychange", () => document.visibilityState === "hidden" && save());
  }, () => {});
  const done = () => { document.body.classList.remove("booting"); if (typeof titleDraw === "function") titleDraw(); };
  booted.then(done, done).then(bootDone);
  return booted;
}

// Looks enough like a WebSocket for state.js and agent.js: readyState, onopen/onmessage/onclose, send, close.
class LocalSocket {
  constructor(path) {
    this.readyState = 0; this.id = ++localId;
    bootLocal().then(() => {
      localSocks.set(this.id, this);
      worker.postMessage({t: "open", id: this.id, path});
      this.readyState = 1;
      if (this.onopen) this.onopen();
    }, (e) => { console.error(e); const c = document.getElementById("clock"); if (c) c.textContent = "couldn't start: " + e.message; });
  }
  send(raw) { if (this.readyState === 1) worker.postMessage({t: "msg", id: this.id, raw}); }
  close() { if (this.readyState === 1) worker.postMessage({t: "close", id: this.id}); }
  closed() {
    if (this.readyState === 3) return;
    this.readyState = 3; localSocks.delete(this.id);
    if (this.onclose) this.onclose();
  }
}
// At once, with the page (measured as a phone on a first visit, 9 Mbit/s: in the world after 8.6 s, not 15.5). But not
// on a line the browser says is slow: there the page's own scripts and pictures go first, and the world starts when
// the first socket is asked for (state.js), as it did (at 1.6 Mbit/s the menu answered a second later, the island
// came three seconds later).
(() => { const c = navigator.connection; if (!c || !(c.saveData || /2g|3g/.test(c.effectiveType || "") || c.downlink < 5)) bootLocal(); })();
