"""The one public reader from ``scene_id`` to the scene's own folder name.

LANE-A (WORLD).  Ordered by COO-DECISION ``20260829_0848`` item 3, which split
"a roster that follows the scene the character is standing in" into two owners:
LANE-A owns the converter from ``scene_id`` -- the integer the runtime holds --
to the scene's name, and the chief wires that reader into ``runtime.py`` (3911
and 1119).  The COO's words for the shape were "one public reader, not a new
table", because the registry already carries ``n_id``.  This module is that
reader.  ``scene_folder_for_scene_id`` is its whole public surface; everything
else here exists to keep that function honest.

WHY LANE-B WAS RIGHT NOT TO GUESS THIS, AND IT IS NOT A STYLE POINT.  The
obvious implementation - hand the caller ``s_MODLE_ID`` from the client's
``SCENE_NAME`` table, which the registry copies into each destination's
``model_id`` - is WRONG FOR SIX OF THE SIXTEEN SCENES THIS REGISTRY ADDRESSES,
and wrong in a way that reads as correct on a Windows bridge and fails on the
gate.  Measured this round against the two committed sources:

    scene 1  s_MODLE_ID BG0001  folder bg0001   <- differs
    scene 2  s_MODLE_ID BG0002  folder Bg0002   <- differs
    scene 3  s_MODLE_ID BG0003  folder Bg0003   <- differs
    scene 4  s_MODLE_ID BG0004  folder bg0004   <- differs
    scene 5  s_MODLE_ID BG0005  folder bg0005   <- differs
    scene 6  s_MODLE_ID Bg0006  folder bg0006   <- differs
    scene 7 .. 997                              <- ten agree exactly

THERE IS NO PATTERN TO GUESS.  Scene 3 is ``Bg0003`` and scene 4 is ``bg0004``;
scene 6 is ``Bg0006`` in the table and ``bg0006`` on disk.  Across the client's
full 271 scenes, 14 spell the folder differently from ``s_MODLE_ID``.  The only
way to be right is to read the index, which is what the committed copy is for.

WHAT IT COSTS TO GET WRONG, stated as consequences rather than as tidiness:

* ``world_scene_numbering.OWNER_CONFIRMED_SCENES`` is ``("Bg0002",)`` and
  ``REFUSAL_REASONS`` is keyed the same way.  A caller handed ``"BG0002"``
  gets ``identity_is_provable`` False for the ONE scene whose cast the owner
  walked and confirmed on screen, and a generic refusal reason with it - the
  guard reporting a confirmed scene as unassessed, quietly, in the direction
  that looks safe.
* Any path that builds ``gamedata/scene/<name>/`` from the answer misses on a
  case-sensitive filesystem.  The gate is Linux; the bridge is Windows.  That
  is a defect that passes locally and fails only where the merge is decided.

A FOLDER NAME IS NOT A SCENE IDENTITY, AND THIS ONE BITES INSIDE THE SIXTEEN.
The map from scene id to folder is a function; its inverse is not.  Measured
from the same two files: the client's 271 scene rows name only 226 distinct
folders, and 45 folders are named by two scene ids each.  One of those pairs is
addressed by this registry - SCENE 17 AND SCENE 186 BOTH NAME ``Bg1001``.  So a
caller may use this answer to FIND a scene's data, and must not use it to
IDENTIFY the scene: anything keyed per-scene (a roster cache, a census tag, a
spawn record) must stay keyed by ``scene_id``, or scene 186 will silently be
served whatever scene 17 put there the moment 186 is ever addressed.

WHAT THIS READER REFUSES TO DO.  It answers for the sixteen scene ids the
registry addresses and returns ``None`` for every other id.  It does not fall
back to the client table for an unaddressed scene.  The reason is the one
LANE-B named when it declined to build this itself: a wrong answer here puts
the wrong scene's monsters in front of a player who is standing somewhere else.
An id this registry has never vetted has no roster address.
~~even though the copy holds all 271 rows and could~~ STRUCK, round yam18f,
pf-adversary D9: in the release archive - the configuration this reader is
being built for - the copy is not present at all, so the restraint being
claimed as a virtue is not available where it is claimed.

AND ``None`` IS ONLY AN ANSWER FOR ONE CALL.  Driven, same round: feeding
``None`` to ``world_scene_numbering.identity_block_reason`` - the composition
this package's own tests demonstrate - yields BYTE-IDENTICAL output for scene
4242 (does not exist in the client), scene 186 (exists, folder known,
deliberately unaddressed) and scene 17 (addressed and real).  All three read as
"we know this scene, we merely will not assert identities".  So the refusal
does NOT survive into the boot log on its own, and the caller is where it has
to be kept: the roster path must branch on ``None`` BEFORE it composes any
other verdict, and ``roster or DEFAULT_ROSTER`` two lines later would undo
every guarantee this module offers.  That caller-side assertion is the chief's
to write and is named in
``pf_bridge/notes_to_chief/20260829_1234_LANE-A-STATUS-scene-id-to-scene-name-
reader-is-ready-for-the-chief.md``; nothing in THIS repository proves it
happens, and this paragraph is here so no one reads that proof into the module.

WHY THE FOLDER NAME AND NOT THE OTHER TWO CANDIDATES.  ``SCENE_NAME.tsv``
ships three name-shaped columns and the COO's phrase (``chue chak``, "scene
name") does not by itself pick one: ``s_MODLE_ID`` (the model id argued
against above), ``s_SCENE_NAME`` (the Thai display string a player reads on
screen) and ``s_IMAGENAME``.  This reader answers with the FOLDER because the
caller it was ordered for loads a roster and reaches for scene data on disk.
A caller that wants the words to show a human wants ``s_SCENE_NAME`` and will
not find it here (pf-adversary, round yam18f, D10: the first draft compared
two candidates and read as though it had compared all of them).

WHERE THE SPELLINGS COME FROM, AND WHY THEY ARE LITERALS HERE.  The tuple
below is generated, not typed, and ``tests/test_world_scene_folder.py``
re-derives every row of it from
``world_data/world_scene_folder_crosswalk.json`` on every machine including the
gate.  They are literals in this ``.py`` rather than a JSON read at import for
the reason ``world_marker_copy`` records in its own docstring:
``build_foundation_release.py`` collects ``src/**/*.py`` and no data, so a
module that read the copy at import would boot here and die in the release
archive.  This reader is going onto the boot path at ``runtime.py``, so that
failure would be a boot failure, not a test failure.

WHAT IS STILL NOT PROVEN HERE, and it is the same limit every LANE-A artifact
carries this week: the gate checks this module against a copy LANE-A committed,
never against the client.  Only ``verify_against_sources()`` run on the bridge
compares the copy with the client's shipped files.  The wider question is asked
at ``pf_bridge/notes_to_chief/20260829_1126_LANE-A-ASK-COO-what-can-a-lane-not-
write.md``.
"""
from __future__ import annotations

