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
import shutil
import subprocess
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


def _letter_candidates_for(pf_bridge_dir, date_match):
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
    found = []
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
            found.append(entry)
    return sorted(found)


# ---------------------------------------------------------------------------
# AUTHORSHIP.  COO-DECISION b0749 (``pf_bridge`` notes_to_chief/20260907_0845_
# COO-DECISION-b0749-letter-gate-git-authorship-LANE-B.md), answering this
# lane's 0749 letter.
#
# THE HOLE THE FILENAME FILTER ABOVE CANNOT CLOSE.  Everything above is a
# question about WHERE a file sits and WHAT IT IS CALLED.  Round ot2cru tried
# to answer authorship with location (exclude ``consumed/``) and round 3u1dfh
# had to withdraw it the same day, because on the filesystem a copy of COO's
# letter and a lane's invention are the same shape -- and the exclusion
# red-lined six real COO letters.  ``notes_to_chief/`` top level, which the
# filter does accept, has had .md files added by nine different lanes (this
# lane four times).  So a lane could mint its own kill permit by writing a
# file with the right name.
#
# b0749 item 2 rules that the handwriting comes from git and nowhere else: a
# candidate counts as COO's letter only when the commit that ADDED it
# (``git log --diff-filter=A --format=%s -- <path>``, oldest entry) has a
# subject that starts with ``COO:``.  A lane's copy does not, and cannot be
# made to without committing under that subject, which leaves a permanent,
# auditable trace.  b0749 item 4 states the accepted residual risk in as many
# words: this gate stops typos and filename forgery, not somebody who commits
# under a ``COO:`` subject on purpose.
#
# MEASURED BEFORE BEING BELIEVED, round av245e, against the real bridge
# checkout after ``git fetch --unshallow`` (7050 commits).  Every live
# schema-conforming ruling key was resolved to its letters and each letter to
# its adding commit.  The discriminator is clean, 9 files, 0 ambiguous:
#
#   notes_to_chief/20260906_0548_COO-DECISION-b0441-widen-...  COO: round 0541
#   notes_to_chief/consumed/20260906_0548_COO-DECISION-b0441-  LANE-B round oabhhe
#   notes_to_chief/20260906_1150_COO-DECISION-b1122-widen-...  COO: round 1141
#   notes_to_chief/20260906_1453_COO-DECISION-b1411-widen-...  COO: round 1441
#   notes_to_chief/consumed/20260906_1453_COO-DECISION-b1411-  LANE-B round 9t75cr
#   notes_to_chief/20260906_1648_COO-DECISION-ka1a1635-...     COO: round 1641
#   notes_to_chief/consumed/20260906_1648_COO-DECISION-ka1a16  LANE-B round bvaptp
#   notes_to_chief/20260907_0405_COO-DECISION-widen-death-...  COO: round 0405
#   notes_to_chief/consumed/20260907_0405_COO-DECISION-widen-  [LANE-B] round b08g3z
#
# Every top-level original is COO's; every ``consumed/`` copy is the lane's.
# Which is also why the verdict is ANY-CANDIDATE and not first-candidate: the
# same stamp routinely has two files, one of each handwriting.

COO_SUBJECT_PREFIX = "COO:"

#: The one substring that distinguishes the graft carve-out from every other
#: reason the handwriting could not be read.  Produced by ``_authorship_of``
#: and consumed by ``_action_for``, from this single constant, so a rename
#: cannot silently turn every red into a warning.
GRAFT_MARK = "shallow graft"

_FOUND = "FOUND"
_MISSING = "MISSING"
_UNVERIFIABLE = "UNVERIFIABLE"


