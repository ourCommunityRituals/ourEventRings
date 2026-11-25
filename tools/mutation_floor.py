"""Per-file mutation floors for ncr/, and the ratchet that keeps them from
going down. Reads mutmut's results (mutants/ncr/*.py.meta) after `mutmut run`.

Score = killed / (killed + survived + no tests), per file. Timeouts count as
killed, as in mutmut. A floored file missing from the results, or with no
mutant that ran, fails: a floor on a file that was not mutated cannot fail.

Usage:
  python tools/mutation_floor.py                       check mutants/ against mutation-floors.json
  python tools/mutation_floor.py --ratchet <base.json> no floor in mutation-floors.json may be lower
                                                       than in <base.json>, or missing
"""
import json
import sys
from pathlib import Path

FLOORS = Path("mutation-floors.json")
RESULTS = Path("mutants")

# mutmut 3 exit codes per mutant (mutmut/stats.py status_by_exit_code):
# killed 1, 3; timeout 36, 24, -24, 152, 255; caught by type check 37;
# survived 0; no tests 5, 33. Anything else (not checked, suspicious,
# segfault, interrupted) is a mutant that was not judged, and fails the file:
# fail closed, as an error is not a kill.
KILLED = {1, 3, 24, -24, 36, 37, 152, 255}
SURVIVED = {0}
NO_TESTS = {5, 33}
SKIPPED = {34}


def file_score(codes):
    killed = sum(1 for c in codes if c in KILLED)
    valid = killed + sum(1 for c in codes if c in SURVIVED or c in NO_TESTS)
    return None if valid == 0 else killed / valid * 100


def read_results(root: Path) -> dict:
    out = {}
    for meta in sorted(root.glob("ncr/**/*.py.meta")):
        rel = meta.relative_to(root).as_posix()[: -len(".meta")]
        out[rel] = list(json.loads(meta.read_text())["exit_code_by_key"].values())
    return out


def check_floors(results: dict, floors: dict) -> list:
    failures = []
    for path, floor in floors.items():
        if path not in results:
            failures.append(f"{path}: not in the mutation results (was it mutated?)")
            continue
        unjudged = [c for c in results[path] if c not in KILLED | SURVIVED | NO_TESTS | SKIPPED]
        if unjudged:
            failures.append(f"{path}: {len(unjudged)} mutant(s) not judged (exit codes {sorted(set(map(str, unjudged)))})")
            continue
        score = file_score(results[path])
        if score is None:
            failures.append(f"{path}: no mutant ran")
        elif score < floor:
            failures.append(f"{path}: {score:.2f}% is below its floor of {floor}%")
    return failures


def check_ratchet(floors: dict, base: dict) -> list:
    failures = []
    for path, floor in base.items():
        if path not in floors:
            failures.append(f"{path}: its floor of {floor}% was removed (floors may only go up)")
        elif floors[path] < floor:
            failures.append(f"{path}: floor lowered from {floor}% to {floors[path]}% (floors may only go up)")
    return failures


def read_floors(path: Path) -> dict:
    floors = json.loads(path.read_text()).get("floors")
    if not isinstance(floors, dict) or not floors:
        raise ValueError(f"{path} lists no floors")
    for p, f in floors.items():
        if not isinstance(f, (int, float)) or isinstance(f, bool) or not 0 <= f <= 100:
            raise ValueError(f"{path}: the floor of {p} is not a number from 0 to 100")
    return floors


def main(argv) -> int:
    floors = read_floors(FLOORS)
    if "--ratchet" in argv:
        failures = check_ratchet(floors, read_floors(Path(argv[argv.index("--ratchet") + 1])))
        label = "Mutation floor ratchet"
    else:
        failures = check_floors(read_results(RESULTS), floors)
        label = "Per-file mutation floor"
    for f in failures:
        print(f"::error title={label}::{f}")
    if not failures:
        print(f"{label}: {len(floors)} files, all hold.")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
