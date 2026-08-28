"""Which scenes' Mob-Set numbers are real ``MOBS.n_ID`` values, and which are
per-scene ordinals that mean nothing outside their own file.

LANE-A (WORLD).  This module exists because of one attended failure.
``GT-078`` booted the flagless path, put 115 actors into Port Royal
(``bg0001``) at 115 correct positions, and the owner rejected it on sight:
every placement was right and **every NPC was the wrong character**.  The
rule that produced those identities is ``n_ID = <set number>``, and that same
rule is owner-CONFIRMED correct for the prison island (``Bg0002``).  Nobody
could say why one scene obeys it and the other does not, so the project has
been treating ``bg0001``'s identities as "unconfirmed" - i.e. as something a
future round might confirm.

They are not unconfirmed.  They are a category error, and the discriminator
is in the shipped scene files.

WHAT WAS MEASURED (round ``o8cy9q``, from committed artifacts only; no game
client, no DB, no capture).  Source: ``pf_bridge/gamedata/scene/*/*.placements
.tsv`` (266 scenes that declare any set) and
``pf_bridge/gamedata/tables/CONSTDATA_TH__MOBS.tsv`` (3,210 rows, max
``n_ID`` 10,080).

1. A scene's set numbers are either DENSE - exactly ``1..N`` with no gap - or
   SPARSE.  Across all 266 scenes: **202 dense, 64 sparse**.
2. Every large continent/town scene is SPARSE with a maximum in the 102-115
   band, as if its author picked specific rows out of a shared table:
   ``Bg0002`` 45 sets in 1..104, ``bg0003`` 51 in 1..111, ``Bg0015`` 51 in
   1..115, ``bg0005`` 64 in 1..105, and so on.
3. **``bg0001`` is the only large town scene that is dense**: 113 sets, and
   they are exactly ``1..113``.  A file that uses 113 of a ~115-slot space
   with no gap at all, while all ten of its siblings have gaps, was numbered
   by counting - not by choosing.
4. Reading ``bg0001``'s sets 1..113 as ``n_ID`` returns the prison island's
   cast: 1 Navy transport soldier, 2 Sebastian, 4 Mo Yuzi, 16/17/26 pirate
   prisoners - all ``n_LEVEL_MIN/MAX`` 20/20.  That is ``Bg0002``'s roster,
   arriving in a level 10-20 port town.  It is exactly the picture the owner
   rejected on ``GT-078``, reproduced here from the tables alone.

THE RULE THIS PINS.  A set number is a global ``MOBS.n_ID`` only in a scene
whose numbering is SPARSE.  In a DENSE scene the number is a per-scene
ordinal and the real identity lives in a table that is not in the scene file
(the gap ``RE-128`` was opened for).  ``Bg0002`` sparse + owner-confirmed and
``bg0001`` dense + owner-rejected are the two ends this rests on; the other
ten town scenes are predictions this module states but does not claim.

WHY IT IS A GUARD AND NOT A FIX.  Knowing ``bg0001``'s numbers are ordinals
does not reveal what they map to, so this module cannot put the right NPCs in
Port Royal.  What it can do is stop the project from spending another
attended round re-learning ``GT-078``: ``identity_is_provable()`` is
fail-closed, ``assert_identity_claim()`` refuses, and
``numbering_console_line()`` puts the verdict in every boot log next to the
census that carries the identities.

NONCLAIMS.  This module does not claim to know any ``bg0001`` identity; that
``RE-128`` is answered (it is narrowed, not closed); that the ten predicted
scenes are correct (untested); that dense numbering has one single cause -
"authored by counting" is the reading, and a re-export or a renumbering pass
would look the same and would not change the consequence; or that any byte on
the wire changes because this module exists.  It reads frozen numbers and
returns verdicts.  It sends nothing.
"""

from typing import Optional

# --- namespace verdicts -----------------------------------------------------

NAMESPACE_GLOBAL_NID = "global_nid"
NAMESPACE_LOCAL_ORDINAL = "local_ordinal"
NAMESPACE_UNKNOWN = "unknown"

NAMESPACE_KINDS = (
    NAMESPACE_GLOBAL_NID,
    NAMESPACE_LOCAL_ORDINAL,
    NAMESPACE_UNKNOWN,
)

# --- the measurement, frozen ------------------------------------------------

