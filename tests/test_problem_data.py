import json

import pytest

from core.problem_data import (
    ProblemDataError,
    get_problem_by_id,
    get_problems_for_plant,
    get_seasonal_context_rule,
    get_source_records,
    get_sources_for_problem,
    load_problem_data,
    validate_problem_data,
)
from core.problem_matcher import collect_follow_up_questions, find_problem_candidates


DATASET_PATH = "data/plant_problem_diagnostics.json"


def test_loads_real_dataset_and_exposes_expected_structure() -> None:
    data = load_problem_data(DATASET_PATH)

    assert len(data["plants"]) == 15
    assert data["plants"][0]["plant_id"] == "aloe_vera"
    assert get_problem_by_id("aloe_wet_soft_leaves", "aloe_vera", DATASET_PATH) is not None


def test_real_dataset_has_no_integrity_errors() -> None:
    data = load_problem_data(DATASET_PATH)

    assert validate_problem_data(data) == []


@pytest.mark.parametrize(
    ("contents", "message"),
    [
        ("", "empty"),
        ("not json", "malformed JSON"),
        (json.dumps([]), "Top-level diagnostic data must be a JSON object"),
        (json.dumps({"plants": []}), "missing required fields"),
    ],
)
def test_invalid_dataset_files_raise_clear_errors(tmp_path, contents: str, message: str) -> None:
    path = tmp_path / "diagnostics.json"
    path.write_text(contents, encoding="utf-8")

    with pytest.raises(ProblemDataError, match=message):
        load_problem_data(path)


def test_unknown_plant_and_problem_return_empty_or_none() -> None:
    assert get_problems_for_plant("not_a_plant", DATASET_PATH) == []
    assert get_problem_by_id("not_a_problem", path=DATASET_PATH) is None
    assert get_problem_by_id("aloe_wet_soft_leaves", "not_a_plant", DATASET_PATH) is None


def test_source_resolution_and_seasonal_lookup() -> None:
    problem = get_problem_by_id("aloe_wet_soft_leaves", path=DATASET_PATH)
    assert problem is not None
    sources = get_sources_for_problem(problem, DATASET_PATH)
    assert [source_id for source_id in problem["source_ids"]] == ["NC_Aloe", "KY_AloeSpots"]
    assert all("title" in source and "url" in source for source in sources)
    assert get_source_records(["NC_Aloe"], DATASET_PATH) == sources[:1]
    assert get_seasonal_context_rule("rainy_or_persistently_wet_spell", DATASET_PATH)["condition_id"] == (
        "rainy_or_persistently_wet_spell"
    )
    assert get_seasonal_context_rule("unknown_condition", DATASET_PATH) is None


def test_exact_symptom_matching_normalizes_case_and_whitespace() -> None:
    candidates = find_problem_candidates(" aloe_vera ", "  YELLOW   LEAVES ", DATASET_PATH)

    assert [problem["problem_id"] for problem in candidates] == ["aloe_wet_soft_leaves"]


def test_symptom_matching_rejects_substrings_and_unknown_symptoms() -> None:
    assert find_problem_candidates("aloe_vera", "yellow", DATASET_PATH) == []
    assert find_problem_candidates("aloe_vera", "unlisted symptom", DATASET_PATH) == []
    assert find_problem_candidates("unknown_plant", "yellow leaves", DATASET_PATH) == []


def test_multiple_matching_candidates_are_preserved_and_questions_deduplicated(tmp_path) -> None:
    data = load_problem_data(DATASET_PATH)
    data["plants"] = [
        {
            "plant_id": "demo",
            "display_name": "Demo",
            "scientific_name": "Demo species",
            "problems": [
                {
                    "problem_id": "demo_one",
                    "display_title": "One",
                    "symptom_labels": ["shared symptom"],
                    "possible_causes": [],
                    "follow_up_questions": ["Question one", "Shared question"],
                    "safe_next_steps": [],
                    "avoid_recommending_without_more_evidence": [],
                    "source_ids": [],
                    "evidence_scope": "test",
                    "evidence_notes": "",
                },
                {
                    "problem_id": "demo_two",
                    "display_title": "Two",
                    "symptom_labels": ["shared symptom"],
                    "possible_causes": [],
                    "follow_up_questions": ["Shared question", "Question two"],
                    "safe_next_steps": [],
                    "avoid_recommending_without_more_evidence": [],
                    "source_ids": [],
                    "evidence_scope": "test",
                    "evidence_notes": "",
                },
            ],
        }
    ]
    path = tmp_path / "diagnostics.json"
    path.write_text(json.dumps(data), encoding="utf-8")

    candidates = find_problem_candidates("demo", "shared symptom", path)

    assert [problem["problem_id"] for problem in candidates] == ["demo_one", "demo_two"]
    assert collect_follow_up_questions(candidates) == ["Question one", "Shared question", "Question two"]


def test_validation_detects_duplicate_ids_and_missing_sources(tmp_path) -> None:
    data = load_problem_data(DATASET_PATH)
    data["sources"] = {}
    data["plants"].append(data["plants"][0].copy())
    data["plants"][-1]["problems"] = [data["plants"][0]["problems"][0].copy()]
    errors = validate_problem_data(data)

    assert any("Duplicate plant ID" in error for error in errors)
    assert any("Duplicate problem ID" in error for error in errors)
    assert any("references missing source ID" in error for error in errors)
    path = tmp_path / "invalid.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ProblemDataError, match="Duplicate plant ID"):
        load_problem_data(path)
