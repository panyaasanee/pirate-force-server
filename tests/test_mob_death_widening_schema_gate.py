"""LANE-B / CI-GATE-001: a new WIDENING_RULINGS key must carry its own letter.

COO-DECISION b1647 (schema 1647, ``pf_bridge`` notes_to_chief/20260906_1647_
COO-DECISION-b1525-*.md) fixed the shape a NEW ruling key must have: it must
contain one of ``COO-DECISION`` / ``COO-RULING`` / ``PANYA-DECISION``, contain
``widen-death-scope``, and END with an ISO timestamp
(``<YYYY-MM-DDTHH:MM+07:00>``) -- order-tolerant otherwise.  The 7 keys that
predate that schema are frozen, character for character, and are only ever
WARNED about, never failed.

COO-DECISION b1712 (``pf_bridge`` notes_to_chief/20260906_1745_COO-DECISION-
b1712-*.md) is the concrete gate this file is: a key that is NOT in the frozen
list and does not match the schema is red outright; a key that matches the
schema must ALSO have a same-day-stamped letter in ``pf_bridge``'s
``notes_to_chief/`` naming ``COO-DECISION`` and ``widen``, or it is red too --
because ``mob_death.py``'s own docstring already proves (round szdkgs,
pf-adversary) that the SERVER cannot tell a real ruling string from a
paraphrase or a hand mistake; only a second, independently-timestamped
artifact in the other repository can.

WHY THE FROZEN LIST HAD 8 KEYS, NOT 7 (7 since round b08g3z, see the
last bullet).  COO's own text (b1712 item 3) says
"3 of 7 keys have their date in the middle".  Measured directly against
``mob_death.WIDENING_RULINGS`` as it stands at the round this gate was
written (round bvaptp), there are 8 keys that do not match the new
trailing-date schema, not 7:

  * 3 do have the "COO-DECISION <date> widen-death-scope-...-templates" shape
    b1712 item 3 means by "date in the middle" (bg0003, bg0004, bg0005);
  * 2 more DO carry a date, but in a different position/shape again (the
    916-training-iron-man key's date is followed by a parenthetical citing a
    SECOND date; the bg0002 key's date sits right after "PANYA-DECISION",
    before an "(ADDENDUM 20:18)" aside);
  * 2 carry NO ``widen-death-scope`` substring at all (the Mountain Deer
    diagnostic key, and the bare ``COO-RULING-20260901-1046`` key) -- they are
    not "widen-death-scope permits" under b1647 item 1's own definition, but
    they are still WIDENING_RULINGS keys, so this file's enumeration (every
    key, per COO's own instruction) still has to place them somewhere, and
    the only place a key with no schema match can go is the frozen list;
  * 1 (``COO-RULING-20260827-1350 widen-death-scope-bg0001``) carried no date
    at all.  REMOVED from the tuple in round b08g3z: COO-DECISION
    2026-09-07T04:05+07:00 issued the successor letter this lane asked for,
    the key was renamed to
    ``COO-RULING-20260907-0405 widen-death-scope-bg0001 2026-09-07T04:05+07:00``
    and now passes the schema-plus-letter path below like any other key, so
    the frozen tuple holds 7.  A REMOVAL, which is what that decision
    permits ("withdraw is not add"); nothing was added to the tuple, and the
    closed-tuple assertion below is what proves the removal was earned --
    if the renamed key still failed the schema the set equality would go red.

Rather than force the count to 7 by leaving one of these 8 off the frozen
tuple by hand (which would silently narrow what this gate protects -- the
excluded key would then have to pass the NEW schema, which it cannot, and the
gate would go red on a key nobody actually widened this round), this file
freezes literally every key that fails the schema today, per the round's own
standing instruction: "if reality does not cleanly split into exactly 7,
write down what you found and use every non-conforming key".  Full accounting
in ``pf_bridge/rounds/B_<...>_bvaptp_*.md``.

THE 6 KEYS THAT ALREADY CONFORM (bg0006 through bg0011, minted 2026-09-06)
are not listed here at all -- they go through the schema-plus-letter check
below like any future key would, and this file proves they still have their
letters today rather than assuming it.
"""
from __future__ import annotations

import re
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import mob_death  # noqa: E402

