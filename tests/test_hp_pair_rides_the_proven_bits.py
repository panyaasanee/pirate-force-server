"""LANE-DB / M4: the wire bit and offset each vital rides, pinned against the
REPORT that proved them rather than against the table that uses them.

WHY THIS FILE EXISTS -- a mutant that survives 391 of this lane's tests.

Round `mgyoob` asked chief (`pf_bridge/notes_to_chief/20260903_0755_LANE-DB-RE-
REQUEST-chief-which-u32-is-hp-current.md` -- IN THE OTHER REPOSITORY AND
UNOPENABLE FROM HERE) which of the pair `hp_current`/`hp_max` the client's HP
bar reads, and wrote down why nothing in this repository could answer it: the
composer, `persistence_vitals`' `HP_CURRENT_X`/`HP_MAX_X`, and every test that
builds an expectation all take their order from ONE table, `gm/attr_wire.
FIELDS`.  A table agreeing with itself is consistency, not evidence.

Round `l8tn7f` measured what that costs.  With `FIELDS` x=3 and x=4 keeping
their NAMES but swapping their `mask_bit` and `offset` -- so a login writes the
character's CURRENT hp into the client's `hp_max` slot and its maximum into the
slot the HP bar reads -- this lane's whole suite stayed green:

    tests/test_persistence_vitals.py            \\
    tests/test_persistence_vitals_seed_007.py   \\
    tests/test_persistence_login_vitals.py      \\
    tests/test_persistence_vitals_heal.py       \\
    tests/test_persistence_vitals_or_none.py    \\
    tests/test_persistence_attr_compose.py
    -> 391 passed, 418 subtests passed

Invisible today only because every live row is `100/100`, which makes the two
numbers equal.  The seam this lane landed in `session.py` is what ends that:
once a row holds `37/250` the swap puts a full bar on a nearly dead character.

WHAT THIS FILE ASSERTS, AND WHY IT IS NOT A SECOND COPY OF THE TABLE.

`COO-DECISION 20260903_0846` forbids a card that retypes a list in a second
file and requires it to derive from the source.  So no bit and no offset is
typed into this file.  Every number is PARSED, at test time, out of TWO of
this repository's own reports -- and the two are not the same KIND of
evidence, which is the whole point:

1.  `reports/PF_CHUNK2_Q1_ACTORATTR_MASK_FINDINGS_20260819.md` section 3.2 --
    the GATE table.  Its own heading says the twelve gated `BasicAttr` fields
    are "derive จากไบต์ ไม่ใช่ hard-code".  It gives bit, offset, tag and
    width.  What it gives for the SEMANTIC is a name in a column (`HP
    current`), and this lane's own rule -- "a table agreeing with itself is
    consistency, not evidence" -- applies to that name as much as to
    `FIELDS`.

2.  `reports/PF_HP_DEATH001_HP_DEATH_AND_RESPAWN_STATIC_20260819.md` section
    ①, headed *"byte-proof -- current vs max is decided by a consumer, not by
    a name"* -- the CONSUMER proof, and the one that actually answers the
    question.  The HUD updater `0x53F180` pushes the pair into the bar helper
    `0x53EED0`, whose own disassembly labels its arguments: `arg0 = the LAST
    push = +0x48`, `arg1 = +0x44`, `divsd xmm0, xmm1 ; arg1 / arg0`, and
    `mov [edi+0x220], esi ; the NUMBER the label prints = arg1`.  The
    numerator of the fill ratio and the number on the label is *current*; the
    denominator is *max*.

`ConsumerProofDecidesWhichIsCurrentTests` below derives `current` from the
DISASSEMBLY'S OWN ARGUMENT LABELS (arg1 -> current, arg0 -> max) and then
requires the gate table, the consumer proof and `FIELDS` to agree three ways.
A pin that took the semantic from the gate table alone would be the same
mistake the RE request was written to avoid, one rung further out.

An earlier draft of this file cited only source 1, and a `pf-adversary` pass
(round `l8tn7f`, defect D1) named that as the weakness before it was
committed.  The same pass established that the RE request itself
(`pf_bridge/notes_to_chief/20260903_0755_...` -- IN THE OTHER REPOSITORY AND
UNOPENABLE FROM HERE) was answerable from `reports/` on the day it was
written, so it is WITHDRAWN rather than escalated.

WHAT IT DOES NOT CLAIM.  Nothing here is client-observable: no frame is
composed, nothing is sent, and no character is rendered.  It does not prove
the report is right about the client -- it proves this server has not drifted
from the evidence it says it is built on.  It says nothing about `ActorAttr
+0x1A8/+0x1AC`, the alternate HP pair the same report describes for
`0x430E10(category) == 8`; the server does not send `category` and this lane
does not own that switch.
"""
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import persistence_vitals as vitals  # noqa: E402
from pirateforce_foundation.gm.attr_wire import BY_X  # noqa: E402