# Aggregate over every scene file that declares at least one set.  Pinned so a
# re-export of gamedata that changes the shape of the corpus turns a test red
# rather than silently moving the rule underneath it.
SCENE_FILES_WITH_SETS = 266
DENSE_SCENE_COUNT = 202
SPARSE_SCENE_COUNT = 64

# (scene, placement_rows, distinct_sets, max_set, set_name_family) for every
# scene declaring >= 20 sets.  These are the scenes big enough for a
# population round to care about; the long tail of 3-to-8-set interiors is
# summarised by the aggregates above.  Density is derived, never stored:
# a scene is dense exactly when ``max_set == distinct_sets``.
FROZEN_SCENE_SET_CENSUS = (
    ("bg0001", 149, 113, 113, "Mob_Set_N"),
    ("Bg0002", 106, 45, 104, "MOBSET_N"),
    ("bg0003", 72, 51, 111, "MOBSET_N"),
    ("bg0004", 116, 55, 108, "Mob_Set_N"),
    ("bg0005", 92, 64, 105, "MOBSET_N"),
    ("bg0006", 80, 52, 114, "Mob_Set_N"),
    ("Bg0007", 68, 56, 111, "MOBSET_N"),
    ("Bg0008", 76, 48, 106, "MOBSET_N"),
    ("bg0009", 63, 44, 105, "Mob_set_N"),
    ("Bg0010", 100, 40, 105, "Mob_Set_N"),
    ("Bg0011", 56, 31, 105, "Mob_Set_N"),
    ("Bg0012", 67, 44, 102, "MIXED"),
    ("Bg0015", 91, 51, 115, "MOBSET_N"),
    ("Bg0016", 74, 48, 107, "MOBSET_N"),
    ("bg0017", 61, 46, 47, "Mob_Set_N"),
    ("Bg0020", 93, 30, 30, "Mob_Set_N"),
    ("Bg0021", 105, 28, 28, "Mob_Set_N"),
    ("Bg0022", 69, 28, 28, "Mob_Set_N"),
    ("Bg0023", 80, 23, 23, "Mob_Set_N"),
    ("bg2004", 64, 24, 26, "MIXED"),
    ("Bg2006", 227, 27, 29, "MobSet_N"),
    ("bg2007", 72, 23, 28, "MIXED"),
    ("Bg2016", 240, 23, 27, "MIXED"),
    ("Bg2017", 91, 23, 23, "MOBSET_N"),
    ("Bg3001", 38, 24, 56, "MIXED"),
    ("Bg3002", 39, 25, 55, "MIXED"),
    ("Bg3003", 42, 34, 34, "MIXED"),
    ("Bg3004", 46, 46, 46, "MobSet_N"),
    ("Bg3007", 66, 40, 58, "MIXED"),
    ("Bg3008", 59, 46, 56, "MIXED"),
    ("Bg5002", 38, 30, 30, "MOBSET_N"),
    ("Bg5003", 74, 47, 48, "MOBSET_N"),
    ("Bg5004", 30, 29, 29, "MIXED"),
)

# The two scenes an owner has actually looked at, and what they said.  Every
# other verdict in this module is a prediction; these two are the evidence the
# rule was read off, so they are named separately and never inferred.
OWNER_CONFIRMED_GLOBAL_NID = ("Bg0002",)
OWNER_REJECTED_LOCAL_ORDINAL = ("bg0001",)

# The scene ids the Foundation actually serves, mapped to the scene file whose
# numbering governs them.  Kept tiny and explicit: an unlisted scene id is
# UNKNOWN, which is fail-closed, rather than guessed from the number.
SCENE_ID_TO_SCENE_FILE = {
    1: "bg0001",
    2: "Bg0002",
}

_CENSUS_BY_SCENE = {row[0]: row for row in FROZEN_SCENE_SET_CENSUS}


# --- classification ---------------------------------------------------------

def classify_counts(distinct_sets: int, max_set: int) -> str:
    """The namespace verdict for one scene's set-number shape.

    Dense (``max_set == distinct_sets``, i.e. exactly ``1..N``) reads as a
    per-scene ordinal; sparse reads as a selection out of ``MOBS.n_ID``.
    Both arguments come from a scene file, so both are validated: a zero or
    negative count is not a small scene, it is a parse that went wrong, and
    ``max_set < distinct_sets`` is arithmetically impossible for a set of
    distinct positive integers.
    """
    if type(distinct_sets) is not int or type(max_set) is not int:
        raise ValueError("set counts must be integers")
    if distinct_sets < 1 or max_set < 1:
        raise ValueError("set counts must be positive")
    if max_set < distinct_sets:
        raise ValueError(
            "max set %d cannot be below the count of distinct sets %d"
            % (max_set, distinct_sets))
    if max_set == distinct_sets:
        return NAMESPACE_LOCAL_ORDINAL
    return NAMESPACE_GLOBAL_NID


