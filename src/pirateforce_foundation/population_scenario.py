"""Strict opt-in configuration for authoritative V94 population capability."""

from dataclasses import dataclass
import json
from pathlib import Path

from .population import (
    AUTHORITATIVE_COUNT,
    PORT_ROYAL_SOURCE_COUNT,
    PORT_ROYAL_SOURCE_SHA256,
    REFRESH_DISTANCE,
    SCENE_ID,
)


INITIAL_REAPPLY_MS = 3000


@dataclass(frozen=True)
class PopulationScenario:
    scenario_id: str
    scene_id: int
    authoritative_count: int
    refresh_distance: float
    initial_reapply_ms: int


_PROFILE = PopulationScenario(
    "port_royal_authoritative_population_v94",
    SCENE_ID,
    AUTHORITATIVE_COUNT,
    REFRESH_DISTANCE,
    INITIAL_REAPPLY_MS,
)


_EXPECTED = {
    "schema": 1,
    "id": "port_royal_authoritative_population_v94",
    "test_only": True,
    "entry": {"flow": "full_writable_character", "scene_id": SCENE_ID},
    "population": {
        "trigger": "first_exact_target_pos_after_runtime_ack",
        "source": "v141_exact_port_royal_unambiguous_placements",
        "source_count": PORT_ROYAL_SOURCE_COUNT,
        "source_sha256": PORT_ROYAL_SOURCE_SHA256,
        "authoritative_count": AUTHORITATIVE_COUNT,
        "refresh_distance": 1000,
        "initial_reapply_ms": INITIAL_REAPPLY_MS,
    },
    "transition": {
        "retained": "npc_attr_only",
        "entrants": "npc_attr_plus_full_movement_attr",
        "omitted": "absent",
    },
    "capabilities": ["authoritative_npc_style_membership"],
    "nonclaims": [
        "monster", "remote_player", "faction", "combat", "item",
        "vehicle", "portal", "authentic_runtime_policy",
    ],
}


def _exact_equal(actual, expected) -> bool:
    if type(actual) is not type(expected):
        return False
    if type(expected) is dict:
        return (
            set(actual) == set(expected)
            and all(_exact_equal(actual[key], value) for key, value in expected.items())
        )
    if type(expected) is list:
        return len(actual) == len(expected) and all(
            _exact_equal(left, right) for left, right in zip(actual, expected)
        )
    return actual == expected


def load_population_scenario(path: str | Path) -> PopulationScenario:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("invalid population scenario") from exc
    if type(data) is not dict or not _exact_equal(data, _EXPECTED):
        raise ValueError("population scenario exceeds the exact V94 allowlist")
    population = data["population"]
    return require_population_scenario(PopulationScenario(
        data["id"], data["entry"]["scene_id"],
        population["authoritative_count"],
        float(population["refresh_distance"]),
        population["initial_reapply_ms"],
    ))


def require_population_scenario(value) -> PopulationScenario:
    if (
        type(value) is not PopulationScenario
        or type(value.scenario_id) is not str
        or type(value.scene_id) is not int
        or type(value.authoritative_count) is not int
        or type(value.refresh_distance) is not float
        or type(value.initial_reapply_ms) is not int
        or value != _PROFILE
    ):
        raise ValueError("population scenario object exceeds the exact V94 allowlist")
    return value
