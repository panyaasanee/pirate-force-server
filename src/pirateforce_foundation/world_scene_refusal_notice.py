"""The refused login stops being anonymous: one line names WHO is stuck.

WHAT THIS FILE IS FOR, IN ONE SENTENCE.  When a character's stored row names
a scene this tree will not open, ``runtime.py`` catches
``world_scene_entry.SceneEntryRefused``, prints the exception and returns no
frames, and the line on the bridge console says WHY but never says WHO, so
an operator watching a console with several accounts on it cannot tell which
player is stuck, nor which row to look at to unstick them.  This module
composes the line that says both.

    WHAT THE CLIENT DOES WITH NO REPLY IS RECORDED, NOT PROVEN, AND IS SAID
    THAT WAY HERE.  ``runtime.py``'s own handler comment describes a client
    "parked on connecting with nothing logged", and LANE-DB's login-vitals
    module carries a pf-adversary-forced correction of that same sentence
    (grep ``is `runtime.py`'s own recorded observation about a DIFFERENT``
    under ``src/`` - the file is deliberately not named here, because a
    guard in that lane's own tests refuses any second file under ``src/``
    that spells its module name, and it caught an earlier draft of this
    paragraph doing exactly that).  The correction says the sentence is an
    observation about a DIFFERENT refusal: consistent with this one, not
    measured on it.  An earlier draft of this paragraph wrote "parks on
    connecting forever" as bare fact, three days after the tree was
    corrected for the same claim.  What IS measured is the server half: no
    frames go back.

WHY THIS IS A LANE-A FILE AND NOT A ONE-LINE EDIT IN ``runtime.py``.
``runtime.py`` is the chief's file (CHARTER-02) and this lane does not edit
it.  What this lane owns is the composed line; the wiring is one statement
the chief swaps in, and it is written down in a file git can see rather than
in a pull-request body a checkout cannot read:
``pf_bridge/notes_to_chief/20260903_1505_LANE-A-CORE-REQUEST-CHIEF-wire-the-
refusal-notice-at-runtime-8028.md``.  ~~Until that swap happens NOTHING IN
THIS FILE REACHES A CONSOLE -- read that as the plain status of the file,
not as a promise about tomorrow, and note that no test in this repository
can go red on the day the wiring is forgotten.~~  BOTH SENTENCES ARE FALSE
AT HEAD and are struck rather than deleted because they were the reason the
CORE-REQUEST existed (pf-adversary D7, round ``gs8hmn``).  chief landed the
swap: ``runtime.py:8462`` calls ``refusal_console_line`` on the real login
refusal path, and ``tests/test_scene_refusal_notice_wiring.py::
TheConsoleNamesTheLoginItRefusedTests`` drives a refusal through the real
dispatcher and reads the character id back off stdout, so it goes red the
day the wiring is removed.  THIS FILE IS ON THE PRODUCTION CONSOLE PATH.
A reader who takes the struck sentences at face value would conclude the
module is inert and its output shape is free to change; it is not.

SCOPE, SET BY ``COO-DECISION 20260903_1249`` POINT 4 AND NOT WIDENED HERE.
The order is "make the refusal observable (a console line, and a reason that
names the subject that was refused)" with a red line under it: DO NOT CHANGE
THE BEHAVIOUR OF THE GATE BY ONE BYTE.  So this module decides nothing.  It
holds no policy, reads no registry, admits and refuses nobody; it turns an
exception plus the row that provoked it into a string.  Every admission
question still belongs to ``world_scene_entry.resolve_entry`` exactly as it
did before this file existed.

WHY IT NEVER RAISES, WHICH IS DELIBERATE AND NOT LAZINESS.  The one caller
this module is written for is an ``except`` handler.  An exception raised
from inside that handler does not produce a better error message -- it
unwinds the connection's listener thread and restores exactly the silence
this file exists to end, with the original refusal lost on the way out.  So
every public function here is total: it accepts anything, and reports what
it was given rather than dying of it.  A caller that hands it something
unexpected gets a line saying so, on the console, where a person can read
it.  ``fail-closed`` for a DECIDER means "refuse"; for a NOTICE it means
"never go quiet", and those point in opposite directions.

THE LINE KEEPS THE PREFIX THE CONSOLE ALREADY HAS.  ``runtime.py:8028``
prints ``WORLD_SCENE_ENTRY_REFUSED {exc}`` today.  Three readers depend on
that text and all three keep working: ``tests/test_lane_a_scene_census.py``
pins ``WORLD_SCENE_ENTRY_REFUSED [scene_not_allowed_at_login]`` - token AND
bracketed reason, contiguous, the strictest of the three - and
``tests/test_gm_login_scene_sanctioned_bypass_wiring.py`` greps the token
alone three times (twice ``assertIn``, once ``assertNotIn``).  The composed
line therefore LEADS with ``TOKEN [reason]`` and adds everything else after
it; ``str(error)`` itself is preserved verbatim at the end under
``refusal_message=``.  See ``refusal_console_line`` for why the free text
goes last rather than second.

WHICH HANDLER THIS IS FOR, BECAUSE ``runtime.py`` HAS TWO.  ``except
world_scene_entry.SceneEntryRefused`` appears twice in the login path.  The
FIRST (near ``runtime.py:7936``) catches the PROBE that decides whether a GM
login-scene override may be applied: the login is NOT refused there, the
console token is ``GM_LOGIN_SCENE_OVERRIDE_REFUSED``, and that handler wraps
its own ``print`` in ``try/except Exception: pass`` because a raising print
would destroy a staged entry.  THIS MODULE IS FOR THE SECOND ONE
(``runtime.py:8028``), where the character's own row is refused and the
login returns no frames.  Wiring it into the first would rename a token
other readers grep for.

WHAT IT DOES NOT CLAIM.
1. It does NOT claim the player is told anything.  The client still gets no
   reply, because giving it one would change the gate's behaviour, which the
   order forbids.  This is an OPERATOR-observable change; the player-facing
   half is a separate ticket and must not be reported as this one.
2. It does NOT claim the line reached a console.  Like every composer in
   this lane, it returns a string; whether the caller printed it, and
   whether the console that received it was the cp874 bridge console, is
   decided by the caller.
3. It does NOT claim the refusal is rare, or that the reasons listed in
   ``world_scene_entry.REFUSAL_REASONS`` are all the reasons a login can
   fail.  It reports the one exception it was handed.

A THIRD ASCII FOLD IN THIS LANE, NAMED RATHER THAN PRETENDED AWAY.
``world_population_handoff._ascii_safe`` and
``world_scene_liveness._ascii_reason`` already fold text for the same cp874
console, and pf-adversary is right that ``_ascii_token`` is a third.  It is
not reuse because it answers a different question: those two return a
string, this one returns ``(printable, TRUE LENGTH, WAS IT EXACT)`` -- a
Thai character name folds to ``?????`` in all three, and only here does the
console also learn that the real name was five characters and that what it
is showing is a substitution.  Dropping that would take the "which player"
back out of a line whose whole purpose is naming them.  What WAS a real
defect is that this file invented a third spelling of the empty value while
its own comment claimed to be removing ambiguity; ``UNKNOWN`` is now
``none``, which is what the two neighbours print.  Folding the three into
one helper is worth a round of somebody's time and is not this round's.
"""

