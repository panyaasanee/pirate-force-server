"""Pin RE-195's bounded negative, and make it act on the tree, not on itself.

Three kinds of assertion and nothing else:

  (a) re-measure a fact on THIS tree (the identities every roster composes,
      the source expression that composes them, every identity-composition
      site in src/);
  (b) pin that gm/name_color_gate still refuses, that the refusal names the
      routes RE-195 closed, and that its transcribed provenance has not been
      edited silently;
  (c) act on the WHOLE source tree: no RE-191 palette value may appear
      anywhere in src/, in code or in a comment.

Nothing here claims anything about a colour on a screen.  It boots nothing
and sends nothing.

pf-adversary, round `wggs0i`, on the first draft of this file (12 of 34
mutants survived it).  What changed, and why each change is here:
  D1  the module hardcoded FontStyleID numbers, which NOW.md P-2 forbids and
      which gm/attr_wire.py keeps in a comment for that exact reason -- the
      style table and `style_lane_is_measured` are gone, so the tests that
      asserted a tuple contains its own members are gone with them.
  D2  `typed_style61_tail_reachable(-1) -> True` affirmed the consequent and
      no test ever exercised that branch (`return False` survived) -- the
      predicate is one-sided now and the unmeasured side is asserted.
  D3  the whole-file sha pin of field_mobs.py went red on a comment-only
      edit by another lane, and its failure message said "nothing is broken"
      in the one case where something was -- replaced by pinning the
      composing EXPRESSION, which is red only when the composition moves.
  D4  nothing executed the gate against the tree -- two repo-wide scans now
      do (palette absence, identity-composition sites).
  D6  the roster check measured 4 of ~16 identities from 1 of 9 composers --
      it now walks every roster field_mobs exposes and every site in src/.
  D7  six spellings of RE-191's palette survived the shape-regex -- the
      palette check is by VALUE now (via hashes, so the values themselves
      still never enter this repository), over the whole tree.
"""
from __future__ import annotations

import ast
import hashlib
import inspect
import io
import pathlib
import re
import sys
import tokenize

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import field_mobs
from pirateforce_foundation.gm import name_color_gate as gate

_SRC = ROOT / "src"
_SRC_FILES = sorted(_SRC.rglob("*.py"))

#: The composing expression RE-195 measured, as source text.
_PINNED_IDENTITY_EXPRESSION = "return 0x2000 + self.placement_index + 1"

#: sha256 of every RE-191 palette value, in the spellings a paste would use
#: (4-component and 3-component, integer and normalised float).  HASHES ONLY:
#: writing the values here would itself be the paste this test forbids.
_FORBIDDEN_PALETTE_SHA256 = frozenset(
    {
        "10b7616421640a2ea6e2c87d7db2367b4fccffc79f4be38f839e2857ec49b0e8",
        "3e5d72f22f2bb266a86c178b846c2ea0da3507e0da89ca5b9dcf39e52cce2008",
        "5b9c26fced97dc03ebabc0416a9a8c77bcd42e9057bd1e9a6ca456c01db93af7",
        "62ffcc4afa2ecdb1c7ba3abd7a4a04d2e29ae5717cd99602232a7ae5d5ecea32",
        "64aa5061d87ce4beacbcfdba963aa26814ccaba73321db616d9988b9349257a8",
        "736873d6f91f25404302e6c3faea6df0e75a627cee20538f99590663b79ae678",
        "869633ee86f44e29dc5d43eaaf27ee81a1478d0e9fbfe6058008aca153034e95",
        "93fdc923147fbc679d68b63d46904099c2e82a28e71d2960a8a600f15b105acf",
        "94678497707edbefe4aa737818be0e92a811caf281f0062ef880de4746916dd9",
        "9529eedd135a7337e9b6248052beb8c65be47941728b01ae157ae126cc168912",
        "ce149d1c9499ca01ff114754f63af761a371e32806686508ffe71c085ff96be0",
        "e00a07d6a42e1180202a63591d3b5cccdab01263bb404474e1f488b2420cf115",
        "e036331ab506142c323623280b07c5432e5e7aa374f6a7fdb85808a10d0a5895",
        "e316e0458600d1ceb7ad6a8b7dc553b06ee178b1b74744e55a7fbb7ff3ca1be0",
        "eca0a0f1041cd3548ad740182fd453b74d84ba86fa49722526acdb25ed3206cf",
        "f74cf8ad1cce6e73b235b3cdc3717e0adb227f441e533f9fd0b2a8113a83fb88",
    }
)

_NUMBER_RUN = re.compile(
    r"(?<![\w.])(\d{1,3}(?:\.\d+)?)\s*,\s*(\d{1,3}(?:\.\d+)?)\s*,\s*"
    r"(\d{1,3}(?:\.\d+)?)(?:\s*,\s*(\d{1,3}(?:\.\d+)?))?(?![\w.])"
)


def _all_rosters():
    """Every roster field_mobs can hand out, not just the default one."""
    rosters = [("default", field_mobs.load_roster())]
    for scene in (field_mobs.BG0002_SCENE,):
        rosters.append((scene, field_mobs.load_roster(scene)))
    return rosters


# --------------------------------------------------------------------------
# (a) what this tree actually composes
# --------------------------------------------------------------------------