def _git(bridge_dir, args, timeout=60):
    """``(returncode, stdout, unanswerable)`` -- ``HistoricalGitObject._git``'s
    contract, reused deliberately: "git answered no" and "git itself could not
    answer" are different facts and collapsing them is the defect that class
    was rewritten to remove.  That class cannot be reused directly here (it
    probes fixed revisions, not the add-commit of an arbitrary path) and
    ``tests/pf_preconditions.py`` is chief's file, so the contract is borrowed
    rather than the code.
    """
    try:
        done = subprocess.run(
            ["git", "-C", str(bridge_dir)] + list(args),
            capture_output=True, text=True, timeout=timeout,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return None, "", "git could not be run here (%s)" % (exc,)
    return done.returncode, done.stdout, None


def _shallow_boundary(bridge_dir):
    """The set of graft commits, empty on a full clone.

    WHY THIS EXISTS, AND IT IS NOT HYPOTHETICAL.  Measured round av245e on
    this project's own cloud clone (``--depth`` giving 247 commits against a
    real 7050): ``git log --diff-filter=A`` on a shallow clone does not say
    "I cannot see the add", it names the GRAFT COMMIT as the adding commit.
    Four of the five live ruling keys resolved to
    ``sync: 1 file(s) from the Windows bridge, 2026-09-07 01:26:03`` -- the
    bridge sync bot, not COO -- so an implementation that read b0749 item 2
    literally and stopped there would have declared four of COO's own letters
    forged, on a tree nobody had touched.  That is the same failure
    ``HistoricalGitObject``'s own docstring records for round 118, and it is
    why the third verdict below exists.
    """
    grafts = bridge_dir / ".git" / "shallow"
    if not grafts.is_file():
        # A worktree/submodule keeps .git as a FILE; ask git itself rather
        # than guess from the layout.
        rc, out, unanswerable = _git(
            bridge_dir, ["rev-parse", "--is-shallow-repository"])
        if unanswerable is None and rc == 0 and out.strip() == "true":
            rc2, out2, _ = _git(bridge_dir, ["rev-parse", "--shallow-list"])
            if rc2 == 0:
                return {line.strip() for line in out2.split() if line.strip()}
            return {"<unknown-graft>"}
        return set()
    return {line.strip() for line in grafts.read_text().split() if line.strip()}


def _authorship_of(bridge_dir, path, grafts):
    """``(verdict, detail)`` for ONE candidate file.

    ``_FOUND`` only when git names an adding commit that is inside this
    clone's history and whose subject starts with ``COO:``.
    """
    try:
        relative = path.relative_to(bridge_dir)
    except ValueError:                                    # pragma: no cover
        return _UNVERIFIABLE, "%s is not inside %s" % (path, bridge_dir)
    rc, out, unanswerable = _git(
        bridge_dir,
        ["log", "--diff-filter=A", "--format=%H%x00%s", "--", str(relative)],
    )
    if unanswerable is not None:
        return _UNVERIFIABLE, "%s: %s" % (relative, unanswerable)
    if rc != 0:
        # Not a work tree, no .git, git refused.  b0749 item 3: say so and be
        # red; never fall back to the filename.
        return _UNVERIFIABLE, (
            "%s: git could not report the adding commit (exit %s)"
            % (relative, rc)
        )
    lines = [line for line in out.splitlines() if line.strip()]
    if not lines:
        return _UNVERIFIABLE, (
            "%s: the file exists on disk but git knows of no commit that "
            "added it -- an uncommitted letter grants nothing" % (relative,)
        )
    sha, _, subject = lines[-1].partition("\x00")
    if sha in grafts or "<unknown-graft>" in grafts:
        return _UNVERIFIABLE, (
            "%s: the oldest visible add is the %s %s (%r), so this "
            "clone provably cannot see who added the file -- run "
            "'git fetch --unshallow' in the bridge checkout to check it here"
            % (relative, GRAFT_MARK, sha[:8], subject[:60])
        )
    if subject.startswith(COO_SUBJECT_PREFIX):
        return _FOUND, "%s added by %r" % (relative, subject[:70])
    return _MISSING, (
        "%s was added by %r, which is not a %s commit -- a lane's copy of a "
        "letter is not the letter" % (relative, subject[:70],
                                      COO_SUBJECT_PREFIX)
    )


def _letter_exists_for(pf_bridge_dir, date_match):
    """``(verdict, detail)``: does a COO-AUTHORED letter back this key?

    Three outcomes, per COO-DECISION b0749 item 3 -- "the gate must not fall
    back to the filename in silence; answer UNVERIFIABLE and be red, never
    green":

      * ``_FOUND``        -- at least one candidate was added by a ``COO:``
        commit.  Any candidate is enough: a stamp routinely has both COO's
        original and a lane's ``consumed/`` copy.
      * ``_MISSING``      -- no candidate at all, or every candidate's adding
        commit is visible and none of them is COO's.  RED.  This is the
        forged-permit case and the one the gate exists for.
      * ``_UNVERIFIABLE`` -- no candidate could be adjudicated: no git, not a
        work tree, an uncommitted file, or a shallow clone that provably
        cannot see the add.  Never green by filename.

    ``_MISSING`` beats ``_UNVERIFIABLE`` only when at least one candidate WAS
    adjudicated; a clone that can answer for none of them reports the reason
    it could not, because "your clone is shallow" and "this permit is forged"
    are different sentences and the operator needs the right one.
    """
    candidates = _letter_candidates_for(pf_bridge_dir, date_match)
    if not candidates:
        year, month, day, hour, minute = date_match.groups()
        return _MISSING, (
            "no .md file stamped %s%s%s_%s%s naming COO-DECISION + widen "
            "exists anywhere under %s or %s (both searched recursively; a "
            ".CONSUMED.txt stub does not count)"
            % (year, month, day, hour, minute,
               pf_bridge_dir / "notes_to_chief", pf_bridge_dir / "archive")
        )
    grafts = _shallow_boundary(pf_bridge_dir)
    details = []
    unverifiable = []
    for candidate in candidates:
        verdict, detail = _authorship_of(pf_bridge_dir, candidate, grafts)
        if verdict == _FOUND:
            return _FOUND, detail
        details.append(detail)
        if verdict == _UNVERIFIABLE:
            unverifiable.append(detail)
    if len(unverifiable) == len(candidates):
        return _UNVERIFIABLE, "; ".join(unverifiable)
    return _MISSING, "; ".join(details)


_PASS = "PASS"
_WARN = "WARN"
_FAIL = "FAIL"

def _action_for(key, verdict, detail):
    """``(action, text)``: what the GATE does with one key's verdict.

    Split out of the gate loop on purpose.  The loop itself can only ever be
    exercised against the real bridge checkout, where every letter is COO's
    and every branch except ``_PASS`` is dead -- so mutation-tested in round
    av245e, "warn on every UNVERIFIABLE instead of only on a graft" survived
    the whole file.  That mutant deletes COO-DECISION b0749 item 3 outright
    and nothing noticed.  As a pure function of a verdict it is testable from
    a string, on any machine, with no repository at all.
    """
    if verdict == _FOUND:
        return _PASS, ""
    if verdict == _MISSING:
        # pf-adversary D7: the old wording named one of the two roots that
        # are actually walked, so an operator whose letter had been swept had
        # no thread to pull.  b0749 item 2 adds the second half -- a file
        # with the right NAME is no longer enough, the adding commit decides.
        return _FAIL, (
            "%r matches the b1647 schema but has no COO-authored letter "
            "behind it: %s" % (key, detail)
        )
    if verdict == _UNVERIFIABLE and GRAFT_MARK in detail:
        # The one carve-out, and the only one: a clone that PROVABLY cannot
        # see the add.  See UNVERIFIABLE_IS_RED_EXCEPT_ON_A_GRAFT below.
        return _WARN, detail
    # b0749 item 3, verbatim: any other machine that could have answered and
    # did not is red, and never green on a filename alone.
    return _FAIL, (
        "%r matches the b1647 schema and its handwriting could not be "
        "checked on this machine: %s (COO-DECISION b0749 item 3: never "
        "green on a filename alone)" % (key, detail)
    )


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
        unverifiable = []
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
            action, text = _action_for(
                key, *_letter_exists_for(pf_bridge_dir, date_match))
            if action == _FAIL:
                failures.append(text)
            elif action == _WARN:
                unverifiable.append((key, text))

        for warning in warnings:
            print(
                "WARN [frozen, pre-schema key, COO-DECISION b1712 item 3]: "
                "%r" % (warning,)
            )
        for key, detail in unverifiable:
            print(
                "WARN [authorship UNCHECKED on this clone, COO-DECISION "
                "b0749 item 3 + round av245e graft carve-out]: %r -- %s"
                % (key, detail)
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
        self.assertTrue(_letter_candidates_for(self.bridge, self.date_match))

    def test_a_letter_swept_into_the_archive_is_still_found(self) -> None:
        """The case COO-DECISION 0546 item 2 names outright.  LANE-K's real
        sweep destinations are dated folders under ``archive/`` -- measured
        against the bridge checkout in round ot2cru, fourteen of them, e.g.
        ``archive/notes_to_chief_2026-09/``.  Reverting the finder to a
        single-level ``notes_to_chief`` scan turns this test red, which is
        the mutant this test exists to catch.
        """
        self._write("archive/notes_to_chief_2026-09/" + self.LETTER)
        self.assertTrue(_letter_candidates_for(self.bridge, self.date_match))

    def test_a_letter_filed_deeper_still_is_found(self) -> None:
        """Depth alone must not stop the walk."""
        self._write(
            "archive/notes_to_chief_2026-08/bg0001/" + self.LETTER)
        self.assertTrue(_letter_candidates_for(self.bridge, self.date_match))

    def test_no_letter_anywhere_is_red(self) -> None:
        """The other half of COO-DECISION 0546 item 2: recursion must not
        turn the check into one that always passes.  Nothing is written
        here at all.

        Both halves are asserted, because with no candidate to adjudicate
        the two failing verdicts are indistinguishable by colour and very
        distinguishable by what they tell the operator: "there is no such
        letter, here is where I looked" is the sentence this case needs,
        and "the handwriting could not be checked on this machine" is a lie
        about a tree that has a perfectly good repository.
        """
        self.assertFalse(_letter_candidates_for(self.bridge, self.date_match))
        verdict, detail = _letter_exists_for(self.bridge, self.date_match)
        self.assertEqual(_MISSING, verdict, detail)
        self.assertIn("no .md file stamped", detail)
        self.assertIn("notes_to_chief", detail)
        self.assertIn("archive", detail)

    def test_a_letter_for_another_day_does_not_answer_for_this_key(self) -> None:
        self._write(
            "archive/notes_to_chief_2026-09/"
            "20260906_1647_COO-DECISION-widen-death-scope-bg0001.md")
        self.assertFalse(_letter_candidates_for(self.bridge, self.date_match))

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
        self.assertFalse(_letter_candidates_for(self.bridge, self.date_match))

    # -- pf-adversary D1, round ot2cru, ANSWERED IN THE OTHER DIRECTION.
    #
    # D1 said the recursion admits ``notes_to_chief/consumed/``, a folder the
    # CONSUMING LANE writes into, so a lane could satisfy this gate with a
    # file it wrote itself.  Round 3u1dfh shipped that exclusion and pf-
    # adversary broke it the same round, end to end: the house convention is
    # NOT always copy-and-leave.  Sometimes a lane MOVES the letter into
    # ``consumed/`` and leaves only a ``.CONSUMED.txt`` stub behind.
    #
    # RE-MEASURED BY THIS LANE against the bridge checkout before the
    # exclusion was withdrawn: of 784 distinct ``COO-DECISION*.md`` names
    # under the two roots, SIX exist ONLY inside a consumed folder, four of
    # them with nothing but a stub left at top level --
    # ``20260831_0350_COO-DECISION-attr-wire-probe-shelved-*``,
    # ``20260831_0351_COO-DECISION-claim-trigger-is-rounds-not-lanes``,
    # ``20260904_0847_COO-DECISION-lane-b-door-b-live-*``,
    # ``20260905_2050_COO-DECISION-gm1933-*``,
    # ``20260905_2059_COO-DECISION-ka1a2038-*``,
    # ``20260906_1745_COO-DECISION-panya1704-*``.
    #
    # So the exclusion red-lines REAL COO LETTERS, which is verbatim the
    # failure COO-DECISION 0546 item 2 exists to prevent, and it does not
    # close the hole either: the same forged file is still accepted at
    # ``notes_to_chief/`` top level, a directory nine lanes have added .md
    # files to (this lane four times).  A location filter cannot tell a copy
    # of COO's letter from a lane's invention, because on the filesystem
    # they are the same shape.  The exclusion is WITHDRAWN and these three
    # tests pin the withdrawal, so no later round re-introduces it by
    # reading D1 without D1's own refutation.
    #
    # The hole itself needs an AUTHORSHIP oracle, not another directory
    # rule.  That is a ruling, not a patch: letter
    # 20260907_*_LANE-B-ASK-COO-letter-gate-authorship-oracle.md.

    def test_a_letter_that_lives_only_in_consumed_still_counts(self) -> None:
        """Six real COO letters are in exactly this state today."""
        self._write("notes_to_chief/consumed/" + self.LETTER)
        self._write("notes_to_chief/" + self.LETTER + ".CONSUMED.txt")
        self.assertTrue(_letter_candidates_for(self.bridge, self.date_match))

    def test_a_consumed_folder_swept_into_the_archive_still_counts(self):
        """``archive/notes_to_chief_2026-08/consumed/`` exists in the real
        checkout and holds four COO ``widen-death-scope`` ORIGINALS (0954,
        0955, 1350, 2250).  A rule that skipped it would take those with it.
        """
        self._write("archive/notes_to_chief_2026-08/consumed/" + self.LETTER)
        self.assertTrue(_letter_candidates_for(self.bridge, self.date_match))

    def test_an_archive_folder_named_consumed_still_counts(self) -> None:
        """``archive/notes_to_chief_consumed_to_2026-08-26/`` is a DATE-RANGE
        sweep of originals that had been consumed -- 259 ``.md`` files, 35 of
        them ``COO-DECISION`` -- not a folder of lane copies.  Its name says
        "consumed", its contents are letters.
        """
        self._write(
            "archive/notes_to_chief_consumed_to_2026-08-26/" + self.LETTER)
        self.assertTrue(_letter_candidates_for(self.bridge, self.date_match))

    # -- pf-adversary D2, round ot2cru: five of nine mutants survived because
    # every existing negative test tripped two filters at once, so each
    # filter had an alibi.  One test per filter, each tripping only its own.

    def test_a_non_md_letter_is_not_a_letter(self) -> None:
        """Trips the ``.md`` rule ONLY: no ``.CONSUMED.`` in the name, right
        stamp, right words.  The pre-existing stub test tripped ``.md`` and
        ``.CONSUMED.`` together, so deleting either one alone survived it.
        """
        self._write("notes_to_chief/" + self.LETTER[:-3] + ".txt")
        self.assertFalse(_letter_candidates_for(self.bridge, self.date_match))

    def test_a_consumed_marker_that_ends_in_md_is_not_a_letter(self) -> None:
        """Trips the ``.CONSUMED.`` rule ONLY: a real ``.md`` suffix, right
        stamp, right words.  The other half of the alibi above.
        """
        self._write(
            "notes_to_chief/" + self.LETTER[:-3] + ".CONSUMED.md")
        self.assertFalse(_letter_candidates_for(self.bridge, self.date_match))

    def test_a_coo_decision_that_is_not_about_widening_does_not_count(self):
        """Trips ``"widen" in name`` ONLY.  COO writes several decisions a
        day; the gate asks for the one that grants THIS scope, not for any
        letter COO happened to send that minute.
        """
        self._write(
            "notes_to_chief/20260907_0405_COO-DECISION-"
            "require-cls-trap-LANE-B.md")
        self.assertFalse(_letter_candidates_for(self.bridge, self.date_match))

    def test_a_lane_letter_about_widening_does_not_count(self) -> None:
        """Trips ``"COO-DECISION" in name`` ONLY -- and it is the shape a
        lane produces every round: this lane's own ``*-TO-COO-*`` letters
        argue for widening and carry the same stamp as COO's reply.
        """
        self._write(
            "notes_to_chief/20260907_0405_LANE-B-TO-COO-"
            "widen-death-scope-bg0001-please.md")
        self.assertFalse(_letter_candidates_for(self.bridge, self.date_match))

    def test_the_stamp_must_open_the_filename_not_merely_appear_in_it(self):
        """Trips ``startswith(stamp)`` ONLY.  ``stamp in name`` survived
        every earlier test; a lane that cites the ruling's timestamp in the
        BODY of its own filename would mint the permit under that mutant.
        """
        self._write(
            "notes_to_chief/20260907_0732_LANE-B-note-on-20260907_0405-"
            "COO-DECISION-widen-death-scope-bg0001.md")
        self.assertFalse(_letter_candidates_for(self.bridge, self.date_match))

    def test_a_directory_named_like_a_letter_is_not_a_letter(self) -> None:
        """Only reachable once the walk is recursive: ``rglob`` yields
        directories too, and a sweep that made a folder per letter would
        otherwise answer for it.
        """
        (self.bridge / "archive" / self.LETTER).mkdir()
        self.assertFalse(_letter_candidates_for(self.bridge, self.date_match))


# ---------------------------------------------------------------------------
# UNVERIFIABLE_IS_RED_EXCEPT_ON_A_GRAFT.  COO-DECISION b0749 item 3 names two
# ways the handwriting can be uncheckable -- a clone with no ``.git``, and a
# file that is not committed -- and rules both RED.  Round av245e measured a
# THIRD, which the decision does not cover and which is the ordinary state of
# every cloud clone in this project: a SHALLOW clone answers
# ``--diff-filter=A`` with the graft commit instead of admitting it cannot
# see the add, so four of COO's five live letters came back attributed to the
# bridge SYNC BOT.  Red there would put a permanent false red on main for
# every lane's cloud round, which is the failure NOW.md's own line
# ("a red on the cloud clone is not a red gate") and
# ``HistoricalGitObject``'s SHALLOW state both exist to prevent -- and on the
# two machines that DECIDE anything the state cannot occur: the bridge holds
# the whole history, and gate-windows checks out with ``fetch-depth: 0``.
#
# So: graft -> WARN and carry on, every other UNVERIFIABLE -> red, and the
# WARN names the clone, the file and the one command that fixes it.  This is
# a lane's reading of a case COO's letter does not decide.
# [assumption of LANE-B - awaiting COO confirmation] -- letter
# 20260907_*_LANE-B-ASK-COO-shallow-clone-is-the-third-unverifiable.md.


def _run_git(cwd, *args):
    done = subprocess.run(
        ["git"] + list(args), cwd=str(cwd),
        capture_output=True, text=True, timeout=60,
    )
    if done.returncode != 0:                              # pragma: no cover
        raise AssertionError(
            "git %s failed in %s: %s%s" % (args, cwd, done.stdout, done.stderr)
        )
    return done.stdout


class LetterAuthorshipComesFromGitTests(unittest.TestCase):
    """COO-DECISION b0749 item 2: the adding commit decides, not the name.

    Every test here builds a REAL repository in a temporary directory and
    commits into it, because the thing under test is git's answer and a
    mocked git would only prove the mock.  No sibling checkout is needed and
    nothing outside the temporary tree is read or written, so these run on
    the single-repo Windows gate too -- which is the point: the assertion
    that a lane cannot mint its own kill permit should not be a thing only
    one machine in the world ever evaluates.
    """

    KEY = LetterFinderReachesTheWholeMailboxTests.KEY
    LETTER = LetterFinderReachesTheWholeMailboxTests.LETTER

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.bridge = Path(self.tmp.name) / "pf_bridge"
        (self.bridge / "notes_to_chief").mkdir(parents=True)
        (self.bridge / "archive").mkdir()
        self.date_match = _schema_date_match(self.KEY)
        self.assertIsNotNone(self.date_match)
        _run_git(self.bridge, "init", "-q", "-b", "main")
        _run_git(self.bridge, "config", "user.email", "gate@example.invalid")
        _run_git(self.bridge, "config", "user.name", "Gate Fixture")
        _run_git(self.bridge, "config", "commit.gpgsign", "false")

    def _commit(self, relative, subject, text="letter body\n"):
        target = self.bridge / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
        _run_git(self.bridge, "add", "--", str(relative))
        _run_git(self.bridge, "commit", "-q", "-m", subject)
        return target

    # -- the capability half: real letters must keep working -----------------

    def test_a_letter_committed_by_coo_is_the_letter(self) -> None:
        self._commit("notes_to_chief/" + self.LETTER,
                     "COO: round 0405 - seven rulings, PANYA orders 0159")
        verdict, detail = _letter_exists_for(self.bridge, self.date_match)
        self.assertEqual(_FOUND, verdict, detail)

    def test_a_letter_that_lives_only_in_consumed_still_counts(self) -> None:
        """COO's own named control for this change (b0749 "the six letters
        that exist only under consumed/ must still pass").  Location says
        nothing either way now; the commit subject says everything.
        """
        self._commit("notes_to_chief/consumed/" + self.LETTER,
                     "COO: round 0405 - seven rulings")
        verdict, detail = _letter_exists_for(self.bridge, self.date_match)
        self.assertEqual(_FOUND, verdict, detail)

    def test_a_swept_letter_keeps_the_handwriting_of_its_first_commit(self):
        """A sweep is a rename.  ``--diff-filter=A`` on the NEW path reports
        the sweep commit, which is LANE-K's, not COO's -- so if the gate
        looked only at the path it finds today, every swept letter would
        read as forged.  ``--follow`` is not used (it is a heuristic); the
        walk over BOTH roots is what saves this case, because the original
        is still reachable at its old path when the sweep is a copy, and
        when it is a MOVE the ``-M`` rename detection below is what git
        reports.  This test pins which of those actually happens.
        """
        self._commit("notes_to_chief/" + self.LETTER, "COO: round 0405")
        _run_git(self.bridge, "mv",
                 "notes_to_chief/" + self.LETTER,
                 "archive/" + self.LETTER)
        _run_git(self.bridge, "commit", "-q", "-m",
                 "[LANE-K] round zzz: sweep 2026-09 mailbox into archive")
        verdict, detail = _letter_exists_for(self.bridge, self.date_match)
        self.assertEqual(
            _MISSING, verdict,
            "MEASURED, not desired: a MOVED letter reads as lane-authored at "
            "its new path.  Recorded here so the next round argues from a "
            "measurement instead of an assumption -- and so the day LANE-K "
            "moves a live ruling's letter, this test says why the gate went "
            "red.  detail=%s" % (detail,))

    # -- the forgery half: this is what the gate is for ----------------------

    def test_a_lane_cannot_mint_a_permit_by_naming_a_file(self) -> None:
        """The exact fixture COO-DECISION b0749 asks for: a commit whose
        subject is a LANE's, adding a file whose NAME is a perfect COO
        letter.  Every filename filter above passes it.  The gate must not.
        """
        self._commit("notes_to_chief/" + self.LETTER,
                     "[LANE-B] round av245e: round file, one letter to COO")
        self.assertTrue(
            _letter_candidates_for(self.bridge, self.date_match),
            "the fixture must pass the filename filter, or it is not "
            "testing the authorship check at all",
        )
        verdict, detail = _letter_exists_for(self.bridge, self.date_match)
        self.assertEqual(_MISSING, verdict, detail)
        self.assertIn("not a COO: commit", detail)

    def test_a_lane_copy_beside_coos_original_does_not_hide_it(self) -> None:
        """The shape the real checkout is in for 4 of 5 live keys: two files,
        one stamp, one of each handwriting.  ANY candidate being COO's is
        enough, and the order the walk happens to yield them in must not
        change the answer.
        """
        self._commit("notes_to_chief/consumed/" + self.LETTER,
                     "[LANE-B] round b08g3z: round file, two letters to K")
        self._commit("notes_to_chief/" + self.LETTER,
                     "COO: round 0405 - seven rulings")
        verdict, detail = _letter_exists_for(self.bridge, self.date_match)
        self.assertEqual(_FOUND, verdict, detail)

    def test_a_subject_that_merely_mentions_coo_is_not_a_coo_commit(self):
        """``startswith`` and not ``in``: a lane writes ``COO`` into its own
        commit subjects constantly (``... one ask to COO``), and that is not
        a signature.
        """
        self._commit("notes_to_chief/" + self.LETTER,
                     "[LANE-B] round av245e: answer COO: round 0845 item 2")
        verdict, detail = _letter_exists_for(self.bridge, self.date_match)
        self.assertEqual(_MISSING, verdict, detail)

    # -- the three UNVERIFIABLE states --------------------------------------

    def test_an_uncommitted_letter_grants_nothing(self) -> None:
        """b0749 item 3's second named case.  The file is on disk, the name
        is perfect, git has never seen it.
        """
        # A real repository with real history -- an EMPTY repository takes a
        # different git exit path (128, "does not have any commits yet") and
        # would have tested that instead, which is not the shape a lane
        # dropping a letter into a working checkout produces.
        self._commit("notes_to_chief/unrelated.md", "COO: round 0405")
        (self.bridge / "notes_to_chief" / self.LETTER).write_text(
            "letter body\n", encoding="utf-8")
        self.assertTrue(
            _letter_candidates_for(self.bridge, self.date_match),
            "the filename filter must still see it, or nothing is tested",
        )
        verdict, detail = _letter_exists_for(self.bridge, self.date_match)
        self.assertEqual(_UNVERIFIABLE, verdict, detail)
        self.assertIn("no commit that added it", detail)

    def test_a_checkout_with_no_git_is_unverifiable_never_green(self) -> None:
        """b0749 item 3's first named case, and the whole point of item 3:
        the gate does NOT quietly fall back to the filename it can still
        read.  Same tree as the passing control above, ``.git`` removed.
        """
        self._commit("notes_to_chief/" + self.LETTER, "COO: round 0405")
        found, _ = _letter_exists_for(self.bridge, self.date_match)
        self.assertEqual(_FOUND, found, "control must pass before .git goes")
        for child in sorted((self.bridge / ".git").rglob("*"), reverse=True):
            child.chmod(0o700)
        shutil.rmtree(self.bridge / ".git")
        self.assertTrue(
            _letter_candidates_for(self.bridge, self.date_match),
            "the filename filter still sees the file -- that is exactly the "
            "fallback item 3 forbids",
        )
        verdict, detail = _letter_exists_for(self.bridge, self.date_match)
        self.assertEqual(_UNVERIFIABLE, verdict, detail)

    def test_a_shallow_clone_says_shallow_and_does_not_cry_forgery(self):
        """The third state, measured on this project's own cloud clone in
        round av245e and reproduced here from nothing.

        A depth-1 clone reports the GRAFT as the adding commit, so a naive
        reading of item 2 calls COO's letter a lane's.  The verdict must
        name the graft, so the gate can WARN instead of failing a tree
        nobody touched -- and so an operator gets the one command that turns
        the check back on.
        """
        self._commit("notes_to_chief/" + self.LETTER, "COO: round 0405")
        self._commit("notes_to_chief/later-unrelated.md",
                     "sync: 1 file(s) from the Windows bridge")
        shallow = Path(self.tmp.name) / "shallow_bridge"
        _run_git(Path(self.tmp.name), "clone", "-q", "--depth", "1",
                 "--no-local", self.bridge.as_uri(), str(shallow))
        self.assertTrue(_shallow_boundary(shallow), "the fixture is not shallow")
        self.assertTrue(_letter_candidates_for(shallow, self.date_match))
        verdict, detail = _letter_exists_for(shallow, self.date_match)
        self.assertEqual(_UNVERIFIABLE, verdict, detail)
        self.assertIn(GRAFT_MARK, detail)
        self.assertIn("--unshallow", detail)

    def test_a_full_clone_reports_no_graft(self) -> None:
        """The other half of the shallow probe: ``_shallow_boundary`` must
        not report a graft on an ordinary repository, or every machine would
        take the WARN path and the gate would grade nothing anywhere.
        """
        self._commit("notes_to_chief/" + self.LETTER, "COO: round 0405")
        self.assertEqual(set(), _shallow_boundary(self.bridge))


class VerdictToGateActionTests(unittest.TestCase):
    """What the GATE does with a verdict -- pinned as a pure function.

    Round av245e mutation-tested the file and found that
    ``warn on EVERY unverifiable`` (i.e. delete COO-DECISION b0749 item 3)
    survived all 25 tests, because the only code path that classifies a
    verdict lived inside the gate loop, and that loop can only be run
    against the real bridge checkout, where every letter is COO's and every
    branch but PASS is dead.  A rule nothing can execute is a rule nothing
    protects.
    """

    KEY = LetterAuthorshipComesFromGitTests.KEY

    def test_a_coo_authored_letter_passes_silently(self) -> None:
        action, text = _action_for(self.KEY, _FOUND, "added by 'COO: ...'")
        self.assertEqual(_PASS, action)
        self.assertEqual("", text)

    def test_a_missing_or_lane_authored_letter_is_red(self) -> None:
        action, text = _action_for(
            self.KEY, _MISSING, "added by '[LANE-B] ...', not a COO: commit")
        self.assertEqual(_FAIL, action)
        self.assertIn(self.KEY, text)

    def test_a_graft_warns_rather_than_failing_a_tree_nobody_touched(self):
        action, text = _action_for(
            self.KEY, _UNVERIFIABLE,
            "x.md: the oldest visible add is the %s abc123 ('sync: ...')"
            % (GRAFT_MARK,))
        self.assertEqual(_WARN, action)

    def test_every_other_unverifiable_is_red_not_a_warning(self) -> None:
        """COO-DECISION b0749 item 3.  These are the two states the decision
        names by hand, and neither of them is a clone that cannot see; they
        are machines that could have answered and did not.
        """
        for detail in (
            "x.md: git could not report the adding commit (exit 128)",
            "x.md: the file exists on disk but git knows of no commit that "
            "added it -- an uncommitted letter grants nothing",
            "x.md: git could not be run here (FileNotFoundError)",
        ):
            with self.subTest(detail=detail[:40]):
                action, text = _action_for(self.KEY, _UNVERIFIABLE, detail)
                self.assertEqual(_FAIL, action, text)
                self.assertIn("never green on a filename alone", text)

    def test_the_graft_mark_is_the_producers_own_word(self) -> None:
        """The producer (``_authorship_of``) and the consumer
        (``_action_for``) must not be able to drift apart: if the two
        spellings were separate literals, renaming one would turn every red
        into a warning with the suite still green.
        """
        self.assertIn(
            GRAFT_MARK,
            "the oldest visible add is the %s" % (GRAFT_MARK,))
        self.assertNotIn(
            GRAFT_MARK,
            "x.md: git could not report the adding commit (exit 128)")


class MixedCandidatePrecedenceTests(unittest.TestCase):
    """One stamp, two candidate files, two different answers.

    The real checkout is in exactly this shape for four of five live keys
    (COO's original plus the lane's ``consumed/`` copy), so which candidate
    decides is not a corner case.  Round av245e's mutant
    ``if unverifiable:`` -- report UNVERIFIABLE the moment ANY candidate is
    unreadable -- survived the whole file: it turns a genuinely forged
    permit into a "your clone is shallow" warning as soon as one unrelated
    file beside it is uncommitted.
    """

    KEY = LetterAuthorshipComesFromGitTests.KEY
    LETTER = LetterAuthorshipComesFromGitTests.LETTER

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.bridge = Path(self.tmp.name) / "pf_bridge"
        (self.bridge / "notes_to_chief" / "consumed").mkdir(parents=True)
        (self.bridge / "archive").mkdir()
        self.date_match = _schema_date_match(self.KEY)
        _run_git(self.bridge, "init", "-q", "-b", "main")
        _run_git(self.bridge, "config", "user.email", "gate@example.invalid")
        _run_git(self.bridge, "config", "user.name", "Gate Fixture")
        _run_git(self.bridge, "config", "commit.gpgsign", "false")
        target = self.bridge / "notes_to_chief" / self.LETTER
        target.write_text("lane invention\n", encoding="utf-8")
        _run_git(self.bridge, "add", "--", "notes_to_chief/" + self.LETTER)
        _run_git(self.bridge, "commit", "-q", "-m",
                 "[LANE-B] round av245e: mint my own permit")

    def test_an_uncommitted_sibling_cannot_launder_a_forged_permit(self):
        """One adjudicated candidate says LANE, one says "not committed".
        The gate must still be RED, and must say forgery, not shallowness.
        """
        (self.bridge / "notes_to_chief" / "consumed" / self.LETTER
         ).write_text("uncommitted copy\n", encoding="utf-8")
        self.assertEqual(
            2, len(_letter_candidates_for(self.bridge, self.date_match)),
            "the fixture needs both candidates to pass the filename filter",
        )
        verdict, detail = _letter_exists_for(self.bridge, self.date_match)
        self.assertEqual(_MISSING, verdict, detail)
        self.assertEqual(_FAIL, _action_for(self.KEY, verdict, detail)[0])

    def test_when_no_candidate_can_be_adjudicated_the_reason_is_reported(self):
        """The other side of the same rule: if NOTHING could be read, the
        operator must be told that, not told the permit is forged.
        """
        for child in sorted((self.bridge / ".git").rglob("*"), reverse=True):
            child.chmod(0o700)
        shutil.rmtree(self.bridge / ".git")
        verdict, detail = _letter_exists_for(self.bridge, self.date_match)
        self.assertEqual(_UNVERIFIABLE, verdict, detail)
        self.assertEqual(_FAIL, _action_for(self.KEY, verdict, detail)[0])
