"""Pin DELETE-REFRESH-001's binary facts to the client image they came from.

HYP-PF-021 sends a `SelectActorVital` 0x36EF list rebuild after the pinned
0x36DB echo ack.  The design rests on two statements about the read-only
client binary, and neither of them may be a hand-typed number:

  1. the character list has ONE buffer and no erase-by-key path, so only a
     rebuild can remove a row (UI-REFRESH-001, re-derived independently by
     the verifier rather than copied from the report);
  2. the page variable 0x107A2C0 -- which the delete animation sets to 0x0B
     and the acknowledgement never restores -- has a twenty-FIRST writer that
     UI-REFRESH-001's immediate-only scan could not see: the register write
     0x4BD650 inside cStateCreateActor's vtable slot +0x10, the state
     machine's enter hook, which the SelectActorVital rebuild causes to run.

These tests import ``tools/verify_delete_refresh_static.py`` (which records
its own drift instead of exiting) and assert that every guard held and that
the load-bearing counts are what the lane's source constants say they are.
They also cross-check the lane module so a silent edit to either side cannot
move the claim.

Nothing is executed: one binary and two source files are read.  No server,
no GameClient, no socket, no database.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "verify_delete_refresh_static.py"
CLIENT = ROOT.parent / "GameClient" / "GameClient.local.bin"
CLIENT_SHA = "9627211412AC60D50AD189CE5A629443CE928EC23A9F8D219DFB2B157028B623"

# The skip reason must carry the [precondition:...] token - see tests/pf_preconditions.py.
sys.path.insert(0, str(ROOT / "tests"))
from pf_preconditions import CLIENT_IMAGE  # noqa: E402

sys.path.insert(0, str(ROOT / "src"))
from pirateforce_foundation.delete_refresh_hypothesis import (  # noqa: E402
    CLIENT_SHA256,
    STATIC_ANCHORS,
)


def _load_tool():
    spec = importlib.util.spec_from_file_location(
        "pf_delete_refresh_static", TOOL,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


@CLIENT_IMAGE.skip_unless_present()
class DeleteRefreshStaticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tool = _load_tool()
        cls.counts = cls.tool.COUNTS

    # --- the verifier itself ---------------------------------------------

    def test_every_static_guard_reproduced(self):
        self.assertEqual(self.tool.GUARDS_FAILED, [])
        self.assertGreaterEqual(self.tool.GUARDS_TOTAL, 40)

    def test_the_guards_ran_against_the_pinned_client_image(self):
        self.assertEqual(self.counts["client_sha256"], CLIENT_SHA)
        self.assertEqual(CLIENT_SHA256, CLIENT_SHA)

    # --- fact 1: one buffer, one rebuild, no erase ------------------------

    def test_only_the_select_actor_apply_can_refill_the_list(self):
        self.assertEqual(
            self.counts["character_list_fill_callers"], ["0x5efcac"],
        )
        self.assertEqual(
            self.counts["character_list_add_one_callers"], ["0x5efd76"],
        )
        self.assertEqual(self.counts["character_list_erase_by_key_paths"], 0)
        self.assertEqual(self.counts["rebuild_vital_id"], "0x36EF")
        self.assertEqual(self.counts["rebuild_apply"], "0x5EFC40")

    # --- fact 2: the page variable's complete writer set ------------------

    def test_the_page_variable_has_exactly_26_references(self):
        self.assertEqual(self.counts["page_variable_references_in_text"], 26)
        self.assertEqual(self.counts["page_variable_immediate_writes"], 20)
        self.assertEqual(self.counts["page_variable_reads"], 5)
        self.assertEqual(
            self.counts["page_variable_register_writes"], ["0x4bd650"],
        )
        self.assertEqual(
            self.counts["page_variable_immediate_writes"]
            + len(self.counts["page_variable_register_writes"])
            + self.counts["page_variable_reads"],
            self.counts["page_variable_references_in_text"],
        )

    def test_the_register_write_lives_in_the_state_enter_hook(self):
        self.assertEqual(self.counts["character_select_enter_hook"], "0x4BD5E0")
        self.assertEqual(
            self.counts["character_select_enter_hook_vtable_slot"], "+0x10",
        )
        self.assertEqual(
            self.counts["character_select_enter_hook_direct_call_sites"], 0,
        )
        self.assertEqual(self.counts["state_tick"], "0x4C7540")
        self.assertEqual(self.counts["state_tick_enter_call_site"], "0x4C75D9")

    def test_the_acknowledgement_still_cannot_do_any_of_it(self):
        self.assertEqual(self.counts["delete_ack_handler"], "0x4BAEB0")
        self.assertEqual(self.counts["delete_animation_page_value"], "0x0B")

    # --- the lane module and the binary agree -----------------------------

    def test_the_lane_constants_match_the_binary(self):
        self.assertTrue(self.counts["lane_cross_check_ran"])
        self.assertTrue(self.counts["v141_cross_check_ran"])
        self.assertEqual(
            "0x%08X" % STATIC_ANCHORS["page_variable"],
            self.counts["page_variable"],
        )
        self.assertEqual(
            "0x%06X" % STATIC_ANCHORS["character_select_enter_hook"],
            self.counts["character_select_enter_hook"],
        )
        self.assertEqual(
            "0x%06X" % STATIC_ANCHORS["state_tick"], self.counts["state_tick"],
        )
        self.assertEqual(
            "0x%06X" % STATIC_ANCHORS["select_actor_apply"],
            self.counts["rebuild_apply"],
        )
        self.assertEqual(
            "0x%06X" % STATIC_ANCHORS["delete_ack_handler"],
            self.counts["delete_ack_handler"],
        )
        self.assertEqual(
            "0x%08X" % STATIC_ANCHORS["character_list_singleton_global"],
            self.counts["character_list_singleton_global"],
        )
        self.assertEqual(
            STATIC_ANCHORS["page_variable_register_write"], 0x4BD650,
        )

    # --- what is NOT claimed ---------------------------------------------

    def test_no_client_observable_claim_is_recorded_here(self):
        """The pixels are GT-021, not this file.

        Everything above is a statement about bytes in one immutable file.
        The prediction that the rebuild makes the row disappear AND unfreezes
        the buttons is exactly what the attended round has to decide.
        """
        self.assertEqual(self.counts["milestone"], "DELETE-REFRESH-001")
        self.assertEqual(self.counts["hypothesis"], "HYP-PF-021")


if __name__ == "__main__":
    unittest.main()
