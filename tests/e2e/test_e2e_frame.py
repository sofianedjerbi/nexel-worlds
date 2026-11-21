"""What a frame costs, on a phone above all: how much of the screen it paints, how much memory it makes for the
collector to take back, and what it works out again that has not changed. What is kept from one frame to the next
must be what would be worked out afresh."""

import pytest
DRAWN = "dirtyTiles.length === 0"

# what is kept against the same worked out now: the hint for the tile you face -> [how many differ, how many asked]
KEPT = """() => { const say = (f) => (f ? JSON.stringify([f.p, f.it.text, f.it.ok, !!f.it.info]) : 'null'); let bad = 0, n = 0;
  for (const alt of [false, true]) { n++; if (say(facingIntent(alt)) !== say(facingNow(alt))) bad++; }
  return [bad, n, say(facingNow(false))]; }"""

def test_what_is_kept_from_frame_to_frame_is_what_would_be_worked_out_now(game):
    """The hint for the tile you face was worked out three times a frame. It is kept until what it is worked out
    from changes: the land, your place, the way you face, what you hold, a tick of the world."""
    def same(why):
        bad, n, said = game.js(KEPT)
        assert bad == 0 and n == 2, (why, bad, n, said)
        return said
    same("as you wake")
    game.give(pickaxe=1); game.hold_item("pickaxe"); game.face(0, 1); game.sleep(300)
    first = same("a pickaxe in hand")
    game.stamp(-3, 1, ["......."] * 3, levels=["3333333"] * 3)              # a hill comes up in front of you
    game.wait(DRAWN, 8000); game.sleep(400)
    assert same("the land changed") != first                                   # ...and what you can do to it is not what it was
    game.hold(["ArrowUp"], 700); game.sleep(300)
    same("after a walk")
    x, y = game.pos()                                                          # a stair down into a tunnel: seen through its roof
    game.stamp(1, 0, ["...."], levels=["abcd"])
    game.rpc("dev_stamp", x=x + 5, y=y, rows=["........"], levels=["d" * 8], roofs=["4" * 8], heads=["2" * 8])
    game.rpc("dev_teleport", x=x + 6, y=y, z=-4)
    game.wait(f"myAt && myAt.x === {x + 6} && myAt.z === -4", 8000)
    game.wait(DRAWN, 8000); game.rest()
    same("under a roof")
    game.clear_area(14)


@pytest.mark.realtime
def test_standing_still_makes_little_memory(game):
    """With trees behind a hill in view the page made a megabyte of memory a frame for the collector to take back
    (60 MB a second: an array and a pair made for every tile asked about, the same edges and hints worked out again
    for each tree, each frame); standing in the live world as a phone, 12 to 23 MB a second. A ninth of that here."""
    cdp = game.page.context.new_cdp_session(game.page)
    game.stamp(-6, -8, ["T" * 13, "T" * 13] + ["." * 13] * 3, levels=["0" * 13] * 2 + ["3" * 13] * 3)   # trees behind a hill: cut at its edge, each frame
    game.wait(DRAWN, 8000); game.sleep(1200)
    cdp.send("HeapProfiler.enable")
    cdp.send("HeapProfiler.startSampling", {"samplingInterval": 4096, "includeObjectsCollectedByMajorGC": True, "includeObjectsCollectedByMinorGC": True})
    frames = game.js("new Promise((res) => { let n = 0; const t0 = performance.now(); (function f() { n++; if (performance.now() - t0 < 3000) requestAnimationFrame(f); else res(n); })(); })")
    prof = cdp.send("HeapProfiler.stopSampling")["profile"]
    by = {}
    def walk(node):
        f = node["callFrame"]; k = (f["functionName"] or "?") + " " + f["url"].split("/")[-1].split("?")[0]
        by[k] = by.get(k, 0) + node.get("selfSize", 0)
        for c in node.get("children", []):
            walk(c)
    walk(prof["head"])
    a_frame = sum(by.values()) / max(1, frames)
    top = sorted(by.items(), key=lambda kv: -kv[1])[:6]
    print("memory made a frame: %.0f KB over %d frames" % (a_frame / 1000, frames), top)
    game.clear_area(14)
    assert frames > 30 and a_frame < 300_000, (round(a_frame), frames, top)
