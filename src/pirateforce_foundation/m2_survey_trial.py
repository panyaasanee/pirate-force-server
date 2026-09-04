"""LANE-E / M2: the attended-only opening for the survey-record provisioning
trial, and the two trial numbers that trial has to supply.

WHAT THIS MODULE IS.  It is a gate and two constants -- nothing composes a
frame here and nothing sends one.  The composer already exists (LANE-A's M2
provisioning-trial module, on `main` since server#753 -- deliberately NOT
named as a string here, so this file stays outside that module's own
"who may name me" guard) and the call site is chief's, in `runtime.py`.
What was missing between them, and is supplied here, is (1) a fail-closed
environment opening so the trial cannot reach a flagless boot, and (2) the
two numbers the composer refuses to default: the wire ``msg_id`` and the
``vital_version``.

THE OPENING: ``PF_M2_SURVEY_TRIAL``
-----------------------------------
Same shape as ``gm/speed_wire.py``'s ``PF_SPEED_TRIAL`` (which says of
itself: "FAIL-CLOSED IN THE SAME SHAPE PFGM_FORCE USES"), for the same
reason -- an attended round arms it on one boot, and every other boot in the
world is shut without anybody having to remember to shut it:

    unset            -> TRIAL_UNSET      (shut, silent-by-default)
    exactly "1"      -> TRIAL_OPEN       (armed)
    anything else    -> TRIAL_MALFORMED  (shut, and NAMED on the console)
    environ raises   -> TRIAL_MALFORMED  (shut)

``environ`` is injectable, so a test of THIS module never touches the
process environment.  A test that drives the real dispatcher still has to
set the real variable -- there is no injection seam through `runtime.py` --
and `tests/test_m2_survey_trial.py` does exactly that, under `addCleanup`
(pf-adversary D12: the earlier wording claimed more than the tests do).

WHY THE VALUE IS EXACTLY "1" AND CARRIES NO NUMBERS.  An earlier draft let
the flag carry ``msg_id=...`` so an attended tester could try another id
without a rebuild.  That is a worse trade than it looks: the two numbers
below are the ones the evidence names, a tester has no independent basis for
choosing a different one, and a mistyped id would produce exactly the same
observation as a wrong hypothesis (a client that ignores the frame) with
nothing on the console able to tell the two apart.  So the numbers are in
the build, printed on the console when they go out, and named in the ticket.

``NAVIGATIONEX_ADD_SURVEY_DATA_VITAL_ID`` -- A TRIAL VALUE, NOT A PROVEN ONE
---------------------------------------------------------------------------
0xC4AF.  What is measured about it, and what is not, in the order it matters
(evidence gathered this round, pf_bridge/rounds/R342_*):

  MEASURED  The name in the client is ``NavigationEx_AddSurveyDataVtial``,
            typo included, confirmed by three independent structures: the
            runtime literal at VA 0x00F47000 (thunk census), the RTTI type
            descriptor ``.?AVNavigationEx_AddSurveyDataVtial@@`` in .data
            (FACTPACK_L2_CLASSCENSUS001_20260820.tsv:874), and Codex's own
            registry row (pf_bridge/external/PF_PROTOCOL_REGISTRY.tsv:465).
            Spelling it correctly as "...Vital" yields 0xC4BA -- a DIFFERENT
            number -- so the typo is load-bearing.
  MEASURED  The v141 protocol_name_id hash
            ``sum((i+1)*ord(c) for i,c in enumerate(name)) & 0xFFFF``
            reproduces the id of all 327 rows of
            pf_bridge/VITAL_REGISTRY_FROM_CLIENT_BINARY_20260817.tsv with
            zero mismatches (controls: TriggerVital 0x1FB2,
            NavigationEx_EnterInstanceVital 0xC723,
            NavigationEx_UseAddingMoraleItemResultVital 0x7A94), and matches
            docs/PF_VITAL_NAMES.json -- an independent snapshot -- on every
            one of the 280 names the two share, with zero mismatches
            (pf-adversary D10 re-derived the count: an earlier draft of
            this note said 17, which was never the shared count).  That
            hash over the name above is 0xC4AF.
            ``tests/test_m2_survey_trial.py`` recomputes it, so a typo in
            these four hex digits is a red test, not a silent no-match.
  MEASURED  The vital sits mid-block with two PROVEN neighbours: id slots
            0x01089668..0x01089680 run contiguously
            (RequestSurvey / AddSurveyData / RemoveSurveyData /
            StartSalvaging / EndSalvaging / EnterInstance / UseAddingMorale),
            and the two slot VAs Codex gives for the PROVEN pair match the
            registry exactly.  Circumstantial, and labelled as such.
  NOT PROVEN  No artifact anywhere on this clone READS 0xC4AF out of the
            binary.  Every source DERIVES it from the name, so they are not
            independent of each other: the registry does not carry the row
            at all (its round-62 string sweep covered 310 of 519 thunks and
            missed five of the seven NavigationEx vitals), and the census
            file says of itself "THIS IS NOT A NAME TABLE ... 'wire_id' is
            DERIVED, not read from a table in the binary".
  NOT PROVEN  No frame of this vital has ever been observed on real wire
            (pf_bridge/external/PF_FIELD_VALIDATION.tsv:928-929:
            observed_frames 0, NOT_OBSERVED both directions).

So: if the client's string is spelled as three structures say it is, and if
the client's id assignment is the same hash it demonstrably is across the 345
names these two independent tables corroborate between them, then 0xC4AF follows.  That is a strong argument and it is still an
argument -- which is why this is a TRIAL value behind an attended-only flag,
sent with its own console line, exactly as COO-DECISION 20260904_1845 item 1
directed.  GT-233 is the cheapest thing that would upgrade it: a captain's
report window that pops is an observation of the id INDEPENDENT of the name.

``NAVIGATIONEX_ADD_SURVEY_DATA_VITAL_VERSION`` -- ALSO A TRIAL VALUE
--------------------------------------------------------------------
0.  Weaker evidence than the id, and it is not dressed up: RE-227 never
named a version, no ``*_VITAL_VERSION_CONFIRMED`` constant exists for this
vital, and nothing has been observed.  0 is this codebase's own modal value
for a version whose vital has no proven one (trace_path, gm/attr_wire,
mob_combat's CHitResult, the ui_*_wire family all use 0), and the frozen
envelope writes it as a single ``u8tag(0x0B, vital_version)``.  If GT-233
comes back with the window not popping, the version is one of the two
numbers to vary before the mechanism is doubted -- the ticket says the same
about the XYZ.
"""
from __future__ import annotations