REPORT = ROOT / "reports" / "PF_CHUNK2_Q1_ACTORATTR_MASK_FINDINGS_20260819.md"

#: One gated `BasicAttr` line of section 3.2.  The trailing description is
#: captured lazily and stripped: it is what NAMES the field, and the arrow
#: clause after it (`-> HPBAR ...`) is the consumer, not part of the name.
_ROW = re.compile(
    r"^\s*BasicAttr\s+bit\s+(0x[0-9A-Fa-f]{4})"
    r"\s+\+(0x[0-9A-Fa-f]{3})"
    r"\s+tag\s+(0x[0-9A-Fa-f]{2})"
    r"\s+w\s+(\d+|-)"
    r"\s*(.*?)\s*$"
)

#: How many gated rows section 3.2 has.  Derived from the report's own prose
#: ("12 ฟิลด์ที่ถูกเกต"), not from a number this lane chose -- see
#: `TheParseIsNotVacuousTests`, which is the reason any of this is safe to
#: assert at all: a regex that stops matching turns every pin below into a
#: silent pass, and that is the exact shape of the mutant this file exists to
#: catch.
_GATED_ROWS_CLAIMED_BY_THE_REPORT = 12


#: The heading section 3.2 lives under.  THE ANCHOR IS LOAD-BEARING AND THE
#: REASON IS A DEFECT THIS FILE ALREADY HAD.  The report prints the same
#: twelve-row table TWICE: once as section 3.2 (the prose table, lines ~135)
#: and once inside the verification transcript further down (the tool's own
#: stdout, lines ~1393).  An unanchored parse read BOTH into one dict and the
#: second silently won every key -- so a `pf-adversary`-shaped mutant that
#: renamed the `HP current` row IN SECTION 3.2 left all twelve tests green,
#: because the transcript copy overwrote the mutated row.  Measured, in round
#: `l8tn7f`, before this anchor existed.
_SECTION = "### 3.2"
_NEXT_HEADING = re.compile(r"^#{1,4}\s")


def _section_3_2() -> list[str]:
    """The lines of section 3.2, and nothing else."""
    lines = REPORT.read_text(encoding="utf-8").splitlines()
    starts = [i for i, line in enumerate(lines) if line.startswith(_SECTION)]
    if len(starts) != 1:
        raise AssertionError(
            f"expected exactly one {_SECTION!r} heading in {REPORT}, "
            f"found {len(starts)} at lines {[i + 1 for i in starts]}"
        )
    start = starts[0]
    for end in range(start + 1, len(lines)):
        if _NEXT_HEADING.match(lines[end]):
            return lines[start:end]
    return lines[start:]


def _parse_rows(lines) -> dict[int, dict]:
    """Every gated `BasicAttr` row in `lines`, keyed by mask bit.

    Refuses a repeated bit rather than letting the later line win, which is
    the exact way the unanchored version of this parser hid a mutant.
    """
    rows: dict[int, dict] = {}
    for line in lines:
        match = _ROW.match(line)
        if match is None:
            continue
        bit, offset, tag, width, description = match.groups()
        bit_value = int(bit, 16)
        if bit_value in rows:
            raise AssertionError(
                f"bit {bit} appears twice in the block being parsed:\n"
                f"  {rows[bit_value]['line']}\n  {line.strip()}"
            )
        rows[bit_value] = {
            "bit": bit_value,
            "offset": int(offset, 16),
            "tag": int(tag, 16),
            "width": None if width == "-" else int(width),
            # `HP current  -> HPBAR + ...` -> `HP current`
            "name": description.split("->")[0].strip(),
            "consumers": description.split("->", 1)[1].strip()
            if "->" in description else "",
            "line": line.strip(),
        }
    return rows


