"""LANE-A / M2: the `SAILING_RESULT` key the client's contact tick needs at
record `+0x14`, derived from the client's own table -- never typed in.

WHY THIS FILE EXISTS
---------------------
RE-265 (`pf_bridge/notes_to_chief/
20260905_1932_RE-265-RESULT-COMMON-CONFIRM-OPENS-AFTER-SAILING-RESULT-KEY.md`,
CLOSED BOUNDED-NEGATIVE 2026-09-05T19:32+07:00) found the real gate R318 was
missing: `NavigationExModule_Client`'s contact tick does not open
`Common_Confirm` off the XYZ distance test alone.  It first reads the
record's `+0x14` u16 as a key into a store loaded from the client table named
`SAILING_RESULT`; a null lookup (the trial's own `+0x14=0`) exits BEFORE the
distance test ever runs, which is exactly the silence R318 measured.  Only a
key that resolves to a real row reaches the XYZ compare and, within 500
units, the dialog.

COO-DECISION `20260905_1947` (`pf_bridge/notes_to_chief/
20260905_1947_COO-DECISION-re265-answered-m2-blocker-is-sailing-result-key-
lane-a-builder-pr-plus-gt-same-round-1951-due-2121-LANE-A.md`) item 2 orders
this record's `+0x14` filled with an `n_ID` from
`gamedata/tables/CONSTDATA_TH__SAILING_RESULT.tsv` where `n_AREA=126` --
"read `n_VARI_*`/`n_EVENT`, do NOT guess, do NOT hardcode a number that is
not derived from the TSV -- if the table does not name an island, use every
`n_AREA=126` row whose `n_EVENT` matches, and record it as provisional".

WHAT THE TABLE ACTUALLY SAYS, READ RATHER THAN ASSUMED
---------------------------------------------------------
It does not name an island.  All 18 `n_AREA=126` rows share `n_EVENT=2`,
`n_VARI_3=3` and `s_OUTFIT=Ocean_Island_000` -- the shape of a per-AREA
random-encounter/loot table (`n_WEIGHT`/level-bound columns, distinct
`n_VARI_1` per row), not a per-DESTINATION dock table.  `n_AREA` values
elsewhere in the same file are 127/128/129/304/305 -- other sea panels this
project already tracks (NOW.md: Bermuda/Bg3002, the 304/305 sea-edge
crossing) -- one more agreement that this table's key is "which sea AREA",
not "which island inside it".  So COO's own fallback clause is the live
case, not a hedge: every `n_AREA=126` row is an equally valid, equally
unweighted key for the gate this file exists to satisfy, and this module
follows the ruling's instruction literally rather than picking a favourite.

NONCLAIM: this does not prove `+0x14` is the destination island, or that the
client cares which of the 18 rows it names -- RE-265 nonclaim 1 already
forbids reading island/scene/Trigger-TIP meaning into it.  All this module
proves is that the value it returns is a REAL key in the table the client's
own tick looks up, which is the one thing RE-265 measured the gate needs.

WHY A COMMITTED COPY, NOT A LIVE READ OF `pf_bridge/gamedata/`
------------------------------------------------------------------
Same discipline as `world_marker_copy.py`: this server repository does not
depend on the bridge tree at runtime, and a live read would make the
provisioned key differ by which machine composed the frame.  The 18 rows
this module actually needs are copied verbatim into
`world_data/world_sailing_result_area126.tsv`, `COPY_SHA256` pins that copy's
own bytes, and `tests/test_world_m2_sailing_result_key.py` re-derives the
same 18 rows straight from the bridge source
(`@BRIDGE_GAMEDATA.skip_unless_present()`) and fails red if they disagree --
so a forged row costs two files, not one, exactly the property
`world_marker_copy.py`'s own docstring proves is the reachable bar, not "the
gate now checks the client data" outright.

WHY THE ROWS ARE LOADED LAZILY, NOT AT MODULE SCOPE (D1, pf-adversary round
`tk4hr7`) -- this module used to bind ``AREA_126_SAILING_RESULT_IDS`` at
IMPORT time, which meant every boot of this repository, flagged or not,
had to successfully hash and parse the committed copy before `runtime.py`
(which imports the provisioning-trial composer, which imports this module)
could finish importing at all.  A corrupted or moved copy raised
``SailingResultCopyError`` before any `try`/`except` around the one caller
that actually needs this value ever got a chance to run -- the server would
not boot AT ALL, on Panya's machine or anyone else's, over a file nothing
but a single no-backup attended trial reads.  `world_marker_copy.py` never
makes this mistake: none of its rows are bound at module scope, every
`derive_*`/`shortcut_*` function calls `load_copy()` itself, on demand.
``area_126_sailing_result_ids()`` below follows the same shape: it re-reads
and re-verifies the committed copy on every call rather than caching a
module-scope binding, so an import of this module can never fail on a bad
copy -- only a call into a function that actually needs the rows can.
"""
from __future__ import annotations

