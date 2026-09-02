"""Pin RE-195's bounded negative so a later round cannot wire P-2 blind.

Every assertion here is one of two kinds and nothing else:

  (a) it re-measures a fact on THIS tree (``field_mobs``' composed
      identities, the module's own source text), or
  (b) it pins that ``gm/name_color_gate`` still refuses, and that its
      refusal still names the route RE-195 actually closed.

None of it claims anything about a colour on a screen.  A GM warp, a GM
account, or any other lane tool is not involved: this file boots nothing and
sends nothing.

pf-adversary, round ``wggs0i``: the first draft of this file asserted only
``verdict.allowed is False``, which stays green if a future round guts the
blocker list to an empty tuple, deletes the identity classifier, or pastes
RE-191's palette into the module -- three edits that are exactly what the
gate exists to stop.  Each of those three is its own red test below.
"""
from __future__ import annotations

import hashlib
import pathlib
import re
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import field_mobs
from pirateforce_foundation.gm import name_color_gate as gate

_MODULE_PATH = pathlib.Path(gate.__file__)
_FIELD_MOBS_PATH = pathlib.Path(field_mobs.__file__)


def _sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# --------------------------------------------------------------------------
# (a) what this tree actually composes
# --------------------------------------------------------------------------


def test_every_shipped_identity_lands_on_the_positive_side_of_the_sign_test():
    """The premise of the bounded negative, re-measured rather than quoted."""
    mobs = field_mobs.load_roster()
    assert mobs, "load_roster() returned nothing; the premise cannot be measured"
    for mob in mobs:
        identity = mob.actor_identity
        assert gate.identity_lane(identity) == gate.IDENTITY_LANE_POSITIVE, (
            f"placement {mob.placement_index} composes identity {identity!r}, "
            "which is NOT the lane RE-195 measured this server to be in -- "
            "re-derive RE-195 before trusting anything in name_color_gate"
        )
        assert gate.typed_style61_tail_reachable(identity) is False


def test_field_mobs_is_still_the_file_re195_measured():
    """A bounded negative measured against a different file is not evidence."""
    current = _sha256(_FIELD_MOBS_PATH)
    if current != gate.FIELD_MOBS_SHA256_AT_RE195:
        pytest.fail(
            "field_mobs.py changed since RE-195 measured it "
            f"({gate.FIELD_MOBS_SHA256_AT_RE195} -> {current}).  The identity "
            "test above still passes on THIS tree, so nothing is broken -- but "
            "the constant in gm/name_color_gate.py must be re-pinned in the "
            "same commit that changed the file, with a line in the round file "
            "saying whether the composition itself moved."
        )


# --------------------------------------------------------------------------
# (b) the refusal, and the three ways a future round could hollow it out
# --------------------------------------------------------------------------


def test_p2_color_wiring_is_refused_and_names_its_evidence():
    verdict = gate.p2_color_wiring_verdict()
    assert verdict.allowed is False
    assert verdict.evidence == (gate.RE_191_RESULT_LETTER, gate.RE_195_RESULT_LETTER)
    assert "RE-195" in verdict.reason()


def test_all_three_closed_routes_are_still_named_in_the_refusal():
    """Deleting a blocker must be a visible edit, not a quiet one."""
    reason = gate.p2_color_wiring_verdict().reason()
    for token in (
        "identity_scheme_is_positive",
        "faction_is_a_fallback_operand_only",
        "hit_writer_needs_a_signed_negative_target",
    ):
        assert token in reason, f"RE-195 closed {token!r}; the gate stopped saying so"
    assert len(gate.P2_COLOR_WIRING_BLOCKERS) == 3
    assert hex(gate.FACTION_COMPARATOR_SOLE_CALL_SITE_VA) in reason


def test_the_module_holds_no_colour_literal():
    """RE-191's own forbidden-actions section, made mechanical.

    The palette belongs in the letter.  A four-component literal appearing in
    this module is the shape of somebody pasting it in, which is precisely
    the hardcoded-colour outcome RE-191's last paragraph rules out.
    """
    source = _MODULE_PATH.read_text(encoding="utf-8")
    quad = re.compile(r"\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)")
    assert quad.search(source) is None, (
        "a 4-component numeric literal appeared in name_color_gate.py -- if "
        "that is RE-191's palette, it must not live here (see that ticket's "
        "forbidden-actions section)"
    )


def test_styles_62_and_63_are_reported_unmeasured_not_guessed():
    for style_id in gate.STYLES_COVERED_BY_RE195:
        assert gate.style_lane_is_measured(style_id) is True
    for style_id in (62, 63):
        assert gate.style_lane_is_measured(style_id) is False


# --------------------------------------------------------------------------
# input shapes: a gate that answers quietly on junk gives the permissive
# answer people remember
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "bad",
    [True, False, 1.0, "0x2001", None, b"\x01", 2 ** 31, -(2 ** 31) - 1],
)
def test_identity_lane_refuses_shapes_it_cannot_classify(bad):
    with pytest.raises(gate.NameColorGateError):
        gate.identity_lane(bad)


def test_bool_is_not_silently_a_positive_identity():
    """``True`` would otherwise classify as the positive lane and read like
    a real answer."""
    with pytest.raises(gate.NameColorGateError):
        gate.typed_style61_tail_reachable(True)


@pytest.mark.parametrize("bad", [True, 61.0, "61", None])
def test_style_lane_is_measured_refuses_shapes_it_cannot_classify(bad):
    with pytest.raises(gate.NameColorGateError):
        gate.style_lane_is_measured(bad)


def test_the_sign_test_itself_is_the_documented_one():
    """Zero and negatives are the nonpositive side; 1 upward is the other."""
    assert gate.identity_lane(0) == gate.IDENTITY_LANE_SIGNED_NONPOSITIVE
    assert gate.identity_lane(-1) == gate.IDENTITY_LANE_SIGNED_NONPOSITIVE
    assert gate.identity_lane(1) == gate.IDENTITY_LANE_POSITIVE
    assert gate.identity_lane(0x2001) == gate.IDENTITY_LANE_POSITIVE
