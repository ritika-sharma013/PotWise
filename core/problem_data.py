"""Read and validate the research draft used by the Plant Problem Helper.

This module only retrieves symptom-linked research records. It does not score
causes or diagnose plants; the dataset does not define validated scoring rules.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable


DEFAULT_PROBLEM_DATA_PATH = (
    Path(__file__).resolve().parents[1] / "data" / "plant_problem_diagnostics.json"
)

ProblemRecord = dict[str, Any]
ProblemData = dict[str, Any]

_TOP_LEVEL_FIELDS = {
    "dataset_name",
    "version",
    "research_date",
    "status",
    "intended_use",
    "design_principle",
    "global_diagnostic_policy",
    "seasonal_context_rules",
    "sources",
    "plants",
}
_PLANT_FIELDS = {"plant_id", "display_name", "scientific_name", "problems"}
_PROBLEM_FIELDS = {
    "problem_id",
    "display_title",
    "symptom_labels",
    "possible_causes",
    "follow_up_questions",
    "safe_next_steps",
    "avoid_recommending_without_more_evidence",
    "source_ids",
    "evidence_scope",
    "evidence_notes",
}
_SEASONAL_FIELDS = {
    "condition_id",
    "label",
    "check_first",
    "interpretation",
    "must_not_assume",
    "source_ids",
}
_SOURCE_FIELDS = {"title", "organization", "url", "scope"}


class ProblemDataError(ValueError):
    """Raised when the diagnostic dataset cannot be safely used."""


def _is_non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _normalise_id(value: str) -> str:
    if not isinstance(value, str):
        return ""
    return " ".join(value.casefold().split())


def _require_fields(value: dict[str, Any], required: set[str], label: str, errors: list[str]) -> None:
    missing = sorted(required - value.keys())
    if missing:
        errors.append(f"{label} is missing required fields: {', '.join(missing)}")


def _validate_string_list(value: Any, label: str, errors: list[str]) -> None:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        errors.append(f"{label} must be a list of strings")


def validate_problem_data(payload: Any) -> list[str]:
    """Return clear schema and integrity errors without changing ``payload``."""

    errors: list[str] = []
    if not isinstance(payload, dict):
        return ["Top-level diagnostic data must be a JSON object"]

    _require_fields(payload, _TOP_LEVEL_FIELDS, "Top-level diagnostic data", errors)
    for field in ("dataset_name", "version", "research_date", "status", "intended_use", "design_principle"):
        if field in payload and not _is_non_empty_string(payload[field]):
            errors.append(f"Top-level field '{field}' must be a non-empty string")
    _validate_string_list(payload.get("global_diagnostic_policy"), "global_diagnostic_policy", errors)

    plants = payload.get("plants")
    if not isinstance(plants, list):
        errors.append("plants must be a list")
        plants = []
    seasonal_rules = payload.get("seasonal_context_rules")
    if not isinstance(seasonal_rules, list):
        errors.append("seasonal_context_rules must be a list")
        seasonal_rules = []
    sources = payload.get("sources")
    if not isinstance(sources, dict):
        errors.append("sources must be an object keyed by source ID")
        sources = {}

    source_ids: set[str] = set()
    for source_id, source in sources.items():
        if not _is_non_empty_string(source_id):
            errors.append("sources contains an empty source ID")
        source_key = _normalise_id(str(source_id))
        if source_key in source_ids:
            errors.append(f"Duplicate source ID: {source_id}")
        source_ids.add(source_key)
        if not isinstance(source, dict):
            errors.append(f"Source '{source_id}' must be an object")
            continue
        _require_fields(source, _SOURCE_FIELDS, f"Source '{source_id}'", errors)
        for field in _SOURCE_FIELDS:
            if field in source and not _is_non_empty_string(source[field]):
                errors.append(f"Source '{source_id}' field '{field}' must be a non-empty string")

    plant_ids: set[str] = set()
    problem_ids: set[str] = set()
    for plant_index, plant in enumerate(plants):
        label = f"Plant at index {plant_index}"
        if not isinstance(plant, dict):
            errors.append(f"{label} must be an object")
            continue
        _require_fields(plant, _PLANT_FIELDS, label, errors)
        plant_id = plant.get("plant_id")
        if not _is_non_empty_string(plant_id):
            errors.append(f"{label} has an invalid or missing plant_id")
            plant_key = ""
        else:
            plant_key = _normalise_id(plant_id)
            if plant_key in plant_ids:
                errors.append(f"Duplicate plant ID: {plant_id}")
            plant_ids.add(plant_key)
        for field in ("display_name", "scientific_name"):
            if field in plant and not _is_non_empty_string(plant[field]):
                errors.append(f"{label} field '{field}' must be a non-empty string")
        problems = plant.get("problems")
        if not isinstance(problems, list):
            errors.append(f"Plant '{plant_id or plant_index}' problems must be a list")
            continue
        for problem_index, problem in enumerate(problems):
            problem_label = f"Problem at plant '{plant_id or plant_index}', index {problem_index}"
            if not isinstance(problem, dict):
                errors.append(f"{problem_label} must be an object")
                continue
            _require_fields(problem, _PROBLEM_FIELDS, problem_label, errors)
            problem_id = problem.get("problem_id")
            if not _is_non_empty_string(problem_id):
                errors.append(f"{problem_label} has an invalid or missing problem_id")
            else:
                problem_key = _normalise_id(problem_id)
                if problem_key in problem_ids:
                    errors.append(f"Duplicate problem ID: {problem_id}")
                problem_ids.add(problem_key)
            _validate_string_list(problem.get("symptom_labels"), f"{problem_label} symptom_labels", errors)
            _validate_string_list(problem.get("follow_up_questions"), f"{problem_label} follow_up_questions", errors)
            _validate_string_list(problem.get("safe_next_steps"), f"{problem_label} safe_next_steps", errors)
            _validate_string_list(
                problem.get("avoid_recommending_without_more_evidence"),
                f"{problem_label} avoid_recommending_without_more_evidence",
                errors,
            )
            _validate_string_list(problem.get("source_ids"), f"{problem_label} source_ids", errors)
            if isinstance(problem.get("source_ids"), list):
                for source_id in problem["source_ids"]:
                    if _normalise_id(str(source_id)) not in source_ids:
                        errors.append(f"{problem_label} references missing source ID: {source_id}")
            causes = problem.get("possible_causes")
            if not isinstance(causes, list):
                errors.append(f"{problem_label} possible_causes must be a list")

    seasonal_ids: set[str] = set()
    for rule_index, rule in enumerate(seasonal_rules):
        label = f"Seasonal rule at index {rule_index}"
        if not isinstance(rule, dict):
            errors.append(f"{label} must be an object")
            continue
        _require_fields(rule, _SEASONAL_FIELDS, label, errors)
        condition_id = rule.get("condition_id")
        if not _is_non_empty_string(condition_id):
            errors.append(f"{label} has an invalid or missing condition_id")
        else:
            condition_key = _normalise_id(condition_id)
            if condition_key in seasonal_ids:
                errors.append(f"Duplicate seasonal condition ID: {condition_id}")
            seasonal_ids.add(condition_key)
        for field in ("check_first", "must_not_assume", "source_ids"):
            _validate_string_list(rule.get(field), f"{label} {field}", errors)
        if isinstance(rule.get("source_ids"), list):
            for source_id in rule["source_ids"]:
                if _normalise_id(str(source_id)) not in source_ids:
                    errors.append(f"{label} references missing source ID: {source_id}")

    return errors


def load_problem_data(path: str | Path | None = None) -> ProblemData:
    """Load and validate the research dataset, raising a clear error if unsafe."""

    data_path = Path(path) if path is not None else DEFAULT_PROBLEM_DATA_PATH
    if not data_path.exists():
        raise ProblemDataError(f"Diagnostic dataset not found: {data_path}")
    try:
        contents = data_path.read_text(encoding="utf-8")
        if not contents.strip():
            raise ProblemDataError(f"Diagnostic dataset is empty: {data_path}")
        payload = json.loads(contents)
    except ProblemDataError:
        raise
    except (OSError, UnicodeError) as exc:
        raise ProblemDataError(f"Could not read diagnostic dataset '{data_path}': {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ProblemDataError(f"Diagnostic dataset is malformed JSON: {exc}") from exc
    errors = validate_problem_data(payload)
    if errors:
        raise ProblemDataError("Invalid diagnostic dataset:\n- " + "\n- ".join(errors))
    return payload


def get_problems_for_plant(plant_id: str, path: str | Path | None = None) -> list[ProblemRecord]:
    """Return all problems for an exact normalized plant ID, or an empty list."""

    query = _normalise_id(plant_id)
    if not query:
        return []
    data = load_problem_data(path)
    return [
        problem
        for plant in data["plants"]
        if _normalise_id(plant["plant_id"]) == query
        for problem in plant["problems"]
    ]


def get_problem_by_id(
    problem_id: str,
    plant_id: str | None = None,
    path: str | Path | None = None,
) -> ProblemRecord | None:
    """Return one exact problem record, optionally restricted to one plant."""

    query = _normalise_id(problem_id)
    plant_query = _normalise_id(plant_id) if plant_id else None
    if not query:
        return None
    data = load_problem_data(path)
    for plant in data["plants"]:
        if plant_query is not None and _normalise_id(plant["plant_id"]) != plant_query:
            continue
        for problem in plant["problems"]:
            if _normalise_id(problem["problem_id"]) == query:
                return problem
    return None


def get_seasonal_context_rule(condition_id: str, path: str | Path | None = None) -> dict[str, Any] | None:
    """Return one exact seasonal context rule, or ``None`` if unknown."""

    query = _normalise_id(condition_id)
    if not query:
        return None
    data = load_problem_data(path)
    return next(
        (rule for rule in data["seasonal_context_rules"] if _normalise_id(rule["condition_id"]) == query),
        None,
    )


def get_source_records(source_ids: Iterable[str], path: str | Path | None = None) -> list[dict[str, Any]]:
    """Resolve source IDs to their trusted source records in input order."""

    data = load_problem_data(path)
    sources = data["sources"]
    return [sources[source_id] for source_id in source_ids if source_id in sources]


def get_sources_for_problem(problem: ProblemRecord, path: str | Path | None = None) -> list[dict[str, Any]]:
    """Resolve the source records referenced by a problem record."""

    source_ids = problem.get("source_ids", [])
    if not isinstance(source_ids, list):
        return []
    return get_source_records(source_ids, path)
