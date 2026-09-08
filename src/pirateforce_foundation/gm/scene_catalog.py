"""GM-004: scene id -> GM scene name catalog.

Source: pf_bridge/gamedata/tables/TEXTDATA_TH__SCENE_NAME_TIP.tsv, copied
byte-for-byte into ``gm/data/gm_scene_name_tip.tsv`` (this is the "แมพ GM"
the owner asked for -- 330 GM-labeled scene names shipped in the client's own
data, not anything this lane invented).

    SOURCE_SHA256 below is the sha256 of that copy; it is checked at import
    time against the committed file so a future edit -- accidental or not --
    fails loudly instead of silently drifting from the client's table.

This module answers "what scene id does this GM scene name refer to" and
back.  It does not answer "does warping to this scene id work" -- that is a
runtime/wire question outside a static gamedata table's evidence tier (see
AGENTS.md evidence grades; this table is grade A, a committed client
artifact, and stays grade A only for "this id has this name").
"""
from __future__ import annotations

from pathlib import Path
import csv
import difflib
import hashlib

_DATA_PATH = Path(__file__).parent / "data" / "gm_scene_name_tip.tsv"

SOURCE_SHA256 = "f9076cfc3c14433b376811437d68375d5dd1ce1ef2c7a50dbc1d4e4d241bfa3a"


def _load_rows() -> list[tuple[int, str, str]]:
    raw = _DATA_PATH.read_bytes()
    actual_sha = hashlib.sha256(raw).hexdigest()
    if actual_sha != SOURCE_SHA256:
        raise RuntimeError(
            f"gm_scene_name_tip.tsv sha256 mismatch: expected {SOURCE_SHA256}, "
            f"got {actual_sha} -- table drifted from the pinned client source, "
            "re-derive from pf_bridge/gamedata before trusting this catalog"
        )
    rows: list[tuple[int, str, str]] = []
    with _DATA_PATH.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle, delimiter="\t")
        header = next(reader)
        assert header == ["n_ID", "s_SCENE_NAME", "s_GM_SCENE_NAME"], header
        for row in reader:
            n_id, scene_name, gm_scene_name = row
            rows.append((int(n_id), scene_name.strip(), gm_scene_name.strip()))
    return rows


_ROWS = _load_rows()

SCENE_ID_TO_GM_NAME: dict[int, str] = {n_id: gm_name for n_id, _, gm_name in _ROWS}
SCENE_ID_TO_NAME: dict[int, str] = {n_id: name for n_id, name, _ in _ROWS}
SCENE_COUNT = len(_ROWS)


def gm_scene_name(scene_id: int) -> str:
    """The GM-facing scene name for scene_id, e.g. 1 -> 'Port Royal'."""
    try:
        return SCENE_ID_TO_GM_NAME[scene_id]
    except KeyError as exc:
        raise KeyError(f"scene_id {scene_id} is not in the GM scene catalog") from exc


def scene_ids_named(gm_scene_name_query: str) -> list[int]:
    """All scene_ids whose GM scene name matches exactly (many names repeat)."""
    return [
        n_id for n_id, name in SCENE_ID_TO_GM_NAME.items() if name == gm_scene_name_query
    ]


def is_known_scene_id(scene_id: int) -> bool:
    return scene_id in SCENE_ID_TO_GM_NAME


# --- name -> scene_id, the direction an operator at the client needs ------
#
# `gm_scene_name` answers "what is scene 2 called".  An operator sitting at
# the client at 1 a.m. has the opposite question: they know they want the
# island, not that the island is scene 2.  `resolve_gm_scene_name` is that
# direction, and `gm/commands.py`'s `warp` grammar is its only caller today.
#
# THE TABLE IS NOT A FUNCTION.  Measured on the pinned file: 330 rows,
# 293 distinct GM names.  SIX names repeat -- `Hidden Island` alone is on
# 20 scene ids and `Poseidon Island` on 10 -- and FOUR rows carry an empty
# name (ids 13, 137, 138, 141).  (Corrected by pf-adversary round `nqgmam`
# D5: this paragraph said 294 and seven, which is 293 and six plus the
# empty name counted as a name -- the same mistake twice, in the very
# paragraph whose point is that the empty name is excluded.  `GM_NAME_COUNT`
# is 293 and is what the operator-facing refusal prints.)  So this returns
# ALL matching ids and lets
# the caller decide; a "first match wins" resolver would have silently sent
# a GM to one of twenty Hidden Islands, and an empty query would have
# matched four scenes at once.  An empty (or whitespace-only) query matches
# NOTHING here, by construction rather than by a caller remembering to
# check.
#
# Folding: leading/trailing space is stripped, internal whitespace runs
# collapse to one space (the shipped table pads every cell with spaces),
# and case folds.  Measured on the pinned file: folding case merges no two
# distinct names, so the fold cannot invent an ambiguity the table does not
# already have -- `test_gm_scene_catalog.py` pins that.


