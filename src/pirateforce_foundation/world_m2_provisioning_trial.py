"""LANE-A / M2: the first provisioning trial's two records, composed and
ready for a send path.

~~"and called by no send path anywhere in this repository"~~ IS STRUCK as of
2026-09-04 (chief, round `t7bsfx`/R342, PR #760): `runtime.py` now calls
`encode_trial_records` once, in scene 126, behind the attended-only flag
`PF_M2_SURVEY_TRIAL`, per COO-DECISION 20260904_1845 item 1 -- which is the
CORE-REQUEST this file's own docstring asked for below.  The guard test that
backed the old claim was not deleted: it now names that one caller, and
`tests/test_m2_survey_trial.py::RuntimeCallSiteTests` holds the other half
(one call, inside the branch the flag opens, both numbers read from the gate
module).

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

BOTH OF THE TWO THINGS BELOW LANDED ON 2026-09-04 (see the strike above);
they are kept here because they say what the call site had to supply and on
what terms:

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
encoding the two trial records is not a new guess -- it is these two
calls. -- BOTH LANDED (round `t7bsfx`/R342): `msg_id`/`vital_version` are
`m2_survey_trial.NAVIGATIONEX_ADD_SURVEY_DATA_VITAL_ID_TRIAL` /
`..._VERSION_TRIAL`, and the call site is `runtime.py`'s
`m2_survey_trial_scene_attempted` block, which calls `encode_trial_records`
exactly once per arrival in scene 126 and appends
`m2_survey_trial_sent_<count>` to `session.events` when it composes
something -- the one place in this repository that composing a send is
recorded (pf-adversary, round `m1wqqy`: nobody has traced this event
through to a confirmed socket write, so it proves a frame was QUEUED, not
that it left the wire), and
the source `lane_hooks/lane_a_enter_instance_log.py`'s `sent=` fragment now
reads from (`ADVERSARY_PENDING` item 1, round `16uvmp`, closed round
`m1wqqy`).  `encode_trial_records`'s scene guard now has a NAMED reason too
(`world_m2_survey_plan.scene_guard_reason`; `ADVERSARY_PENDING` item 3,
same closing round) -- this function still returns the bare `()` its one
caller expects (chief's `elif trial_state == TRIAL_OPEN` branch reads only
truthiness), so a CORE-REQUEST is what it takes to have `runtime.py` print
the reason on its own refusal line instead of the generic `no_records`; see
this round's letter.

RECORD `+0x14` IS NO LONGER A BARE ZERO (round `yob0a2`+1, LANE-A,
COO-DECISION `20260905_1947` item 2, answering `RE-265`).  RE-265 (`pf_bridge/
notes_to_chief/20260905_1932_RE-265-RESULT-COMMON-CONFIRM-OPENS-AFTER-
SAILING-RESULT-KEY.md`) found the gate R318 actually missed: the client's
contact tick reads `+0x14` as a key into a store loaded from the client table
`SAILING_RESULT`, and exits BEFORE the XYZ distance test when the lookup is
null -- exactly what a bare `+0x14=0` produces.  Both trial records now carry
a REAL candidate from `CONSTDATA_TH__SAILING_RESULT.tsv` (the scene these
records are provisioned for is `n_AREA=126`), derived from a committed copy
of that table, never typed in.

THE TWO CANDIDATES NOW DISCRIMINATE A COLUMN, NOT A ROW (round `tk4hr7`+1,
LANE-A, COO-DECISION `20260905_2349` item 1, GT-233 v3 option (ข) --
SUPERSEDES the row-discriminating design below this paragraph replaced).
RE-265 measured that `+0x14` is a key into a `SAILING_RESULT`-derived store,
but never measured WHICH COLUMN of that table the store is keyed by
(pf-adversary, round `tk4hr7`, D3): the retired design assumed `n_ID` and
only ever tested "which row", which cannot come back positive if the store
is actually keyed by `n_AREA` (or anything else) instead.
`world_m2_sailing_result_key.column_discriminating_keys()` gives the two
records one candidate per named hypothesis instead: the lowest `n_ID` among
the 18 `n_AREA=126` rows (dock 153 / Prison Exile), and `n_AREA` itself,
`126` (dock 154 / Spice Paradise) -- a resolved lookup on either record is
now evidence about which COLUMN the client reads, and a silent result on
BOTH means the column is still unknown, not that the whole
`SAILING_RESULT`-key theory is wrong (no-backup attended shot, COO-DECISION
`20260905_1348`; see the `GT-233` v3 ticket for the exact sentence).  This
also closes D8: the retired design's two lowest `n_ID`s (`1`, `2`) put
island 3's key exactly equal to island 2's `+0x12` (`survey_id`, `2`/`3` for
the two docks); the new pair (`1`, `126`) matches neither dock's `+0x12`.

~~"one DISTINCT id per record" (pf-adversary, round `wjprxa`, D1: reusing
one id for both records would have spent GT-233's single no-backup attended
shot on one candidate instead of two)~~ IS STRUCK along with the function it
described (`provisional_area_126_keys`) -- the reasoning was sound for
"which row" but never addressed "which column", which is the question
COO-DECISION `20260905_2349` actually asks this trial to answer.  The table
still does not name which of its 18 `n_AREA=126` rows belongs to which
island -- see that module's own docstring -- so the `n_ID` candidate is
still COO's own fallback reading, marked PROVISIONAL, not a claim that the
client cares which row it is.
"""
from __future__ import annotations

