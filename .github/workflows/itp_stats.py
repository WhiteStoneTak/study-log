from pathlib import Path
import csv, re, collections
import matplotlib.pyplot as plt

ROOT   = Path(__file__).resolve().parents[1]
WRONG  = ROOT / "it-passport" / "wrong"
STATS  = ROOT / "stats"

# Ensure directories exist
WRONG.mkdir(parents=True, exist_ok=True)
STATS.mkdir(parents=True, exist_ok=True)

cat_count = collections.Counter()

for md in WRONG.glob("*.md"):
    txt = md.read_text(encoding="utf-8")

    # Skip resolved questions
    if "status: ✅ Resolved" in txt:
        continue

    # Extract category (case-insensitive)
    m = re.search(r"category:\s*(\w+)", txt, re.I)
    if m:
        cat = m.group(1).capitalize()   # unify capitalization
        cat_count[cat] += 1

# ── CSV output ─────────────────────────────────────
with (STATS / "itp_weekly.csv").open("w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["category", "count"])
    writer.writerows(cat_count.items())

# ── Pie chart ──────────────────────────────────────
if cat_count:
    plt.figure(figsize=(4, 4))
    plt.pie(cat_count.values(), labels=cat_count.keys(), autopct="%1.0f%%", startangle=90)
    plt.title("Unresolved IT Passport Questions")
    plt.tight_layout()
    plt.savefig(STATS / "itp_pie.png", dpi=150)
    plt.close()
