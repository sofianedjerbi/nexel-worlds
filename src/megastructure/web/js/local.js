// The demo build (GitHub Pages): no server to connect to, so the real Python server runs in this tab under Pyodide
// and the two sockets are in-page objects. The world is saved in IndexedDB, so it's still there after a reload.
// Only the Pages build loads this file (tools/build_pages.py); with a real server, openSocket() uses WebSockets.

const PYODIDE = "https://cdn.jsdelivr.net/pyodide/v314.0.7/full/";
const SAVES = "/saves";
let booted = null;

function bootLocal() {
  if (booted) return booted;
  booted = (async () => {
    const say = (t) => { const c = document.getElementById("clock"); if (c) c.textContent = t; };
    say("loading Python…");
    await new Promise((ok, fail) => {
      const s = document.createElement("script");
      s.src = PYODIDE + "pyodide.js"; s.onload = ok; s.onerror = () => fail(new Error("couldn't load Pyodide"));
      document.head.appendChild(s);
    });
    const py = await loadPyodide({indexURL: PYODIDE});
    say("loading the world…");
    const code = await fetch("py.zip").then((r) => r.arrayBuffer());
    py.unpackArchive(code, "zip", {extractDir: "/lib/game"});
    py.FS.mkdirTree(SAVES);
    py.FS.mount(py.FS.filesystems.IDBFS, {}, SAVES);
    const sync = (load) => new Promise((ok) => py.FS.syncfs(load, ok));
    await sync(true);
    py.runPython("import sys; sys.path.insert(0, '/lib/game')");
    const game = py.pyimport("megastructure.browser");
    game.start(SAVES);
    let saving = false;
    const save = async () => { if (saving) return; saving = true; game.save(); await sync(false); saving = false; };
    setInterval(save, 15000);
    window.saveWorld = save;
    addEventListener("pagehide", save);
    addEventListener("visibilitychange", () => document.visibilityState === "hidden" && save());
    return game;
  })();
  return booted;
}

// Looks enough like a WebSocket for state.js and agent.js: readyState, onopen/onmessage/onclose, send, close.
class LocalSocket {
  constructor(path) {
    this.readyState = 0;
    bootLocal().then((game) => {
      this.ws = game.connect(path, (raw) => this.onmessage && this.onmessage({data: raw}), () => this.closed());
      this.readyState = 1;
      if (this.onopen) this.onopen();
    }, (e) => { console.error(e); const c = document.getElementById("clock"); if (c) c.textContent = "couldn't start: " + e.message; });
  }
  send(raw) { if (this.readyState === 1) this.ws.push(raw); }
  close() { if (this.ws) this.ws.shut(); }
  closed() {
    if (this.readyState === 3) return;
    this.readyState = 3;
    if (this.onclose) this.onclose();
  }
}
