# Mutation testing for ncr/

The tests say the NCR layers are computed right and the privacy guards hold.
Mutation testing checks that they would notice if not. mutmut writes one small
fault at a time into `ncr/` (a `<` to `<=`, a `True` to `False`, a dropped
condition), reruns the tests, and records whether any test failed. A mutant
that survives is a fault the tests would let ship.

## Running

    pip install -r requirements.txt mutmut==3.8.1
    mutmut run                       # about a minute; working copy in mutants/
    python tools/mutation_floor.py   # each file at or above its floor
    mutmut results                   # the survivors
    mutmut show <name>               # one survivor's diff

`.github/workflows/mutation-testing.yml` does the same nightly, on demand, and
on a pull request that touches `ncr/` or the tests. On a pull request it also
checks that no floor in `mutation-floors.json` was lowered or dropped.

## Floors

Each file's floor is its score when last measured: killed over killed,
survived and untested. A mutant mutmut did not judge (not checked,
suspicious, a crash) fails its file, so a broken run cannot pass. Raise a
floor when the tests improve; it may never go down.

| File | Floor | What it holds |
| --- | --- | --- |
| `ncr/rows.py` | 85.05% | the input guard: no person column, res 7 cells only, under-5 and unrounded rows refused |
| `ncr/compute.py` | 66.29% | nodes, corridors, rings, growth patterns |
| `ncr/practice.py` | 61.48% | the practice data generator |
| `ncr/layers.py` | 48.29% | the GeoJSON layers and the public-layer guard |

`ncr/__main__.py` (the command line) has no floor: none of its 123 mutants is
reached by a test. The CI job's build step runs it, but not as a test.

## First run (2026-11-24)

The two privacy guards had gaps, now tested in `tests/test_privacy_guards.py`:

- `check_public` (layers.py): 13 mutants survived. The existing count test
  put the number under an unknown key, so the unknown-key check caught it and
  the number check behind it never ran. Removing the number check, the level
  range or the unit check all passed. Now 1 survives (an error message's
  wording).
- `check_row` and `read_rows` (rows.py): 14 survived. A destination cell that
  is not a cell, an event code out of shape, an upper-case person column and
  a file with extra or reordered columns were not tested. Now 2 survive (the
  wording of a message, and the CSV newline setting).

The largest remaining gaps are in `layers.py` (the shape and label code) and
`compute.py` (trend and season thresholds).

## Across the fleet

One of a series of mutation runs across the test pyramid: StrykerJS in the
ourCommunityRituals packages, ourWKRP and ourSharedEvents, hand-written
end-to-end mutants in ourWKRP and ourSharedEvents, and hand-written mutants on
the brain's gate scripts in OCR-docs.