from __future__ import annotations

from . import world_scene_entry

# The token the console already carries, kept identical on purpose - see the
# module docstring.  ``runtime.py`` spells it as a literal today; when the
# wiring lands it should read this name instead, so the two cannot drift.
CONSOLE_TOKEN = "WORLD_SCENE_ENTRY_REFUSED"

# Longest name this line will print before it stops.  A console line that
# scrolls the reason off the top of a cp874 terminal is a line that hid the
# thing it exists to show; the true length is reported separately so the cap
# can never be mistaken for the name itself.
NAME_LIMIT = 32

# Longest refusal message this line will print.  Same argument as NAME_LIMIT.
# The messages ``world_scene_entry`` raises today are well under it -- but
# ``scene_not_pinned``'s message embeds ``repr(row.scene_id)`` and a caught
# ``KeyError``, neither of which this module sizes, so a cut here is
# reachable.  It is therefore REPORTED (``refused_message_len`` /
# ``refused_message_exact``) instead of being left to look like the whole
# message, which is the same discipline the name half has carried since
# round ``od1xso``.
MESSAGE_LIMIT = 240

# Longest refusal reason the leading bracket will print.  ITS OWN NUMBER,
# which is the whole point: this used to be ``NAME_LIMIT``, a constant sized
# for a CHARACTER NAME, so a fifth refusal reason of 33 characters would
# have been cut by a cap that has nothing to do with reasons (chief's report
# ``20260903_1605`` item 5; COO-DECISION ``20260903_1746`` item 4 handed
# this lane the numbers in this file).  64 is twice the longest reason the
# vocabulary has ever carried (``scene_not_allowed_at_login``, 26) and
# ``tests/test_scene_refusal_notice_wiring.py`` goes red the day a reason
# outgrows it -- red BEFORE the greps go quiet, which is the property that
# matters.
#
# WHY THIS IS A FIXED NUMBER AND NOT ONE DERIVED FROM ``REFUSAL_REASONS``.
# The first draft of this round computed it as
# ``max(NAME_LIMIT, *map(len, REFUSAL_REASONS))`` at import.  pf-adversary
# refuted that in three separate ways and every one of them is a defect this
# file already knows how to name:
#   * A ceiling computed from the data it bounds is not a ceiling.  A
#     vocabulary carrying a 430-character reason simply RAISED the cap to
#     430 and printed a 958-character console line -- the exact outcome
#     ``NAME_LIMIT``'s own comment forbids ("a line that scrolls the reason
#     off the top of a cp874 terminal is a line that hid the thing it exists
#     to show").  The derivation removed the only bound the field had.
#   * ``REASON_TRUNCATED`` became dead code by construction: no member of
#     the vocabulary present at import can exceed a cap computed from that
#     vocabulary at import, so the loud branch could never fire in a real
#     process.
#   * It ran untrusted iteration at IMPORT time behind ``except
#     Exception``.  A vocabulary whose ``__iter__`` raised ``SystemExit`` or
#     ``KeyboardInterrupt`` stopped this module from loading at all -- and
#     ``runtime.py`` imports it to compose the only account of a refused
#     login there is.  Measured, not predicted: two fresh subprocesses,
#     ``IMPORT FAILED``.
# The threat this cap answers is an HONEST fifth reason that is too long
# (chief's report), not a hostile vocabulary; a hostile vocabulary is a
# defect in the source file that defines the words, and the sanitising below
# is what this module owes it.  A fixed number answers the first threat
# completely and leaves the second bounded.
REASON_LIMIT = 64

