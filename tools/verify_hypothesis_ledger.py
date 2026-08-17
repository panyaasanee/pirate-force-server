"""Strict verifier for the canonical bounded-hypothesis ledger."""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LEDGER = ROOT / "docs" / "HYPOTHESIS_LEDGER.json"
# Lineage: 08FD966F.. (HYP-PF-011 append, round 34) -> 276FF122.. (2026-08-17:
# HYP-PF-010 evidence_gap rewritten + GT-002 runtime report appended to
# evidence_refs after the first real-client acceptance, commit b1087bb lineage).
CANONICAL_CONTENT_SHA256 = "276FF122492DB72E308A0104E6A125DB0F14D5DC243F41ED8E2A48AF3076B712"
IMMUTABLE_V141_PATH = "current/pf_login_game_server_v141.py"
IMMUTABLE_V141_SHA256 = "2EB05ED2FDBDD5EE3D91F7FBB8C1D16A4C7A02A843BC97169B16A389E4EA4C22"
ANNOTATION_RE = re.compile(
    r"^\s*# PF-HYPOTHESIS-LEDGER: ([A-Z]+-PF-[0-9]{3}) "
    r"(active|frozen|retired|harness_only)\s*$", re.MULTILINE,
)
EXPECTED_IDS = (
    "HYP-PF-001", "HYP-PF-002", "HYP-PF-003", "HYP-PF-004",
    "HYP-PF-005", "HYP-PF-006", "HYP-PF-007", "HYP-PF-008",
    "HYP-PF-009", "HYP-PF-010",
    "DIAG-PF-001",
    "RET-PF-001", "GEO-PF-001", "GEO-PF-002", "GEO-PF-003",
    "GEO-PF-004", "GEO-PF-005",
    # HYP-PF-011 is appended after the geometry block on purpose: the ledger
    # list order is canonical, and appending keeps every existing entry index
    # stable for the index-based test fixtures (the round-31 lesson).
    "HYP-PF-011",
)
EXPECTED_META = {
    "HYP-PF-001": ("protocol_hypothesis", "SCENE-005", "frozen"),
    "HYP-PF-002": ("protocol_hypothesis", "SCENE-007", "frozen"),
    "HYP-PF-003": ("protocol_hypothesis", "V134", "expired_pending_decision"),
    "HYP-PF-004": ("protocol_hypothesis", "V136", "expired_pending_decision"),
    "HYP-PF-005": ("protocol_hypothesis", "V137", "expired_pending_decision"),
    "HYP-PF-006": ("protocol_hypothesis", "V138", "expired_pending_decision"),
    "HYP-PF-007": ("protocol_hypothesis", "SCENE-001", "expired_pending_decision"),
    "HYP-PF-008": ("protocol_hypothesis", "ITEM-MOVE-HYP-001", "active"),
    "HYP-PF-009": (
        "protocol_hypothesis", "SECOND-PASSWORD-BYPASS-001", "active",
    ),
    "HYP-PF-010": ("protocol_hypothesis", "ITEM-MOVE-GEN-001", "active"),
    "DIAG-PF-001": ("diagnostic_value", "SCENE-003", "expired_pending_decision"),
    "RET-PF-001": ("retired_claim", "ARENA-002", "retired"),
    "GEO-PF-001": ("test_geometry", "ARENA-001", "harness_only"),
    "GEO-PF-002": ("test_geometry", "SCENE-002", "expired_pending_decision"),
    "GEO-PF-003": ("test_geometry", "SCENE-007", "expired_pending_decision"),
    "GEO-PF-004": ("test_geometry", "V135", "expired_pending_decision"),
    "GEO-PF-005": ("test_geometry", "V140", "harness_only"),
    "HYP-PF-011": ("protocol_hypothesis", "MULTI-CLIENT-001", "active"),
}
KINDS = {"protocol_hypothesis", "diagnostic_value", "retired_claim", "test_geometry"}
STATUSES = {"active", "frozen", "retired", "harness_only", "expired_pending_decision"}
COMMON_FIELDS = {
    "id", "kind", "introduced_checkpoint", "exact_value_or_transform", "scope",
    "status", "provenance", "evidence_refs", "accepted_ceiling", "evidence_gap",
    "falsification", "stop_rule", "production_allowed", "expiry", "max_versions",
    "extension_approval_ref", "source_refs",
}


