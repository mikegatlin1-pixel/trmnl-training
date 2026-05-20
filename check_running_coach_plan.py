#!/usr/bin/env python3
from __future__ import annotations

from datetime import date, timedelta

import main


def main_cli() -> int:
    plan = main.load_plan_from_running_coach()
    if not plan:
        print("No RunningCoach weekly plan rows found.")
        return 1

    today = date.today()
    horizon = today + timedelta(days=10)
    upcoming = [
        row for row in plan
        if today.isoformat() <= row["iso"] <= horizon.isoformat()
    ]

    print(f"RunningCoach rows loaded: {len(plan)}")
    print(f"Upcoming rows through {horizon.isoformat()}: {len(upcoming)}")
    for row in upcoming:
        hr = " HR" if row.get("hr") else ""
        print(f"{row['iso']} | {row['type']} | {row['title']} | {row['dur']}{hr}")

    return 0 if upcoming else 1


if __name__ == "__main__":
    raise SystemExit(main_cli())
