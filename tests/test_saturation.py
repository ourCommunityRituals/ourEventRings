import csv

import pytest

from ncr.compute import compute, run
from ncr.layers import collection, write_history
from ncr.practice import generate, labels
from ncr.saturation import HISTORY_COLUMNS, history, ring_hexagons, ring_saturation

from .helpers import A, B, C, D, MON, weekly


def triangle(ab=10, ba=10, outside=10, weeks=100):
    rows = []
    for x, y, n in ((A, B, ab), (B, A, ba), (B, C, 10), (C, B, 10), (A, C, 10), (C, A, 10)):
        rows += weekly(x, y, n, weeks=weeks)
    if outside:
        rows += weekly(D, A, outside, weeks=weeks)  # one way into the ring from outside it
    return rows


def only_ring(result):
    assert len(result.rings) == 1
    return result.rings[0]


def test_each_share_by_hand():
    result = compute(triangle())
    ring = only_ring(result)
    sat = ring_saturation(result, ring)
    hexes = ring_hexagons(ring)
    assert set(ring.core) <= hexes
    # Only the three core cells carry traffic inside the outline.
    assert sat.active == 3 and sat.hexagons == len(hexes)
    assert sat.coverage == round(3 / len(hexes), 3)
    assert sat.steadiness == 1.0
    # 52 weeks: 3 links x 2 ways x 10 = 3120 inside; 520 more come in from D.
    assert sat.closure == round(3120 / 3640, 3)
    assert sat.reciprocity == 1.0
    assert sat.saturation == round((sat.coverage + 1.0 + 3120 / 3640 + 1.0) / 4, 3)
    assert sat.weeks_observed == 52 and sat.confidence == 1.0
    assert (sat.resolution, sat.size) == (7, "small")


def test_a_lopsided_link_lowers_reciprocity_and_a_closed_ring_is_fully_closed():
    result = compute(triangle(ab=20, ba=10, outside=0))
    sat = ring_saturation(result, only_ring(result))
    assert sat.reciprocity == round((0.5 + 1 + 1) / 3, 3)
    assert sat.closure == 1.0


def test_local_scans_count_as_staying_inside():
    rows = triangle() + weekly(A, A, 20)
    result = compute(rows)
    sat = ring_saturation(result, only_ring(result))
    assert sat.closure == round((3120 + 1040) / (3640 + 1040), 3)


def test_a_young_ring_carries_low_confidence():
    result = compute(triangle(weeks=30))  # two seasons of data, 30 of 52 weeks
    sat = ring_saturation(result, only_ring(result))
    assert sat.weeks_observed == 30
    assert sat.confidence == round((30 / 52 + min(result.rings[0].seasons_seen, 4) / 4) / 2, 3)
    assert sat.confidence < 1.0


def test_steadiness_reads_weeks_with_traffic():
    rows = [r for r in triangle(outside=0) if (r.week - MON).days // 7 % 2 == 0]  # every other week
    result = compute(rows)
    sat = ring_saturation(result, only_ring(result))
    assert sat.steadiness == pytest.approx(0.5, abs=0.02)


def test_history_layers_up_and_keeps_one_id_per_ring():
    rows = history(triangle(), step_weeks=4, resolutions=(7,))
    assert rows and {r["size"] for r in rows} == {"small"}
    assert len({r["ring"] for r in rows}) == 1
    conf = [r["confidence"] for r in rows]
    assert conf == sorted(conf) and conf[0] < conf[-1] == 1.0
    assert rows[0]["year_ago"] is None
    later = [r for r in rows if r["year_ago"] is not None]
    assert later, "a ring seen for over a year has a year-ago baseline"
    assert all(set(r) >= set(HISTORY_COLUMNS) for r in rows)


def test_history_sets_no_threshold_and_names_no_stage():
    rows = history(generate(), step_weeks=13)
    assert {r["size"] for r in rows} == {"small", "medium"}  # the practice set has no large ring
    for r in rows:
        assert "stage" not in r
        assert 0 <= r["saturation"] <= 1 and 0 <= r["confidence"] <= 1


def test_peer_median_compares_rings_of_one_size(tmp_path):
    rows = history(generate(), step_weeks=26)
    for r in rows:
        assert r["peer_median"] is None  # one ring per size in the practice set: no peers
    path = write_history(rows, tmp_path)
    got = list(csv.DictReader(path.open()))
    assert tuple(got[0]) == HISTORY_COLUMNS and len(got) == len(rows)


def test_admin_layer_carries_saturation_and_public_does_not():
    result = run(generate())
    admin = [f["properties"] for f in collection(result, labels(), True)["features"]
             if f["properties"]["layer"] == "ring" and f["properties"]["role"] == "core"]
    public = [f["properties"] for f in collection(result, labels(), False)["features"]
              if f["properties"]["layer"] == "ring"]
    assert admin and all(0 < p["saturation"] <= 1 and "confidence" in p for p in admin)
    assert public and all("saturation" not in p and "confidence" not in p for p in public)
