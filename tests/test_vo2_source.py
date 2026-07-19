import csv

from main import get_apple_health_vo2


def test_apple_health_vo2_uses_latest_dated_measurement(tmp_path):
    path = tmp_path / "vo2max.csv"
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["date", "vo2max_ml_kg_min"])
        writer.writeheader()
        writer.writerow({"date": "2026-06-01", "vo2max_ml_kg_min": "40.2"})
        writer.writerow({"date": "2026-07-08", "vo2max_ml_kg_min": "42.50"})

    value = get_apple_health_vo2(path)

    assert value == {"value": 42.5, "date": "2026-07-08", "source": "Apple Health"}


def test_apple_health_vo2_does_not_invent_pace_estimate_when_missing(tmp_path):
    assert get_apple_health_vo2(tmp_path / "missing.csv") is None
