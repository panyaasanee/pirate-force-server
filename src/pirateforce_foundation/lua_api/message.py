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

MULTIPLAYER POSTURE (AGENTS.md section 7, first line)
-----------------------------------------------------
:class:`InMemoryMessageSink` is keyed by ``character_id`` FIRST and caps
per character, so one script looping on one character can fill that
character's own bucket and no one else's.  The character cap refuses new
characters by name rather than evicting an existing player's records.
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

    def record(self, character_id: int, audience: int, message_id: int) -> int:
        """Record one shown message; returns how many are now on record for
        this character (read back after the write, never a bare echo)."""
        ...

    def messages_for(self, character_id: int) -> Tuple[Tuple[int, int], ...]:
        """``((audience, message_id), ...)`` in the order recorded."""
        ...


#: Per-sink bounds, same shape/reasoning as ``lua_api.quest``'s own caps: a
#: bound a looping script cannot grow past, refused by name rather than
#: silently evicted.
CHARACTERS_CAP = 4096
MESSAGES_PER_CHARACTER_CAP = 1024


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
                 messages_per_character: int = MESSAGES_PER_CHARACTER_CAP) -> None:
        for name, value in (("characters", characters),
                            ("messages_per_character", messages_per_character)):
            if type(value) is bool or not isinstance(value, int) or value < 1:
                raise ValueError("%s must be a positive int" % name)
        self._characters_cap = characters
        self._messages_cap = messages_per_character
        self._shown: dict = {}

    def record(self, character_id: int, audience: int, message_id: int) -> int:
        rows = self._shown.get(character_id)
        if rows is None:
            if len(self._shown) >= self._characters_cap:
                return 0
            rows = self._shown.setdefault(character_id, [])
        if len(rows) >= self._messages_cap:
            return len(rows)
        rows.append((audience, message_id))
        return len(rows)

    def messages_for(self, character_id: int) -> Tuple[Tuple[int, int], ...]:
        return tuple(self._shown.get(character_id, ()))
