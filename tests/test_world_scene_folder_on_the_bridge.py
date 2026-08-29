"""The one hop this repository cannot make: the copy versus the client files.

SEPARATE FILE ON PURPOSE, and the reason is a defect rather than tidiness.
Round ``yam18f`` first wrote this check inside ``test_world_scene_folder.py``
as a conditional body:

    if not (BRIDGE_GAMEDATA / "PF_GAMEDATA_SCENE_INDEX.tsv").exists():
        self.assertFalse((BRIDGE_GAMEDATA / "tables").exists())
        return

and called that a virtue - "written as a conditional body rather than as a
skip so the file's own skip scan stays absolute".  pf-adversary (D4) repointed
the path at a machine without a bridge, which is what the gate is, and the
test reported **1 passed**.  Not skipped.  Passed.  With no ``SKIPPED`` line,
``tools/pf_pytest_precondition_census.py`` cannot see it, so the check drifted
out of the counted skip pile into the pile that reads as evidence - the exact
failure ``docs/PYTEST_SKIP_PINS.json`` exists to prevent: "a skipped check is
not a passed check... an unpinned skip is how a real test drifts into the skip
pile without anybody noticing."  The skip scan had stayed absolute by making
the skip unobservable.

So the check moved here, uses the declared precondition, and is PINNED with a
count in ``docs/PYTEST_SKIP_PINS.json`` under ``bridge_gamedata``.  It now
announces itself as skipped on every machine that has no bridge, and
``test_world_scene_folder.py`` keeps a skip scan with no exemptions at all.
This is the same split the precedent uses: ``test_world_marker_copy.py``
carries no skip, and the bridge hop lives in ``test_world_scene_marker.py``.

WHAT THIS PROVES WHEN IT DOES RUN: that the committed crosswalk is byte-for-
byte what the client's two shipped files regenerate.  It is the only check in
this repository that compares LANE-A's copy against the client rather than
against LANE-A's other files.
"""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from pf_preconditions import BRIDGE_GAMEDATA  # noqa: E402

from pirateforce_foundation import world_scene_folder as wsf  # noqa: E402

# The precondition guards ``<sibling>/pf_bridge/gamedata/tables``; curate() and
# verify_against_sources() take the gamedata directory above it, because they
# read the scene index from the gamedata root and the scene table from tables/.
_GAMEDATA = BRIDGE_GAMEDATA.paths[0].parent


@BRIDGE_GAMEDATA.skip_unless_present()
class FolderCrosswalkReverificationOnTheBridgeTest(unittest.TestCase):

    def test_the_copy_is_what_the_client_files_produce(self):
        wsf.verify_against_sources(_GAMEDATA)

    def test_the_pinned_source_digests_match_the_files_on_the_bridge(self):
        """The digests, checked against the actual client files.

        Inside the repository these two constants can only be compared with
        each other and with the copy that was generated beside them.  Here they
        are compared with the bytes they claim to describe, which is the only
        place that comparison can happen at all.
        """
        import hashlib
        gamedata = Path(_GAMEDATA)
        pairs = (
            (gamedata / "tables" / Path(wsf.SCENE_NAME_TSV).name,
             wsf.SCENE_NAME_TSV_SHA256),
            (gamedata / Path(wsf.SCENE_INDEX_TSV).name,
             wsf.SCENE_INDEX_TSV_SHA256),
        )
        for path, pinned in pairs:
            with self.subTest(path=path.name):
                actual = hashlib.sha256(path.read_bytes()).hexdigest()
                self.assertEqual(actual, pinned)


if __name__ == "__main__":
    unittest.main()
