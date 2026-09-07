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

import os
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
#: TWO unverifiable codes, not one string a consumer has to re-read.
#: pf-adversary D5 (round av245e): the graft carve-out used to be decided by
#: ``GRAFT_MARK in detail``, and ``detail`` interpolates a candidate's PATH and
#: a commit SUBJECT -- free text this repository does not control.  An
#: uncommitted file under ``archive/shallow graft scratch/`` therefore warned
#: where it had to be red, and any commit subject could do the same.  The
#: producer (``_authorship_of``) now says WHICH unverifiable this is and the
#: consumer (``_action_for``) never parses prose.  ``GRAFT_MARK`` below stays,
#: but only as words for a human -- no decision reads it any more.
_UNVERIFIABLE_GRAFT = "UNVERIFIABLE_GRAFT"
_UNVERIFIABLE_OTHER = "UNVERIFIABLE_OTHER"
_UNVERIFIABLE_VERDICTS = (_UNVERIFIABLE_GRAFT, _UNVERIFIABLE_OTHER)


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


def _ascii(text):
    """``text`` with every non-ASCII character escaped.

    pf-adversary D11 (round av245e): this file is the first place where text
    this repository does not control (a commit subject, a path) reaches
    ``print()``.  The bridge console is cp874:strict -- a Thai subject in a
    letter's commit message would raise ``UnicodeEncodeError`` inside the
    gate and kill the run with a traceback that names encoding, not
    handwriting.  House rule (``AGENTS.md`` section 7): everything printed is
    ASCII.
    """
    return str(text).encode("ascii", "backslashreplace").decode("ascii")


def _shallow_boundary(bridge_dir):
    """The set of graft commits, empty unless git itself says "shallow".

    WHY THIS EXISTS, AND IT IS NOT HYPOTHETICAL.  Measured round av245e on
    this project's own cloud clone (``--depth`` giving 247 commits against a
    real 7050): ``git log --diff-filter=A`` on a shallow clone does not say
    "I cannot see the add", it names the GRAFT COMMIT as the adding commit.
    Four of the five ruling DATE STAMPS resolved to
    ``sync: 1 file(s) from the Windows bridge, 2026-09-07 01:26:03`` -- the
    bridge sync bot, not COO -- so an implementation that read b0749 item 2
    literally and stopped there would have declared four of COO's own letters
    forged, on a tree nobody had touched.  That is the same failure
    ``HistoricalGitObject``'s own docstring records for round 118, and it is
    why the third verdict exists.

    ASK GIT, NEVER THE LAYOUT (pf-adversary D3, round av245e, the defect that
    pulled the marker off ``pirate-force-server#1008``).  The first draft
    guessed: no ``.git/shallow`` FILE and it fell back to
    ``git rev-parse --shallow-list``, which is not a git option at all --
    ``rev-parse`` echoes an unknown token back and exits 0, so the set became
    ``{"--shallow-list"}``, no sha ever matched it, and every letter in a
    LINKED WORKTREE OF A SHALLOW CLONE was reported forged.  That is not a
    corner: this house's own pf-adversary protocol builds a worktree on the
    cloud clone, so every lane running a full review would have been told
    COO's letters are fakes.  ``--git-path shallow`` is the option that
    exists, and it resolves through worktrees and submodules -- where ``.git``
    is a FILE -- without this function knowing anything about either layout.

    PROVABLE OR NOTHING (COO-DECISION 0945 item 1): the carve-out needs a sha
    git actually lists as a graft.  "I could not find the file" derives
    nothing and returns ``set()``, which lands on the RED path, because a
    carve-out that can be reached by a failed lookup is a carve-out anyone
    can reach by breaking a lookup.
    """
    rc, out, unanswerable = _git(
        bridge_dir, ["rev-parse", "--is-shallow-repository"])
    if unanswerable is not None or rc != 0 or out.strip() != "true":
        return set()
    rc2, out2, unanswerable2 = _git(
        bridge_dir, ["rev-parse", "--git-path", "shallow"])
    if unanswerable2 is not None or rc2 != 0 or not out2.strip():
        return set()
    grafts = Path(out2.strip())
    if not grafts.is_absolute():
        grafts = bridge_dir / grafts
    if not grafts.is_file():
        return set()
    return {line.strip() for line in grafts.read_text().split() if line.strip()}