def test_every_roster_identity_is_in_the_class_re195_measured():
    total = 0
    for scene, mobs in _all_rosters():
        assert mobs, f"roster {scene!r} is empty; the premise cannot be measured"
        for mob in mobs:
            assert gate.is_measured_bypass_identity(mob.actor_identity) is True, (
                f"{scene} placement {mob.placement_index} composes "
                f"{mob.actor_identity!r}, outside the class RE-195 measured"
            )
            total += 1
    assert total >= 16, f"only {total} identities were reachable to measure"


def test_the_composing_expression_is_the_one_re195_measured():
    """Red when the composition moves -- not when a neighbour gains a comment.

    The first draft hashed the whole of field_mobs.py, which another lane's
    documentation-only edit turns red for no information (pf-adversary D3).
    """
    src = inspect.getsource(field_mobs.FieldMob.actor_identity.fget)
    assert _PINNED_IDENTITY_EXPRESSION in src, (
        "FieldMob.actor_identity no longer composes the expression RE-195 "
        "measured; re-derive RE-195 before trusting gm/name_color_gate, and "
        f"do not simply re-pin. Current source:\n{src}"
    )


def _identity_composition_sites():
    """Every `0x2000 + ...` addition in src/, found structurally."""
    for path in _SRC_FILES:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.BinOp) or not isinstance(node.op, ast.Add):
                continue
            operands = (node.left, node.right)
            if any(
                isinstance(x, ast.Constant) and x.value == 0x2000 for x in operands
            ):
                yield path, node


def test_no_identity_composer_in_the_tree_introduces_a_negative_base():
    """Acts on the whole tree, not on this module (pf-adversary D4/D6).

    RE-195's bounded negative is stated over what the server composes.  If
    ANY composer starts producing a nonpositive identity, that premise is
    false everywhere, not only in the roster this file can load.
    """
    sites = list(_identity_composition_sites())
    assert sites, "no identity-composition site found; the scan broke"
    for path, node in sites:
        for child in ast.walk(node):
            assert not isinstance(child, ast.USub), (
                f"{path.relative_to(ROOT)}:{node.lineno} negates an identity "
                "composed from 0x2000 -- RE-195's bounded negative was measured "
                "on positive identities only; re-derive it before landing this"
            )
            assert not isinstance(child, ast.Sub), (
                f"{path.relative_to(ROOT)}:{node.lineno} subtracts inside an "
                "identity composed from 0x2000 -- same reason"
            )


# --------------------------------------------------------------------------
# (b) the refusal, and the ways a future round could hollow it out
# --------------------------------------------------------------------------


def test_p2_color_wiring_is_refused():
    verdict = gate.p2_color_wiring_verdict()
    assert verdict.allowed is False
    assert "RE-195" in verdict.reason()


def test_the_verdict_cannot_be_minted_in_the_allowed_state():
    # non-empty blockers on purpose: an empty-blocker verdict is refused by a
    # DIFFERENT guard, and the first draft of this test was green against a
    # gutted `allowed` check because of exactly that overlap.
    real = gate.P2_COLOR_WIRING_BLOCKERS
    with pytest.raises(gate.NameColorGateError):
        gate.P2ColorWiringVerdict(allowed=True, blockers=real, evidence=())
    with pytest.raises(gate.NameColorGateError):
        gate.P2ColorWiringVerdict(allowed=1, blockers=real, evidence=())
    with pytest.raises(gate.NameColorGateError):
        gate.P2ColorWiringVerdict(allowed=False, blockers=(), evidence=())


def test_all_three_closed_routes_are_still_named_in_the_refusal():
    reason = gate.p2_color_wiring_verdict().reason()
    for token in (
        "identity_scheme_is_positive",
        "faction_is_a_fallback_operand_only",
        "hit_writer_needs_a_signed_negative_target",
    ):
        assert token in reason, f"RE-195 closed {token!r}; the gate stopped saying so"
    assert len(gate.P2_COLOR_WIRING_BLOCKERS) == 3
    assert hex(gate.FACTION_COMPARATOR_SOLE_CALL_SITE_VA) in reason


