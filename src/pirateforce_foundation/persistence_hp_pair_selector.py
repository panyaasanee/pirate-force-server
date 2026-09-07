"""Which HP pair the client displays, and the refusal that keeps a lie off it.

LANE-DB, round `o5zblc` (first draft), rewritten in round `cgnzsd` after
`pf-adversary` found the first draft's guard INVERTED.  The rewrite is not a
patch: the trigger, the gap set and the layer attribution all changed.  What
survived is the derivation of the row indices and the read-only report.

THE ONE SENTENCE THE FIRST DRAFT NEVER WROTE -- WHICH LAYER IS THIS ABOUT:

    [FRAME LAYER] This guard is about what a FRAME does.  An alternate-pair
    row that is absent from a frame has an unset mask bit, and the full-
    object-copy apply makes an unset bit a ZERO on this client (`RE-222` Q0,
    quoted at `gm/attr_wire.py:105`), so an armed selector plus an absent or
    zero pair displays HP `0/0` -- `GT-218`'s symptom.
    [CONSTRUCTOR LAYER] `-1/1` is a DIFFERENT fact, one layer down:
    `persistence_attr_compose.CLIENT_CONSTRUCTION_DEFAULTS` says the client
    constructs x=52 = 0xFFFFFFFF and x=53 = 1, which is what the object
    holds when NO frame has ever written those rows at all.

Both are dishonest and this module refuses both, but it no longer tells the
reader that `0/0` is `-1/1`.  Every `REASON_*` below carries its layer in
its own name so a caller reading a refusal cannot mix them up either.

THE MECHANISM, quoted from tables this repository already ships -- none of it
invented here:

* `gm/attr_wire.py` row x=9 is `category_5C` (BasicAttr +0x5C, u16); its own
  note says `0x430E10(this)==8 swaps HP to x52/53`.
* `gm/attr_wire.py` rows x=52/x=53 are `alt_hp_current` / `alt_hp_max`
  (ActorAttr +0x1A8/+0x1AC, u32), "used when 0x430E10(x9)==8".
* `SELECTOR_NOTE_R301` in that module states the shape exactly, and this
  module repeats its correction rather than the tempting shorthand: **the
  alternate pair is not chosen by comparing x=9 with 8.**  x=9 is passed to
  `0x430E10` and it is that function's RESULT that is compared with 8.
  Nothing in this repository can evaluate `0x430E10`.

WHAT THIS MODULE ADDS OVER THE FENCE THAT ALREADY SHIPS -- the question the
first draft was asked and did not answer.  `make_update_attr_frame`
(`gm/attr_wire.py:992`) already refuses

    values.get(SELECTOR_ROW_X) == SELECTOR_COMPARED_VALUE
    and not ALT_HP_PAIR_ROWS <= set(values)

with its own console token `GM_ATTR_SELECTOR_STANDDOWN`.  That is a
MEMBERSHIP test: it asks whether the two rows are in the block, never what
they carry.  Measured on this tree (`test_incumbent_fence_admits_what_this_
module_refuses` runs the incumbent's own clause, imported, not retyped):

    {9: 8}                        -> incumbent refuses   (this module too)
    {9: 8, 52: 0, 53: 0}          -> incumbent ADMITS    -> HUD reads 0/0
    {9: 8, 52: 0xFFFFFFFF, 53: 1} -> incumbent ADMITS    -> HUD reads -1/1

So the shipping fence is exactly one predicate short: presence, not honesty.
This module is that predicate.  It is NOT a second permission gate -- it
never admits anything the incumbent refuses, and there is a test pinning
that direction (`test_this_module_never_admits_what_the_incumbent_refuses`).

WIRING: none yet, deliberately.  The call site is one line inside
`make_update_attr_frame`, which is LANE-GM/chief territory, not LANE-DB's.
This round sends a CORE-REQUEST for that one line instead of reaching into
another lane's file.  Until it is wired this module is a predicate plus a
read-only report, and this docstring must not say otherwise.

WHAT THIS MODULE DOES NOT CLAIM:

* It does NOT claim any scene id takes the alternate pair, 126 included.
  `SELECTOR_NOTE_R301` says in as many words "WHAT CATEGORY 8 IS: not
  decoded", and an earlier draft of that note had to strike a sentence
  telling a tester which scene to visit.  The scene-id-to-category mapping
  is undecoded and no function here computes it.
* It does NOT claim x=9 is the scene id.  `SELECTOR_NOTE_R301` records that
  this repository's own byte-exact sweep RETRACTED that name.
* It does NOT send anything or touch any pre-existing function.

Provenance labels naming files that live in the `pf_bridge` repository (not
in this one, so a clone of this repository cannot open them) are marked
`[pf_bridge]` where they appear, per pf-adversary D6.
"""

