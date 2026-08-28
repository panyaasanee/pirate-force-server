"""No scene's Mob-Set numbers may be shipped as ``MOBS.n_ID`` identities today.

LANE-A (WORLD).  This module is a refusal, not a discovery.  It exists because
two separate paths in this tree put a scene file's set number on the wire as an
actor identity, and neither of them can currently justify doing so:

* ``bg0001`` (Port Royal) ships 115 actors with ``n_ID = <set number>``.
  ``GT-078`` booted that path, and the owner rejected it on sight: every
  placement right, every NPC wrong.
* ``Bg0002`` (prison island) ships 97 on the same rule.  That one is a
  ``strong_hypothesis_not_yet_confirmed`` - see ``NAMING_SCHEME_STATUS`` and
  the docstring in ``scene2_prison_exile_tables``, which is the source of truth
  for how strong the ``NN = n_ID`` hypothesis is: 2 of 7 anchors numerically
  confirmed, and the owner's written instruction is not to state it as fact
  until all 7 clear.

WHY ``bg0001`` CANNOT BE RIGHT, at the client-observable layer.  This is the
part that is settled, and it was settled by the owner on 2026-08-27, not here.
``notes_to_chief/20260827_1240_PANYA-EVIDENCE-video2-Port-Royal-NPC-tour-*``
records the in-game map window listing Port Royal's scene NPCs in ``n_ID``
order 156, 157, 158, 159, 160, 161, 162, 163, tabulates 32 confirmed Port Royal
``n_ID`` values spanning 156-913, and states that **none** of them come from the
``MOBS`` 1-35 block.  ``bg0001``'s set numbers run 1..113.  A roster that lives
at 156-913 cannot be addressed by numbers that stop at 113.  That is sufficient
on its own, and it needs no theory about how scene files are numbered.

WHAT THIS MODULE DELIBERATELY DOES NOT DO.  An earlier draft of this round
tried to derive a general rule - that a set number is a real ``n_ID`` in scenes
numbered "sparsely" and a per-scene ordinal in scenes numbered "densely" - and
to let sparse+confirmed scenes through the guard.  Adversary review killed it
and it is recorded here so nobody rebuilds it:

* The comparison group was selected on the dependent variable.  "Density" was
  defined as ``max_set == distinct_sets``, and the group was chosen by
  ``max_set`` in the 102-115 band, so only a scene with >= 102 distinct sets
  could possibly come out dense.  Every sibling had 40-64.  "14 of 15 are
  sparse" was arithmetic, not evidence.
* The rule's single positive example refutes it.  ``Bg0002``'s set numbers are
  ``{1..41}`` plus ``{101..104}``; the confirmed region is the contiguous
  ``1..41``, which the rule classifies as a per-scene ordinal.  Its "sparse"
  verdict rested entirely on 101-104 - the four numbers the owner explicitly
  forbade guessing about, and which ``scene2_prison_exile_tables`` ships as
  UNRESOLVED.
* The converse fails at scale: dozens of small interiors are "sparse" only
  because one set number is absent, which would have licensed shipping the
  prison cast into them.

A simpler explanation already covers the evidence without any of that:
``n_ID`` is allocated in per-region blocks, the prison island owns the low
block, Port Royal owns 156+ and 600-900, and every scene file numbers its own
sets from 1 - so ``Bg0002``'s numbers coincide with ``n_ID`` only because its
region block happens to start at 1.  Under that reading every scene's set
numbers are ordinals, which is why this module refuses every scene rather than
sorting them into two kinds.

SO THE GUARD IS UNCONDITIONAL.  ``identity_is_provable()`` returns False for
every scene, including ``Bg0002``.  It is not a placeholder for a future
classifier; it encodes that no scene has cleared the bar the owner set.  The
one thing that should ever flip an entry here is anchors clearing, recorded by
the module that owns that hypothesis - not a numeric pattern found in the
scene files.

NONCLAIMS.  This module does not identify any ``bg0001`` NPC; does not close or
answer ``RE-128``; does not claim ``Bg0002``'s hypothesis is wrong (only that
it is not yet assertable); and changes no byte on the wire.  Nothing calls
``assert_identity_claim()`` on a dispatch path yet - wiring it into the two
paths that ship identities is a separate decision, asked of the owner in
``notes_to_chief/20260828_1841_LANE-A-*``.
"""

