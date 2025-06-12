#!/usr/bin/env python3
"""
study-log statistics generator
──────────────────────────────
Creates:

• stats/daily_minutes.csv          – date, minutes
• stats/weekly_minutes.csv         – ISO week, minutes
• stats/weekly_chart.png           – line chart (minutes / week)
• stats/pies/daily/YYYY-MM-DD.png  – subject pie per day
• stats/pies/weekly/YYYY-WNN.png   – subject pie per week
• logs/weekly/YYYY-WNN.md          – weekly review (auto-stub)
• README.md                        – total-hours badge (auto-patched)
"""

# ————————————————————————————————————————————————————————
# Imports & helpers
# ————————————————————————————————————————————————————————
from pathlib import Path
import csv, re, datetime as dt, time
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")                  # headless backend for CI
import matplotlib.pyplot as plt

# Simple timer for debug logs
T0 = time.time()
def stamp(msg: str) -> None:
    print(f"[stats] {msg}  (+{time.time() - T0:.1f}s)")

# ————————————————————————————————————————————————————————
# Repo paths
# ————————————————————————————————————————————————————————
ROOT        = Path(__file__).resolve().parents[1]
DAILY_DIR   = ROOT / "logs" / "daily"
WEEKLY_DIR  = ROOT / "logs" / "weekly"
STATS_DIR   = ROOT / "stats"
PIE_DAILY   = STATS_DIR / "pies" / "daily"
PIE_WEEKLY  = STATS_DIR / "pies" / "weekly"
README      = ROOT / "README.md"

for p in (STATS_DIR, PIE_DAILY, PIE_WEEKLY, WEEKLY_DIR):
    p.mkdir(parents=True, exist_ok=True)

# ————————————————————————————————————————————————————————
# Regex patterns
# ————————————————————————————————————————————————————————
TOTAL_RE   = re.compile(r"Total:\s*(?:(\d+)h)?\s*(\d+)m", re.I)
SUBJECT_RE = re.compile(r"^###\s+(.+?)\s+\((\d+)m\)", re.I | re.M)

# ————————————————————————————————————————————————————————
# Containers
# ————————————————————————————————————————————————————————
daily_rows              = []                              # list[{date, minutes}]
weekly_totals           = defaultdict(int)                # ISO week → minutes
daily_subject_minutes   = defaultdict(dict)               # date → {subject: m}
weekly_subject_minutes  = defaultdict(lambda: defaultdict(int))

# ------------------------------------------------------------------
# 1) Parse daily Markdown logs
# ------------------------------------------------------------------
stamp("scan daily logs")

for md in sorted(DAILY_DIR.glob("20??-??-??.md")):
    date_str = md.stem                                    # YYYY-MM-DD
    text = md.read_text(encoding="utf-8")

    m_total = TOTAL_RE.search(text)
    if not m_total:
        continue                                          # skip if no Total line

    hours, mins = m_total.groups()
    total_m = (int(hours) if hours else 0) * 60 + int(mins)
    daily_rows.append({"date": date_str, "minutes": total_m})

    # subject breakdown
    for subj, m in SUBJECT_RE.findall(text):
        daily_subject_minutes[date_str][subj] = int(m)

    # ISO-week aggregation
    y, w, _ = dt.date.fromisoformat(date_str).isocalendar()
    iso_week = f"{y}-W{w:02d}"
    weekly_totals[iso_week] += total_m

    for subj, m in daily_subject_minutes[date_str].items():
        weekly_subject_minutes[iso_week][subj] += m

if not daily_rows:
    print("[stats] ✗  no logs found – abort")
    raise SystemExit(0)

# ------------------------------------------------------------------
# 2) Export CSVs
# ------------------------------------------------------------------
stamp("export CSV")

(STATS_DIR / "daily_minutes.csv").write_text(
    "date,minutes\n" + "\n".join(f"{r['date']},{r['minutes']}" for r in daily_rows),
    encoding="utf-8"
)

(STATS_DIR / "weekly_minutes.csv").write_text(
    "iso_week,minutes\n" + "\n".join(f"{w},{m}" for w, m in sorted(weekly_totals.items())),
    encoding="utf-8"
)

