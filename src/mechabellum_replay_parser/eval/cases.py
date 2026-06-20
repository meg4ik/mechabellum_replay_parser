from __future__ import annotations

import json
import shutil
from pathlib import Path

from pydantic import BaseModel

from ..coach.schemas import StateView


class EvalExpected(BaseModel):
    must_address_threats: list[str] = []
    recommended_response_types: list[str] = []
    forbidden_response_types: list[str] = []
    acceptable_units: list[str] = []
    placement_expectations: list[dict] = []

    expected_influence_findings: list[str] = []
    expected_critical_zones: list[str] = []
    forbidden_high_severity_findings: list[str] = []


class EvalCase(BaseModel):
    name: str
    description: str = ""
    state_view: StateView
    expected: EvalExpected


def load_case(case_dir: Path) -> EvalCase:
    sv_path = case_dir / "state_view.json"
    expected_path = case_dir / "expected.json"
    if not sv_path.exists():
        raise FileNotFoundError(f"state_view.json missing in {case_dir}")
    if not expected_path.exists():
        raise FileNotFoundError(f"expected.json missing in {case_dir}")

    state_view = StateView.model_validate_json(sv_path.read_text(encoding="utf-8"))
    expected = EvalExpected.model_validate_json(
        expected_path.read_text(encoding="utf-8")
    )

    meta: dict = {}
    meta_path = case_dir / "metadata.json"
    if meta_path.exists():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))

    return EvalCase(
        name=meta.get("name", case_dir.name),
        description=meta.get("description", ""),
        state_view=state_view,
        expected=expected,
    )


def load_all_cases(cases_dir: Path) -> list[EvalCase]:
    cases: list[EvalCase] = []
    if not cases_dir.is_dir():
        return cases
    for case_dir in sorted(cases_dir.iterdir()):
        if case_dir.is_dir() and (case_dir / "state_view.json").exists():
            try:
                cases.append(load_case(case_dir))
            except Exception:  # noqa: BLE001
                pass
    return cases


def save_case_from_debug(
    name: str,
    expected: EvalExpected,
    debug_dir: Path = Path(".debug"),
    cases_dir: Path = Path("eval_cases"),
    description: str = "",
) -> EvalCase:
    """Create an eval case from the most recent .debug/ pipeline run."""
    sv_path = debug_dir / "latest_state_view.json"
    if not sv_path.exists():
        raise FileNotFoundError(
            f"No debug state view at {sv_path}. Run the full pipeline first (DEBUG=1)."
        )
    state_view = StateView.model_validate_json(sv_path.read_text(encoding="utf-8"))

    case_dir = cases_dir / name
    case_dir.mkdir(parents=True, exist_ok=True)

    (case_dir / "state_view.json").write_text(
        state_view.model_dump_json(indent=2), encoding="utf-8"
    )
    (case_dir / "expected.json").write_text(
        expected.model_dump_json(indent=2), encoding="utf-8"
    )
    (case_dir / "metadata.json").write_text(
        json.dumps({"name": name, "description": description}, indent=2),
        encoding="utf-8",
    )

    _ARTIFACT_MAP = {
        "latest_features.json": "features.json",
        "latest_legal_actions.json": "legal_actions.json",
        "latest_bundles.json": "tactical_bundles.json",
    }
    for src_name, dst_name in _ARTIFACT_MAP.items():
        src = debug_dir / src_name
        if src.exists():
            shutil.copy2(src, case_dir / dst_name)

    return EvalCase(
        name=name, description=description, state_view=state_view, expected=expected
    )