def test_transcribed_provenance_has_not_been_edited_silently():
    """These constants cannot be re-derived here -- the image is not in this
    repository -- so the only defence against transcription rot is that a
    change to one shows up as a diff in this file too (pf-adversary D7)."""
    assert gate.CLIENT_IMAGE_BYTES == 14_759_424
    assert gate.CLIENT_IMAGE_SHA256 == (
        "9627211412ac60d50ad189ce5a629443ce928ec23a9f8d219dfb2b157028b623"
    )
    assert gate.SELECTOR_SPAN == (0x00443F50, 0x004443C5)
    assert gate.SELECTOR_SPAN_SHA256 == (
        "ee845ee6ef6337ea41ae57a5a4df8af5a8a8ac00e458ea1ce3e587aff1f9cdf9"
    )
    assert gate.RELATIONSHIP_PREDICATE_SPAN == (0x0043C380, 0x0043C63C)
    assert gate.FACTION_COMPARATOR_VA == 0x004A1D50
    assert gate.FACTION_COMPARATOR_SOLE_CALL_SITE_VA == 0x0043C5E0
    assert gate.RE_191_RESULT_LETTER == (
        "notes_to_chief/20260901_1439_CODEX-RE191-RESULT-FONTSTYLE63-RGBA.md"
    )
    assert gate.RE_195_RESULT_LETTER == (
        "notes_to_chief/"
        "20260902_0341_RE-195-RESULT-RELATION-FALLBACK-STYLE61-NOT-CURRENT.md"
    )
    assert gate.PAIR_RELATION_ZERO_GATE_SPAN == (0x0043C531, 0x0043C547)
    # CORRECTED by RE-263.  The previous pin read "ActorAttr+0x98 bit
    # 0x04000000", which says a bit lives inside the value at +0x98.  It does
    # not: +0x98 is a one-byte uint8_enum and 0x04000000 is the presence bit
    # in the mask word at +0x1B4.  A test that pins a wrong transcription is
    # worse than no test -- it makes the error load-bearing -- so the pin
    # moves with the correction rather than being relaxed.
    assert gate.PAIR_RELATION_ZERO_GATE_OPERAND == (
        "ActorAttr+0x98 (u8), presence bit +0x1B4 & 0x04000000"
    )
    assert gate.PAIR_RELATION_ZERO_GATE_CMP_LOCAL_VA == 0x0043C531
    assert gate.PAIR_RELATION_ZERO_GATE_CMP_TARGET_VA == 0x0043C53A
    assert gate.ACTOR_ATTR_0X98_PRESENCE_GATE == "+0x1B4 & 0x04000000"
    assert gate.ACTOR_ATTR_0X98_CONSTRUCTOR_DEFAULT == 0
    assert gate.ACTOR_ATTR_0X98_DEFAULT_WRITER_VA == 0x00464D69
    assert gate.LOCAL_ACTOR_NAME_STYLE_EMIT_SITE_VAS == (0x00443FE9, 0x00443FF2)
    assert gate.RELATION_PREDICATE_POSITIVE_LANE_CALL_SITE_VA == 0x00444018
    # D4/D8 (pf-adversary, round y1evqj): the module used to cite this TSV
    # by bare filename (read as living in external/) and to call the two
    # LOCAL emit sites above "the" emit points. Both corrected this round.
    assert gate.PF_ATTR_NAME_COLOR_SELECTOR_TSV_PATH == (
        "notes_to_chief/reference_codex_attr/PF_ATTR_NAME_COLOR_SELECTOR.tsv"
    )
    assert gate.PF_ATTR_NAME_COLOR_SELECTOR_TSV_ROW_COUNT == 14
    assert gate.PAIR_RELATION_ZERO_GATE_ROUTE_VERDICT == (
        "RE-263 BOUNDED-NEGATIVE: not a second route"
    )
    assert gate.PAIR_RELATION_ZERO_GATE_STATUS == "PROVEN_ROLE_ONLY"
    assert gate.PAIR_RELATION_ZERO_GATE_SOURCE == (
        "notes_to_chief/reference_codex_attr/PF_A2_ATTR_FIELD_DELTA.tsv rows 6-7"
    )
    # This module keeps FontStyleID numbers out of its own code AND prose
    # (see the rule a few lines below in the source); the TSV row cited above
    # names two of them in its own `semantic_name` field, which is exactly
    # why that field is not reproduced here, digits or otherwise.
    assert "56" not in gate.PAIR_RELATION_ZERO_GATE_OPERAND
    assert not hasattr(gate, "PAIR_RELATION_ZERO_GATE_SEMANTIC_NAME")


def test_the_new_gate_sits_at_a_lower_address_than_the_comparator():
    """Cross-referenced this round: a second, earlier-addressed branch in the
    SAME predicate span RE-195 already named, never cited before.  This is
    the only claim the ordering proves -- a static LAYOUT fact.  It is NOT a
    walked control-flow fact: nothing here says execution actually reaches
    this branch before the comparator, only that it sits at a lower address
    in the same span (pf-adversary: a test named "sits earlier" would invite
    exactly that stronger reading)."""
    lo, hi = gate.RELATIONSHIP_PREDICATE_SPAN
    gate_lo, gate_hi = gate.PAIR_RELATION_ZERO_GATE_SPAN
    assert lo <= gate_lo < gate_hi <= hi
    assert gate_hi < gate.FACTION_COMPARATOR_SOLE_CALL_SITE_VA


def test_the_new_gate_constants_are_not_wired_into_the_verdict():
    """Naming this gate must not quietly change the verdict or the blocker
    count -- and unlike this module's other transcribed constants, THESE FOUR
    ARE DELIBERATELY UNCONSUMED, because consuming them would mean answering
    a reachability question nobody has measured yet (pf-adversary: a test
    that only re-checks unrelated, unchanged logic proves nothing about the
    new constants themselves -- this test pins that absence of a wire
    explicitly, by asserting no attribute path from the verdict machinery
    reaches the new names, rather than implying a causal guard that does not
    exist)."""
    verdict = gate.p2_color_wiring_verdict()
    assert verdict.allowed is False
    assert len(gate.blocker_names()) == 3
    assert gate.unaddressed_blockers() == (
        "faction_is_a_fallback_operand_only",
    )


# --------------------------------------------------------------------------
# (c) the whole tree: RE-191's palette must not exist in this repository
# --------------------------------------------------------------------------


def _palette_hits(text):
    for match in _NUMBER_RUN.finditer(text):
        parts = [p for p in match.groups() if p is not None]
        for width in (len(parts), 3):
            if width > len(parts):
                continue
            candidate = ",".join(parts[:width])
            digest = hashlib.sha256(candidate.encode("ascii")).hexdigest()
            if digest in _FORBIDDEN_PALETTE_SHA256:
                yield match.start(), width


