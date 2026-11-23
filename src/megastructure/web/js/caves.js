// Caves (client). The land is cells (cells.js); a cave is empty cells under solid ones, and nothing more. In it you
// are seen through the HD look's x-ray window (hd.js). Here: the height you stand at.

// Your tile and the height you stand at, kept as the server keeps it (Movement.landing), once a frame
function trackMe() {
  if (Leap.on()) return;                                     // (in the air: leap.js keeps them)
  const me = ents.get("agent" + myId);
  if (me) {
    const x = Math.round(me.x), y = Math.round(me.y);        // (where you're seen, which runs ahead of the server's tile)
    if (!myAt || myAt.x !== x || myAt.y !== y) {
      let z = myAt && Math.abs(myAt.x - x) + Math.abs(myAt.y - y) === 1 ? landAt(myAt.z, x, y, myAt.x, myAt.y) : null;
      const told = me.e && me.e.z !== undefined ? me.e.z : meObs && meObs.self.z !== undefined ? meObs.self.z : 99;
      if (z === null) z = settleAt(x, y, told);              // (woken, moved: where the server has you)
      myWas = myAt; myAt = {x, y, z};
    } else myAt.z = settleAt(x, y, myAt.z);                  // (the ground dug from under you: down you come)
    // standing where the server has you: its height for you is the truth (yours can go stale: a fall you didn't see,
    // a respawn; you then couldn't step off a height you weren't on)
    if (me.e && me.e.z !== undefined && me.e.x === x && me.e.y === y && Math.abs(me.x - x) < .001 && Math.abs(me.y - y) < .001 && !pred) myAt.z = settleAt(x, y, me.e.z);
  }
}
