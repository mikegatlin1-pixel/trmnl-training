from main import header_status, load_plan_metadata, parse_plan_metadata


def test_parse_plan_metadata_exposes_confidence_and_freshness():
    metadata = parse_plan_metadata(
        """# Week 2026-W30
Phase: Base / Rebuild
Focus: Conservative week
Data confidence: LOW
Evidence cutoff: 2026-07-08
Fresh: Hevy: 0d old
Stale or missing: Workouts: 11d old; Sleep: 28d old
Planning rule: Conservative maintenance only.

## Mon 07/20 - Easy run
"""
    )

    assert metadata == {
        "phase": "Base / Rebuild",
        "focus": "Conservative week",
        "data_confidence": "LOW",
        "evidence_cutoff": "2026-07-08",
        "fresh": "Hevy: 0d old",
        "stale_or_missing": "Workouts: 11d old; Sleep: 28d old",
        "planning_rule": "Conservative maintenance only.",
    }


def test_load_plan_metadata_uses_latest_week_file(tmp_path):
    (tmp_path / "week_2026-W29.md").write_text("Data confidence: HIGH\n", encoding="utf-8")
    (tmp_path / "week_2026-W30.md").write_text(
        "Data confidence: LOW\nEvidence cutoff: 2026-07-08\n",
        encoding="utf-8",
    )

    metadata = load_plan_metadata(tmp_path)

    assert metadata["data_confidence"] == "LOW"
    assert metadata["evidence_cutoff"] == "2026-07-08"


def test_header_status_replaces_stale_hardcoded_phase_week():
    assert header_status({"data_confidence": "LOW", "phase": "Base / Rebuild"}, 4) == "LOW CONFIDENCE · BASE / REBUILD"
    assert header_status({}, 3) == "WEEK 3 / 4"
