"""The client's MARKER crosswalk, committed here so the GATE can check it.

WHY THIS FILE EXISTS, AND IT IS NOT A CONVENIENCE.  ``world_scene_marker.py``
pins 13 arrival points and six measured totals, and every one of them was
transcribed by hand from two TSVs that live in the BRIDGE repository.  The
only thing tying those literals to the client was
``MarkerReverificationOnTheBridgeTest``, which is
``@BRIDGE_GAMEDATA.skip_unless_present()`` -- a DECLARED SKIP on the machine
that decides whether a change merges.  pf-adversary measured what that costs
(round ``8ubiku2``, E1): on a clone without ``pf_bridge`` beside it, forge a
coordinate in ``_ROWS``, update the by-value pin to match, move the registry
spawn to match, and the suite is GREEN.  The forged point then carries source
``client_marker_table`` and the loader certifies it.

``COO-DECISION 20260829_0941`` (mailbox ``20260829_0941_COO-DECISION-the-gate-
gets-a-committed-copy-and-a-digest-test.md``) approved the fix in two parts,
and this module is both of them:

1. the rows of the client tables that this project actually uses are copied
   into ``world_data/world_marker_crosswalk.json``, with the ``sha256`` of each
   FULL source file beside them, as DATA rather than as code; and
2. a plain test -- not a workflow, so it runs everywhere including
   ``gate-windows`` -- re-derives ``_ROWS`` from that committed copy and goes
   red when the two disagree.  ``tests/test_world_marker_copy.py`` is that
   test and it carries NO skip decorator.

HOW FAR THIS ACTUALLY REACHES, STATED BEFORE ANYONE QUOTES IT.  What the gate
can now prove is that ``world_scene_marker._ROWS``, the six totals beside it,
the two shortcut examples and the three degenerate-origin rows are a faithful
projection of a COMMITTED artifact whose bytes are pinned by ``COPY_SHA256``.  What the gate still
cannot prove is that the committed artifact matches the client, because the
client's tables are not in this repository and nothing here can reach them.
That last hop is still the bridge's, and it is now ONE command against ONE
file instead of a tree walk: ``verify_against_sources()`` re-curates from the
bridge tree and compares bytes.

So the honest description of the change is narrower than "the gate now checks
the client data", and this docstring says the narrower thing on purpose.

~~Before: forging a coordinate cost THREE hand-typed literals ... After ...
Four coordinated edits ... and each verbatim row carries its 1-based source
line number so a reviewer with the bridge tree falsifies the whole thing with
``sed -n '<line>p'``.~~  **STRUCK, MEASURED FALSE BY pf-adversary IN THE ROUND
THAT WROTE IT (round i8timv, D1 and D6), BEFORE THE PR LEFT DRAFT.**  Three
things were wrong with that paragraph and all three flattered this round:

* **"the verbatim row in the copy" and "that row's RAW u32 text" are THE SAME
  EDIT.**  There is no signed number anywhere in the JSON; the raw u32 text IS
  the verbatim row.  A list of four was a list of three.
* **The before-count and the after-count were not counting the same things**,
  so subtracting them was meaningless.  Executed end to end, the forgery that
  round ``8ubiku2`` measured now costs FIVE edits, four of them hand-typed:
  ``_ROWS``, the by-value literal in ``tests/test_world_scene_marker.py``, the
  registry spawn in ``scenarios/world_scene_registry_001.json``, the verbatim
  row here - and then ``COPY_SHA256``, which is not typed but computed with one
  ``sha256sum``.  **The honest delta this round bought is +1 hand-typed literal
  and one mechanical hash.**  pf-adversary ran it: 4419 passed, 385 skipped,
  byte-identical to the unforged baseline, forged point still labelled
  ``client_marker_table``.
* **"a second number system" is false for half the table.**  Scene 14's ``n_Y``
  is ``18989`` in the file and ``18989`` in the module.  Only negative
  coordinates differ, and there the conversion is one expression.
* **"falsifies the whole thing with sed" is false for the six TOTALS.**  Line
  numbers exist for the 18 verbatim rows only.  The 661 index pairs carry none,
  so a wrong total is caught by internal literals, not by an external anchor.

What is left after all that is smaller and still worth having: an ACCIDENT -
a typo, a bad merge, a half-finished edit - cannot survive at all, where before
it could; and a deliberate forgery has to touch one more file and leave it in
the diff.  That is the claim.  ``VERIFICATION_REACH`` in ``world_scene_marker``
carries the same sentence and a test asserts its wording, because the previous
version of that constant was the most-quoted and least-checked string in the
lane.

THE QUESTION THIS DESIGN DOES NOT ANSWER, RECORDED BECAUSE IT IS THE REAL ONE.
``COPY_SHA256``, this JSON, and both source-table hashes are all literals in
one repository, written by one lane, in one commit.  Every artifact the gate
compares is authored by the party being audited; what changed is how many
places that party must write the same number.  A lock is only a lock if the
other party can lose it.  Anchoring this outside the lane needs something the
lane cannot write in the same commit - a gate-time fetch of the client table,
a signature, or a second party's countersignature - and that is a project-level
choice, asked in
``pf_bridge/notes_to_chief/20260829_1126_LANE-A-ASK-COO-what-can-a-lane-not-write.md``.

WHAT IS COPIED, AND WHY IT IS NOT THE WHOLE TABLE.  The ruling says to curate
the rows this project actually uses.  Taken literally that is 15 marker rows,
which would leave the six TOTALS (271 scenes, 390 markers, 19 self-numbered
rows, 258 marker-less scenes, 257 the shortcut invents a point for, 3 that
survive the back-pointer check) checkable only on the bridge -- and those
totals are exactly what a docstring got wrong by a factor of 36 two rounds
ago.  So the copy keeps:

* the COLUMNS every total is computed from, for ALL rows -- ``(n_ID,
  n_MARKER)`` for the 271 scenes and ``(n_ID, n_SCENE)`` for the 390 markers.
  Two small integers per row, no coordinates, no names, no music files;
* the FULL row, verbatim, for the 18 markers this project quotes a coordinate
  from -- the 13 arrival points, ``MARKER[130]`` and ``MARKER[17]`` (the two
  rows the prohibition in rule 2 is argued from), and ``MARKER[126..128]``,
  added in this round's adversary pass because ``world_scene_marker`` states
  those three are "the degenerate (0, 0, z) origin" and pf-adversary (D9)
  measured that the claim was the one line of the totals block still resting
  on nothing a gate could check.

~~[LANE-A READING OF AN APPROVED RULING -- AWAITING COO CONFIRMATION]~~
**CONFIRMED BY COO 2026-08-29T12:41+07:00**, consumed by LANE-A round
``drrnpu``: ``pf_bridge/notes_to_chief/20260829_1241_COO-DECISION-curated-
copy-keeps-the-used-columns.md`` approves option 2 - the copy keeps the 15
full rows AND the used columns of every row - and says explicitly that
nothing is to be reverted.  Keeping two columns of every row is this lane's
reading of "the rows actually used", on the ground that a total IS a use of a
row.  The narrower reading (15 rows and nothing else) was the alternative the
letter offered; it is now refused rather than pending, so a later round that
finds this paragraph must not "tidy" ``curate()`` down to it.  The letter
asking was ``pf_bridge/notes_to_chief/20260829_1038_LANE-A-ASK-COO-what-a-
curated-copy-should-keep.md``.

WHAT THIS MODULE IS NOT.  It is not on the boot path and it must not become
so: ``build_foundation_release.py`` collects ``src/**/*.py`` and nothing else,
so a module that read this JSON at import would boot fine here and die in the
release archive.  ``world_scene_marker`` therefore keeps its literals and this
module is imported by tests and by bridge-side tooling only.
"""
from __future__ import annotations