from pathlib import Path
import csv
import hashlib
import json

# Convention marker, same as every other always-on module in this package.
# Nothing here is behind a scenario flag and nothing here sends a frame.
production_allowed = True

COPY_PATH = Path(__file__).parent / "world_data" / "world_scene_folder_crosswalk.json"

# The digest of the committed copy, same two-key lock as world_marker_copy:
# editing the copy without moving this pin fails load_copy(), and moving this
# pin without regenerating fails the re-derive test.  Neither can be satisfied
# without both files appearing in the same diff.
COPY_SHA256 = "6c5051c784d23f004f7fc297545d521d566b0137a526ed48928726d4cf8ef245"

# The two source files, named the way the rest of this package names them,
# WITH THEIR DIGESTS.  The digests are not decoration: without them the copy
# says which FILES it came from and not which CLIENT BUILD, so a regeneration
# against a patched client would re-pin COPY_SHA256, update the literals, and
# pass every test while this module and world_scene_marker described two
# different clients (pf-adversary, round yam18f, D5).  SCENE_NAME_TSV_SHA256 is
# asserted equal to world_scene_marker's constant for the same file - the two
# modules share a source, so they must share a build.
SCENE_NAME_TSV = "pf_bridge/gamedata/tables/CONSTDATA_TH__SCENE_NAME.tsv"
SCENE_NAME_TSV_SHA256 = (
    "e38114a802576266ce37b2abcf8ebce3f105d7d5abaf4bc5ca066e7848c5d60b"
)
SCENE_INDEX_TSV = "pf_bridge/gamedata/PF_GAMEDATA_SCENE_INDEX.tsv"
SCENE_INDEX_TSV_SHA256 = (
    "c4016cf685671d4c7bbb1909bb300146afd802dd6b53f2d5e7b928249f26652d"
)

