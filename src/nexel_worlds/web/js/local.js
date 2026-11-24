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
      else if (m.t === "progress") bootShow(m.p);
      else if (m.t === "ready") { window.bootTook = m.took; m.took.page = Math.round(performance.now()); ok(); }      // (ms of each step of the start, and when the page heard)
      else if (m.t === "error") fail(new Error(m.message));
      else if (m.t === "msg") { if (s && s.onmessage) s.onmessage({data: m.raw}); }
      else if (m.t === "closed") { if (s) s.closed(); }
      else if (m.t === "modules") { window.worldModules = m.names; }
      else if (m.t === "saved") { const done = localSaves.get(m.id); localSaves.delete(m.id); if (done) done(); }
    };
  });
  booted.then(() => {
    const save = () => new Promise((ok) => { const id = ++localId; localSaves.set(id, ok); worker.postMessage({t: "save", id}); });
    window.saveWorld = save;                         // (the worker also saves every 15 s)
    addEventListener("pagehide", save);
    addEventListener("visibilitychange", () => document.visibilityState === "hidden" && save());
  }, () => {});
  booted.then(keepForNextTime, () => {});
  const done = () => { document.body.classList.remove("booting"); if (typeof titleDraw === "function") titleDraw(); };
  booted.then(done, done).then(bootDone);
  return booted;
}

// How far the world is (local_worker.js: 0 to 1): the strip at the foot of Wake up is that long (title.css), in whole
// pixels of the window's art. It was a strip that ran from left to right for as long as it took, saying nothing.
let bootAt = 0;
function bootShow(p) {
  bootAt = Math.max(bootAt, p);
  const j = document.getElementById("join"), q = parseFloat(getComputedStyle(document.documentElement).getPropertyValue("--q")) || 1;
  if (j) j.style.setProperty("--boot-w", Math.floor(bootAt * j.clientWidth / q) * q + "px");
}
addEventListener("DOMContentLoaded", () => bootShow(bootAt));       // (said before the button was there)
// The next visit: a service worker (sw.js, written by the build with the build's own mark) keeps the page, its script,
// its pictures, Python and the game: the first screen at once, the world in a second or two, with no line at all.
// Asked for once the world has come: everything it keeps is then in the browser's own store, nothing is fetched twice.
// A newer build: the worker takes over as soon as it has it all, and a page still at the first screen starts again
// on it by itself (a page in the world plays on: its next load is the new build).
function keepForNextTime() {
  const sw = navigator.serviceWorker;
  if (!sw || !window.SW_FILE) return;
  const had = !!sw.controller;
  window.swAsked = true;
  sw.addEventListener("controllerchange", () => { if (had && document.body.classList.contains("title")) location.reload(); });
  sw.register(window.SW_FILE).then(() => sw.ready).then(() => { window.swReady = true; }).catch(() => {});
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
// on a line the browser says is slow: there the page's own script and pictures go first (at 1.6 Mbit/s the menu
// answered a second later, the island came three seconds later), and the world starts as soon as the last of them has
// arrived (the pack of pictures, asked for in the page's head: web_bundle.py). It waited for the first socket
// (state.js): every picture decoded and the island made, 1.5 to 2.5 s of a phone's work with nothing on the line.
// On any line now, the first screen's own bytes go first (ASSET_PACK.need: the pictures it shows; the ones it never
// shows, the wild ones and the emotes, come with the world): Python's 1.5 MB shared the line with the title's pictures.
(() => { const P = window.ASSET_PACK; if (!P) bootLocal(); else (P.upto ? P.upto(P.need) : P.blob).then(bootLocal); })();
