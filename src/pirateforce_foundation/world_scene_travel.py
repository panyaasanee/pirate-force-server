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
  ``docs/EXPERIMENT_LEDGER.md:32`` records SCENE-001 as a runtime PASS in
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

from . import world_scene_marker
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
PRISON_EXILE_SCENE_ID = 2
HELL_VOLCANO_SCENE_ID = 14
SLAVE_MARKET_SCENE_ID = 4
EVIL_PORT_SCENE_ID = 5
OCEAN_WALLED_CITY_SCENE_ID = 6
SILVER_HARBOUR_SCENE_ID = 8
DEEP_SEA_TEMPLE_SCENE_ID = 10
SPICE_PARADISE_SCENE_ID = 3
VOODOO_ISLAND_SCENE_ID = 7
MEASURED_SCENE_IDS = (1, 2)
CENSUS_SCENE_ID = SCENE_ID
CENSUS_SOURCE = "bg0001_census"
# GENERALIZED 2026-08-27 (PANYA-DECISION 20:10, M1-P) - the composer this
# module points at is now keyed by scene id, not a single hardcoded string.
# ``CENSUS_SCENE_ID``/``CENSUS_SOURCE`` above are UNCHANGED and stay exactly
# what they were (scene 1 -> "bg0001_census") so nothing that already reads
# them by name breaks; ``CENSUS_SOURCES`` is the new, wider table and
# ``population_source`` reads THIS one now.  "bg0002_roster" is
# ``world_population_bg0002.py``'s own name for itself, not invented here -
# see that module for the builder this string refers to, and its own
# docstring for what "roster" vs bg0001's "census" is meant to signal (every
# Bg0002 entry is already named; there is no named/nameless split to describe).
# WIDENED 2026-08-29 (round vyi2ud, LANE-A) with the third composer this lane
# has shipped: "bg0015_roster" is ``world_population_bg0015.py``'s own name for
# itself, on main since round 02k3w5, refusing every scene but 14 exactly the
# way the other two refuse everything but theirs.  What this line changes is a
# REPORT, not a dispatch: with scene 14 absent, the scene-entry console line
# printed ``population=none`` for a scene that has had a composed 81-actor
# roster in this repository for two rounds, and ``world_population_handoff``
# named its reason ``scene_14_has_no_population_table`` - both false at HEAD.
# Neither reads this table to decide what to SEND (the handoff still takes its
# CLEAR branch for every source but bg0001's, unchanged), so nothing here
# wires the roster to an arrival; that is the one line this lane cannot write
# for itself and the round's letter to chief asks for it by name.
# WIDENED 2026-08-30 (round 2jdde8, LANE-A) with the fourth composer this lane
# has shipped: "bg0004_roster" is ``world_population_bg0004.py``'s own name for
# itself (built, verified, NOT wired round 6p22bu; this round is the wiring
# half of that pair, same split bg0015's own history shows).  Scene 4's
# registry row still reads ``login_entry_allowed: false`` (COO-DECISION
# 2026-08-30T14:41+07:00 approving the crosswalk explicitly said not to flip
# it here) and no login/crossing path reaches scene 4 today, so this row is
# inert on ``main`` the same way scene 14's row was inert between its own
# build and open rounds: registered, refused by the admission check in
# ``lane_hooks/lane_a_scene_census.py``, never invoked in production.
# WIDENED 2026-08-31 (round c42axq, LANE-A) with the fifth composer this lane
# has shipped: "bg0010_roster" is ``world_population_bg0010.py``'s own name
# for itself (built, verified, NOT wired round u3jo4g; this round is the
# wiring half of that pair, same split bg0004's own history shows -- build
# u3jo4g, wire c42axq).  Scene 10's registry row still reads
# ``login_entry_allowed: false`` at that point (opened later the same round
# sequence, round 3t75jw), so this row was inert on ``main`` between those
# two rounds the same way scene 4's row was inert between its own build and
# open rounds: registered, refused by the admission check in
# ``lane_hooks/lane_a_scene_census.py``, never invoked in production.
# WIDENED 2026-08-31 (round l03cgh, LANE-A) with the sixth composer this
# lane has shipped: "bg0005_roster" is ``world_population_bg0005.py``'s own
# name for itself, the third door of the ten surveyed in round ``12lyda``
# (92 native placements, the highest of the eight still shut after scenes 4
# and 10 opened).  This round builds, wires AND -- after the same D1/D2/D3
# check every earlier door had -- opens scene 5's door in one pass; see
# ``scenarios/world_scene_registry_001.json``'s own
# ``login_entry_allowed_because`` on this row for that check.
# WIDENED 2026-08-31 (round fx0007, LANE-A) with the seventh composer this
# lane has shipped: "bg0006_roster" is ``world_population_bg0006.py``'s own
# name for itself, the fourth door of the ten surveyed in round ``12lyda``
# (80 native placements, the highest of the seven still shut after scenes 4,
# 5 and 10 opened).  Same compressed build+wire+open-in-one-pass shape round
# ``l03cgh`` set for scene 5; see ``scenarios/world_scene_registry_001.json``'s
# own ``login_entry_allowed_because`` on this row for the D1/D2/D3 check.
# WIDENED 2026-08-31 (round p4wire, LANE-A) with the eighth composer this
# lane has shipped: "bg0008_roster" is ``world_population_bg0008.py``'s own
# name for itself, the fifth door of the ten surveyed in round ``12lyda``
# (76 native placements, the highest of the six still shut after scenes 4,
# 5, 6 and 10 opened).  Same compressed build+wire+open-in-one-pass shape
# rounds ``l03cgh``/``fx0007`` set for scenes 5 and 6; see
# ``scenarios/world_scene_registry_001.json``'s own
# ``login_entry_allowed_because`` on this row for the D1/D2/D3 check.
# WIDENED 2026-08-31 (this round, LANE-A) with the ninth composer this
# lane has shipped: "bg0003_roster" is ``world_population_bg0003.py``'s own
# name for itself, the sixth door of the ten surveyed in round ``12lyda``
# (72 native placements, the highest of the five still shut after scenes 4,
# 5, 6, 8 and 10 opened).  Same compressed build+wire+open-in-one-pass shape
# rounds ``l03cgh``/``fx0007``/``p4wire`` set for scenes 5, 6 and 8; see
# ``scenarios/world_scene_registry_001.json``'s own
# ``login_entry_allowed_because`` on this row for the D1/D2/D3 check.
# WIDENED 2026-08-31 (round 78zayw, LANE-A) with the tenth composer this
# lane has shipped: "bg0007_roster" is ``world_population_bg0007.py``'s own
# name for itself, the seventh door of the ten surveyed in round ``12lyda``
# (68 native placements, the highest of the four still shut after scenes 4,
# 5, 6, 8, 10 and 3 opened).  Same compressed build+wire+open-in-one-pass
# shape rounds ``l03cgh``/``fx0007``/``p4wire``/``p7wm17`` set for scenes 5,
# 6, 8 and 3; see ``scenarios/world_scene_registry_001.json``'s own
# ``login_entry_allowed_because`` on this row for the D1/D2/D3 check.
CENSUS_SOURCES = {
    CENSUS_SCENE_ID: CENSUS_SOURCE,
    PRISON_EXILE_SCENE_ID: "bg0002_roster",
    HELL_VOLCANO_SCENE_ID: "bg0015_roster",
    SPICE_PARADISE_SCENE_ID: "bg0003_roster",
    VOODOO_ISLAND_SCENE_ID: "bg0007_roster",
    SLAVE_MARKET_SCENE_ID: "bg0004_roster",
    EVIL_PORT_SCENE_ID: "bg0005_roster",
    OCEAN_WALLED_CITY_SCENE_ID: "bg0006_roster",
    SILVER_HARBOUR_SCENE_ID: "bg0008_roster",
    DEEP_SEA_TEMPLE_SCENE_ID: "bg0010_roster",
}
CLIENT_REGISTERED_SCENE_COUNT = 271