def _add_records(bridge_dir, relative, follow):
    """``(unanswerable, rc, records)`` -- every commit git calls an ADD of
    ``relative``, newest first, as ``[sha, subject, path]``.

    ``follow=True`` asks git to walk back through renames as well, and then
    ``--name-status`` is what says WHICH path each older add was of.  The
    marker byte in the format keeps commit headers apart from the
    name-status lines without parsing either as the other.
    """
    args = ["log", "--diff-filter=A", "--format=%x01%H%x00%s"]
    if follow:
        args = args + ["--follow", "--name-status"]
    rc, out, unanswerable = _git(bridge_dir, args + ["--", str(relative)])
    if unanswerable is not None or rc != 0:
        return unanswerable, rc, []
    records = []
    for line in out.splitlines():
        if line.startswith("\x01"):
            sha, _, subject = line[1:].partition("\x00")
            records.append([sha, subject, None])
        elif line.strip() and records and records[-1][2] is None:
            records[-1][2] = line.split("\t")[-1].strip()
    for record in records:
        if record[2] is None:
            record[2] = str(relative)
    return None, rc, records


def _authorship_of(bridge_dir, path, grafts):
    """``(verdict, detail)`` for ONE candidate file.

    ``_FOUND`` only when git names an adding commit that is inside this
    clone's history and whose subject starts with ``COO:``.

    TWO QUESTIONS, NOT ONE, AND THAT IS pf-adversary D1 (round av245e).
    "Who added this path" is not the same as "who wrote this letter" the
    moment LANE-K sweeps the mailbox: measured on the bridge checkout, all 14
    ``archive/`` letters that match this gate's filename filter report a
    sweep commit as their add, and ``git log --follow`` recovers ``COO: ...``
    for 14 of 14.  The finder already walks ``archive/`` so a swept letter
    still COUNTS; without the second question that only moved the failure one
    step, and the next sweep would have turned all 19 keys red at once with
    nobody having touched a thing.  COO-DECISION 0945 item 3 now also forbids
    MOVING a letter that backs a live key (copy it, never ``git mv``) -- but
    a gate that is only correct while every lane remembers a convention is
    the kind of gate this file exists to stop being.

    WHY THE SECOND QUESTION CANNOT BE ``--follow`` ALONE, MEASURED HERE
    rather than reasoned about: git's follow sets ``find_copies_harder``, so
    it walks back through a COPY as happily as through a rename -- an
    identical file that is still sitting there, never deleted, is accepted as
    the origin.  Left alone that is a laundering path in both directions: it
    attributed COO's own letter to a lane's earlier ``consumed/`` copy (the
    fixture below that caught this), and it would let a lane copy COO's text
    into a file stamped with a DIFFERENT date and inherit COO's handwriting
    for a key COO never signed.  So the follow only ever ADDS evidence, never
    removes it (the direct add is asked first and can stand on its own), and
    a followed ancestor counts only when its FILENAME is the same -- a sweep
    keeps the name, which is the stamp, which is the only thing tying a
    letter to a key at all.
    """
    try:
        relative = path.relative_to(bridge_dir)
    except ValueError:                                    # pragma: no cover
        return _UNVERIFIABLE_OTHER, "%s is not inside %s" % (
            _ascii(path), _ascii(bridge_dir))
    unanswerable, rc, records = _add_records(bridge_dir, relative, follow=False)
    shown = _ascii(relative)
    if unanswerable is not None:
        return _UNVERIFIABLE_OTHER, "%s: %s" % (shown, unanswerable)
    if rc != 0:
        # Not a work tree, no .git, git refused.  b0749 item 3: say so and be
        # red; never fall back to the filename.
        return _UNVERIFIABLE_OTHER, (
            "%s: git could not report the adding commit (exit %s)"
            % (shown, rc)
        )
    if not records:
        return _UNVERIFIABLE_OTHER, (
            "%s: the file exists on disk but git knows of no commit that "
            "added it -- an uncommitted letter grants nothing" % (shown,)
        )
    sha, subject, _ = records[-1]
    subject = _ascii(subject)
    if subject.startswith(COO_SUBJECT_PREFIX):
        return _FOUND, "%s added by %r" % (shown, subject[:70])

    swept_sha, swept_subject = _swept_origin(bridge_dir, relative)
    if swept_subject is not None and swept_subject.startswith(
            COO_SUBJECT_PREFIX):
        return _FOUND, "%s was filed later, but the same filename was added " \
            "by %r" % (shown, swept_subject[:70])

    if sha in grafts or (swept_sha is not None and swept_sha in grafts):
        return _UNVERIFIABLE_GRAFT, (
            "%s: the oldest visible add is the %s %s (%r), so this "
            "clone provably cannot see who added the file -- run "
            "'git fetch --unshallow' in the bridge checkout to check it here"
            % (shown, GRAFT_MARK, _ascii(sha[:8]), subject[:60])
        )
    return _MISSING, (
        "%s was added by %r, which is not a %s commit -- a lane's copy of a "
        "letter is not the letter" % (shown, subject[:70],
                                      COO_SUBJECT_PREFIX)
    )


