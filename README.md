# ourEventRings

Research and NCR analytics for OurCommunityRituals (OER). This repo turns scan
traffic from ourSharedEvents into the **Node, Corridor and Ring** layers the
NCR approach describes (OCR_VISION section 9, OSE ADR-009, OCR ADR-010).

## The rule this code keeps

It counts traffic on containers, never people. The only input is scans on QR
posters: where a poster hangs (an H3 res 7 corridor cell), where its event is
(another res 7 cell), the event type and the week. No phone id, cookie, return
rate or location of a person is read. A file that carries such a column is
refused whole (`ncr/rows.py`).

## What it computes (`ncr/compute.py`)

| Layer | How |
| --- | --- |
| Busy places (nodes) | Scans per corridor cell: local, sent out, received; saturation (share of weeks with traffic); trend; potential (posters here send scans out, little comes back) |
| Connections (corridors) | Scans from posters in cell A for events in cell B. Both ways when the smaller side is at least a third of the larger; validated when seen in 2+ seasons; seasonal or structural; quarter trend and year-on-year growth |
| Rings | 3+ cells in a cycle whose links run both ways (core), all seen together in 2+ seasons, plus cells tied in by a validated link (periphery). A spoke to one hub is a corridor, not a ring |
| Growth patterns | SPIDERWEB (one cell feeding 3+ newer links), REVERB (both ways and growing year on year), FRACTAL (rings counted again at res 6 and res 5) |

ADR-009 leaves ring thresholds to be fitted from real data, so they live in
`Settings` and every output says `provisional`.

## What it writes (`ncr/layers.py`)

- `layer-public.geojson`: shapes only, no numbers (owner decision 2026-11-23).
  A 1 to 3 level, direction and plain labels; `check_public` refuses anything else.
- `layer-admin.geojson`: the same shapes with counts, under 5 withheld, the rest
  rounded down to 5.
- `research/*.csv`: corridors, cells, rings, corridor by event type.

## Run it

```
pip install -r requirements.txt
python -m pytest -q tests
python -m ncr practice --out fixtures
python -m ncr build --rows fixtures/practice-rows.csv --labels fixtures/practice-labels.csv --out out
```

`fixtures/practice-rows.csv` is made-up practice data (fixed seed) in the exact
shape of the weekly OSE export that OSE-2216 will build. It is not real traffic.