def _report_rows() -> dict[int, dict]:
    """The gated `BasicAttr` rows of section 3.2, keyed by mask bit."""
    return _parse_rows(_section_3_2())


def _transcript_rows() -> dict[int, dict]:
    """The same table as the verification transcript printed it.

    Not a second source -- it is the same tool's own stdout -- but it is a
    second COPY, and a mutant that edits one copy and not the other is a
    mutant this file can see.  Its wstring row prints `w None` where the
    prose table prints `w -`, so it yields eleven rows, not twelve; that
    difference is asserted rather than smoothed over.
    """
    lines = REPORT.read_text(encoding="utf-8").splitlines()
    starts = [i for i, line in enumerate(lines) if line.startswith(_SECTION)]
    start = starts[0]
    length = len(_section_3_2())
    # Excluded BY POSITION, not by content: the two copies share most of
    # their lines verbatim, so excluding by string value would drop the
    # transcript's rows as well and leave a handful of near-duplicates that
    # happen to differ in trailing whitespace.  Measured: five rows instead
    # of eleven.
    outside = lines[:start] + lines[start + length:]
    return _parse_rows(outside)


class TheParseIsNotVacuousTests(unittest.TestCase):
    """The pins below are only worth their green if the parse really read the
    report.  Every one of them is an `assertEqual` against a dict lookup, so a
    regex that matches nothing would raise `KeyError` -- but a regex that
    matches the WRONG lines, or a report that moved, would not.  These grade
    the input before anything grades the server."""

    def test_the_report_is_where_this_file_says_it_is(self):
        self.assertTrue(REPORT.is_file(), REPORT)

    def test_every_gated_row_of_section_3_2_was_read(self):
        rows = _report_rows()
        self.assertEqual(
            len(rows), _GATED_ROWS_CLAIMED_BY_THE_REPORT,
            "section 3.2 claims twelve gated BasicAttr fields; the parse "
            f"found {len(rows)}: {sorted(hex(b) for b in rows)}",
        )

    def test_the_bits_read_are_the_twelve_consecutive_ones(self):
        """A parse that read six rows twice would still count twelve."""
        self.assertEqual(
            sorted(_report_rows()),
            [1 << n for n in range(_GATED_ROWS_CLAIMED_BY_THE_REPORT)],
        )

    def test_the_parse_is_anchored_to_one_section_and_not_to_the_file(self):
        """The defect this anchor exists for, stated as a test: the report
        prints this table twice, and a parse that reads the whole file gets
        the transcript copy instead of section 3.2."""
        section = _section_3_2()
        self.assertTrue(section[0].startswith(_SECTION), section[0])
        whole_file = REPORT.read_text(encoding="utf-8").splitlines()
        self.assertLess(len(section), len(whole_file))
        # The transcript copy really is there, really does carry the same
        # bits, and really would have won an unanchored parse.
        transcript = _transcript_rows()
        self.assertTrue(transcript, "the second copy of the table vanished")
        self.assertLessEqual(set(transcript), set(_report_rows()))

    def test_the_two_copies_of_the_table_agree(self):
        """A mutant that edits one copy and not the other is visible here.
        The wstring row is exempt on WIDTH only -- the transcript prints
        `w None` where the prose prints `w -` -- so it does not appear in the
        transcript parse at all, and the exemption is that absence, not a
        loosened comparison."""
        prose = _report_rows()
        transcript = _transcript_rows()
        self.assertEqual(len(transcript), len(prose) - 1, sorted(transcript))
        for bit, row in transcript.items():
            with self.subTest(bit=hex(bit)):
                self.assertEqual(row["offset"], prose[bit]["offset"])
                self.assertEqual(row["tag"], prose[bit]["tag"])
                self.assertEqual(row["width"], prose[bit]["width"])

    def test_the_two_hp_rows_are_named_and_carry_the_bar_as_a_consumer(self):
        """The name is what makes `hp_current` the current one.  If the
        report ever stops saying it, this file must go red rather than keep
        asserting an order it can no longer source."""
        rows = _report_rows()
        current = [r for r in rows.values() if r["name"] == "HP current"]
        maximum = [r for r in rows.values() if r["name"] == "HP max"]
        self.assertEqual(len(current), 1, [r["line"] for r in rows.values()])
        self.assertEqual(len(maximum), 1, [r["line"] for r in rows.values()])
        # The consumer is the whole point: `HP current` is the one the bar and
        # the death predicates read.  `HP max` reaches the bar only.
        self.assertIn("HPBAR", current[0]["consumers"])
        self.assertIn("death predicates", current[0]["consumers"])
        self.assertIn("HPBAR", maximum[0]["consumers"])
        self.assertNotIn("death predicates", maximum[0]["consumers"])


