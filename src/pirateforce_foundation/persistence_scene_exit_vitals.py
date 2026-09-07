"""What the server must restate about HP when a character leaves a scene.

LANE-DB, round `5vzis0`.  Ordered by `COO-DECISION 20260907_1441` (owner of
the "blue bar / BoatHealth" ticket set to LANE-DB alone) and by `NOW.md`
line 34, which names `GT-301` as this lane's next queue item: leaving scene
`126` must return the CHARACTER's HP, and `BoatHealth` must not be `-1`.

THE SYMPTOM AND ITS ARITHMETIC, so nobody has to re-derive it:

    `KA1A-R322B` (owner, at the client): in the sea the panel reads `HP -1/1`,
    and after landing, clicking on self still reads `HP -1 LV1`.

    `-1/1` is not a corrupted number.  It is EXACTLY the client's own
    construction default for the alternate HP pair, which this repository
    already ships as a measured table:
    `persistence_attr_compose.CLIENT_CONSTRUCTION_DEFAULTS` rows x=52 and
    x=53 are `0xFFFFFFFF` and `1`, named `GetBoatHealth_current` /
    `GetBoatHealth_max` (`PROVEN_EXACT`, ActorAttr +0x1A8/+0x1AC, in
    `pf_bridge/notes_to_chief/reference_codex_attr/
    PF_ATTR_FIELD_SEMANTICS.tsv`).  `0xFFFFFFFF` read as a signed 32-bit row
    is `-1`.  So the panel is not showing a broken character HP; it is
    showing the BOAT's health rows, never written by any frame, still
    holding what the client's constructor put there.

    That is the whole of `R321`'s "faction" theory refuted with arithmetic
    rather than opinion, which is also what `COO-DECISION 20260907_1441`
    item 3 ordered: faction arrived in full and the bar stayed wrong, so
    this is not a faction ticket and its pass criterion must not be tied to
    `GT-281`.

WHAT THIS MODULE DECIDES, AND WHAT IT REFUSES TO DECIDE:

* It decides what the server may RESTATE from its own row on a scene exit:
  the primary pair x=3 / x=4, and only when the database really holds both.
  `store.read_typed_attributes` omits a NULL column rather than rendering it
  `0`, so an unseeded character arrives here as absent and is REFUSED, not
  guessed (`COO-ORDER 20260901_1059`, the rule this lane exists under).
* It refuses to state x=52 / x=53 at all.  No column of `characters` maps to
  either row -- MEASURED here from `SERVER_OWNED_FIELDS` rather than written
  as a literal, so the day this lane ships those columns the refusal lifts
  by itself -- and a server that invented a boat's health would be guessing
  the very kind of number the owner's rule bans.  `BoatHealth != -1` is
  therefore NOT satisfied by this module inventing a boat HP; it is
  satisfied by the server owning the rows or by the client being put back on
  the primary branch.  Which of those two is the fix is a question for the
  attended run `GT-301` asks for, and it is written into that ticket rather
  than answered here.

WHO CALLS THIS, HONESTLY STATED: nothing in `src/` today, and the seam it
needs is not in this lane's write zone.  `COO-DECISION 20260907_1441` item 6
names where it comes from -- LANE-A pays the scene-edge seam on request --
and the request went out in the same round as this file
(`pf_bridge/notes_to_chief/*_LANE-DB-TO-A-scene-edge-seam-for-hp-restate.md`,
in the other repository; a reviewer of this one cannot open it, which is why
it is named as a request rather than cited as an authority).

WHAT THE `guard_block` CALL IS AND IS NOT.  The restate this module composes
is handed to `persistence_hp_pair_selector.guard_block` before it is
returned, and that door had no caller outside its own tests until this
round.  Stated precisely, because the first draft of this paragraph
overstated it twice and `pf-adversary` measured both:

* NOT "the door is now on the path the owner's symptom is on".  This module
  has no caller either, so what the door gained is an import-graph edge to a
  second unwired module.  The production HP path (the session's login vitals
  seam, down to this lane's vitals resolver) still does not call it.
* NOT the discharge of an outstanding debt.  That door's own module records a
  MEASURED, deliberate scope decision -- there is no hole in the login wall
  for it to plug, and the request for a call site was WITHDRAWN in the round
  that wrote it.  Calling that a debt and paying it here would be reframing
  finished reasoning as an oversight.
* What it IS: a real refusal on a real input set.  Probed on pairs a migrated
  store can hold, the call refuses `101/100`, `50/0`, `0xFFFFFFFF/1`,
  `0xFFFFFFF0/0xFFFFFFFF` and `2**31/2**32-1`, and ADMITS `0/100` -- a dead
  character, which must pass, and which the first draft of this module's
  suite never tested even once.
"""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType

