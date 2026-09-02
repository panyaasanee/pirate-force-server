from dataclasses import dataclass

@dataclass(frozen=True)
class Position:
    scene_id: int
    scene_seq: int
    x: float
    y: float
    z: float
    heading: float = 0.0

@dataclass(frozen=True)
class Character:
    id: int
    account_id: int
    selector: int
    name: str
    actor_wire: bytes
    avatar_wire: bytes
    identity_lo: int
    identity_hi: int
    position: Position
    # The movement speed this character's login sends, or None for "the
    # composer's own constant".  CORE-REQUEST `pf_bridge/notes_to_chief/
    # 20260902_2010` (COO-DECISION 20260902_1846 point 3): the value has to
    # RIDE THE CHARACTER rather than be threaded through each call, because
    # `start_game` is called four more times per login than the login itself
    # -- runtime.py recomposes the frame for the faction probe on every
    # flagless production login, and again for a scene override -- and a
    # value threaded into only the first of those is a value the recompose
    # silently puts back to the constant.  `session.py` is the only place
    # that fills it in, from `login_speed.resolve_for_character`; the store
    # does not read it (`store._character` is LANE-DB's, and its charter,
    # COO-DECISION 20260901_1100, does not let this lane change an existing
    # method there), so a character loaded from the database arrives here
    # with None and behaves exactly as main behaves today.
    movement_speed: float | None = None