from typing import NamedTuple

from . import world_m2_survey_plan as plan
from . import world_m2_sailing_result_key as sailing_result
from .navigationex_survey_record import (
    OUTER_PRESENCE_PRESENT,
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

    Each record's `+0x14` gets a DIFFERENT `world_m2_sailing_result_key`
    COLUMN HYPOTHESIS, not a different row of the same column
    (COO-DECISION `20260905_2349` item 1, GT-233 v3 option (ข); see
    `world_m2_sailing_result_key.column_discriminating_keys` for the full
    reasoning, and this module's own docstring for why the row-
    discriminating design it replaces could never come back positive if the
    client keys its store by `n_AREA` instead of `n_ID`).  Ordered the same
    way `planned_records()` already is
    (`world_m2_survey_plan.PLANNED_TRIGGER_IDS`: 153 then 154), so dock 153
    (Prison Exile) always gets the `n_ID` candidate and dock 154 (Spice
    Paradise) always gets the `n_AREA` candidate -- reproducible, not
    incidental, and load-bearing for reading GT-233's result (a pop on one
    record and not the other says which column, only because which record
    tested which hypothesis is fixed).

    THIS FUNCTION, NOT `column_discriminating_keys`, IS WHERE D8 IS ACTUALLY
    ENFORCED (pf-adversary round `tk4hr7`+1, re-verification of this
    round's own first D8 fix): `column_discriminating_keys` has no idea
    what `+0x12` (`survey_id`) values this trial is about to send -- only
    this function, which reads BOTH `plan.trial_survey_id(record)` and the
    `+0x14` candidates, can check them against each other.  The first
    version of this round's fix only guarded the two `+0x14` candidates
    against EACH OTHER (never equal to each other), which pf-adversary
    proved insufficient by monkeypatching `provisional_area_126_key()` to
    return `2` -- a plausible future TSV update -- and observing the
    collision with dock 153's own `+0x12` pass through silently.  So every
    `+0x14` candidate is checked here against every `+0x12` this trial
    sends, structurally, not just against today's committed data.
    """
    records = plan.planned_records()
    keys = sailing_result.column_discriminating_keys(len(records))
    survey_ids = tuple(plan.trial_survey_id(record) for record in records)
    for key in keys:
        if key in survey_ids:
            raise sailing_result.SailingResultCopyError(
                f"+0x14 candidate {key} collides with a +0x12 survey_id "
                f"this trial sends ({survey_ids!r}) -- a resolved lookup "
                "could not be told apart from the client echoing the "
                "other field; refusing to compose ambiguous records "
                "(D8, pf-adversary round tk4hr7)"
            )
    return tuple(
        TrialSurveyRecord(
            trigger_id=record.trigger_id,
            fields=SurveyRecordFields(
                # `plan.trial_survey_id(record)`, not `record.scene_name_tip_id`
                # spelled again here: the value this trial SENDS and the value
                # `plan.confirm_resolution` can RECOGNISE on the echo have to be
                # one decision in one place.  Round `16uvmp` measured what two
                # copies cost -- the plan recognised only its own 0xA0xx handle,
                # so a perfect attended run of GT-233 would have echoed 2/3,
                # resolved as "not issued", refused the arrival, and printed the
                # one console line that reads as a refutation of RE-227.
                survey_id=plan.trial_survey_id(record),
                x=record.x,
                y=record.y,
                z=record.z,
                # RE-265 + COO-DECISION 20260905_1947 item 2: a real
                # SAILING_RESULT key, not a bare zero -- see the module
                # docstring's "RECORD +0x14 IS NO LONGER A BARE ZERO".  A
                # DIFFERENT COLUMN HYPOTHESIS per record (n_ID here,
                # n_AREA there), not a different row of the same column --
                # see this function's own docstring and COO-DECISION
                # 20260905_2349 item 1.
                unmeasured_0x14=key,
            ),
        )
        for record, key in zip(records, keys)
    )


def encode_trial_records(
    legacy, msg_id: int, vital_version: int, player_scene_id: int,
    outer_leading_byte: int | None = OUTER_PRESENCE_PRESENT,
) -> tuple[tuple[int, bytes, bytes], ...]:
    """``(trigger_id, pc, frame)`` for every record in
    ``trial_survey_records()``, encoded through ``navigationex_survey_
    record.encode_add_survey_data_outer`` -- or ``()`` when the player is
    not standing in the scene these coordinates are expressed in.

    ``legacy``, ``msg_id`` and ``vital_version`` are exactly that function's
    own required arguments, passed through unchanged -- this function adds
    no default for ``msg_id`` either, for the same reason: printing a wire
    id here that RE-227 never proved would be the mistake its own nonclaims
    section exists to prevent.  Its one caller (runtime.py, behind the
    attended-only flag `PF_M2_SURVEY_TRIAL`) passes 0xC4AF as a TRIAL value
    with a console line naming it; see the module docstring's strike.

    ``player_scene_id`` HAS NO DEFAULT ON PURPOSE, AND THE REASON IS A
    MEASURED ONE (pf-adversary, round `16uvmp`).  `world_m2_survey_plan`
    has carried `plan_is_for_scene()` since it was written and nothing has
    ever called it, while the call site this module was waiting for is
    described only as "when the player enters the sea scene".  Wire that
    without the guard and a player who reaches scene 17 -- the scene row
    3021 actually teleports to, see `world_m2_sea_destination` -- gets both
    records provisioned with SCENE-126 coordinates.  Land within 500 units
    of one of those triples in scene 17's own frame and the client pops the
    captain report; confirming it now composes a full deliverable arrival
    (round `16uvmp` made the confirm resolve), so the cost of the missing
    guard changed from a refusal to a teleport.  Requiring the caller to
    say where the player is makes the check impossible to forget rather
    than easy to remember.  Chief's call site (round `t7bsfx`) asks the
    same question a second time, on its own side, before it gets here.
    ``outer_leading_byte`` IS FORWARDED, NOT INVENTED HERE (round
    `f03s5f`, pf-adversary pass 2).  The composer grew that argument
    because `pf_bridge/external/PF_SERIALIZER_FIELDS.tsv` and RE-086 both
    record a `0x0B` field of length 1, gate ALWAYS, on this class's own
    outer serializer, and R313's frame carried none.  A first version of
    that change left this function unable to pass it, which would have
    let an attended round set the flag, send byte-identical bytes, get
    the same dialog, and report "the byte did not help" without ever
    having sent it.

    ~~"`None` -- the default, and what chief's call site passes today --
    keeps R313's exact bytes"~~ IS STRUCK, round `vwekfq` (LANE-A): RE-256
    (`pf_bridge/notes_to_chief/
    20260905_1007_RE-256-RESULT-PRESENCE-ONE-SINGLE-RECORD-VERSION-ZERO.md`)
    measured this byte directly for this class -- a pointer-presence
    boolean, ``1`` for one record present, ``0`` for none, never a record
    count -- which resolves the layout/version half of GT-233's gate.  This
    function is the one place in this repository that builds a REAL
    GT-233 trial record for an actual send (`runtime.py`'s call site, one
    caller, behind `PF_M2_SURVEY_TRIAL`), so it is the caller RE-256's
    BUILD_IMPACT line means: a real send must not choose ``None`` any
    more.  The default is now `OUTER_PRESENCE_PRESENT` (``1``) -- every
    record this function returns is a record that IS present (the early
    `return ()` above is how "no record" is expressed; it never reaches an
    `outer_leading_byte` question at all, so there is no live call path
    where `0` is the right default here).  `runtime.py`'s call site does
    not pass this argument explicitly and so now gets the corrected byte
    automatically, with no edit to `runtime.py` itself.  `None` is kept as
    a still-valid explicit override (chiefly for tests that want to
    reproduce R313's original, pre-RE-256 bytes on purpose), never as
    something a real send falls back to.
    """
    if not plan.plan_is_for_scene(player_scene_id):
        return ()
    return tuple(
        (record.trigger_id,) + encode_add_survey_data_outer(
            legacy, msg_id, vital_version, record.fields,
            outer_leading_byte=outer_leading_byte,
        )
        for record in trial_survey_records()
    )


def trial_scene_refusal_reason(player_scene_id: object) -> str | None:
    """``None`` when ``encode_trial_records(player_scene_id, ...)`` would
    compose records; otherwise the NAMED reason its scene guard refused
    (`world_m2_survey_plan.scene_guard_reason`).

    `encode_trial_records` itself still returns the bare `()` its one caller
    (`runtime.py`) already handles by truthiness -- widening that return
    shape is chief's call, not this module's, and the CORE-REQUEST for it is
    this round's letter.  This function exists so a caller who DOES want the
    reason -- a test, or `runtime.py` after that request lands -- has
    somewhere to ask instead of re-deriving it from `player_scene_id ==
    world_m2_survey_plan.XYZ_FRAME_SCENE_ID`.  Never raises.
    """
    return plan.scene_guard_reason(player_scene_id)