#: Section ① of the HP-death report.  Three separate anchors, all of them
#: comments the disassembler's own author wrote next to the bytes.
_ARG0 = re.compile(r";\s*arg0\s*=\s*the LAST push\s*=\s*\+(0x[0-9A-Fa-f]+)")
_ARG1 = re.compile(r";\s*arg1\s*=\s*\+(0x[0-9A-Fa-f]+)")
_PRINTED = re.compile(r"the NUMBER the label prints\s*=\s*(arg[01])")
_RATIO = re.compile(r"divsd[^;]*;\s*(arg[01])\s*/\s*(arg[01])")
_CONCLUSION = re.compile(
    r"So\s+`\+(0x[0-9A-Fa-f]+)`\s*=\s*current,\s*`\+(0x[0-9A-Fa-f]+)`\s*=\s*max"
)

CONSUMER_PROOF = (
    ROOT / "reports" / "PF_HP_DEATH001_HP_DEATH_AND_RESPAWN_STATIC_20260819.md"
)


def _consumer_proof() -> dict:
    """What section ① says, read out of the disassembly's own labels.

    Deliberately does NOT read the report's prose conclusion to decide which
    offset is current: it derives that from `arg1` (numerator of the fill
    ratio AND the number the label prints) and then uses the conclusion
    sentence only as a CROSS-CHECK.  A parse that took the conclusion as its
    source would be reading a sentence, which is the class of evidence this
    file exists to stop relying on.
    """
    text = CONSUMER_PROOF.read_text(encoding="utf-8")
    arg_offset = {
        "arg0": int(_ARG0.search(text).group(1), 16),
        "arg1": int(_ARG1.search(text).group(1), 16),
    }
    printed = _PRINTED.search(text).group(1)
    numerator, denominator = _RATIO.search(text).groups()
    stated_current, stated_max = (
        int(g, 16) for g in _CONCLUSION.search(text).groups()
    )
    return {
        "arg_offset": arg_offset,
        "printed": printed,
        "numerator": numerator,
        "denominator": denominator,
        "current": arg_offset[numerator],
        "max": arg_offset[denominator],
        "stated_current": stated_current,
        "stated_max": stated_max,
    }


class ConsumerProofDecidesWhichIsCurrentTests(unittest.TestCase):
    """Section ①, derived rather than quoted."""

    def test_the_consumer_proof_is_where_this_file_says_it_is(self):
        self.assertTrue(CONSUMER_PROOF.is_file(), CONSUMER_PROOF)

    def test_the_number_on_the_label_is_the_numerator(self):
        """The argument that is BOTH the numerator of the fill ratio AND the
        number printed on the label is what `current` means here.  If a future
        edit of the report ever separates those two, this file must go red
        rather than keep deciding on one of them."""
        proof = _consumer_proof()
        self.assertEqual(proof["numerator"], proof["printed"])
        self.assertNotEqual(proof["numerator"], proof["denominator"])

    def test_current_derived_from_the_disassembly_matches_the_prose(self):
        proof = _consumer_proof()
        self.assertEqual(proof["current"], proof["stated_current"])
        self.assertEqual(proof["max"], proof["stated_max"])

    def test_the_gate_table_and_the_consumer_proof_name_the_same_offsets(self):
        """Source 1 and source 2, joined.  The gate table knows which BIT
        carries which OFFSET; the consumer proof knows which OFFSET is
        current.  Neither alone answers the question `FIELDS` has to get
        right."""
        proof = _consumer_proof()
        by_name = {r["name"]: r for r in _report_rows().values()}
        self.assertEqual(by_name["HP current"]["offset"], proof["current"])
        self.assertEqual(by_name["HP max"]["offset"], proof["max"])

    def test_fields_sends_the_current_hp_under_the_bit_of_the_current_slot(self):
        """The three-way join, and the assertion the whole file is for."""
        proof = _consumer_proof()
        rows = _report_rows()
        by_offset = {r["offset"]: r for r in rows.values()}
        current_field = BY_X[vitals.HP_CURRENT_X]
        max_field = BY_X[vitals.HP_MAX_X]
        self.assertEqual(current_field[3], proof["current"])
        self.assertEqual(max_field[3], proof["max"])
        self.assertEqual(current_field[2], by_offset[proof["current"]]["bit"])
        self.assertEqual(max_field[2], by_offset[proof["max"]]["bit"])