from pf_preconditions import BRIDGE_SIBLING  # noqa: E402


# ---------------------------------------------------------------------------
# FROZEN, per COO-DECISION b1712 item 1 / b1647 item 2: "a name added to the
# frozen list is itself a fail; the list is closed."  Hardcoded character for
# character from mob_death.WIDENING_RULINGS as read at round bvaptp.  Do NOT
# add to this tuple: a key that is not here and does not match the schema
# below must get its own COO-DECISION letter instead, the same as any other
# new ruling.
FROZEN_WIDENING_RULING_KEYS = (
    "COO-DECISION widen-death-scope-916-training-iron-man "
    "2026-08-27T09:55+07:00 (ref PANYA-DECISION 2026-08-27T09:50+07:00 "
    "section 3, supersedes COO 0954)",
    "PANYA-DECISION 2026-08-27T20:10+07:00 (ADDENDUM 20:18) "
    "widen-death-scope-bg0002",
    "PANYA-DECISION 2026-08-27T20:10+07:00 (ADDENDUM 20:18) "
    "diag-mountain-deer-template-27",
    "COO-RULING-20260901-1046",
    "COO-DECISION 2026-09-04T11:48+07:00 "
    "widen-death-scope-bg0005-six-templates",
    "COO-DECISION 2026-09-04T14:50+07:00 "
    "widen-death-scope-bg0003-seven-templates",
    "COO-DECISION 2026-09-05T05:46+07:00 "
    "widen-death-scope-bg0004-five-templates",
)

# ---------------------------------------------------------------------------
# Schema, COO-DECISION b1647 item 2, "a regex that tolerates word order": a
# key is the NEW shape when it contains one of the three marker tokens AND
# contains "widen-death-scope" AND ENDS (anchored) with an ISO timestamp of
# the exact shape the schema mandates, "<YYYY-MM-DDTHH:MM+07:00>".
_MARKER_RE = re.compile(r"COO-DECISION|COO-RULING|PANYA-DECISION")
_WIDEN_RE = re.compile(r"widen-death-scope")
_TRAILING_DATE_RE = re.compile(
    r"(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})\+07:00$"
)


def _schema_date_match(key):
    """The trailing-date match if ``key`` is the new shape, else ``None``."""
    if not _MARKER_RE.search(key) or not _WIDEN_RE.search(key):
        return None
    return _TRAILING_DATE_RE.search(key)


def _letter_exists_for(pf_bridge_dir, date_match):
    """A ``notes_to_chief/`` file stamped with this key's own date, naming
    ``COO-DECISION`` and ``widen`` in its filename (COO-DECISION b1712 item
    1's letter requirement).

    SEARCHED RECURSIVELY, THE ARCHIVE INCLUDED -- COO-DECISION
    2026-09-07T05:46+07:00 item 2, answering this lane's 0512 letter.  The
    first draft read ``notes_to_chief/`` one level deep, which quietly made
    "never archive a letter that is the base of a live ruling key" a rule
    the house had to remember: LANE-K sweeps letters out of the mailbox on
    age, cannot know which letter some key in the OTHER repository stands
    on, and the key would go red weeks later with nobody having touched it.
    A letter that has been filed is still a letter, so the finder is what
    changes, not the sweeping rule.

    WHERE A SWEPT LETTER ACTUALLY IS, measured in round ot2cru against the
    bridge checkout rather than taken from the decision's wording.  The
    decision says "``notes_to_chief/**`` recursive, ``archive/`` included",
    which reads as ``notes_to_chief/archive/``.  That directory does not
    exist.  LANE-K's sweeps land in ``pf_bridge/archive/`` in dated folders
    of their own -- ``archive/notes_to_chief_2026-08/``,
    ``archive/notes_to_chief_2026-09/``,
    ``archive/notes_to_chief_2026-08-29_lane-b-r256-carveout-closed/`` and
    eleven more -- and two of the letters already in there are
    ``COO-DECISION ... widen-death-scope-bg0002 ...`` letters, i.e. exactly
    the shape this function looks for.  A finder that only walked
    ``notes_to_chief/**`` would satisfy the decision's words and still go
    red on the first sweep, which is the failure the decision exists to
    prevent.  So BOTH roots are walked, recursively.  The ``.md``-only rule
    below is unchanged and applies at every depth in both.
    """
    year, month, day, hour, minute = date_match.groups()
    stamp = "%s%s%s_%s%s" % (year, month, day, hour, minute)
    roots = [pf_bridge_dir / "notes_to_chief", pf_bridge_dir / "archive"]
    entries = []
    for root in roots:
        if root.is_dir():
            entries.extend(root.rglob("*"))
    if not entries:
        return False
    for entry in entries:
        name = entry.name
        # pf-adversary, round b08g3z, RAN this: the first draft accepted ANY
        # filename carrying the stamp, so the lane's own
        # "<letter>.md.CONSUMED.txt" stub -- a file this lane writes, in the
        # same directory, when it consumes the letter -- satisfied the check
        # on its own.  Delete COO's actual letter and the gate stayed green,
        # which is the exact hole the file's own opening paragraph says this
        # gate exists to close ("only a second, independently-timestamped
        # artifact in the other repository can").  A letter is a ``.md``
        # file; a stub, a marker and a receipt are not, and none of them can
        # stand in for one.
        if not name.endswith(".md"):
            continue
        if ".CONSUMED." in name:
            continue
        if not entry.is_file():
            continue
        if name.startswith(stamp) and "COO-DECISION" in name and "widen" in name:
            return True
    return False


