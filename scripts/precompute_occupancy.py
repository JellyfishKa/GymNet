import csv
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "data" / "data.csv"
OUT_PATH = ROOT / "backend" / "app" / "services" / "occupancy_peak_factors.json"


def main():
    buckets = defaultdict(list)
    with open(CSV_PATH) as f:
        for row in csv.DictReader(f):
            key = f"{int(row['hour'])}_{int(row['day_of_week'])}"
            buckets[key].append(int(row["number_people"]))

    avgs = {k: sum(v) / len(v) for k, v in buckets.items()}
    max_avg = max(avgs.values())
    factors = {k: round(v / max_avg, 4) for k, v in avgs.items()}

    with open(CSV_PATH) as f:
        all_counts = [int(row["number_people"]) for row in csv.DictReader(f)]

    stats = {
        "peak_factors": factors,
        "global_avg_people": round(sum(all_counts) / len(all_counts), 2),
        "global_max_people": max(all_counts),
    }
    OUT_PATH.write_text(json.dumps(stats, indent=2))
    print(f"Written {len(factors)} factors to {OUT_PATH}")


if __name__ == "__main__":
    main()
