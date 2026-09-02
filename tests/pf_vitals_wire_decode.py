"""LANE-DB: read a BasicAttr field back OUT of a real login frame.

WHY THIS FILE EXISTS, and it is the answer to a question four
``pf-adversary`` passes asked in four different shapes.

Every tie this lane built between its stored numbers and the wire compared
the frame to a TRANSCRIPTION of the frame: a regex over ``player_wire.py``'s
source text, or a substring assembled from the same three numbers the test
was trying to check.  Both are satisfiable without the wire being right, and
the fourth pass demonstrated exactly that, twice:

* the source window was computed over ``body``, which INCLUDES the function's
  docstring, with ``str.index`` finding the FIRST occurrence of each anchor.
  Four anchor lines pasted into the docstring -- the single most likely edit
  to a function whose docstring already documents emission order -- moved the
  window onto prose, and ``hp_max = 150`` shipped with
  ``tests/test_persistence_vitals.py`` entirely green.
* keeping the source text and changing the bytes
  (``legacy.u32tag(0x14, 100)[:-4] + struct.pack("<I", 150)``, plus a decoy
  ``level + 100 + 100`` after the speed tag) satisfied the regex AND the
  substring check, and both files stayed green with 150 on the wire.

The general form: ``regex(source) AND substring_in(frame)`` is two
independently satisfiable conditions, and neither of them is *the field at
this wire position holds this value*.

So this module decodes.  It walks the BasicAttr mask the way a client does --
in ascending mask-bit order, taking each field's tag and width from
``gm/attr_wire.FIELDS`` rather than from anything this lane wrote -- and
returns ``{x: value}``.  A docstring cannot change what it reads, a decoy
later in the frame cannot be mistaken for the pair, and a field ADDED to the
block (``player_wire``'s own docstring pre-announces mp_current/mp_max, whose
bits sit between hp_max and movement speed) joins the walk instead of turning
an HP assertion red for the wrong reason -- which the source window did.
"""
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation.gm.attr_wire import BY_X  # noqa: E402

#: Width in bytes of each fixed-size field kind, and the struct code used to
#: read it.  Taken from `gm/attr_wire.encode_field`, which is what WROTE the
#: bytes -- if that function grows a kind, this raises rather than guessing.
_READ = {
    "u8": ("<B", 1), "u16": ("<H", 2), "u32": ("<I", 4),
    "i32": ("<i", 4), "f32": ("<f", 4), "u64": ("<Q", 8),
}


class WireDecodeError(AssertionError):
    """This frame is not shaped the way `gm/attr_wire.FIELDS` says it is."""


def find_basic_mask(frame: bytes) -> tuple[int, int]:
    """``(offset just past the mask, mask value)`` for the BasicAttr block.

    The mask is a ``u16`` at tag ``0x12`` (``gm/attr_wire.py``: BasicAttr's
    mask is a u16 at tag 0x12, ActorAttr's a u64 at tag 0x32), and so is the
    ``level`` field -- so the tag alone does not identify it.  What does: the
    mask of a player's block sets the name, level and HP-pair bits, and no
    level this server sends does.  The match must be UNIQUE; two candidates
    means this function is guessing and it says so instead.
    """
    required = BY_X[1][2] | BY_X[2][2] | BY_X[3][2] | BY_X[4][2]
    found = []
    for i in range(len(frame) - 2):
        if frame[i] != BY_X[2][4]:
            continue
        value = struct.unpack_from("<H", frame, i + 1)[0]
        if value & required == required:
            found.append((i + 3, value))
    if not found:
        raise WireDecodeError(
            "no BasicAttr mask in this frame: no u16 tag 0x12 carries the "
            "name/level/HP bits (0x%04X)" % (required,))
    if len(found) > 1:
        raise WireDecodeError(
            "%d candidate BasicAttr masks in this frame (%r); this decoder "
            "cannot tell which block is the player's" % (len(found), found))
    return found[0]


def decode_basic_block(frame: bytes) -> dict:
    """``{x: value}`` for every BasicAttr field the frame's mask declares.

    A ``wstr`` field is reported as its decoded text; a field kind this
    decoder does not know raises rather than being skipped, because skipping
    one would silently shift every field after it and hand back numbers read
    from the wrong offsets -- the exact failure this module exists to end.
    """
    pos, mask = find_basic_mask(frame)
    out = {}
    for x in sorted(BY_X):
        row = BY_X[x]
        if row[1] != "basic" or not mask & row[2]:
            continue
        tag, kind = row[4], row[5]
        if pos >= len(frame):
            raise WireDecodeError(
                "frame ends before x=%d (%s), which its own mask declares"
                % (x, row[6]))
        if frame[pos] != tag:
            raise WireDecodeError(
                "at x=%d (%s) the frame has tag 0x%02X, not the 0x%02X "
                "gm/attr_wire.FIELDS gives it: the block's emission order "
                "and the field table disagree" % (
                    x, row[6], frame[pos], tag))
        pos += 1
        if kind == "wstr":
            size = struct.unpack_from("<I", frame, pos)[0]
            pos += 4
            out[x] = frame[pos:pos + size].decode("utf-16le")
            pos += size
            continue
        if kind not in _READ:
            raise WireDecodeError(
                "x=%d (%s) is kind %r, which this decoder cannot read; every "
                "later field would be read at the wrong offset"
                % (x, row[6], kind))
        code, width = _READ[kind]
        out[x] = struct.unpack_from(code, frame, pos)[0]
        pos += width
    return out
