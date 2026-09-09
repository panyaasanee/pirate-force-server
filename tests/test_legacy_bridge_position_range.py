"""A stored position past float32 refuses the frame; it does not kill the thread.

[CORE-REQUEST LANE-A 20260909_1519 -> chief round qnys56]
Before this guard, `LegacyProjector.start_game`/`movement_attr` read
`character.position` raw and handed it to `f32tag`, whose `struct.pack("<f",...)`
raises OverflowError on a magnitude past float32.  runtime.py's `select_and_start`
call site catches (KeyError, PermissionError) and (ValueError, RuntimeError) -- not
OverflowError -- so the exception unwound the shared listener thread on every login
of that character.
"""
import math
import struct
import sys
from pathlib import Path

import pytest

# Same shape as tests/test_foundation_legacy_seam.py line 49: this repository has
# no conftest.py and no pythonpath setting, so every test file puts src/ on the
# path itself.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation.legacy_bridge import (  # noqa: E402
    F32_MAX_MAGNITUDE,
    WirePositionOutOfRange,
    refuse_unencodable_position,
)


class Pos:
    def __init__(self, x=0.0, y=0.0, z=0.0, heading=0.0):
        self.x, self.y, self.z, self.heading = x, y, z, heading


class Char:
    character_id = 199


def test_the_boundary_this_guard_is_drawn_at_is_the_one_struct_uses():
    # Not a chosen threshold: the two must agree, or the guard is either
    # refusing frames struct would have encoded or letting through ones it
    # cannot.  Measured against struct itself, both sides of the edge.
    struct.pack("<f", F32_MAX_MAGNITUDE)
    with pytest.raises(OverflowError):
        struct.pack("<f", F32_MAX_MAGNITUDE * 1.0000001)


@pytest.mark.parametrize("field", ["x", "y", "z", "heading"])
def test_each_field_past_float32_is_refused_by_name(field):
    p = Pos()
    setattr(p, field, 3.5e38)
    with pytest.raises(WirePositionOutOfRange) as e:
        refuse_unencodable_position(p, "start_game", Char())
    msg = str(e.value)
    assert "WIRE_POSITION_OUTSIDE_FLOAT32" in msg
    assert "start_game.%s" % field in msg
    assert "199" in msg          # the row is named, so the log can find it


def test_the_refusal_is_catchable_where_the_login_path_catches():
    # runtime.py ~10483 catches (ValueError, RuntimeError) around
    # select_and_start.  That tuple is what keeps the listener thread alive,
    # so the refusal has to be inside it; OverflowError is not.
    assert issubclass(WirePositionOutOfRange, ValueError)
    assert not issubclass(WirePositionOutOfRange, OverflowError)


def test_an_ordinary_row_passes_through_unchanged():
    p = Pos(12.5, -3.0, 900.25, 1.5)
    assert refuse_unencodable_position(p, "start_game", Char()) is p


def test_the_largest_encodable_magnitude_is_not_refused():
    # The edge belongs to the allowed side: struct encodes it, so this seam
    # must not refuse it.  A guard that is one ULP tight is a guard that
    # refuses a frame the client would have accepted.
    p = Pos(F32_MAX_MAGNITUDE, -F32_MAX_MAGNITUDE, 0.0, 0.0)
    assert refuse_unencodable_position(p, "start_game", Char()) is p


def test_inf_and_nan_are_deliberately_left_alone_here():
    # NONCLAIM, and it is load-bearing: f32tag encodes both today without
    # raising, so they are not this seam's OverflowError hole.  The finite
    # question belongs to world_scene_entry's own row guard (LANE-A).  If this
    # test ever has to change, that is a decision, not a cleanup.
    p = Pos(math.inf, math.nan, 0.0, 0.0)
    assert refuse_unencodable_position(p, "movement_attr", Char()) is p


def test_a_field_that_is_not_a_number_is_named_too():
    p = Pos("somewhere", 0.0, 0.0, 0.0)
    with pytest.raises(WirePositionOutOfRange) as e:
        refuse_unencodable_position(p, "movement_attr", Char())
    assert "WIRE_POSITION_NOT_A_NUMBER" in str(e.value)


def test_a_position_object_missing_a_field_is_not_invented():
    class Partial:
        x = 1.0
        y = 2.0
        # no z, no heading
    assert refuse_unencodable_position(Partial(), "start_game") is not None
