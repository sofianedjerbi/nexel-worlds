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
// (drawn a task on, once this script has run: loaded as one script of a few parts (web_bundle.py), wear.js can be in this part, its
//  wornReady declared and not yet made, and typeof on it throws. With the pictures already kept, a reload painted at once here, and the
//  throw stopped the rest of the part: no title, no land. A task on, wornReady is made, or not declared yet and paint asks again)
(() => { const row = document.createElement("div"); row.id = "racepick"; $("raceslot").appendChild(row); setTimeout(drawRacePick); })();
