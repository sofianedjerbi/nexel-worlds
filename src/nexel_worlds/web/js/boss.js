// Old Mossback, the first boss (sim/boss.py): what its events sound and look like, and the fight's music.

const BOSS_SOUND = {wake: "boss_wake", stomp: "boss_stomp", snap: "boss_snap", shake: "boss_shake", land: "sporeling_land", puff: "spore_puff"};
function bossEvent(e) {
  if (Nyx.owns(e)) return Nyx.event(e);                                     // Nyxwing's: nyxwing.js
  if (BOSS_SOUND[e.what]) sfx(BOSS_SOUND[e.what], e.x, e.y, e.what === "land" || e.what === "puff" ? 0 : 20);     // the boss carries further
  if (e.what === "stomp") for (const dx of [-3, -2, 2, 3]) burst(e.x + dx, e.y, "dust", 7, {up: 1.5, spread: 3, g: 3});
  if (e.what === "wake") for (const dx of [-1, 0, 1]) burst(e.x + dx, e.y, "dust", 6, {up: 1, spread: 2, g: 3});
  if (e.what === "shake") burst(e.x, e.y - 2, "H", 14, {up: 2, spread: 5, g: 4, life: .9});
  if (e.what === "puff") burst(e.x, e.y, "dust", 8, {up: 1, spread: 3, g: 1, life: .7});
}
// A fight's loop plays while a boss is in view: Old Mossback's while it is awake, Sugar rush while Nyxwing is here (from
// its entrance, whose landing is the song's drop: audio.js bossMusic).
setInterval(() => {
  const here = (k, f) => [...ents.values()].some((q) => q.e && q.e.kind === k && f(q.e)), nyx = [...ents.values()].find((q) => q.e && q.e.kind === "nyxwing");
  if (nyx) bossMusic("nyxwing", Nyx.began(nyx.e));                          // (from where the fight is: you may have come late)
  else bossMusic(here("mossback", (e) => e.act !== "sleep") ? "boss" : false);
}, 500);
