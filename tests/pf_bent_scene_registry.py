"""One bent reading of lane A's scene registry, shared by every test that
needs "a scene the registry refuses".

WHY THIS MODULE EXISTS.  Until PANYA-DECISION 20260908_1218 the shipped
`scenarios/world_scene_registry_001.json` carried four rows pinned
`login_entry_allowed: false` (17, 126, 304, 305) and two pinned
`persist_position_allowed: false` (14, 17), and twenty-two test files
reached for one of those scene ids whenever they needed an example of a
refusal.  1218 opened all six pins, so naming a scene id no longer names a
refusal, and the fixture had to move somewhere that does not depend on
which doors happen to be shut on a given day.

WHAT IT DOES.  `bend` takes lane A's OWN loaded registry -- the real rows,
the real spawns, the real marker ids -- and flips exactly one boolean on
exactly one row.  That is the edit an operator makes to the shipped JSON
between two boots, so a predicate that refuses the bent row is a predicate
that would refuse a real pin.  A hand-built stand-in would prove nothing:
the admissibility predicates read three fields off a row, and a fake can
satisfy all three while no shipped row does.

WHAT IS NOT CLAIMED.  Nothing here says any scene IS refused today.  The
shipped registry refuses nobody at login, which is the whole point of 1218;
these helpers exist so the ABILITY to refuse stays under test after the
data stopped exercising it.  A caller that bends a row with no spawn, or a
row that is not in the registry at all, gets a registry that proves nothing
-- so `bend` raises rather than returning quietly in both cases.

The technique and its reasoning come from
`tests/test_gm_login_scene_registry_snapshot.py` (LANE-A round 9lv3fa),
which walked it first for one file; this module is that walk, named once.
"""
from __future__ import annotations

import contextlib
import dataclasses
import importlib
import sys
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import world_scene_travel  # noqa: E402

# Bound at import, before any test patches the loader, so a bend built
# inside a patch context still reads the real file rather than another
# bend.  `load_scene_registry` is reached as a module attribute everywhere
# it is used, never rebound at import, which is what makes patching it a
# faithful stand-in for "what the disk says".
_REAL_LOAD_SCENE_REGISTRY = world_scene_travel.load_scene_registry

# A ship at sea.  It is in the registry with a measured spawn, it is in the
# client's scene name table, and it is the scene twenty-two test files used
# to name when they wanted a refusal -- so bending it keeps every one of
# those cases pointed at the same row it was written against, with only the
# SOURCE of the refusal moved from the file to the bend.
SEA = 17


def bend(scene_id: int = SEA, **flags: bool) -> world_scene_travel.SceneRegistry:
    """Lane A's real registry with one row's booleans replaced.

    `bend(17, login_entry_allowed=False)` is "the registry, except a
    character standing on a ship at sea is refused at login" -- the shipped
    reading up to 2026-09-08.  Passing no flags is a caller error, not an
    identity: it would install a bend that bends nothing and let a case
    pass without measuring anything.
    """
    if not flags:
        raise ValueError("bend() with no flags proves nothing; name one")
    unknown = set(flags) - {"login_entry_allowed", "persist_position_allowed"}
    if unknown:
        raise ValueError(f"not a pinned policy field: {sorted(unknown)}")
    real = _REAL_LOAD_SCENE_REGISTRY()
    rows = tuple(real.destinations)
    target = [row for row in rows if row.n_id == scene_id]
    if not target:
        raise ValueError(f"scene {scene_id} is not in the registry to bend")
    if not getattr(target[0], "spawn", None):
        raise ValueError(
            f"scene {scene_id} has no spawn; bending it proves nothing")
    return world_scene_travel.SceneRegistry(destinations=tuple(
        dataclasses.replace(row, **flags) if row.n_id == scene_id else row
        for row in rows))


def shut_at_login(scene_id: int = SEA) -> world_scene_travel.SceneRegistry:
    """The registry as it read before 1218 for one scene: door shut."""
    return bend(scene_id, login_entry_allowed=False)


def unpersisted(scene_id: int = SEA) -> world_scene_travel.SceneRegistry:
    """The registry as it read before 1218 for one scene: no write-back."""
    return bend(scene_id, persist_position_allowed=False)


