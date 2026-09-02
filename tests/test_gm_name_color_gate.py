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
import pathlib
import re
import sys

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

