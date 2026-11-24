"""tools/mutation_floor.py, the per-file mutation gate, and its wiring.

Each BORN RED case was watched failing with its fault written into the tool
(`score < floor` read as `score <= floor`, the missing-file branch removed,
the unjudged branch removed, the ratchet's `<` read as `>`)."""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import mutation_floor as mf  # noqa: E402


def test_score_is_killed_over_killed_survived_and_untested():
    assert mf.file_score([1, 36, 0, 33]) == 50
    assert mf.file_score([1, 34]) == 100
    assert mf.file_score([34]) is None


def test_a_file_at_its_floor_passes():
    assert mf.check_floors({"ncr/a.py": [1, 0]}, {"ncr/a.py": 50}) == []


def test_born_red_under_the_floor_missing_or_unjudged_fails():
    assert "below its floor" in " ".join(mf.check_floors({"ncr/a.py": [1, 0]}, {"ncr/a.py": 50.01}))
    assert "not in the mutation results" in " ".join(mf.check_floors({}, {"ncr/a.py": 1}))
    assert "not judged" in " ".join(mf.check_floors({"ncr/a.py": [1, None]}, {"ncr/a.py": 1}))
    assert "no mutant ran" in " ".join(mf.check_floors({"ncr/a.py": [34]}, {"ncr/a.py": 1}))


def test_born_red_the_ratchet_refuses_a_floor_lowered_or_dropped():
    assert mf.check_ratchet({"a": 60, "b": 1}, {"a": 50}) == []
    assert "lowered" in " ".join(mf.check_ratchet({"a": 40}, {"a": 50}))
    assert "removed" in " ".join(mf.check_ratchet({}, {"a": 50}))


def test_read_floors_refuses_an_empty_or_out_of_range_file(tmp_path):
    p = tmp_path / "f.json"
    p.write_text(json.dumps({"floors": {}}))
    with pytest.raises(ValueError, match="no floors"):
        mf.read_floors(p)
    p.write_text(json.dumps({"floors": {"a": 101}}))
    with pytest.raises(ValueError, match="0 to 100"):
        mf.read_floors(p)


def test_every_module_but_the_command_line_has_a_floor():
    floors = mf.read_floors(ROOT / "mutation-floors.json")
    modules = {p.relative_to(ROOT).as_posix() for p in (ROOT / "ncr").glob("*.py")} - {
        "ncr/__init__.py", "ncr/__main__.py"}
    assert set(floors) == modules


def test_the_workflow_runs_mutmut_then_the_floors_nightly():
    wf = (ROOT / ".github/workflows/mutation-testing.yml").read_text()
    assert "mutmut run" in wf and "python tools/mutation_floor.py" in wf
    assert "--ratchet" in wf
    assert "schedule:" in wf and "workflow_dispatch:" in wf
