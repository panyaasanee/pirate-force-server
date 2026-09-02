"""gm/attr_wire.py: the selector note, and the renames/widenings this lane
REFUSED -- pinned so that reverting either half goes red.

Why this file exists.  `ka1-B`'s letter 20260901_2215 (items 3, 4, 5) asked
for four renames in `attr_wire.FIELDS` and for nineteen rows to be marked
`known`.  Round `ehx4w6` made NO rename and NO widening; it corrected one
word in two notes.  See `SELECTOR_NOTE_R301` in the module for the argument,
including the rename this lane tried first and had refuted before commit.

Each test below pins something a reverting edit would have to defeat on
purpose.  Two properties are deliberately asserted on the NOTE TEXT rather
than on a name, because the notes are the whole substance of the change:

  * no row may say the alternate HP pair is selected by comparing x=9's own
    value to 8 -- the comparison is on `0x430E10`'s RESULT;
  * no row may tell a reader which scene or scene category gets that pair --
    `0x430E10` is undecoded and an earlier draft of the module invented it.

NONCLAIM: nothing here proves anything about the client.  The claims these
tests protect are quotations from two in-repo reports; `SourceReportsStill
SayItTests` pins the quotations, not the bytes.  The byte-level guards in
`tools/pf_hp_death_respawn_static.py` need the client image, which this
checkout does not have -- those guards SKIP here, and that is exactly why
the citations are pinned as text.
"""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation.gm.attr_wire import BY_NAME, BY_X, SENSITIVE_FIELDS
from pirateforce_foundation.persistence_attr_compose import (
    CLIENT_CONSTRUCTION_DEFAULTS,
)

ATTR_WIRE = ROOT / "src" / "pirateforce_foundation" / "gm" / "attr_wire.py"
CHUNK2 = ROOT / "reports" / "PF_CHUNK2_Q1_ACTORATTR_MASK_FINDINGS_20260819.md"
HP_DEATH = ROOT / "reports" / "PF_HP_DEATH001_HP_DEATH_AND_RESPAWN_STATIC_20260819.md"
HP_STATIC = ROOT / "tools" / "pf_hp_death_respawn_static.py"

# The rows the trigger letter asked to widen.  x=30 is in the letter's list
# and is refused twice over (SENSITIVE_FIELDS), which is why the module says
# eighteen and the letter says nineteen.
REFUSED_WIDENING = (
    7, 9, 10, 12, 15, 26, 27, 28, 30, 38, 39, 44, 45, 46, 47, 49, 50, 51, 55,
)
# The rows the trigger letter asked to rename, with the name each must keep.
REFUSED_RENAME = {
    9: "category_5C",
    38: "u8_180",
    52: "alt_hp_current",
    53: "alt_hp_max",
}


class SelectorNoteTests(unittest.TestCase):
    """The one substantive correction: the comparison is on 0x430E10's result."""

    def _notes(self):
        return {x: field[8] for x, field in BY_X.items()}

    def test_the_two_selector_rows_name_the_function_not_the_raw_value(self):
        for x in (9, 52):
            self.assertIn(
                "0x430E10",
                self._notes()[x],
                "row x=%d describes the alternate-HP selector and must say the "
                "comparison is on 0x430E10's result, not on x=9's own value" % x,
            )

    def test_no_row_says_the_raw_field_is_compared_with_eight(self):
        # Catches the withdrawn wordings in every spelling seen so far:
        # "used when x9 == 8", "x=9 == 8", "partial: ==8 swaps HP".
        bare = re.compile(r"(?<!\))\s*==\s*8")
        for x, note in self._notes().items():
            stripped = note.replace("0x430E10(this)==8", "").replace(
                "0x430E10(x9)==8", ""
            )
            self.assertNotRegex(
                stripped,
                bare,
                "row x=%d compares a raw value with 8; the selector compares "
                "0x430E10's RESULT with 8 (%r)" % (x, note),
            )

    def test_no_row_tells_anyone_which_scene_gets_the_alternate_pair(self):
        # 0x430E10 is undecoded, so any note naming a scene invents the
        # mapping.  An earlier draft of this module did exactly that.
        forbidden = re.compile(r"scene\s*8|category\s*8\s*(is|=)", re.IGNORECASE)
        for x, note in self._notes().items():
            self.assertIsNone(
                forbidden.search(note),
                "row x=%d claims to know what category 8 is; the reports say "
                "0x430E10 was never decoded (%r)" % (x, note),
            )

    def test_x38_note_carries_its_single_source_label(self):
        self.assertIn("[CORPUS, UNVERIFIED]", BY_X[38][8])