# ------------------------------------------------------------------
# 3) Helpers – pie chart generator
# ------------------------------------------------------------------
def save_pie(data: dict, path: Path, title: str) -> None:
    """Save a 4×4 in pie chart if data is non-empty."""
    if not data:
        return
    labels, values = zip(*[(k, v) for k, v in data.items() if v > 0])
    plt.figure(figsize=(4, 4))
    plt.pie(values, labels=labels, autopct="%1.0f%%", startangle=90)
    plt.title(title)
    plt.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(path, dpi=120)
    plt.close()

# ------------------------------------------------------------------
# 4) Weekly line chart
# ------------------------------------------------------------------
stamp("generate weekly line chart")

weeks   = [w for w, _ in sorted(weekly_totals.items())]
minutes = [weekly_totals[w] for w in weeks]

plt.figure(figsize=(8, 4))
plt.plot(weeks, minutes, marker="o")
plt.xticks(rotation=45, ha="right", fontsize=8)
plt.ylabel("Minutes")
plt.title("Weekly Study Time")
plt.tight_layout()
plt.savefig(STATS_DIR / "weekly_chart.png", dpi=120)
plt.close()

# ------------------------------------------------------------------
# 5) Subject pie charts
# ------------------------------------------------------------------
stamp("generate pie charts")

# per-day (last 30 days to save CI time)
CUTOFF_DAYS = 30
today = dt.date.today()

for date_str, data in daily_subject_minutes.items():
    if (today - dt.date.fromisoformat(date_str)).days > CUTOFF_DAYS:
        continue
    save_pie(data, PIE_DAILY / f"{date_str}_pie.png", f"{date_str}")

# per-week
for wk, data in weekly_subject_minutes.items():
    save_pie(data, PIE_WEEKLY / f"{wk}_pie.png", f"{wk}")

# ------------------------------------------------------------------
# 6) Create weekly review stub if missing
# ------------------------------------------------------------------
stamp("create missing weekly reviews")

for wk, mins in weekly_totals.items():
    md_path = WEEKLY_DIR / f"{wk}.md"
    if md_path.exists():
        continue
    year, num = wk.split("-W")
    md_path.write_text(
        f"# Week {num} Review ({wk})\n\n"
        f"**Total study time:** {mins} m ({mins/60:.2f} h)\n\n"
        f"> _Auto-generated on {dt.date.today()}_\n",
        encoding="utf-8",
    )

# ------------------------------------------------------------------
# 7) Patch / insert single total-hours badge in README
# ------------------------------------------------------------------
stamp("update README badge")

tot_hours = sum(r["minutes"] for r in daily_rows) / 60
html_badge = (
    f'  <img src="https://img.shields.io/badge/total hours-{tot_hours:.1f}h-blue" '
    f'alt="total hours">\n'
)

if README.exists():
    lines = README.read_text(encoding="utf-8").splitlines(keepends=True)
else:
    lines = ["# study-log\n"]

# -- A. remove any stale Markdown badge lines ----------------------
lines = [ln for ln in lines if not ln.lstrip().startswith("![total hours]")]

# -- B. try to replace existing HTML badge ------------------------
for i, ln in enumerate(lines):
    if 'alt="total hours"' in ln:
        indent = ln[: len(ln) - len(ln.lstrip())]
        lines[i] = indent + html_badge.lstrip()
        break
else:
    # -- C. insert into the centred <p> badge block ----------------
    inserted = False
    for i, ln in enumerate(lines):
        if ln.strip().startswith("<p") and "img.shields.io" in ln:
            if "</p>" in ln:
                lines[i] = ln.replace("</p>", html_badge.rstrip() + "</p>")
                inserted = True
                break
    # -- D. if no badge block exists, append one at top ------------
    if not inserted:
        badge_block = (
            '<p align="center">\n'
            f'{html_badge.rstrip()}\n'
            '</p>\n'
        )
        lines.insert(1, badge_block)

README.write_text("".join(lines), encoding="utf-8")

stamp("done")

print(
    f"[stats] days={len(daily_rows)} | weeks={len(weekly_totals)} | "
    f"total={tot_hours:.1f} h"
)