class WideningRulingSchemaGateTests(unittest.TestCase):
    """COO-DECISION b1647 item 3 + b1712 item 1, combined into one gate."""

    def test_widening_ruling_keys_are_frozen_or_carry_their_own_letter(self):
        # COO-DECISION b1712 item 2: sibling dir first (the house convention
        # every other bridge-lookup in this repo uses -- see BRIDGE_SIBLING
        # itself), PF_BRIDGE_DIR is the explicit override for a layout where
        # the two repositories are not siblings.  "not found = skip with a
        # reason, never silently pass" is b1712's own wording; BRIDGE_SIBLING
        # already prints exactly that reason, so it is reused rather than a
        # second one invented for the same fact.
        import os
        env = os.environ.get("PF_BRIDGE_DIR")
        if env and Path(env).is_dir():
            pf_bridge_dir = Path(env)
        else:
            BRIDGE_SIBLING.require(self)
            pf_bridge_dir = BRIDGE_SIBLING.paths[0]

        keys = list(mob_death.WIDENING_RULINGS.keys())
        self.assertTrue(keys, "WIDENING_RULINGS is empty -- nothing to gate")

        # The frozen tuple is CLOSED (b1712 item 1): it must equal exactly
        # the keys that fail the new schema today, neither more nor fewer,
        # so this also catches a key silently falling OUT of
        # WIDENING_RULINGS while its name lingers in the frozen tuple.
        live_non_conforming = {
            key for key in keys if _schema_date_match(key) is None
        }
        self.assertEqual(
            set(FROZEN_WIDENING_RULING_KEYS), live_non_conforming,
            "the closed frozen list no longer equals the set of keys that "
            "fail the b1647 schema -- see this file's own module docstring; "
            "a real new non-conforming key must go through the schema + "
            "letter path, never be hand-added to the frozen tuple",
        )

        failures = []
        warnings = []
        for key in keys:
            if key in FROZEN_WIDENING_RULING_KEYS:
                if _schema_date_match(key) is None:
                    warnings.append(key)
                continue
            date_match = _schema_date_match(key)
            if date_match is None:
                failures.append(
                    "%r is not in the frozen list and does not match the "
                    "b1647 schema (needs COO-DECISION/COO-RULING/"
                    "PANYA-DECISION + widen-death-scope + a trailing "
                    "<YYYY-MM-DDTHH:MM+07:00>)" % (key,)
                )
                continue
            if not _letter_exists_for(pf_bridge_dir, date_match):
                failures.append(
                    "%r matches the new schema but no notes_to_chief file "
                    "stamped with its trailing date and naming COO-DECISION "
                    "+ widen was found under %s"
                    % (key, pf_bridge_dir / "notes_to_chief")
                )

        for warning in warnings:
            print(
                "WARN [frozen, pre-schema key, COO-DECISION b1712 item 3]: "
                "%r" % (warning,)
            )

        self.assertFalse(failures, "\n".join(failures))


