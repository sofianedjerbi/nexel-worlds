// Bridges and piers (ground ":"): where one runs, for the land it runs onto and for its model.
// A bridge has ONE paint: its model's, a deck of planks on posts cut from the pack's sheet (bridge_model.js). (It had a second: the
// pack's planks and end pieces laid flat on its tile under the model, lay: under the deck and the water, a paint nobody saw kept in step by hand.)
// Its tile is water (water.js: there is water under every bridge); the land a bridge runs onto goes on to it with no shore
// between (rests: only at its ends, along the way it runs; beside it the bank is a bank).
const Bridge = {
  // it runs east and west (if not: north and south)
  ew(x, y) { return [-1, 1].some((d) => { const q = gndAt(x + d, y); return q === ":" || isLand(q); }); },
  // seen from the land at (x, y): is the tile at (tx, ty) beside it a bridge that runs onto it?
  rests(x, y, tx, ty) { return gndAt(tx, ty) === ":" && (ty === y ? tx !== x && Bridge.ew(tx, ty) : tx === x && !Bridge.ew(tx, ty)); },
};
