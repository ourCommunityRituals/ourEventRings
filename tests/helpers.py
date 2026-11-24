from datetime import date, timedelta

import h3

from ncr.rows import FlowRow

MON = date(2025, 1, 6)


def c(lat: float, lng: float) -> str:
    return h3.latlng_to_cell(lat, lng, 7)


A, B, C, D, E = c(41.71, -87.68), c(41.72, -87.70), c(41.66, -87.68), c(41.58, -87.50), c(41.88, -86.59)


def weekly(src, dst, scans, weeks=100, start=MON, months=None, uec="REC-BOCCE-001"):
    out = []
    for i in range(weeks):
        wk = start + timedelta(weeks=i)
        if months and wk.month not in months:
            continue
        out.append(FlowRow(wk, src, dst, uec, scans))
    return out