# MODULES THAT BOUND THE LOADER BY NAME AT IMPORT.  `lifecycle` does
# `from .world_scene_travel import ... load_scene_registry`, so patching the
# attribute on `world_scene_travel` alone leaves the LIVE persist gate
# reading the shipped file while every predicate reads the bend -- a case
# that then passes for the wrong reason, or fails while looking like a
# product defect.  MEASURED in round 3a11a0: with only the one patch,
# `test_a_warp_inside_an_unpersisted_scene_confirms_nothing` saw the row
# move.  A module added to this list needs no other change; one MISSING
# from it is the failure above, which is why `patch_disk` walks it rather
# than each caller remembering.
_REBINDERS = ("lifecycle",)


def patch_disk(registry):
    """Make every reader's `load_scene_registry` return `registry`.

    Returned unstarted so a caller can use it as a context manager or hand
    it to `addCleanup`; `registry` may be a SceneRegistry or a zero-argument
    factory, so a case can bend per call when it needs to.

    Note for a caller driving a LIVE session: `lifecycle` reads the registry
    once, in its constructor, so the patch has to be started BEFORE the boot
    that builds it, not merely before the call being measured.
    """
    if callable(registry):
        def reading(*args, **kwargs):
            return registry()
    else:
        def reading(*args, **kwargs):
            return registry

    targets = [(world_scene_travel, "load_scene_registry")]
    for name in _REBINDERS:
        module = importlib.import_module(f"pirateforce_foundation.{name}")
        if getattr(module, "load_scene_registry", None) is not None:
            targets.append((module, "load_scene_registry"))
    return _MultiPatch([
        mock.patch.object(owner, attr, reading) for owner, attr in targets])


class _MultiPatch:
    """`mock.patch` semantics over several targets at once."""

    def __init__(self, patchers):
        self._patchers = tuple(patchers)

    def start(self):
        for patcher in self._patchers:
            patcher.start()
        return self

    def stop(self):
        for patcher in reversed(self._patchers):
            patcher.stop()

    def __enter__(self):
        return self.start()

    def __exit__(self, *exc_info):
        self.stop()
        return False


class BentDiskMixin:
    """`setUp` installs a bent disk reading for the whole case.

    Subclasses name `BENT_SCENE` and `BENT_FLAGS`; the default is the
    pre-1218 reading of the sea scene, which is what most of the files
    adopting this mixin were written against.
    """

    BENT_SCENE = SEA
    BENT_FLAGS = {"login_entry_allowed": False}

    def setUp(self) -> None:
        patcher = patch_disk(bend(self.BENT_SCENE, **self.BENT_FLAGS))
        patcher.start()
        self.addCleanup(patcher.stop)
        super().setUp()


@contextlib.contextmanager
def process_reads(registry):
    """The whole PROCESS answers from `registry`, THE CACHES NAMED BELOW.

    ~~caches included~~ -- STRUCK, LANE-A round ioz8fd (pf-adversary D5 of
    round 3a11a0).  "Caches included" read as a promise about every cache in
    the tree and this function knew about one.  It now clears two, and the
    third is named rather than silently missed.

    CLEARED HERE:

    * `gm/warp_scene_persist`'s module-level login snapshot, taken once per
      process, so patching the loader after it exists changes nothing there.
    * `world_m2_arrival._CACHED_REGISTRY`, via that module's own
      `forget_cached_registry()`, which existed and was never called.

    NOT CLEARED, AND THERE IS NO WAY TO FROM HERE:
    `gm/warp_chain_preflight._scene_registry.cached` is a function attribute
    with no reset entry point (`warp_chain_preflight.py:280`).  A case that
    reaches `preflight_chain` after anything in the same process has already
    asked it a question reads the SHIPPED file no matter what this function
    does.  Deleting the attribute from a test would be this module reaching
    into another lane's internals; the entry point belongs in that module.

    Each cache is cleared on the way in AND on the way out, so the next case
    gets the shipped reading back.

    Use this, not `patch_disk`, whenever the code under test is reached
    through `_persist_warp_scene`, `persist_warp_scene`, `login_would_accept`
    or `barred_login_scene_ids`.
    """
    from pirateforce_foundation.gm import warp_scene_persist
    from pirateforce_foundation import world_m2_arrival

    def forget():
        warp_scene_persist.reset_login_registry_snapshot_for_tests()
        world_m2_arrival.forget_cached_registry()

    with patch_disk(registry):
        forget()
        try:
            yield registry
        finally:
            forget()
