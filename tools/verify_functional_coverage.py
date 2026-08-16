"""Strict verifier for the Functional Coverage Matrix.

A narrow fixture, golden, or single controlled run proves one fact and never
closes a domain function.  This verifier makes that policy mechanical: a domain
may only declare itself complete when every required capability is exactly
``complete``, and the resulting banner must be published verbatim in STATUS.md.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path, PurePosixPath
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MATRIX = ROOT / "docs" / "FUNCTIONAL_COVERAGE.json"
STATUS_PATH = "STATUS.md"
STATUSES = (
    "not_started", "in_progress", "blocked", "runtime_pass", "complete",
)
COMPLETE = "complete"
EVIDENCE_REQUIRED = {"runtime_pass", "complete"}
EVIDENCE_FORBIDDEN = {"not_started"}
DOMAIN_FIELDS = {
    "id", "title", "domain_complete", "status_banner",
    "next_missing_behavior", "capabilities",
}
CAPABILITY_FIELDS = {
    "id", "title", "required", "status", "evidence_refs", "test_refs", "notes",
}
POLICY_FIELDS = {
    "statuses", "completion_rule", "banner_rule", "policy_text",
}
INCOMPLETE_SUFFIX = ": INCOMPLETE"
COMPLETE_SUFFIX = ": COMPLETE"


class CoverageError(ValueError):
    """The functional coverage matrix is malformed or has drifted."""


def _exact_fields(value: dict[str, Any], expected: set[str], label: str) -> None:
    if set(value) != expected:
        missing = sorted(expected - set(value))
        extra = sorted(set(value) - expected)
        raise CoverageError(f"{label} fields mismatch; missing={missing}, extra={extra}")


def _text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CoverageError(f"{label} must be a non-empty string")
    return value


def _identifier(value: Any, label: str) -> str:
    text = _text(value, label)
    if not text.replace("_", "").isalnum() or text != text.lower():
        raise CoverageError(f"{label} must be a lowercase snake_case identifier: {text!r}")
    return text


def _bool(value: Any, label: str) -> bool:
    if type(value) is not bool:
        raise CoverageError(f"{label} must be a bool")
    return value


def _repo_path(root: Path, raw: Any, label: str) -> str:
    text = _text(raw, label)
    posix = PurePosixPath(text)
    if posix.is_absolute() or ".." in posix.parts or "\\" in text:
        raise CoverageError(f"{label} must be a safe repo-relative POSIX path")
    path = (root / Path(*posix.parts)).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError as exc:
        raise CoverageError(f"{label} escapes the repository") from exc
    if not path.is_file():
        raise CoverageError(f"{label} does not exist: {text}")
    return text


def _path_list(value: Any, root: Path, label: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise CoverageError(f"{label} must be a list")
    result = tuple(
        _repo_path(root, item, f"{label}[{index}]") for index, item in enumerate(value)
    )
    if len(result) != len(set(result)):
        raise CoverageError(f"{label} contains duplicates")
    return result


@dataclass(frozen=True)
class Capability:
    id: str
    required: bool
    status: str
    evidence_refs: tuple[str, ...]
    test_refs: tuple[str, ...]

    @classmethod
    def parse(cls, value: Any, root: Path, label: str) -> "Capability":
        if not isinstance(value, dict):
            raise CoverageError(f"{label} must be an object")
        _exact_fields(value, CAPABILITY_FIELDS, label)
        ident = _identifier(value["id"], f"{label}.id")
        _text(value["title"], f"{label}.title")
        _text(value["notes"], f"{label}.notes")
        required = _bool(value["required"], f"{label}.required")
        status = _text(value["status"], f"{label}.status")
        if status not in STATUSES:
            raise CoverageError(f"{label}.status is not an allowed status: {status!r}")
        evidence = _path_list(value["evidence_refs"], root, f"{label}.evidence_refs")
        tests = _path_list(value["test_refs"], root, f"{label}.test_refs")
        if status in EVIDENCE_REQUIRED and not evidence:
            raise CoverageError(
                f"{label} status {status!r} requires at least one evidence ref"
            )
        if status in EVIDENCE_FORBIDDEN and (evidence or tests):
            raise CoverageError(
                f"{label} status {status!r} must not carry evidence or test refs"
            )
        if status == COMPLETE and not tests:
            raise CoverageError(f"{label} complete status requires at least one test ref")
        return cls(ident, required, status, evidence, tests)


@dataclass(frozen=True)
class Domain:
    id: str
    title: str
    domain_complete: bool
    status_banner: str
    next_missing_behavior: str
    capabilities: tuple[Capability, ...]

    @classmethod
    def parse(cls, value: Any, root: Path, index: int) -> "Domain":
        label = f"domains[{index}]"
        if not isinstance(value, dict):
            raise CoverageError(f"{label} must be an object")
        _exact_fields(value, DOMAIN_FIELDS, label)
        ident = _identifier(value["id"], f"{label}.id")
        title = _text(value["title"], f"{label}.title")
        complete = _bool(value["domain_complete"], f"{label}.domain_complete")
        banner = _text(value["status_banner"], f"{label}.status_banner")
        next_missing = _text(value["next_missing_behavior"], f"{label}.next_missing_behavior")

        raw_caps = value["capabilities"]
        if not isinstance(raw_caps, list) or not raw_caps:
            raise CoverageError(f"{label}.capabilities must be a non-empty list")
        caps = tuple(
            Capability.parse(item, root, f"{label}.capabilities[{i}]")
            for i, item in enumerate(raw_caps)
        )
        ids = tuple(cap.id for cap in caps)
        if len(ids) != len(set(ids)):
            raise CoverageError(f"{label} has duplicate capability ids")
        if not any(cap.required for cap in caps):
            raise CoverageError(f"{label} must declare at least one required capability")

        open_required = tuple(
            cap.id for cap in caps if cap.required and cap.status != COMPLETE
        )

        # The core gate: a narrow checkpoint never closes a domain.
        if complete and open_required:
            raise CoverageError(
                f"{ident} declares domain_complete=true but required capabilities are "
                f"not complete: {list(open_required)!r}"
            )

        expected_banner = f"{title}{COMPLETE_SUFFIX if complete else INCOMPLETE_SUFFIX}"
        if banner != expected_banner:
            raise CoverageError(
                f"{ident} status_banner must be {expected_banner!r}, got {banner!r}"
            )

        if complete:
            if next_missing != "none":
                raise CoverageError(
                    f"{ident} is complete so next_missing_behavior must be 'none'"
                )
        else:
            if next_missing not in ids:
                raise CoverageError(
                    f"{ident} next_missing_behavior must name one of its capability "
                    f"ids, got {next_missing!r}"
                )
            if next_missing not in open_required:
                raise CoverageError(
                    f"{ident} next_missing_behavior {next_missing!r} is not an open "
                    f"required capability"
                )
        return cls(ident, title, complete, banner, next_missing, caps)


@dataclass(frozen=True)
class Coverage:
    schema: int
    domains: tuple[Domain, ...]


def _verify_status_banners(domains: tuple[Domain, ...], root: Path) -> None:
    status_file = root / STATUS_PATH
    if not status_file.is_file():
        raise CoverageError(f"{STATUS_PATH} does not exist")
    contents = status_file.read_text(encoding="utf-8")
    for domain in domains:
        if contents.count(domain.status_banner) != 1:
            raise CoverageError(
                f"{STATUS_PATH} must publish {domain.status_banner!r} exactly once"
            )
        stale = f"{domain.title}{COMPLETE_SUFFIX if not domain.domain_complete else INCOMPLETE_SUFFIX}"
        if stale in contents:
            raise CoverageError(
                f"{STATUS_PATH} still carries the contradicting banner {stale!r}"
            )


def load_coverage(path: Path = DEFAULT_MATRIX, *, root: Path = ROOT) -> Coverage:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CoverageError(f"cannot read coverage matrix: {exc}") from exc
    if not isinstance(raw, dict):
        raise CoverageError("coverage root must be an object")
    _exact_fields(raw, {"schema", "policy", "domains"}, "coverage")
    if type(raw["schema"]) is not int or raw["schema"] != 1:
        raise CoverageError("coverage schema must be integer 1")

    policy = raw["policy"]
    if not isinstance(policy, dict):
        raise CoverageError("policy must be an object")
    _exact_fields(policy, POLICY_FIELDS, "policy")
    declared = policy["statuses"]
    if not isinstance(declared, list) or tuple(declared) != STATUSES:
        raise CoverageError(f"policy.statuses drift; expected {list(STATUSES)!r}")
    for name in ("completion_rule", "banner_rule", "policy_text"):
        _text(policy[name], f"policy.{name}")

    values = raw["domains"]
    if not isinstance(values, list) or not values:
        raise CoverageError("domains must be a non-empty list")
    domains = tuple(Domain.parse(value, root, index) for index, value in enumerate(values))
    ids = tuple(domain.id for domain in domains)
    if len(ids) != len(set(ids)):
        raise CoverageError("duplicate domain id")
    _verify_status_banners(domains, root)
    return Coverage(1, domains)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--matrix", type=Path, default=DEFAULT_MATRIX)
    args = parser.parse_args(argv)
    try:
        coverage = load_coverage(args.matrix)
    except CoverageError as exc:
        parser.error(str(exc))
    open_domains = [d for d in coverage.domains if not d.domain_complete]
    print(f"FUNCTIONAL_COVERAGE PASS domains={len(coverage.domains)}")
    for domain in coverage.domains:
        total = len(domain.capabilities)
        done = sum(1 for cap in domain.capabilities if cap.status == COMPLETE)
        print(
            f"  {domain.status_banner} ({done}/{total} complete)"
            f" next={domain.next_missing_behavior}"
        )
    if open_domains:
        print(f"OPEN DOMAINS: {len(open_domains)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
