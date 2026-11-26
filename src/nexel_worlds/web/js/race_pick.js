// Who you are, picked on the first screen (races.js draws each race).

// The first screen: pick who you are (title.js lays it out, css/title.css draws it). The choice is kept in this
// browser and sent with your name (agent.js).
// The first time, each race's picture is made in a turn of its own: a race's whole sheet is made for it, four of them
// in one go held a phone's first screen still for 0.4 s (the keys and the island's first frames waited behind it).
let myRace = localStorage.getItem("nexel-race") || "cat", racePickSeen = false;
function drawRacePick() {
  const row = $("racepick");
  if (!IMG.character || !IMG.character.complete || !IMG.character.width) return setTimeout(drawRacePick, 150);
  row.innerHTML = "";
  const later = !racePickSeen; racePickSeen = true;
  for (const [i, r] of Races.RACES.entries()) {
    const b = document.createElement("button");
    b.type = "button"; b.dataset.race = r.key; b.title = r.name; b.className = r.key === myRace ? "on" : "";
    const c = document.createElement("canvas"); c.width = c.height = 24;
    const g = c.getContext("2d"); g.imageSmoothingEnabled = false;
    const paint = () => { const s = typeof wornReady === "function" && wornReady("#f3f2c0", null, r.key, false); if (s) g.drawImage(s, 12, 10, 24, 24, 0, 0, 24, 24); else setTimeout(paint, 60); };   // (its sheet made between frames: wear.js)
    if (later && r.key !== myRace) setTimeout(paint, 40 * i); else paint();
    b.appendChild(c);
    b.onclick = () => pickRace(r.key);
    row.appendChild(b);
  }
}
function pickRace(key) { myRace = key; localStorage.setItem("nexel-race", myRace); drawRacePick(); }
(() => { const row = document.createElement("div"); row.id = "racepick"; $("raceslot").appendChild(row); drawRacePick(); })();
