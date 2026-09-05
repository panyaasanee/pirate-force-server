"""P-3 next step, tried and refused: joining GMUI captions to GMTOOL log types.

`rounds/GM_20260906_0112_dl1etn_...md` (LANE-GM round `dl1etn`) left this as
the next round's cheapest lead: sixteen of the seventeen GMUI rows now have a
real caption (`gmui_catalog.rows_with_a_read_label`), and the client's own
`GMTOOL` text table (`gmui_catalog.log_types()`, 97 rows) is the closest
thing to an enumeration of "what GM operations exist" any committed artifact
carries.  If a row's caption named the same operation as a log type, that
would be a second, independent artifact pointing at the same row -- and
`GMUI_LABEL_BLOCK_ROLES` already warns (`LOG_TYPES_ARE_NOT_BUTTONS`) that a
log type is not itself a button, so a caption/log-type join was never going
to CLOSE a row -- only rank which rows are worth wiring first.

TWO SEARCHES, BOTH REFUSED, FOR DIFFERENT REASONS.

1. WHOLE-STRING JOIN (:data:`CANDIDATES`, :func:`backed_matches`).  Every
   string in the copied GMUI block (all 37 rows: row captions, option text,
   unit suffixes, tab titles -- not only the sixteen row labels) checked
   against all 97 log messages, both directions of substring containment.
   Three hits, and all three trace to one thing: block row 1896 (page-3
   row-5 caption) is a two-word compound, and each half separately equals a
   full log message elsewhere in the table (log ids 4 and 12); one of those
   same words is ALSO the tab-3 title (block row 1891), which is the third
   hit.  A tab title matching a log-type word is not a row-specific signal
   -- every row under that tab would inherit it -- and a compound whose
   both halves are common generic words is not one either.
   :data:`NO_JOIN_SURVIVES_BECAUSE` says so.

2. SUBSTRING-OVERLAP JOIN (:data:`NOTABLE_OVERLAPS`, :func:`rare_overlaps`).
   `pf-adversary` (this round) broke the first search's own domain claim: it
   is not true that no log message shares vocabulary with the GMUI panel
   (an earlier draft of this module said so, and was wrong -- a log message
   names a monster, three name a player).  A whole-string join is blind to a
   shared WORD embedded inside two different longer compounds, so this
   second search finds the longest common substring between every block
   text and every log message and keeps the ones at least
   :data:`_NOTABLE_MIN_LEN` characters long, then reports, for each distinct
   substring found this way, how many of the 97 log messages independently
   contain it -- a substring recurring across many log messages (the panel
   shares vocabulary like "player" or "item" with the table because both
   are about the same game, not because any specific row names any specific
   log type) is noise; one that recurs in at most :data:`_RARE_MAX_LOG_IDS`
   is at least RARE enough to look at by hand.  :func:`rare_overlaps` is
   that filtered list -- four substrings on today's data -- and every one of
   them is read out, by hand, in `docs/GM_LANE.md` (this round's note),
   because a rarity filter can tell "uncommon" from "common", not "the same
   ACTION" from "the same NOUN used for an unrelated action": the one
   candidate with a real English gloss worth naming here is the word this
   table spells for "monster", shared between the GMUI row captioned
   "monster that spawns" and the log message for "monster (loot) drop" --
   two different verbs (spawn vs. drop) attached to the same noun, which is
   why it is filed as read-and-rejected rather than promoted.  Neither
   search's output is ever auto-promoted into :func:`backed_matches`; see
   that function for the bar a round has to clear by hand.

WHY THE DOMAINS MOSTLY DO NOT MEET, STATED PRECISELY THIS TIME.
`gm_tool_log_types.tsv` is 97 rows of item and economy bookkeeping (drops,
guild storage, crystal sockets, item synthesis, dye, casting, pet
satisfaction, market listings -- see
:data:`LOG_TYPE_TABLE_IS_ITEM_ECONOMY_BOOKKEEPING`).  Six GMUI rows this
lane has read name a world/player-administration ACTION with no committed
counterpart anywhere in that table at all -- :data:`ACTION_ROWS_WITH_NO_LOG_MATCH`
lists them by block id, and :func:`_candidates` (search 1) already proves
each has zero whole-caption hits.  What the table does NOT lack is generic
NOUN vocabulary: it names a player (3 messages) and a monster (1 message),
because this is a game with players and monsters, and search 2 above is
what surfaces that without letting it pass for evidence.

WHAT THIS BUYS THE NEXT ROUND.  A negative result recorded in code, not only
prose: :func:`backed_matches` returns empty and is pinned empty by a test, so
a later change to either table that silently produced a real match would be
caught rather than missed.  Both searches are re-run from the live tables
every import (not memorised as a hardcoded verdict), so a future edit to
`gmui_label_block.tsv` or `gm_tool_log_types.tsv` re-asks the same question
against the new data instead of trusting this round's answer forever.
"""
from __future__ import annotations

