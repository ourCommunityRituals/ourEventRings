from ncr.compute import compute, run
from ncr.practice import generate, labels

from .helpers import A, B, C, D, E, weekly


def both(x, y, n=20, **kw):
    return weekly(x, y, n, **kw) + weekly(y, x, n, **kw)


def test_three_corridors_both_ways_make_a_ring():
    r = compute(both(A, B) + both(B, C) + both(C, A))
    assert len(r.rings) == 1 and r.rings[0].core == sorted([A, B, C])


def test_a_spoke_to_one_hub_is_not_a_ring():
    r = compute(both(A, B) + both(A, C) + both(A, D))
    assert r.rings == []


def test_a_one_way_cycle_is_not_a_ring():
    r = compute(weekly(A, B, 20) + weekly(B, C, 20) + weekly(C, A, 20))
    assert r.rings == []


def test_a_ring_seen_in_one_season_is_not_a_ring():
    r = compute(both(A, B, weeks=6) + both(B, C, weeks=6) + both(C, A, weeks=6))
    assert r.rings == []


def test_a_ring_needs_its_links_together_in_two_seasons():
    # Each link alone is seen in two seasons, but never all three in the same two.
    r = compute(both(A, B, months={1, 4}) + both(B, C, months={7, 10}) + both(C, A, months={1, 7}))
    assert all(l.validated for l in r.links.values())
    assert r.rings == []


def test_periphery_joins_by_a_one_way_link():
    r = compute(both(A, B) + both(B, C) + both(C, A) + weekly(D, A, 20))
    assert r.rings[0].periphery == [D]


def test_lopsided_traffic_is_one_way():
    r = compute(weekly(A, B, 60) + weekly(B, A, 10))
    (link,) = r.links.values()
    assert link.direction == "one" and link.from_cell == A


def test_summer_only_link_is_seasonal_not_fading():
    r = compute(weekly(E, A, 20, months={6, 7, 8}))
    (link,) = r.links.values()
    assert link.temporal == "SEASONAL" and link.status == "seasonal" and link.validated


def test_local_traffic_counts_for_the_cell_not_a_link():
    r = compute(weekly(A, A, 20))
    assert r.links == {} and r.cells[A].local > 0


def test_practice_data_finds_the_south_side_ring():
    r = run(generate())
    names = labels()
    (ring,) = r.rings
    assert {names[x] for x in ring.core} == {"Beverly", "Evergreen Park", "Blue Island"}
    assert {"Hammond", "Sawyer, Michigan"} <= {names[x] for x in ring.periphery}
    spider = [names[c.cell] for c in r.cells.values() if c.pattern == "SPIDERWEB"]
    assert spider == ["Beverly"]
    assert 7 in r.fractal and 5 in r.fractal


def test_the_trickle_under_five_never_becomes_a_link():
    r = run(generate())
    names = labels()
    pairs = {frozenset((names[l.a], names[l.b])) for l in r.links.values()}
    assert frozenset(("Bronzeville", "Beverly")) not in pairs
