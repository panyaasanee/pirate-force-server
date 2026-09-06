"""LANE-A: the gate that goes red the day the census outgrows the allowlist.

WHAT THIS FILE IS FOR, IN ONE SENTENCE.  ``multi_set_placement_refusals()``
in every scene identity module decides whether the two legs of a multi-set
placement are interchangeable, it decides that by comparing the columns
``SceneIdentity`` happens to carry, and until this file existed nothing
anywhere said that this was a DECISION rather than an accident of which
fields an old round typed.

THE MEASUREMENT THAT MADE IT URGENT (``LANE-A-ASK-COO 20260906_0522``).
Scenes 304 and 305 collapse ten multi-set placements between them, and both
pairs resolve to the same two ``CONSTDATA_TH__MOBS`` rows: 8167 and 8171.
pf-adversary read the raw table and those rows DIFFER - on ``s_PROPERTIES``
(8 values against 1) and on both speeds (600 against 200).  Shipping the
first leg is still honest today, because the census does not put either of
those on the wire, so no viewer can tell which leg arrived.  But the gate
was answering "interchangeable" for a structural reason rather than a
measured one: it cannot see a column the dataclass does not carry, so it
would go on saying yes on the day someone adds one.

SO THIS FILE GRADES THE ALLOWLIST, NOT THE SCENES.  ``COO-DECISION
20260906_0549`` item 3 asked for exactly two properties, and each test below
is one of them:

* every column the census SHIPS has a declared source column, so a field
  added to ``SceneIdentity`` cannot go silently uncompared;
* the set the census ships and the set the legs may differ on do not
  overlap - today, empty; the day they do overlap, RED, and red at the
  lane that widened the census rather than three rounds later at a player
  who saw the wrong ship.

WHAT THIS FILE DOES NOT CLAIM.  Not that 8167 and 8171 are the same
monster - they are not, and the allowlist is the written admission of that.
Not that any player has ever seen either.  Only that what this server puts
on the wire cannot tell them apart, and that the day it can, a test says so.
"""
from __future__ import annotations

import dataclasses

import pytest

from pirateforce_foundation import world_bg3001_identity
from pirateforce_foundation import world_bg3007_identity
from pirateforce_foundation import world_bg3008_identity
from pirateforce_foundation.lane_hooks import lane_a_scene_census


# The three scene identity modules that resolve a multi-set placement today.
# A fourth one joining this list is a one-line edit here; a fourth one NOT
# joining it is why the tests below read the module's own tuple rather than
# a copy of it.
IDENTITY_MODULES = (
    ("bg3001", world_bg3001_identity),
    ("bg3007", world_bg3007_identity),
    ("bg3008", world_bg3008_identity),
)


@pytest.mark.parametrize("name,module", IDENTITY_MODULES)
def test_every_shipped_column_has_a_declared_source_column(name, module):
    """No shipped field may be invisible to the leg comparison.

    THE FAILURE THIS CATCHES.  Someone adds ``speed_walk`` to
    ``SceneIdentity`` for a reason that has nothing to do with multi-set
    placements.  ``SHIPPED_COLUMNS_EXCEPT_MOBS_ID`` is derived, so the new
    field joins the comparison by existing - good - but nothing says WHICH
    raw column it came from, so the overlap test below could not honestly
    answer.  This test is the one that names the omission, and the fix is
    one row in ``SHIPPED_COLUMN_SOURCES``.
    """
    undeclared = lane_a_scene_census.undeclared_shipped_fields(module)
    assert undeclared == (), (
        f"{name}: shipped fields with no declared source column: "
        f"{undeclared}.  Add each one to "
        f"lane_a_scene_census.SHIPPED_COLUMN_SOURCES naming the table and "
        f"column the scene module's own join reads it from."
    )


@pytest.mark.parametrize("name,module", IDENTITY_MODULES)
def test_the_census_ships_no_column_the_legs_may_differ_on(name, module):
    """The gate itself.  Empty intersection, or the pair is not collapsible.

    THE FAILURE THIS CATCHES, CONCRETELY.  A lane adds ``s_PROPERTIES`` to
    the census so a client can read a monster's property list.  Scene 305
    keeps collapsing its four ``57|58`` placements to the first leg, and now
    the property list a viewer receives is 8167's eight values for an actor
    that is 8171 half the time.  Nothing crashes; a player sees the wrong
    ship's properties and nobody knows why.  This assertion fires in CI
    instead, in the same commit that widened the census.
    """
    overlap = lane_a_scene_census.shipped_columns_legs_may_differ_on(module)
    assert overlap == (), (
        f"{name}: the census now ships {overlap}, which "
        f"lane_a_scene_census.MOBS_COLUMNS_LEGS_MAY_DIFFER_ON says the two "
        f"legs of a multi-set placement are allowed to differ on.  Either "
        f"stop collapsing multi-set placements to their first leg in this "
        f"scene, or re-measure the leg pair and narrow the allowlist - do "
        f"not widen the allowlist to make this green."
    )


