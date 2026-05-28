import csv
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "data" / "gym_members_exercise_tracking.csv"
OUT_PATH = ROOT / "backend" / "app" / "services" / "calories_per_exercise.json"


def main():
    by_type = defaultdict(list)
    with open(CSV_PATH) as f:
        for row in csv.DictReader(f):
            duration = float(row["Session_Duration (hours)"])
            calories = float(row["Calories_Burned"])
            if duration > 0:
                by_type[row["Workout_Type"]].append(calories / duration)

    cal_per_hour = {k: round(sum(v) / len(v), 1) for k, v in by_type.items()}
    print("Cal/hour by type:", cal_per_hour)

    result = {
        "PushUps": cal_per_hour.get("Strength", 500.0),
        "Squats": cal_per_hour.get("Strength", 500.0),
        "RunInPlace": cal_per_hour.get("Cardio", 600.0),
        "_source": cal_per_hour,
    }
    OUT_PATH.write_text(json.dumps(result, indent=2))
    print(f"Written to {OUT_PATH}")


if __name__ == "__main__":
    main()
