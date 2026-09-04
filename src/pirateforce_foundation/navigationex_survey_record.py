"""LANE-A / M2: the `NavigationEx_AddSurveyDataVtial` record encoder.

COO-DECISION 20260904_0747 item 3(b): RE-227 (static, full CFG census;
pf_bridge/notes_to_chief/20260904_0724) pinned the nested-record field
layout the server must provision so a client checks island proximity
locally and pops the captain-report window on its own -- but the same
letter, in the same breath, forbids sending it for real:

    ห้ามส่งออกสาย production จนกว่าจะมี XYZ ของเกาะ 2/3 ที่วัดได้
    (ไม่ใช่เดา ไม่ใช่จาก actor ใน Bg3001 ที่ 0525 บอกว่าไม่ใช่เป้า)
    เปิดได้เฉพาะเมื่อ XYZ มาจาก GT-228

So this module builds the record and tests it byte-for-byte against RE-227's
own pinned field list.  ~~"and IS CALLED FROM NO SEND PATH ANYWHERE IN THIS
REPOSITORY"~~ IS STRUCK as of 2026-09-04 (chief, round `t7bsfx`/R342, PR
#760): GT-228 measured the island XYZ, and the runtime.py call site the
paragraph anticipated now exists -- reaching this file transitively through
LANE-A's provisioning-trial module (not named as a string here, so this file
stays outside that module's own "who may name me" guard), behind the flag
`PF_M2_SURVEY_TRIAL`, per COO-DECISION 20260904_1845 item 1.

NESTED RECORD FIELD LAYOUT (RE-227, verbatim field order and offsets;
nested-record serializer span `[0x0072e590,0x0072e691)` SHA
`5b714541671c8731a3b88df657089f97645ad1a6d2dc7ec9f06ee7ee271aa8f2`):

    `0B` byte  @ record `+0x10`  -- PROVEN: the contact tick selects a
                                    record only when this byte == 1
                                    (`SURVEY_RECORD_KIND`).
    `12` u16   @ `+0x12`         -- the "opaque" survey id.  PROVEN: copied
                                    unchanged into the EnterInstanceVital
                                    confirm frame.  Nothing proves it is an
                                    island id, a scene id, or a Trigger-TIP
                                    id (RE-227 nonclaim 3) -- callers must
                                    not read meaning into it either.
    `12` u16   @ `+0x14`         -- UNMEASURED.  RE-227: "field อื่นคง
    `12` u16   @ `+0x16`            opaque" (only the float triple has a
                                    proven consumer crosswalk).
    `2A` f32   @ `+0x18`         -- X.  PROVEN crosswalk: the contact tick
    `2A` f32   @ `+0x1C`            compares this triple against the
    `2A` f32   @ `+0x20`            player's position (squared distance
                                    <=250000, i.e. <=500 units).
    `32` qword @ `+0x28`         -- UNMEASURED.
    `12` u16   @ `+0x30`         -- UNMEASURED.

THE OUTER ENVELOPE IS NOT RE-227's TO GIVE.  RE-227 pinned the outer
serializer only as an address span and a hash
(`[0x00733570,0x00733614)`), with no per-field breakdown -- unlike the
nested record, which it gave field-by-field.  Guessing that shape from the
span alone would be exactly the "guessing an opcode" this project's lanes
are forbidden to do.  What IS already proven and already used by this same
codebase for the same *kind* of frame -- one nested vital record pushed as
the sole element of a client's VitalData collection -- is
`current/pf_login_game_server_v141.py`'s own `make_runtime_vitals`, the
PLURAL composer, called with a one-element list.  `encode_add_survey_data_
outer` below reuses that frozen function rather than re-deriving the
envelope by hand: it is the proven "push records" shape, not a new guess.

~~an earlier version of this paragraph named the SINGULAR
`make_runtime_vital`~~ IS STRUCK (chief, round `t7bsfx`/R342, pf-adversary
D1).  The two composers agree byte-for-byte except that the plural one
appends the trailing `0B 00` derived-class change mask, and this repository
records THREE independent incidents of the singular envelope raising
`GSCN_RunTimeProtocolRes ErrorData=28317` on the real client -- v141:706-710
(the frozen composer's own comment), `delete_actor_hypothesis.py:28-33`
(attended GT-010, 2026-08-18), `gm/state_wire.py:104-116` (GT-107/RE-113) --
and `gm/chat_command_action.py:1281` records that error CLOSING the client
in R306.  `tests/test_navigationex_survey_record.py` now pins the two bytes
as a byte fact, so this cannot regress quietly.

R313 (2026-09-05, attended, `pf_bridge/notes_to_chief/20260905_0212_KA1A-
R313-RESULTS-*`) SENT THIS FOR REAL AND THE CLIENT REJECTED IT.  The client
named the class itself in the error dialog -- "NavigationEx_AddSurveyDataVtial
ErrorData=50351" -- which proves the msg_id is right (RE-227 never had a
numeric id to cite; this is now the closest thing to one) and, per the same
error's own wording, that the record's CONTENT, not the envelope, is what it
could not read.  `tests/test_navigationex_survey_record.py`'s
`R313CaptureParityTests` pins the captured bytes and proves this encoder
reproduces them exactly (both the 60-byte `pc` and the 70-byte compressed
`frame` R313's letter names) -- so the rejection is NOT an encoder-vs-RE-227
mismatch; it must live in one of the four fields this module already labels
UNMEASURED, in `vital_version`, or somewhere RE-227's static pass never
reached.  ROUND `f03s5f` NARROWED THAT LAST CLAUSE TO AN ADDRESS.  50351 is
not an error code: it is `0xC4AF`, this class's own id (see
`R313_SURVEY_DIALOG_ERRORDATA` below and `read_failure_layer`), by the same
rule this repository already spells out for 28317 = `0x6E9D` = the outer
envelope's id.  So the dialog says the outer collection parsed, the client
dispatched to THIS class, and this class's own reader stopped -- and the
one part of this class RE-227 never read field-by-field is its OUTER
serializer `[0x00733570,0x00733614)`, given as a span and a hash only,
while the nested record got a field list.  This round's RE ticket
(`pf_bridge/notes_to_chief/20260905_0430_LANE-A-RE-TICKET-*`) asks for that
span, field by field: whether the class reads a record COUNT (or any header)
before the first record is exactly the kind of fault that produces this
dialog while every field the record does carry is byte-correct.  Nothing
here guesses that shape -- the composer is unchanged until the RE answer
lands.  Closing it further needs either the RE runner's machine (this
environment has no `GameClient.local.bin`) or another attended trial
varying one field at a time -- not another read of this module.
~~"As of this round GT-233's queue head still reads READY ... this round's
letter ASKS for BLOCKED-ON-LAYOUT"~~ IS STRUCK: chief made that edit in
round `s5uz94` (R347, 2026-09-05T03:3x+07:00) and `GAME_TEST_QUEUE.md`'s
GT-233 head now reads BLOCKED-ON-LAYOUT -- read directly from the queue
file this round, not carried over from the last one.

`msg_id` IS A REQUIRED CALLER-SUPPLIED ARGUMENT, ON PURPOSE, WITH NO
DEFAULT -- and it stays that way.  ~~"So this module never writes that
number down as a fact"~~ IS STRUCK in round `f03s5f`: R313 supplied the
client-observable half the paragraph below was waiting for (the client
resolved `0xC4AF` to the class NAME on screen), so the number now has a
home WITH its evidence, `NAVIGATIONEX_ADD_SURVEY_DATA_VITAL_ID` below.
The composer still refuses to default it -- naming a proven number and
choosing it for every caller are two different things, and the trial's two
numbers stay in chief's `m2_survey_trial.py` where the flag is.  The
paragraph that follows is kept, unedited apart from that strike, because
its reasoning is why the number was NOT written down for a fortnight and
what would have to be true to write down the next one:

The numeric wire id for `NavigationEx_AddSurveyDataVtial` is
ABSENT from `pf_bridge/VITAL_REGISTRY_FROM_CLIENT_BINARY_20260817.tsv` --
the same registry that supplied `TriggerVital = 0x1FB2` and
`NavigationEx_EnterInstanceVital = 0xC723` elsewhere in this project
(checked: `grep -i AddSurveyData` against that file returns nothing).  A
broader, lower-confidence census
(`reports/PF_NAMES_FOLD003_LEGACY_SLOTS_AND_THUNK_CENSUS_20260819.census.
json`) names `0xC4AF` for this vital, annotated `"Vtial(typo-in-client)"`,
but that census is not the registry this project's own hash-recompute
pattern treats as ground truth for a wire id, and RE-227 itself never cites
a numeric id for this message -- only the two serializer spans.  Printing
`0xC4AF` into this module as if it were proven would be the same mistake
RE-227's own nonclaims section exists to prevent.  So this module never
writes that number down as a fact: it is left as the caller's job, the same
way `NAVIGATIONEX_ENTER_INSTANCE_VITAL_ID` became a runtime.py constant only
after the registry line that proved it.
"""
from __future__ import annotations