def test_the_three_scene_modules_ship_the_same_seven_columns():
    """One map, because there is one join.  A fork must announce itself.

    ``SHIPPED_COLUMN_SOURCES`` is keyed by field name and shared by all
    three modules, which is only honest while all three really do run the
    same join.  They do today - each module's docstring states it as "the
    same join against the same five tables" - and this pins it.  A module
    that forks its shape fails HERE with a readable message, rather than
    quietly borrowing another scene's source columns above.
    """
    shapes = {
        name: tuple(f.name for f in dataclasses.fields(module.SceneIdentity))
        for name, module in IDENTITY_MODULES
    }
    assert len(set(shapes.values())) == 1, (
        f"scene identity shapes have diverged: {shapes}.  "
        f"SHIPPED_COLUMN_SOURCES is one map for all of them; a forked "
        f"module needs its own source map before the gate above can speak "
        f"for it."
    )


def test_the_allowlist_names_the_columns_the_pair_was_measured_to_differ_on():
    """The allowlist is a measurement, so it is pinned as one.

    Not a style assertion: this tuple is the reason the gate is allowed to
    say "interchangeable" at all, and a round that quietly extends it to
    silence the gate above is the exact failure ``COO-DECISION
    20260906_0549`` was written to prevent.  Changing this list means
    re-reading ``CONSTDATA_TH__MOBS.tsv`` for the leg pair and citing the
    reading - which means editing this test too, deliberately.
    """
    assert lane_a_scene_census.MOBS_COLUMNS_LEGS_MAY_DIFFER_ON == (
        "MOBS.n_ID",
        "MOBS.s_NAME",
        "MOBS.s_PROPERTIES",
        "MOBS.n_SPEED_WALK",
        "MOBS.n_SPEED_RUN",
    )


def test_the_display_name_column_is_not_the_mobs_name_column():
    """The one confusion that would break this gate quietly.

    ``MOBS.s_NAME`` is in the allowlist and the census ships a name, so a
    reader in a hurry concludes the intersection is non-empty and either
    deletes the row or stops trusting the gate.  It is not the same column:
    the shipped label is ``MOBS_TIP.s_NAME``, from a different table, which
    every scene module's join states and which is why ASCII-ness of
    ``MOBS_TIP.s_NAME`` is a drop condition there while ``MOBS.s_NAME``
    (Chinese-traditional, unencodable in the bridge's cp874) is read by
    nothing.  Pinned so the distinction survives a refactor.
    """
    assert lane_a_scene_census.SHIPPED_COLUMN_SOURCES["name"] == (
        "MOBS_TIP.s_NAME"
    )
    assert "MOBS_TIP.s_NAME" not in (
        lane_a_scene_census.MOBS_COLUMNS_LEGS_MAY_DIFFER_ON
    )
    assert "MOBS.s_NAME" in (
        lane_a_scene_census.MOBS_COLUMNS_LEGS_MAY_DIFFER_ON
    )


def test_an_undeclared_field_makes_the_gate_abstain_rather_than_pass():
    """A missing source column must never read as "no overlap".

    The overlap function returns an empty tuple in two very different
    situations - "nothing overlaps" and "I could not tell" - so this pins
    that the second one is never REACHED without the companion test above
    being red at the same time.  Simulated with a stand-in module rather
    than by mutating a real one.
    """

    class _Forked:
        SHIPPED_COLUMNS_EXCEPT_MOBS_ID = ("outfit", "speed_walk")

    forked = _Forked()
    assert lane_a_scene_census.undeclared_shipped_fields(forked) == (
        "speed_walk",
    )
    assert lane_a_scene_census.shipped_columns_legs_may_differ_on(forked) == ()


def test_a_census_that_shipped_a_speed_would_be_caught():
    """The gate is red when it should be - proven, not asserted.

    Without this, all the green above is equally consistent with a function
    that returns ``()`` unconditionally.  A stand-in module that ships
    ``MOBS.n_SPEED_WALK`` under a declared name is the mutant, and the gate
    must name the column back.
    """

    class _WiderCensus:
        SHIPPED_COLUMNS_EXCEPT_MOBS_ID = ("outfit", "name", "speed_walk")

    widened = dict(lane_a_scene_census.SHIPPED_COLUMN_SOURCES)
    widened["speed_walk"] = "MOBS.n_SPEED_WALK"
    original = lane_a_scene_census.SHIPPED_COLUMN_SOURCES
    lane_a_scene_census.SHIPPED_COLUMN_SOURCES = widened
    try:
        overlap = lane_a_scene_census.shipped_columns_legs_may_differ_on(
            _WiderCensus()
        )
    finally:
        lane_a_scene_census.SHIPPED_COLUMN_SOURCES = original
    assert overlap == ("MOBS.n_SPEED_WALK",)
    # and the module is left exactly as it was found
    assert lane_a_scene_census.SHIPPED_COLUMN_SOURCES is original