from __future__ import annotations

from dataclasses import dataclass

from .gm import attr_wire
from .persistence_attr_compose import CLIENT_CONSTRUCTION_DEFAULTS


class HpPairError(ValueError):
    """A block would let the client display an HP pair the server never set."""


def _x_named(name: str) -> int:
    """The `FIELDS` index whose name is `name`, or raise.

    Derived, never typed: if another lane renames or drops one of these rows
    in `gm/attr_wire.py`, this raises at import and every test in this
    module's suite goes red, rather than this module quietly pinning a stale
    number.  That is the point -- the rows belong to LANE-GM, not here.
    """
    matches = [row[0] for row in attr_wire.FIELDS if row[6] == name]
    if len(matches) != 1:
        raise HpPairError(
            f"gm/attr_wire.FIELDS must name exactly one row {name!r}; "
            f"found {len(matches)}: {matches}"
        )
    return matches[0]


#: BasicAttr HP, the pair the client reads when the selector does not fire.
PRIMARY_PAIR: tuple[int, int] = (_x_named("hp_current"), _x_named("hp_max"))
#: ActorAttr HP, the pair the client reads when `0x430E10(x9) == 8`.
ALTERNATE_PAIR: tuple[int, int] = (
    _x_named("alt_hp_current"),
    _x_named("alt_hp_max"),
)
#: The row whose value is fed to `0x430E10`.  Not the comparand itself.
SELECTOR_FIELD: int = _x_named("category_5C")

#: The value on x=9 that this module treats as arming the selector.
#:
#: IMPORTED, NOT TYPED (pf-adversary D7: the first draft hardcoded `8` and no
#: test read it).  It is `gm/attr_wire.SELECTOR_COMPARED_VALUE`, so the two
#: doors cannot drift apart; if LANE-GM changes its comparand this module
#: follows in the same commit or its tests go red.
#:
#: HONEST NAME OF WHAT THIS IS.  `SELECTOR_NOTE_R301` says the client compares
#: the RESULT of `0x430E10(x9)` with 8, not x=9 itself, so testing `x9 == 8`
#: is a check on an INPUT, not an evaluation of the condition -- the same
#: caveat `gm/attr_wire.py:980-991` writes out by hand for the incumbent
#: fence, with the same named false positive (a player legitimately carrying
#: category byte 8) and the same named false negative (every other input
#: whose `0x430E10` result is 8).  This module inherits both, on purpose:
#: matching the incumbent's trigger exactly is what keeps it a strictly
#: stronger version of the same door rather than a second, different one.
SELECTOR_ARMED_VALUE: int = attr_wire.SELECTOR_COMPARED_VALUE

#: What the client constructs for the alternate pair when NO frame has ever
#: written those rows -- the CONSTRUCTOR layer, taken from the corpus copy
#: rather than retyped.
ALTERNATE_CONSTRUCTION_DEFAULTS: tuple[object, object] = (
    CLIENT_CONSTRUCTION_DEFAULTS[ALTERNATE_PAIR[0]].value,
    CLIENT_CONSTRUCTION_DEFAULTS[ALTERNATE_PAIR[1]].value,
)

_U32_MODULUS = 1 << 32