from typing import NamedTuple


# PROVEN (RE-227 item 2): the contact tick only reads a record whose byte at
# +0x10 equals this value.
SURVEY_RECORD_KIND = 1

# The numeric wire id for `NavigationEx_AddSurveyDataVtial`.  The module
# docstring above explains, at length, why this file refused to write this
# number down -- a low-confidence census named it, the registry that this
# project treats as ground truth does not carry the class at all, and
# RE-227 never cites a numeric id.  R313 (attended, 2026-09-05) closed that
# gap FROM THE SCREEN, both layers at once:
#
#   wire              -- the trial sent `msg_id=0xC4AF` (console line
#                        `M2_SURVEY_TRIAL_SENT ... msg_id=0xC4AF`, and the
#                        captured bytes `R313CaptureParityTests` pins).
#   client-observable -- the client's own dialog resolved that id to the
#                        class NAME: "NavigationEx_AddSurveyDataVtial
#                        ErrorData=50351".  An id the client could not
#                        resolve could not have been printed as a name.
#
# So the id is now proven in the way this project requires, and naming it
# here is no longer a guess.  `encode_add_survey_data_outer` still takes
# `msg_id` with NO default: what changed is that the number has a home with
# its evidence attached, not that this composer picked one for its callers.
NAVIGATIONEX_ADD_SURVEY_DATA_VITAL_ID = 0xC4AF

