"""Which HP pair the client displays, and the refusal that keeps -1 off it.

LANE-DB, round `o5zblc`.  Built because `NOW.md` (COO round `0445`) names a
creation ticket for A/DB in one line: "leaving 126 restores HP; BoatHealth
must not be -1".  The owner's own observation behind that line is
`notes_to_chief/20260907_0123_KA1A-R322B-RESULTS-*.md`: at sea the self
panel showed HP **-1/1**, and after landing, clicking herself STILL showed
HP -1 LV1.

THE MECHANISM, as far as the bytes go -- none of it is invented here, all of
it is quoted from a table this repository already ships:

* `gm/attr_wire.py` row x=9 is `category_5C` (BasicAttr +0x5C, u16), and its
  own note says `0x430E10(this)==8 swaps HP to x52/53`.
* `gm/attr_wire.py` rows x=52/x=53 are `alt_hp_current` / `alt_hp_max`
  (ActorAttr +0x1A8/+0x1AC, u32), "used when 0x430E10(x9)==8".
* `SELECTOR_NOTE_R301` in that same module states the shape exactly, and
  this module repeats its correction rather than the tempting shorthand:
  **the alternate pair is not chosen by comparing x=9 with 8.**  x=9 is
  passed to `0x430E10` and it is that function's RESULT that is compared
  with 8.  Nothing in this repository can evaluate `0x430E10`, so nothing
  here computes the branch -- the branch is an INPUT to this module, to be
  supplied by whoever measured it.
* `persistence_attr_compose.CLIENT_CONSTRUCTION_DEFAULTS` carries the
  client's own constructed value for both alternate rows: x=52 =
  0xFFFFFFFF, x=53 = 1.  Read as the signed u32 the HUD prints, that is
  exactly the "-1 / 1" the owner saw.  A server that never sets the
  alternate pair is therefore not neutral: it ships -1.

WHAT THIS MODULE DOES NOT CLAIM, stated first because the tempting sentence
is wrong:

* It does NOT claim scene 126 is category 8, or name any scene that takes
  the alternate pair.  `SELECTOR_NOTE_R301` says in as many words "WHAT
  CATEGORY 8 IS: not decoded", and an earlier draft of that very note had
  to strike out a sentence that told a tester which scene to visit.  The
  owner's observation is a client-observable symptom; the mapping from
  scene id to category is still undecoded, and the attended ticket this
  round writes is what would decode it.
* It does NOT claim x=9 is the scene id.  `SELECTOR_NOTE_R301` records that
  this repository's own byte-exact sweep RETRACTED that name; x=9 is
  `category_5C` and nothing more.
* It does NOT send anything, compose anything for the wire, or touch any
  pre-existing function.  It reads typed columns through LANE-DB's own
  `store.read_typed_attributes` and otherwise operates on values a caller
  already holds.

THE PRODUCTION PART is `guard_alternate_pair`: a block that carries the
selector row x=9 must also carry an honest alternate pair, or it is refused.
That is the same shape `COO-DECISION 20260904_0215`'s (b'') already applied
one row over -- a row's ABSENCE is not neutral on this client, so "send what
we have" is refused rather than trusted.  Without the guard, the first frame
that legitimately carries x=9 (it is `known=True` and its real value is now
REQUIRED on a named send) hands the HUD an alternate pair the server never
set, which is -1/1 by construction.
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
#: The result `0x430E10` is compared with, per `SELECTOR_NOTE_R301`.
SELECTOR_RESULT_FOR_ALTERNATE: int = 8

#: What the client constructs for the alternate pair when the server is
#: silent, taken from the corpus copy rather than retyped.
ALTERNATE_CONSTRUCTION_DEFAULTS: tuple[object, object] = (
    CLIENT_CONSTRUCTION_DEFAULTS[ALTERNATE_PAIR[0]].value,
    CLIENT_CONSTRUCTION_DEFAULTS[ALTERNATE_PAIR[1]].value,
)

_U32_MODULUS = 1 << 32

REASON_MISSING = "alternate_pair_row_absent_client_keeps_its_construction_default"
REASON_CONSTRUCTION_DEFAULT = "alternate_pair_row_carries_the_client_construction_default"
REASON_NEGATIVE = "alternate_pair_row_displays_as_negative"
REASON_NOT_AN_INT = "alternate_pair_row_is_not_a_u32"


def as_signed_u32(value: object) -> int:
    """The number the HUD prints for a u32 row, or raise.

    0xFFFFFFFF is what the corpus records and `-1` is what the owner saw;
    this is the one function that turns one into the other, so no other
    place in this module has to know the width.
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