from pathlib import Path
import csv
import hashlib
import json

# Convention marker, same as every other always-on module in this package.
# Nothing here is behind a scenario flag and nothing here sends a frame.
production_allowed = True

COPY_PATH = Path(__file__).parent / "world_data" / "world_marker_crosswalk.json"

# The digest of the committed copy.  This is part 2 of the ruling: a round that
# edits world_scene_marker._ROWS and leaves the copy alone fails the re-derive
# test, and a round that edits the copy and leaves this pin alone fails
# load_copy().  Neither can be satisfied by "updating the pin to match myself"
# without the change appearing in the diff of BOTH files.
COPY_SHA256 = "ee4f601f215a70547230f9bc3657111f0acfbfc29f0649dbef1236bf0f2f65da"

# The two source files, named the way the rest of this package names them.
SCENE_NAME_TSV = "pf_bridge/gamedata/tables/CONSTDATA_TH__SCENE_NAME.tsv"
MARKER_TSV = "pf_bridge/gamedata/tables/CONSTDATA_TH__MARKER.tsv"

# The 18 marker rows kept verbatim: the 13 a scene names, the two the
# prohibition is argued from, and the three the totals block describes.
# 130 is the row the shortcut hands scene 130 (it belongs to scene 2), 17 is
# the row it hands the sea, and 126/127/128 are the three that survive the
# back-pointer check - world_scene_marker calls them the degenerate (0, 0, z)
# origin, and until pf-adversary's D9 in this round that sentence was the one
# claim in the totals block no machine could check.
QUOTED_MARKER_IDS = (
    1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 14, 17, 126, 127, 128, 130, 1000,
)