# What the leading bracket prints INSTEAD OF A PREFIX if a refusal reason
# ever exceeds ``REASON_LIMIT``.  A cut reason is the one truncation in this
# line that is actively dangerous: ``TOKEN [reason]`` leads the line,
# ``GAME_TEST_QUEUE.md:6678`` and ``tests/test_lane_a_scene_census.py:1013``
# grep it as one contiguous string, and a prefix of a real reason still
# READS like a real reason to a human scanning a console.  A word that is
# not in the vocabulary at all cannot be misread as one.
REASON_TRUNCATED = "reason_truncated"

# What the bracket prints instead of a reason that could FORGE A BRACKET.
# pf-adversary D2, second input, and it needs no truncation at all: the
# 28-character reason ``scene_not_allowed_at_login]x`` is under every cap,
# is sanitised to itself (``]`` is 0x5D, inside the printable range this
# file keeps), and composes
# ``WORLD_SCENE_ENTRY_REFUSED [scene_not_allowed_at_login]x]`` -- which
# CONTAINS the contiguous string ``tests/test_lane_a_scene_census.py:1013``
# and ``GAME_TEST_QUEUE.md:6678`` pin, so a refusal that is not
# ``scene_not_allowed_at_login`` satisfies both readers and reads as that
# reason to a human.  A prefix was never the only way to lie in this field;
# a SUPERSTRING is the other, and it predates this round.  A reason carrying
# a bracket of its own is refused by name rather than printed.
REASON_MALFORMED = "reason_malformed"