#: [FRAME LAYER] the row is not in the block, so its mask bit is unset and
#: the client's full-object-copy apply reads it as ZERO (`RE-222` Q0).
REASON_ABSENT_READS_ZERO = "frame_layer_row_absent_unset_mask_bit_reads_zero"
#: [FRAME LAYER] the row IS in the block and carries zero, which is the same
#: number an unset bit produces and is never an honest HP.
REASON_ZERO = "frame_layer_row_carries_zero"
#: [CONSTRUCTOR LAYER] the row carries the value the client would have held
#: anyway if no frame had written it -- sending it changes nothing and hides
#: that nothing was sent.
REASON_CONSTRUCTION_DEFAULT = "constructor_layer_row_carries_client_construction_default"
#: [FRAME LAYER] the row decodes to a negative number on a HUD that prints
#: this row signed.
REASON_NEGATIVE = "frame_layer_row_displays_as_negative"
#: [FRAME LAYER] the row is not a value this wire can carry at all.
REASON_NOT_A_U32 = "frame_layer_row_is_not_a_u32"
#: [FRAME LAYER] current exceeds max, which no HP bar can draw honestly.
REASON_CURRENT_ABOVE_MAX = "frame_layer_current_above_max"

#: Every reason string, so a caller can assert it handled all of them and a
#: new reason added later cannot slip past an exhaustive match unnoticed.
ALL_REASONS: frozenset[str] = frozenset(
    {
        REASON_ABSENT_READS_ZERO,
        REASON_ZERO,
        REASON_CONSTRUCTION_DEFAULT,
        REASON_NEGATIVE,
        REASON_NOT_A_U32,
        REASON_CURRENT_ABOVE_MAX,
    }
)

#: Console token for the refusal, in the shape the bridge console greps for.
#: Distinct from LANE-GM's `GM_ATTR_SELECTOR_STANDDOWN` on purpose: two doors
#: that print the same token cannot be told apart in a log.
HP_PAIR_REFUSED_CONSOLE_TOKEN = "DB_HP_PAIR_DISHONEST"


def as_signed_u32(value: object) -> int:
    """The number the HUD prints for a u32 row, or raise.

    0xFFFFFFFF is what the corpus records and `-1` is what a HUD prints for
    it; this is the one function that turns one into the other, so no other
    place in this module has to know the width.

    `bool` is refused before `int` is accepted: `True` is an `int` in Python
    and `True == 1` is x=53's construction default, so a bool walking in
    here would be reported under the wrong reason.
    """
    if isinstance(value, bool) or not isinstance(value, int):
        raise HpPairError(f"not a u32 value: {value!r}")
    if not 0 <= value < _U32_MODULUS:
        raise HpPairError(f"outside u32: {value!r}")
    return value - _U32_MODULUS if value >= (_U32_MODULUS >> 1) else value


@dataclass(frozen=True)
class PairGap:
    """One reason an alternate-pair row is not honest."""

    x: int
    field_name: str
    reason: str


def _field_name(x: int) -> str:
    for row in attr_wire.FIELDS:
        if row[0] == x:
            return row[6]
    raise HpPairError(f"x={x} is not a row of gm/attr_wire.FIELDS")


def _row_gap(x: int, index: int, values: dict[int, object]) -> PairGap | None:
    """The single reason row `x` is dishonest, or None.

    Order matters and is deliberate: absence first (there is no value to
    look at), then type, then the construction default, then zero, then
    negative.  The construction default is checked before zero and negative
    so a row carrying 0xFFFFFFFF is reported at the CONSTRUCTOR layer that
    explains it rather than merely as "negative".
    """
    if x not in values:
        return PairGap(x, _field_name(x), REASON_ABSENT_READS_ZERO)
    value = values[x]
    try:
        shown = as_signed_u32(value)
    except HpPairError:
        return PairGap(x, _field_name(x), REASON_NOT_A_U32)
    if value == ALTERNATE_CONSTRUCTION_DEFAULTS[index]:
        return PairGap(x, _field_name(x), REASON_CONSTRUCTION_DEFAULT)
    if shown == 0:
        return PairGap(x, _field_name(x), REASON_ZERO)
    if shown < 0:
        return PairGap(x, _field_name(x), REASON_NEGATIVE)
    return None


