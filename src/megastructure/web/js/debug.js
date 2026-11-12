// Debugging aids, typed in the chat line (Enter, or /):
//   /coords   where you are (X, Y and the height Z you stand at) and the tile you aim at, top right
//   /grid     every tile outlined where it is drawn (lifted with its ground), its height written in it; the borders
//             of the blocks the land comes in (32 tiles) in orange
// Each is on until typed again, and kept between visits. Any other /word is an action sent to the server, as before
// (/dig dir=N).

const DEBUG = {coords: localStorage.getItem("megastructure-coords") === "1", grid: localStorage.getItem("megastructure-grid") === "1"};
const COMMANDS = {
  coords: () => flip("coords", "Coordinates"),
  grid: () => flip("grid", "Grid"),
};
function flip(what, name) {
  DEBUG[what] = !DEBUG[what];
  localStorage.setItem("megastructure-" + what, DEBUG[what] ? "1" : "0");
  toast(`${name} ${DEBUG[what] ? "on" : "off"} (/${what})`);
}
// A /word typed in the chat line that is one of ours: done here. -> was it?
function localCommand(word) {
  const run = COMMANDS[String(word || "").toLowerCase()];
  if (run) run();
  return !!run;
}

// Where you are, top right (caves.js keeps your tile and height: myAt), and the tile you aim at with its height
let xyzText = "";
function showXYZ() {
  let t = "";
  if (DEBUG.coords && myAt) {
    const aim = me && aimedTile();
    t = `X ${myAt.x}  Y ${myAt.y}  Z ${myAt.z}` + (aim ? `   ·   aim ${aim.p.x}, ${aim.p.y}  z ${topAt(aim.p.x, aim.p.y)}` : "");
  }
  if (t !== xyzText) { xyzText = t; $("xyz").textContent = t; }
}

function drawGrid(sx, sy, S) {
  if (!DEBUG.grid) return;
  const [vx, vy, vw, vh] = viewRect(1), write = S >= 32;
  ctx.save();
  ctx.font = `${Math.max(9, Math.round(S / 3.4))}px SproutPixel`; ctx.textAlign = "left"; ctx.textBaseline = "top"; ctx.lineWidth = 1;
  for (let y = vy; y <= vy + vh + 6; y++) for (let x = vx; x <= vx + vw; x++) {   // (+6 rows south: high ground there is drawn up into view)
    if (!tile(x, y)) continue;
    const lv = standAt(x, y), X = Math.round(sx(x)), Y = Math.round(sy(y, x));
    ctx.strokeStyle = "rgba(255,255,255,.3)"; ctx.strokeRect(X + .5, Y + .5, S, S);
    ctx.fillStyle = "rgba(255,140,80,.85)";
    if (x % B === 0) ctx.fillRect(X, Y, 2, S);
    if (y % B === 0) ctx.fillRect(X, Y, S, 2);
    if (write && lv) { ctx.fillStyle = "rgba(40,28,36,.75)"; ctx.fillText(lv, X + 4, Y + 3); ctx.fillStyle = "#fff6e0"; ctx.fillText(lv, X + 3, Y + 2); }
  }
  ctx.restore();
}