# What is printed where a field could not be read at all.  ``none`` and not
# ``unknown``: this lane already prints ``none`` for the same condition in
# ``world_scene_travel.entry_console_line`` ("spawn=none") and in
# ``world_population_handoff``, and an earlier draft of this file invented a
# third spelling while its own comment claimed to be removing ambiguity.
UNKNOWN = "none"


def _ascii_token(
    value: object, limit: int, keep_spaces: bool = False
) -> tuple[str, int, bool]:
    """``(printable, true_length, is_exact)`` for a value going on the wire.

    ``keep_spaces`` is for the free-text refusal message, which sits at the
    FRONT of the line and is terminated by the first ``refusal_reason=``, so
    spaces in it cannot be mistaken for a field separator and squashing them
    would only make the sentence harder to read.  Every ``key=value`` field
    after it is composed with ``keep_spaces=False``, where a space really
    would invent a field that is not there.  Whitespace that is not a plain
    space (a newline above all) becomes ``_`` either way: it must stay
    visible, and it must not split the line.

    The bridge console is cp874 and this lane's console lines stay inside
    7-bit ASCII deliberately (``world_scene_travel.entry_console_line`` says
    the same in its own docstring).  A Thai character name is legal cp874
    and illegal here, so it is SUBSTITUTED rather than dropped: the operator
    still gets the length and the exactness flag, and the numeric ids beside
    it identify the row without ambiguity anyway.
    """
    if value is None:
        return UNKNOWN, 0, False
    try:
        text = value if type(value) is str else str(value)
    except Exception:  # noqa: BLE001 - a __str__ that raises is still a row
        return UNKNOWN, 0, False
    true_length = len(text)
    out = []
    exact = True
    for char in text:
        if char == " " and keep_spaces:
            out.append(" ")
            continue
        if char.isspace():
            out.append("_")
            exact = False
            continue
        code = ord(char)
        if 0x21 <= code <= 0x7E:
            out.append(char)
            continue
        out.append("?")
        exact = False
    if len(out) > limit:
        out = out[:limit]
        exact = False
    printable = "".join(out)
    if not printable:
        return UNKNOWN, true_length, False
    return printable, true_length, exact


def _safe_getattr(obj: object, name: str) -> object:
    """``getattr`` that survives a property which raises.

    ``getattr(obj, name, None)`` only swallows ``AttributeError``; a stub or a
    half-built object whose ``name`` property raises anything else takes the
    whole composer down to its last-resort line and the REASON goes with it.
    The reason is the half the console has today, so losing it to a defect in
    the SUBJECT half would be a straight regression.  Read a field, or report
    that field as unreadable, and keep the rest of the line.
    """
    try:
        return getattr(obj, name)
    except Exception:  # noqa: BLE001 - deliberately total, see above
        return None


def _int_token(value: object) -> str:
    """A field that should be an integer, or a readable account of why not."""
    if value is None:
        return UNKNOWN
    if type(value) is bool:
        # bool is an int in Python and a bool in an id field is a defect
        # worth seeing rather than printing as 0/1.
        return "not_an_int"
    # ``str()`` OF AN int CAN RAISE, WHICH IS NOT A JOKE: CPython caps
    # int->str at 4300 digits (PEP 686 / sys.set_int_max_str_digits), so a
    # row carrying a huge integer takes an unguarded composer down.
    # pf-adversary reached this with ``id=10**5000``.
    try:
        if type(value) is int:
            return str(value)
        return str(int(value))
    except BaseException:  # noqa: BLE001 - report the shape, never die of it
        return "not_an_int"