_DESTINATION_FIELDS = {
    "n_id", "model_id", "scene_name_source_utf8_hex", "scene_name_ascii",
    "image_name", "native_placement_count", "native_definition_count",
    "native_sha256", "role", "status", "table_row", "spawn", "ground",
    # REQUIRED, not optional, and that is rule 3 of COO-DECISION
    # 20260829_0542 being enforced rather than trusted: every destination
    # states which MARKER row its coordinate came from, or states that it
    # came from something else.  A row added without it refuses to load,
    # which is the same fail-closed shape the rest of this loader uses -
    # the alternative is a coordinate whose evidence tier nobody can name.
    "coordinate_provenance",
}
# Optional per-destination blocks.  ``superseded_spawn`` is history kept in
# place rather than deleted; ``table_row_differences`` is commentary on the
# pinned columns and carries no value the code reads.  ``login_entry_allowed``
# and ``persist_position_allowed`` are the odd ones out - they ARE read - see
# their own comments below (DEFAULT_LOGIN_ENTRY_ALLOWED and
# DEFAULT_PERSIST_POSITION_ALLOWED respectively).
_DESTINATION_OPTIONAL_FIELDS = {
    "superseded_spawn", "table_row_differences", "login_entry_allowed",
    "persist_position_allowed",
}
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
    # The arrival-point rule the COO made standing on 2026-08-29 (0542):
    # which scenes may take a MARKER point, that the read must go through
    # SCENE_NAME[n].n_MARKER and never index MARKER by scene id, and that
    # the resulting evidence tier is "authored" until an attended round
    # says otherwise.  Text rather than switches - what enforces it is
    # world_scene_marker.py plus the required field below.
    "arrival_point_rule",
}
# The shape of that per-row provenance.  Validated like every other block
# here so a row cannot carry half of it.
#
# ``deviates_from_rule_1`` was added after pf-adversary (round 8ubiku, D2)
# showed the first version was a self-report: it decided whether rule 3
# applied to a row by reading a boolean THAT ROW set about itself, so
# flipping ``from_marker`` to false moved a marker-sourced coordinate out of
# the rule entirely, with its spawn still byte-identical to MARKER[14] and
# every test green.  A row cannot vote itself out of the rule any more - the
# authority is ``table_row.n_MARKER``, which comes from the client's table
# and is already sitting in the same row.
_COORDINATE_PROVENANCE_FIELDS = {
    "source", "from_marker", "marker_n_id", "evidence_tier", "note",
    "deviates_from_rule_1",
}
# The tiers this project recognises.  An open string field would let a round
# invent "verified" or "confirmed-ish" and mean nothing by it.
_EVIDENCE_TIERS = {
    "client-observed",      # a client was stood on this point and seen
    "authored",             # the map's developers wrote the coordinate down
    "decreed_provisional",  # the owner named it, under an expiry
    "chosen_no_evidence",   # picked because the scene offered nothing
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
    # True for every destination this project pinned before round 0z3kjx, and
    # for any destination the registry does not mention this field on at all
    # (see DEFAULT_LOGIN_ENTRY_ALLOWED below).  False marks a destination that
    # a character's own persisted row must never be allowed to open by
    # itself - see the comment above DEFAULT_LOGIN_ENTRY_ALLOWED for why this
    # exists and world_scene_entry.resolve_entry's ``via_login`` for who
    # checks it.  This is a login-time POLICY, not a fact about the scene
    # itself (unlike everything above it, which is read off the client's own
    # tables), so it lives here rather than inside table_row.
    login_entry_allowed: bool = True
    # True for every destination this project pinned before round jafskv, and
    # for any destination the registry does not mention this field on at all
    # (see DEFAULT_PERSIST_POSITION_ALLOWED below).  False marks a destination
    # whose XYZ this project has not yet decided how to write into
    # ``character_positions`` at all - see the comment above
    # DEFAULT_PERSIST_POSITION_ALLOWED for the bug this closes and
    # ``is_position_persist_allowed`` for who is meant to check it.  Like
    # ``login_entry_allowed`` this is a WRITE-TIME POLICY, not a fact read off
    # the client's own tables, so it lives here rather than inside table_row.
    persist_position_allowed: bool = True

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


def _require_bool(value: Any, label: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{label} must be true or false")
    return value


PROVISIONAL_SPAWN_PROVENANCE_PREFIX = "PROVISIONAL-OWNER-DECREE"

# ``login_entry_allowed`` distinguishes "usable as a destination a
# script/dispatch path can resolve on purpose" from "usable as the
# destination a character's OWN PERSISTED ROW can name at login".  Round
# 0z3kjx's adversary pass found the gap this closes: scene 17's spawn stopped
# being null the moment the owner's decree landed, and
# world_scene_entry.resolve_entry is the SAME call runtime.py's login path
# makes with whatever scene_id happens to be sitting in the character's DB
# row - nothing stops that row from naming 17 (no CHECK constraint,
# migrations/001_initial.sql:5), and nothing before this flag existed would
# have refused it once the spawn stopped being None (the free
# REFUSED_NO_PINNED_SPAWN refusal that used to protect it was gone). Absent
# from a pin, this defaults True and every pre-existing destination (1, 2,
# 278, 997) is unaffected byte for byte. False is reserved for a destination
# whose only sanctioned entry door is a specific, code-reviewed dispatch
# path that resolves it on purpose (today: columbus_quest_dispatch.
# resolve_columbus_arrival, via resolve_entry's own via_login=False) - not a
# door a stored row can open by accident.
DEFAULT_LOGIN_ENTRY_ALLOWED = True

# ``persist_position_allowed`` distinguishes "safe to write this character's
# CURRENT scene id and XYZ into character_positions" from "not yet, this
# scene's write shape is still an open question".  GT-106 (attended session
# kha1-B, 2026-08-27 16:35-16:46, notes_to_chief/20260827_1710_GT106-RESULT-
# M2-Columbus-3021-enters-scene17-*) found the gap this closes: a character
# walked into scene 17 (the Columbus M2 dispatch, op1/3021, landing on the
# PROVISIONAL-OWNER-DECREE spawn) and, after teardown, its character_positions
# row read
# scene_id=1 with the scene-17 XYZ (x=-149.0, y=-1250.3, z=745.0) stapled onto
# it - not scene 17 (nobody chose that number on purpose either) and not the
# Port Royal position the character actually departed from.  That row is
# wrong twice over: scene 1 is the wrong scene, and (-149, -1250, 745) is not
# a position anybody measured as valid ground for scene 1.
#
# WHY THE FIX PINNED HERE IS "DO NOT PERSIST", NOT "PERSIST 17 INSTEAD".  The
# obvious-looking correction - write scene_id=17 with that XYZ - drives
# straight into the trap round 0z3kjx built ``login_entry_allowed`` to catch:
# scene 17 is pinned ``login_entry_allowed: false`` precisely because a
# character's own persisted row naming 17 is refused at the next login
# (``world_scene_entry.resolve_entry``, ``REFUSED_NOT_ALLOWED_AT_LOGIN``) -
# and scene 17 has no known way back in-game (``n_MARKER=0``, RE-077 open,
# ``return_ticket=REQUIRED`` on GT-106's own console line). Writing scene_id=17
# today would not fix the wrong row, it would turn "wrong row" into "player
# locked out of their character at next login". Refusing to persist at all
# is the smaller, reversible failure: the character keeps whatever position it
# last held in a scene that IS safe to log back into, and the next login lands
# there exactly as it does today - CHARTER-02's cumulative rule again, at the
# write path this time instead of the read path.
#
# Absent from a pin, this defaults True and every pre-existing destination (1,
# 2, 278, 997) is unaffected byte for byte - this project has never observed a
# persistence problem at any of them, so none of them earns the exception.
# False is reserved for a destination this project has caught in the act of
# corrupting its own character_positions row, until a wiring round (see
# ``is_position_persist_allowed`` below) decides what SHOULD be written there
# instead of nothing.
DEFAULT_PERSIST_POSITION_ALLOWED = True


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
        provenance_block = row["coordinate_provenance"]
        if (
            type(provenance_block) is not dict
            or set(provenance_block) != _COORDINATE_PROVENANCE_FIELDS
        ):
            raise ValueError(
                f"scene {n_id} coordinate_provenance is incomplete or has "
                "unknown fields")
        from_marker = _require_bool(
            provenance_block["from_marker"], f"scene {n_id} from_marker")
        deviates = _require_bool(
            provenance_block["deviates_from_rule_1"],
            f"scene {n_id} deviates_from_rule_1")
        marker_n_id = provenance_block["marker_n_id"]
        if provenance_block["evidence_tier"] not in _EVIDENCE_TIERS:
            raise ValueError(
                f"scene {n_id} evidence tier "
                f"{provenance_block['evidence_tier']!r} is not one this "
                "project recognises")
        # The two halves have to agree, or the field records a decision
        # nobody made: a row that claims a marker must name which one, and a
        # row that claims none must not carry an id that a later reader
        # would treat as one.
        if from_marker:
            _require_int(marker_n_id, f"scene {n_id} marker n_ID", 1, 0xFFFF)
        elif marker_n_id is not None:
            raise ValueError(
                f"scene {n_id} says its coordinate is not from a marker but "
                "names one anyway")
        table_row = row["table_row"]
        if type(table_row) is not dict or set(table_row) != _TABLE_ROW_FIELDS:
            raise ValueError(
                f"scene {n_id} table row is incomplete or has unknown fields")
        for column, value in table_row.items():
            _require_int(value, f"scene {n_id} {column}", 0, 0xFFFFFFFF)
        spawn, spawn_provenance = _spawn(row["spawn"], ground, n_id)
        # THE AUTHORITY IS THE CLIENT'S TABLE, NOT THE ROW'S OPINION OF
        # ITSELF.  n_MARKER came from CONSTDATA_TH__SCENE_NAME and is already
        # validated above, so it - not from_marker - decides whether rule 1
        # reaches this scene (COO-DECISION 20260829_0542; the self-report
        # hole is pf-adversary round 8ubiku D2/D3).
        entry_marker = table_row["n_MARKER"]
        if from_marker:
            if entry_marker == 0:
                raise ValueError(
                    f"scene {n_id} claims a marker coordinate, but its own "
                    "table row carries n_MARKER 0")
            if marker_n_id != entry_marker:
                raise ValueError(
                    f"scene {n_id} names marker {marker_n_id} but its table "
                    f"row names {entry_marker}")
            # And the coordinate itself has to BE that marker's point.  This
            # is the check that stops a provenance field from being edited in
            # the same commit as the coordinate it describes: the pinned
            # marker rows are the second opinion, and they came from the
            # client's table rather than from this file.
            pinned = world_scene_marker.arrival_point(n_id)
            if pinned is None or pinned.marker_n_id != marker_n_id:
                raise ValueError(
                    f"scene {n_id} claims marker {marker_n_id}, which the "
                    "pinned marker crosswalk does not confirm")
            if spawn != pinned.xyz:
                raise ValueError(
                    f"scene {n_id} says its spawn came from marker "
                    f"{marker_n_id} but does not stand on that marker's "
                    "point")
            if deviates:
                raise ValueError(
                    f"scene {n_id} both takes its marker and claims to "
                    "deviate from the rule that says to")
        # THE TABLE ROW IS ALSO HAND-TYPED, AND ROUND 8ubiku CALLED IT "the
        # client's table" AS THOUGH IT WERE NOT (pf-adversary, round 8ubiku2,
        # E3).  n_MARKER is validated for shape and compared to nothing, so
        # the previous version moved the self-report rather than removing it:
        # setting scene 14's table_row.n_MARKER to 0 walked it straight out
        # of rule 1 with the spawn still sitting on MARKER[14].  The pinned
        # crosswalk is the one copy of this fact that a bridge round
        # re-derives, so it gets a vote here.
        pinned_for_scene = world_scene_marker.arrival_point(n_id)
        if pinned_for_scene is not None and entry_marker != pinned_for_scene.marker_n_id:
            raise ValueError(
                f"scene {n_id} table row says n_MARKER {entry_marker}, but "
                f"the pinned crosswalk says this scene names marker "
                f"{pinned_for_scene.marker_n_id}")
        if deviates and pinned_for_scene is not None and spawn == pinned_for_scene.xyz:
            # A declared deviation that stands exactly on the marker it says
            # it is deviating from is a label, not a deviation.
            raise ValueError(
                f"scene {n_id} declares a deviation from rule 1 but stands on "
                "the marker point it claims to deviate from")
        if not from_marker and entry_marker != 0 and not deviates:
            # A scene that HAS an authored arrival point and declines to use
            # it is exactly what rule 1 forbids by default.  It stays
            # possible - scene 1's home spawn is the live example - but only
            # as a LABELLED deviation that a reader can grep for, never as a
            # quiet false flag.
            raise ValueError(
                f"scene {n_id} has marker {entry_marker} but does not use it "
                "and does not declare a deviation from rule 1")
        elif entry_marker == 0 and deviates:
            raise ValueError(
                f"scene {n_id} declares a deviation from rule 1, which does "
                "not reach a scene whose n_MARKER is 0")
        login_entry_allowed = (
            _require_bool(
                row["login_entry_allowed"], f"scene {n_id} login_entry_allowed")
            if "login_entry_allowed" in row
            else DEFAULT_LOGIN_ENTRY_ALLOWED
        )
        persist_position_allowed = (
            _require_bool(
                row["persist_position_allowed"],
                f"scene {n_id} persist_position_allowed")
            if "persist_position_allowed" in row
            else DEFAULT_PERSIST_POSITION_ALLOWED
        )
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
            login_entry_allowed=login_entry_allowed,
            persist_position_allowed=persist_position_allowed,
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
    """Which population table is true for this scene - a named source, or none.

    Reads :data:`CENSUS_SOURCES`, which is keyed by scene id.  The bg0001
    census of BUILD-001 is a table of bg0001 placements built with
    ``scene_id`` fixed at 1; the Bg0002 roster of M1-P (PANYA-DECISION
    2026-08-27 20:10) is a separate table built with ``scene_id`` fixed at 2.
    Each builder refuses any OTHER scene id itself - see
    ``world_population.build_world_population`` and
    ``world_population_bg0002.build_bg0002_population`` - so this function is
    a report, same as it always was; the refusal that actually prevents
    cross-scene delivery lives in the builders.  A scene this table does not
    name answers ``None``, and a caller that populates on a non-None answer
    cannot deliver the wrong scene's actors into a scene this table has no
    entry for.
    """
    return CENSUS_SOURCES.get(_require_int(n_id, "scene n_ID", 1, 0xFFFF))


def is_position_persist_allowed(
    n_id: int,
    registry: SceneRegistry | None = None,
) -> bool:
    """Whether a character's CURRENT scene id and XYZ may be written back into
    ``character_positions`` for this scene - not whether the scene is
    addressable, and not whether logging IN to it is allowed.

    GT-106 is why this function exists: a character who walked into scene 17
    came out of teardown with a ``character_positions`` row reading
    ``scene_id=1`` carrying scene 17's XYZ - a row nobody chose, wrong on both
    columns, and unsafe for the next login (see
    ``DEFAULT_PERSIST_POSITION_ALLOWED``'s comment for the full incident and
    why the fix is "do not write", not "write 17 instead"). This is the
    question a write-time caller is meant to ask before it touches that table
    at all; ``login_entry_allowed``/``resolve_entry``'s ``via_login`` is the
    matching question for reads, and the two are deliberately separate checks
    because a scene can fail either one without failing the other.

    FAIL-OPEN FOR A SCENE THIS REGISTRY DOES NOT PIN AT ALL - AND ONLY FOR
    THAT CASE.  This is the opposite default from ``login_entry_allowed``
    (fail-closed: ``resolve_entry`` raises before a stored row can even reach
    this question) and from ``spawn_position`` (refuses rather than inventing
    a position). Both of those exist because an UNKNOWN destination is an
    UNTRUSTED one - a stored row naming a scene nobody measured is exactly
    the shape of bug this project keeps finding. This function's unknown case
    is different: every destination this bug has ever been observed at is
    already pinned (today: only 17), and every scene NOT in this registry is,
    by definition, a scene this project has never routed a character through
    on purpose - which means it is also a scene this exact persistence bug has
    never had the chance to touch. Fail-closed here would not protect against
    a known trap; it would silently stop writing positions for every scene
    this project adds next, on the strength of a bug none of them has
    exhibited. So: known-and-broken (a pinned False) refuses, unknown (not
    pinned at all, or the field simply absent from a pinned row) defaults to
    True - the same "nothing changes for a scene that was never part of the
    incident" contract ``DEFAULT_LOGIN_ENTRY_ALLOWED`` makes, applied to a
    default that points the other way for a different reason.

    Still validates ``n_id`` itself (type and the wire field's 1..0xFFFF
    range) rather than fail-opening on a garbage argument - a caller that
    passes a value the scene field could never carry has a bug of its own,
    which this function should say loudly rather than paper over.
    """
    _require_int(n_id, "scene n_ID", 1, 0xFFFF)
    reg = registry or load_scene_registry()
    try:
        target = reg[n_id]
    except KeyError:
        return True
    return target.persist_position_allowed


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