def test_no_re191_palette_value_appears_anywhere_in_src():
    """RE-191's forbidden-actions section, made mechanical over the tree.

    Checked by VALUE, not by shape: the first draft's regex passed six
    different spellings of the same paste, including the normalised float
    form the letter also publishes.  The values live only as hashes here so
    that enforcing the ban does not itself import the palette.
    """
    offenders = []
    for path in _SRC_FILES:
        text = path.read_text(encoding="utf-8")
        for offset, width in _palette_hits(text):
            line = text.count("\n", 0, offset) + 1
            offenders.append(f"{path.relative_to(ROOT)}:{line} ({width} components)")
    assert not offenders, (
        "an RE-191 palette value appears in src/: "
        + "; ".join(offenders)
        + " -- NOW.md P-2 and RE-191's forbidden-actions section rule it out; "
        "the numbers belong in the letter"
    )


def test_the_palette_check_can_actually_see_a_paste():
    """A guard nobody has watched fail is a guard nobody should trust."""
    assert list(_palette_hits("PALETTE = (255, 100, 100, 255)"))
    assert list(_palette_hits("x = [179,179,179,255]"))
    assert list(_palette_hits("grey = 179, 179, 179"))
    assert list(_palette_hits("# 0.701960802, 0.701960802, 0.701960802, 1"))
    assert not list(_palette_hits("span = (0x00443F50, 0x004443C5)"))
    assert not list(_palette_hits("version = 1, 2, 3"))


# --------------------------------------------------------------------------
# input shapes
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "bad", [True, False, 1.0, "0x2001", None, b"\x01", 2 ** 64, -(2 ** 63) - 1]
)
def test_identity_refuses_shapes_it_cannot_classify(bad):
    with pytest.raises(gate.NameColorGateError):
        gate.is_measured_bypass_identity(bad)


@pytest.mark.parametrize("outside", [0, -1, -(2 ** 63), 2 ** 32, 2 ** 64 - 1])
def test_identities_outside_the_measured_class_raise_unmeasured_not_false(outside):
    """False would read as "does not bypass", which reads as "reaches the
    tail" -- the overclaim RE-195 does not support in that direction."""
    with pytest.raises(gate.NameColorGateUnmeasured):
        gate.is_measured_bypass_identity(outside)


def test_the_measured_class_boundaries_are_the_documented_ones():
    assert gate.MEASURED_BYPASS_IDENTITY_RANGE == (1, 2 ** 32)
    assert gate.is_measured_bypass_identity(1) is True
    assert gate.is_measured_bypass_identity(2 ** 32 - 1) is True
    with pytest.raises(gate.NameColorGateUnmeasured):
        gate.is_measured_bypass_identity(0)
    with pytest.raises(gate.NameColorGateUnmeasured):
        gate.is_measured_bypass_identity(2 ** 32)


def test_no_fontstyleid_number_is_hardcoded_in_the_gate_module():
    """NOW.md P-2: no FontStyleID may live in this module (pf-adversary D1).

    gm/attr_wire.py keeps its own FontStyleID domain out of code for the same
    reason and its crosscheck test enforces that; this module holds to the
    same rule.

    Checked structurally: every int literal in the module, minus exponents
    (``2 ** 63`` is a 64-bit bound, not a style id).
    """
    source = pathlib.Path(gate.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    exponents = {
        id(node.right)
        for node in ast.walk(tree)
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Pow)
    }
    offenders = [
        f"line {node.lineno}: {node.value}"
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant)
        and type(node.value) is int
        and 55 <= node.value <= 67
        and id(node) not in exponents
    ]
    assert not offenders, "FontStyleID-range literal in code: " + "; ".join(offenders)