class LedgerError(ValueError):
    """The canonical hypothesis ledger is malformed or has drifted."""


def _exact_fields(value: dict[str, Any], expected: set[str], label: str) -> None:
    if set(value) != expected:
        missing = sorted(expected - set(value))
        extra = sorted(set(value) - expected)
        raise LedgerError(f"{label} fields mismatch; missing={missing}, extra={extra}")


def _text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise LedgerError(f"{label} must be a non-empty string")
    return value


def _string_list(value: Any, label: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not value:
        raise LedgerError(f"{label} must be a non-empty list")
    result = tuple(_text(item, f"{label} item") for item in value)
    if len(result) != len(set(result)):
        raise LedgerError(f"{label} contains duplicates")
    return result


def _repo_path(root: Path, raw: Any, label: str) -> Path:
    text = _text(raw, label)
    posix = PurePosixPath(text)
    if posix.is_absolute() or ".." in posix.parts or "\\" in text:
        raise LedgerError(f"{label} must be a safe repo-relative POSIX path")
    path = (root / Path(*posix.parts)).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError as exc:
        raise LedgerError(f"{label} escapes the repository") from exc
    if not path.is_file():
        raise LedgerError(f"{label} does not exist: {text}")
    return path


@dataclass(frozen=True)
class SourceRef:
    path: str
    required_markers: tuple[str, ...]
    active_claim_marker: bool
    immutable: bool

    @classmethod
    def parse(cls, value: Any, root: Path, label: str) -> "SourceRef":
        if not isinstance(value, dict):
            raise LedgerError(f"{label} must be an object")
        immutable = value.get("immutable") is True
        expected = {"path", "required_markers", "active_claim_marker"}
        if immutable:
            expected |= {"immutable", "sha256", "immutable_anchors"}
        _exact_fields(value, expected, label)
        path_text = _text(value["path"], f"{label}.path")
        path = _repo_path(root, path_text, f"{label}.path")
        markers = _string_list(value["required_markers"], f"{label}.required_markers")
        active = value["active_claim_marker"]
        if type(active) is not bool:
            raise LedgerError(f"{label}.active_claim_marker must be bool")
        try:
            contents = path.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            raise LedgerError(f"{label}.path must be UTF-8 text") from exc
        for marker in markers:
            if marker not in contents:
                raise LedgerError(f"{label} marker not found in {path_text}: {marker!r}")
        if immutable:
            if path_text != IMMUTABLE_V141_PATH:
                raise LedgerError(f"{label} immutable exception is not allowlisted")
            if value["sha256"] != IMMUTABLE_V141_SHA256:
                raise LedgerError(f"{label} immutable SHA-256 drift")
            if hashlib.sha256(path.read_bytes()).hexdigest().upper() != IMMUTABLE_V141_SHA256:
                raise LedgerError(f"{label} immutable file hash mismatch")
            anchors = _string_list(value["immutable_anchors"], f"{label}.immutable_anchors")
            for anchor in anchors:
                if contents.count(anchor) != 1:
                    raise LedgerError(f"{label} immutable anchor must occur exactly once: {anchor!r}")
        return cls(path_text, markers, active, immutable)


@dataclass(frozen=True)
class Expiry:
    tracked_versions: tuple[str, ...]
    decision: str

    @classmethod
    def parse(cls, value: Any, label: str) -> "Expiry":
        if not isinstance(value, dict):
            raise LedgerError(f"{label} must be an object")
        _exact_fields(value, {"tracked_versions", "decision"}, label)
        return cls(
            _string_list(value["tracked_versions"], f"{label}.tracked_versions"),
            _text(value["decision"], f"{label}.decision"),
        )


@dataclass(frozen=True)
class Entry:
    id: str
    kind: str
    introduced_checkpoint: str
    status: str
    expiry: Expiry
    source_refs: tuple[SourceRef, ...]
    extension_approval_ref: dict[str, Any] | None

    @classmethod
    def parse(cls, value: Any, root: Path, index: int) -> "Entry":
        label = f"entries[{index}]"
        if not isinstance(value, dict):
            raise LedgerError(f"{label} must be an object")
        kind = value.get("kind")
        expected_fields = COMMON_FIELDS | ({"authentic"} if kind == "test_geometry" else set())
        _exact_fields(value, expected_fields, label)
        ident = _text(value["id"], f"{label}.id")
        kind = _text(kind, f"{label}.kind")
        checkpoint = _text(value["introduced_checkpoint"], f"{label}.introduced_checkpoint")
        status = _text(value["status"], f"{label}.status")
        if kind not in KINDS or status not in STATUSES:
            raise LedgerError(f"{label} has unknown kind/status")
        expected = EXPECTED_META.get(ident)
        if expected is None:
            raise LedgerError(f"unknown hypothesis id: {ident}")
        if (kind, checkpoint, status) != expected:
            raise LedgerError(f"{ident} metadata drift: {(kind, checkpoint, status)!r} != {expected!r}")

        for name in (
            "exact_value_or_transform", "scope", "provenance", "accepted_ceiling",
            "evidence_gap", "falsification", "stop_rule",
        ):
            _text(value[name], f"{label}.{name}")
        evidence_refs = _string_list(value["evidence_refs"], f"{label}.evidence_refs")
        for number, ref in enumerate(evidence_refs):
            _repo_path(root, ref, f"{label}.evidence_refs[{number}]")

        if value["production_allowed"] is not False:
            raise LedgerError(f"{ident} production_allowed must be false")
        max_versions = value["max_versions"]
        if type(max_versions) is not int or max_versions != 3:
            raise LedgerError(f"{ident} max_versions must be exactly 3")
        approval = value["extension_approval_ref"]
        approved_through = None
        if approval is not None:
            if not isinstance(approval, dict):
                raise LedgerError(f"{ident} extension approval must be a scoped object")
            _exact_fields(
                approval, {"approval_id", "approved_entry_ids", "approved_through"},
                f"{label}.extension_approval_ref",
            )
            _text(approval["approval_id"], f"{label}.extension_approval_ref.approval_id")
            approved_ids = _string_list(
                approval["approved_entry_ids"],
                f"{label}.extension_approval_ref.approved_entry_ids",
            )
            if ident not in approved_ids or any(item not in EXPECTED_IDS for item in approved_ids):
                raise LedgerError(f"{ident} approval is not scoped to canonical IDs")
            approved_through = _text(
                approval["approved_through"],
                f"{label}.extension_approval_ref.approved_through",
            )
        expiry = Expiry.parse(value["expiry"], f"{label}.expiry")
        if approval is not None and approved_through != expiry.tracked_versions[-1]:
            raise LedgerError(f"{ident} approval must end at the last tracked checkpoint")
        if len(expiry.tracked_versions) > max_versions:
            if approval is None and status not in {"frozen", "expired_pending_decision"}:
                raise LedgerError(f"{ident} exceeds max_versions but is not expired/frozen")
        elif approval is not None:
            raise LedgerError(f"{ident} has extension approval without exceeding max_versions")

        refs_value = value["source_refs"]
        if not isinstance(refs_value, list) or not refs_value:
            raise LedgerError(f"{label}.source_refs must be a non-empty list")
        refs = tuple(SourceRef.parse(item, root, f"{label}.source_refs[{i}]") for i, item in enumerate(refs_value))
        if len({ref.path for ref in refs}) != len(refs):
            raise LedgerError(f"{ident} source_refs contains duplicate paths")
        if status in {"active", "frozen", "harness_only", "expired_pending_decision"} and not any(ref.active_claim_marker for ref in refs):
            raise LedgerError(f"{ident} requires an active source marker")
        if kind == "retired_claim":
            if status != "retired" or any(ref.active_claim_marker for ref in refs):
                raise LedgerError(f"{ident} retired claim cannot have an active source marker")
            if approval is not None:
                raise LedgerError(f"{ident} retired claim cannot have an extension approval")
        if kind == "test_geometry":
            if value["authentic"] is not False:
                raise LedgerError(f"{ident} geometry authentic must be false")
            if status not in {"harness_only", "expired_pending_decision"}:
                raise LedgerError(f"{ident} geometry must be harness-only or expired")
        return cls(ident, kind, checkpoint, status, expiry, refs, approval)


@dataclass(frozen=True)
class Ledger:
    schema: int
    entries: tuple[Entry, ...]


def _annotation_state(status: str) -> str:
    if status in {"frozen", "expired_pending_decision"}:
        return "frozen"
    return status


def verify_source_annotations(
    entries: tuple[Entry, ...], root: Path, *,
    scan_items: list[tuple[str, str]] | None = None,
    require_complete: bool = True,
) -> None:
    """Bidirectionally bind inline emitter annotations to canonical source refs."""
    declared: dict[tuple[str, str], str] = {}
    for entry in entries:
        expected_state = _annotation_state(entry.status)
        for ref in entry.source_refs:
            if ref.immutable or not ref.path.endswith(".py"):
                continue
            key = (ref.path, entry.id)
            if key in declared:
                raise LedgerError(f"duplicate declared emitter: {key!r}")
            declared[key] = expected_state

    if scan_items is None:
        paths = [*sorted((root / "src").rglob("*.py")), *sorted((root / "scenarios").glob("*.json"))]
        scan_items = [
            (path.relative_to(root).as_posix(), path.read_text(encoding="utf-8"))
            for path in paths if "__pycache__" not in path.parts
        ]
    observed: set[tuple[str, str]] = set()
    for path_text, contents in scan_items:
        for match in ANNOTATION_RE.finditer(contents):
            ident, state = match.groups()
            if ident not in EXPECTED_META:
                raise LedgerError(f"unregistered emitter annotation {ident} in {path_text}")
            key = (path_text, ident)
            if key not in declared:
                raise LedgerError(f"annotation is not declared by source_refs: {key!r}")
            if state != declared[key]:
                raise LedgerError(
                    f"annotation state mismatch for {key!r}: {state!r} != {declared[key]!r}"
                )
            if key in observed:
                raise LedgerError(f"duplicate emitter annotation: {key!r}")
            observed.add(key)
    if require_complete:
        missing = sorted(set(declared) - observed)
        if missing:
            raise LedgerError(f"declared emitter is missing adjacent annotation: {missing!r}")


def load_ledger(path: Path = DEFAULT_LEDGER, *, root: Path = ROOT) -> Ledger:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise LedgerError(f"cannot read ledger: {exc}") from exc
    if not isinstance(raw, dict):
        raise LedgerError("ledger root must be an object")
    _exact_fields(raw, {"schema", "policy", "entries"}, "ledger")
    if raw["schema"] != 1 or type(raw["schema"]) is not int:
        raise LedgerError("ledger schema must be integer 1")
    policy = raw["policy"]
    if not isinstance(policy, dict):
        raise LedgerError("policy must be an object")
    _exact_fields(policy, {"max_related_versions", "approval_schema", "policy_text"}, "policy")
    if policy["max_related_versions"] != 3 or type(policy["max_related_versions"]) is not int:
        raise LedgerError("policy max_related_versions must be integer 3")
    approval_schema = policy["approval_schema"]
    if not isinstance(approval_schema, dict):
        raise LedgerError("policy approval_schema must be an object")
    _exact_fields(approval_schema, {"required_fields", "rule"}, "policy.approval_schema")
    if _string_list(approval_schema["required_fields"], "policy.approval_schema.required_fields") != (
        "approval_id", "approved_entry_ids", "approved_through",
    ):
        raise LedgerError("policy approval fields drift")
    _text(approval_schema["rule"], "policy.approval_schema.rule")
    _text(policy["policy_text"], "policy.policy_text")
    values = raw["entries"]
    if not isinstance(values, list):
        raise LedgerError("entries must be a list")
    entries = tuple(Entry.parse(value, root, index) for index, value in enumerate(values))
    ids = tuple(entry.id for entry in entries)
    if len(ids) != len(set(ids)):
        raise LedgerError("duplicate hypothesis id")
    if ids != EXPECTED_IDS:
        raise LedgerError(f"canonical hypothesis inventory drift: {ids!r}")
    verify_source_annotations(entries, root)
    canonical = json.dumps(
        raw, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    if hashlib.sha256(canonical).hexdigest().upper() != CANONICAL_CONTENT_SHA256:
        raise LedgerError("canonical hypothesis content drift")
    return Ledger(1, entries)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER)
    args = parser.parse_args(argv)
    try:
        ledger = load_ledger(args.ledger)
    except LedgerError as exc:
        parser.error(str(exc))
    print(f"HYPOTHESIS_LEDGER PASS entries={len(ledger.entries)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