# Sentinel used only inside curate(): the two index arrays are substituted into
# the rendered JSON one PAIR per line.  Plain ASCII on purpose - a control
# character would be re-escaped by json.dumps and the replace would miss.  The
# substitution matches the full quoted token, so it cannot hit real data.
_PAIRS_PLACEHOLDER = "__PF_PAIRS__"


class MarkerCopyError(RuntimeError):
    """The committed copy is missing, altered, or disagrees with the module.

    RuntimeError rather than LookupError: this is never a "that scene has no
    marker" answer, it is always "the artifact this repository is supposed to
    be checking against is not the artifact that is here".
    """


def s32(value: object) -> int:
    """The client's u32 columns read as two's-complement int32.

    Kept here as well as in the re-derivation script because the copy stores
    the RAW unsigned text: scene 1's ``n_X`` is ``4294956974`` in the file and
    ``-10322`` in the module, and the conversion is the thing being checked,
    not an implementation detail to be hidden behind a pre-signed number.
    """
    number = int(value)  # type: ignore[arg-type]
    return number - (1 << 32) if number >= (1 << 31) else number


def _read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def curate(tables_dir: Path | str) -> str:
    """Build the copy's exact JSON text from a bridge ``gamedata/tables`` dir.

    This is the generator, and it is the reason the copy is not hand-typed.
    Returns text rather than writing a file so a caller can compare it with
    the committed bytes without touching the working tree -- which is what
    ``verify_against_sources()`` does.
    """
    tables = Path(tables_dir)
    scene_path = tables / Path(SCENE_NAME_TSV).name
    marker_path = tables / Path(MARKER_TSV).name
    scene_rows = _read_tsv(scene_path)
    marker_rows = _read_tsv(marker_path)
    # 1-based line number in the source file, captured while walking it: the
    # header is line 1 and the rows follow in file order, so a reviewer on the
    # bridge checks a row with sed -n '<line>p' and never has to trust this
    # file's ordering.  Taken from enumerate rather than from list.index(row),
    # which the first draft used: index() returns the FIRST equal row, so two
    # byte-identical rows in a future table would silently point one of them at
    # the other's line, and the cross-check test could not see it because the
    # two rows agree on everything it compares (pf-adversary, round i8timv,
    # D11).  No duplicate exists in today's 390 rows; this is the guard for the
    # table that changes.
    marker_by_id: dict[int, tuple[int, dict[str, str]]] = {}
    for offset, row in enumerate(marker_rows):
        marker_id = int(row["n_ID"])
        if marker_id in marker_by_id:
            raise MarkerCopyError(
                f"marker id {marker_id} appears twice in {marker_path.name}; "
                "the crosswalk cannot say which row a scene named"
            )
        marker_by_id[marker_id] = (2 + offset, row)

    scene_index = [
        (int(row["n_ID"]), int(row["n_MARKER"])) for row in scene_rows
    ]
    marker_index = [
        (int(row["n_ID"]), int(row["n_SCENE"])) for row in marker_rows
    ]

    verbatim: dict[str, dict[str, object]] = {}
    for marker_id in QUOTED_MARKER_IDS:
        line_number, row = marker_by_id[marker_id]
        verbatim[str(marker_id)] = {
            "source_line": line_number,
            "raw": {key: row[key] for key in ("n_ID", "n_SCENE", "n_X", "n_Y",
                                              "n_Z", "n_DIRTECTION")},
        }

    document = {
        "_what_this_is": (
            "A curated projection of two client tables "
            "(CONSTDATA_TH__SCENE_NAME.tsv and CONSTDATA_TH__MARKER.tsv), "
            "committed so that the merge gate can check "
            "src/pirateforce_foundation/world_scene_marker.py against "
            "something other than itself. Data only: no module reads this at "
            "import time."
        ),
        "_who_updates_this_and_when": (
            "LANE-A owns this file. It is regenerated, never hand-edited, and "
            "only from a bridge working tree. Use the project's pinned "
            "interpreter (py -3 on the bridge, python3 elsewhere) and note "
            "newline='' - it is load-bearing, not decoration: "
            "py -3 -c \"import pathlib, sys; "
            "sys.path.insert(0, 'src'); "
            "from pirateforce_foundation.world_marker_copy import curate; "
            "pathlib.Path('src/pirateforce_foundation/world_data/"
            "world_marker_crosswalk.json').write_text("
            "curate('../pf_bridge/gamedata/tables'), encoding='utf-8', "
            "newline='')\" "
            "-- then update COPY_SHA256 in world_marker_copy.py in the SAME "
            "commit. WITHOUT newline='' this command writes CRLF on Windows, "
            "the pin you compute is the CRLF digest, .gitattributes normalizes "
            "the committed blob back to LF, and every test goes red on the "
            "gate for a reason invisible on your own machine (pf-adversary, "
            "round i8timv, D4: the CRLF file even PASSED the old "
            "verify_against_sources, which compared text and not bytes). "
            "When the client's tables change, the source sha256 values "
            "below stop matching and that regeneration is mandatory before any "
            "round may quote a marker coordinate again. A hand edit to this "
            "file is a defect even when the numbers in it are right, because "
            "the point of the file is that nobody typed it."
        ),
        "_what_it_does_not_prove": (
            "That these bytes match the client. Only a bridge run of "
            "world_marker_copy.verify_against_sources() proves that. What the "
            "gate proves is that world_scene_marker agrees with THIS file."
        ),
        "schema_version": 1,
        "source": {
            "scene_name": {
                "path": SCENE_NAME_TSV,
                "sha256": hashlib.sha256(scene_path.read_bytes()).hexdigest(),
                "row_count": len(scene_rows),
                "columns_kept": ["n_ID", "n_MARKER"],
            },
            "marker": {
                "path": MARKER_TSV,
                "sha256": hashlib.sha256(marker_path.read_bytes()).hexdigest(),
                "row_count": len(marker_rows),
                "columns_kept": ["n_ID", "n_SCENE"],
                "rows_kept_in_full": list(QUOTED_MARKER_IDS),
            },
        },
        "scene_marker_index": _PAIRS_PLACEHOLDER + "scene_marker_index",
        "marker_scene_index": _PAIRS_PLACEHOLDER + "marker_scene_index",
        "marker_rows_verbatim": verbatim,
    }
    text = json.dumps(document, indent=1, ensure_ascii=True, sort_keys=False)
    # The two index arrays are 661 pairs.  Rendered by json.dumps at indent=1
    # they become 3300 lines of one integer each, which is a data file no
    # reviewer can read and a diff nobody will scroll.  They are rendered one
    # PAIR per line instead - still valid JSON, still one line per row of the
    # client's table, and a human can now scan for the row they care about.
    for key, pairs in (("scene_marker_index", scene_index),
                       ("marker_scene_index", marker_index)):
        rendered = "[\n" + ",\n".join(
            f"  [{left}, {right}]" for left, right in pairs
        ) + "\n ]"
        text = text.replace(f'"{_PAIRS_PLACEHOLDER}{key}"', rendered)
    return text + "\n"