def alternate_pair_gaps(values: dict[int, object]) -> tuple[PairGap, ...]:
    """Every reason `values` would show a dishonest alternate HP pair.

    Empty means: both alternate rows are present, are u32, are not zero, are
    not the client's own construction default, do not print negative, and
    current does not exceed max.  It does NOT mean the numbers are the
    character's real HP -- this function is handed values, it does not know
    where they came from.

    ZERO IS A GAP, and that is the whole correction of round `cgnzsd`.  The
    first draft refused the construction default and negatives and had no
    opinion about zero, which inverted the guard with respect to this
    repository's strongest evidence: `gm/attr_wire.py:105` (`RE-222` Q0) and
    `_refuse_selector_change`'s own docstring both say an unset mask bit is
    a ZERO on this client and that a frame flipping the selector hands the
    HUD `0/0` -- `GT-218`'s symptom.  A guard against that symptom that
    passes `0/0` is not a weak guard, it is the wrong one.

    KNOWN CONSERVATISM, written down rather than smoothed over: x=53's
    construction default IS the number 1, so a character whose real
    `alt_hp_max` were 1 is reported as a gap it is not.  Refusing a real 1
    costs a refusal; accepting the default puts a lie on a HUD.  This module
    takes the refusal, and the day a server column feeds x=53 the check
    should move to "did a column supply it" instead of comparing values.
    """
    gaps = [
        gap
        for index, x in enumerate(ALTERNATE_PAIR)
        for gap in (_row_gap(x, index, values),)
        if gap is not None
    ]
    if not gaps:
        current = as_signed_u32(values[ALTERNATE_PAIR[0]])
        maximum = as_signed_u32(values[ALTERNATE_PAIR[1]])
        if current > maximum:
            gaps.append(
                PairGap(
                    ALTERNATE_PAIR[0],
                    _field_name(ALTERNATE_PAIR[0]),
                    REASON_CURRENT_ABOVE_MAX,
                )
            )
    return tuple(gaps)


def selector_is_armed(values: dict[int, object]) -> bool:
    """True when x=9 carries the value the incumbent fence stands down on.

    PRESENCE IS NOT THE TRIGGER, and that is the second correction of round
    `cgnzsd`.  The first draft fired whenever x=9 was in the block at all;
    `gm/attr_wire.LOGIN_SOURCED_ROWS` is `{9, 10, 11}` and x=52/x=53 are in
    no login shape this server composes, so that draft would have refused
    every login this server sends.  The trigger is the VALUE, exactly as the
    incumbent fence at `gm/attr_wire.py:992` uses it.
    """
    return values.get(SELECTOR_FIELD) == SELECTOR_ARMED_VALUE


def refusal_message(gaps: tuple[PairGap, ...]) -> str:
    """The console line for a refusal.  ASCII only (the bridge is cp874)."""
    listed = ", ".join(f"x={g.x}({g.field_name}):{g.reason}" for g in gaps)
    return (
        f"{HP_PAIR_REFUSED_CONSOLE_TOKEN} "
        f"selector x={SELECTOR_FIELD} ({_field_name(SELECTOR_FIELD)}) carries "
        f"{SELECTOR_ARMED_VALUE} but {len(gaps)} alternate-pair row(s) are "
        f"not honest -- {listed}; if 0x430E10 returns {SELECTOR_ARMED_VALUE} "
        "for this character the client reads that pair, and an unset or zero "
        "row reads as HP 0/0 on the frame layer (RE-222 Q0, quoted at "
        "gm/attr_wire.py:105), while the client's own construction default "
        "for these rows is 0xFFFFFFFF/1 on the constructor layer"
    )