from dataclasses import dataclass
import re

from . import gmui_catalog
from .gmui_catalog import GMUI_LABEL_BLOCK_ROLES, LABEL_BLOCK

#: What the 97-row GMTOOL log-type table is actually about, named so a
#: reader who has not opened it does not have to guess why the whole-string
#: join comes back nearly empty.  Read off the table itself
#: (`gm_tool_log_types.tsv`), not summarised from memory: item drops and
#: pickups, trading (player, shop, black market, guild storage), crystal-slot
#: sockets, item synthesis, dyeing (equipment and ship), casting, pet
#: satisfaction resets, Gashapon, market stall listings, and item
#: deletion/expiry.  This does NOT mean the table is free of every word the
#: GMUI panel uses -- see the module docstring's search 2 -- it means no
#: message in it is ABOUT a world/player-administration action; see
#: :data:`ACTION_ROWS_WITH_NO_LOG_MATCH` for the specific rows checked.
LOG_TYPE_TABLE_IS_ITEM_ECONOMY_BOOKKEEPING = (
    "gm_tool_log_types.tsv's 97 rows are item and economy audit events "
    "(drops, trades, guild storage, crystal sockets, synthesis, dye, "
    "casting, pet, market); see ACTION_ROWS_WITH_NO_LOG_MATCH for the "
    "specific GMUI actions checked against it and found absent, and the "
    "module docstring's search 2 for why 'absent as an action' is not the "
    "same claim as 'shares no vocabulary at all'"
)

#: The GMUI rows whose caption names a distinct world/player-administration
#: ACTION -- hide, appear, fly-to-scene (x3: scene/NPC/player), summon
#: player, kick player, spawn monster, kill monster, ban chat (x2: by area,
#: by character), change faction -- by `block_id`, English gloss only (no
#: Thai literal on this added .py line; the words are in
#: `gmui_label_block.tsv`, which the ids below index into).  Every one of
#: these produces zero hits in :data:`CANDIDATES` (verified by
#: :func:`test_gm_gmui_log_type_join` in the sibling test file, which reads
#: this tuple rather than repeating it) -- the whole-string join finds no
#: log message that is ABOUT any of these actions.
ACTION_ROWS_WITH_NO_LOG_MATCH = (
    (1386, "hide"),
    (1388, "appear"),
    (1389, "fly to scene"),
    (1393, "fly to NPC"),
    (1394, "fly to player"),
    (1395, "summon player"),
    (1397, "kick player"),
    (1399, "spawn monster"),
    (1400, "kill monster"),
    (1401, "ban chat by area"),
    (1407, "ban chat by character"),
    (1671, "change faction"),
)

_MIN_MATCH_LEN = 2

#: A longest-common-substring hit shorter than this is not worth reporting
#: at all (search 2 below) -- most Thai particles and short grammatical
#: fragments clear this trivially, so the floor exists only to skip
#: single-character noise, not to do the real filtering (that is
#: :data:`_RARE_MAX_LOG_IDS`, on how many log messages independently share
#: the substring found).
_NOTABLE_MIN_LEN = 6

#: A substring recurring in more than this many of the 97 log messages is
#: common vocabulary, not a rare word worth a human reading by hand -- see
#: the module docstring's search 2.  Set to 1 on today's data: it is what
#: separates "monster" (1 message) from "player" (3 messages) or "change"
#: (8 messages), and the next round is free to raise it and re-read the
#: wider set that would produce, but must not lower :func:`rare_overlaps`'s
#: bar in the other direction (auto-promoting) without an attended check --
#: see :func:`backed_matches`.
_RARE_MAX_LOG_IDS = 1