#: A style id spelled inside a string or a COMMENT is not an int literal, so
#: the test above cannot see it.  Round `srn7ksvmt` proved that gap the
#: expensive way: its first draft carried
#: ``..._LABEL_NAME_FontStyleID_56_else_55`` as a string constant, the int
#: scan stayed green, and pf-adversary -- not the suite -- was what caught it.
#:
#: WHAT THIS SCANNER READS, and why each surface is here.  pf-adversary struck
#: the FIRST draft of this scanner too, for announcing a closure it did not
#: have:
#:   * COMMENTS.  That draft read only ``ast`` nodes, which discard comments
#:     -- and ``#:`` comments are where THIS module keeps its prose, including
#:     the block that states the no-style-id rule.  The sibling module
#:     ``gm/attr_wire.py`` deliberately keeps its own style-id domain in a
#:     comment, so a comment is the single most likely place a future author
#:     puts one here.  A three-line mutant (one comment, two constants)
#:     survived that draft entirely.
#:   * FOLDED strings, so ``"FontStyleID_5" + "6"``, implicit adjacency and an
#:     f-string's literal parts are read as one value.
#:   * String constants, docstrings included.
#: The tokenize/folding machinery is the same shape as
#: ``tests/test_gm_p2_color_call_site_tripwire.py`` -- which already solved
#: this one file away, and which exempts this module (near its line 410),
#: which is exactly why the hole existed.
#:
#: WHAT IT STILL DOES NOT CATCH -- named, not hidden, because the first
#: draft's sin was announcing a closed gap:
#:   * a spelling with no marker word from the list below;
#:   * a style id written in hex (``0x38``) or spelled out in words;
#:   * a number assembled at runtime from parts no literal contains.
#: A bare-number rule (any standalone 55-67 anywhere) was tried and REMOVED:
#: it fired on ``"64 bits"``, ``"scene 61"``, ``"line 61 of runtime.py"`` and
#: on sha digests, and a guard that goes red on another lane's copy edit --
#: with a message asserting a FontStyleID that is not there -- gets deleted,
#: not obeyed.
_STYLE_MARKERS = r"(?:fontstyle|style|label_?name|nameboard|name_?id)"
#: A marker word with an id-range number glued to it or a short gap away:
#: ``FontStyleID_56``, ``STYLE 61``, ``LABEL_NAME_ID_056``.  Zero padding is
#: accepted; a longer digit run is not (``style610`` is not id 61).
_STYLE_MARKER_THEN_NUMBER = re.compile(
    _STYLE_MARKERS + r"[A-Za-z_]*[ _.:=-]*(?<![0-9])0{0,2}(?:5[5-9]|6[0-7])(?![0-9])",
    re.IGNORECASE,
)
#: Provenance is the one exemption: a bridge artifact's own filename may carry
#: a style id, because renaming someone else's letter to satisfy this test
#: would break the citation.  NARROWED after pf-adversary: the first draft
#: exempted any whitespace-free token ending in an artifact extension, so
#: ``"STYLE_56.md"`` and ``"gm/style61_notes.py"`` walked through, and a
#: mutant widening it to ``.*\.(md|...)$`` -- exempting whole prose sentences
#: -- survived.  A real citation starts at a real top-level directory, and
#: ``test_the_artifact_path_exemption_is_as_narrow_as_its_comment_says``
#: kills that mutant now instead of a comment asserting it.
_ARTIFACT_PATH = re.compile(
    r"^(?:notes_to_chief|external|gamedata|archive|rounds|docs|src|tests"
    r"|tools_bridge|scenarios|config)/[A-Za-z0-9_./-]+"
    r"\.(?:md|tsv|json|py|txt|csv)$"
)
#: The ONE historical identifier this module's prose may name.  pf-adversary
#: D1 of round `wggs0i` deleted ``typed_style61_tail_reachable`` and the
#: module's docstring records that it did.  Forcing prose to stop naming what
#: was removed buys a green bar by erasing the record, so the exemption is by
#: exact value, pinned, and one entry long -- not the blanket "docstrings are
#: exempt" the first draft used, which let a glued style id hide in any
#: docstring.
_HISTORICAL_IDENTIFIERS = ("typed_style61_tail_reachable",)


def _folded_string_values(tree: ast.AST) -> list[tuple[int, str]]:
    """String constants, ``+`` joins and an f-string's literal parts."""
    values: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and type(node.value) is str:
            values.append((node.lineno, node.value))
        elif (
            isinstance(node, ast.BinOp)
            and isinstance(node.op, ast.Add)
            and isinstance(node.left, ast.Constant)
            and isinstance(node.right, ast.Constant)
            and type(node.left.value) is str
            and type(node.right.value) is str
        ):
            values.append((node.lineno, node.left.value + node.right.value))
        elif isinstance(node, ast.JoinedStr):
            joined = "".join(
                part.value
                for part in node.values
                if isinstance(part, ast.Constant) and type(part.value) is str
            )
            if joined:
                values.append((node.lineno, joined))
    return values


def _comment_texts(source: str) -> list[tuple[int, str]]:
    """Every ``#`` comment, which ``ast`` throws away."""
    return [
        (tok.start[0], tok.string)
        for tok in tokenize.generate_tokens(io.StringIO(source).readline)
        if tok.type is tokenize.COMMENT
    ]


def _without_historical_identifiers(text: str) -> str:
    for name in _HISTORICAL_IDENTIFIERS:
        text = text.replace(name, " ")
    return text


def _style_id_offenders_in_prose(source: str) -> list[str]:
    """Every string or comment in ``source`` that names a FontStyleID value."""
    tree = ast.parse(source)
    offenders = []
    surfaces = [("string", ln, v) for ln, v in _folded_string_values(tree)]
    surfaces += [("comment", ln, v) for ln, v in _comment_texts(source)]
    for kind, lineno, text in surfaces:
        if _ARTIFACT_PATH.match(text.strip()):
            continue
        if _STYLE_MARKER_THEN_NUMBER.search(_without_historical_identifiers(text)):
            offenders.append(f"line {lineno}: style id in {kind} {text[:60]!r}")
    return offenders


#: Spellings the scanner MUST catch.  Each is a shape a future author could
#: plausibly write here; the first is the exact string round `srn7ksvmt`
#: nearly shipped.  The numbers live in this fixture and not in the module --
#: which is the whole rule.
_MUST_CATCH = (
    'X = "CNetActor_pair_relation_zero_gate__CMyActor_value_1_selects'
    '_LABEL_NAME_FontStyleID_56_else_55"\n',
    'X = "LABEL_NAME_ID_56_else_55"\n',
    'X = "FontStyleID_056_else_055"\n',
    'X = "the fallback picks style 61"\n',
    'X = "nameboard 63 is the RE-191 one"\n',
    '# FontStyleID 56 selects the label name; 55 otherwise\n',
    'X = "FontStyleID_5" + "6"\n',
    'X = "FontStyle" "ID_56"\n',
    'sep = "_"\nX = f"FontStyleID{sep}56"\n',
    'def f():\n    """FontStyleID_56 for the local actor."""\n',
)