# `ErrorData` IN THE CLIENT'S "VitalData read failed" DIALOG IS A MESSAGE
# ID, NOT AN ERROR CODE.  This repository already knew that for one number:
# `delete_actor_hypothesis.py:32` and `mob_loot.py:159` both spell out
# "28317 = 0x6E9D = GSCN_RunTimeProtocolRes, the class id itself".  R313's
# number obeys the same rule and nobody had applied it yet:
#
#     50351 == 0xC4AF == NAVIGATIONEX_ADD_SURVEY_DATA_VITAL_ID
#
# That matters for GT-233's diagnosis, because the R313 letter reads the
# two numbers as two error codes ("คนละรหัสกับ 28317") and concludes from
# their difference that the fault moved from the envelope to the record.
# The difference does not carry that meaning on its own -- but the rule
# does, and it happens to point the same way, more precisely: ErrorData
# names the object whose reader stopped, so 28317 meant "the outer
# RunTimeProtocolRes could not finish" while 50351 means "the outer
# envelope parsed, the client dispatched to THIS class, and this class's
# own reader is what failed".  What it does NOT say is WHICH field -- an
# id names a place, not a cause.  `read_failure_layer` below is that rule
# as code, so the next attended round can read a dialog number without
# doing hex by hand at the screen.
R313_SURVEY_DIALOG_ERRORDATA = 50351

# Fixed nested-record length: 1 (tag 0x0B) + 1 (u8 value) + 3*(1+2) (three
# u16 fields) + 3*(1+4) (three f32 fields) + 1+8 (one qword field)
# + 1+2 (one trailing u16 field) = 2 + 9 + 15 + 9 + 3 = 38 bytes.
RECORD_LEN = 38


class SurveyRecordFields(NamedTuple):
    """Every field RE-227 pinned for the nested `NavigationEx_
    AddSurveyDataVtial` record, in wire order.  Every field past
    ``survey_id`` and the XYZ triple is UNMEASURED (see module docstring) --
    named here by offset, not by guessed meaning, so a caller cannot
    mistake a placeholder for a proven value.
    """

    survey_id: int          # +0x12 u16, opaque -- echoed by EnterInstance
    x: float                # +0x18 f32
    y: float                # +0x1C f32
    z: float                # +0x20 f32
    unmeasured_0x14: int = 0    # +0x14 u16, UNMEASURED
    unmeasured_0x16: int = 0    # +0x16 u16, UNMEASURED
    unmeasured_0x28: int = 0    # +0x28 qword, UNMEASURED
    unmeasured_0x30: int = 0    # +0x30 u16, UNMEASURED


