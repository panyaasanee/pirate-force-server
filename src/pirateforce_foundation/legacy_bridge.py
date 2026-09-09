"""Projection seam into frozen V141 serializers; no gameplay behavior is changed."""
import importlib.util
import math
import struct
import sys
from pathlib import Path

from .inventory import make_backpack_attr
from .persistence_scene_field_patch import project_actor_wire_for_list
from .player_wire import (
    make_actor_attr_with_name_and_class,
    make_actor_attr_with_name_class_and_faction,
)

def load_legacy(path: str | Path):
    spec = importlib.util.spec_from_file_location("pf_legacy_v141", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module

# The largest magnitude `struct.pack("<f", ...)` will encode.  Anything above it
# raises OverflowError out of `f32tag`, which is NOT a caution threshold: it is
# what the four bytes on the wire can physically carry, so it is one of the
# refusals HOUSE_RULES 2220 item 5 still allows -- and it gets a name and a
# printed line, never a silent trim.
F32_MAX_MAGNITUDE = 3.4028234663852886e38

class WirePositionOutOfRange(ValueError):
    """A stored position this seam cannot encode as float32.

    A ValueError ON PURPOSE.  The production login path in runtime.py wraps
    `select_and_start` in `except (ValueError, RuntimeError)` and answers with a
    printed, named refusal (the BACKPACK_LOAD_REFUSED handler is the precedent,
    same call site).  Raising anything outside that tuple -- OverflowError, which
    is what happens today -- unwinds the listener thread instead.
    """

def refuse_unencodable_position(p, where, character=None):
    """Refuse a position the float32 wire cannot carry, BEFORE any tag is built.

    [CORE-REQUEST LANE-A 20260909_1519, `pf_bridge/notes_to_chief/
    20260909_1519_LANE-A-CORE-REQUEST-move-the-float32-guard-upstream-of-select-
    and-start.md`; chief round qnys56]

    MEASURED on main this round, not argued: `f32tag(3.5e38)` raises
    `OverflowError: float too large to pack with f format`, `grep -n "except"
    runtime.py` has no OverflowError anywhere near the `select_and_start` call
    site (~10483), and both seams below read `character.position` RAW.  So one
    persisted row with a coordinate past float32 killed the listener thread on
    every login of that character -- and the thread is shared, so the row took
    the connection down with it rather than only that one login.

    LANE-A's own `_row_is_finite`/`_wire_refusal` guard sits in
    `world_scene_entry.resolve_entry`, which the login path reaches ~10846/~10929
    -- AFTER `select_and_start` has already composed this frame.  Their request
    was to move the guard upstream; this is upstream, at the one place both
    projections read the position, so neither seam can be reached around.

    Nonclaims: this refuses only what the WIRE cannot encode.  It does NOT judge
    whether a coordinate is a sensible place to stand (that is world's question,
    not this seam's), and it deliberately leaves inf/NaN alone -- `f32tag` encodes
    both today without raising, so refusing them here would be this seam changing
    behaviour it was not asked to change, on rows LANE-A's own finite guard owns.
    """
    for name in ("x", "y", "z", "heading"):
        v = getattr(p, name, None)
        if v is None:
            continue
        try:
            f = float(v)
            # `math.isfinite` FIRST, and it is not an oversight that inf/NaN fall
            # through: `f32tag` encodes both today without raising, so they are
            # not part of the OverflowError hole this guard was asked to close,
            # and refusing them here would silently take over the finite question
            # that world_scene_entry's own row guard owns (LANE-A, and their
            # 20260909_1518 ASK-COO about who owns arrival is still open).
            if math.isfinite(f) and abs(f) > F32_MAX_MAGNITUDE:
                who = getattr(character, "character_id", None)
                raise WirePositionOutOfRange(
                    "WIRE_POSITION_OUTSIDE_FLOAT32 %s.%s=%r character_id=%r "
                    "-- the stored row cannot be encoded as float32; refusing the "
                    "frame instead of unwinding the listener thread" % (where, name, v, who))
        except (TypeError, ValueError) as exc:
            if isinstance(exc, WirePositionOutOfRange):
                raise
            # A field that is not a number at all is the same class of problem
            # and reaches `struct.pack` the same way; name it rather than let it
            # surface as a TypeError from four frames deeper.
            raise WirePositionOutOfRange(
                "WIRE_POSITION_NOT_A_NUMBER %s.%s=%r -- refusing the frame" % (where, name, v))
    return p

class LegacyProjector:
    def __init__(self, legacy):
        self.v = legacy

    def character_list(self, characters):
        # `project_actor_wire_for_list` patches the select-screen scene
        # field named by `persistence_scene_field_patch.SCENE_FIELD`
        # (`FIELD_A`, per RE-248's static IMAGE trace -- `GT-245` is the
        # client-observable proof, not yet run) with `c.position.scene_id`
        # so the frame shows the character's CURRENT scene instead of her
        # frozen BIRTH one (`COO-DECISION 20260904_2152` item 4;
        # `tests/test_persistence_scene_field_patch.py`).
        payload = (self.v.u8tag(0x0B,0)+self.v.u32tag(0x14,0)+self.v.u32tag(0x14,0)+
                   self.v.u32tag(0x1F,0)+self.v.u8tag(0x0B,0)+self.v.u8tag(0x0B,len(characters))+
                   b"".join(project_actor_wire_for_list(c) for c in characters)+self.v.u8tag(0x0B,0)+self.v.u8tag(0x0B,0))
        return self.v.make_runtime_vital(self.v.SELECT_ACTOR_VITAL, 10, payload)

    def create_success(self, character):
        return self.v.make_runtime_create_actor_success(character.actor_wire)

    def movement_attr(self, character, position=None):
        """Project the persisted position without changing the frozen zero-heading wire."""
        p = position or character.position
        refuse_unencodable_position(p, "movement_attr", character)
        return (
            self.v.u8tag(0x0B, 1)
            + bytes([0x32])
            + struct.pack("<II", character.identity_lo & 0xFFFFFFFF,
                          character.identity_hi & 0xFFFFFFFF)
            + self.v.u8tag(0x0B, 0xFF)
            + self.v.f32tag(p.x) + self.v.f32tag(p.y) + self.v.f32tag(p.z)
            + self.v.f32tag(p.heading)
            + self.v.u8tag(0x0B, 0)
            + self.v.u32tag(0x26, 0)
            + self.v.f32tag(0.0) * 3
        )

    def start_game(self, character, position=None, basic_faction=None, backpack=None):
        # PF-HYPOTHESIS-LEDGER: HYP-PF-001 frozen
        # PF-HYPOTHESIS-LEDGER: HYP-PF-007 frozen
        # PF-HYPOTHESIS-LEDGER: GEO-PF-002 frozen
        # PF-HYPOTHESIS-LEDGER: GEO-PF-003 frozen
        p = position or character.position
        refuse_unencodable_position(p, "start_game", character)
        # CORE-REQUEST-022: every StartGame this seam composes carries
        # class+level now (player_wire.make_actor_attr_with_name_and_class /
        # _class_and_faction docstrings) -- both callers of this seam that
        # pass basic_faction (runtime.py's flagless production recompose and
        # its scenario-gated HYP-PF-027 pinned-identity probe) build a
        # second frame from the SAME selected character and diff its length
        # against this one; keeping both branches on the class+level
        # baseline is what keeps that diff at its original 5 bytes.  The
        # frozen, class-less make_actor_attr_with_name/_with_basic_faction
        # stay defined in player_wire.py as the pinned reference other
        # lanes' own offline tests compare against directly, just no longer
        # called from this seam.
        # CORE-REQUEST `pf_bridge/notes_to_chief/20260902_2010` (COO-DECISION
        # 20260902_1846 point 3): the speed is read OFF THE CHARACTER, not
        # threaded in as an argument, and that is the whole reason this seam
        # needed no new parameter.  This projector is a SINGLETON -- app.py
        # builds exactly one and hands it to every connection's state class
        # -- so a per-login value parked on `self` would be one player's speed
        # leaking into the next player's frame.  Riding the character instead
        # also means the three `start_game` recomposes in runtime.py (the
        # faction probe on every flagless production login, the scene-override
        # resync, and the pinned-identity probe) compose the SAME speed as the
        # login did without one line of change at any of them: they all pass
        # `self.foundation.selected`, which is the object session.py resolved.
        # `None` (a character straight out of the store) keeps the constant.
        speed = getattr(character, "movement_speed", None)
        # THE VITALS RIDE THE CHARACTER TOO, and ALL THREE OR NONE
        # (PANYA-DECISION 20260901_1059, COO-DECISION 20260903_0647).  One
        # `None` among them -- a character straight out of the store, another
        # lane's stub, a model that never grew the fields -- makes `vitals`
        # empty, and an empty splat is byte-for-byte the frame `main` sends
        # today.  There is deliberately no branch that fills a missing one in
        # from a constant: that is the "unknown field guessed as a number"
        # shape the owner's letter forbids, and it would put a guessed level
        # beside a real hp on the same wire.
        level = getattr(character, "level", None)
        hp_current = getattr(character, "hp_current", None)
        hp_max = getattr(character, "hp_max", None)
        vitals = {}
        if level is not None and hp_current is not None and hp_max is not None:
            vitals = {
                "level": level, "hp_current": hp_current, "hp_max": hp_max,
            }
        # THE CLASS RIDES THE CHARACTER TOO (CORE-REQUEST of `pf_bridge/
        # notes_to_chief/20260904_0423` point 2.2, `COO-DECISION 20260904_0446`
        # point 3).  `None` -- a character straight out of the store, a row
        # created before the class seam existed, another lane's stub -- means
        # the empty splat, and an empty splat is byte-for-byte the frame
        # `main` sends today, because the composer's signature default
        # `player_wire.PLAYER_LOGIN_CLASS_ID` then stands.  The frame's LENGTH
        # is the same either way: the field is `u32tag(0x19, class_id)`, fixed
        # width for every value, which is what the recompose length guards in
        # `runtime.py` depend on.
        #
        # THIS IS NOT AN ALL-OR-NONE PAIR with the vitals above and must not
        # become one: `PANYA-DECISION 20260901_1059` forbids sending a guessed
        # number beside a measured one, and this number is never guessed -- it
        # is either read off the row's own column or not sent at all.  A
        # character whose vitals are unreadable but whose class is known still
        # logs in as her class.
        class_kwargs = {}
        class_id = getattr(character, "class_id", None)
        if class_id is not None:
            class_kwargs = {"class_id": class_id}
        actor = (
            make_actor_attr_with_name_and_class(
                self.v, character.identity_lo, character.identity_hi,
                p.scene_id, p.scene_seq, character.name,
                movement_speed=speed, **class_kwargs, **vitals,
            )
            if basic_faction is None else
            make_actor_attr_with_name_class_and_faction(
                self.v, character.identity_lo, character.identity_hi,
                p.scene_id, p.scene_seq, character.name, basic_faction,
                movement_speed=speed, **class_kwargs, **vitals,
            )
        )
        avatar = character.avatar_wire
        movement = self.movement_attr(character, p)
        backpack_wire = (
            self.v.make_backpack_attr_four_items()
            if backpack is None else make_backpack_attr(self.v, backpack)
        )
        payload = (self.v.u8tag(0x08,character.selector)+self.v.u8tag(0x05,0)+self.v.u8tag(0x0B,2)+
                   self.v.u16tag(0x0F,3)+self.v.u16tag(0x0F,0)+self.v.u8tag(0x0B,4)+
                   self.v.u16tag(0x12,0x12AD)+actor+self.v.u16tag(0x12,0x16A0)+avatar+
                   self.v.u16tag(0x12,0x2067)+movement+self.v.u16tag(0x12,self.v.BACKPACK_ATTR)+
                   backpack_wire+self.v.u8tag(0x0B,0))
        return self.v.make_login_vital(self.v.START_GAME_RES, 3, payload)
