"""tools/flake_rates.py: each browser test's failures over main's runs, read from CI's job logs (excerpts of real ones)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import flake_rates as F  # noqa: E402

# (run 45818474332, job 139908258837: the -v lines, colours and all, and the short summary)
RUN1 = """2026-11-26T12:29:50.9425870Z tests/e2e/test_e2e_ask.py::test_a_sign_is_written_as_it_goes_up \x1b[32mPASSED\x1b[0m   [  2%]
2026-11-26T12:32:39.8765532Z tests/e2e/test_e2e_jump_feel.py::test_the_hop_goes_a_block_up_and_comes_down_smoothly \x1b[32mPASSED\x1b[0m [ 52%]
2026-11-26T12:32:46.1478503Z tests/e2e/test_e2e_jump_feel.py::test_auto_jump_up_a_staircase_is_smooth_and_keeps_its_rhythm \x1b[31mFAILED\x1b[0m [ 55%]
2026-11-26T12:33:20.5945815Z tests/e2e/test_e2e_jump_feel.py::test_sprint_jumping_over_a_wide_hole_or_water_the_body_flies_the_arc[hole] \x1b[32mPASSED\x1b[0m [ 67%]
2026-11-26T12:33:21.0000000Z tests/e2e/test_e2e_audio.py::test_the_music_plays \x1b[33mSKIPPED\x1b[0m (no music rendered) [ 70%]
2026-11-26T12:34:42.3962612Z =================================== FAILURES ===================================
2026-11-26T12:34:42.4087214Z =========================== short test summary info ============================
2026-11-26T12:34:42.4088644Z \x1b[31mFAILED\x1b[0m tests/e2e/test_e2e_jump_feel.py::test_auto_jump_up_a_staircase_is_smooth_and_keeps_its_rhythm - AssertionError: ([350, 150], 83.3)
2026-11-26T12:34:42.4091293Z \x1b[31m=================== 1 failed, 33 passed in 313.69s (0:05:13) ===================\x1b[0m
"""

# (another run: the staircase passes, a hole-jump fails at its set-up, and a file does not load)
RUN2 = """2026-11-26T13:02:01.1Z tests/e2e/test_e2e_jump_feel.py::test_auto_jump_up_a_staircase_is_smooth_and_keeps_its_rhythm PASSED [ 55%]
2026-11-26T13:02:09.1Z tests/e2e/test_e2e_jump_feel.py::test_sprint_jumping_over_a_wide_hole_or_water_the_body_flies_the_arc[hole] ERROR [ 67%]
2026-11-26T13:05:00.1Z =========================== short test summary info ============================
2026-11-26T13:05:00.1Z ERROR tests/e2e/test_e2e_jump_feel.py::test_sprint_jumping_over_a_wide_hole_or_water_the_body_flies_the_arc[hole] - TimeoutError: page | gone
2026-11-26T13:05:00.1Z ERROR tests/e2e/test_e2e_broken.py
"""


def test_a_log_gives_each_test_that_ended_and_whether_it_failed():
    r = F.parse(RUN1)
    assert r["tests/e2e/test_e2e_jump_feel.py::test_auto_jump_up_a_staircase_is_smooth_and_keeps_its_rhythm"] == (
        True, "AssertionError: ([350, 150], 83.3)")
    assert r["tests/e2e/test_e2e_jump_feel.py::test_sprint_jumping_over_a_wide_hole_or_water_the_body_flies_the_arc[hole]"] == (False, "")
    assert "tests/e2e/test_e2e_audio.py::test_the_music_plays" not in r       # (a skip is no run of the test)
    assert len(r) == 4


def test_an_error_at_set_up_and_a_file_that_does_not_load_are_failures():
    r = F.parse(RUN2)
    assert r["tests/e2e/test_e2e_jump_feel.py::test_sprint_jumping_over_a_wide_hole_or_water_the_body_flies_the_arc[hole]"] == (
        True, "TimeoutError: page | gone")
    assert r["tests/e2e/test_e2e_broken.py"] == (True, "")


def test_worst_first_over_the_runs_each_test_ran_in():
    rows = F.tally([F.parse(RUN2), F.parse(RUN1)])                         # (newest first)
    stair = "tests/e2e/test_e2e_jump_feel.py::test_auto_jump_up_a_staircase_is_smooth_and_keeps_its_rhythm"
    hole = "tests/e2e/test_e2e_jump_feel.py::test_sprint_jumping_over_a_wide_hole_or_water_the_body_flies_the_arc[hole]"
    assert rows == [("tests/e2e/test_e2e_broken.py", 1, 1, ""),            # (1/1: it was there only once)
                    (stair, 1, 2, "AssertionError: ([350, 150], 83.3)"),   # (ties: by name)
                    (hole, 1, 2, "TimeoutError: page | gone")]


def test_the_table_is_markdown_with_its_bars_kept_out_of_the_cells():
    md = F.table(F.tally([F.parse(RUN2), F.parse(RUN1)]), 2)
    assert "over its last 2 full runs" in md
    assert "| `test_e2e_broken.py` | 1/1 | 100% |  |" in md
    assert "TimeoutError: page \\| gone" in md
    assert F.table([], 6).endswith("| (none) | | | |")