def _fold_gm_scene_name(name: str) -> str:
    """Fold one GM scene name to the key `resolve_gm_scene_name` matches on."""
    return " ".join(name.split()).casefold()


def _build_name_index() -> dict[str, tuple[int, ...]]:
    index: dict[str, list[int]] = {}
    for n_id, _scene_name, gm_name in _ROWS:
        key = _fold_gm_scene_name(gm_name)
        if not key:
            # The four unnamed rows. They are reachable by id and only by id.
            continue
        index.setdefault(key, []).append(n_id)
    return {key: tuple(sorted(ids)) for key, ids in index.items()}


_GM_NAME_TO_SCENE_IDS: dict[str, tuple[int, ...]] = _build_name_index()

GM_NAME_COUNT = len(_GM_NAME_TO_SCENE_IDS)

#: The longest key `resolve_gm_scene_name` can ever match, in characters,
#: derived from the pinned table rather than typed.  Measured today: 54, on
#: a Thai name -- the table is `TEXTDATA_TH__*` and ~~37~~ **209** of its 330
#: rows carry Thai (pf-adversary, this round, D4: 37 was `SCENE_COUNT -
#: GM_NAME_COUNT`, the duplicate-row arithmetic from 40 lines above this,
#: re-labelled; walked all 330 rows over U+0E00..U+0E7F to correct it), so
#: this is a CHARACTER count and deliberately not a byte count.
#:
#: It exists so that `gm/commands.py` can bound the `warp <scene name>`
#: query without a number somebody chose: no query that folds to something
#: longer than this can match any scene, and a bound that moves with the
#: table cannot go stale the way a literal would.
LONGEST_GM_NAME_LENGTH = max(len(key) for key in _GM_NAME_TO_SCENE_IDS)


def resolve_gm_scene_name(query: str) -> tuple[int, ...]:
    """Every scene id whose GM scene name folds to `query`, ascending.

    Empty tuple means no scene carries that name -- including for an empty
    or whitespace-only query, which never matches the table's four unnamed
    rows.  A tuple longer than one means the name is genuinely ambiguous in
    the client's own table; the caller must not pick one.
    """
    if not isinstance(query, str):
        raise TypeError("query must be a str")
    key = _fold_gm_scene_name(query)
    if not key:
        return ()
    return _GM_NAME_TO_SCENE_IDS.get(key, ())


# --- a near miss is not a dead end ----------------------------------------
#
# `resolve_gm_scene_name` is exact-or-nothing, which is right for deciding
# WHERE to send a GM but wrong as the last thing an operator reads.  The
# round that added it left this hole: mistype one letter of a 330-row table
# at 1 a.m. and the only answer is "no GM scene carries that name", with no
# way to search from the client.  `suggest_gm_scene_names` is that search.
#
# EVERY CHARACTER IT RETURNS COMES OUT OF THE PINNED TABLE, NEVER OUT OF THE
# QUERY.  That is the whole reason this can be printed at all: these lines
# reach a cp874 console, and `test_gm_scene_catalog.py` pins that all 330
# shipped names encode to cp874, so a suggestion cannot be the unlucky byte
# that kills the console.  Echoing the operator's own text back would carry
# no such guarantee -- see `gm/commands.py::_parse_warp_named`.
#
# It returns NAMES with their id count, not a flat list of ids: `Hidden
# Island` is on twenty scenes, and a suggestion that prints twenty numbers
# is a suggestion nobody reads.  The caller decides how many to show.

#: Below this ratio a "suggestion" is noise that sends the operator to the
#: wrong island.  Measured on the pinned table rather than chosen: at 0.7,
#: `Prison Exile Iland` (one letter dropped) still finds `Prison Exile
#: Island`, and `qqqqqqqq` finds nothing at all.  Both are pinned.
SUGGESTION_MINIMUM_RATIO = 0.7

#: A way-out line is read or it is not; three is the most that stays read.
MAX_SUGGESTIONS = 3