def _reason_of(error: object) -> str:
    """The refusal reason, checked against the module that defines them.

    Derived, never re-listed: ``world_scene_entry.REFUSAL_REASONS`` is the
    one place the vocabulary lives, and a reason added there without a
    thought for this file still prints correctly here.  A value outside it
    is reported as unrecognised rather than passed through, because a
    reason this tree does not define is itself the finding.
    """
    reason = _safe_getattr(error, "reason")
    if type(reason) is not str:
        return "reason_absent"
    if reason not in world_scene_entry.REFUSAL_REASONS:
        return "reason_unrecognised"
    # SANITISED EVEN THOUGH IT CAME FROM THE VOCABULARY.  Deriving the
    # vocabulary from its owner (rather than copying the four names into
    # this file) is the right call, and it means this module prints a
    # string another module chose.  pf-adversary added a reason containing
    # a newline to ``REFUSAL_REASONS`` and this function emitted TWO console
    # lines with the whole suite green.  "Derived" is not "trusted".
    printable, length, _exact = _ascii_token(reason, REASON_LIMIT)
    if length > REASON_LIMIT:
        # Every field in this file reports what it was handed; this is the
        # one field where reporting a TRUNCATED value would be reporting a
        # DIFFERENT refusal, because the bracket leads the line and two
        # readers grep it contiguously.  Reachable the day the vocabulary
        # grows a reason past the cap -- the wiring test goes red first, and
        # this is what the console does if it did not.
        return REASON_TRUNCATED
    if "[" in printable or "]" in printable:
        # See ``REASON_MALFORMED``.  Checked on the SANITISED text, not on
        # the raw value: the sanitiser is what decides which characters
        # reach the console, so anything it lets through is what has to be
        # judged here.
        return REASON_MALFORMED
    return printable


def _message_token(error: object) -> tuple[str, object, bool]:
    """``str(error)`` flattened to one printable ASCII line, plus its size.

    The length and the exactness flag are returned rather than dropped: the
    message is the only field on this line whose length this module does not
    control (see ``MESSAGE_LIMIT``), so a reader who cannot tell 240
    characters of message from 240 characters of a longer one has been shown
    a cut and told it was the whole thing.

    THE TWO PLACEHOLDER CASES REPORT DIFFERENT THINGS, AND THE FIRST DRAFT
    OF THIS ROUND REPORTED THEM THE SAME (pf-adversary D5).  Both returned
    ``0, False``, which under this line's own documented meaning reads "the
    thirteen characters you can see are a CUT of a zero-character message"
    -- a sentence that is false twice.
    * An EMPTY message was measured, and its length really is 0 and really
      is exact.  ``message_empty`` is a name for nothing, not a cut of it.
    * An UNREADABLE message was never measured at all, so its length is
      ``UNKNOWN`` and not ``0``.  Printing a plausible number for a value
      that was never read is the one thing every other helper in this file
      refuses to do (``not_an_int``, ``reason_absent``, ``none``).
    """
    try:
        text = str(error)
    except Exception:  # noqa: BLE001 - see the module docstring
        return "message_unreadable", None, False
    if not text:
        return "message_empty", 0, True
    return _ascii_token(text, MESSAGE_LIMIT, keep_spaces=True)