class EachVitalRidesTheBitTheReportProvedTests(unittest.TestCase):
    """`FIELDS` and the report must agree on bit, offset, tag and width for
    every column this lane owns a typed column for.  Nothing here re-types a
    number: both sides are looked up."""

    #: x -> the report's own name for that field.  This is the ONLY thing
    #: this file states rather than derives, and it is a NAME, not a number:
    #: the whole question the RE request asked is which name goes with which
    #: bit, so the answer has to be sourced (the report) and the question has
    #: to be spelled (here).
    OWNED = {
        "LEVEL_X": "level",
        "HP_CURRENT_X": "HP current",
        "HP_MAX_X": "HP max",
    }

    def test_the_three_vitals_ride_the_reports_bits(self):
        rows = _report_rows()
        by_name = {r["name"]: r for r in rows.values()}
        for symbol, report_name in self.OWNED.items():
            x = getattr(vitals, symbol)
            field = BY_X[x]
            proven = by_name[report_name]
            with self.subTest(symbol=symbol, x=x, report_name=report_name):
                # x, block, mask_bit, offset, tag, kind, name, known, note
                self.assertEqual(field[1], "basic")
                self.assertEqual(field[2], proven["bit"], proven["line"])
                self.assertEqual(field[3], proven["offset"], proven["line"])
                self.assertEqual(field[4], proven["tag"], proven["line"])

    def test_the_hp_pair_is_not_reversible_without_this_file_going_red(self):
        """The mutant, stated as an assertion rather than as a comment: the
        bit `hp_current` rides must be the one the report gives the row whose
        consumers include the death predicates, and it must not be the other
        one.  A swap of the two `FIELDS` rows' bits and offsets fails both
        halves."""
        rows = _report_rows()
        by_name = {r["name"]: r for r in rows.values()}
        current = BY_X[vitals.HP_CURRENT_X]
        maximum = BY_X[vitals.HP_MAX_X]
        self.assertEqual(current[2], by_name["HP current"]["bit"])
        self.assertEqual(maximum[2], by_name["HP max"]["bit"])
        self.assertNotEqual(current[2], by_name["HP max"]["bit"])
        self.assertNotEqual(maximum[2], by_name["HP current"]["bit"])
        self.assertLess(
            current[2], maximum[2],
            "the login frame emits in ascending mask-bit order, so a reader "
            "of the frame sees hp_current first; that is only correct while "
            "the report gives hp_current the lower bit",
        )

    def test_the_typed_columns_of_this_lane_ride_the_reports_bits_too(self):
        """`mp_current`/`mp_max` have columns since `migrations/006` and no
        adjudicated value, so nothing sends them today -- but the day one
        does, it must ride the bit the report proved, and the pin costs
        nothing now.  Sourced by name from the report exactly like the three
        above."""
        rows = _report_rows()
        by_name = {r["name"]: r for r in rows.values()}
        from pirateforce_foundation import persistence_typed_attrs as typed
        for column, report_name in (("mp_current", "MP current"),
                                    ("mp_max", "MP max")):
            x = typed.TYPED_COLUMNS[column].x
            field = BY_X[x]
            proven = by_name[report_name]
            with self.subTest(column=column):
                self.assertEqual(field[2], proven["bit"], proven["line"])
                self.assertEqual(field[3], proven["offset"], proven["line"])


if __name__ == "__main__":
    unittest.main()