def suggest_gm_scene_names(
    query: str, limit: int = MAX_SUGGESTIONS
) -> tuple[tuple[str, int], ...]:
    """Table names close to `query`, as (shipped name, how many scene ids).

    Empty tuple for an empty/whitespace-only query, for a query that folds
    to a key already in the table (an exact hit is not a suggestion -- the
    caller had a match and did not need this), and for a query that is
    neither close to nor contained in any shipped name.  Best match first.

    WHO READS THIS TODAY: NOBODY, and that has to be said first
    (pf-adversary round `pdf3gh`, D1, MEASURED).  The only live caller is
    `gm/commands.py::_did_you_mean`, which puts this into a
    `GmCommandParseError` message -- and the only code in `src/` that
    catches that exception, `chat_command.py`, discards the message by
    contract and answers with `refusal_hint`, one of seven fixed sentences
    that is "NEVER DERIVED FROM WHAT WAS TYPED".  Measured end to end:
    the console line for `/warp Atlantic` is byte-identical before and
    after this search existed.  So every number below is a fact about a
    string the wire path throws away, and none of it is an operator-facing
    improvement until somebody decides whether a suggestion may be printed
    at all.  That decision is open and is the next round's first question.

    TWO SEARCHES, IN THIS ORDER, because they answer two different people.
    `difflib` answers the operator who typed a whole name and dropped a
    letter.  It CANNOT answer the operator who remembers a piece of one:
    walked over the table today, **61** of the 86 distinct first words of
    the shipped names returned nothing at all -- of which **55**
    (`Atlantic`, `Deep`, `Dragon`, `Eagle`, `Bear`) score below
    `SUGGESTION_MINIMUM_RATIO` against every one of the 293 keys, because
    the ratio is computed over the WHOLE name and a fragment is mostly
    missing name.  (The other 6 are first words that ARE whole table keys
    and return `()` through the exact-hit rule at the top of this
    function, before and after -- 61 was right for "answered nothing" and
    wrong for "scored below the ratio", which is the pair pf-adversary
    round `pdf3gh` D5 separated.)  So `warp Atlantic` used to end at "no
    GM scene carries that name" with nothing after the semicolon -- in the
    parser's message, which is the layer this paragraph is about.
    Containment fills the slots `difflib` left empty; it never displaces a
    close match, so no query that was answered before is answered worse.

    A fragment shorter than any real name browses rather than searches (`a`
    returns the first three names carrying an `a`).  That is bounded by
    `limit` and pinned in the order below rather than forbidden by a floor:
    the shortest key in the table is 9 characters, and a floor derived from
    it would have refused `Atlantic` -- the very query this exists for.

    The second element of each pair is the number of scene ids that name is
    on, so a caller can say "on 20 scenes" instead of printing 20 numbers.
    """
    if not isinstance(query, str):
        raise TypeError("query must be a str")
    if limit <= 0:
        return ()
    key = _fold_gm_scene_name(query)
    if not key or key in _GM_NAME_TO_SCENE_IDS:
        return ()
    folded_keys = list(_GM_NAME_TO_SCENE_IDS)
    close = difflib.get_close_matches(
        key,
        folded_keys,
        n=limit,
        cutoff=SUGGESTION_MINIMUM_RATIO,
    )
    ordered = list(close)
    if len(ordered) < limit:
        already = set(ordered)
        for folded in _containing_keys(key, folded_keys):
            if folded in already:
                continue
            ordered.append(folded)
            already.add(folded)
            if len(ordered) == limit:
                break
    return tuple(
        (SCENE_ID_TO_GM_NAME[_GM_NAME_TO_SCENE_IDS[folded][0]],
         len(_GM_NAME_TO_SCENE_IDS[folded]))
        for folded in ordered
    )


def _containing_keys(key: str, folded_keys: list[str]) -> list[str]:
    """Every folded table key that CONTAINS `key`, in a pinned order.

    Ordered by where the fragment lands and then alphabetically, so the same
    query returns the same three names on every run and on every machine --
    `dict` order over the table would be neither, and an operator who reads
    a different answer to the same typo twice stops reading the answer.
    A name that STARTS with the fragment comes first because that is the
    shape a half-remembered name has.

    ~~`warp Prison` is a person who knows the beginning of `Prison Exile
    Island`~~ IS STRUCK AS THE EXAMPLE (pf-adversary round `pdf3gh`, D6,
    MEASURED): that query answers `Navy Prison` FIRST, because `navy
    prison` is a difflib close match and every difflib hit is placed ahead
    of every containment hit by the caller.  The starts-with rule is real
    INSIDE this function and is not the order the caller returns, and the
    one example chosen to justify it was the one that refutes it.  Whether
    a containment hit should ever outrank a close match is a question this
    round did not answer and did not have to, because nothing prints
    either sentence today (see `suggest_gm_scene_names`); it is written
    down here so the next round answers it deliberately.
    """
    hits = [(folded.index(key), folded) for folded in folded_keys if key in folded]
    hits.sort()
    return [folded for _position, folded in hits]
