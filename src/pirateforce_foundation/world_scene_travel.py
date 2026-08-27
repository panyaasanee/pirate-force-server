"""Scene destinations for a player - LANE-A build order BUILD-002.

WHAT THIS MODULE IS FOR.  ``scene_id`` has carried the value 1 in every frame
this project has ever sent from its default path, and the one time it carried
2 it was behind ``--scene-load-scenario``.  The client, meanwhile, ships a
table of 271 registered scenes.  This module makes a scene a NAMED DESTINATION
with pinned facts instead of a magic number, so the runtime can put a player
somewhere other than Port Royal without a flag and without anyone re-deriving
the same table row from the bridge repository a third time.

WHAT ``scene_id`` MIGHT BE, AND WHY THAT IS STILL A CANDIDATE.  The reading
this module is built on is that the wire value is the ``n_ID`` column of the
client's own ``CONSTDATA_TH__SCENE_NAME`` table:

* ``n_ID`` 1 is model ``BG0001``, and bg0001 is the map every boot in this
  project has rendered under ``scene_id = 1``.
* ``n_ID`` 2 is model ``BG0002``, Prison Exile Island, and
  ``docs/EXPERIMENT_LEDGER.md:31`` records SCENE-001 as a runtime PASS in
  which the client loaded and rendered Prison Exile Island after this server
  sent ``scene_id = 2``.

    THAT IS NOT AN IDENTITY YET, AND CALLING IT ONE WOULD REPEAT A MISTAKE
    THIS PROJECT HAS ALREADY REFUSED ONCE.  Rows 1 and 2 are two of the twelve
    rows where ``n_MARKER`` and ``n_CLINE_TYPE`` both happen to equal
    ``n_ID`` - and they are also the first and second data rows in the file.
    Three rival readings therefore agree with both observations and disagree
    about this destination: under the marker reading Bg1177 has no addressable
    value at all (its ``n_MARKER`` is 0), under the cline reading it is
    ``0xFFFFFFFF``, and under the row-ordinal reading it is 252, not 278.
    ``GT-053`` refused a ``MAP_SCENE_LIST.n_ID`` join for exactly this reason.
    What settles it is ``RE-077`` job T2 on the HIT path (open), or the
    attended boot in ``GT-078``.  Until then ``sent_before`` is the module's
    own answer to "has this client ever accepted such a value", and it says NO
    for 278.

THE DESTINATION THIS BUILD ORDER TARGETS.  ``n_ID`` 278, model ``Bg1177``,
named "beach football field (TEST)" by the original developers, with
``s_IMAGENAME`` ``BgNull``.  Its shipped ``.npc`` carries nine placements, all
named ``Mob_set_*``, and their geometry is the only ground evidence anybody in
this project has for any scene::

    x span 6195.03    y span 2209.42    z span 0.00195 units

Nine positions spread over six thousand units share one z to within float32
noise.  Whoever placed those mobs treated the whole area as one flat plane -
which is what the owner asked for on 2026-08-25 20:1x (+07:00): wide, flat, no
crates, no hull, no water to fall into.

    THAT IS NOT A TERRAIN MEASUREMENT.  A ``.npc`` file carries NPC placements
    and nothing else.  Flat placement z says where a developer put mobs; it
    does not describe the ground mesh, walls, water, sky or lighting, and it
    cannot say whether the stage is white.  The eye check in the attended
    ticket decides that.  This module pins what the file says and stops.

WHAT THIS MODULE DELIBERATELY DOES NOT BUILD.  Moving a character who is
ALREADY LIVE from one scene to another is not here.  Nobody in this project
knows what the client needs, in what order, to survive that transition -
``RE-077 SCENE-TRANSITION-SEQUENCE-001`` is open and unanswered.  Guessing a
sequence and shipping it would produce a lane that "works" until it silently
does not.  What is here is the half that rests on measured shape: which scene
a player ENTERS, and where they stand when they get there.

THE CROSS-BUILD-ORDER HAZARD.  BUILD-001 delivers 115 bg0001 placements built
with ``SCENE_ID`` hardcoded to 1.  The moment a player can enter scene 278, a
runtime that keeps calling the census unchanged would deliver bg0001's dock
population into a football field.  ``population_source()`` REPORTS which
population is true for a scene, and a report is not a guard: the refusal that
actually prevents it lives in ``world_population.build_world_population``,
which since round jjxgz3 takes a required ``scene_id`` and raises anywhere but
home.  Use both - this one to decide, that one to make the decision binding.

THE RETURN TICKET, WHICH IS PART OF THE DESIGN AND NOT A DETAIL.  Row 278
carries ``n_SAVE = 0`` and ``n_MARKER = 0``: the client's own table marks this
scene as not-saved and gives it no authored arrival point, and ``RE-077`` is
open, so there is no in-game way out of it that anybody here can name.  A
character whose persisted row is rewritten to 278 is therefore a character who
cannot walk home, and CHARTER-02 rule 2 says a version that takes away what
the last version could do is not a version, it is damage.  So this module
ships the way back in the same breath as the way there: ``home_return_position``
returns the row that puts a character back in Port Royal, and the attended
ticket restores it at teardown.  Do not use ``entry_position`` without deciding
who calls ``home_return_position`` afterwards.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from .model import Position
from .population import SCENE_ID, SCENE_SEQUENCE


# Convention marker only.  Nothing in this tree branches on it.  Until
# runtime.py - the chief's file, not this lane's - calls into this module, a
# player logs in exactly where they logged in yesterday.
production_allowed = True
test_only = False

REGISTRY_FILENAME = "world_scene_registry_001.json"
REGISTRY_PATH = (
    Path(__file__).resolve().parents[2] / "scenarios" / REGISTRY_FILENAME
)

HOME_SCENE_ID = SCENE_ID
TEST_STAGE_SCENE_ID = 278
MEASURED_SCENE_IDS = (1, 2)
CENSUS_SCENE_ID = SCENE_ID
CENSUS_SOURCE = "bg0001_census"
CLIENT_REGISTERED_SCENE_COUNT = 271

_DESTINATION_FIELDS = {
    "n_id", "model_id", "scene_name_source_utf8_hex", "scene_name_ascii",
    "image_name", "native_placement_count", "native_definition_count",
    "native_sha256", "role", "status", "table_row", "spawn", "ground",
}
# Optional per-destination blocks.  ``superseded_spawn`` is history kept in
# place rather than deleted; ``table_row_differences`` is commentary on the
# pinned columns and carries no value the code reads.
_DESTINATION_OPTIONAL_FIELDS = {"superseded_spawn", "table_row_differences"}
_SPAWN_FIELDS = {"x", "y", "z", "provenance"}
# Every column the client's table carries that this project has any reason to
# look at.  They are validated as present rather than read selectively, so a
# destination cannot be pinned with the interesting half of its row missing -
# which is how scene 278's n_SAVE=0 and n_MARKER=0 nearly went unrecorded.
_TABLE_ROW_FIELDS = {
    "n_SCENE_WEATHER", "n_SCENE_DAYANDNIGHT", "n_SCENE_TYPE",
    "n_SCENE_SUBTYPE", "n_CLINE_TYPE", "n_CANGLIDE", "n_CANRIDE",
    "n_LIMIT_HEIGHT", "n_SAVE", "n_MARKER", "n_CAMERA_TYPE", "n_COLLECT_MAP",
    "n_SCENE_LV", "n_VIDEO_NAME",
}
_GROUND_FIELDS = {
    "derived_from", "placements_tsv", "placements_tsv_sha256",
    "x_min", "x_max", "y_min", "y_max", "z_min", "z_max", "z_spread",
    "extent_x", "extent_y", "extent_x_named_records_only",
    "closest_pair_distance", "farthest_pair_distance", "record_shape_note",
    "undecoded_columns", "reading", "limit",
}
_ROOT_FIELDS = {
    "schema", "id", "lane", "build_order", "test_only", "production_allowed",
    "selection", "not_a_scenario", "wire_field", "provenance",
    "table_columns_pinned", "destinations", "capabilities", "nonclaims",
}


@dataclass(frozen=True)
class SceneDestination:
    """One addressable scene, with every fact that decides whether to use it."""

    n_id: int
    model_id: str
    scene_name_ascii: str
    image_name: str
    native_placement_count: int
    role: str
    status: str
    spawn: tuple[float, float, float] | None
    spawn_provenance: str | None
    ground_z_spread: float | None
    ground_extent: tuple[float, float] | None
    save_flag: int
    entry_marker: int
    camera_type: int
    limit_height: int

    @property
    def has_authored_entry(self) -> bool:
        """Whether the client's own table gives this scene an arrival marker.

        Scene 278 has none, which is half of why a character sent there has no
        way home (the other half is that RE-077 is open).  A caller that moves
        a character into a scene where this is False owes that character a
        return path - see ``home_return_position``.
        """
        return self.entry_marker != 0

    @property
    def persists_characters(self) -> bool:
        """Whether the table marks this scene the way it marks scenes 1 and 2.

        What n_SAVE gates is not measured here; what IS measured is that both
        scenes this client has ever loaded for us carry 1 and this one carries
        0.  Treated as a warning to carry, not as a prediction.
        """
        return self.save_flag != 0

    @property
    def sent_before(self) -> bool:
        """True only for scene ids a live client in this project has accepted.

        A destination that is addressable in the client's table is not thereby
        a destination the client has been observed to load.  Callers that need
        the difference get it from here rather than from reading ``n_id``.
        """
        return self.n_id in MEASURED_SCENE_IDS


@dataclass(frozen=True)
class SceneRegistry:
    destinations: tuple[SceneDestination, ...]

    def __getitem__(self, n_id: int) -> SceneDestination:
        for destination in self.destinations:
            if destination.n_id == n_id:
                return destination
        raise KeyError(f"scene {n_id} is not pinned in the registry")

    @property
    def ids(self) -> tuple[int, ...]:
        return tuple(item.n_id for item in self.destinations)


def _require_int(value: Any, label: str, low: int, high: int) -> int:
    if type(value) is not int or not low <= value <= high:
        raise ValueError(f"{label} must be an integer in [{low},{high}]")
    return value


def _require_text(value: Any, label: str) -> str:
    if type(value) is not str or not value or not value.isascii():
        raise ValueError(f"{label} must be non-empty ASCII text")
    return value


def _require_float(value: Any, label: str) -> float:
    if type(value) not in (int, float):
        raise ValueError(f"{label} must be a number")
    return float(value)


PROVISIONAL_SPAWN_PROVENANCE_PREFIX = "PROVISIONAL-OWNER-DECREE"


def _spawn(raw: Any, ground: Any, n_id: int) -> tuple[
    tuple[float, float, float] | None, str | None
]:
    if raw is None:
        return None, None
    if type(raw) is not dict or set(raw) != _SPAWN_FIELDS:
        raise ValueError(f"scene {n_id} spawn is incomplete or has unknown fields")
    point = tuple(_require_float(raw[axis], f"scene {n_id} spawn {axis}")
                  for axis in "xyz")
    provenance = _require_text(raw["provenance"], f"scene {n_id} spawn provenance")
    is_provisional = provenance.startswith(PROVISIONAL_SPAWN_PROVENANCE_PREFIX)
    if ground is not None and not is_provisional:
        # A spawn point outside the only ground this scene has evidence for is
        # a standing position nobody measured.  This can fire: the spawn and
        # the bounds are separate rows in the pin and an edit to either one
        # alone breaks the relation.  Skipped for a PROVISIONAL-OWNER-DECREE
        # spawn on purpose: the owner's decree (scene 17, 2026-08-27T14:45+07:00,
        # see world_scene_entry.py's SCENE_ENTRY token) is explicitly NOT
        # derived from ground evidence -- checking it against ground would
        # refuse the very override it exists to make, and the registry itself
        # already lands the ground block and the decree in the same round
        # without either one retracting the other (see world_scene_registry_
        # 001.json's own merge note on this entry).
        #
        # TWO KNOWN LIMITS, NAMED RATHER THAN HIDDEN (pf-adversary, round
        # e0daaa). (1) This is a bare string-prefix match on JSON text this
        # loader trusts completely -- nothing here cross-checks the
        # provenance against a real letter under pf_bridge/notes_to_chief/,
        # so a hand-edit that merely types the right prefix would exempt any
        # destination's spawn from its ground check, real decree or not.
        # This matches how every OTHER provenance string in this file is
        # already trusted (hashes here pin gamedata files, never decree
        # authorization), so it is not a new hole this exemption introduces,
        # but it is a real one. (2) Nothing here or in resolve_entry expires
        # this exemption when the decree's own stated condition (RE-103 T3
        # evidence landing) is met -- retiring it today means a human
        # hand-edits this JSON back to a measured spawn. There is no
        # mechanism that would notice or alert if that day arrives and
        # nobody remembers.
        for axis, low, high in (
            ("x", ground["x_min"], ground["x_max"]),
            ("y", ground["y_min"], ground["y_max"]),
            ("z", ground["z_min"], ground["z_max"]),
        ):
            value = point["xyz".index(axis)]
            if not _require_float(low, "bound") <= value <= _require_float(high, "bound"):
                raise ValueError(
                    f"scene {n_id} spawn {axis} is outside the pinned placement bounds"
                )
    return point, provenance


def load_scene_registry(path: str | Path = REGISTRY_PATH) -> SceneRegistry:
    """Read and validate the pinned destination table.

    The two source files these facts came from live in the bridge repository
    and are not present here, so this cannot re-derive them; it checks the
    shape of the pin and the relations INSIDE it, and the hashes it carries are
    what a bridge-side round re-checks against the sources.
    """
    data = json.loads(Path(path).read_text(encoding="ascii"))
    if type(data) is not dict or set(data) != _ROOT_FIELDS:
        raise ValueError("scene registry root is incomplete or has unknown fields")
    if (
        data["schema"] != 1
        or data["id"] != "world_scene_registry_001"
        or data["test_only"] is not False
        or data["production_allowed"] is not True
    ):
        raise ValueError("unsupported scene registry")
    rows = data["destinations"]
    if type(rows) is not list or not rows:
        raise ValueError("scene registry has no destinations")

    destinations: list[SceneDestination] = []
    seen: set[int] = set()
    for row in rows:
        if (
            type(row) is not dict
            or not _DESTINATION_FIELDS <= set(row)
            or not set(row) <= (_DESTINATION_FIELDS | _DESTINATION_OPTIONAL_FIELDS)
        ):
            raise ValueError("scene destination is incomplete or has unknown fields")
        n_id = _require_int(row["n_id"], "scene n_ID", 1, 0xFFFF)
        if n_id in seen:
            raise ValueError(f"scene {n_id} is pinned twice")
        seen.add(n_id)
        ground = row["ground"]
        if ground is not None and (
            type(ground) is not dict or set(ground) != _GROUND_FIELDS
        ):
            raise ValueError(
                f"scene {n_id} ground is incomplete or has unknown fields")
        table_row = row["table_row"]
        if type(table_row) is not dict or set(table_row) != _TABLE_ROW_FIELDS:
            raise ValueError(
                f"scene {n_id} table row is incomplete or has unknown fields")
        for column, value in table_row.items():
            _require_int(value, f"scene {n_id} {column}", 0, 0xFFFFFFFF)
        spawn, spawn_provenance = _spawn(row["spawn"], ground, n_id)
        destinations.append(SceneDestination(
            n_id=n_id,
            model_id=_require_text(row["model_id"], "model id"),
            scene_name_ascii=_require_text(row["scene_name_ascii"], "scene name"),
            image_name=_require_text(row["image_name"], "image name"),
            native_placement_count=_require_int(
                row["native_placement_count"], "native placement count", 0, 0xFFFF),
            role=_require_text(row["role"], "role"),
            status=_require_text(row["status"], "status"),
            spawn=spawn,
            spawn_provenance=spawn_provenance,
            ground_z_spread=(
                None if ground is None
                else _require_float(ground["z_spread"], "z spread")),
            ground_extent=(
                None if ground is None
                else (_require_float(ground["extent_x"], "extent x"),
                      _require_float(ground["extent_y"], "extent y"))),
            save_flag=table_row["n_SAVE"],
            entry_marker=table_row["n_MARKER"],
            camera_type=table_row["n_CAMERA_TYPE"],
            limit_height=table_row["n_LIMIT_HEIGHT"],
        ))
    return SceneRegistry(tuple(destinations))


def destination(
    n_id: int = HOME_SCENE_ID,
    registry: SceneRegistry | None = None,
) -> SceneDestination:
    """The pinned destination for a scene id, or a refusal naming the reason.

    Called with no argument this is home: scene 1, which is what the runtime
    does today.  Nothing about this module changes where anybody lands until a
    caller passes another id on purpose.
    """
    return (registry or load_scene_registry())[
        _require_int(n_id, "scene n_ID", 1, 0xFFFF)
    ]


def entry_fields(target: SceneDestination) -> tuple[int, int]:
    """The ``(scene_id, scene_seq)`` pair to put in the player's entry frame.

    ``scene_seq`` is 0 for every destination because 0 is the only value ever
    measured, at scene 1 and at scene 2 alike.  It is returned rather than left
    to the caller so that a scene change cannot quietly become a scene-sequence
    change at the same time.
    """
    if type(target) is not SceneDestination:
        raise ValueError("entry fields need a SceneDestination")
    return (target.n_id, SCENE_SEQUENCE)


def spawn_position(target: SceneDestination) -> tuple[float, float, float]:
    """Where to stand a character that enters this destination.

    Refuses rather than inventing a position for a scene with no pinned spawn:
    a made-up standing position in an unmeasured scene is the fastest way to
    produce a boot that fails for a reason nobody can name.
    """
    if type(target) is not SceneDestination:
        raise ValueError("spawn position needs a SceneDestination")
    if target.spawn is None:
        raise ValueError(
            f"scene {target.n_id} has no pinned spawn position - "
            "measure one before sending a player there"
        )
    return target.spawn


def login_teleport_fields(
    target: SceneDestination,
) -> tuple[int, int, float, float, float]:
    """The five arguments ``legacy.make_login_teleport`` takes, for one place.

    HOME IS RETURNED EXACTLY AS IT IS SENT TODAY.  ``runtime.py`` currently
    calls ``make_login_teleport(1, 0)``, i.e. scene 1 with a zero target, and
    that zero target is the shape every default boot in this project has been
    observed to survive.  This function reproduces it argument for argument, so
    wiring it in cannot change what a player who stays home receives - which is
    CHARTER-02's cumulative rule at the smallest scale there is.

    Only a destination that is NOT home carries a position, because only then
    is there something to carry: the client's teleport handler (0x5F14B0,
    documented at v141:2414) rejects the packet unless SceneID > 0, and every
    pinned destination satisfies that by construction.
    """
    scene_id, scene_seq = entry_fields(target)
    if target.n_id == HOME_SCENE_ID:
        return (scene_id, scene_seq, 0.0, 0.0, 0.0)
    x, y, z = spawn_position(target)
    return (scene_id, scene_seq, x, y, z)


def home_return_position(registry: SceneRegistry | None = None) -> Position:
    """The row that puts a character back in Port Royal - the way home.

    This exists because of one measured pair of facts about the test stage:
    its table row carries ``n_MARKER = 0`` (no authored arrival point) and
    ``n_SAVE = 0``, and no transition sequence is known (``RE-077``).  A
    character moved into such a scene has no in-game way back, and a build that
    takes away what the previous build could do is not a new version.  Whoever
    writes ``entry_position`` into a character row owns writing this one back.
    """
    home = destination(HOME_SCENE_ID, registry)
    scene_id, scene_seq = entry_fields(home)
    x, y, z = spawn_position(home)
    return Position(scene_id, scene_seq, x, y, z, 0.0)


def entry_position(target: SceneDestination, heading: float = 0.0) -> Position:
    """The persisted ``Position`` row that puts a character in this scene.

    NOTE: read ``home_return_position`` before calling this on any destination
    whose ``has_authored_entry`` is False.

    This is the flagless mechanism, and it already exists end to end: the
    character's stored position is what ``legacy_bridge.start_game`` reads for
    the entry frame's ``scene_id``, and ``store.update_position`` already
    accepts any scene id the wire field can hold.  Nothing new has to be
    invented for a player to WAKE UP somewhere other than Port Royal; the
    scene has to be in the row.  Moving a character who is already live is the
    other half, and it is not this function - see the module docstring.

    Heading defaults to 0, which is what the one measured non-home entry
    (SCENE-001, scene 2) used.  Whether the client applies an entry heading to
    the avatar or to the camera is unmeasured, so this does not pretend to
    choose one.
    """
    scene_id, scene_seq = entry_fields(target)
    x, y, z = spawn_position(target)
    if type(heading) not in (int, float):
        raise ValueError("heading must be a number")
    return Position(scene_id, scene_seq, x, y, z, float(heading))


def population_source(n_id: int) -> str | None:
    """Which population table is true for this scene - the census, or none.

    The bg0001 census of BUILD-001 is a table of bg0001 placements built with
    ``scene_id`` fixed at 1.  In any other scene those actors are dock NPCs
    delivered into the wrong map, so this answers ``None`` there, and a caller
    that populates on a non-None answer cannot make that mistake.
    """
    if _require_int(n_id, "scene n_ID", 1, 0xFFFF) == CENSUS_SCENE_ID:
        return CENSUS_SOURCE
    return None


def entry_report(target: SceneDestination) -> dict:
    """One flat dict for a console line or a ticket: where, and how well known.

    ``sent_before`` is in the report on purpose.  A destination this client has
    never been asked to load is a different kind of boot from one it has, and
    the person reading the console at 2am should not have to remember which is
    which.
    """
    scene_id, scene_seq = entry_fields(target)
    return {
        "scene_id": scene_id,
        "scene_seq": scene_seq,
        "model_id": target.model_id,
        "scene_name": target.scene_name_ascii,
        "image_name": target.image_name,
        "spawn": list(target.spawn) if target.spawn is not None else None,
        "spawn_provenance": target.spawn_provenance,
        "sent_before": target.sent_before,
        "population_source": population_source(scene_id),
        "native_placement_count": target.native_placement_count,
        "ground_z_spread": target.ground_z_spread,
        "save_flag": target.save_flag,
        "entry_marker": target.entry_marker,
        "camera_type": target.camera_type,
        "limit_height": target.limit_height,
        "needs_return_ticket": not target.has_authored_entry,
    }


def entry_console_line(target: SceneDestination) -> str:
    """The single ASCII line the boot should print before sending the player.

    The bridge console is cp874; this stays inside 7-bit ASCII deliberately.
    """
    report = entry_report(target)
    spawn = report["spawn"]
    where = (
        "spawn=none" if spawn is None
        else "spawn=({0:.3f},{1:.3f},{2:.3f})".format(*spawn)
    )
    return (
        "WORLD_SCENE scene_id={0} seq={1} model={2} name={3} {4} "
        "sent_before={5} population={6} save={7} marker={8} return_ticket={9}"
        .format(
            report["scene_id"], report["scene_seq"], report["model_id"],
            report["scene_name"].replace(" ", "_"), where,
            "yes" if report["sent_before"] else "NO",
            report["population_source"] or "none",
            report["save_flag"], report["entry_marker"],
            "REQUIRED" if report["needs_return_ticket"] else "not_needed",
        )
    )
