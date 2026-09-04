"""LANE-A / M2: the first provisioning trial's two records, composed and
ready for a send path -- and called by no send path anywhere in this
repository.

COO-DECISION 20260904_1345 item 3(b) ordered this built now that GT-228
(R308, PASS) measured real island XYZ: "send `NavigationEx_
AddSurveyDataVtial` records for both islands (2/3, XYZ per item 2, byte
`+0x10`=1) when the player enters the sea scene; the first trial's u16
opaque value = the destination scene number (2/3), per item 1 -- a trial
value, not a conclusion; attended-only".

WHY THIS IS A SEPARATE MODULE, NOT A FUNCTION ON `world_m2_survey_plan`
------------------------------------------------------------------------
`world_m2_survey_plan.py` has its own guard test
(`NotASendPathTests.test_the_plan_does_not_reach_the_record_encoder`)
asserting its source never names the encoder module at all -- a boundary
this file exists to respect rather than erode: the plan says WHICH
destinations and WHAT coordinates; this file is the one place that also
knows about `navigationex_survey_record`'s wire shape, and it is exactly as
inert as the two modules it joins.

WHAT THE TRIAL ``survey_id`` IS, AND IS NOT
--------------------------------------------
Each record's `SurveyRecordFields.survey_id` is
`PlannedRecord.scene_name_tip_id` -- 2 for Prison Exile Island, 3 for Spice
Paradise Island, the SAME two numbers GT-228/R308 observed on the wire as
`TriggerVital 0x1FB2`'s trigger id at contact (see `lane_hooks/
lane_a_island_trigger_log.py`'s "GT-228 OBSERVED OVERRIDE").  Deliberately
NOT `PlannedRecord.handle` (`world_m2_survey_plan.SURVEY_HANDLE_BASE +
trigger_id`), which is a different, already-in-use allocation scheme for
confirm-frame bookkeeping.  Choosing the observed scene number is COO's own
call (item 1: "id = the destination scene number" is the primary
hypothesis) and is stated here as a TRIAL VALUE, not a claim about what the
client reads the field as -- RE-227 nonclaim 3 and `navigationex_survey_
record`'s own docstring both hold: nothing proves this u16 means anything
to the client beyond an opaque value it copies back unchanged.

CALLED FROM NO SEND PATH ANYWHERE IN THIS REPOSITORY.  Two things are still
missing before that could change, and neither is this module's to supply:

    1. The wire `msg_id` for `NavigationEx_AddSurveyDataVtial`.  RE-227
       never proved a number for it (see `navigationex_survey_record`'s own
       docstring) -- `encode_survey_records()` below takes it as a REQUIRED
       caller argument, on purpose, with no default, the same discipline
       `encode_add_survey_data_outer` already uses.
    2. The runtime.py call site itself -- "on player entering the sea scene,
       behind an attended-only flag" is chief's territory
       (`runtime.py`/`app.py`), by CORE-REQUEST, same as every other lane
       send path in this project (confirmed again as of this round:
       pf_bridge/notes_to_chief/20260904_1036_LANE-A-STATUS-* and
       .../FROM_CHIEF_R334_TO_ALL_20260904_0820.md).

So this module's whole job is: the day both of those land, composing and
encoding the two trial records is not a new guess -- it is these two calls.
"""
from __future__ import annotations

from typing import NamedTuple

from . import world_m2_survey_plan as plan
from .navigationex_survey_record import (
    SurveyRecordFields,
    encode_add_survey_data_outer,
)


class TrialSurveyRecord(NamedTuple):
    """One provisioning-trial record: which destination, and the wire
    fields `navigationex_survey_record` needs to encode it.

    ``trigger_id`` is the DOCK-TABLE id (153 Prison Exile / 154 Spice
    Paradise) -- this lane's usual namespace, matching
    `world_m2_survey_plan.PlannedRecord.trigger_id`.  It is NOT the id a
    later `TriggerVital` capture will carry on the wire: that is
    `fields.survey_id` (2/3, GT-228's observed contact ids -- see
    `lane_hooks/lane_a_island_trigger_log.py`'s "GT-228 OBSERVED OVERRIDE").
    A future runtime.py call site correlating a sent record against an
    inbound capture must match on `fields.survey_id`, not on this field --
    matching 153/154 against a wire frame that only ever carries 2/3 will
    silently never match anything.
    """

    trigger_id: int
    fields: SurveyRecordFields


def trial_survey_records() -> tuple[TrialSurveyRecord, ...]:
    """The first provisioning trial's records, one per destination
    `world_m2_survey_plan.planned_records()` can provision right now (today,
    both M2 islands).  Empty if `MEASURED_XYZ` is ever emptied again -- this
    function has no opinion of its own, it only reads the plan's.
    """
    return tuple(
        TrialSurveyRecord(
            trigger_id=record.trigger_id,
            fields=SurveyRecordFields(
                survey_id=record.scene_name_tip_id,
                x=record.x,
                y=record.y,
                z=record.z,
            ),
        )
        for record in plan.planned_records()
    )


def encode_trial_records(
    legacy, msg_id: int, vital_version: int,
) -> tuple[tuple[int, bytes, bytes], ...]:
    """``(trigger_id, pc, frame)`` for every record in
    ``trial_survey_records()``, encoded through ``navigationex_survey_
    record.encode_add_survey_data_outer``.

    ``legacy``, ``msg_id`` and ``vital_version`` are exactly that function's
    own required arguments, passed through unchanged -- this function adds
    no default for ``msg_id`` either, for the same reason: printing a wire
    id here that RE-227 never proved would be the mistake its own nonclaims
    section exists to prevent.  CALLED FROM NO SEND PATH ANYWHERE IN THIS
    REPOSITORY; see the module docstring.
    """
    return tuple(
        (record.trigger_id,) + encode_add_survey_data_outer(
            legacy, msg_id, vital_version, record.fields,
        )
        for record in trial_survey_records()
    )