def _normalize(text: str) -> str:
    """Strip the punctuation/whitespace a row caption carries that a log
    message never does (a trailing `:`), so a caption and a log message
    spelling the same word without the colon can still meet."""
    return re.sub(r"[:\s]+", "", text)


def _is_mutual_substring(left: str, right: str) -> bool:
    """True when either string contains the other, in full.

    Split out from the search loop so it can be pinned directly with
    synthetic ASCII strings (see the sibling test file) -- proving BOTH
    directions fire does not need real Thai data, and pinning it against
    real data alone missed that the reverse direction was dead code on
    today's tables (`pf-adversary`, this round).
    """
    return left in right or right in left


def _longest_common_substring(left: str, right: str) -> str:
    """The longest run of characters `left` and `right` share, contiguous.

    Classic O(len(left) * len(right)) dynamic-programming table.  Used only
    by search 2 (:data:`NOTABLE_OVERLAPS`); search 1 needs only whole-string
    containment and does not call this.
    """
    best_len = 0
    best_end = 0
    previous_row = [0] * (len(right) + 1)
    for i, left_ch in enumerate(left, start=1):
        current_row = [0] * (len(right) + 1)
        for j, right_ch in enumerate(right, start=1):
            if left_ch == right_ch:
                current_row[j] = previous_row[j - 1] + 1
                if current_row[j] > best_len:
                    best_len = current_row[j]
                    best_end = i
            else:
                current_row[j] = 0
        previous_row = current_row
    return left[best_end - best_len : best_end]


@dataclass(frozen=True)
class JoinCandidate:
    """One place a GMUI block string and a log message share a substring.

    Every field is re-derived from the pinned tables at import time -- this
    is not a hand-written list, so it cannot go stale silently the way a
    table copied into a letter can.
    """

    block_id: int
    block_role: str
    block_text: str
    log_id: int
    log_type: int
    log_text: str

    @property
    def is_a_tab_title(self) -> bool:
        """True when the GMUI side of the hit is a tab caption, not a row.

        A tab title covers every row under it, so a word it shares with a
        log message is not a signal about any ONE row -- it is the shape a
        coincidence takes, not a row-specific match.
        """
        return self.block_role.endswith(".tab_title")


def _searched_block_ids() -> frozenset[int]:
    """The block ids :func:`_candidates` actually walked to completion.

    Built as a side effect of the same loop (see the last line of that
    loop's body) rather than declared separately, so a mutation that skips
    an id partway through the loop -- rather than shrinking the declared
    search space up front -- still shows up here as a missing id.  This is
    what `pf-adversary` (this round) showed the previous version of this
    module's coverage test could not catch.
    """
    return _SEARCH_RESULT[1]


def _run_whole_string_search() -> tuple[tuple["JoinCandidate", ...], frozenset[int]]:
    """Search 1: every substring hit, plus every block id actually visited.

    Deliberately over-broad on the GMUI side: it checks every row of the
    copied block (captions, option text, unit suffixes, tab titles), not
    only the sixteen row labels, so a real match sitting on an option or a
    unit could not be missed by only looking where this lane expected one.
    """
    hits: list[JoinCandidate] = []
    visited: set[int] = set()
    for block_id, role in GMUI_LABEL_BLOCK_ROLES.items():
        block_text = LABEL_BLOCK[block_id]
        block_norm = _normalize(block_text)
        if len(block_norm) >= _MIN_MATCH_LEN:
            for log_id, log_type, log_text in gmui_catalog.log_types():
                log_norm = _normalize(log_text)
                if len(log_norm) < _MIN_MATCH_LEN:
                    continue
                if _is_mutual_substring(block_norm, log_norm):
                    hits.append(
                        JoinCandidate(
                            block_id=block_id,
                            block_role=role,
                            block_text=block_text,
                            log_id=log_id,
                            log_type=log_type,
                            log_text=log_text,
                        )
                    )
        # Last line of the loop body ON PURPOSE: a mutation that adds an
        # early `continue` for some block id (as `pf-adversary` tried this
        # round) skips this line for that id too, so _searched_block_ids()
        # comes back short and the coverage test below catches it.
        visited.add(block_id)
    return tuple(hits), frozenset(visited)


_SEARCH_RESULT = _run_whole_string_search()
CANDIDATES = _SEARCH_RESULT[0]