def load_copy() -> dict[str, object]:
    """The committed copy, refused if its bytes are not the pinned bytes."""
    try:
        raw = COPY_PATH.read_bytes()
    except FileNotFoundError as exc:
        # No "pragma: no cover" here.  The first draft carried one saying "the
        # file is committed", which was wrong twice: the branch IS covered by
        # test_a_missing_copy_is_an_error_and_not_an_empty_answer, and the file
        # is NOT present in the release archive, which collects src/**/*.py and
        # no data (pf-adversary, round i8timv, D8).
        raise MarkerCopyError(
            f"the committed marker crosswalk is missing at {COPY_PATH}"
        ) from exc
    actual = hashlib.sha256(raw).hexdigest()
    if actual != COPY_SHA256:
        raise MarkerCopyError(
            f"world_marker_crosswalk.json sha256 mismatch: pinned "
            f"{COPY_SHA256}, found {actual}. The copy was edited without "
            "moving COPY_SHA256, or COPY_SHA256 was moved without "
            "regenerating the copy. Regenerate from the bridge tree; do not "
            "type either one by hand."
        )
    return json.loads(raw.decode("utf-8"))


def derive_rows(copy: dict[str, object] | None = None) -> tuple[
    tuple[int, int, int, int, int, int, int], ...
]:
    """Re-derive ``world_scene_marker._ROWS`` from the committed copy.

    Same crosswalk the client's data forces: ``SCENE_NAME[n].n_MARKER`` first,
    then ``MARKER[that id]``, and the marker row's own ``n_SCENE`` carried
    through as a third column so the caller can check the back-pointer against
    a transcribed value instead of against itself.
    """
    document = load_copy() if copy is None else copy
    verbatim = document["marker_rows_verbatim"]  # type: ignore[index]
    derived: list[tuple[int, int, int, int, int, int, int]] = []
    for scene_id, marker_id in document["scene_marker_index"]:  # type: ignore[index]
        if not marker_id:
            continue
        row = verbatim[str(marker_id)]["raw"]  # type: ignore[index]
        derived.append((
            scene_id,
            marker_id,
            int(row["n_SCENE"]),
            s32(row["n_X"]),
            s32(row["n_Y"]),
            s32(row["n_Z"]),
            int(row["n_DIRTECTION"]),
        ))
    return tuple(derived)


