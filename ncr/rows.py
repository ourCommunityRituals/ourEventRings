"""The input rows and the privacy rules every row must already meet.

One row = one week, one source corridor (the H3 res 7 cell where a poster
hangs), one destination corridor (the res 7 cell where its event is), one event
type (uec_code) and the scans on those posters that week. OSE floors and rounds
each row before it leaves (OSE-2216); this module checks that again and refuses
anything that could describe a person.
"""
from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import h3

K = 5  # the under-5 floor: no published count below 5, no exceptions
CORRIDOR_RES = 7

COLUMNS = ("week", "source_cell", "destination_cell", "uec_code", "scans")

# Columns that would put a person (or a way back to one) into the job. Their
# presence anywhere in an input file is refused, not ignored.
FORBIDDEN_COLUMNS = frozenset(
    {
        "anonymous_id",
        "anon_id",
        "anon_id_hash",
        "ose_anon",
        "cookie",
        "user_agent",
        "user_agent_hash",
        "ip",
        "lat",
        "lon",
        "lng",
        "latitude",
        "longitude",
        "email",
        "name",
        "phone",
        "device_id",
        "return_rate",
        "returns",
        "visitor",
        "visitors",
        "people",
    }
)

UEC = re.compile(r"^[A-Z]{3}-[A-Z0-9]+-\d{3}$")


class RowError(ValueError):
    """An input row breaks a privacy or shape rule. The whole file is refused."""


@dataclass(frozen=True)
class FlowRow:
    week: date  # the Monday that starts the week
    source_cell: str
    destination_cell: str
    uec_code: str
    scans: int


def round_down(n: int) -> int:
    """Round a count down to a multiple of 5 (owner ruling 2026-11-18)."""
    return n - (n % K)


def publish(n: int) -> int | None:
    """A count as it may be published: None below the floor, else rounded down."""
    if n < K:
        return None
    return round_down(n)


def check_row(row: FlowRow) -> FlowRow:
    for cell, what in ((row.source_cell, "source_cell"), (row.destination_cell, "destination_cell")):
        if not h3.is_valid_cell(cell):
            raise RowError(f"{what} {cell!r} is not an H3 cell")
        if h3.get_resolution(cell) != CORRIDOR_RES:
            raise RowError(
                f"{what} {cell!r} is res {h3.get_resolution(cell)}; only res {CORRIDOR_RES} crosses the boundary"
            )
    if not UEC.match(row.uec_code):
        raise RowError(f"uec_code {row.uec_code!r} is not CLUSTER-TYPE-NNN")
    if row.week.weekday() != 0:
        raise RowError(f"week {row.week} is not a Monday")
    if row.scans < K:
        raise RowError(f"a row of {row.scans} scans is under the floor of {K}; OSE must withhold it")
    if row.scans % K:
        raise RowError(f"a row of {row.scans} scans is not rounded down to a multiple of {K}")
    return row


def read_rows(path: Path) -> list[FlowRow]:
    with path.open(newline="") as f:
        reader = csv.DictReader(f)
        header = [h.strip().lower() for h in (reader.fieldnames or [])]
        bad = sorted(set(header) & FORBIDDEN_COLUMNS)
        if bad:
            raise RowError(f"refused: column(s) {', '.join(bad)} could describe a person")
        if tuple(header) != COLUMNS:
            raise RowError(f"expected columns {COLUMNS}, got {tuple(header)}")
        rows = []
        for i, r in enumerate(reader, start=2):
            try:
                row = FlowRow(
                    week=date.fromisoformat(r["week"]),
                    source_cell=r["source_cell"],
                    destination_cell=r["destination_cell"],
                    uec_code=r["uec_code"],
                    scans=int(r["scans"]),
                )
            except (ValueError, TypeError) as e:
                raise RowError(f"line {i}: {e}") from e
            try:
                rows.append(check_row(row))
            except RowError as e:
                raise RowError(f"line {i}: {e}") from e
        return rows


def write_rows(path: Path, rows: list[FlowRow]) -> None:
    with path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(COLUMNS)
        for r in rows:
            w.writerow([r.week.isoformat(), r.source_cell, r.destination_cell, r.uec_code, r.scans])
