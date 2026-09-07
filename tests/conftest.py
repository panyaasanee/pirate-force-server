"""Per-test isolation for the process-global structures production shares.

Added by chief round ``l5tqxc`` (R376) together with ``DEATH_SEED_WIRING``,
the seam LANE-B's pf-adversary finding D2 asked for (``COO-DECISION
20260906_1955`` item 3).

WHY THIS FILE HAD TO EXIST THE MOMENT THE SEAM LANDED.  ``mob_death_
persistence`` keeps ONE grave book per process, on purpose: a scene's deaths
belong to the world and not to the connection that caused them (``PANYA
20260906_1057/1140``), and a reboot is a new world.  Until this round nothing
read that book back, so a kill committed by one test was invisible to the
next one and the coupling cost nothing.  ``_sync_combat_scene_state`` now
seeds every session from it, and the coupling became load-bearing in the
worst way: 13 tests across 4 files reddened purely because an EARLIER test in
the same process had killed the monster they were about to kill
(``mob_death_refused_already_dead_no_death_frames``), which made the suite's
result depend on its own ordering.

WHAT THIS IS NOT.  It is not a way to make the seam's own tests pass:
``tests/test_death_seed_call_site.py`` installs its own book explicitly, in
its own ``setUp``, and would pass with this file deleted.  It is not a reset
of production state either -- nothing here runs on a real server; a booted
server keeps exactly one book for its lifetime, which is the whole feature.

WHAT IT COSTS, stated rather than left for a grader to find: a test that
MEANT to inherit another test's graves cannot, and none does today (the only
files that read the book install their own). And a run under plain
``python -m unittest``, which does not load conftest.py, keeps the old
order-dependent behaviour -- the gate runs pytest, and both of this repo's
own gate channels (``pytest_subset`` and the full suite) do too.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import mob_death_persistence  # noqa: E402


@pytest.fixture(autouse=True)
def _a_world_of_its_own():
    """Every test gets an empty grave book, and leaves an empty one behind.

    Autouse and function-scoped, so it covers ``unittest.TestCase`` classes
    too (pytest applies autouse fixtures to them). Installed BEFORE the test
    body and replaced after it, so neither the order tests run in nor a test
    that dies mid-way can hand its graves to the next one.
    """
    mob_death_persistence.install_world_deaths(
        mob_death_persistence.WorldDeaths())
    mob_death_persistence.forget_announced_scenes()
    try:
        yield
    finally:
        mob_death_persistence.install_world_deaths(
            mob_death_persistence.WorldDeaths())
        mob_death_persistence.forget_announced_scenes()