def derive_census(copy: dict[str, object] | None = None) -> dict[str, object]:
    """Re-derive every TOTAL ``world_scene_marker`` states, from the copy.

    These are the numbers a docstring got wrong by a factor of 36 in round
    ``8ubiku``; computing them here means the gate re-computes them on every
    run instead of a bridge round eventually noticing.
    """
    document = load_copy() if copy is None else copy
    scene_index = [tuple(pair) for pair in document["scene_marker_index"]]  # type: ignore[index]
    marker_index = [tuple(pair) for pair in document["marker_scene_index"]]  # type: ignore[index]
    marker_scene_by_id = {marker_id: scene for marker_id, scene in marker_index}
    marker_less = [scene for scene, marker in scene_index if not marker]
    invents = [scene for scene in marker_less if scene in marker_scene_by_id]
    return {
        "scene_row_count": len(scene_index),
        "marker_row_count": len(marker_index),
        "scenes_with_a_marker": sum(1 for _, marker in scene_index if marker),
        "marker_rows_whose_id_equals_their_scene": sum(
            1 for marker_id, scene in marker_index if marker_id == scene
        ),
        "marker_less_scenes": len(marker_less),
        "scenes_the_shortcut_would_invent_a_point_for": len(invents),
        "shortcut_survives_the_back_pointer_check": tuple(sorted(
            scene for scene in invents if marker_scene_by_id[scene] == scene
        )),
        "marker_row_at_scene_130_belongs_to": marker_scene_by_id[130],
    }