from pathlib import Path
import csv

# Convention marker, same as every other always-on module in this package.
# Nothing here is behind a scenario flag and nothing here sends a frame.
production_allowed = True

COPY_PATH = Path(__file__).parent / "world_data" / "world_sailing_result_area126.tsv"

# The digest of the committed copy (`sha256sum` of the file as it sits in
# git, LF line endings).  A round that edits the copy without updating this
# pin fails `load_copy()`; a round that edits what
# `area_126_sailing_result_ids()` returns by hand without touching the copy
# fails the re-derive test -- neither can be satisfied by "trust me", same
# shape as `world_marker_copy.COPY_SHA256`.
COPY_SHA256 = "5c96db08b848a679b7cfe8dafc65beaafc5c4dffd304cfa5f1d13b00184fe55e"

# The one source file this copy is curated from.
SAILING_RESULT_TSV = "pf_bridge/gamedata/tables/CONSTDATA_TH__SAILING_RESULT.tsv"

# The sea scene (`world_m2_survey_plan.XYZ_FRAME_SCENE_ID`) this key is
# provisioned for.  Not imported from that module -- this file has no other
# reason to depend on the survey plan, and the number is the client table's
# own `n_AREA` column, not a borrowed constant.
SAILING_RESULT_AREA = 126

# The `n_EVENT` every `n_AREA=126` row shares.  Named so a caller can assert
# it rather than re-deriving it from raw text; a table update that splits
# scene 126 into more than one event value would want a human to look at it,
# not a silent join on a value that stopped being constant.
SAILING_RESULT_EVENT = 2


class SailingResultCopyError(RuntimeError):
    """The committed copy is missing, altered, or disagrees with this
    module's own pin.  RuntimeError, not LookupError: this is never "area 126
    has no rows", it is always "the artifact this module is supposed to be
    reading is not the artifact that is here"."""


def _read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def curate(tables_dir: Path | str) -> str:
    """Build the copy's exact text from a bridge ``gamedata/tables`` dir.

    Returns text rather than writing a file, so a caller (the regeneration
    command below, or a test) can compare it with the committed bytes
    without touching the working tree.
    """
    source = Path(tables_dir) / Path(SAILING_RESULT_TSV).name
    rows = _read_tsv(source)
    header = list(rows[0].keys()) if rows else []
    lines = ["\t".join(header)]
    for row in rows:
        if row["n_AREA"] != str(SAILING_RESULT_AREA):
            continue
        lines.append("\t".join(row[key] for key in header))
    return "\n".join(lines) + "\n"


# Regenerate with (from a checkout that has `pf_bridge` beside this repo):
#
#   py -3 -c "import pathlib, sys; sys.path.insert(0, 'src'); \
#     from pirateforce_foundation.world_m2_sailing_result_key import curate; \
#     pathlib.Path('src/pirateforce_foundation/world_data/' \
#       'world_sailing_result_area126.tsv').write_text( \
#       curate('../pf_bridge/gamedata/tables'), encoding='utf-8', newline='')"
#
# then update COPY_SHA256 in this file in the SAME commit
# (`sha256sum src/pirateforce_foundation/world_data/
# world_sailing_result_area126.tsv`).  `newline=''` is load-bearing, not
# decoration -- same reason `world_marker_copy.py` spells it out.


