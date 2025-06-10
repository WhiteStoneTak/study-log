#!/usr/bin/env python3
"""
study-log statistics generator

Outputs
• stats/daily_minutes.csv          – date, minutes
• stats/weekly_minutes.csv         – iso_week, minutes
• stats/weekly_chart.png           – line chart (minutes / week)
• stats/pies/daily/<date>_pie.png  – subject pie chart per day
• stats/pies/weekly/<week>_pie.png – subject pie chart per ISO week
• logs/weekly/<week>-review.md     – created if missing
• README.md                        – total-hours badge auto-updated
"""

from pathlib import Path
import re
import csv
import datetime as dt
from collections import defaultdict

# ── external: matplotlib only ───────────────────────────────────────
import matplotlib.pyplot as plt

# ── repo paths ──────────────────────────────────────────────────────
ROOT        = Path(__file__).resolve().parents[1]
DAILY_DIR   = ROOT / "logs" / "daily"
WEEKLY_DIR  = ROOT / "logs" / "weekly"
STATS_DIR   = ROOT / "stats"
PIE_DAILY   = STATS_DIR / "pies" / "daily"
PIE_WEEKLY  = STATS_DIR / "pies" / "weekly"
README      = ROOT / "README.md"

# ensure folders
for p in (STATS_DIR, PIE_DAILY, PIE_WEEKLY, WEEKLY_DIR):
    p.mkdir(parents=True, exist_ok=True)

# ── regex patterns ─────────────────────────────────────────────────
TOTAL_RE   = re.compile(r"Total:\s*(?:(\d+)h)?\s*(\d+)m", re.I)
SUBJECT_RE = re.compile(r"^###\s+(.+?)\s+\((\d+)m\)", re.I | re.M)

# ── containers ─────────────────────────────────────────────────────
daily_rows            = []                       # list of dicts
weekly_totals         = defaultdict(int)         # week -> minutes
daily_subject_minutes = defaultdict(dict)        # date -> {sub: m}
weekly_subject_minutes = defaultdict(lambda: defaultdict(int))

# ── 1) parse daily logs ────────────────────────────────────────────
for md in sorted(DAILY_DIR.glob("20??-??-??.md")):
    date_str = md.stem                           # YYYY-MM-DD
    text     = md.read_text(encoding="utf-8")

    m_total = TOTAL_RE.search(text)
    if not m_total:
        continue
    h, m = m_total.groups()
    total_m = (int(h) if h else 0) * 60 + int(m)
    daily_rows.append({"date": date_str, "minutes": total_m})

    # subject split
    for sub, mins in SUBJECT_RE.findall(text):
        mins = int(mins)
        daily_subject_minutes[date_str][sub] = mins

    # weekly aggregation
    y, w, _ = dt.date.fromisoformat(date_str).isocalendar()
    iso_week = f"{y}-W{w:02d}"
    weekly_totals[iso_week] += total_m
    for sub, mins in daily_subject_minutes[date_str].items():
        weekly_subject_minutes[iso_week][sub] += mins

# if no data → exit quietly
if not daily_rows:
    print("[stats] no daily logs found – nothing to do.")
    exit(0)

# ── 2) csv export ──────────────────────────────────────────────────
(STATS_DIR / "daily_minutes.csv").write_text(
    "date,minutes\n" + "\n".join(f"{r['date']},{r['minutes']}" for r in daily_rows),
    encoding="utf-8"
)
(STATS_DIR / "weekly_minutes.csv").write_text(
    "iso_week,minutes\n" + "\n".join(f"{w},{m}" for w, m in sorted(weekly_totals.items())),
    encoding="utf-8"
)

# ── 3) charts helper ───────────────────────────────────────────────
def save_pie(data: dict, path: Path, title: str):
    if not data:
        return
    labels, values = zip(*[(k, v) for k, v in data.items() if v > 0])
    plt.figure(figsize=(4, 4))
    plt.pie(values, labels=labels, autopct="%1.0f%%", startangle=90)
    plt.title(title)
    plt.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(path, dpi=150)
    plt.close()

# ── 4) weekly line chart ───────────────────────────────────────────
weeks   = [w for w, _ in sorted(weekly_totals.items())]
minutes = [weekly_totals[w] for w in weeks]
plt.figure(figsize=(8, 4))
plt.plot(weeks, minutes, marker="o")
plt.xticks(rotation=45, ha="right", fontsize=8)
plt.ylabel("Minutes")
plt.title("Weekly Study Time")
plt.tight_layout()
plt.savefig(STATS_DIR / "weekly_chart.png", dpi=150)
plt.close()

# ── 5) subject pie charts ─────────────────────────────────────────
#   per day
for date_str, sub_dict in daily_subject_minutes.items():
    save_pie(sub_dict, PIE_DAILY / f"{date_str}_pie.png", f"{date_str} subject mix")

#   per week
for wk, sub_dict in weekly_subject_minutes.items():
    save_pie(sub_dict, PIE_WEEKLY / f"{wk}_pie.png", f"{wk} subject mix")

# ── 6) create missing weekly review markdown -----------------------
for wk, mins in weekly_totals.items():
    f = WEEKLY_DIR / f"{wk}.md"
    if f.exists():
        continue
    year, num = wk.split("-W")
    f.write_text(
        f"# Week {num} Review ({wk})\n\n"
        f"**Total study time:** {mins} m ({mins/60:.2f} h)\n\n"
        f"> _Auto-generated on {dt.date.today()}_\n",
        encoding="utf-8"
    )

# ── 7) total hours badge in README ---------------------------------
tot_min = sum(r["minutes"] for r in daily_rows)
badge   = f"![total hours](https://img.shields.io/badge/total hours-{tot_min/60:.1f}h-blue)\n"

if README.exists():
    lines = README.read_text(encoding="utf-8").splitlines(True)
else:
    lines = ["# study-log\n"]

replaced = False
for i, ln in enumerate(lines):
    if "img.shields.io/badge/total" in ln:
        lines[i] = badge
        replaced = True
        break
if not replaced:
    for i, ln in enumerate(lines):
        if ln.startswith("#"):
            lines.insert(i + 1, badge)
            break

README.write_text("".join(lines), encoding="utf-8")

print(
    f"[stats] days={len(daily_rows)}  weeks={len(weekly_totals)}  "
    f"total={tot_min/60:.1f}h  charts: weekly line + {len(daily_subject_minutes)} daily pies + {len(weekly_subject_minutes)} weekly pies"
)