from .persistence_attr_compose import SERVER_OWNED_FIELDS
from .persistence_hp_pair_selector import (
    ALTERNATE_PAIR,
    HpPairError,
    PRIMARY_PAIR,
    guard_block,
)

#: The token an operator greps for in a headless boot.  ASCII only: the
#: bridge console is cp874 and a character outside that range kills the tool
#: that reads it (`COMMON_LANE_ROUND`, "code and console output are ASCII").
SCENE_EXIT_VITALS_CONSOLE_TOKEN = "DB_SCENE_EXIT_VITALS"

#: Restate refused because the row does not hold both halves of the pair.
#: The name says `unseeded` and not `missing` on purpose: the column exists
#: (`migrations/006_character_typed_attribute_columns.sql` built it), it just
#: has no value, and those are different repairs.
REASON_ROW_UNSEEDED = "primary_pair_not_seeded_in_the_row"

#: Restate refused because the composed pair would itself be dishonest.
#: Reaching this means `guard_block` spoke; its message is carried whole.
REASON_GUARD_REFUSED = "hp_pair_guard_refused_the_restate"

#: x=52 / x=53 are not stated by this server.  Not an error -- a boundary.
REASON_ALTERNATE_UNOWNED = "boat_health_rows_have_no_column_on_this_server"

#: The column names behind the primary pair, READ from the same table the
#: compose path reads rather than typed here a second time.
#:
#: WHAT THAT BUYS AND WHAT IT DOES NOT, because the sentence that stood here
#: claimed more than it delivers: `SERVER_OWNED_FIELDS` holds HAND-WRITTEN
#: strings (`_SERVER_OWNED_ROWS` in that module), so a MIGRATION renaming
#: `hp_current` moves nothing here -- a human editing that table does.  What
#: reading it buys is that this module and the compose path cannot disagree
#: about which column is x=3.  `SchemaPinTests` is what compares that table
#: to `migrations/`; this line free-rides on that and does not replace it.
def _primary_columns() -> tuple[str, ...]:
    """The `characters` columns behind x=3 / x=4, read at call time.

    A FUNCTION rather than a module constant, and that is the repair for
    pf-adversary `5vzis0` D8 rather than a style choice: as a constant
    evaluated at import, the literal `("hp_current", "hp_max")` was
    indistinguishable from the read, because the only test of it compared the
    constant to the same expression that built it -- a tautology that both
    spellings pass.  Computed per call, a test can patch the owned table and
    watch the answer move, which is what kills the literal.  It is the same
    shape `alternate_rows_owned_by_this_server` already had, and the reason
    that one's mutants died while this one's survived.
    """
    return tuple(SERVER_OWNED_FIELDS[x].column for x in PRIMARY_PAIR)


def alternate_rows_owned_by_this_server() -> tuple[int, ...]:
    """Which of x=52 / x=53 this server has a column for.  Empty today.

    Computed from `SERVER_OWNED_FIELDS`, never written as `()` -- and that
    much IS defended: this module's suite patches that table to pretend a
    column shipped and watches the answer narrow, which kills the literal.

    The day this lane ships `boat_health_current` / `boat_health_max` takes
    TWO edits and the sentence that stood here named only one: a migration
    for the columns, AND a row in `_SERVER_OWNED_ROWS`, whose strings are
    typed by hand.  This function follows the second automatically.  It does
    not read `migrations/`, and saying it changes answer "without anyone
    editing it" was a false docstring sentence of exactly the kind this lane
    has now shipped in four consecutive rounds.
    """
    return tuple(x for x in ALTERNATE_PAIR if x in SERVER_OWNED_FIELDS)


@dataclass(frozen=True)
class SceneExitVitals:
    """The restate one character's scene exit may carry, and why.

    `rows` is what a composer may put on the wire: empty when nothing may be
    stated, never a mapping of invented zeroes.

    IT IS A READ-ONLY VIEW, and `frozen=True` is why that has to be said
    separately.  `frozen` stops the FIELD being rebound; it does nothing
    about the mapping behind it.  With a plain dict a caller could write
    `rows[52] = 0xFFFFFFFF` AFTER `guard_block` had passed the pair, and
    `console_line` would then print x=52 carrying -1 while still reporting
    the boat rows as unstated.  A guard verdict that does not bind the object
    it verified is not a verdict, so what is handed out is a
    `MappingProxyType` and that write raises.

    `reason` is `None` exactly when `rows` is non-empty -- enforced in
    `__post_init__` rather than promised here, because an invariant attached
    to a class anyone can construct is a property of the factory, not of the
    class.
    """

    character_id: int
    scene_id: int
    rows: "MappingProxyType[int, int] | dict[int, int]"
    reason: str | None
    detail: str

    def __post_init__(self):
        if bool(self.rows) != (self.reason is None):
            raise ValueError(
                "SceneExitVitals must carry a reason when it states no rows, "
                "and no reason when it states some: "
                f"rows={dict(self.rows)!r} reason={self.reason!r}"
            )

    @property
    def may_restate(self) -> bool:
        """True when the server has something honest to say about HP here."""
        return bool(self.rows)

    @property
    def alternate_rows_refused(self) -> tuple[int, ...]:
        """The boat rows this restate deliberately says nothing about."""
        owned = set(alternate_rows_owned_by_this_server())
        return tuple(x for x in ALTERNATE_PAIR if x not in owned)


