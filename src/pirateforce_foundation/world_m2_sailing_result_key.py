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
`n_ITEM_ID=3` and `s_OUTFIT=Ocean_Island_000` -- the shape of a per-AREA
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
# pin fails `load_copy()`; a round that edits `AREA_126_SAILING_RESULT_IDS`
# by hand without touching the copy fails the re-derive test -- neither can
# be satisfied by "trust me", same shape as `world_marker_copy.COPY_SHA256`.
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
    return tuple(ids)


# Every `n_ID` this build could use as the record's `+0x14` key: the full set
# of `n_AREA=126` rows in the client's own table.  Loaded once at import,
# from the pinned committed copy -- never from a live `pf_bridge` read, and
# never a hand-typed literal.
AREA_126_SAILING_RESULT_IDS: tuple[int, ...] = _load_ids()


def provisional_area_126_key() -> int:
    """The single lowest `n_ID` among ``AREA_126_SAILING_RESULT_IDS``.

    Kept for a caller that provisions exactly ONE record and has nowhere to
    put a second candidate.  A caller provisioning MORE THAN ONE record --
    this module's actual GT-233 caller included -- must use
    ``provisional_area_126_keys(n)`` instead; see that function's docstring
    for why (pf-adversary, round `wjprxa`, D1: reusing this single value for
    every record throws away the diagnostic COO's own fallback clause was
    written to keep). Never raises past module import.
    """
    return min(AREA_126_SAILING_RESULT_IDS)


def provisional_area_126_keys(count: int) -> tuple[int, ...]:
    """``count`` DISTINCT `+0x14` candidates, one per record a caller is
    about to provision -- the lowest ``count`` `n_ID`s, in ascending order.

    COO-DECISION `20260905_1947` item 2's fallback clause says to use EVERY
    `n_AREA=126` row when the table does not name an island, not to collapse
    to one row and repeat it.  pf-adversary (round `wjprxa`, D1) measured
    what collapsing costs: `GT-233`'s flip carries `COO-DECISION
    20260905_1348`'s standing "no backup boot" rule (RE-265 forbids trying
    a second hypothesis in the same attended run), so if the ONE candidate
    both trial records shared did not resolve inside the client's lookup,
    the round would end with the same silence R318 already measured -- with
    no way to tell "this specific row does not resolve" apart from "the
    whole SAILING_RESULT-key theory is wrong".  Giving each record a
    DIFFERENT row spends the same single attended shot on two rows instead
    of one: a mixed result (one island's dialog pops, the other's does not)
    is itself client-observable evidence about the row, not just the
    mechanism, which a shared value could never produce.

    Raises ``SailingResultCopyError`` if ``count`` exceeds how many distinct
    rows the committed copy actually has -- fail closed rather than repeat a
    row silently, which is the exact mistake this function exists to
    correct. Never picks a row twice.
    """
    if count < 0:
        raise ValueError(f"count must be >= 0, got {count}")
    if count > len(AREA_126_SAILING_RESULT_IDS):
        raise SailingResultCopyError(
            f"asked for {count} distinct SAILING_RESULT keys but the "
            f"committed copy only has {len(AREA_126_SAILING_RESULT_IDS)} "
            "n_AREA=126 rows -- refusing to repeat a row silently"
        )
    return tuple(sorted(AREA_126_SAILING_RESULT_IDS)[:count])