def shortcut_survivor_points(copy: dict[str, object] | None = None) -> tuple[
    tuple[int, int, int, int], ...
]:
    """The XYZ of markers 126/127/128, the three the back-pointer check misses.

    ``world_scene_marker`` says in prose that all three are "the degenerate
    (0, 0, z) origin".  Until this round the copy kept no coordinates for them,
    so that sentence was the one line of the totals block a gate could not
    check - true, and resting on nothing (pf-adversary, round i8timv, D9).
    Returns ``(marker id, x, y, z)`` ascending.
    """
    document = load_copy() if copy is None else copy
    verbatim = document["marker_rows_verbatim"]  # type: ignore[index]
    survivors = []
    for marker_id in sorted(
        int(k) for k in verbatim if int(k) in (126, 127, 128)
    ):
        row = verbatim[str(marker_id)]["raw"]  # type: ignore[index]
        survivors.append((marker_id, s32(row["n_X"]), s32(row["n_Y"]),
                          s32(row["n_Z"])))
    return tuple(survivors)


def shortcut_at_scene_17(copy: dict[str, object] | None = None) -> tuple[
    int, int, int, int
]:
    """What indexing ``MARKER`` by scene id hands the sea: scene 126's row."""
    document = load_copy() if copy is None else copy
    row = document["marker_rows_verbatim"]["17"]["raw"]  # type: ignore[index]
    return (int(row["n_SCENE"]), s32(row["n_X"]), s32(row["n_Y"]),
            s32(row["n_Z"]))


def verify_against_sources(tables_dir: Path | str) -> None:
    """The bridge-side hop this repository cannot do: copy vs client tables.

    Raises ``MarkerCopyError`` naming the first disagreement.  A round that
    gets a raise here has found drift between the committed copy and the
    client's shipped data and must regenerate, never edit either side to
    agree.

    COMPARES BYTES, NOT TEXT, AND THAT IS THE WHOLE POINT OF THIS PARAGRAPH.
    The first version read the committed file with ``read_text``, which
    normalizes newlines, so a CRLF copy written by the documented regeneration
    command on Windows compared EQUAL here and was then REFUSED by
    ``load_copy()`` on every machine, including the gate - the verifier the
    design nominates as its last hop reported green on the one accident the
    design makes easy (pf-adversary, round i8timv, D4).  ``read_bytes`` is what
    the digest sees, so this is what the check has to see.
    """
    regenerated = curate(tables_dir).encode("utf-8")
    committed = COPY_PATH.read_bytes()
    if regenerated != committed:
        regenerated_sha = hashlib.sha256(regenerated).hexdigest()
        committed_sha = hashlib.sha256(committed).hexdigest()
        detail = ""
        if regenerated.replace(b"\r\n", b"\n") == committed.replace(b"\r\n", b"\n"):
            detail = (
                " - the two differ ONLY in line endings, so this is the CRLF "
                "regeneration accident: rewrite the copy with newline='' and "
                "re-pin"
            )
        raise MarkerCopyError(
            "the committed crosswalk is not what the client tables produce: "
            f"regenerated sha256 {regenerated_sha}, committed {committed_sha}"
            + detail
        )
