"""LANE-Q: the message-wire seam three Lua API names share.

WHAT A SCRIPT ACTUALLY SAYS WHEN IT "SHOWS A MESSAGE"
-----------------------------------------------------
The shipped corpus never hands a string to any of the three message names.
It hands an INTEGER, and that integer is a row id in the game's own
message table.  Derived, not guessed:

  * ``pf_bridge/gamedata/tables/TEXTDATA_TH__MESSAGE.tsv`` -- columns
    ``n_ID  n_TYPE  n_NOTIFY_TYPE  s_MESSAGE``, 907 rows, ids 1..961 with
    gaps.
  * Every literal id passed at a ``Player.ShowMessage`` /
    ``Trigger.TriggerShowMessage`` / ``Party.ShowMessage`` call site in
    all 616 files exists as a row there: ``1, 4, 421, 824, 855, 856, 859,
    860, 882, 885, 890, 897`` (Player) and ``914..921`` (Trigger).  Zero
    misses.
  * The MEANING agrees at every site that has surrounding logic to check.
    ``856`` = "quest not accepted, or quest state does not match" and it
    is passed right where a quest script bails out on a state check;
    ``855`` = "item count is already at the cap"; ``859`` = "not enough of
    the related item"; ``914..921`` are arena-announcer broadcast lines
    and every one of them is passed from a ``t_*_msg`` trigger.
  * The competing candidates were checked rather than assumed away.
    ``TEXTDATA_TH__TIP_MESSAGE.tsv`` stops at id 561 and is REFUTED: 17 of
    the 20 literal ids have no row there at all.
    ``TEXTDATA_TH__UI_MESSAGE.tsv`` covers every id by range and so is not
    refuted by coverage -- it is refuted by CONTENT: its 855/856/859 are
    the UI labels "skill details" / "up status" / "skill points:", which
    are not something a quest bails out with.

WHAT IS DELIBERATELY NOT VENDORED HERE
--------------------------------------
:data:`CATALOG` carries ``message_id``/``message_type``/``notify_type``
and NOT the localized ``s_MESSAGE`` text, the same split
``lua_api/api_spec.tsv`` already took for its own source table (it vendors
the shape and leaves the bridge repository's own columns in the bridge).
This lane needs the id space to VALIDATE what a script passes; it does not
build a frame and so never needs the text.

That is a real limit, not a tidy one, and it is named here rather than
discovered later: whoever finally emits the frame needs the text, and the
text lives in the bridge table above (or in the frozen legacy seam's own
``make_show_message(text)``, ``current/pf_login_game_server_v141.py``,
which already builds ``ShowMessageVital`` 0x36D2 -- proven layout in
``pf_bridge/external/PF_SERIALIZER_FIELDS.tsv``, one
UNTAGGED_WSTRING16LE_LEN32LE at +0x14).  This module hands that future
caller an ordered, per-character record of WHICH ids to show, in the order
the scripts asked for them.  It does not send anything, and no module in
this package constructs that vital.

AUDIENCE
--------
``Trigger.TriggerShowMessage(audience, message_id)`` takes an audience as
its first argument.  The meaning is the corpus's own, from
``gamedata/lua/t_msg_mod.lua``'s Big5 header comment ("Var2 = message type
(1 individual, 2 party, 3 scene, 4 channel)") read together with that same
file's if-chain, which maps ``Var2 == 1 -> TriggerShowMessage(0, ...)``,
``== 2 -> 1``, ``== 3 -> 2``, ``== 4 -> 3``.  So the wire value is the
comment's own number minus one: 0 individual, 1 party, 2 scene, 3 channel.

``Player.ShowMessage``/``Party.ShowMessage`` take no audience -- their
namespace IS the audience, so they record :data:`AUDIENCE_INDIVIDUAL` and
(when Party goes real, one call site, not this round)
:data:`AUDIENCE_PARTY`.

MULTIPLAYER POSTURE (AGENTS.md section 7, first line; PROCESS_GATES section 25)
-------------------------------------------------------------------------------
An audience is not decoration -- it decides WHO the record belongs to, so
the sink is keyed accordingly rather than filing everything under the
character whose script happened to fire the trigger:

  * ``AUDIENCE_INDIVIDUAL`` / ``AUDIENCE_PARTY`` -> the CHARACTER's own
    bucket.  A party message is still filed under the character who
    triggered it, tagged ``AUDIENCE_PARTY``, because fanning it out to the
    rest of the party needs a party registry this lane does not own; the
    entry names the originating character so a future dispatcher can
    expand it.  That is a NAMED gap, not a silent one.
  * ``AUDIENCE_SCENE`` / ``AUDIENCE_CHANNEL`` -> the SCENE's own bucket,
    read back with :meth:`broadcasts_for`.  This is the half that a
    character key gets WRONG: ``t_bg2017_msg.lua``'s arena announcements
    (``TriggerShowMessage(2, 918)`` -- "the champion enters!") are meant
    for everyone in that scene, and filing them under one character means
    the second player in the same scene never has them.  The precedent is
    in this same package: ``lua_api.trigger.TriggerStatusRegistry`` keys by
    ``(scene, trigger_id)`` and cites `PANYA-DECISION 20260905_1057`
    ("shared by every session in a scene") for doing so.

Caps are per bucket -- one looping script fills its own character's or its
own scene's bucket and nobody else's -- and a refused write returns 0
rather than the current length, so a caller can always tell a dropped
message from a stored one.

Still NOT solved here, said plainly: nothing delivers any of this to a
client, and a scene bucket is a record of intent, not a broadcast.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Optional, Protocol, Tuple

#: 0 individual, 1 party, 2 scene, 3 channel -- see the module docstring's
#: AUDIENCE section for the derivation.  Named constants rather than bare
#: integers so a call site that means "scene" cannot be read as "2 (why?)".
AUDIENCE_INDIVIDUAL = 0
AUDIENCE_PARTY = 1
AUDIENCE_SCENE = 2
AUDIENCE_CHANNEL = 3

#: The complete audience domain.  The corpus only ever passes a literal 2
#: (``t_bg2017_msg.lua`` and friends); 0/1/3 arrive through
#: ``Trigger.Var2``-driven branches in ``t_msg_mod.lua``/``t_msg_modc.lua``,
#: which is where the 0..3 domain comes from -- an audience outside this
#: set is refused, not clamped.
AUDIENCES = frozenset({
    AUDIENCE_INDIVIDUAL, AUDIENCE_PARTY, AUDIENCE_SCENE, AUDIENCE_CHANNEL,
})

_AUDIENCE_NAMES = {
    AUDIENCE_INDIVIDUAL: "individual",
    AUDIENCE_PARTY: "party",
    AUDIENCE_SCENE: "scene",
    AUDIENCE_CHANNEL: "channel",
}

_CATALOG_PATH = Path(__file__).with_name("message_catalog.tsv")


def audience_name(audience: int) -> str:
    """A log-safe ASCII name for an audience number, ``"?"`` if unknown."""
    return _AUDIENCE_NAMES.get(audience, "?")


def _load_catalog(path: Path = _CATALOG_PATH):
    rows = {}
    with path.open(encoding="ascii", newline="") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            rows[int(row["message_id"])] = (
                int(row["message_type"]), int(row["notify_type"]))
    return rows


#: ``message_id -> (message_type, notify_type)``, the frozen ASCII half of
#: ``TEXTDATA_TH__MESSAGE.tsv`` (see the module docstring).  907 rows.
CATALOG = _load_catalog()

#: The largest id in the shipped table.  Used as the coercion ceiling so a
#: script that passes a wild number is refused at the door rather than
#: reaching the catalog lookup with a 4-billion-element intent.
MAX_MESSAGE_ID = max(CATALOG)


def is_known_message_id(message_id: int) -> bool:
    """Does the shipped table actually have this row?

    A miss is NOT a crash and NOT a silent pass: the caller logs a
    bad-value line and refuses, because a message id with no row is a
    message the client could never render.
    """
    return message_id in CATALOG


def notify_type(message_id: int) -> Optional[int]:
    """``n_NOTIFY_TYPE`` for a known id, ``None`` for an unknown one."""
    row = CATALOG.get(message_id)
    return None if row is None else row[1]


class MessageSink(Protocol):
    """The seam ``build_namespace``'s ``sink`` parameter names.

    Same contract every other store in this package states for itself:
    every method takes already-COERCED plain ints -- the calling closure
    validates whatever a script handed in before it ever reaches a sink,
    so a sink implementation never sees an unvalidated Lua value.
    """

    def record(self, scene: Optional[str], character_id: int, audience: int,
               message_id: int) -> int:
        """File one shown message under whichever bucket its AUDIENCE
        names (see the module docstring's MULTIPLAYER POSTURE section).

        Returns how many records that bucket now holds, read back after
        the write -- or ``0`` when the write was REFUSED by a cap, which is
        what makes a dropped message distinguishable from a stored one.
        """
        ...

    def messages_for(self, character_id: int) -> Tuple[Tuple[int, int], ...]:
        """``((audience, message_id), ...)`` addressed to this character,
        in the order recorded."""
        ...

    def broadcasts_for(self, scene: str) -> Tuple[Tuple[int, int, int], ...]:
        """``((audience, message_id, from_character_id), ...)`` addressed
        to everyone in this scene, in the order recorded."""
        ...


#: Per-bucket bounds, same shape/reasoning as ``lua_api.quest``'s own caps:
#: a bound a looping script cannot grow past, refused by name rather than
#: silently evicted.
CHARACTERS_CAP = 4096
MESSAGES_PER_CHARACTER_CAP = 1024
SCENES_CAP = 512
MESSAGES_PER_SCENE_CAP = 1024

#: The two audiences that belong to a SCENE rather than to the character
#: whose script fired the trigger.
BROADCAST_AUDIENCES = frozenset({AUDIENCE_SCENE, AUDIENCE_CHANNEL})


class InMemoryMessageSink:
    """The default :class:`MessageSink` when no real one is injected.

    PROCESS MEMORY, an inert bucket for tests and spikes -- the same role
    ``lua_api.quest.InMemoryQuestStateStore`` plays for quest state.  It is
    explicitly NOT the answer to "what does the player see": nothing here
    sends a frame.  Never raises on anything a script's own arguments could
    reach; a non-positive cap is a caller-programming error and does raise
    ``ValueError``, the same distinction every other in-package store
    documents for itself.
    """

    def __init__(self, characters: int = CHARACTERS_CAP,
                 messages_per_character: int = MESSAGES_PER_CHARACTER_CAP,
                 scenes: int = SCENES_CAP,
                 messages_per_scene: int = MESSAGES_PER_SCENE_CAP) -> None:
        for name, value in (("characters", characters),
                            ("messages_per_character", messages_per_character),
                            ("scenes", scenes),
                            ("messages_per_scene", messages_per_scene)):
            if type(value) is bool or not isinstance(value, int) or value < 1:
                raise ValueError("%s must be a positive int" % name)
        self._characters_cap = characters
        self._messages_cap = messages_per_character
        self._scenes_cap = scenes
        self._scene_messages_cap = messages_per_scene
        self._shown: dict = {}
        self._broadcast: dict = {}

    @staticmethod
    def _append(buckets: dict, key, buckets_cap: int, entries_cap: int,
                entry) -> int:
        rows = buckets.get(key)
        if rows is None:
            if len(buckets) >= buckets_cap:
                return 0
            rows = buckets.setdefault(key, [])
        if len(rows) >= entries_cap:
            return 0
        rows.append(entry)
        return len(rows)

    def record(self, scene: Optional[str], character_id: int, audience: int,
               message_id: int) -> int:
        if audience in BROADCAST_AUDIENCES:
            if not scene:
                # A scene-wide message with no scene to file it under is not
                # a message anyone could ever be shown -- refused, not
                # quietly downgraded into the triggering character's bucket
                # (that downgrade is exactly the defect this shape fixes).
                return 0
            return self._append(
                self._broadcast, scene, self._scenes_cap,
                self._scene_messages_cap, (audience, message_id, character_id))
        return self._append(
            self._shown, character_id, self._characters_cap,
            self._messages_cap, (audience, message_id))

    def messages_for(self, character_id: int) -> Tuple[Tuple[int, int], ...]:
        return tuple(self._shown.get(character_id, ()))

    def broadcasts_for(self, scene: str) -> Tuple[Tuple[int, int, int], ...]:
        return tuple(self._broadcast.get(scene, ()))