def classify_scene(scene: str) -> str:
    """The namespace verdict for a scene file, or UNKNOWN if it is not in the
    frozen census.  Never raises for an unmeasured scene - an unmeasured scene
    is precisely the case the fail-closed path downstream exists for."""
    row = _CENSUS_BY_SCENE.get(scene)
    if row is None:
        return NAMESPACE_UNKNOWN
    return classify_counts(row[2], row[3])


def scene_file_for_scene_id(scene_id: int) -> Optional[str]:
    """The scene file governing a served scene id, or None when unmapped."""
    if type(scene_id) is not int:
        raise ValueError("scene id must be an integer")
    return SCENE_ID_TO_SCENE_FILE.get(scene_id)


def identity_is_provable(scene: str) -> bool:
    """Whether ``n_ID = <set number>`` may be asserted for this scene.

    True only for a scene that is BOTH classified global-``n_ID`` AND on the
    owner-confirmed list.  Sparse-but-unconfirmed is a prediction this module
    is willing to print and unwilling to ship identities on, so it returns
    False - the conservative answer is the one that cannot cost an attended
    round.
    """
    if scene in OWNER_REJECTED_LOCAL_ORDINAL:
        return False
    if scene not in OWNER_CONFIRMED_GLOBAL_NID:
        return False
    return classify_scene(scene) == NAMESPACE_GLOBAL_NID


def identity_block_reason(scene: str) -> Optional[str]:
    """Why identity may not be asserted for ``scene``, or None when it may.

    The string is short, ASCII, and meant to be printed beside the census.
    """
    if identity_is_provable(scene):
        return None
    kind = classify_scene(scene)
    if scene in OWNER_REJECTED_LOCAL_ORDINAL:
        return "owner_rejected_on_sight(GT-078);set_numbers_are_ordinals"
    if kind == NAMESPACE_LOCAL_ORDINAL:
        return "dense_1..N_numbering;set_number_is_not_n_ID"
    if kind == NAMESPACE_UNKNOWN:
        return "scene_not_in_frozen_census"
    return "sparse_but_not_owner_confirmed"


def assert_identity_claim(scene: str) -> None:
    """Refuse, loudly, to assert ``n_ID = <set number>`` where it is not
    provable.  Call this from any path about to put a set number on the wire
    as an identity."""
    reason = identity_block_reason(scene)
    if reason is not None:
        raise ValueError(
            "identity claim refused for scene %s: %s" % (scene, reason))


# --- console -----------------------------------------------------------------

def numbering_console_line(scene: str) -> str:
    """One ASCII token stating the namespace verdict for ``scene``.

    The bridge console is cp874, so this stays inside 7-bit ASCII, same rule
    as ``world_population.census_console_line()``.  It carries the two raw
    numbers the verdict is derived from, so a reader can re-derive the
    verdict from the line itself rather than trusting the word.
    """
    row = _CENSUS_BY_SCENE.get(scene)
    kind = classify_scene(scene)
    provable = identity_is_provable(scene)
    reason = identity_block_reason(scene)
    if row is None:
        shape = "sets=? max=? family=?"
    else:
        shape = "sets=%d max=%d family=%s" % (row[2], row[3], row[4])
    return (
        "WORLD_IDENTITY_NAMESPACE scene={0} kind={1} {2} "
        "identity_provable={3} reason={4}".format(
            scene, kind, shape, 1 if provable else 0,
            reason if reason is not None else "-")
    )


def numbering_console_suffix(scene_id: int) -> str:
    """The namespace token for a served scene id, ready to append to the
    census line.  An unmapped scene id still produces a token, carrying
    ``scene=?`` and the fail-closed verdict, because a census going out for a
    scene this module cannot name is the case most worth seeing in a log."""
    scene = scene_file_for_scene_id(scene_id)
    if scene is None:
        return (
            "WORLD_IDENTITY_NAMESPACE scene=? kind=%s sets=? max=? family=? "
            "identity_provable=0 reason=scene_id_%d_not_mapped"
            % (NAMESPACE_UNKNOWN, scene_id)
        )
    return numbering_console_line(scene)
