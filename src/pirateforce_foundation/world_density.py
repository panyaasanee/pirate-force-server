"""Where the town actually is - LANE-A build order BUILD-001, M1.

WHY THIS MODULE EXISTS.  ``world_population`` answers HOW MANY actors leave the
server.  It does not answer the only question the player's eyes can answer:
WHERE does a character have to stand before any of them is near.  Measured from
the scene's own placement file, using the shipped census only:

    census members within 2000 units of the login anchor ...............  2
    census members within 2000 units of the attended measured spawn ....  3
    census members within  500 units of the attended measured spawn ....  0
    census members within 2000 units of the best stand point ........... 12

TWO DIFFERENT "WHERE THE PLAYER STARTS", AND THE DIFFERENCE MATTERS.  v141's
``V134_PLAYER_XYZ`` is a constant.  The position a character really logs in at
comes from its DB row, and the attended GT-045 run measured that 715.6 units
away from the constant - close range there is emptier still, with nothing at
all inside 500 units.  Quote ``attended_measured_spawn()`` for anything about
what a person will see.

THIS EXTENDS A FACT ALREADY PINNED AT HEAD, IT DOES NOT DISCOVER IT.
``tests/test_world_population.py`` already asserts that no more than two census
members sit within 2000u of the login anchor, and already uses the dense
neighbourhood's XY as a second anchor.  What is new here is the reason (the
scene file, not the actor count), the whole-scene search, and the 34 rows v141
drops.

WHAT RAISING 3 TO 115 ACTUALLY BUYS AT THE LOGIN VIEW - AND IT IS NOT ZERO.
Exactly ONE census member joins the login view: placement 1, "Sebastian", at
1,226 units.  The nearest actor of all - placement 0, "Navy Transfer", 100
units away - is already one of the three the server sends today.  An earlier
draft of this module said the census adds nobody; that was refuted from this
module's own data and the sentence is corrected rather than removed.  The
direction still holds: one extra actor at 1,226 units is not a populated town.

So M1 - "the town is alive" - does NOT arrive by raising the actor count.  The
scene's own placement file is what empties the login view.  Read that as the
reason an M1 acceptance test taken ONLY at the login anchor grades the wrong
thing, not as an argument against sending 115.

WHAT WAS MEASURED, AND FROM WHAT.  Two committed tables, both in ``pf_bridge``,
neither of them the client binary: the scene's decoded placement table (149
records) and ``CONSTDATA_TH__MOBS.tsv`` (3,210 rows).

THREE CROSS-SOURCE CONTROLS, TWO OF WHICH AGREE COMPLETELY.  All 115 XYZ agree
exactly between v141's frozen table and the separate decode.  All 115 visual
presets equal the ``s_OUTFIT`` of the MOBS row the template id maps to - that
is the strong one, because the preset travels THROUGH the MOBS table and is
only equal if the ``n_ID`` <-> ``template_ids`` join is real.  And 0 of 115
source names agree, because one decode stores display names and the other
stores set labels: the disagreement is what proves neither is a copy.

WHAT "UNAMBIGUOUS" TURNED OUT TO MEAN, AND THAT IT IS A RULE.  v141 ships 115
of the scene's 149 placement records.  Measured row by row: 31 dropped rows
carry two ``s_OUTFIT`` variants split by ``;``, and 3 have no MOBS row at all.
The criterion also separates the other way - 0 of the 115 SHIPPED rows match
either condition - so it is a rule rather than a description of the survivors.

Note what the 31 are: mountain deer, rock turtles, jungle tigers, two named
pirate crews.  Choosing a variant for them is a hostile-actor question, and
hostile actors are LANE-B's build order.  This module MEASURES the gap and does
not close it.

THE 710 TRIPLES, AND WHY THIS MODULE NO LONGER CALLS THEM SPAWN POINTS.  Eleven
placement records carry extra XYZ triples - 710 as written, 707 distinct.  An
earlier draft counted them as spawn points "generously, therefore safely".
That was wrong twice over: 644 of the 710 belong to rows the server does not
send at all, and the generosity lands on the COMPARISON side of the headline,
which widens the contrast instead of guarding it.  The evidence gathered this
round points at patrol paths, not spawns: every one of the eleven chains starts
between 6 and 414 units from its own placement's home, and seven of eleven
return to within 500 units of where they began.  ``CONSTDATA_TH__AI_WANDER.tsv``
sits in the same directory and would settle it; it has not been read, so this
module says "not decoded yet" and never "nothing establishes it".

WHAT THIS MODULE DOES NOT DO.  It does not change the shipped census count,
which stays 115 under the owner's ruling (CHARTER-02, 2026-08-25 23:45).  It
does not move any character.  It does not claim a delivered actor becomes a
model on screen - that is ``GT-072``, open and PARTIAL.  And it does not claim
any stand point is reachable or standable.

WHAT THIS MODULE CANNOT CHECK, SAID OUT LOUD RATHER THAN SKIPPED.  The two
source tables live in the other repository.  ``verify_pin_against_source()``
therefore returns the checked list AND the unverifiable list, and a test pins
how many entries are unverifiable, so a silent skip cannot quietly grow.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import math
from pathlib import Path
from typing import Any

from .population import (
    PORT_ROYAL_SOURCE_COUNT,
    SceneActorPlacement,
    load_port_royal_placements,
)


# Convention marker only.  Nothing in this tree branches on it.
production_allowed = True
test_only = False

PIN_PATH = (
    Path(__file__).resolve().parents[2] / "scenarios" / "world_scene_density_001.json"
)
PIN_ID = "bg0001_scene_density_001"

SCENE_ID = 1
SCENE_NAME = "bg0001"

# The band the M1 question is actually asked in.  A player standing still sees
# what is around them, not what is 30,000 units away on the other side of the
# map, so the headline numbers are 2000-unit counts.
M1_VIEW_RADIUS = 2000.0

# [PROPOSED] the band the console verdict is decided on.  It is deliberately
# the NEAREST band, not the widest: an earlier draft decided on the 2000u count
# and could therefore call a position with an NPC 104 units away "empty", and a
# position whose only company was 1,900 units off "populated".  Nothing on the
# client side justifies any threshold - this one is a lane choice, and the raw
# per-band counts are printed next to it so a reader never has to trust it.
VERDICT_RADIUS = 500.0
VERDICT_MINIMUM = 2

MEASURED_BANDS = (500.0, 1000.0, 2000.0, 5000.0, 10000.0)

SCENE_PLACEMENT_RECORDS = 149
CENSUS_GAP_RECORDS = SCENE_PLACEMENT_RECORDS - PORT_ROYAL_SOURCE_COUNT

# Triples AS WRITTEN in the file.  Not a count of positions (three coordinates
# are written twice) and not a count of spawn points (see the module docstring).
SCENE_XYZ_TRIPLES_WRITTEN = 859
SCENE_DISTINCT_COORDINATES = 856

_FLOAT32_MAX = 3.4028234663852886e38


@dataclass(frozen=True)
class StandPoint:
    """One position, and how much of the scene is near it."""

    label: str
    x: float
    y: float
    z: float
    shipped_census_within: tuple[tuple[float, int], ...]
    all_file_points_within: tuple[tuple[float, int], ...]

    @property
    def xyz(self) -> tuple[float, float, float]:
        return (self.x, self.y, self.z)

    def census_neighbours(self, radius: float = M1_VIEW_RADIUS) -> int:
        """The number to quote.  It survives 2D, and it survives the tiebreak."""
        return self._band(self.shipped_census_within, radius)

    def file_point_neighbours(self, radius: float = M1_VIEW_RADIUS) -> int:
        """The number NOT to quote alone: it counts data of undecided meaning."""
        return self._band(self.all_file_points_within, radius)

    @staticmethod
    def _band(rows: tuple[tuple[float, int], ...], radius: float) -> int:
        for band, count in rows:
            if band == radius:
                return count
        raise ValueError(f"radius {radius} was not one of the measured bands")


def _require_xyz(value: Any) -> tuple[float, float, float]:
    if type(value) is not tuple or len(value) != 3:
        raise ValueError("a position must be an exact three-value tuple")
    checked = []
    for axis, item in zip("xyz", value):
        if type(item) not in (int, float):
            raise ValueError(f"{axis} must be a finite float32 value")
        result = float(item)
        if not math.isfinite(result) or abs(result) > _FLOAT32_MAX:
            raise ValueError(f"{axis} must be a finite float32 value")
        checked.append(result)
    return (checked[0], checked[1], checked[2])


_REQUIRED_KEYS = (
    "provenance", "cross_source_controls", "scene_inventory", "the_gap_of_34",
    "are_the_extra_triples_spawn_points_or_paths", "stand_points", "robustness",
    "nonclaims",
)


def _load_pin() -> dict:
    if not PIN_PATH.is_file():
        raise FileNotFoundError(f"density pin missing: {PIN_PATH}")
    with PIN_PATH.open(encoding="ascii") as stream:
        document = json.load(stream)
    if document.get("schema") != 1 or document.get("id") != PIN_ID:
        raise ValueError("density pin is not the document this module reads")
    # A document with the right id but the wrong shape used to reach the
    # callers and fail as a KeyError three frames away.  Refuse it here.
    missing = [key for key in _REQUIRED_KEYS if key not in document]
    if missing:
        raise ValueError(f"density pin is missing sections: {missing}")
    for key in ("login_anchor", "attended_measured_spawn", "densest"):
        if key not in document["stand_points"]:
            raise ValueError(f"density pin has no stand point {key!r}")
    return document


def _stand_point(key: str) -> StandPoint:
    entry = _load_pin()["stand_points"][key]
    measured = entry["measured"]
    try:
        census = tuple(
            (band, measured[f"within_{int(band)}u_shipped_census"])
            for band in MEASURED_BANDS
        )
        scene = tuple(
            (band, measured[f"within_{int(band)}u_all_file_points"])
            for band in MEASURED_BANDS
        )
    except KeyError as error:
        raise ValueError(f"density pin stand point {key!r} is missing {error}")
    return StandPoint(
        label=entry["label"],
        x=float(entry["x"]),
        y=float(entry["y"]),
        z=float(entry["z"]),
        shipped_census_within=census,
        all_file_points_within=scene,
    )


def login_anchor() -> StandPoint:
    """Where a character stands after login today, and how thin that is."""
    return _stand_point("login_anchor")


def attended_measured_spawn() -> StandPoint:
    """Where an attended run really found the character - NOT a v141 constant.

    ``login_anchor()`` is ``V134_PLAYER_XYZ``, a constant.  The position a
    character actually logs in at comes from its DB row, and the attended
    GT-045 run measured that at 715.6 units away from the constant.  At the
    measured spawn the close-range view is emptier still: ZERO census members
    within 500 units, against one at the constant.

    Anything said about what a person will see should quote this point.
    Anything said about the frozen table's own anchor should quote the other.
    """
    return _stand_point("attended_measured_spawn")


def densest_stand_point() -> StandPoint:
    """The best place in bg0001 to stand if the point is to SEE the census.

    Two warnings travel with this coordinate, both of them measured:

    * It is NOT a placement.  It is one of the extra triples carried by
      placement 43, i.e. a position out of the very data this module refuses to
      call spawn points.  Use ``densest_real_placement()`` for anything a human
      is asked to stand on.
    * It is one of several candidate positions tied at the top census count,
      and the tie was broken with all-file points - data whose meaning is
      undecided.  A different tiebreak moves this coordinate.

    The census count itself is not affected by either warning: the best real
    placement scores the same 12.
    """
    return _stand_point("densest")


def densest_real_placement() -> tuple[tuple[float, float, float], int]:
    """The best stand point that is an actual placement, and its census count."""
    entry = _load_pin()["stand_points"]["densest"]["best_point_that_IS_a_real_placement"]
    return (
        (float(entry["x"]), float(entry["y"]), float(entry["z"])),
        int(entry["census_within_2000u"]),
    )


def scene_inventory() -> dict[str, int]:
    """The counts, straight off the pin, with no arithmetic in between."""
    inventory = _load_pin()["scene_inventory"]
    return {
        "placement_records": int(inventory["placement_records"]),
        "shipped_census_records": int(inventory["shipped_census_records"]),
        "gap_records": int(inventory["records_not_in_the_shipped_census"]),
        "extra_triples_written": int(
            inventory["extra_xyz_triples_written_in_the_file"]
        ),
        "triples_written_total": int(
            inventory["xyz_triples_written_in_the_file_total"]
        ),
        "distinct_coordinates": int(inventory["distinct_coordinates_total"]),
    }


def census_gap() -> tuple[dict, ...]:
    """The 34 placement records the shipped census does not carry."""
    return tuple(_load_pin()["the_gap_of_34"]["records"])


def census_gap_reasons() -> dict[str, int]:
    return dict(_load_pin()["the_gap_of_34"]["by_reason"])


def gap_rule_separates_both_ways() -> dict[str, int]:
    """How many SHIPPED rows the drop criterion also catches.  Should be zero."""
    block = _load_pin()["the_gap_of_34"]["the_rule_separates_in_both_directions"]
    return {
        "dropped_rows_matching_the_rule": int(block["dropped_rows_matching_the_rule"]),
        "shipped_rows_with_a_semicolon": int(
            block["shipped_rows_with_a_semicolon_in_s_OUTFIT"]
        ),
        "shipped_rows_with_no_MOBS_row": int(block["shipped_rows_with_no_MOBS_row"]),
    }


def census_added_at_the_login_view() -> tuple[dict, ...]:
    """Which census members raising 3 to 115 actually adds near the login anchor."""
    block = _load_pin()["stand_points"]["login_anchor"]
    return tuple(block["what_raising_3_to_115_adds_here"]["added_by_the_census"])


def extra_triple_chains() -> tuple[dict, ...]:
    """The eleven chains, with the geometry that makes them look like paths."""
    return tuple(_load_pin()["are_the_extra_triples_spawn_points_or_paths"]["chains"])


def radius_sensitivity() -> tuple[dict, ...]:
    """The headline compare restated at six radii instead of the chosen one."""
    return tuple(_load_pin()["robustness"]["radius_sensitivity"])


def neighbours_within(
    legacy: Any,
    player_xyz: tuple[float, float, float],
    radius: float = M1_VIEW_RADIUS,
) -> tuple[SceneActorPlacement, ...]:
    """Which shipped-census members are within ``radius`` of a position, LIVE.

    Computed from the frozen table at call time, never from the pin.  That is
    the point: it is the half of the pin this repository can refute on its own.
    """
    if type(radius) not in (int, float) or not math.isfinite(float(radius)):
        raise ValueError("radius must be a finite number")
    if float(radius) <= 0.0:
        raise ValueError("radius must be positive")
    x, y, z = _require_xyz(player_xyz)
    limit = float(radius) ** 2
    near = []
    for placement in load_port_royal_placements(legacy):
        distance2 = (
            (placement.x - x) ** 2 + (placement.y - y) ** 2 + (placement.z - z) ** 2
        )
        if distance2 <= limit:
            near.append((distance2, placement.placement_index, placement))
    near.sort(key=lambda item: (item[0], item[1]))
    return tuple(item[2] for item in near)


# Every pin claim this repository cannot reach, named one by one.  A test pins
# the length of this tuple, so a future claim cannot join the list in silence.
UNVERIFIABLE_HERE = (
    "scene_inventory.placement_records - needs the pf_bridge placement table",
    "scene_inventory.extra_xyz_triples_written_in_the_file - same table",
    "scene_inventory.distinct_coordinates_total - same table",
    "the_gap_of_34.records - needs the placement table and the MOBS table",
    "the_gap_of_34.the_rule_separates_in_both_directions - same two tables",
    "cross_source_controls.* - the whole point of them is the other decode",
    "are_the_extra_triples_spawn_points_or_paths.chains - needs the placement table",
    "stand_points.*.measured.within_*u_all_file_points - needs the placement table",
    "provenance.*.sha256 - no code path in this repository reads either digest",
)


def verify_pin_against_source(legacy: Any) -> dict[str, tuple[str, ...]]:
    """Recompute what this repository can reach, and NAME what it cannot.

    Returns ``{"disagreements": (...), "unverifiable": (...)}``.  An earlier
    version returned only the disagreements, which meant a pin whose headline
    all-file counts had been replaced with garbage still came back clean.  A
    skip that is not counted reads as a pass, so the skips are returned too and
    a test pins how many there are.
    """
    problems = []
    placements = load_port_royal_placements(legacy)
    if len(placements) != PORT_ROYAL_SOURCE_COUNT:
        problems.append(
            f"frozen census is {len(placements)} rows, pin assumes "
            f"{PORT_ROYAL_SOURCE_COUNT}"
        )
    for key in ("login_anchor", "attended_measured_spawn", "densest"):
        point = _stand_point(key)
        for band, pinned in point.shipped_census_within:
            live = len(neighbours_within(legacy, point.xyz, band))
            if live != pinned:
                problems.append(
                    f"{key}: pin says {pinned} census members within {int(band)}u, "
                    f"the frozen table says {live}"
                )
    inventory = scene_inventory()
    if inventory["shipped_census_records"] != len(placements):
        problems.append("pin's shipped_census_records disagrees with the frozen table")
    if inventory["placement_records"] - inventory["shipped_census_records"] != (
        inventory["gap_records"]
    ):
        problems.append("pin's own gap arithmetic does not close")
    if inventory["triples_written_total"] != (
        inventory["placement_records"] + inventory["extra_triples_written"]
    ):
        problems.append("pin's own triple arithmetic does not close")

    # The one live check of the login-view claim: the members the pin says the
    # census adds must really be absent from today's three and present nearby.
    shipped_today = set(getattr(legacy, "V112_TEST_INDICES", ()))
    near = {p.placement_index for p in neighbours_within(
        legacy, login_anchor().xyz, M1_VIEW_RADIUS)}
    for row in census_added_at_the_login_view():
        index = int(row["placement_index"])
        if index in shipped_today:
            problems.append(f"pin credits the census with placement {index}, "
                            "which the server already sends today")
        if index not in near:
            problems.append(f"pin credits the census with placement {index}, "
                            "which is not inside the login view at all")

    real_xyz, real_count = densest_real_placement()
    live_real = len(neighbours_within(legacy, real_xyz, M1_VIEW_RADIUS))
    if live_real != real_count:
        problems.append(
            f"pin says the best real placement sees {real_count} census members, "
            f"the frozen table says {live_real}"
        )
    return {"disagreements": tuple(problems), "unverifiable": UNVERIFIABLE_HERE}


def m1_console_line(legacy: Any, player_xyz: tuple[float, float, float]) -> str:
    """One ASCII line saying how much of the census is near this position.

    Printed next to ``world_population.census_console_line`` it separates the
    two halves of M1 that keep getting confused: how many actors were SENT, and
    how many of them are anywhere near the person looking.  Every count on the
    line is computed live except ``best_2000u``, which is marked ``pin=`` so a
    reader is never guessing which layer a number came from.
    """
    x, y, z = _require_xyz(player_xyz)
    near = {
        int(band): len(neighbours_within(legacy, (x, y, z), band))
        for band in MEASURED_BANDS
    }
    decisive = len(neighbours_within(legacy, (x, y, z), VERDICT_RADIUS))
    return (
        "WORLD_DENSITY scene={0} at=({1:.1f},{2:.1f},{3:.1f}) "
        "census_within_500u={4} 1000u={5} 2000u={6} 5000u={7} 10000u={8} "
        "pin=best_2000u:{9} verdict={10}@{11}u[PROPOSED]".format(
            SCENE_NAME, x, y, z,
            near[500], near[1000], near[2000], near[5000], near[10000],
            densest_stand_point().census_neighbours(),
            "THIN_VIEW" if decisive < VERDICT_MINIMUM else "POPULATED_VIEW",
            int(VERDICT_RADIUS),
        )
    )