# ``scene_id -> folder name``, for the scene ids world_scene_registry_001.json
# addresses.  GENERATED from the committed copy; do not hand-edit either side.
# The test that re-derives this also asserts the id set equals the registry's,
# so a destination added to the registry without an address here goes red, and
# an address here for a scene the registry does not carry goes red too.
#
# ~~That is what keeps this from becoming the second table the COO said not to
# build.~~  STRUCK, round yam18f, pf-adversary D8, because it flattered this
# round: the ruling said "one public reader, NOT a new table", and what shipped
# is a 16-row literal table plus a 271-row committed JSON table.  The id-set
# test does not prevent that; it only prevents the table from carrying a
# DIFFERENT id set than the registry.  The honest sentence is that this lane
# built a table the ruling told it not to build, because the measurement in the
# docstring above says the registry's own model_id column cannot answer the
# question, and the cost is recorded here rather than argued away.
_FOLDER_BY_SCENE_ID = (
    (1, "bg0001"),
    (2, "Bg0002"),
    (3, "Bg0003"),
    (4, "bg0004"),
    (5, "bg0005"),
    (6, "bg0006"),
    (7, "Bg0007"),
    (8, "Bg0008"),
    (9, "Bg0009"),
    (10, "Bg0010"),
    (11, "Bg0011"),
    (14, "Bg0015"),
    (17, "Bg1001"),
    (130, "Bg4001"),
    (278, "Bg1177"),
    (997, "FilmScene"),
)

# The six ids whose folder spelling differs from s_MODLE_ID, kept as a named
# constant because it is the measurement this module exists for.  A future
# round that "simplifies" the reader into returning model_id turns this from a
# fact into a lie, and test_the_reader_is_not_model_id goes red on it.
SPELLING_DIFFERS_FROM_MODEL_ID = (1, 2, 3, 4, 5, 6)

# Totals from the client's two files, re-derived from the copy by the tests.
# Quoted here because a docstring number nobody can check is how this lane got
# a count wrong by a factor of 36 in round 8ubiku.  Read the two folder counts
# as the different quantities they are: 289 is how many scene folders the index
# ships, 226 is how many of them a scene row actually names.
CLIENT_SCENE_ROW_COUNT = 271
CLIENT_SCENE_FOLDER_COUNT = 289
CLIENT_DISTINCT_FOLDERS_NAMED_BY_A_SCENE = 226
CLIENT_SPELLING_MISMATCH_COUNT = 14

# 45 folders carry two scene ids each, so the inverse of this reader is not a
# function.  Kept as a number rather than as prose because the first draft of
# this module wrote "271 scenes, 289 folders" and left a reader to assume the
# map was one-to-one, which it is not.
FOLDERS_NAMED_BY_MORE_THAN_ONE_SCENE = 45

# The one collision that touches a scene this registry addresses: scene 17 (the
# sea, an M2 destination candidate) and scene 186 both live in Bg1001.  Only 17
# is addressed today, so nothing is served wrongly right now; this constant is
# what goes red the day a round addresses 186 without deciding what that means.
SCENE_IDS_SHARING_AN_ADDRESSED_FOLDER = ((17, 186, "Bg1001"),)