#: Spellings the scanner MUST NOT catch.  pf-adversary measured the first
#: draft going red on the middle four -- innocent prose from another lane --
#: with a message asserting a FontStyleID that was not there.
_MUST_NOT_CATCH = (
    'X = "notes_to_chief/20260901_1439_CODEX-RE191-RESULT-FONTSTYLE63-RGBA.md"\n',
    'X = ("notes_to_chief/"\n'
    '     "20260902_0341_RE-195-RESULT-RELATION-FALLBACK-STYLE61-NOT-CURRENT.md")\n',
    'X = "a 64-bit wire quantity"\n',
    'X = "identity does not fit 64 bits of wire quantity"\n',
    'X = "scene 61"\n',
    'X = "line 61 of runtime.py"\n',
    'X = "63a7211412ac60d50ad189ce5a629443ce928ec23a9f8d219dfb2b157028b623"\n',
    'def f():\n    """typed_style61_tail_reachable was deleted by D1."""\n',
)


def test_the_prose_scanner_catches_every_shape_it_claims_to():
    for fixture in _MUST_CATCH:
        assert _style_id_offenders_in_prose(fixture), f"missed: {fixture!r}"


def test_the_prose_scanner_stays_quiet_on_the_shapes_it_must_not_punish():
    for fixture in _MUST_NOT_CATCH:
        offenders = _style_id_offenders_in_prose(fixture)
        assert not offenders, f"false positive on {fixture!r}: {offenders}"


def test_the_artifact_path_exemption_is_as_narrow_as_its_comment_says():
    """The exemption is the only way past the scanner, so it is pinned.

    pf-adversary widened it to ``.*\\.(md|...)$`` and the suite stayed green:
    the "real top-level directory" narrowing was asserted in a comment and by
    nothing else.  These are the shapes that widening lets in.
    """
    for smuggled in (
        'X = "STYLE_56.md"\n',
        'X = "gm/style61_notes.py"\n',
        'X = "the fallback picks style 56, see relation.md"\n',
    ):
        assert _style_id_offenders_in_prose(smuggled), f"exempted: {smuggled!r}"


def test_the_historical_identifier_exemption_is_one_entry_and_exact():
    """A blanket "prose is exempt" was the first draft; this replaced it.

    If the exemption ever grows, it must grow on purpose: a second entry, or
    a prefix match instead of an exact one, re-opens every docstring.
    """
    assert _HISTORICAL_IDENTIFIERS == ("typed_style61_tail_reachable",)
    # The exemption is a substring blank, so a name CONTAINING the exempt one
    # is covered too.  That is the price of not maintaining word boundaries
    # for a one-entry list, and it is stated rather than papered over.
    assert _style_id_offenders_in_prose(
        'def f():\n    """style61 on its own is not the deleted identifier."""\n'
    ), "the exemption is blanking more than one exact name"


def test_no_fontstyleid_number_hides_in_this_module_s_prose():
    """The gap the int scan above leaves open, narrowed on the same module."""
    source = pathlib.Path(gate.__file__).read_text(encoding="utf-8")
    offenders = _style_id_offenders_in_prose(source)
    assert not offenders, "FontStyleID in prose: " + "; ".join(offenders)


# --------------------------------------------------------------------------
# (d) the refusal points FORWARD as well as backward -- and says what nothing
#     is filed against
#
# Round `5ddsii` filed the ticket (COO-DECISION 2026-09-03T10:46+07:00 item
# (b)); chief queued it as `RE-222`, not the ~~`RE-211`~~ the draft drew --
# the queue counter is shared with `GAME_TEST_QUEUE.md` (chief `20260903_1304`
# point 2).  These tests pin the QUEUED number, because that is the one an
# operator can look up.
# Filing a ticket is the one thing that can hollow out a refusal without
# touching a single one of its blockers: a reader sees "a ticket is open",
# reads that as "this is nearly unblocked", and writes the colour code the
# refusal exists to stop.
#
# pf-adversary, round `5ddsii`, on the first draft of this section: 12 of 13
# mutants survived it.  What changed:
#   S1/O4  a `route_out()` string method and an `open_questions` dataclass
#          field are GONE.  No call site in either repository ever called
#          them, its one number was unasserted and could exceed its own
#          denominator (`bears_on=6/3`), and it mixed instance state with
#          module state inside one line.  Deleting both removed five of his
#          twelve survivors outright -- the same "no caller = no module" rule
#          COO 1046 item (c) used the same day to reject another module.
#   S6     the drift guard was only ever tested against CARDINALITY changes,
#          so a length check was indistinguishable from a set check; a RENAME
#          that keeps the count is now tested, and it is the case that used
#          to escape as a bare KeyError past every caller the module's own
#          docstring tells to catch NameColorGateError.
#   S7     the question TEXT was completely unpinned -- rewriting a question
#          into an ANSWER kept 126 tests green.
#   S8-S12 the strip / empty-name branches of blocker_names() were unreached.
#   O1     the letter asks THREE questions and only two were representable.
#   O2     the hit-writer mapping is this lane's inference, not the letter's
#          words, and shipped unlabelled.
#   O3     a test named "..._are_the_ones_actually_filed" compared a constant
#          against a retyped copy of itself -- exactly the D7 shape this lane
#          already burned on.  Renamed to what it actually does.
# --------------------------------------------------------------------------


