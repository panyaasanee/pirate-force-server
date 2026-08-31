"""CORE-REQUEST-GM-041: the read point `gm/` asked for -- would toggling a
GM-switchable NPC on/off change what the next recompose cycle sends?
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import gm_npc_toggle_recompose as npc_toggle
from pirateforce_foundation.gm import npc_switch_catalog


class NpcToggleWouldRecomposeTests(unittest.TestCase):
    def test_every_known_switchable_npc_answers_false_today(self):
        # 855, 871, 882, 897, 902, 8180, 8181 -- the 7 n_GM_SWITCH=1 rows
        # (same set test_gm_npc_switch_catalog.py pins). No on/off state
        # exists yet for a recompose call site to read, so today's honest
        # answer is False for all seven, not a stub that agrees with hope.
        for mob_id in npc_switch_catalog.NPC_ID_TO_NAME:
            with self.subTest(mob_id=mob_id):
                self.assertFalse(npc_toggle.npc_toggle_would_recompose(mob_id))

    def test_non_switchable_mob_id_raises_value_error(self):
        # 1 is not one of the 7 -- the question is undefined for it, not "no".
        with self.assertRaises(ValueError):
            npc_toggle.npc_toggle_would_recompose(1)

    def test_zero_is_not_switchable_and_raises(self):
        with self.assertRaises(ValueError):
            npc_toggle.npc_toggle_would_recompose(0)

    def test_non_int_mob_id_raises_type_error(self):
        with self.assertRaises(TypeError):
            npc_toggle.npc_toggle_would_recompose("855")

    def test_bool_mob_id_raises_type_error(self):
        # bool is a subclass of int; True == 1 would otherwise slip past an
        # isinstance(mob_id, int) check and silently ask about mob_id 1.
        with self.assertRaises(TypeError):
            npc_toggle.npc_toggle_would_recompose(True)

    def test_negative_mob_id_raises_value_error_not_type_error(self):
        # not switchable, but still an int -- must fail on the catalog
        # lookup, not be mistaken for a type problem.
        with self.assertRaises(ValueError):
            npc_toggle.npc_toggle_would_recompose(-1)


if __name__ == "__main__":
    unittest.main()
