from datetime import date
from pathlib import Path

import h3
import pytest

from ncr.rows import FlowRow, RowError, check_row, publish, read_rows, round_down

from .helpers import A, B


def write(tmp_path: Path, header: str, line: str) -> Path:
    p = tmp_path / "rows.csv"
    p.write_text(f"{header}\n{line}\n")
    return p


@pytest.mark.parametrize("col", ["anonymous_id", "anon_id_hash", "user_agent_hash", "lat", "visitors", "return_rate"])
def test_a_person_column_refuses_the_whole_file(tmp_path, col):
    p = write(tmp_path, f"week,source_cell,destination_cell,uec_code,scans,{col}",
              f"2025-01-06,{A},{B},REC-BOCCE-001,10,x")
    with pytest.raises(RowError, match="could describe a person"):
        read_rows(p)


def test_a_row_under_five_is_refused():
    with pytest.raises(RowError, match="under the floor"):
        check_row(FlowRow(date(2025, 1, 6), A, B, "REC-BOCCE-001", 4))


def test_a_row_not_rounded_to_five_is_refused():
    with pytest.raises(RowError, match="multiple of 5"):
        check_row(FlowRow(date(2025, 1, 6), A, B, "REC-BOCCE-001", 7))


def test_a_cell_finer_than_res_7_is_refused():
    fine = h3.latlng_to_cell(41.71, -87.68, 9)
    with pytest.raises(RowError, match="res 9"):
        check_row(FlowRow(date(2025, 1, 6), fine, B, "REC-BOCCE-001", 10))


def test_a_week_that_is_not_a_monday_is_refused():
    with pytest.raises(RowError, match="Monday"):
        check_row(FlowRow(date(2025, 1, 7), A, B, "REC-BOCCE-001", 10))


def test_good_file_reads(tmp_path):
    p = write(tmp_path, "week,source_cell,destination_cell,uec_code,scans", f"2025-01-06,{A},{B},REC-BOCCE-001,10")
    assert read_rows(p)[0].scans == 10


def test_publish_withholds_under_five_and_rounds_down():
    assert publish(0) is None and publish(4) is None
    assert publish(5) == 5 and publish(9) == 5 and publish(10) == 10
    assert round_down(14) == 10