#: Why every row in :data:`CANDIDATES` is refused rather than promoted to a
#: real join, named so a reader who greps rather than reads still meets it.
NO_JOIN_SURVIVES_BECAUSE = (
    "all three hits trace to one row (block 1896) whose caption is a "
    "two-word compound of two common, generic words -- one of which is "
    "also the tab-3 TITLE (which covers all five of that tab's rows, so it "
    "cannot be evidence about any one of them).  A compound decomposing "
    "into two words that separately exist elsewhere in a 97-row table is "
    "not a signal beyond name similarity: there is no second, independent "
    "confirmation (no matching id, no matching category, no matching "
    "direction) -- it is a coincidence, not a join; see "
    "LOG_TYPE_TABLE_IS_ITEM_ECONOMY_BOOKKEEPING and "
    "ACTION_ROWS_WITH_NO_LOG_MATCH for why the two tables' domains do not "
    "otherwise meet on any ACTION"
)


def _notable_overlaps() -> dict[str, frozenset[int]]:
    """Every substring of at least :data:`_NOTABLE_MIN_LEN` characters that
    a GMUI block string and a log message share, mapped to EVERY log id (not
    only the one pair it was first found on) that independently contains it.

    This is search 2 from the module docstring: unlike :data:`CANDIDATES`,
    it can find a shared word embedded inside two different longer
    compounds (the whole-string join is blind to that -- `pf-adversary`,
    this round).  The per-substring log-id count is what
    :func:`rare_overlaps` filters on.
    """
    substrings: set[str] = set()
    for block_text in LABEL_BLOCK.values():
        block_norm = _normalize(block_text)
        for _log_id, _log_type, log_text in gmui_catalog.log_types():
            log_norm = _normalize(log_text)
            common = _longest_common_substring(block_norm, log_norm)
            if len(common) >= _NOTABLE_MIN_LEN:
                substrings.add(common)
    return {
        substring: frozenset(
            log_id
            for log_id, _log_type, log_text in gmui_catalog.log_types()
            if substring in _normalize(log_text)
        )
        for substring in substrings
    }


NOTABLE_OVERLAPS = _notable_overlaps()


def rare_overlaps() -> dict[str, frozenset[int]]:
    """:data:`NOTABLE_OVERLAPS` narrowed to substrings recurring in at most
    :data:`_RARE_MAX_LOG_IDS` log messages -- rare enough to be worth a
    human reading it, never rare enough to auto-promote.  See the module
    docstring's search 2 and `docs/GM_LANE.md` (this round) for what each
    one reads as by hand.
    """
    return {
        substring: log_ids
        for substring, log_ids in NOTABLE_OVERLAPS.items()
        if len(log_ids) <= _RARE_MAX_LOG_IDS
    }


#: Block ids a later round has confirmed, by something beyond name
#: similarity, to be the caption of a row whose log type is now named --
#: NOT a table any round may edit on a hunch.  The only way an id belongs
#: here is stated in :func:`backed_matches`.  Empty today: neither search
#: above found a candidate that clears the bar (see
#: :data:`NO_JOIN_SURVIVES_BECAUSE` and :func:`rare_overlaps`), so the set
#: stays empty rather than seeded with a coincidence either search rejected.
_ATTENDED_CONFIRMED_JOINS: frozenset[int] = frozenset()


def backed_matches() -> tuple[JoinCandidate, ...]:
    """Candidates strong enough to rank a row for wiring.  Empty today.

    THE BAR A CANDIDATE WOULD HAVE TO CLEAR, so the next round that adds one
    knows what it is being asked for: not a tab title (see
    :attr:`JoinCandidate.is_a_tab_title`), not a single generic word shared
    with nothing else, and confirmed by something beyond name similarity --
    an id relationship, a category grouping this lane can point at, or
    (best) an attended observation that pressing the row's button produces
    the log-type's `n_LogType` in a server log.  A round that clears the bar
    for a block id adds it to :data:`_ATTENDED_CONFIRMED_JOINS` and writes
    down what cleared it, in the same commit.  Nothing clears it today,
    which is why this returns `()` -- see :data:`NO_JOIN_SURVIVES_BECAUSE`
    and :func:`rare_overlaps`.
    """
    return tuple(
        candidate
        for candidate in CANDIDATES
        if candidate.block_id in _ATTENDED_CONFIRMED_JOINS
    )
