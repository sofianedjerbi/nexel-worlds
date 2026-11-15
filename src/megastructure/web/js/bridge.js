// Bridges and piers: planks over water (ground ":").
// Every tile of one was the same plain planks, and two things went wrong at its ends. The land it ran onto was
// painted as a shore towards it, and a shore's edge has a see-through px along it with water behind: but there was
// no water behind (water is painted under water and round it, and a bridge was not water), so the dark behind the
// world showed: a black bar at each end. And a bridge ended like a cut plank.
// Now: there is water under every bridge (water.js); the land a bridge runs onto goes on to it with no shore
// between (rests: only at its ends, along the way it runs; beside it the bank is a bank); and its two ends are the
// pack's end pieces, with their posts: on land over the planks, which run on to the bank; out in the water (a
// pier's end) the ones whose posts stand in foam.
const Bridge = {
  // it runs east and west (if not: north and south)
  ew(x, y) { return [-1, 1].some((d) => { const q = gndAt(x + d, y); return q === ":" || isLand(q); }); },
  // seen from the land at (x, y): is the tile at (tx, ty) beside it a bridge that runs onto it?
  rests(x, y, tx, ty) { return gndAt(tx, ty) === ":" && (ty === y ? tx !== x && Bridge.ew(tx, ty) : tx === x && !Bridge.ew(tx, ty)); },
  // the sheet's cells for the bridge tile (x, y), laid on g
  lay(g, x, y, ox, oy) {
    const ew = Bridge.ew(x, y), at = (k) => (ew ? gndAt(x + k, y) : gndAt(x, y + k)), back = at(-1) === ":", on = at(1) === ":";
    const dry = isLand(at(back ? 1 : -1));           // (at an end: what is past it)
    if (back === on || dry) g.drawImage(IMG.bridge, ew ? 0 : 32, 32, 16, 16, ox, oy, 16, 16);      // planks
    if (back !== on) g.drawImage(IMG.bridge, ew ? (back ? 16 : 0) : (dry ? 32 : 48), ew ? (dry ? 0 : 16) : (back ? 16 : 0), 16, 16, ox, oy, 16, 16);
  },
};