from typing import Optional

# --- verdicts ---------------------------------------------------------------

# Kept as a closed vocabulary so a caller cannot invent a third state that
# happens to be truthy.
IDENTITY_REFUSED = "refused"
IDENTITY_ALLOWED = "allowed"

# Every scene this tree can currently ship identities for, and the single
# reason each one is refused.  A scene absent from this table is refused too
# (see ``identity_block_reason``); listing these two explicitly is what makes
# the refusal auditable rather than merely a default.
REFUSAL_REASONS = {
    "bg0001": (
        "port_royal_roster_is_n_ID_156-913_per_owner_video2_20260827;"
        "set_numbers_stop_at_113;owner_rejected_GT-078"
    ),
    "Bg0002": (
        "NN=n_ID_is_strong_hypothesis_not_yet_confirmed;"
        "2_of_7_anchors;owner_forbids_stating_as_fact_until_7"
    ),
}

# The scene ids the Foundation serves, mapped to the scene file that governs
# them.  Explicit and closed: an unlisted id is refused, never guessed.
SCENE_ID_TO_SCENE_FILE = {
    1: "bg0001",
    2: "Bg0002",
}

# Deliberately empty, and deliberately present.  When anchors clear for a
# scene, the change is one entry here plus the evidence in the owning module -
# which makes the moment a scene becomes assertable a reviewable diff instead
# of a silent consequence of some other edit.
OWNER_CONFIRMED_SCENES: tuple[str, ...] = ()


def scene_file_for_scene_id(scene_id: int) -> Optional[str]:
    """The scene file governing a served scene id, or None when unmapped."""
    if type(scene_id) is not int or type(scene_id) is bool:
        raise ValueError("scene id must be an integer")
    return SCENE_ID_TO_SCENE_FILE.get(scene_id)


def identity_is_provable(scene: str) -> bool:
    """Whether ``n_ID = <set number>`` may be asserted for ``scene``.

    False for every scene today.  This is not a stub: it is the finding.  The
    only path that can return True is a scene added to
    ``OWNER_CONFIRMED_SCENES``, which is empty because no scene has cleared the
    anchors the owner required.
    """
    return scene in OWNER_CONFIRMED_SCENES


def identity_block_reason(scene: str) -> Optional[str]:
    """Why identity may not be asserted for ``scene``, or None when it may.

    Short, ASCII, and meant to be printed beside the census.  A scene with no
    recorded reason still gets refused - with a reason saying exactly that,
    rather than an empty string that reads like an absence of a problem.
    """
    if identity_is_provable(scene):
        return None
    recorded = REFUSAL_REASONS.get(scene)
    if recorded is not None:
        return recorded
    return "no_scene_has_cleared_owner_anchors;scene_not_individually_assessed"


def assert_identity_claim(scene: str) -> None:
    """Refuse to assert ``n_ID = <set number>``.  Call this from any path about
    to put a set number on the wire as an actor identity."""
    reason = identity_block_reason(scene)
    if reason is not None:
        raise ValueError(
            "identity claim refused for scene %s: %s" % (scene, reason))


# --- console -----------------------------------------------------------------

def numbering_console_line(scene: str) -> str:
    """One ASCII token stating the identity verdict for ``scene``.

    The bridge console is cp874, so this stays inside 7-bit ASCII, same rule as
    ``world_population.census_console_line()``.
    """
    provable = identity_is_provable(scene)
    reason = identity_block_reason(scene)
    return (
        "WORLD_IDENTITY_GUARD scene={0} verdict={1} identity_provable={2} "
        "reason={3}".format(
            scene,
            IDENTITY_ALLOWED if provable else IDENTITY_REFUSED,
            1 if provable else 0,
            reason if reason is not None else "-",
        )
    )


def numbering_console_suffix(scene_id: int) -> str:
    """The verdict token for a served scene id, ready to append to a census
    line.  An unmapped scene id still produces a token carrying ``scene=?`` and
    a refusal, because a census going out for a scene this module cannot name
    is the case most worth seeing in a log."""
    scene = scene_file_for_scene_id(scene_id)
    if scene is None:
        return (
            "WORLD_IDENTITY_GUARD scene=? verdict=%s identity_provable=0 "
            "reason=scene_id_%d_not_mapped" % (IDENTITY_REFUSED, scene_id)
        )
    return numbering_console_line(scene)