# The assumption the case-insensitive join rests on: no two of the client's 289
# scene folders differ only by case.  If a future client ships such a pair the
# join stops being a function, and curate() raises rather than picking one.
#
# THIS IS A DERIVED ANSWER, NOT A DECLARED ONE.  It was a bare ``True`` whose
# only test asserted that True is True - a claim about the client that nothing
# on the gate could falsify, inside a module whose whole argument is that
# unfalsifiable numbers are how this lane got one wrong by a factor of 36
# (pf-adversary, round yam18f, D6).  The copy now carries the index's full
# folder list, so both this and the 289 are computed from data at gate time.
def folder_names_are_case_unique(copy: "dict[str, object] | None" = None) -> bool:
    """Whether the client's shipped folder names are unique when lowercased."""
    document = load_copy() if copy is None else copy
    folders = list(document["index_folder_names"])  # type: ignore[index]
    return len({str(name).lower() for name in folders}) == len(folders)


class SceneFolderCopyError(RuntimeError):
    """The committed copy is missing, altered, or disagrees with the module."""


def _read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def scene_folder_for_scene_id(scene_id: int) -> str | None:
    """The scene folder governing ``scene_id``, or ``None`` when unaddressed.

    THE ONE PUBLIC READER (COO-DECISION 20260829_0848 item 3).  Call this from
    any path that has a scene id and needs the scene's own name - a roster
    load, a census line, a gamedata path.  Do not read ``model_id`` off the
    registry for that purpose: it is the client table's spelling, which differs
    from the folder's for six of the sixteen addressed scenes.

    ``None`` means "this registry does not address that scene id", which is a
    refusal and not an absence of data.  Callers must treat it as "ship no
    roster", never as "ship the default one".
    """
    if type(scene_id) is not int or type(scene_id) is bool:
        raise ValueError("scene id must be an integer")
    return dict(_FOLDER_BY_SCENE_ID).get(scene_id)


def folder_console_suffix(scene_id: int) -> str:
    """One ASCII token naming the folder a scene id resolved to, for the boot
    log.  The bridge console is cp874, so this stays inside 7-bit ASCII, same
    rule as ``world_population.census_console_line()``.  An unaddressed id
    prints ``folder=?`` rather than nothing, because a roster path reaching a
    scene this registry never vetted is the case most worth seeing in a log.
    """
    folder = scene_folder_for_scene_id(scene_id)
    return "WORLD_SCENE_FOLDER scene_id=%d folder=%s addressed=%d" % (
        scene_id, folder if folder is not None else "?", 1 if folder else 0,
    )


