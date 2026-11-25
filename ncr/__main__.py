"""python -m ncr practice --out DIR      write the practice rows and labels
python -m ncr build --rows CSV [--labels CSV] --out DIR [--as-of YYYY-MM-DD]
python -m ncr corridors --geography DIR --out DIR   corridor segments for one geography
"""
from __future__ import annotations

import argparse
import csv
from datetime import date
from pathlib import Path

from .compute import run
from .layers import write_all
from .practice import generate, labels
from .rows import read_rows, write_rows


def read_labels(path: Path | None) -> dict[str, str]:
    if not path:
        return {}
    with path.open(newline="") as f:
        return {r["cell"]: r["label"] for r in csv.DictReader(f)}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="ncr")
    sub = p.add_subparsers(dest="cmd", required=True)
    pr = sub.add_parser("practice")
    pr.add_argument("--out", type=Path, required=True)
    b = sub.add_parser("build")
    b.add_argument("--rows", type=Path, required=True)
    b.add_argument("--labels", type=Path)
    b.add_argument("--out", type=Path, required=True)
    b.add_argument("--as-of", type=date.fromisoformat)
    co = sub.add_parser("corridors")
    co.add_argument("--geography", type=Path, required=True)
    co.add_argument("--out", type=Path, required=True)
    a = p.parse_args(argv)

    if a.cmd == "corridors":
        from .corridors import load_definitions, load_jurisdictions, segments, write_segments

        defs = load_definitions(a.geography / "corridors.json")
        segs = segments(defs, load_jurisdictions(a.geography / "jurisdictions.geojson"))
        paths = write_segments(defs, segs, a.out)
        straddling = sum(s.straddles for s in segs)
        print(f"{defs['name']}: {len(segs)} segments, {straddling} straddle a town line")
        for k, v in paths.items():
            print(f"  {k}: {v}")
        return 0

    if a.cmd == "practice":
        a.out.mkdir(parents=True, exist_ok=True)
        write_rows(a.out / "practice-rows.csv", generate())
        with (a.out / "practice-labels.csv").open("w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["cell", "label"])
            for c, name in sorted(labels().items()):
                w.writerow([c, name])
        print(f"wrote {a.out}/practice-rows.csv and practice-labels.csv")
        return 0

    result = run(read_rows(a.rows), as_of=a.as_of)
    paths = write_all(result, read_labels(a.labels), a.out)
    print(f"as of {result.as_of}: {len(result.cells)} cells, {len(result.links)} links, "
          f"{len(result.rings)} ring(s); rings by resolution {result.fractal}")
    for k, v in paths.items():
        print(f"  {k}: {v}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