def test_filing_the_ticket_did_not_weaken_the_refusal_by_one_byte():
    verdict = gate.p2_color_wiring_verdict()
    assert verdict.allowed is False
    assert len(verdict.blockers) == 3
    assert "RE-195" in verdict.reason()
    with pytest.raises(gate.NameColorGateError):
        gate.P2ColorWiringVerdict(
            allowed=True, blockers=gate.P2_COLOR_WIRING_BLOCKERS, evidence=()
        )
    # and the one-sided predicate is still one-sided: a nonpositive identity
    # is UNMEASURED, ticket or no ticket.
    with pytest.raises(gate.NameColorGateUnmeasured):
        gate.is_measured_bypass_identity(-1)


def test_nothing_here_reads_a_result_so_no_question_may_read_as_an_answer():
    """S7.  A question rewritten into an answer is how "a ticket is filed"
    becomes "P-2 is unblocked" without a single blocker being retired."""
    values = tuple(gate.RE_222_QUESTION_FOR_BLOCKER.values())
    assert values, "the map went empty"
    for value in values:
        if not value:
            continue
        assert value.startswith("RE-222 Q"), value
        # long enough that a truncation mutant (`value[:6]`) cannot pass
        assert len(value) > 80, value
    # and the join site may not transform them on the way out: a `[:6]` in
    # `open_questions()` truncated every question while this test, which read
    # the map directly, stayed green (pf-adversary S7, second form).
    for entry in gate.open_questions():
        name, sep, question = entry.partition(" -> ")
        assert sep, entry
        assert question == gate.RE_222_QUESTION_FOR_BLOCKER[name], entry
    haystack = " ".join(values) + " ".join(gate.RE_222_QUESTION_LABELS)
    for forbidden in ("ANSWERED", "RESULT", "measured that", "confirmed that"):
        assert forbidden not in haystack, (
            f"{forbidden!r} in the question text: this module reads no result"
        )


def test_all_three_questions_the_letter_asks_are_named_here():
    """O1.  Two of the three retire a blocker; the third prices the direction
    and retires nothing.  A reader who greps this module must still see it."""
    labels = gate.RE_222_QUESTION_LABELS
    assert len(labels) == 3
    assert [label[:2] for label in labels] == ["Q1", "Q2", "Q3"]
    mapped_text = " ".join(gate.RE_222_QUESTION_FOR_BLOCKER.values())
    assert "Q3" not in mapped_text, (
        "Q3 prices the direction; claiming it retires a blocker is the "
        "overclaim this test exists to stop"
    )


def test_the_inferred_mapping_is_labelled_as_this_lanes_inference():
    """O2.  The letter never mentions the hit writer.  The link is this
    lane's reasoning, and an unlabelled inference read as measurement is
    exactly one unit of false progress."""
    value = gate.RE_222_QUESTION_FOR_BLOCKER[
        "hit_writer_needs_a_signed_negative_target"
    ]
    assert "[PROPOSED" in value, value
    corroborated = gate.RE_222_QUESTION_FOR_BLOCKER["identity_scheme_is_positive"]
    assert "[letter says so]" in corroborated, corroborated


def test_the_ticket_constants_have_not_been_edited_silently():
    """NOT a proof that anything was filed -- it cannot be one: the letter
    lives in the OTHER repository and this one cannot re-derive it.  Same
    shape and same limits as the provenance test above: the only defence
    against transcription rot is that editing one shows up as a diff here
    too.  Named for what it does, after pf-adversary (round `5ddsii`, O3)
    found the earlier name claiming a fact the assertions do not establish.
    """
    assert gate.RE_222_TICKET_ID == "RE-222"
    assert gate.RE_222_TICKET_LETTER == (
        "notes_to_chief/20260903_1119_LANE-GM-RE-211-TICKET-"
        "typed-and-live-gate-for-nonpositive-identity.md"
    )


def test_a_blocker_no_ticket_covers_is_counted_out_loud():
    addressed = {q.partition(" -> ")[0] for q in gate.open_questions()}
    unaddressed = set(gate.unaddressed_blockers())
    # structural: every blocker is on exactly one side of the line.
    assert addressed | unaddressed == set(gate.blocker_names())
    assert not (addressed & unaddressed)
    # S3: a superset passes a "each name appears" check, so pin the SET.
    assert unaddressed == {"faction_is_a_fallback_operand_only"}
    assert len(addressed) == 2
    # deliberate retyped name, and the only one in this file: RE-222 asks
    # about the identity split and what a nonpositive identity costs the
    # client's registry.  It does NOT reopen RE-195's faction finding, and
    # its own out-of-scope section says so.  A round that files against that
    # route edits this line together with the map, in one reviewable diff.