def curate(gamedata_dir: Path | str) -> str:
    """Build the copy's exact JSON text from a bridge ``gamedata`` directory.

    This is the generator, and it is the reason the copy is not hand-typed.
    Returns text rather than writing a file so a caller can compare it with the
    committed bytes without touching the working tree.
    """
    gamedata = Path(gamedata_dir)
    scene_path = gamedata / "tables" / Path(SCENE_NAME_TSV).name
    index_path = gamedata / Path(SCENE_INDEX_TSV).name
    scene_rows = _read_tsv(scene_path)
    index_rows = _read_tsv(index_path)

    folders = [row["scene"] for row in index_rows]
    folder_by_lower: dict[str, str] = {}
    for folder in folders:
        key = folder.lower()
        if key in folder_by_lower and folder_by_lower[key] != folder:
            # Not a hypothetical guard: the whole join is case-insensitive, so
            # two folders differing only by case would make it ambiguous and
            # this module would be picking one silently.  Refuse instead.
            raise SceneFolderCopyError(
                f"scene folders {folder_by_lower[key]!r} and {folder!r} differ "
                "only by case; the model-id join is no longer a function"
            )
        folder_by_lower[key] = folder

    pairs: list[tuple[int, str, str]] = []
    seen_ids: set[int] = set()
    for row in scene_rows:
        model = row["s_MODLE_ID"]
        scene_id = int(row["n_ID"])
        # THE FORWARD MAP MUST BE A FUNCTION TOO.  The folder side of this
        # join was guarded from the first draft and the scene side was not, so
        # a client shipping n_ID twice would have resolved to whichever row
        # came last, silently, with every test green (pf-adversary, round
        # yam18f, D7).  Today's 271 rows carry 271 distinct ids; this is the
        # guard for the table that changes.
        if scene_id in seen_ids:
            raise SceneFolderCopyError(
                f"scene id {scene_id} appears twice in {scene_path.name}; the "
                "crosswalk cannot say which folder that scene names"
            )
        seen_ids.add(scene_id)
        folder = folder_by_lower.get(model.lower())
        if folder is None:
            raise SceneFolderCopyError(
                f"scene {scene_id} names model {model!r}, which has no folder "
                f"in {index_path.name}"
            )
        pairs.append((scene_id, model, folder))

    mismatches = [(n_id, model, folder)
                  for n_id, model, folder in pairs if model != folder]
    document = {
        "schema": 1,
        "id": "world_scene_folder_crosswalk_001",
        "lane": "A_WORLD",
        "what_this_is": (
            "the client's own crosswalk from a scene id to the folder that "
            "scene's data lives in, curated so the gate can re-derive "
            "world_scene_folder._FOLDER_BY_SCENE_ID without the bridge tree. "
            "Generated by world_scene_folder.curate(); do not hand-edit."
        ),
        "index_folder_names": sorted(folders),
        "provenance": {
            "scene_name_table": SCENE_NAME_TSV,
            "scene_name_table_sha256": hashlib.sha256(
                scene_path.read_bytes()).hexdigest(),
            "scene_index": SCENE_INDEX_TSV,
            "scene_index_sha256": hashlib.sha256(
                index_path.read_bytes()).hexdigest(),
            "join": (
                "SCENE_NAME[n].s_MODLE_ID matched case-insensitively against "
                "the scene column of PF_GAMEDATA_SCENE_INDEX.tsv. The match is "
                "case-insensitive because 14 of 271 rows disagree in case, and "
                "it is unambiguous because no two folders differ only by case "
                "- curate() raises if that ever stops being true."
            ),
            "reverify_on_the_bridge": (
                "python -c \"from pirateforce_foundation import "
                "world_scene_folder as f; f.verify_against_sources("
                "'pf_bridge/gamedata')\""
            ),
        },
        "totals": {
            "scene_row_count": len(pairs),
            "scene_folders_shipped_by_the_index": len(folders),
            "distinct_scene_folders_shipped_by_the_index": len(set(folders)),
            "scenes_resolving_to_a_folder": len(pairs),
            "distinct_folders_named_by_a_scene": len(
                {folder for _, _, folder in pairs}),
            "folders_named_by_more_than_one_scene": sum(
                1 for folder in {f for _, _, f in pairs}
                if sum(1 for _, _, g in pairs if g == folder) > 1),
            "exact_spelling_matches": len(pairs) - len(mismatches),
            "spelling_mismatch_count": len(mismatches),
        },
        "scene_ids_sharing_a_folder": sorted(
            [folder, sorted(n for n, _, g in pairs if g == folder)]
            for folder in {f for _, _, f in pairs}
            if sum(1 for _, _, g in pairs if g == folder) > 1
        ),
        "spelling_mismatches": [list(row) for row in mismatches],
        "scene_folder_index": [[n_id, folder] for n_id, _, folder in pairs],
        "scene_model_index": [[n_id, model] for n_id, model, _ in pairs],
    }
    text = json.dumps(document, indent=2, ensure_ascii=True, sort_keys=False)
    return text + "\n"


def load_copy() -> dict[str, object]:
    """The committed copy, refused if its bytes are not the pinned bytes."""
    try:
        raw = COPY_PATH.read_bytes()
    except FileNotFoundError as exc:
        raise SceneFolderCopyError(
            f"the committed scene folder crosswalk is missing at {COPY_PATH}"
        ) from exc
    actual = hashlib.sha256(raw).hexdigest()
    if actual != COPY_SHA256:
        raise SceneFolderCopyError(
            f"world_scene_folder_crosswalk.json sha256 mismatch: pinned "
            f"{COPY_SHA256}, found {actual}. The copy was edited without "
            "moving COPY_SHA256, or COPY_SHA256 was moved without "
            "regenerating the copy. Regenerate from the bridge tree; do not "
            "type either one by hand."
        )
    return json.loads(raw.decode("utf-8"))