def _swept_origin(bridge_dir, relative):
    """``(sha, subject)`` of the oldest add of a file with THIS filename in
    ``relative``'s rename chain, or ``(None, None)``.

    Same-name only, on purpose: see ``_authorship_of``'s second half.  A
    LANE-K sweep is ``git mv`` into ``archive/<dated folder>/``, which keeps
    the filename; a copy that renames the file is not a sweep and gets no
    handwriting from here.
    """
    unanswerable, rc, records = _add_records(bridge_dir, relative, follow=True)
    if unanswerable is not None or rc != 0:
        return None, None
    name = Path(relative).name
    same_name = [r for r in records if Path(r[2]).name == name]
    if not same_name:
        return None, None
    sha, subject, _ = same_name[-1]
    return sha, _ascii(subject)


def _letter_exists_for(pf_bridge_dir, date_match):
    """``(verdict, detail)``: does a COO-AUTHORED letter back this key?

    Four outcomes, per COO-DECISION b0749 item 3 -- "the gate must not fall
    back to the filename in silence; answer UNVERIFIABLE and be red, never
    green":

      * ``_FOUND``               -- at least one candidate was added by a
        ``COO:`` commit.  Any candidate is enough: a stamp routinely has both
        COO's original and a lane's ``consumed/`` copy.
      * ``_MISSING``             -- no candidate at all, or every candidate's
        adding commit is visible and none of them is COO's.  RED.  This is
        the forged-permit case and the one the gate exists for.
      * ``_UNVERIFIABLE_GRAFT``  -- nothing could be adjudicated and EVERY
        reason was a proven graft boundary.  The one WARN, COO-DECISION 0945
        item 1.
      * ``_UNVERIFIABLE_OTHER``  -- nothing could be adjudicated and at least
        one reason was something else: no git, not a work tree, an
        uncommitted file.  RED.

    ``_MISSING`` beats unverifiable only when at least one candidate WAS
    adjudicated; a clone that can answer for none of them reports the reason
    it could not, because "your clone is shallow" and "this permit is forged"
    are different sentences and the operator needs the right one.  A MIX of
    graft and non-graft reasons is red, not a warning: the carve-out is for a
    tree that provably cannot answer, not for one that answered badly once.
    """
    candidates = _letter_candidates_for(pf_bridge_dir, date_match)
    if not candidates:
        year, month, day, hour, minute = date_match.groups()
        return _MISSING, (
            "no .md file stamped %s%s%s_%s%s naming COO-DECISION + widen "
            "exists anywhere under %s or %s (both searched recursively; a "
            ".CONSUMED.txt stub does not count)"
            % (year, month, day, hour, minute,
               _ascii(pf_bridge_dir / "notes_to_chief"),
               _ascii(pf_bridge_dir / "archive"))
        )
    grafts = _shallow_boundary(pf_bridge_dir)
    details = []
    unverifiable = []
    for candidate in candidates:
        verdict, detail = _authorship_of(pf_bridge_dir, candidate, grafts)
        if verdict == _FOUND:
            return _FOUND, detail
        details.append(detail)
        if verdict in _UNVERIFIABLE_VERDICTS:
            unverifiable.append((verdict, detail))
    if len(unverifiable) == len(candidates):
        every_one_a_graft = all(
            verdict == _UNVERIFIABLE_GRAFT for verdict, _ in unverifiable)
        return (
            _UNVERIFIABLE_GRAFT if every_one_a_graft else _UNVERIFIABLE_OTHER,
            "; ".join(detail for _, detail in unverifiable),
        )
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

    The verdict alone decides (pf-adversary D5): this function must never
    read ``detail``, which carries paths and commit subjects that neither
    this repository nor COO controls.
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
    if verdict == _UNVERIFIABLE_GRAFT:
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