def refusal_report(
    error: object,
    character: object = None,
    row: object = None,
    reply_frames: object = None,
) -> dict:
    """Everything the line says, as a dict, for tests and for reports.

    ``character`` is the selected character (``model.Character``) whose
    login was refused; ``row`` is the ``Position`` that was handed to
    ``resolve_entry`` -- which is NOT always the character's stored row, see
    ``refused_row_scene_id`` below.  Both are read with ``_safe_getattr``
    and neither is required: a caller that has only one of them still gets
    a usable line.

    ``reply_frames`` is how many frames the caller is about to return to
    the client.  It is a PARAMETER and not a constant on purpose: this
    module does not know what its caller does next, and a hardcoded
    ``reply=none`` here would keep printing "none" on the day somebody
    makes the refusal answer the player.  Left unset it reports
    ``unreported``.

    THIS FUNCTION IS AS TOTAL AS THE LINE COMPOSER.  It is advertised "for
    tests and for reports", and a report generator that dies on a hostile
    row is a report generator that hid the row.  Every field is produced by
    a helper that reports what it was handed instead of raising on it.
    """
    name_token, name_length, name_exact = _ascii_token(
        _safe_getattr(character, "name"), NAME_LIMIT
    )
    if reply_frames is None:
        reply = "unreported"
    else:
        reply = _int_token(reply_frames)
    message_token, message_length, message_exact = _message_token(error)
    return {
        "token": CONSOLE_TOKEN,
        "reason": _reason_of(error),
        "message": message_token,
        "message_length": message_length,
        "message_exact": message_exact,
        "character_id": _int_token(_safe_getattr(character, "id")),
        "account_id": _int_token(_safe_getattr(character, "account_id")),
        "selector": _int_token(_safe_getattr(character, "selector")),
        "name": name_token,
        "name_length": name_length,
        "name_exact": name_exact,
        "row_scene_id": _int_token(_safe_getattr(row, "scene_id")),
        "row_scene_seq": _int_token(_safe_getattr(row, "scene_seq")),
        "reply_frames": reply,
    }


# The structured half of the line, in order.  Field name -> report key.  The
# free-text message is deliberately NOT in here: it goes last, see
# refusal_console_line.
_FIELDS = (
    ("refused_character_id", "character_id"),
    ("refused_account_id", "account_id"),
    ("refused_selector", "selector"),
    ("refused_name", "name"),
    ("refused_name_len", "name_length"),
    ("refused_name_exact", "name_exact"),
    ("refused_row_scene_id", "row_scene_id"),
    ("refused_row_scene_seq", "row_scene_seq"),
    ("reply_frames", "reply_frames"),
)

# Report keys whose value is a flag, printed ``yes``/``no`` rather than
# ``True``/``False``: the rest of this lane's console lines spell booleans
# that way, and an earlier draft special-cased exactly one of them by name.
_FLAG_KEYS = ("name_exact",)