def resolve_for_scene_exit(store, character_id: int, scene_id: int) -> SceneExitVitals:
    """What the server may restate about HP as `character_id` leaves `scene_id`.

    Read-only.  One database call, this lane's own `read_typed_attributes`,
    which raises `KeyError` for a character that does not exist or has been
    soft-deleted -- deliberately not caught here, because a scene exit for a
    character the database does not have is a bug in the caller, not a gap in
    the row.

    `scene_id` is carried, never compared.  This module holds no opinion that
    scene `126` is special: the ocean panel is where the owner SAW the
    symptom, and a restate that is honest there is honest everywhere.

    A NAME THIS PARAGRAPH USED TO CARRY AND MUST NOT: it claimed another
    module of this repository "already owns" the scene-id-to-ocean mapping.
    MEASURED, and false twice over -- that function answers `None` for scene
    126 (it maps only the scenes with a mined mob roster, and the module that
    does resolve 126 is a different one), and merely NAMING it in this
    docstring turned that module's own importer pin RED, because the pin is a
    substring scan.  Deleted rather than repaired: this module does not need
    to know which module owns the ocean, which is the point of not comparing
    `scene_id` at all.
    """
    typed = store.read_typed_attributes(character_id)
    columns = _primary_columns()
    values = [typed.get(column) for column in columns]

    if any(value is None for value in values):
        missing = ", ".join(
            column for column, value in zip(columns, values) if value is None
        )
        return SceneExitVitals(
            character_id=character_id,
            scene_id=scene_id,
            rows=MappingProxyType({}),
            reason=REASON_ROW_UNSEEDED,
            detail=(
                f"no value in the row for {missing}; the server states nothing "
                "rather than a zero it never measured"
            ),
        )

    rows = {x: int(value) for x, value in zip(PRIMARY_PAIR, values)}
    try:
        guard_block(rows)
    except HpPairError as exc:
        return SceneExitVitals(
            character_id=character_id,
            scene_id=scene_id,
            rows=MappingProxyType({}),
            reason=REASON_GUARD_REFUSED,
            detail=str(exc),
        )

    return SceneExitVitals(
        character_id=character_id,
        scene_id=scene_id,
        # Read-only: the guard has spoken about exactly this mapping, and no
        # caller may edit it afterwards.  See the class docstring.
        rows=MappingProxyType(rows),
        reason=None,
        detail=(
            f"x={PRIMARY_PAIR[0]}/{PRIMARY_PAIR[1]} restated from the row; "
            f"x={ALTERNATE_PAIR[0]}/{ALTERNATE_PAIR[1]} "
            f"({REASON_ALTERNATE_UNOWNED}) left unstated"
        ),
    )


def console_line(resolved: SceneExitVitals) -> str:
    """One ASCII line for a headless boot.  Never more than one line.

    The refusal spelling shouts (`!!`) for the same reason this lane's login
    console line does: an operator scrolling a boot log has to see a refusal
    without reading it, and a refusal that looks like a success is how a gap
    survives an attended run.  That module is deliberately described rather
    than NAMED here -- its own suite pins the set of files that mention it,
    because it may be reached from exactly ONE seam under `src/`
    (`COO-DECISION 20260903_0447`), and that pin is a substring scan which a
    bare mention in prose would trip.  MEASURED: naming it here turned
    `TheModuleOwnsNoConstantsTests::test_the_module_has_at_most_one_seam_and_
    it_is_the_login_one` red in this round's first full-suite run.  The pin is
    right and this file is the one that moves: nothing here imports it.
    """
    stated = (
        ",".join(f"x{x}={value}" for x, value in sorted(resolved.rows.items()))
        if resolved.rows
        else "none"
    )
    refused = "/".join(f"x{x}" for x in resolved.alternate_rows_refused) or "none"
    head = SCENE_EXIT_VITALS_CONSOLE_TOKEN
    if not resolved.may_restate:
        head = f"!! {SCENE_EXIT_VITALS_CONSOLE_TOKEN}"
    return (
        f"{head} character_id={resolved.character_id} "
        f"scene={resolved.scene_id} restated={stated} "
        f"boat_rows_unstated={refused} "
        f"reason={resolved.reason or 'none'}"
    )
