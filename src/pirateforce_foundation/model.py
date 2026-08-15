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