def refusal_console_line(
    error: object,
    character: object = None,
    row: object = None,
    reply_frames: object = None,
) -> str:
    """One ASCII line naming the refusal AND the login it refused.

    Shape (one line, no newline, 7-bit ASCII)::

        WORLD_SCENE_ENTRY_REFUSED [scene_has_no_pinned_spawn]
        refused_character_id=7 refused_account_id=3 refused_selector=0
        refused_name=Blackbeard refused_name_len=10 refused_name_exact=yes
        refused_row_scene_id=278 refused_row_scene_seq=0 reply_frames=0
        refused_message_len=117 refused_message_exact=yes
        refusal_message=[scene_has_no_pinned_spawn] scene 278 is pinned but
        has no spawn position - measure one before sending a player there

    THAT EXAMPLE IS COPIED FROM A LINE THIS MODULE ACTUALLY COMPOSED, and
    the round that added the two size fields first wrote one it had invented
    -- ``refused_message_len=71`` under a ``[scene_not_pinned]`` message
    whose shortest possible instance is 128 characters, beside a scene id
    that does not refuse at all at HEAD (pf-adversary D6).  The one worked
    example a reader uses to learn what a new field means is the last place
    to put a number nobody can reproduce.

    ``refused_message_exact=no`` says the text after ``refusal_message=`` is
    a CUT of a ``refused_message_len``-character message (or carries a
    substituted character), so a reader never has to guess whether a message
    that ends mid-sentence ended that way at the source.
    ``refused_message_len=none`` says the message was never readable, which
    is not the same as a message of length 0 -- see ``_message_token``.

    WHY THE FREE TEXT IS LAST, WHICH IS THE WHOLE PARSING CONTRACT.  The
    refusal message is the only field this module does not control: it is
    ``str(error)``, and ``resolve_entry`` embeds ``repr(row.scene_id)`` in
    it.  An earlier draft of this file put the message SECOND and told
    readers to parse "up to the first ``refusal_reason=``".  pf-adversary
    refuted it by handing ``resolve_entry`` a row whose ``scene_id`` was the
    string ``"9 refusal_reason=scene_not_pinned refused_character_id=1 ..."``
    -- the forged fields then came FIRST, and a first-occurrence parser read
    a wrong reason and an innocent character id off a real console line.
    With the message last, every structured field precedes anything an
    attacker-controlled string can add, so FIRST OCCURRENCE OF EACH KEY IS
    THE TRUE ONE and text after ``refusal_message=`` is free text by
    definition.  (Reachability today is the callers': ``store.py`` coerces
    ``int(row['scene_id'])`` and ``gm/login_scene_override.py`` requires an
    ``int``.  That is their guarantee, not this module's, and it is not
    something a composer should rely on.)

    ``TOKEN [reason]`` LEADS, AND THAT IS LOAD-BEARING.  ``runtime.py:8028``
    prints ``WORLD_SCENE_ENTRY_REFUSED {exc}`` today, where ``str(exc)``
    starts ``[reason] ``.  ``tests/test_lane_a_scene_census.py:1013`` pins
    the token AND the bracketed reason together as one contiguous string,
    and ``tests/test_gm_login_scene_sanctioned_bypass_wiring.py`` greps the
    token alone (twice for presence, once for absence).  Leading with
    ``TOKEN [reason]`` keeps every one of those readers working -- and the
    bracket here is the VALIDATED ``error.reason``, while the raw
    ``str(error)`` (which carries its own bracket) is preserved verbatim at
    the end, so the day the two disagree the console shows both instead of
    one agreeable-looking string.

    Never raises -- not even ``BaseException`` out of a hostile property;
    see the module docstring for why that is the right shape for this one
    caller, and ``world_scene_liveness._ascii_reason``, which catches the
    same width for the same reason.
    """
    # Composed OUTSIDE the guard below and from the error alone: the reason
    # and the message are the half the console already has today, and
    # ``str(exc)`` never touches the character object.  Losing them to a
    # defect in the SUBJECT half - the half this round ADDS - would be a
    # regression wearing an improvement's clothes.
    try:
        reason = _reason_of(error)
    except BaseException:  # noqa: BLE001 - see the docstring
        reason = "reason_unreadable"
    try:
        message, message_length, message_exact = _message_token(error)
    except BaseException:  # noqa: BLE001 - see the docstring
        message, message_length, message_exact = "message_unreadable", None, False
    try:
        report = refusal_report(error, character, row, reply_frames)
    except BaseException:  # noqa: BLE001 - the subject half failed; the
        # reason half above still stands, and it is what goes out.
        report = None
    parts = [f"{CONSOLE_TOKEN} [{reason}]"]
    if report is None:
        parts.append("refused_subject=unreadable")
    else:
        for field, key in _FIELDS:
            value = report[key]
            if key in _FLAG_KEYS:
                value = "yes" if value else "no"
            parts.append(f"{field}={value}")
    # OUTSIDE THE `report is None` BRANCH ON PURPOSE (pf-adversary D3).  The
    # message and its size are composed from the error alone, above, so they
    # survive a subject half that failed -- and if they were emitted from
    # `report` they would VANISH on the degraded path, leaving the free text
    # to supply the FIRST occurrence of `refused_message_len=` and
    # `refused_message_exact=`.  That is precisely the forgery this line's
    # ordering contract exists to prevent, reopened by the branch that is
    # supposed to be its safety net: measured, a hostile row printed
    # `refused_message_len=9` while this module held the true value 139.
    # Every field a parser trusts precedes `refusal_message=` ON EVERY PATH,
    # or the contract in the docstring below is not a contract.
    parts.append(
        "refused_message_len="
        + (UNKNOWN if message_length is None else str(message_length))
    )
    parts.append(
        "refused_message_exact=" + ("yes" if message_exact else "no")
    )
    parts.append(f"refusal_message={message}")
    return " ".join(parts)