def alternate_pair_gaps(values: dict[int, object]) -> tuple[PairGap, ...]:
    """Every reason `values` would show a dishonest alternate HP pair.

    Empty means: both alternate rows are present, are u32, are not the
    client's own construction default, and do not print negative.  It does
    NOT mean the numbers are the character's real HP -- this function is
    handed values, it does not know where they came from.

    KNOWN CONSERVATISM, written down rather than smoothed over: x=53's
    construction default IS the number 1, so a character whose real
    `alt_hp_max` were 1 is reported as a gap it is not.  Refusing a real
    1 costs a refusal; accepting the default would put -1 on a HUD.  This
    module takes the refusal, and the day a server column feeds x=53 the
    check should move to "did a column supply it" instead of comparing
    values.
    """
    gaps: list[PairGap] = []
    for i, x in enumerate(ALTERNATE_PAIR):
        if x not in values:
            gaps.append(PairGap(x, _field_name(x), REASON_MISSING))
            continue
        value = values[x]
        if value == ALTERNATE_CONSTRUCTION_DEFAULTS[i]:
            gaps.append(PairGap(x, _field_name(x), REASON_CONSTRUCTION_DEFAULT))
            continue
        try:
            shown = as_signed_u32(value)
        except HpPairError:
            gaps.append(PairGap(x, _field_name(x), REASON_NOT_AN_INT))
            continue
        if shown < 0:
            gaps.append(PairGap(x, _field_name(x), REASON_NEGATIVE))
    return tuple(gaps)


def guard_alternate_pair(values: dict[int, object]) -> None:
    """Refuse a block that arms the selector without arming the pair it picks.

    A block that does not carry x=9 at all is none of this function's
    business and passes: this module does not decide whether a send is
    allowed, only that a send which can flip the client onto the alternate
    pair must have set that pair.
    """
    if SELECTOR_FIELD not in values:
        return
    gaps = alternate_pair_gaps(values)
    if not gaps:
        return
    listed = ", ".join(f"x={g.x}({g.field_name}):{g.reason}" for g in gaps)
    raise HpPairError(
        f"block carries the HP-pair selector x={SELECTOR_FIELD} "
        f"({_field_name(SELECTOR_FIELD)}) but {len(gaps)} alternate-pair "
        f"row(s) have no honest value -- {listed}; if 0x430E10 returns "
        f"{SELECTOR_RESULT_FOR_ALTERNATE} for this character the client "
        "displays that pair, and its own construction default prints as "
        "HP -1/1 (SELECTOR_NOTE_R301)"
    )


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
    or x=53 (`persistence_attr_compose.SERVER_OWNED_FIELDS` names 22 rows
    and neither of these is among them), so there is nothing this server
    could read for the alternate pair even if a caller asked.
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
        f"{report.alternate_if_unset_max} (client construction default)",
        f"  alternate_pair_supplied_by_this_server="
        f"{report.alternate_pair_supplied}",
        f"  selector x={SELECTOR_FIELD} result compared with "
        f"{SELECTOR_RESULT_FOR_ALTERNATE}; 0x430E10 is not evaluated here",
    ]
    return "\n".join(lines)
