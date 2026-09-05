"""LANE-B: which attack animation the client plays, on an unflagged boot.

WHAT A PLAYER SEES BECAUSE THIS MODULE EXISTS.  Until now every hit this
server acknowledged echoed the request's own ``+0x30`` (60029) straight back,
and ``GT-247``'s attended run measured what that looks like on the client:
damage numbers rise and **the character does not swing**.  This module is the
production answer -- the BEHAVIOR id of the weapon the performer's class
actually carries, so the swing happens -- with no flag, no scenario and no
environment variable in the path.

THE EVIDENCE THIS IS BUILT ON, and the one place it stops.

``GT-247`` PASS, R315, 2026-09-05 10:24 +07 (``pf_bridge/notes_to_chief/
20260905_1031_KA1A-R315-RESULTS-...md``, owner-confirmed on the screen).  A
single unflagged boot cycled seven ids one per accepted hit and each hit
printed its own ``POSE_TRIAL sent=<id> hit=<n>`` line, so every screen
observation is paired to the id that produced it -- read live, from the
console, not reconstructed afterwards -- and each id came round three times:

    280 -> sword swing        284 -> mace swing       288 -> electric ball
    282 -> gunshot            290 -> green ball
    286 -> NOTHING            60029 (the echo) -> NOTHING

``SCREEN_CONFIRMED_BEHAVIOR_IDS`` is the first five.  ``286`` is measured, and
measured NEGATIVE, so it is exactly the case ``COO-DECISION 20260905_1153``
item 4 rules on: a value the id/pose pairing did not confirm stays
``[PROPOSED]`` and does not go to production.  It is not omitted quietly --
``PROPOSED_BEHAVIOR_IDS`` names it, ``production_behavior_for_class`` refuses
it out loud with the class it belongs to, and a test pins that the refusal is
about the SCREEN result and not about a missing table row.  Why 286 plays
nothing is not decided here (``COO-DECISION 20260905_1045`` item 4 records it
as debt, not a ticket): it could want a resource this character has not got,
or BEHAVIOR 286 could have no animation for this model.

WHERE THE CROSSWALK COMES FROM, now that it is derivable.  ``pose_trial.py``
carries the same six numbers typed by hand, under a comment that says in
capitals they "CANNOT BE RE-DERIVED INSIDE THIS REPOSITORY" and asks whoever
lands the tables to "replace this comment with a test that re-derives the six
rows".  One word of that was wrong: the tables are not in THIS repository,
but ``CONSTDATA_TH__EQUIP_VALUE.tsv`` has been sitting in
``pf_bridge/gamedata/tables/`` all along, which is where every other file in
``data/`` came from.  ``tools/pf_equip_attack_behavior_extract.py`` mines it,
this module loads the result, and ``tests/test_combat_pose.py`` re-derives
the six rows and kills the mutant pf-adversary measured surviving over there
(D3: 280 -> 281 left the suite green).  ``pose_trial.py``'s copy is left
where it is, still serving the attended sweep it was built for; this module
does not import it and does not delete it.

    class_id --(1)--> n_SLOT_RHAND --(2)--> EQUIPMENT_BASE row --(3)-->
    n_EQUIPTYPE --(4)--> n_ATTACK_SKILL == BEHAVIOR.n_ID

Legs (1)-(3) are the extractor's, checked three independent ways there (the
decoded row exists; it is one of the six character-creation rows and those
are the only six in a 974-row table; and its own ``n_CONDITION_CLASS``
bitmask carries the bit of the class that pointed at it).  Leg (4) is
``RE-110``'s crosswalk, chief [PROVEN] 2026-09-04 14:05.  The result agrees
with the class names from a fourth direction nobody arranged: Gladiator gets
the sword swing, Paladin the mace, Sniper the gunshot, Necromancer the
electric ball.

THE ONE THING THIS MODULE CANNOT DO BY ITSELF, stated plainly rather than
worked around.  It needs the performer's ``class_id`` and nothing hands it
one: ``runtime.py``'s call site (chief's file) passes ``legacy``, the parsed
fields, the performer identity and the hit count, and ``characters.class_id``
has a writer (``lifecycle.persist_class_id_from_starting_gear``) but no
reader.  So ``class_id`` arrives as ``None`` today, on every hit, and this
module answers exactly what ``COO-DECISION 20260905_1045`` item 2 says to
answer in that case: send nothing extra, keep the inherited 60029 echo, and
print ``POSE_NO_EQUIP_PROVENANCE``.  Nothing is guessed and 280 is not
hardcoded.  The two one-line hookups that close it are asked for in
``pf_bridge/notes_to_chief/20260905_13xx_LANE-B-CORE-REQUEST-*`` (one to
chief for the call site, one to LANE-DB for the read); the day either lands,
the swing appears with no further change here.

AND THE SEAM AFTER THAT.  "The class's starting right-hand weapon" is the
weapon the player is holding only for as long as nothing can swap it.  That
is true today -- there is no equipped-weapon column in ``migrations/`` and no
inventory equip path -- and it stops being true the moment one lands.  At
that point the right shape is an item-level read in FRONT of
``EQUIP_TYPE_BY_CLASS_ID``, resolving the equipped item to its own
``EQUIPMENT_BASE.n_EQUIPTYPE`` row and falling back to the class default;
``equip_type_for_class`` is deliberately a separate function from
``behavior_for_equip_type`` so that read has somewhere to go in.

FAIL-CLOSED, AND WHY THE WHOLE FILE IS.  Every entry point returns a value
and never raises: it runs inside ``state.dispatch()`` and the frozen
``game_listener`` around it has zero except handlers (interlock X07), so an
exception here kills the accept loop for every session, not one hit.  A
refusal always carries a console token naming the reason, because "no pose
appeared" and "no pose was attempted" are two different attended runs and an
absent line cannot tell them apart.
"""
import csv
import hashlib
from pathlib import Path

