"""The two guards between scan rows and anything published: check_row and
read_rows (what may come in) and check_public (what the public layer may say).

Written after the first mutation run (mutmut, setup.cfg): 13 mutants of
check_public and 14 of check_row and read_rows survived. The existing count
test was caught by the unknown-key check, so the number check behind it never
ran; a bad destination cell, a bad event code, an upper-case person column
and a file with the wrong columns were not tested at all. Each case below was
watched failing with its fault written in.
"""
from datetime import date

import h3
import pytest

from ncr.layers import check_public
from ncr.rows import FlowRow, RowError, check_row, read_rows

from .helpers import A, B

MON = date(2025, 1, 6)


def fc(**props):
    return {"features": [{"properties": {"layer": "busy", "level": 2, **props}}]}


# check_public ---------------------------------------------------------------

def test_public_layer_passes_shapes_and_words():
    check_public(fc(label="Blue Island", direction="both", role="core"))
    check_public({"unit": None, "features": [{"properties": {"layer": "ring", "level": 3}}]})


def test_public_layer_refuses_a_number_under_an_allowed_key():
    for key in ("label", "role", "ring", "ends", "status", "pattern", "direction"):
        with pytest.raises(ValueError, match=f"number in {key}"):
            check_public(fc(**{key: 40}))
    with pytest.raises(ValueError, match="number in label"):
        check_public(fc(label=2.5))


def test_public_layer_refuses_a_count_in_a_later_feature():
    layer = {"features": [{"properties": {"layer": "busy", "level": 1}},
                          {"properties": {"layer": "busy", "level": 1, "label": 15}}]}
    with pytest.raises(ValueError, match="number in label"):
        check_public(layer)


def test_public_layer_allows_true_and_false():
    check_public(fc(ends=True, status=False))


def test_public_layer_level_is_one_two_or_three():
    for level in (1, 2, 3):
        check_public(fc(level=level))
    for level in (0, 4, 40, "2"):
        with pytest.raises(ValueError, match="level must be 1, 2 or 3"):
            check_public(fc(level=level))


def test_public_layer_refuses_an_unknown_key_and_names_it():
    with pytest.raises(ValueError, match=r"\['scans'\]"):
        check_public(fc(scans="many"))


def test_public_layer_must_not_name_a_unit():
    with pytest.raises(ValueError, match="unit"):
        check_public({**fc(), "unit": "scans"})


# check_row ------------------------------------------------------------------

def test_a_row_at_the_floor_passes():
    assert check_row(FlowRow(MON, A, B, "REC-BOCCE-001", 5)).scans == 5


def test_a_destination_that_is_not_a_cell_or_too_fine_is_refused():
    with pytest.raises(RowError, match="destination_cell 'nowhere' is not an H3 cell"):
        check_row(FlowRow(MON, A, "nowhere", "REC-BOCCE-001", 10))
    with pytest.raises(RowError, match="source_cell 'x' is not an H3 cell"):
        check_row(FlowRow(MON, "x", B, "REC-BOCCE-001", 10))
    fine = h3.latlng_to_cell(41.71, -87.68, 9)
    with pytest.raises(RowError, match="destination_cell .* is res 9"):
        check_row(FlowRow(MON, A, fine, "REC-BOCCE-001", 10))
    coarse = h3.latlng_to_cell(41.71, -87.68, 6)
    with pytest.raises(RowError, match="res 6"):
        check_row(FlowRow(MON, coarse, B, "REC-BOCCE-001", 10))


def test_an_event_code_out_of_shape_is_refused():
    for code in ("bocce", "REC-BOCCE-01", "REC-BOCCE-0001", "rec-bocce-001", "RE-BOCCE-001", "REC-BOCCE-001x"):
        with pytest.raises(RowError, match="uec_code"):
            check_row(FlowRow(MON, A, B, code, 10))


# read_rows ------------------------------------------------------------------

def write(tmp_path, header, *lines):
    p = tmp_path / "rows.csv"
    p.write_text("\n".join([header, *lines]) + "\n")
    return p


GOOD_HEADER = "week,source_cell,destination_cell,uec_code,scans"


def test_a_person_column_is_refused_in_any_case_or_spacing(tmp_path):
    p = write(tmp_path, GOOD_HEADER + ", Anonymous_ID ", f"2025-01-06,{A},{B},REC-BOCCE-001,10,x")
    with pytest.raises(RowError, match="anonymous_id could describe a person"):
        read_rows(p)


def test_a_file_with_other_columns_or_order_is_refused(tmp_path):
    with pytest.raises(RowError, match="expected columns"):
        read_rows(write(tmp_path, "week,destination_cell,source_cell,uec_code,scans",
                        f"2025-01-06,{A},{B},REC-BOCCE-001,10"))
    with pytest.raises(RowError, match="expected columns"):
        read_rows(write(tmp_path, GOOD_HEADER + ",note", f"2025-01-06,{A},{B},REC-BOCCE-001,10,x"))


def test_a_bad_row_is_refused_with_its_line_number(tmp_path):
    p = write(tmp_path, GOOD_HEADER,
              f"2025-01-06,{A},{B},REC-BOCCE-001,10",
              f"2025-01-06,{A},{B},REC-BOCCE-001,4")
    with pytest.raises(RowError, match="line 3: a row of 4 scans is under the floor"):
        read_rows(p)
    p = write(tmp_path, GOOD_HEADER, f"not-a-date,{A},{B},REC-BOCCE-001,10")
    with pytest.raises(RowError, match="line 2:"):
        read_rows(p)
    p = write(tmp_path, GOOD_HEADER, f"2025-01-06,{A},{B},REC-BOCCE-001,ten")
    with pytest.raises(RowError, match="line 2:"):
        read_rows(p)


def test_every_good_row_is_read_in_order(tmp_path):
    p = write(tmp_path, GOOD_HEADER,
              f"2025-01-06,{A},{B},REC-BOCCE-001,10",
              f"2025-01-13,{B},{A},REC-BOCCE-002,15")
    rows = read_rows(p)
    assert [(r.week, r.source_cell, r.destination_cell, r.uec_code, r.scans) for r in rows] == [
        (MON, A, B, "REC-BOCCE-001", 10),
        (date(2025, 1, 13), B, A, "REC-BOCCE-002", 15),
    ]
