from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, Iterable, List, Mapping, Sequence, TypedDict


UNKNOWN_OR_DECLINED = {"unknown", "declined"}


class FinalizeError(TypedDict):
    code: str
    message: str
    field_paths: List[str]


class FinalizeDecision(TypedDict):
    field_path: str
    status: str
    reason: str
    evidence_present: bool
    resolution: str | None


class FinalizeRationale(TypedDict):
    required_fields: List[str]
    decisions: List[FinalizeDecision]


class FinalizeResult(TypedDict):
    ok: bool
    finalized: Dict[str, Any] | None
    errors: List[FinalizeError]
    rationale: FinalizeRationale


def _get_value_at_path(payload: Mapping[str, Any], field_path: str) -> Any:
    node: Any = payload
    for part in field_path.split("."):
        if not isinstance(node, Mapping) or part not in node:
            return None
        node = node[part]
    return node


def _is_resolved_value(value: Any) -> bool:
    return value is not None


def _resolution_status(resolutions: Mapping[str, Any], field_path: str) -> str | None:
    raw = resolutions.get(field_path)
    if isinstance(raw, str):
        status = raw.strip().lower()
        return status if status in UNKNOWN_OR_DECLINED else None
    if isinstance(raw, Mapping):
        status = str(raw.get("status", "")).strip().lower()
        return status if status in UNKNOWN_OR_DECLINED else None
    return None


def finalize_schema(
    *,
    schema_object: Mapping[str, Any],
    evidence_map: Mapping[str, Any],
    required_fields: Sequence[str],
    resolutions: Mapping[str, Any] | None = None,
) -> FinalizeResult:
    """
    Validate and finalize a schema instance.

    Rules:
    1) Required fields must have either evidence-backed value OR explicit unknown/declined resolution.
    2) Failures include machine-readable errors with field paths.
    3) On success, persistable payload includes schema object + per-field evidence map.
    4) Response includes rationale for explainability demos.
    """
    normalized_resolutions: Mapping[str, Any] = resolutions or {}

    missing_evidence: List[str] = []
    unresolved_required: List[str] = []
    decisions: List[FinalizeDecision] = []

    for field_path in required_fields:
        value = _get_value_at_path(schema_object, field_path)
        resolution = _resolution_status(normalized_resolutions, field_path)
        evidence_present = field_path in evidence_map

        if _is_resolved_value(value):
            if evidence_present:
                decisions.append(
                    {
                        "field_path": field_path,
                        "status": "accepted",
                        "reason": "value_has_evidence",
                        "evidence_present": True,
                        "resolution": None,
                    }
                )
            else:
                missing_evidence.append(field_path)
                decisions.append(
                    {
                        "field_path": field_path,
                        "status": "rejected",
                        "reason": "value_missing_evidence",
                        "evidence_present": False,
                        "resolution": None,
                    }
                )
            continue

        if resolution in UNKNOWN_OR_DECLINED:
            decisions.append(
                {
                    "field_path": field_path,
                    "status": "accepted",
                    "reason": "explicit_resolution",
                    "evidence_present": evidence_present,
                    "resolution": resolution,
                }
            )
            continue

        unresolved_required.append(field_path)
        decisions.append(
            {
                "field_path": field_path,
                "status": "rejected",
                "reason": "missing_value_and_resolution",
                "evidence_present": evidence_present,
                "resolution": None,
            }
        )

    errors: List[FinalizeError] = []
    if missing_evidence:
        errors.append(
            {
                "code": "required_fields_missing_evidence",
                "message": "Required fields have values but no backing evidence.",
                "field_paths": sorted(missing_evidence),
            }
        )
    if unresolved_required:
        errors.append(
            {
                "code": "required_fields_unresolved",
                "message": "Required fields need evidence-backed values or explicit unknown/declined resolution.",
                "field_paths": sorted(unresolved_required),
            }
        )

    ok = not errors

    rationale: FinalizeRationale = {
        "required_fields": list(required_fields),
        "decisions": decisions,
    }

    if not ok:
        return {
            "ok": False,
            "finalized": None,
            "errors": errors,
            "rationale": rationale,
        }

    return {
        "ok": True,
        "finalized": {
            "schema_object": deepcopy(dict(schema_object)),
            "evidence_map": deepcopy(dict(evidence_map)),
        },
        "errors": [],
        "rationale": rationale,
    }


__all__ = ["finalize_schema", "FinalizeResult"]