def load_copy() -> tuple[dict[str, str], ...]:
    """The committed copy's rows, verified against ``COPY_SHA256`` first.

    Raises ``SailingResultCopyError`` rather than returning a possibly-wrong
    answer if the file on disk is missing or has drifted from the pin.
    """
    import hashlib

    if not COPY_PATH.exists():
        raise SailingResultCopyError(f"missing committed copy: {COPY_PATH}")
    raw = COPY_PATH.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != COPY_SHA256:
        raise SailingResultCopyError(
            f"{COPY_PATH} sha256 {digest} != pinned {COPY_SHA256}; "
            "regenerate with curate() and update COPY_SHA256 together"
        )
    return tuple(
        csv.DictReader(raw.decode("utf-8").splitlines(), delimiter="\t")
    )


def _load_ids() -> tuple[int, ...]:
    rows = load_copy()
    ids: list[int] = []
    for row in rows:
        if row["n_AREA"] != str(SAILING_RESULT_AREA):
            raise SailingResultCopyError(
                f"committed copy carries a row outside n_AREA="
                f"{SAILING_RESULT_AREA}: {row!r}"
            )
        if row["n_EVENT"] != str(SAILING_RESULT_EVENT):
            raise SailingResultCopyError(
                f"committed copy carries a row whose n_EVENT is not "
                f"{SAILING_RESULT_EVENT}: {row!r}"
            )
        ids.append(int(row["n_ID"]))
    if not ids:
        raise SailingResultCopyError(
            "committed copy has no rows -- the provisional key has no source"
        )
    if len(ids) != len(set(ids)):
        # D7, pf-adversary round `tk4hr7`: `provisional_area_126_key()`'s own
        # docstring (and the row-discriminating design it used to back)
        # promises a real, distinct row id -- a promise that held only
        # because today's 18 rows happen to be distinct (enforced by a
        # SIBLING test, `AreaIdsTests.test_ids_are_unique`, not by this
        # function itself). A future table update that duplicates an
        # `n_ID` would pass this loop silently; checking `len(set())`
        # rather than `len()` makes that fail here instead.
        raise SailingResultCopyError(
            f"committed copy carries a duplicate n_ID among {ids!r}"
        )
    return tuple(ids)


def area_126_sailing_result_ids() -> tuple[int, ...]:
    """Every `n_ID` this build could use as the record's `+0x14` key: the
    full set of `n_AREA=126` rows in the client's own table.

    Re-read and re-verified from the pinned committed copy on EVERY call --
    never cached at module scope (D1, pf-adversary round `tk4hr7`: binding
    this at import time meant a corrupted or missing copy took the whole
    server down on boot, flagged or not, instead of failing only the one
    caller that needs it; see the module docstring).  Never from a live
    `pf_bridge` read, and never a hand-typed literal.
    """
    return _load_ids()


def provisional_area_126_key() -> int:
    """The single lowest `n_ID` among ``area_126_sailing_result_ids()``.

    This is the "the key is `n_ID`" hypothesis's one representative value --
    see ``column_discriminating_keys`` for how it is paired with
    ``n_area_key()`` to test that hypothesis against its alternative in the
    same attended shot. Never raises past module import (there is no module
    import left to raise past; a bad copy now raises on the FIRST call
    into this function, not on `import`).
    """
    return min(area_126_sailing_result_ids())


def n_area_key() -> int:
    """`SAILING_RESULT_AREA` (126) itself, as a `+0x14` candidate.

    The "the key is `n_AREA`" hypothesis's one representative value --
    RE-265 measured that `+0x14` is looked up in a store built from the
    client's `SAILING_RESULT` table, but never proved WHICH column that
    store is keyed by (round `tk4hr7`, D3: `n_ID` was assumed, not
    measured). `n_AREA` is the one other column every row in the committed
    copy agrees on, so it is the cheapest second hypothesis available
    without inventing a composite or packed-index key nothing in this
    repository has evidence for.
    """
    return SAILING_RESULT_AREA