class LetterFinderReachesTheWholeMailboxTests(unittest.TestCase):
    """COO-DECISION 2026-09-07T05:46+07:00 item 2: a filed letter still counts.

    These tests build their own bridge-shaped directory in a temporary
    folder, so they need NO sibling checkout and run on the single-repo
    Windows gate as well -- which matters, because the defect they guard
    against (a letter swept into the archive taking a live ruling key red
    with it) would otherwise only ever be discovered weeks later, by
    whoever next ran the gate on a machine that had the sibling.
    """

    #: The shape of a real key that reaches the letter check: schema-
    #: conforming, so ``_schema_date_match`` returns its trailing date.  This
    #: is the bg0001 key as it stands after round b08g3z's rename.
    KEY = (
        "COO-RULING-20260907-0405 widen-death-scope-bg0001 "
        "2026-09-07T04:05+07:00"
    )
    LETTER = (
        "20260907_0405_COO-DECISION-widen-death-scope-bg0001-succeeds-"
        "0041-LANE-B.md"
    )

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.bridge = Path(self.tmp.name)
        (self.bridge / "notes_to_chief").mkdir()
        (self.bridge / "archive").mkdir()
        self.date_match = _schema_date_match(self.KEY)
        self.assertIsNotNone(
            self.date_match,
            "the key these tests are built on stopped matching the b1647 "
            "schema -- fix the key here before reading anything below",
        )

    def _write(self, relative, text="letter body\n"):
        target = self.bridge / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
        return target

    def test_a_letter_in_the_mailbox_is_found(self) -> None:
        self._write("notes_to_chief/" + self.LETTER)
        self.assertTrue(_letter_exists_for(self.bridge, self.date_match))

    def test_a_letter_swept_into_the_archive_is_still_found(self) -> None:
        """The case COO-DECISION 0546 item 2 names outright.  LANE-K's real
        sweep destinations are dated folders under ``archive/`` -- measured
        against the bridge checkout in round ot2cru, fourteen of them, e.g.
        ``archive/notes_to_chief_2026-09/``.  Reverting the finder to a
        single-level ``notes_to_chief`` scan turns this test red, which is
        the mutant this test exists to catch.
        """
        self._write("archive/notes_to_chief_2026-09/" + self.LETTER)
        self.assertTrue(_letter_exists_for(self.bridge, self.date_match))

    def test_a_letter_filed_deeper_still_is_found(self) -> None:
        self._write(
            "archive/notes_to_chief_2026-08/consumed/" + self.LETTER)
        self.assertTrue(_letter_exists_for(self.bridge, self.date_match))

    def test_no_letter_anywhere_is_red(self) -> None:
        """The other half of COO-DECISION 0546 item 2: recursion must not
        turn the check into one that always passes.  Nothing is written
        here at all.
        """
        self.assertFalse(_letter_exists_for(self.bridge, self.date_match))

    def test_a_letter_for_another_day_does_not_answer_for_this_key(self) -> None:
        self._write(
            "archive/notes_to_chief_2026-09/"
            "20260906_1647_COO-DECISION-widen-death-scope-bg0001.md")
        self.assertFalse(_letter_exists_for(self.bridge, self.date_match))

    def test_the_lanes_own_stub_still_cannot_stand_in_for_a_letter(self) -> None:
        """pf-adversary D-1 (round b08g3z), re-asserted at depth: the
        ``.md``-only rule has to survive the recursion, or walking the
        archive would hand the hole back -- ``.CONSUMED.txt`` stubs are
        swept along with the letters they mark, so after a sweep there are
        MORE of them below the archive than in the mailbox.
        """
        self._write("notes_to_chief/" + self.LETTER + ".CONSUMED.txt")
        self._write(
            "archive/notes_to_chief_2026-09/" + self.LETTER + ".CONSUMED.txt")
        self.assertFalse(_letter_exists_for(self.bridge, self.date_match))

    def test_a_directory_named_like_a_letter_is_not_a_letter(self) -> None:
        """Only reachable once the walk is recursive: ``rglob`` yields
        directories too, and a sweep that made a folder per letter would
        otherwise answer for it.
        """
        (self.bridge / "archive" / self.LETTER).mkdir()
        self.assertFalse(_letter_exists_for(self.bridge, self.date_match))
