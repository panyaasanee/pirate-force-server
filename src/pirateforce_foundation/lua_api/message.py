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

VENDORING: THE WHOLE ROW, ASCII-SAFE (COO-DECISION 2026-09-07T04:05)
--------------------------------------------------------------------
``message_catalog.tsv`` is a COMPLETE MIRROR of that table -- all four
columns, ``s_MESSAGE`` included, with every character outside printable
ASCII written as ``\\uXXXX`` so the file itself is pure ASCII on disk.

The previous shape vendored only the two integer columns and told
whoever finally emits the frame to go read the bridge table for the text.
COO ruled against that (letter ``20260907_0322`` from this lane, answered
``20260907_0405``, option (a)): every lane that wires a frame would then
need its own sibling checkout or its own second copy, which is drift with
a schedule.  The text is kept where it is used; the cost of undoing that
is one regenerate command.

The escape is not decoration either.  The bridge console is cp874 and the
Windows gate has already burned two rounds on encoding (#961, #967), so a
vendored file that is ASCII BY CONSTRUCTION cannot reintroduce that class
of failure.  :func:`escape_message_text` / :func:`unescape_message_text`
are the only encoder/decoder pair, and ``tools/pf_regen_lua_message_catalog.py``
imports the encoder rather than copying it.

Three obligations came attached to the permission, and all three are met
here rather than promised: the file carries a provenance header (source
path, source sha256, row count, pull date); a regenerate script lives in
the repository (``--check`` exits non-zero on drift); and the tie to the
source table is a test, ``test_script_lua_api_message.py``'s
``VendoredCatalogMatchesTheRealTableTests``, guarded by BRIDGE_GAMEDATA so
it needs the bridge's tables directory and nothing else -- notably not
lupa, which the previous home for that test also required for no reason.

The one thing the text must never do is reach a terminal.
:func:`message_text` returns the localized Thai string for the eventual
frame builder, which writes it into a UTF-16LE payload; no log line in
this package interpolates it, and a test pins that.

Still true, and still named: this module builds no frame.  The frame
builder that exists is the frozen legacy seam's ``make_show_message(text)``
in ``current/pf_login_game_server_v141.py`` -- the show-message vital, id
``0x36D2``, proven layout in ``pf_bridge/external/PF_SERIALIZER_FIELDS.tsv``,
one UNTAGGED_WSTRING16LE_LEN32LE at +0x14 -- and the dispatch that would call it
lives in ``runtime.py``/``app.py``, outside this lane's write scope.  What
this module hands that future caller is an ordered, per-audience record of
WHICH ids to show -- and now the text to show for each of them.

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

# THE HANDOFF NAME, IN A COMMENT ON PURPOSE (round 7kxfe9).  The vital this
# module deliberately does NOT build is called ShowMessageVital, and a
# future reader should be able to grep that spelling and land here.  It sits
# in a full-line comment rather than in the docstring above because
# tools/pf_ui_wire_name_census.py grades a name SOURCE ("appears in the
# code") when its identifier is on any NON-COMMENT line under
# src/pirateforce_foundation/, and it skips full-line comments precisely to
# avoid that false positive -- but not docstring bodies, a gap its own
# module docstring discloses.  Round 6775u1 spelled the name in the
# docstring, which flipped that row NAME-ONLY -> SOURCE, put the project
# count at 161 against a pinned 160, and left main RED in a module belonging
# to another lane (measured on a pristine origin/main worktree, round
# 7kxfe9).  Naming it in prose was never ownership -- this file's own
# NoLaneQModuleBuildsTheVitalTests walks the AST and proves no code here
# reaches for it -- so the fix belongs on this side of the line, and the
# tool's gap is reported to its owner rather than worked around silently.

from __future__ import annotations

import csv
import re
import threading
from pathlib import Path
from typing import Dict, Mapping, Optional, Protocol, Tuple

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


#: The four columns of the vendored mirror, in file order.
CATALOG_COLUMNS = ("message_id", "message_type", "notify_type", "message_text")

#: A vendored row's text column holds ONLY printable ASCII; every other
#: character -- and the backslash itself -- is written as ``\uXXXX``.  That
#: makes the escape unambiguous in the one direction that matters: a
#: backslash in a vendored line is ALWAYS the start of an escape, never a
#: literal, so decoding is a single substitution with no lookahead rules.
_ESCAPE_RE = re.compile(r"\\u([0-9a-f]{4})")
_KEEP_LITERAL = frozenset(
    chr(code) for code in range(0x20, 0x7F) if chr(code) != "\\")


class MessageCatalogError(RuntimeError):
    """The vendored catalog could not be read.

    Raised LOUDLY and by name, with the path in the message.  The previous
    shape loaded the file at import time under ``encoding="ascii"``, so one
    stray byte or a missing file turned into an ImportError halfway up the
    package -- which, because ``lua_api/__init__`` is what installs the
    namespace hooks, made every Lua API name in this package vanish with no
    line saying why.  A named error at first USE is the fix (pf-adversary
    D5, round 6775u1).
    """


def escape_message_text(text: str) -> str:
    """One line of localized text -> pure ASCII, ``\\uXXXX`` for the rest.

    The inverse of :func:`unescape_message_text`, and the ONLY encoder --
    ``tools/pf_regen_lua_message_catalog.py`` imports this rather than
    keeping a second copy that could drift from the decoder that reads it.
    """
    out = []
    for ch in text:
        if ch in _KEEP_LITERAL:
            out.append(ch)
            continue
        code = ord(ch)
        if code > 0xFFFF:
            # pf-adversary D2, round 7kxfe9: "\\u%04x" % 0x1F3C6 renders
            # "\\u1f3c6", which the 4-hex-digit decoder reads as U+1F3C + a
            # literal "6".  It round-tripped through the ENCODER's own tests
            # (they re-encode what they just decoded) and through --check
            # (both sides share this function), so the corruption was
            # invisible on every machine without the source table.  The
            # shipped table is all-BMP today, measured; the day it is not,
            # this raises instead of silently rewriting a message.
            raise ValueError(
                "message text contains a non-BMP character U+%04X, which "
                "this 4-hex-digit escape cannot represent: widen the format "
                "before regenerating" % code)
        out.append("\\u%04x" % code)
    return "".join(out)


def unescape_message_text(escaped: str) -> str:
    """``\\uXXXX`` back to the real characters.  Inverse of the above."""
    return _ESCAPE_RE.sub(lambda m: chr(int(m.group(1), 16)), escaped)


#: The header line that carries a digest of the file's OWN body.
BODY_DIGEST_PREFIX = "# body_sha256: "


def body_digest(text: str) -> str:
    """sha256 of everything in the vendored file that is not a ``#`` line.

    pf-adversary D1/D3/D4/D5 (round 7kxfe9) all share one shape: the tie
    that proves the vendored copy is honest needs the SOURCE table, and the
    Windows gate -- the machine that decides whether a PR merges -- has no
    bridge checkout at all (``.github/workflows/gate-windows.yml`` does not
    fetch one).  So every row of the text column could be replaced with the
    same string, or a hand-edit could strip the trailing space eight rows
    depend on, and the gate stayed green.

    A digest of the file's own body needs nothing but the file, so the test
    that checks it runs EVERYWHERE, including there.  It does not prove the
    copy matches the source -- only the source-digest test can do that --
    it proves nobody has edited the copy since it was generated, which is
    the half that was unguarded on the machine that matters.
    """
    import hashlib

    body = "".join(line + "\n" for line in text.splitlines()
                   if not line.startswith("#"))
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def _read_catalog(path: Path) -> Dict[int, Tuple[int, int, str]]:
    rows: Dict[int, Tuple[int, int, str]] = {}
    with path.open(encoding="ascii", newline="") as handle:
        # The provenance header is '#'-prefixed and is stripped BEFORE csv
        # sees the stream: csv has no comment syntax, so a header line would
        # otherwise arrive as a data row whose message_id is '# source ...'.
        body = [line for line in handle if not line.startswith("#")]
    reader = csv.DictReader(body, delimiter="\t")
    for line_number, row in enumerate(reader, start=2):
        # pf-adversary D3, round 7kxfe9: a hand-inserted TAB inside a text
        # cell makes csv split that row into FIVE fields, and DictReader
        # files the surplus under restkey and hands back a silently
        # TRUNCATED message -- with the row count, and therefore the header
        # check, still agreeing.  A row that is not exactly four fields is
        # an error here rather than a shorter message later.
        if row.get(None) is not None or any(
                row.get(column) is None for column in CATALOG_COLUMNS):
            raise MessageCatalogError(
                "%s line %d does not have exactly %d fields"
                % (path, line_number, len(CATALOG_COLUMNS)))
        rows[int(row["message_id"])] = (
            int(row["message_type"]),
            int(row["notify_type"]),
            unescape_message_text(row["message_text"]),
        )
    if not rows:
        raise MessageCatalogError("%s has no rows" % path)
    return rows


_CATALOG_LOCK = threading.RLock()
_CATALOG_CACHE: Optional[Dict[int, Tuple[int, int, str]]] = None


def catalog() -> Mapping[int, Tuple[int, int, str]]:
    """``message_id -> (message_type, notify_type, text)``, 907 rows.

    LAZY and cached: read on first use, not at import.  Any failure raises
    :class:`MessageCatalogError` naming the path -- never a silent partial
    read and never an ImportError that takes the namespace hooks with it.
    """
    global _CATALOG_CACHE
    with _CATALOG_LOCK:
        if _CATALOG_CACHE is None:
            try:
                _CATALOG_CACHE = _read_catalog(_CATALOG_PATH)
            except MessageCatalogError:
                raise
            except Exception as exc:  # noqa: BLE001 - re-raised by name
                raise MessageCatalogError(
                    "cannot read the vendored message catalog %s: %r"
                    % (_CATALOG_PATH, exc)) from exc
        return _CATALOG_CACHE


def max_message_id() -> int:
    """The largest id in the shipped table.

    The coercion ceiling the two closures pass to ``_coerce_int``, so a
    script that passes a wild number is refused at the door rather than
    reaching a lookup with a four-billion-element intent.  A FUNCTION, not
    a module constant: a constant would have to be computed at import,
    which is exactly the eager load this round removed.
    """
    return max(catalog())


def is_known_message_id(message_id: int) -> bool:
    """Does the shipped table actually have this row?

    A miss is NOT a crash and NOT a silent pass: the caller logs a
    bad-value line and refuses, because a message id with no row is a
    message the client could never render.
    """
    return message_id in catalog()


def notify_type(message_id: int) -> Optional[int]:
    """``n_NOTIFY_TYPE`` for a known id, ``None`` for an unknown one."""
    row = catalog().get(message_id)
    return None if row is None else row[1]


def message_type(message_id: int) -> Optional[int]:
    """``n_TYPE`` for a known id, ``None`` for an unknown one."""
    row = catalog().get(message_id)
    return None if row is None else row[0]


def message_text(message_id: int) -> Optional[str]:
    """``s_MESSAGE`` for a known id, ``None`` for an unknown one.

    NOT ASCII -- this is the localized Thai string the client renders.  It
    must never reach a log line or anything else printed to the bridge
    console (cp874, see the module docstring's VENDORING section); it
    exists for the eventual frame builder, which writes it into a
    UTF-16LE payload rather than to a terminal.
    """
    row = catalog().get(message_id)
    return None if row is None else row[2]


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

    def record_refusal(self, reason: str) -> int:
        """Count one message a closure REFUSED before it ever got here.

        pf-adversary D12 (round 6775u1): 51 of the 116 corpus call sites
        pass ``Trigger.VarN`` rather than a literal, and the ids in those
        ``.tgr`` tables are still unmined -- so an id landing in one of the
        table's 54 gaps is an expected, recurring event, and it was leaving
        exactly one log line behind and nothing countable.  A run can now
        answer "how many did we drop, and for which reason" without
        grepping its own log.  Returns the new count for that reason.
        """
        ...

    def refusals(self) -> Tuple[Tuple[str, int], ...]:
        """``((reason, count), ...)`` sorted by reason, empty on a clean run.

        pf-adversary D7 (round 7kxfe9): ``record_refusal`` was on this
        protocol but the READER of what it counts was not, so a sink could
        satisfy every check there was and still have no way to answer the
        one question the counter exists to answer.  A write-only counter is
        not a counter, so the reader is part of the contract.
        """
        ...


#: Every method a sink handed to ``build_namespace`` must have.  ``refusals``
#: joined this tuple in round 02mkqc (pf-adversary D7): a counter nobody can
#: read is indistinguishable from no counter at all.
SINK_METHODS = ("record", "record_refusal", "refusals", "messages_for",
                "broadcasts_for")


def check_sink(sink):
    """Raise a NAMED TypeError at INJECTION time for an incomplete sink.

    pf-adversary D6, round 7kxfe9.  ``record_refusal`` was added to the
    :class:`MessageSink` protocol this round, and a sink written against
    last round's protocol still satisfied every check there was -- until a
    script refused a message, at which point an ``AttributeError`` came out
    of the middle of a Lua call.  That is not a rare path: 51 of the 116
    corpus call sites pass an unmined ``Trigger.VarN``, the harness supplies
    ``STUB_DEFAULT`` = 0 for those, and 0 has no row, so the refusal path is
    the one a corpus sweep takes constantly.

    A ``Protocol`` is a static promise; nothing checks it at runtime.  This
    is that check, placed where the caller can act on it (the injection)
    rather than where a script trips over it, and it names the missing
    method instead of the attribute lookup that failed.
    """
    missing = [name for name in SINK_METHODS if not callable(
        getattr(sink, name, None))]
    if missing:
        raise TypeError(
            "%s is not a MessageSink: missing %s"
            % (type(sink).__name__, ", ".join(missing)))
    return sink


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

#: Why a message never reached a bucket.  Named strings rather than free
#: text so a count is groupable and a typo cannot invent a new reason.
REFUSE_BAD_ARITY = "bad_arity"
REFUSE_UNKNOWN_MESSAGE_ID = "unknown_message_id"
REFUSE_BAD_AUDIENCE = "bad_audience"
REFUSE_NO_SCENE = "no_scene"
REFUSE_BUCKET_FULL = "bucket_full"
REFUSE_TOO_MANY_BUCKETS = "too_many_buckets"

#: The one bucket every reason OUTSIDE the declared set is counted under.
#: pf-adversary D7 (round 7kxfe9): ``record_refusal`` took whatever string a
#: caller handed it and gave it its own dict key, so a caller that built a
#: reason out of runtime data (an id, a scene name) grew the dict without
#: bound -- in the one code path a corpus sweep takes constantly (51 of the
#: 116 call sites pass an unmined ``Trigger.VarN``).  Counting it here
#: instead is NOT a silent drop: the count still rises, and it rises under a
#: name that says exactly what happened -- somebody invented a reason.  What
#: is lost is only the invented string, which by
#: ``test_every_reason_a_closure_can_raise_is_in_the_declared_set`` no
#: closure in this package ever produces.
REFUSE_OTHER = "other"

REFUSAL_REASONS = frozenset({
    REFUSE_BAD_ARITY, REFUSE_UNKNOWN_MESSAGE_ID, REFUSE_BAD_AUDIENCE,
    REFUSE_NO_SCENE, REFUSE_BUCKET_FULL, REFUSE_TOO_MANY_BUCKETS,
})

#: Hard ceiling on how many distinct keys :meth:`InMemoryMessageSink.refusals`
#: can ever return -- the declared reasons plus :data:`REFUSE_OTHER`.  A
#: number, not a promise: pinned by a test that feeds the sink a thousand
#: made-up reasons and reads the width back.
MAX_REFUSAL_KEYS = len(REFUSAL_REASONS) + 1


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
        self._refusals: dict = {}
        # Same guard, for the same reason, as the two sibling stores in this
        # package (``lua_api.quest.InMemoryQuestStateStore``,
        # ``lua_api.trigger.TriggerStatusRegistry``): one world per scene is
        # shared by every session in the process (AGENTS.md section 7, first
        # line), so two sessions CAN reach one sink at once, and
        # read-then-append is not atomic on its own.  RLock rather than Lock
        # because ``record`` calls ``_append``, which takes it too.
        self._lock = threading.RLock()

    def _append(self, buckets: dict, key, buckets_cap: int, entries_cap: int,
                entry) -> int:
        with self._lock:
            rows = buckets.get(key)
            if rows is None:
                if len(buckets) >= buckets_cap:
                    self._count(REFUSE_TOO_MANY_BUCKETS)
                    return 0
                rows = buckets.setdefault(key, [])
            if len(rows) >= entries_cap:
                self._count(REFUSE_BUCKET_FULL)
                return 0
            rows.append(entry)
            return len(rows)

    def _count(self, reason: str) -> int:
        # An undeclared reason is COUNTED, under REFUSE_OTHER, never given a
        # key of its own: the dict is bounded by MAX_REFUSAL_KEYS no matter
        # what a caller passes.  See REFUSE_OTHER's own comment for why this
        # is a ceiling rather than a drop.
        key = reason if reason in REFUSAL_REASONS else REFUSE_OTHER
        with self._lock:
            self._refusals[key] = self._refusals.get(key, 0) + 1
            return self._refusals[key]

    def record(self, scene: Optional[str], character_id: int, audience: int,
               message_id: int) -> int:
        if audience in BROADCAST_AUDIENCES:
            if not scene:
                # A scene-wide message with no scene to file it under is not
                # a message anyone could ever be shown -- refused, not
                # quietly downgraded into the triggering character's bucket
                # (that downgrade is exactly the defect this shape fixes).
                self._count(REFUSE_NO_SCENE)
                return 0
            return self._append(
                self._broadcast, scene, self._scenes_cap,
                self._scene_messages_cap, (audience, message_id, character_id))
        return self._append(
            self._shown, character_id, self._characters_cap,
            self._messages_cap, (audience, message_id))

    def record_refusal(self, reason: str) -> int:
        """See :meth:`MessageSink.record_refusal`.

        An unrecognised reason is counted under :data:`REFUSE_OTHER` rather
        than dropped AND rather than given a key of its own: a counter that
        silently swallows what it does not recognise is the defect this
        counter exists to fix, and a counter a caller can grow without
        bound is the defect pf-adversary D7 found in the fix.
        """
        return self._count(reason)

    def refusals(self) -> Tuple[Tuple[str, int], ...]:
        """``((reason, count), ...)`` sorted by reason.  Empty when nothing
        was refused, which is the state a healthy run ends in."""
        with self._lock:
            return tuple(sorted(self._refusals.items()))

    def messages_for(self, character_id: int) -> Tuple[Tuple[int, int], ...]:
        with self._lock:
            return tuple(self._shown.get(character_id, ()))

    def broadcasts_for(self, scene: str) -> Tuple[Tuple[int, int, int], ...]:
        with self._lock:
            return tuple(self._broadcast.get(scene, ()))
