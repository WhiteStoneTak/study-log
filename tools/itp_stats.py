#!/usr/bin/env python3
"""
IT-Passport wrong-answer tracker
────────────────────────────────
• Reads Markdown files in it-passport/wrong/
• Counts unresolved questions by category
• Exports:
    stats/itp_weekly.csv   – "category,count"
    stats/itp_pie.png      – pie chart of unresolved ratios
"""

# ————————————————————————————————————————————————————————
# Imports & paths
# ————————————————————————————————————————————————————————
from pathlib import Path
import csv, re, collections, matplotlib.pyplot as plt, time

ROOT   = Path(__file__).resolve().parents[1]
WRONG  = ROOT / "it-passport" / "wrong"
STATS  = ROOT / "stats"
WRONG.mkdir(parents=True,  exist_ok=True)
STATS.mkdir(parents=True, exist_ok=True)

T0 = time.time()
def stamp(msg: str) -> None:
    print(f"[itp-stats] {msg} (+{time.time() - T0:.1f}s)")

# ————————————————————————————————————————————————————————
# 1) Count unresolved questions per category
# ————————————————————————————————————————————————————————
stamp("scan wrong/")

cat_count = collections.Counter()

for md in WRONG.glob("*.md"):
    text = md.read_text(encoding="utf-8")

    if "status: ✅ Resolved" in text:
        continue                                   # skip solved questions

    m = re.search(r"category:\s*(\w+)", text, re.I)
    if m:
        cat = m.group(1).capitalize()              # unify capitalisation
        cat_count[cat] += 1

if not cat_count:
    print("[itp-stats] ✗ no unresolved questions – nothing to do")
    raise SystemExit(0)

# ————————————————————————————————————————————————————————
# 2) CSV export
# ————————————————————————————————————————————————————————
stamp("export CSV")

csv_path = STATS / "itp_weekly.csv"
with csv_path.open("w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["category", "count"])
    writer.writerows(cat_count.items())

# ————————————————————————————————————————————————————————
# 3) Pie chart export
# ————————————————————————————————————————————————————————
stamp("generate pie chart")

plt.figure(figsize=(4, 4))
plt.pie(
    cat_count.values(),
    labels=cat_count.keys(),
    autopct="%1.0f%%",
    startangle=90,
)
plt.title("Unresolved IT-Passport Questions")
plt.tight_layout()
plt.savefig(STATS / "itp_pie.png", dpi=120)
plt.close()

stamp("done")
print(f"[itp-stats] total unresolved = {sum(cat_count.values())}")