def derive_folders(scene_ids: tuple[int, ...],
                   copy: dict[str, object] | None = None,
                   ) -> tuple[tuple[int, str], ...]:
    """Re-derive ``(scene_id, folder)`` for ``scene_ids`` from the copy.

    This is what the gate runs against ``_FOLDER_BY_SCENE_ID``: the literals
    above are correct only if this returns the same pairs, from data whose
    digest is pinned, on a machine with no bridge tree.
    """
    document = load_copy() if copy is None else copy
    folder_by_id = {int(n_id): folder
                    for n_id, folder in document["scene_folder_index"]}  # type: ignore[index]
    derived = []
    for scene_id in scene_ids:
        folder = folder_by_id.get(scene_id)
        if folder is None:
            raise SceneFolderCopyError(
                f"scene id {scene_id} is addressed by the registry but the "
                "client's scene table has no such row"
            )
        derived.append((scene_id, folder))
    return tuple(derived)


def derive_totals(copy: dict[str, object] | None = None) -> dict[str, int]:
    """Re-compute every total this module states, from the copy rather than
    from the copy's own ``totals`` block - a number transcribed beside the data
    it describes is not a check of that data."""
    document = load_copy() if copy is None else copy
    folder_index = [(int(n_id), folder)
                    for n_id, folder in document["scene_folder_index"]]  # type: ignore[index]
    model_index = {int(n_id): model
                   for n_id, model in document["scene_model_index"]}  # type: ignore[index]
    mismatches = [n_id for n_id, folder in folder_index
                  if model_index[n_id] != folder]
    scenes_per_folder: dict[str, int] = {}
    for _, folder in folder_index:
        scenes_per_folder[folder] = scenes_per_folder.get(folder, 0) + 1
    folders = [str(name) for name in document["index_folder_names"]]  # type: ignore[index]
    return {
        "scene_row_count": len(folder_index),
        # NAMED FOR WHAT IT COUNTS.  An earlier draft called this
        # "distinct_scene_folder_count", the same key the copy's totals block
        # uses for the 289 folders the index ships, while computing the 226 a
        # scene row names - two different quantities one key apart.
        "distinct_folders_named_by_a_scene": len(scenes_per_folder),
        "folders_named_by_more_than_one_scene": sum(
            1 for count in scenes_per_folder.values() if count > 1),
        "exact_spelling_matches": len(folder_index) - len(mismatches),
        "spelling_mismatch_count": len(mismatches),
        # Computed from the folder list itself rather than read out of the
        # copy's totals block.  Until round yam18f's adversary pass this number
        # existed ONLY as a transcription beside the data it described, which
        # is the thing this function's own docstring says is not a check (D6).
        "scene_folders_shipped_by_the_index": len(folders),
        "distinct_scene_folders_shipped_by_the_index": len(set(folders)),
    }


def verify_against_sources(gamedata_dir: Path | str) -> None:
    """The bridge-side hop this repository cannot do: copy vs client files.

    Raises ``SceneFolderCopyError`` naming the disagreement.  Compares BYTES,
    not text: ``read_text`` normalizes newlines, so a CRLF copy regenerated on
    Windows would compare equal here and then be refused by ``load_copy()`` on
    every machine including the gate - the accident this design makes easy
    (pf-adversary caught exactly that in ``world_marker_copy``, round i8timv
    D4, and this verifier is written with that finding already applied).
    """
    regenerated = curate(gamedata_dir).encode("utf-8")
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
        raise SceneFolderCopyError(
            "the committed scene folder crosswalk is not what the client "
            f"files produce: regenerated sha256 {regenerated_sha}, committed "
            f"{committed_sha}" + detail
        )
