"""The one place that turns an ``s_OUTFIT`` cell into what goes on the wire.

WHY THIS MODULE EXISTS.  ``CONSTDATA_TH__MOBS.s_OUTFIT`` is a CELL, not a
basename.  Some rows hold one basename (``M011_000_000_SP1``); others hold a
variant list (``M001_000_000_N;M001_000_000_SP1``).  This lane was shipping
whole cells for 40 of Bg0002's 52 monsters, and COO-DECISION 2026-09-08T17:42
(LANE-B) rules that

    what goes on the wire is always a single basename

for every scene this lane ships, and that the raw cell, if a reader wants it,
lives in a SEPARATE column that nothing puts on the wire (``outfit_cell``).
That ruling is the authority this module implements.

WHAT THE MEASUREMENT ACTUALLY SAYS, STATED NARROWLY ON PURPOSE (corrected
under pf-adversary D3, round db4o73, which caught the first draft of this
docstring overstating it).  ``RE-296`` result 2 (2026-09-07T20:53,
PASS/BOUNDED-POSITIVE) read the function at ``0x0059A7A0``: it loads the
CLIENT'S OWN ``MOBS.s_OUTFIT`` row, tokenises that string, and pushes a
literal ``0`` at ``0x0059AA52`` to take the first token.  That is a
measurement about how the client reads ITS OWN TABLE.  It is NOT a
measurement of what the client does with the ``visual_preset`` wstr this
server writes into ``NPCAttr+0x7C``: the same result's own nonclaim 2 records
that 8 of 13 ``%s%s.avt`` xrefs were never walked, and that the sampled ones
read an already-resolved string and do not tokenise at use time.

So this module does NOT claim that sending a whole cell would fail to draw,
nor that sending one basename makes a body appear.  What it claims is
narrower and enough: the only reading of a cell this project has ever
measured anywhere is "first token", the server has no consumer that wants a
list, and a single basename is the only form both readings agree on.  The
open question -- what the wire wstr does at the client -- is written down in
the round file rather than papered over here.

This module is that single rule.  It is deliberately import-free so that the
roster generator (``tools/pf_mine_scene_mob_roster.py``, which imports
nothing from this package) can load it by path and mine under the very same
function the server runs.  A second copy of the rule is the failure this
module is here to prevent.

HOW WIDE "SINGLE" IS, MEASURED (round vavm4h, paying pf-adversary D9 of
round db4o73, which caught the first draft calling this "the single
dispenser" of the rule while the test behind that sentence skipped LANE-A's
files BY NAME).  It is single FOR THIS LANE.  The same first-token reading
is held in 15 other files -- LANE-A's ``world_bg*_identity.py`` tables, 26
lines between them -- which this lane does not own and does not get to
refactor.  Those are now COUNTED by
``tests/test_mob_avatar_basename.py``: a sixteenth holder, or a change in
any of the fifteen counts, turns that test red naming the file.  The claim
this module is entitled to is therefore the narrow one: LANE-B reads a cell
in one place, and every other reader in the tree is enumerated rather than
excluded by a name pattern that cannot tell a new one from an old one.

BOTH ENDS OF THE RULE REFUSE THE SAME THING (pf-adversary D10).  The gate
below refuses a list cell reaching the wire.  Since round vavm4h the roster
generator refuses the mirror case at the other end -- a cell whose first
token is empty (``";X"``), which would have written a value into a generated
table that this server's own boot path then rejects.  Neither end guesses:
both name the row and stop.

NON-CLAIMS.  It does not validate that the basename names a file that ships
-- nothing on this side of the wire can.  It does not decide WHO is an enemy:
that is ``n_RANK`` plus ``n_AI_COMBAT`` and nothing else (PANYA 1313).  And
see ``AVATAR_SEPARATORS`` below for what is, and is not, measured about the
separator set -- pf-adversary D4 caught the first draft of this file
attributing a claim to ``RE-296`` that ``RE-296`` wrote a red warning
against.
"""

from __future__ import annotations


#: WHAT IS MEASURED: ``RE-296`` result 2 section 6.5 reads the separator AT
#: THE POINT OF USE as ``;`` ALONE (the constant at ``0x00F0C9AC``); the
#: three-character set ``";\t "`` at ``0x00F14594`` is what the table LOADER
#: uses, and that result flags in red that the two must not be assumed to be
#: the same set.  This tuple is deliberately the WIDER set anyway, and that
#: is a choice of this lane's, not a reading of RE-296:
#:
#: * measured, round db4o73, over every OUTFIT column of every table in the
#:   committed ``gamedata/tables`` -- 565 cells contain ``;`` and ZERO
#:   contain a TAB or a space.  So on the data this project actually ships,
#:   the wide set and the narrow set return the same string for every row,
#:   and the choice changes no byte on the wire today.
#: * a cell that DID contain a space would be one this lane has never seen;
#:   refusing to put it on the wire whole is the conservative half.
#:
#: NOT claimed (pf-adversary D4): that the first token is the same string
#: under any subset of these separators.  It is not -- ``A B;C`` reads ``A``
#: here and ``A B`` under ``;`` alone.  If a cell like that ever appears,
#: this constant is the thing to re-measure, and the test that pins
#: ``"A B" -> "A"`` is pinning THIS lane's choice, not the client's.
AVATAR_SEPARATORS = (";", "\t", " ")


def avatar_basename(cell: str) -> str:
    """The single basename the client will actually load from ``cell``.

    Returns the first token of the cell under every separator in
    :data:`AVATAR_SEPARATORS`, with surrounding whitespace stripped.  A cell
    that is already one basename comes back unchanged; an empty or
    whitespace-only cell comes back as ``''``, which callers upstream already
    treat as "this row ships no avatar" rather than as an error.
    """
    if not isinstance(cell, str):
        raise TypeError("s_OUTFIT cell must be str, got %r" % type(cell))
    token = cell.strip()
    for separator in AVATAR_SEPARATORS:
        token = token.split(separator, 1)[0]
    return token.strip()


def has_separator(value: str) -> bool:
    """True when ``value`` is a list cell rather than a single basename.

    The wire-side guard: a value that answers True here must never be handed
    to the client, because the client would format the whole string into the
    ``.avt`` path and open nothing.
    """
    return any(separator in value for separator in AVATAR_SEPARATORS)


class AvatarCellOnTheWireError(ValueError):
    """A list cell reached a place that hands values to the client."""


def refuse_list_cell(value: str, *, what: str) -> str:
    """Refuse ``value`` if it is a cell rather than a basename; else return it.

    This is the gate, not the fixer.  It deliberately does NOT normalise: a
    list cell arriving at the wire means a generated table is stale or a
    caller hand-built a row from ``s_OUTFIT`` directly, and silently trimming
    it would leave that stale table shipping for another round with nothing
    to show for it.  Callers that legitimately hold a raw cell call
    :func:`avatar_basename` themselves, at the point where they read the
    table -- which for this lane is the roster generator and nowhere else.
    """
    if has_separator(value):
        raise AvatarCellOnTheWireError(
            "%s would ship the s_OUTFIT CELL %r on the wire; this lane "
            "sends one basename and never a list (COO-DECISION "
            "2026-09-08T17:42).  Ship avatar_basename(cell) instead."
            % (what, value)
        )
    return value