def column_discriminating_keys(count: int) -> tuple[int, ...]:
    """``count`` `+0x14` candidates, each testing a DIFFERENT hypothesis
    about WHICH COLUMN of `SAILING_RESULT` the client's store is keyed by --
    not different ROWS of the same column.

    COO-DECISION `20260905_2349` item 1 (GT-233 v3, option (ข)) supersedes
    the row-discriminating design this function replaces
    (`provisional_area_126_keys`, pf-adversary round `wjprxa` D1): that
    design gave the trial's two records two DIFFERENT `n_ID`s, which only
    ever tested "is the key `n_ID`, and if so which row" -- it had no way to
    come back positive if the store turns out to be keyed by `n_AREA`, or
    anything else, instead (round `tk4hr7`, D3: RE-265 never measured which
    column is the key, and COO's own `1348` "no backup boot" rule means
    `GT-233` gets exactly one attended shot at this, not one shot per
    hypothesis).

    So instead the two candidates now spend that one shot on two hypotheses:

    * ``count == 1``: ``(provisional_area_126_key(),)`` -- the "key is
      `n_ID`" hypothesis alone, for a caller provisioning exactly one
      record.
    * ``count == 2``: ``(provisional_area_126_key(), n_area_key())`` -- the
      "key is `n_ID`" and "key is `n_AREA`" hypotheses, one per record.
      `GT-233`'s two records (dock 153 / Prison Exile gets the `n_ID`
      candidate, dock 154 / Spice Paradise gets the `n_AREA` candidate) is
      this trial's only consumer today.

    A count of 2 also closes D8 (pf-adversary round `tk4hr7`): the OLD
    scheme's two lowest `n_ID`s (1, 2) put island 3's key exactly equal to
    island 2's OTHER field (`+0x12` = the `survey_id` echoed at contact,
    2 and 3 for the two docks) -- a client response naming "2" could not
    be told apart from "the `n_ID`=2 key resolved" versus "the `+0x12`=2
    field is what the client actually read".  The new values (the lowest
    `n_ID`, today `1`, and `n_AREA` = `126`) match neither dock's `+0x12`
    (`2`/`3`), so a resolved lookup can only ever be read as evidence about
    the column this function was asked to discriminate.

    A silent result on BOTH records is NOT evidence that the whole
    `SAILING_RESULT`-key theory is wrong -- it means the column is still
    unknown (composite key, packed index, or a column this TSV export does
    not carry); see the `GT-233` v3 ticket for the sentence this exists to
    keep a no-backup attended round from over-reading.

    Any other ``count`` raises: this function tests a fixed pair of named
    hypotheses, it does not generalise to "N distinct candidates" the way
    the row-discriminating design it replaces did, and a caller asking for
    more would get candidates this function has no third hypothesis to
    justify.
    """
    if count < 0:
        raise ValueError(f"count must be >= 0, got {count}")
    if count == 0:
        return ()
    if count == 1:
        return (provisional_area_126_key(),)
    if count == 2:
        n_id_candidate = provisional_area_126_key()
        n_area_candidate = n_area_key()
        if n_id_candidate == n_area_candidate:
            # Cannot happen with today's data (n_ID in 1..18, n_AREA=126),
            # but a table update could change either -- fail closed rather
            # than silently hand the trial two records with the same
            # candidate, which would collapse back to the one-hypothesis
            # mistake this function exists to correct.
            raise SailingResultCopyError(
                f"n_ID candidate {n_id_candidate} == n_AREA candidate "
                f"{n_area_candidate}; the two column hypotheses are no "
                "longer distinguishable -- refusing to test one row twice"
            )
        return (n_id_candidate, n_area_candidate)
    raise ValueError(
        f"column_discriminating_keys tests exactly two named hypotheses "
        f"(n_ID, n_AREA); asked for {count} candidates"
    )