import os

from . import world_m2_survey_plan


SURVEY_TRIAL_ENV = "PF_M2_SURVEY_TRIAL"
SURVEY_TRIAL_ARMED_VALUE = "1"

TRIAL_UNSET = "unset"
TRIAL_OPEN = "open"
TRIAL_MALFORMED = "malformed"

# The sea scene the attended round actually boots into: GT-228/R308
# (pf_bridge/notes_to_chief/20260904_1331_KA1A-R308-*) recorded
# `WORLD_SCENE scene_id=126` and an `S126-SPAWN` line on the very boot where
# island contact fired TriggerVital id 2 and id 3.  This is NOT the same
# claim as "126 is the Columbus destination" -- it is not, and
# `world_m2_sea_destination.py` explains at length why the ocean PANEL id
# and the ship scene are different things.
#
# READ FROM THE PLAN, NOT RE-TYPED (pf-adversary D6, this round).  The
# number that matters is the frame LANE-A's coordinates are expressed in,
# and the plan writes that down as `XYZ_FRAME_SCENE_ID`.  A second literal
# here would let the plan be re-measured in another scene while the call
# site kept firing in this one, sending a triple into the wrong space --
# and `world_m2_survey_plan.py:56-60` says the symptom of that is "the
# captain report never popped", the same symptom as every other failure
# this trial can have.
M2_SEA_SCENE_ID = world_m2_survey_plan.XYZ_FRAME_SCENE_ID


def plan_frame_matches(scene_id) -> bool:
    """Whether the plan's coordinates are expressed in ``scene_id``'s frame.

    Delegates to `world_m2_survey_plan.plan_is_for_scene`, which exists for
    exactly this question ("a caller that provisions records without asking
    this is sending a triple into the wrong space") -- re-exported here so
    the call site asks it without naming a second module.
    """
    try:
        return bool(world_m2_survey_plan.plan_is_for_scene(scene_id))
    except Exception:  # noqa: BLE001 - a predicate that cannot answer is a
        # closed door, same direction as every other failure here.
        return False