class SourceReportsStillSayItTests(unittest.TestCase):
    """The module quotes three in-repo documents.  Pin the quotations."""

    def test_chunk2_still_retracts_the_scene_id_name(self):
        text = CHUNK2.read_text(encoding="utf-8")
        self.assertIn("[GUESS]", text)
        self.assertIn("0x430E10", text)
        self.assertIn("PROVEN VA=0x5BD3C0..0x5BD3E0", text)
        self.assertIn("u16 category; 0x430E10(cat)==8", text)

    def test_hp_death_still_refuses_to_say_what_category_8_is(self):
        text = HP_DEATH.read_text(encoding="utf-8")
        self.assertIn("What category 8 *is* is **not claimed**", text)
        self.assertIn("this milestone did not decode it", text)

    def test_the_one_writer_guard_is_still_one_encoding_in_text(self):
        # The module's scope caveat depends on this staying a single
        # find_bytes over ".text".  If the sweep is widened, the caveat
        # becomes stale and should be rewritten -- go red instead.
        text = HP_STATIC.read_text(encoding="utf-8")
        self.assertIn('find_bytes(b"\\x88\\x86\\x58\\x03\\x00\\x00", ".text")', text)
        self.assertIn("_sel_writers == [0x4564B3]", text)
        self.assertIn("SceneCategory(sceneId) == 8", text)

    def test_the_corpus_mirror_is_still_labelled_a_copy_not_a_source(self):
        # The whole refusal rests on this sentence.
        text = (
            ROOT / "src" / "pirateforce_foundation" / "persistence_attr_compose.py"
        ).read_text(encoding="utf-8")
        self.assertIn("One row of the Codex corpus, copied with its provenance", text)


class RefusedRenameTests(unittest.TestCase):
    """Four renames were asked for and refused.  All four stay refused."""

    def test_every_asked_row_keeps_its_current_name(self):
        for x, expected in REFUSED_RENAME.items():
            self.assertEqual(BY_X[x][6], expected)

    def test_the_corpus_names_are_recorded_but_not_adopted(self):
        for x, corpus in (
            (9, "scene_id__SCENE_NAME.n_ID"),
            (38, "LABEL_GUILD_FontStyleID_selector"),
            (52, "GetBoatHealth_current"),
            (53, "GetBoatHealth_max"),
        ):
            self.assertEqual(CLIENT_CONSTRUCTION_DEFAULTS[x].semantic_name, corpus)
            self.assertNotIn(corpus, BY_NAME)
        self.assertNotIn("scene_id", BY_NAME)
        self.assertNotIn("boat_health_current", BY_NAME)

    def test_no_fontstyleid_value_is_hardcoded_in_the_module(self):
        # NOW.md P-2: no FontStyleID may be hardcoded.  The domain lives in a
        # comment; no line of code may carry those numbers.
        code = "\n".join(
            line
            for line in ATTR_WIRE.read_text(encoding="utf-8").splitlines()
            if not line.lstrip().startswith("#")
        )
        self.assertNotIn("FontStyleID", code)


class RefusedWideningTests(unittest.TestCase):
    """The eighteen rows the letter asked to mark known stay refused."""

    def test_every_row_the_letter_listed_is_still_refused(self):
        for x in REFUSED_WIDENING:
            self.assertFalse(
                BY_X[x][7],
                "x=%d was widened to known=True; the letter asked for it and "
                "SELECTOR_NOTE_R301 refuses it pending a COO decision" % x,
            )

    def test_only_the_rows_that_were_already_permitted_are_permitted(self):
        # Snapshot of the permitted set at the start of round `ehx4w6`.  Any
        # addition or removal has to be made on purpose, here.
        permitted = frozenset(x for x, f in BY_X.items() if f[7])
        self.assertEqual(
            permitted,
            frozenset(
                {1, 2, 3, 4, 5, 6, 8, 11, 13, 16, 17, 18, 19, 20, 21, 22, 23, 24,
                 31, 32, 33, 34, 35, 37, 52, 53}
            ),
        )

    def test_a_row_the_compose_table_calls_UNKNOWN_is_never_permitted(self):
        for x, default in CLIENT_CONSTRUCTION_DEFAULTS.items():
            if default.semantic_name != "UNKNOWN":
                continue
            self.assertIn(x, BY_X)
            self.assertFalse(BY_X[x][7], "x=%d is UNKNOWN in the default table" % x)

    def test_the_sensitive_row_is_untouched(self):
        self.assertEqual(SENSITIVE_FIELDS, frozenset({30}))
        self.assertFalse(BY_X[30][7])
        self.assertIn(30, REFUSED_WIDENING)

    def test_every_name_is_still_unique(self):
        self.assertEqual(len(BY_NAME), len(BY_X))


class WithdrawnClaimStaysVisibleTests(unittest.TestCase):
    """House rule: strike through history, never erase it."""

    def test_the_module_records_the_rename_it_tried_and_withdrew(self):
        source = ATTR_WIRE.read_text(encoding="utf-8")
        self.assertIn("SELECTOR_NOTE_R301", source)
        self.assertIn("NO RENAMES", source)
        self.assertRegex(source, r"~~[^~]*earlier draft of this very block")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
