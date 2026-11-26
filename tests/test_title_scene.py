"""The first screen's island (tools/build_title_scene.py): the builder still runs against the game as it is, and the
page's baked copy (web/js/title_map.js) is what it makes, so the island is never left in a format the page no longer reads."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import build_title_scene  # noqa: E402


def test_the_builder_runs_and_the_house_has_its_roof():
    data = build_title_scene.build()
    assert len(data["blocks"]) == 6
    roofs = {(b["x"] + i % b["w"], b["y"] + i // b["w"], z) for b in data["blocks"] for i, z, kind, _ in b.get("floors", []) if kind == "roof"}
    assert roofs == {(x, y, 3) for x in range(38, 45) for y in range(22, 28)}       # (a storey over each of the house's tiles)
    baked = build_title_scene.OUT.read_text().split("const TITLE_MAP = ", 1)[1].rstrip().rstrip(";")
    assert json.loads(baked) == data, "web/js/title_map.js is not what tools/build_title_scene.py makes: run it again"