def guard_alternate_pair(values: dict[int, object]) -> None:
    """Refuse a block that arms the selector without arming the pair it picks.

    A block whose x=9 does not carry `SELECTOR_ARMED_VALUE` -- which is every
    login shape this server composes today -- is none of this function's
    business and passes.  This module does not decide whether a send is
    allowed; it decides that a send which the incumbent fence would let
    through must still not carry a pair the server never honestly set.
    """
    if not selector_is_armed(values):
        return
    gaps = alternate_pair_gaps(values)
    if not gaps:
        return
    raise HpPairError(refusal_message(gaps))


@dataclass(frozen=True)
class HpPairReport:
    """What one real character's HUD would show on each branch."""

    character_id: int
    primary_current: int | None
    primary_max: int | None
    alternate_if_unset_current: int
    alternate_if_unset_max: int
    alternate_pair_supplied: bool

    def branch_would_lie(self) -> bool:
        """True when the alternate branch shows something the row does not."""
        return not self.alternate_pair_supplied


def live_hp_pair_report(store, character_id: int) -> HpPairReport:
    """Read one character's typed HP and say what each branch would display.

    Read-only: the single database call is LANE-DB's own
    `store.read_typed_attributes`, which omits NULL columns rather than
    rendering them as 0 -- so a character whose HP was never seeded comes
    back with `primary_current is None` instead of a fake zero.

    `alternate_pair_supplied` is False unconditionally today and that is a
    measurement, not a placeholder: no column of `characters` maps to x=52
    or x=53 (`persistence_attr_compose.SERVER_OWNED_FIELDS` names the rows
    this server owns and neither of these is among them), so there is
    nothing this server could read for the alternate pair even if a caller
    asked.  It is computed from that constant, not written as `False`, so
    the day a column appears this report changes with it.
    """
    typed = store.read_typed_attributes(character_id)
    server_owned_alternate = [
        x for x in ALTERNATE_PAIR if x in _server_owned_field_indices()
    ]
    return HpPairReport(
        character_id=character_id,
        primary_current=typed.get("hp_current"),
        primary_max=typed.get("hp_max"),
        alternate_if_unset_current=as_signed_u32(
            ALTERNATE_CONSTRUCTION_DEFAULTS[0]
        ),
        alternate_if_unset_max=as_signed_u32(ALTERNATE_CONSTRUCTION_DEFAULTS[1]),
        alternate_pair_supplied=bool(server_owned_alternate),
    )


def _server_owned_field_indices() -> frozenset[int]:
    from .persistence_attr_compose import SERVER_OWNED_FIELDS

    return frozenset(SERVER_OWNED_FIELDS)


def format_report(report: HpPairReport) -> str:
    """One console block, ASCII only (the bridge console is cp874)."""
    primary = (
        "unseeded"
        if report.primary_current is None or report.primary_max is None
        else f"{report.primary_current}/{report.primary_max}"
    )
    lines = [
        "HP_PAIR_SELECTOR_REPORT",
        f"  character_id={report.character_id}",
        f"  primary x={PRIMARY_PAIR[0]}/{PRIMARY_PAIR[1]} shows {primary}",
        f"  alternate x={ALTERNATE_PAIR[0]}/{ALTERNATE_PAIR[1]} shows "
        f"{report.alternate_if_unset_current}/"
        f"{report.alternate_if_unset_max} (constructor layer: client "
        f"construction default, what it holds when no frame ever wrote them)",
        f"  alternate x={ALTERNATE_PAIR[0]}/{ALTERNATE_PAIR[1]} shows 0/0 "
        f"(frame layer: a frame that arms the selector with these rows "
        f"absent, RE-222 Q0)",
        f"  alternate_pair_supplied_by_this_server="
        f"{report.alternate_pair_supplied}",
        f"  selector x={SELECTOR_FIELD} armed value {SELECTOR_ARMED_VALUE}; "
        f"0x430E10 is not evaluated here",
    ]
    return "\n".join(lines)