def _gate_findings(pf_bridge_dir, keys):
    """``(failures, frozen_warnings, unchecked)`` for a set of ruling keys.

    THE ACT STAGE, LIFTED OUT OF THE TEST METHOD (pf-adversary D2, round
    av245e).  Deciding a verdict was already a pure function; turning
    verdicts into a red build was not, and it lived inside a test method that
    only ever runs against the real bridge checkout, where nothing fails.
    Two mutants survived the whole file there: "route ``_FAIL`` into the WARN
    list" and "``assertFalse(failures)`` -> ``print(failures)``".  Both are
    now killable from a temporary fixture on any machine, because this
    function and ``_run_gate`` below can be handed keys and a directory.
    """
    failures = []
    frozen_warnings = []
    unchecked = []
    for key in keys:
        if key in FROZEN_WIDENING_RULING_KEYS:
            if _schema_date_match(key) is None:
                frozen_warnings.append(key)
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
            unchecked.append((key, text))
    return failures, frozen_warnings, unchecked


def _run_gate(pf_bridge_dir, keys):
    """Print the WARN lines, RAISE on any failure, return what was warned.

    COO-DECISION 0945 item 2 put the reader of a WARN in the lane's round
    file, not in ``pf_gate_preflight.py``: the lane that runs the full suite
    on a clone that produced a graft warning must copy the WARN line into its
    round file's nonclaims, with the sentence "this round the letter gate did
    not check n keys".  That is why the warnings are returned as well as
    printed -- a caller can count them.
    """
    failures, frozen_warnings, unchecked = _gate_findings(pf_bridge_dir, keys)
    for warning in frozen_warnings:
        print(
            "WARN [frozen, pre-schema key, COO-DECISION b1712 item 3]: "
            "%r" % (_ascii(warning),)
        )
    for key, detail in unchecked:
        print(
            "WARN [authorship UNCHECKED on this clone, COO-DECISION "
            "b0749 item 3 + round av245e graft carve-out]: %r -- %s"
            % (_ascii(key), _ascii(detail))
        )
    if failures:
        raise AssertionError("\n".join(failures))
    return frozen_warnings, unchecked


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

        # The whole ACT stage lives in ``_run_gate`` now (pf-adversary D2):
        # this method decides WHICH keys are gated, that function decides
        # what the gate DOES about them, and the anti-vacuity tests at the
        # bottom of this file run it against fixtures where it has to fail.
        # A failure raises AssertionError out of ``_run_gate`` itself, so
        # this test method has nothing left to forget to assert.
        _run_gate(pf_bridge_dir, keys)


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
# THIRD, which that decision does not cover and which is the ordinary state of
# every cloud clone in this project: a SHALLOW clone answers
# ``--diff-filter=A`` with the graft commit instead of admitting it cannot see
# the add, so four of the five ruling DATE STAMPS came back attributed to the
# bridge SYNC BOT.  (Five stamps, not five keys: the counting error of round
# av245e's own commit message, pf-adversary D9.  The stamps back 19 of the
# ruling keys that reach this check -- one stamp, 20260906_1648, backs 11 of
# them -- so a false red on one stamp is a false red on up to eleven permits.)
# Red there would put a permanent false red on main for every lane's cloud
# round, which is the failure NOW.md's own line ("a red on the cloud clone is
# not a red gate") and ``HistoricalGitObject``'s SHALLOW state both exist to
# prevent.
#
# WHERE THIS IS ADJUDICATED FOR REAL: on the owner's machine, and nowhere else
# (pf-adversary D4 -- the comment here used to claim a second machine, and was
# wrong).  ``grep -rn "pf_bridge\|PF_BRIDGE_DIR" .github/`` finds no checkout
# of the bridge in any workflow of this repository; the ``fetch-depth: 0`` in
# ``gate-windows.yml`` is this repository's own history, fetched for
# ``pf_multiplayer_readiness_audit.py``.  With no sibling checkout and no
# ``PF_BRIDGE_DIR``, the gate test SKIPS on CI.  So: CI checks zero letters,
# every cloud clone warns, and the one tree that grades handwriting is the
# bridge checkout on the owner's machine.  That is also why the WARN is not
# the end of it -- COO-DECISION 0945 item 2 makes the lane that ran the suite
# copy every WARN line into its round file, so an unchecked key is visible in
# writing rather than only in a console nobody kept.
#
# So: graft -> WARN and carry on, every other UNVERIFIABLE -> red, and the
# WARN names the clone, the file and the one command that fixes it.
# RULED, not assumed: COO-DECISION 2026-09-07T09:45+07:00 item 1 took this
# lane's proposal without loosening it -- provable grafts only, never derived
# from a lookup that failed (see ``_shallow_boundary``), and everything else
# stays red.  Letter: ``pf_bridge`` notes_to_chief/
# 20260907_0945_COO-DECISION-b0902-graft-is-warn-and-copies-not-moves-LANE-B.md
# answering 20260907_0902_LANE-B-ASK-COO-shallow-clone-is-the-third-
# unverifiable.md.


