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

WHAT IS NOT "no call site", and is this module's one real advance: the
restate it composes is handed to `persistence_hp_pair_selector.guard_block`
BEFORE it is offered to any caller.  That door has had no caller anywhere
but its own tests since the round that built it, which is a debt three
`pf-adversary` passes have named.  It now has one, on the exact path the
owner's symptom is on -- so a restate that would itself put a dishonest pair
on the HUD cannot leave this module.
"""

from __future__ import annotations

from dataclasses import dataclass

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

#: The column names behind the primary pair, derived from the same table the
#: compose path reads rather than typed here a second time.  A migration that
#: renames either column moves this with it; a hand-written pair of strings
#: would have gone quietly stale instead.
_PRIMARY_COLUMNS = tuple(SERVER_OWNED_FIELDS[x].column for x in PRIMARY_PAIR)


def alternate_rows_owned_by_this_server() -> tuple[int, ...]:
    """Which of x=52 / x=53 this server has a column for.  Empty today.

    Computed from `SERVER_OWNED_FIELDS`, never written as `()`.  The day a
    migration of this lane adds `boat_health_current` / `boat_health_max`,
    this function changes answer without anyone editing it, and
    `SceneExitVitals.alternate_rows_refused` narrows with it.
    """
    return tuple(x for x in ALTERNATE_PAIR if x in SERVER_OWNED_FIELDS)


@dataclass(frozen=True)
class SceneExitVitals:
    """The restate one character's scene exit may carry, and why.

    `rows` is what a composer may put on the wire: `{}` when nothing may be
    stated, never a dict of invented zeroes.  `reason` is `None` exactly when
    `rows` is non-empty, so a caller cannot read a refusal as a send.
    """

    character_id: int
    scene_id: int
    rows: dict[int, int]
    reason: str | None
    detail: str

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
    symptom, and a restate that is honest there is honest everywhere.  A
    hardcoded `126` here would have to be re-derived the day the ocean has a
    second scene id, and `field_mobs.scene_for_scene_id` already owns that
    mapping for the lanes that need it.
    """
    typed = store.read_typed_attributes(character_id)
    values = [typed.get(column) for column in _PRIMARY_COLUMNS]

    if any(value is None for value in values):
        missing = ", ".join(
            column for column, value in zip(_PRIMARY_COLUMNS, values) if value is None
        )
        return SceneExitVitals(
            character_id=character_id,
            scene_id=scene_id,
            rows={},
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
            rows={},
            reason=REASON_GUARD_REFUSED,
            detail=str(exc),
        )

    return SceneExitVitals(
        character_id=character_id,
        scene_id=scene_id,
        rows=rows,
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