def read_failure_layer(legacy, error_data: int) -> str:
    """Which object's reader stopped, for an ``ErrorData`` number read off
    the client's "VitalData read failed" dialog.

    Returns one of:

        ``"OUTER_ENVELOPE"``  -- the collection envelope itself
                                 (``legacy.GSCN_RUNTIME_PROTOCOL_RES``);
                                 the historical 28317.
        ``"THIS_VITAL"``      -- the AddSurveyData object; R313's 50351.
        ``"SOMETHING_ELSE"``  -- an id this module has no name for.  NOT
                                 "unknown error": some other class failed,
                                 and its id is the number itself.

    This is a reading aid over a rule this repository already proved, not a
    new claim: the number is an id.  It deliberately says nothing about
    WHICH field of that object was wrong, because the client does not tell
    us -- see the block comment above `R313_SURVEY_DIALOG_ERRORDATA`.
    """
    if error_data == legacy.GSCN_RUNTIME_PROTOCOL_RES:
        return "OUTER_ENVELOPE"
    if error_data == NAVIGATIONEX_ADD_SURVEY_DATA_VITAL_ID:
        return "THIS_VITAL"
    return "SOMETHING_ELSE"


def encode_survey_record(legacy, fields: SurveyRecordFields) -> bytes:
    """The nested `NavigationEx_AddSurveyDataVtial` record, byte-for-byte
    per RE-227's pinned field list and order.

    ``legacy`` is the loaded frozen module (``legacy_bridge.load_legacy`` /
    a projector's ``self.v`` / a test's own import of
    `current/pf_login_game_server_v141.py`) -- this module never imports
    the frozen file itself, the same discipline the rest of this lane's
    encoders and hooks already follow, so a caller always controls which
    build of the frozen tag helpers is in play.
    """
    return (
        legacy.u8tag(0x0B, SURVEY_RECORD_KIND)
        + legacy.u16tag(0x12, fields.survey_id)
        + legacy.u16tag(0x12, fields.unmeasured_0x14)
        + legacy.u16tag(0x12, fields.unmeasured_0x16)
        + legacy.f32tag(fields.x)
        + legacy.f32tag(fields.y)
        + legacy.f32tag(fields.z)
        + legacy.qwordtag(0x32, fields.unmeasured_0x28)
        + legacy.u16tag(0x12, fields.unmeasured_0x30)
    )


def encode_add_survey_data_outer(
    legacy, msg_id: int, vital_version: int, fields: SurveyRecordFields,
) -> tuple[bytes, bytes]:
    """The full outbound frame: `legacy.make_runtime_vitals` (the frozen,
    already-proven VitalData-collection envelope, WITH the trailing
    derived-class change mask) wrapped around one
    ``encode_survey_record(legacy, fields)``.

    Returns ``(pc, frame)``, same shape as every other frozen composer in
    this project.  ``msg_id`` has no default -- see the module docstring
    for why the numeric wire id is not committed as a fact here.

    ~~CALLED FROM NO SEND PATH~~ IS STRUCK (2026-09-04, PR #760): GT-228
    measured the XYZ that COO-DECISION 20260904_0747 item 3(b) made the
    condition, and chief added the runtime.py call site it named, behind
    the attended-only flag.  It is still called from exactly one place.
    """
    record = encode_survey_record(legacy, fields)
    # PLURAL, not `make_runtime_vital`.  Chief, round `t7bsfx`/R342, after
    # pf-adversary D1 measured the difference on this very frame: the two
    # composers agree byte-for-byte except that the plural one appends the
    # trailing `0B 00` derived-class change mask, and THREE independently
    # documented incidents in this repository say the singular envelope is
    # what raises `GSCN_RunTimeProtocolRes ErrorData=28317` on the real
    # client -- `current/pf_login_game_server_v141.py:706-710` (the frozen
    # composer's own comment: "omitting it makes the client over-read the
    # collection response"), `delete_actor_hypothesis.py:28-33` (attended
    # GT-010 falsified the singular composition live on 2026-08-18), and
    # `gm/state_wire.py:104-116` (GT-107/RE-113, fixed the same one-line
    # way).  `gm/chat_command_action.py:1281` records that error CLOSING
    # the client in R306, which would spend GT-233's whole attended round
    # on a STOP that looks exactly like a wrong `msg_id`.
    #
    # The docstring above called this envelope "the proven 'push one
    # record' shape".  It is -- for a collection whose mask is present.
    # One record still goes into the collection; the list is the shape the
    # proof was for.
    return legacy.make_runtime_vitals([(msg_id, vital_version, record)])
