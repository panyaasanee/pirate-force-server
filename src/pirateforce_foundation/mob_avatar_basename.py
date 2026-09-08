"""The one place that turns an ``s_OUTFIT`` cell into what goes on the wire.

WHY THIS MODULE EXISTS.  ``CONSTDATA_TH__MOBS.s_OUTFIT`` is a CELL, not a
basename.  Some rows hold one basename (``M011_000_000_SP1``); others hold a
variant list (``M001_000_000_N;M001_000_000_SP1``).  The client formats what
the server sends into ``".\\Data\\GC\\V\\%s.avt"``, and ``RE-296`` result 2
(2026-09-07T20:53, PASS/BOUNDED-POSITIVE) measured the consumer: at
``0x0059AA52`` the index pushed to the tokeniser is a literal ``0``, so the
client uses the FIRST token and no caller can choose another one.

So a cell with a separator in it has exactly one meaning on the wire -- its
first token -- and shipping the whole cell can only produce a filename the
client cannot open.  COO-DECISION 2026-09-08T17:42 (LANE-B) rules that

    what goes on the wire is always a single basename

for every scene this lane ships, and that the raw cell, if a reader wants it,
lives in a SEPARATE column that nothing puts on the wire (``outfit_cell``).

This module is that single rule.  It is deliberately import-free so that the
roster generator (``tools/pf_mine_scene_mob_roster.py``, which is a
standalone script and imports nothing from this package) can load it by path
and mine under the very same function the server runs.  A second copy of the
rule is the failure this module is here to prevent.

NON-CLAIMS.  This does not claim the client tokenises on all three separators
in every code path; ``RE-296`` measured ``;``, TAB and SPACE at the tokeniser
it read, and this module refuses all three because the first token is the
same string under any subset of them.  It does not validate that the basename
names a file that ships -- nothing on this side of the wire can.  It does not
decide WHO is an enemy: that is ``n_RANK`` plus ``n_AI_COMBAT`` and nothing
else (PANYA 1313).
"""

from __future__ import annotations


#: The separators RE-296 read at the client's tokeniser, in the order the
#: measurement names them.  A cell containing any of these is a list.
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
            "%s would ship the s_OUTFIT CELL %r on the wire; the client "
            "formats it whole into '.\\Data\\GC\\V\\<name>.avt' and opens "
            "nothing.  Ship avatar_basename(cell) instead."
            % (what, value)
        )
    return value