_DATA_DIR = Path(__file__).resolve().parent / "data"
_EQUIP_VALUE_PATH = _DATA_DIR / "equip_value_attack_behavior.tsv"
_CREATION_GEAR_PATH = _DATA_DIR / "creation_gear_by_class.tsv"

# sha256 of the two committed copies, checked at import so a hand-edit fails
# loudly instead of drifting.  A self-hash alone "keeps matching itself
# forever regardless of what pf_bridge does" (pf-adversary, round iazmrv), so
# tests/test_combat_pose.py re-runs the extractor against the live bridge
# clone under BRIDGE_GAMEDATA as the drift check that actually looks upstream.
EQUIP_VALUE_SHA256 = (
    "f954714c67ef7bc447b76e83eefcf4e309633719d89b4c18c2b6f971a12d86ca")
CREATION_GEAR_SHA256 = (
    "626e17d45e9581e064fcf03e93aa0e07667b194ce81ee7de1a037a184f8a99a4")


class CombatPoseError(RuntimeError):
    """Import-time refusal only.

    Raised while the module is being loaded (a drifted table copy), never from
    a request path -- see the module header on why nothing below the loaders
    may raise.
    """


def _load(path: Path, expected_sha: str) -> list:
    raw = path.read_bytes()
    actual = hashlib.sha256(raw).hexdigest()
    if actual != expected_sha:
        raise CombatPoseError(
            "%s sha256 mismatch: expected %s, got %s -- table drifted from "
            "the pinned client source, re-derive with "
            "tools/pf_equip_attack_behavior_extract.py before trusting this "
            "crosswalk" % (path.name, expected_sha, actual))
    with path.open("r", encoding="ascii", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


# ``n_EQUIPTYPE -> BEHAVIOR.n_ID`` for the kinds that swing.  The eleven rows
# whose ``n_ATTACK_SKILL`` is 0 (shield, armour, jewellery) are NOT in this
# dict: 0 is the table saying "this kind has no attack", and a lookup that
# returned 0 would be a selector this server would then put on the wire.
ATTACK_BEHAVIOR_BY_EQUIP_TYPE = {}
for _row in _load(_EQUIP_VALUE_PATH, EQUIP_VALUE_SHA256):
    _behavior = int(_row["n_ATTACK_SKILL"])
    if _behavior:
        ATTACK_BEHAVIOR_BY_EQUIP_TYPE[int(_row["n_EQUIPTYPE"])] = _behavior

# ``class_id -> n_EQUIPTYPE`` of that class's starting right-hand weapon.
EQUIP_TYPE_BY_CLASS_ID = {}
# ``class_id -> EQUIPMENT_BASE id``, kept for the console token so an attended
# reader can walk back to the row without the tool.
CREATION_GEAR_BASE_ID_BY_CLASS_ID = {}
for _row in _load(_CREATION_GEAR_PATH, CREATION_GEAR_SHA256):
    _class_id = int(_row["n_CLASS_ID"])
    EQUIP_TYPE_BY_CLASS_ID[_class_id] = int(_row["n_EQUIPTYPE"])
    CREATION_GEAR_BASE_ID_BY_CLASS_ID[_class_id] = int(
        _row["n_EQUIPMENT_BASE_ID"])

# GT-247 R315, owner-confirmed on the screen, each id paired live with its own
# ``POSE_TRIAL sent=<id> hit=<n>`` console line and repeated three times.
SCREEN_CONFIRMED_BEHAVIOR_IDS = frozenset({280, 284, 288, 282, 290})

# Measured on the same screen, in the same boot, and measured to play NOTHING.
# NOT "untested" -- that distinction is the whole point of keeping it here
# rather than leaving it out of the confirmed set silently.
PROPOSED_BEHAVIOR_IDS = frozenset({286})

# The id the inherited v141 dispatch already echoes back on its own, measured
# to play no animation (GT-247 R315 hits 1/8/15).  Named so the refusal below
# can say "this is the thing we are trying to stop sending" instead of a bare
# number.
INHERITED_ECHO_SELECTOR = 60029

# Console tokens.  ASCII, no spaces inside a token, greppable off a cp874
# console -- the same discipline every other console token in this lane has.
POSE_PRODUCTION = "POSE_PRODUCTION"
POSE_NO_EQUIP_PROVENANCE = "POSE_NO_EQUIP_PROVENANCE"
POSE_REFUSED = "POSE_REFUSED"

REASON_NO_CLASS_ID = "no_class_id"
REASON_CLASS_NOT_IN_CREATION_GEAR = "class_not_in_creation_gear"
REASON_KIND_HAS_NO_ATTACK_SKILL = "kind_has_no_attack_skill"
REASON_BEHAVIOR_NOT_SCREEN_CONFIRMED = "behavior_not_screen_confirmed"


def equip_type_for_class(class_id):
    """The ``n_EQUIPTYPE`` of ``class_id``'s starting right hand, or ``None``.

    ``None`` for a ``class_id`` that is not one of the five selectable
    classes -- including ``None`` itself, which is what an unresolved
    ``characters.class_id`` looks like.  Never raises: a non-integer reaches
    the dict lookup as a plain miss.

    THE SEAM (module header): when an equipped-item read lands, it goes in
    FRONT of this function, not inside it.  This one answers "what does this
    class start with", which stays true whatever the player later equips.
    """
    try:
        return EQUIP_TYPE_BY_CLASS_ID.get(class_id)
    except TypeError:
        # An unhashable class_id (a list, a dict) -- a caller bug, but not one
        # worth killing the accept loop over.
        return None


def behavior_for_equip_type(equip_type):
    """The BEHAVIOR id ``equip_type`` swings with, or ``None``.

    ``None`` for the eleven kinds whose ``n_ATTACK_SKILL`` is 0 (the table's
    own "does not swing"), and for any type not in the table at all.
    """
    try:
        return ATTACK_BEHAVIOR_BY_EQUIP_TYPE.get(equip_type)
    except TypeError:
        return None


def is_screen_confirmed(behavior_id):
    """True only for an id an owner watched produce an animation.

    ``COO-DECISION 20260905_1153`` item 4: production may carry only the
    values the id/pose pairing confirmed; everything else is ``[PROPOSED]``.
    """
    return behavior_id in SCREEN_CONFIRMED_BEHAVIOR_IDS


def production_behavior_for_class(class_id):
    """``(behavior_id_or_None, console_line)`` for one accepted hit.

    ``behavior_id`` is ``None`` on every refusal, and a ``None`` here means
    the caller composes and sends NOTHING extra -- the inherited v141 echo of
    the request's own ``+0x30`` is what reaches the client, exactly as it does
    on main today.  The console line is never ``None``: a run that produced no
    swing must be able to say which of the four reasons it was.

    NEVER RAISES (module header, interlock X07).
    """
    if class_id is None:
        return (None, "%s reason=%s" % (
            POSE_NO_EQUIP_PROVENANCE, REASON_NO_CLASS_ID))
    equip_type = equip_type_for_class(class_id)
    if equip_type is None:
        return (None, "%s reason=%s class=%s" % (
            POSE_NO_EQUIP_PROVENANCE, REASON_CLASS_NOT_IN_CREATION_GEAR,
            _token(class_id)))
    behavior_id = behavior_for_equip_type(equip_type)
    if behavior_id is None:
        # Unreachable from the five classes shipped today -- every one of
        # their starting right hands swings.  Kept because the guard is what
        # makes "a class whose starting gear is a shield" a refusal with a
        # reason instead of a ``None`` selector on the wire.
        return (None, "%s reason=%s class=%s equip_type=%d" % (
            POSE_REFUSED, REASON_KIND_HAS_NO_ATTACK_SKILL,
            _token(class_id), equip_type))
    if not is_screen_confirmed(behavior_id):
        return (None, "%s reason=%s class=%s equip_type=%d behavior=%d" % (
            POSE_REFUSED, REASON_BEHAVIOR_NOT_SCREEN_CONFIRMED,
            _token(class_id), equip_type, behavior_id))
    return (behavior_id, "%s class=%s equip_type=%d base=%d behavior=%d" % (
        POSE_PRODUCTION, _token(class_id), equip_type,
        CREATION_GEAR_BASE_ID_BY_CLASS_ID[class_id], behavior_id))


def _token(class_id):
    """``class_id`` rendered for a cp874 console, and never a raised encode.

    An integer prints as itself.  Anything else -- a caller handing this
    module a decoded field it did not check -- is reported by TYPE NAME, never
    by value: this repository has written the same rule down three times from
    measurement, because a value can carry a non-cp874 byte and raise
    ``UnicodeEncodeError`` inside the very print that was reporting it.
    """
    if isinstance(class_id, int) and not isinstance(class_id, bool):
        return str(class_id)
    return "<%s>" % type(class_id).__name__
