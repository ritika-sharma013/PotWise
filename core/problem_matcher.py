"""Conservative symptom-to-problem retrieval for the research draft.

Matching retrieves every exact symptom-label match. It does not rank causes,
calculate confidence, or claim a diagnosis.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from core.problem_data import ProblemRecord, get_problems_for_plant


def _normalise_symptom(value: str) -> str:
    if not isinstance(value, str):
        return ""
    return " ".join(value.casefold().split())


def find_problem_candidates(
    plant_id: str,
    selected_symptom: str,
    path: str | Path | None = None,
) -> list[ProblemRecord]:
    """Return all problems whose symptom label exactly matches the selection."""

    query = _normalise_symptom(selected_symptom)
    if not query:
        return []
    candidates: list[ProblemRecord] = []
    for problem in get_problems_for_plant(plant_id, path):
        labels = problem.get("symptom_labels", [])
        if isinstance(labels, list) and any(
            isinstance(label, str) and _normalise_symptom(label) == query for label in labels
        ):
            candidates.append(problem)
    return candidates


def collect_follow_up_questions(candidates: list[ProblemRecord]) -> list[str]:
    """Collect unique questions in first-seen order without inventing content."""

    questions: list[str] = []
    seen: set[str] = set()
    for problem in candidates:
        values: Any = problem.get("follow_up_questions", [])
        if not isinstance(values, list):
            continue
        for question in values:
            if isinstance(question, str) and question not in seen:
                seen.add(question)
                questions.append(question)
    return questions
