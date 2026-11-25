"""tools/e2e_shards.py: the browser test files dealt out by their time, and that time read from a CI log."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import e2e_shards as S  # noqa: E402

LOG = """2026-11-25T21:52:00.1Z ============================= slowest durations =============================
2026-11-25T21:52:00.1Z 31.01s call     tests/e2e/test_e2e_zoom.py::test_a_level_glides
2026-11-25T21:52:00.1Z 2.50s setup    tests/e2e/test_e2e_zoom.py::test_a_level_glides
2026-11-25T21:52:00.1Z 4.00s call     tests/e2e/test_e2e_bag.py::test_a[phone]
2026-11-25T21:52:00.1Z 0.49s teardown tests/e2e/test_e2e_bag.py::test_a[phone]
"""


def test_a_files_time_is_the_sum_of_its_tests_and_a_partial_list_is_not_read():
    assert S.parse(LOG) == pytest.approx({"tests/e2e/test_e2e_zoom.py": 33.51, "tests/e2e/test_e2e_bag.py": 4.49})
    assert S.parse(LOG.replace("slowest durations", "slowest 10 durations")) == {}


def test_the_longest_go_first_onto_the_least_loaded_runner():
    d = {"a": 300, "b": 200, "c": 100, "d": 100, "e": 100}
    shards = S.plan(list(d), d)                        # 800 s: three runners of TARGET (300)
    assert sorted(shards) == ["a", "b e", "c d"]


def test_an_unmeasured_file_counts_as_the_median_and_few_files_take_few_runners():
    assert S.plan(["x", "y"], {"x": 10}) == ["x y"]
    assert len(S.plan([f"f{i}" for i in range(40)], {"f0": 200})) == S.RUNNERS       # 40 x 200 s: more than 16 runners ask
    assert S.plan([], {}) == []


def test_the_durations_file_names_only_browser_test_files_that_are_there():
    root = Path(S.__file__).resolve().parent.parent
    files = {str(p.relative_to(root)) for p in (root / "tests/e2e").glob("test_*.py")}
    assert set(json.loads(S.DURATIONS.read_text())) <= files
