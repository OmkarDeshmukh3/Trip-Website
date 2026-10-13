from pathlib import Path
import csv
import json
from datetime import datetime, timezone

BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "data" / "recommendation_training.csv"
MODEL_PATH = BASE_DIR / "models" / "trip_recommender.json"
REQUIRED = {"budget_per_person_day", "days", "interest", "destination"}


def train():
    """Prepare the prototype KNN model from the editable CSV training profiles.

    This project keeps the labelled training rows as its model artifact. At prediction
    time recommendation_engine.py compares a new trip profile with these examples.
    The included rows are synthetic demo examples, not real customer behaviour.
    """
    if not DATA_PATH.exists():
        raise FileNotFoundError(f"Training data not found: {DATA_PATH}")

    with DATA_PATH.open(newline="", encoding="utf-8-sig") as source:
        reader = csv.DictReader(source)
        if not REQUIRED.issubset(set(reader.fieldnames or [])):
            raise ValueError("Training CSV must contain: " + ", ".join(sorted(REQUIRED)))
        samples = []
        for row in reader:
            try:
                budget = float(row["budget_per_person_day"])
                days = int(row["days"])
                interest = row["interest"].strip()
                destination = row["destination"].strip()
                if budget > 0 and days > 0 and interest and destination:
                    samples.append({
                        "budget_per_person_day": budget,
                        "days": days,
                        "interest": interest,
                        "destination": destination,
                    })
            except (ValueError, TypeError):
                continue

    if not samples:
        raise ValueError("No valid training rows found. Check data/recommendation_training.csv")

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "model_name": "TripGenie KNN Destination Recommender",
        "algorithm": "K-nearest-neighbours over normalized budget, days, and interest",
        "trained_at_utc": datetime.now(timezone.utc).isoformat(),
        "training_rows": len(samples),
        "destinations": sorted({row["destination"] for row in samples}),
        "training_data": "data/recommendation_training.csv",
        "training_data_note": "Synthetic college-project examples. Replace with curated/anonymized real trip examples for stronger recommendations.",
        "samples": samples,
    }
    MODEL_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Training data loaded: {len(samples)} rows")
    print(f"Destination classes: {len(payload['destinations'])}")
    print(f"Model saved to: {MODEL_PATH.relative_to(BASE_DIR)}")
    print("Note: included profiles are synthetic demonstration data, not real traveler records.")


if __name__ == "__main__":
    train()