# Both TRIAL values.  See the module docstring for exactly what is measured
# about each and what is not.  Neither is a proven wire fact; both are
# printed on the console when a frame carrying them goes out.
NAVIGATIONEX_ADD_SURVEY_DATA_VITAL_NAME = "NavigationEx_AddSurveyDataVtial"
NAVIGATIONEX_ADD_SURVEY_DATA_VITAL_ID_TRIAL = 0xC4AF
NAVIGATIONEX_ADD_SURVEY_DATA_VITAL_VERSION_TRIAL = 0


def protocol_name_id(name: str) -> int:
    """The v141 protocol_name_id hash, as the registry's own header states
    it: ``sum((i+1)*ord(c) for i,c in enumerate(name)) & 0xFFFF``.

    Here so the test can recompute the trial id over the wire name rather
    than restating four hex digits in a second place.
    """
    return sum((i + 1) * ord(c) for i, c in enumerate(name)) & 0xFFFF


def trial_opening(environ=None) -> str:
    """``TRIAL_UNSET`` / ``TRIAL_OPEN`` / ``TRIAL_MALFORMED`` for this boot.

    Never raises.  A process whose ``os.environ`` is unreadable (embedded
    interpreters have managed it) reads as MALFORMED, which is shut -- the
    same direction every other failure takes.
    """
    try:
        source = os.environ if environ is None else environ
        raw = source.get(SURVEY_TRIAL_ENV)
    except Exception:  # noqa: BLE001 - a broken environ must not take the
        # listener down, and must not open the trial either.
        return TRIAL_MALFORMED
    if raw is None:
        return TRIAL_UNSET
    if raw == SURVEY_TRIAL_ARMED_VALUE:
        return TRIAL_OPEN
    return TRIAL_MALFORMED


def console_line(
    state: str, scene_id: int, record_count: int = 0,
    confirmed=None, guess=None,
) -> str:
    """The one console line the call site prints, ASCII only (the bridge
    console is cp874; round 86 and round 142 both died on this).

    One token per outcome, all greppable, and the armed one names both trial
    numbers so a capture and the console agree on what was actually sent
    without anyone having to read the build:

        M2_SURVEY_TRIAL_SENT scene=126 records=2 msg_id=0xC4AF version=0
            confirmed=126 guess=0
        M2_SURVEY_TRIAL_NOT_THIS_BOOT scene=126 reason=unset confirmed=none
            guess=1
        M2_SURVEY_TRIAL_REFUSED scene=126 reason=<exception type>

    ``confirmed`` and ``guess`` say whether the scene in the line is
    something the CLIENT reported or something this server merely intends
    (pf-adversary D2): a `/warp` relabels the row at queue time and the
    client is free to ignore it, so a line that only carried the label
    could report a send "in scene 126" to a player standing in Port Royal.
    Omitted from the text when the caller passes neither.
    """
    tail = ""
    if confirmed is not None or guess is not None:
        tail = (
            f" confirmed={'none' if confirmed is None else int(confirmed)}"
            f" guess={int(bool(guess))}"
        )
    if state == TRIAL_OPEN:
        return (
            "M2_SURVEY_TRIAL_SENT"
            f" scene={int(scene_id)}"
            f" records={int(record_count)}"
            f" msg_id=0x{NAVIGATIONEX_ADD_SURVEY_DATA_VITAL_ID_TRIAL:04X}"
            f" version={NAVIGATIONEX_ADD_SURVEY_DATA_VITAL_VERSION_TRIAL}"
            + tail
        )
    return (
        "M2_SURVEY_TRIAL_NOT_THIS_BOOT"
        f" scene={int(scene_id)} reason={state}" + tail
    )


def refusal_line(scene_id: int, reason: str) -> str:
    """The line for a trial that was armed and still could not compose --
    deliberately a DIFFERENT token from the shut-boot one, so "armed and
    broken" can never be read as "not armed".
    """
    return f"M2_SURVEY_TRIAL_REFUSED scene={int(scene_id)} reason={reason}"
