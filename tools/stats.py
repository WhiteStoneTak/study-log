#!/usr/bin/env python3
"""
Generate study statistics for study-log.

* Parse logs/daily/YYYY-MM-DD.md and grab study time from a line like:
    ## 2025-06-07  (Total: 12h 25m)
* Export daily & weekly CSV files under stats/
* Auto-create weekly review files if they don’t exist
* Update or insert a total-hours badge in README.md
"""

from pathlib import Path
import re
import csv
import datetime as dt
from collections import defaultdict

# ── Repository paths ────────────────────────────────────────────────
ROOT        = Path(__file__).resolve().parents[1]
DAILY_DIR   = ROOT / "logs" / "daily"
WEEKLY_DIR  = ROOT / "logs" / "weekly"
STATS_DIR   = ROOT / "stats"
README      = ROOT / "README.md"

STATS_DIR.mkdir(parents=True, exist_ok=True)
WEEKLY_DIR.mkdir(parents=True, exist_ok=True)

# ── Regex: capture optional hours and mandatory minutes ─────────────
TOTAL_RE = re.compile(
    r"Total:\s*(?:(?P<hours>\d+)h)?\s*(?P<minutes>\d+)m", re.I
)

daily_rows    = []               # list of dicts: {date, minutes}
weekly_totals = defaultdict(int) # aggregated minutes per ISO week

# ── 1) Scan daily logs ──────────────────────────────────────────────
for md_file in sorted(DAILY_DIR.glob("20??-??-??.md")):
    date_str = md_file.stem                                 # YYYY-MM-DD
    with md_file.open(encoding="utf-8") as f:
        text = f.read()

    m = TOTAL_RE.search(text)
    if not m:
        continue                                            # skip if no Total

    hours   = int(m.group("hours")   or 0)
    minutes = int(m.group("minutes") or 0)
    total_m = hours * 60 + minutes

    daily_rows.append({"date": date_str, "minutes": total_m})

    iso_year, iso_week, _ = dt.date.fromisoformat(date_str).isocalendar()
    weekly_totals[f"{iso_year}-W{iso_week:02d}"] += total_m

# ── 2) Write CSVs ───────────────────────────────────────────────────
STATS_DIR.joinpath("daily_minutes.csv").write_text(
    "date,minutes\n" +
    "\n".join(f"{row['date']},{row['minutes']}" for row in daily_rows),
    encoding="utf-8"
)

STATS_DIR.joinpath("weekly_minutes.csv").write_text(
    "iso_week,minutes\n" +
    "\n".join(f"{wk},{mins}" for wk, mins in sorted(weekly_totals.items())),
    encoding="utf-8"
)

# ── 3) Auto-generate missing weekly review files ( …-review.md ) ───
for wk, mins in weekly_totals.items():
    review_path = WEEKLY_DIR / f"{wk}-review.md"
    if review_path.exists():
        continue
    year, week_num = wk.split("-W")
    review_path.write_text(
        f"# Week {week_num} Review ({wk})\n\n"
        f"**Total study time:** {mins} m ({mins/60:.2f} h)\n\n"
        f"> _Auto-generated on {dt.date.today()}_\n",
        encoding="utf-8"
    )

# ── 4) Insert / update total-hours badge in README ────────────────
total_minutes = sum(r["minutes"] for r in daily_rows)
badge_line    = (
    f"![total hours]"
    f"(https://img.shields.io/badge/total hours-{total_minutes/60:.1f}h-blue)\n"
)

if README.exists():
    lines = README.read_text(encoding="utf-8").splitlines(keepends=True)
else:                                            # create a minimal README
    lines = ["# study-log\n"]

replaced = False
for i, ln in enumerate(lines):
    if "img.shields.io/badge/total" in ln:
        lines[i] = badge_line
        replaced = True
        break
if not replaced:
    # insert badge just after the first header line
    for i, ln in enumerate(lines):
        if ln.startswith("#"):
            lines.insert(i + 1, badge_line)
            break

README.write_text("".join(lines), encoding="utf-8")

print(
    f"[stats] days={len(daily_rows)}  weeks={len(weekly_totals)}  "
    f"total={total_minutes/60:.1f}h"
)