def _run_git(cwd, *args):
    """Run git in a fixture repository, insulated from the machine.

    pf-adversary D8 (round av245e): the fixtures inherited the developer's
    own git configuration, so a global ``core.hooksPath`` with a
    ``pre-commit`` hook -- an ordinary thing to have, and the owner's machine
    is the ONE machine that grades letters for real -- turned twelve of these
    tests red for a reason that has nothing to do with handwriting.  A false
    red on the only tree that adjudicates is a gate people learn to ignore.
    """
    env = dict(os.environ)
    env["GIT_CONFIG_GLOBAL"] = os.devnull
    env["GIT_CONFIG_SYSTEM"] = os.devnull
    env["GIT_CONFIG_NOSYSTEM"] = "1"
    done = subprocess.run(
        ["git", "-c", "core.hooksPath=", "-c", "core.excludesFile="]
        + list(args),
        cwd=str(cwd), env=env,
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
        """A sweep is a ``git mv``, so ``--diff-filter=A`` on the path the
        letter has TODAY reports the sweep commit, which is LANE-K's, not
        COO's.  Round av245e pinned that as MEASURED-not-desired and left it;
        pf-adversary D1 measured what it costs -- 14 of 14 archived letters
        in the bridge checkout read as lane-authored, so the NEXT sweep of
        the mailbox turns all 19 live keys red at once, on a tree nobody
        touched, and the operator is told his own COO's letters are forged.
        The same-filename rename walk in ``_authorship_of`` is the fix and
        this is its capability half.
        """
        self._commit("notes_to_chief/" + self.LETTER, "COO: round 0405")
        _run_git(self.bridge, "mv",
                 "notes_to_chief/" + self.LETTER,
                 "archive/" + self.LETTER)
        _run_git(self.bridge, "commit", "-q", "-m",
                 "[LANE-K] round zzz: sweep 2026-09 mailbox into archive")
        verdict, detail = _letter_exists_for(self.bridge, self.date_match)
        self.assertEqual(_FOUND, verdict, detail)
        self.assertIn("COO: round 0405", detail)

    def test_a_copy_under_another_stamp_does_not_inherit_coos_hand(self):
        """The other half, and the reason the walk is same-filename only.

        git's ``--follow`` sets ``find_copies_harder``: it will walk back
        into a file that was never deleted.  So a lane that copies one of
        COO's real letters to a filename carrying a DIFFERENT date stamp
        would inherit COO's commit as the "origin" of its copy -- a permit
        for a key COO never signed, minted with ``cp``.  The filename is the
        stamp and the stamp is the only thing that ties a letter to a key,
        so an origin with another name grants nothing.
        """
        other_stamp = self.LETTER.replace("20260907_0405", "20260907_0505")
        self.assertNotEqual(other_stamp, self.LETTER)
        self._commit("notes_to_chief/" + other_stamp,
                     "COO: round 0505 - a letter for a different key",
                     text="the body a lane is about to copy\n")
        self._commit("notes_to_chief/" + self.LETTER,
                     "[LANE-B] round abibfm: cp the 0505 letter to 0405",
                     text="the body a lane is about to copy\n")
        verdict, detail = _letter_exists_for(self.bridge, self.date_match)
        self.assertEqual(_MISSING, verdict, detail)
        self.assertEqual(
            _FAIL, _action_for(self.KEY, verdict, detail)[0], detail)

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
        self.assertEqual(_UNVERIFIABLE_OTHER, verdict, detail)
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
        self.assertEqual(_UNVERIFIABLE_OTHER, verdict, detail)

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
        self.assertEqual(_UNVERIFIABLE_GRAFT, verdict, detail)
        self.assertIn(GRAFT_MARK, detail)
        self.assertIn("--unshallow", detail)

    def test_a_full_clone_reports_no_graft(self) -> None:
        """The other half of the shallow probe: ``_shallow_boundary`` must
        not report a graft on an ordinary repository, or every machine would
        take the WARN path and the gate would grade nothing anywhere.
        """
        self._commit("notes_to_chief/" + self.LETTER, "COO: round 0405")
        self.assertEqual(set(), _shallow_boundary(self.bridge))

    def test_a_worktree_of_a_shallow_clone_still_names_the_graft(self):
        """pf-adversary D3, and the reason ``pirate-force-server#1008`` lost
        its automerge marker in round av245e.

        A linked worktree keeps ``.git`` as a FILE, so the first draft's
        "is there a ``.git/shallow`` file" question said no and it fell back
        to ``git rev-parse --shallow-list``, which is not a git option:
        ``rev-parse`` echoed the token back and exited 0, the graft set
        became ``{"--shallow-list"}``, no sha ever matched it, and every
        letter here was reported FORGED.  This is not a corner case -- this
        house's pf-adversary protocol builds a worktree on the cloud clone,
        so every lane running a full review would have been shown that
        accusation about COO's own letters.
        """
        self._commit("notes_to_chief/" + self.LETTER, "COO: round 0405")
        self._commit("notes_to_chief/later-unrelated.md",
                     "sync: 1 file(s) from the Windows bridge")
        shallow = Path(self.tmp.name) / "shallow_bridge"
        _run_git(Path(self.tmp.name), "clone", "-q", "--depth", "1",
                 "--no-local", self.bridge.as_uri(), str(shallow))
        tree = Path(self.tmp.name) / "worktree_bridge"
        _run_git(shallow, "worktree", "add", "-q", "--detach", str(tree))
        self.assertTrue((tree / ".git").is_file(),
                        "the fixture is not a linked worktree")

        grafts = _shallow_boundary(tree)
        self.assertTrue(grafts, "the worktree of a shallow clone reported no "
                                "graft, so every letter in it reads as forged")
        for sha in grafts:
            self.assertRegex(sha, r"^[0-9a-f]{40}$",
                             "a graft entry must be a sha git actually "
                             "listed, never a token this file made up")
        verdict, detail = _letter_exists_for(tree, self.date_match)
        self.assertEqual(_UNVERIFIABLE_GRAFT, verdict, detail)
        self.assertEqual(_WARN, _action_for(self.KEY, verdict, detail)[0])

    def test_a_path_that_merely_says_shallow_graft_is_still_red(self):
        """pf-adversary D5: the carve-out used to be ``GRAFT_MARK in
        detail``, and ``detail`` interpolates the candidate's PATH.  So an
        UNCOMMITTED letter filed under a directory somebody named
        ``shallow graft scratch`` warned instead of failing -- b0749 item 3
        deleted by a folder name, on a full clone that could answer
        perfectly well.  The verdict, not the prose, decides now.
        """
        scratch = self.bridge / "archive" / "shallow graft scratch"
        scratch.mkdir(parents=True)
        (scratch / self.LETTER).write_text("uncommitted\n", encoding="utf-8")
        self.assertTrue(_letter_candidates_for(self.bridge, self.date_match))
        verdict, detail = _letter_exists_for(self.bridge, self.date_match)
        self.assertEqual(_UNVERIFIABLE_OTHER, verdict, detail)
        self.assertIn(GRAFT_MARK, detail,
                      "the fixture only bites while the path is echoed back")
        self.assertEqual(_FAIL, _action_for(self.KEY, verdict, detail)[0])


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
            self.KEY, _UNVERIFIABLE_GRAFT,
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
                action, text = _action_for(
                    self.KEY, _UNVERIFIABLE_OTHER, detail)
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
        self.assertEqual(_UNVERIFIABLE_OTHER, verdict, detail)
        self.assertEqual(_FAIL, _action_for(self.KEY, verdict, detail)[0])


class TheGateActsOnWhatItFindsTests(unittest.TestCase):
    """The ACT stage: verdicts have to become a RED BUILD (pf-adversary D2).

    Round av245e mutated this file and two mutants survived everything:
    routing ``_FAIL`` into the WARN list, and replacing the final
    ``assertFalse(failures)`` with ``print(failures)``.  Both survived for
    the same reason -- the only code that turned findings into a failure sat
    inside a test method that can only run against the real bridge checkout,
    where every letter is COO's and nothing ever fails.  The stage that
    protects the whole gate was the one stage nothing executed.

    ``_gate_findings`` and ``_run_gate`` take a directory and a list of keys,
    so both mutants are killable here, from a temporary fixture, on any
    machine, with no bridge checkout at all.
    """

    KEY = LetterAuthorshipComesFromGitTests.KEY
    LETTER = LetterAuthorshipComesFromGitTests.LETTER

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.bridge = Path(self.tmp.name) / "pf_bridge"
        (self.bridge / "notes_to_chief").mkdir(parents=True)
        (self.bridge / "archive").mkdir()
        _run_git(self.bridge, "init", "-q", "-b", "main")
        _run_git(self.bridge, "config", "user.email", "gate@example.invalid")
        _run_git(self.bridge, "config", "user.name", "Gate Fixture")
        _run_git(self.bridge, "config", "commit.gpgsign", "false")
        self.assertIsNotNone(_schema_date_match(self.KEY))
        self.assertNotIn(self.KEY, FROZEN_WIDENING_RULING_KEYS)

    def _commit(self, subject) -> None:
        target = self.bridge / "notes_to_chief" / self.LETTER
        target.write_text("letter body\n", encoding="utf-8")
        _run_git(self.bridge, "add", "--",
                 "notes_to_chief/" + self.LETTER)
        _run_git(self.bridge, "commit", "-q", "-m", subject)

    def test_a_forged_permit_is_a_failure_and_not_a_warning(self) -> None:
        """The routing mutant: a ``_FAIL`` that lands in the WARN list is a
        gate that prints the accusation and exits 0.
        """
        self._commit("[LANE-B] round abibfm: mint my own permit")
        failures, frozen, unchecked = _gate_findings(self.bridge, [self.KEY])
        self.assertEqual(1, len(failures), failures)
        self.assertIn(self.KEY, failures[0])
        self.assertEqual([], unchecked,
                         "a forged permit must never be reported as merely "
                         "unchecked")
        self.assertEqual([], frozen)

    def test_a_failure_raises_out_of_the_gate(self) -> None:
        """The assertion mutant: ``assertFalse(failures)`` ->
        ``print(failures)`` survived the whole file in round av245e.
        """
        self._commit("[LANE-B] round abibfm: mint my own permit")
        with self.assertRaises(AssertionError) as caught:
            _run_gate(self.bridge, [self.KEY])
        self.assertIn(self.KEY, str(caught.exception))

    def test_a_real_letter_lets_the_gate_return(self) -> None:
        """The control that keeps the two tests above honest: the same call
        on the same fixture must NOT raise once the letter is COO's, or they
        would pass against a gate that simply always failed.
        """
        self._commit("COO: round 0405 - seven rulings")
        frozen, unchecked = _run_gate(self.bridge, [self.KEY])
        self.assertEqual([], unchecked)
        self.assertEqual([], frozen)

    def test_a_frozen_key_is_warned_about_and_never_fails(self) -> None:
        """b1712 item 3, and the only reason the frozen tuple is allowed to
        exist at all: those keys are announced, not graded.
        """
        frozen_key = FROZEN_WIDENING_RULING_KEYS[0]
        failures, frozen, unchecked = _gate_findings(
            self.bridge, [frozen_key])
        self.assertEqual([], failures)
        self.assertEqual([frozen_key], frozen)

    def test_a_key_that_is_neither_frozen_nor_schema_shaped_is_red(self):
        """b1712 item 1: a brand-new key that matches nothing is red before
        any letter is even looked for.
        """
        failures, frozen, unchecked = _gate_findings(
            self.bridge, ["widen-death-scope-because-I-said-so"])
        self.assertEqual(1, len(failures), failures)
        self.assertIn("does not match the b1647 schema", failures[0])