def test_the_question_map_cannot_drift_from_the_blockers_in_any_direction(
    monkeypatch,
):
    real = gate.P2_COLOR_WIRING_BLOCKERS
    # (a) a fourth blocker nobody decided the status of
    monkeypatch.setattr(
        gate,
        "P2_COLOR_WIRING_BLOCKERS",
        real + ("a_fourth_route: closed by something",),
    )
    with pytest.raises(gate.NameColorGateError):
        gate.open_questions()
    with pytest.raises(gate.NameColorGateError):
        gate.unaddressed_blockers()
    monkeypatch.undo()
    # (b) a question aimed at a route that has already moved
    monkeypatch.setitem(
        gate.RE_222_QUESTION_FOR_BLOCKER, "a_route_that_left", "RE-222 Q9"
    )
    with pytest.raises(gate.NameColorGateError):
        gate.open_questions()
    monkeypatch.undo()
    # (c) S6 -- a RENAME that keeps the count identical.  Without this case a
    # length check is indistinguishable from a set check, and the real-world
    # failure (rename the blocker, forget the map key) escapes as a bare
    # KeyError past every caller told to catch NameColorGateError.
    renamed = ("faction_is_a_fallback_operand: same prose",) + real[:2]
    assert len(renamed) == len(real)
    monkeypatch.setattr(gate, "P2_COLOR_WIRING_BLOCKERS", renamed)
    with pytest.raises(gate.NameColorGateError):
        gate.open_questions()
    with pytest.raises(gate.NameColorGateError):
        gate.unaddressed_blockers()
    monkeypatch.undo()
    # (d) S5 -- a name that is a PREFIX of a real one is still not that one.
    monkeypatch.setattr(
        gate,
        "P2_COLOR_WIRING_BLOCKERS",
        ("identity_scheme: prose",) + real[1:],
    )
    with pytest.raises(gate.NameColorGateError):
        gate.open_questions()


def test_blocker_names_are_derived_from_the_blockers_not_retyped(monkeypatch):
    for broken in (
        ("no_colon_here so no name",),          # no key at all
        ("same_name: one", "same_name: two"),   # two blockers, one name
        (": prose",),                           # S8-S12: empty name
        (" padded : prose",),                   # S8-S12: unstripped name
        ("a -> b: prose",),                     # section 4: name eats the sep
    ):
        monkeypatch.setattr(gate, "P2_COLOR_WIRING_BLOCKERS", broken)
        with pytest.raises(gate.NameColorGateError):
            gate.blocker_names()
        monkeypatch.undo()


def test_every_string_this_module_hands_out_survives_a_cp874_console():
    """The bridge console is cp874 and these strings are free-form prose --
    the one surface in this module where a stray dash or quote would land."""
    for text in (
        gate.open_questions()
        + gate.RE_222_QUESTION_LABELS
        + tuple(gate.RE_222_QUESTION_FOR_BLOCKER.values())
        + (gate.RE_222_TICKET_ID, gate.RE_222_TICKET_LETTER)
        + (
            gate.PAIR_RELATION_ZERO_GATE_OPERAND,
            gate.PAIR_RELATION_ZERO_GATE_STATUS,
            gate.PAIR_RELATION_ZERO_GATE_SOURCE,
        )
    ):
        assert text.isascii(), text


def test_the_deleted_route_out_stays_deleted():
    """It had no caller in either repository, its only number was unasserted
    and could exceed its own denominator, and it mixed instance state with
    module state in one printed line (pf-adversary S1/S2/O4).  A round that
    wants a human-facing line asks chief for a call site first, the way this
    lane did for GM_IDENTITY_CENSUS in CORE-REQUEST-GM-050."""
    assert not hasattr(gate.P2ColorWiringVerdict, "route_out")
    assert "open_questions" not in gate.P2ColorWiringVerdict.__dataclass_fields__


def test_the_answered_ticket_is_named_and_cannot_go_back_to_unanswered():
    """Round `y1evqj`.  For two days this module told every reader that
    `RE-222` was "filed, not answered" while its DONE/PASS result sat in the
    bridge, consumed and copied.  pf-adversary found it; nothing in this file
    would have.  So the correction gets a card of its own, in both
    directions: the result must be NAMED, and the sentence that hid it must
    not come back.

    Deliberately NOT a check that a blocker moved -- none did, and
    `test_filing_the_ticket_did_not_weaken_the_refusal_by_one_byte` above
    still owns that.  This card is only about the module telling the truth
    about what it has been told."""
    source = pathlib.Path(inspect.getsourcefile(gate)).read_text(encoding="utf-8")

    # 1. The result is named, and by a path that exists on the bridge.
    assert gate.RE_222_RESULT_LETTER.startswith("notes_to_chief/")
    assert "RE-222-RESULT" in gate.RE_222_RESULT_LETTER
    assert gate.RE_222_RESULT_LETTER != gate.RE_222_TICKET_LETTER

    # 2. The answer says what it retires AND what it does not -- a summary
    #    with only the first half is how "Q3 answered" becomes "P-2 open".
    summary = gate.RE_222_RESULT_WHAT_IT_MEASURED
    assert "retired" in summary and "NOT retired" in summary, summary
    assert "viewer" in summary, summary

    # 3. The false sentence may not return unstruck.  It survives in the
    #    file as history, so the test looks for it OUTSIDE strikethrough --
    #    a mutant that deletes the `~~` markers and keeps the claim is the
    #    exact regression this guards.
    stale = "It is filed, not answered"
    for line_number, line in enumerate(source.splitlines(), start=1):
        if stale in line:
            assert "~~" in line, (
                f"line {line_number} states the false claim without striking "
                "it: RE-222 came back DONE/PASS on 2026-09-03"
            )
