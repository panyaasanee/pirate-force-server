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

    # The three login vitals this character's login sends, or None each for
    # "the composer's own constants" (`player_wire.PLAYER_LOGIN_LEVEL` and
    # `PLAYER_LOGIN_HP_CURRENT`/`_HP_MAX`).  COO-DECISION 20260903_0647.
    #
    # THEY RIDE THE CHARACTER for exactly the reason the walk speed above
    # does, and the reason is not style: `legacy_bridge.start_game` is called
    # up to three more times per production login by `runtime.py` (the
    # faction probe on every flagless login, the scene-override resync, the
    # pinned-identity probe), each with the SAME selected character, so a
    # number threaded into the first call only is a number the very next
    # recompose silently puts back to the constant -- green in a unit test,
    # absent on the wire.
    #
    # ALL THREE OR NONE (PANYA-DECISION 20260901_1059): `start_game` sends
    # them only when all three are set, so no login can ever carry the row's
    # `hp_current` beside a guessed `level`.  `store._character` does not read
    # them, so a character loaded from the database arrives here with three
    # `None`s and composes exactly what `main` composes today; `session.py`
    # is the only place that fills them in, through the login-vitals seam
    # there.  THE MODULE THAT SEAM CALLS IS NAMED IN WORDS RATHER THAN
    # SPELLED, and that is not squeamishness: its own test file walks every
    # `.py` under the repository root and fails any module outside
    # `session.py` whose TEXT contains the name, COMMENTS INCLUDED, because
    # that is how "one call point, no second one" (`COO-DECISION
    # 20260903_0447`) is enforced without trusting an import list.  Measured:
    # the first draft of this paragraph turned that guard red.
    level: int | None = None
    hp_current: int | None = None
    hp_max: int | None = None

    # The class the player picked at character creation, read off the row's
    # `class_id` typed column, or None for "the composer's own constant"
    # (`player_wire.PLAYER_LOGIN_CLASS_ID`).  CORE-REQUEST of
    # `pf_bridge/notes_to_chief/20260904_0423`, granted by `COO-DECISION
    # 20260904_0446` point 3.
    #
    # IT RIDES THE CHARACTER for the same measured reason the speed and the
    # three vitals above do, and it is the only shape that survives:
    # `legacy_bridge.start_game` is called up to three more times per
    # production login by `runtime.py` (the faction probe on every flagless
    # login, the scene-override resync, the pinned-identity probe), each with
    # the SAME selected character object.  A class id threaded as an argument
    # into the login call only is a class id the very next recompose puts
    # back to 1 -- green in a unit test, gone from the frame the client keeps.
    #
    # `store._character` does not read it (that method is LANE-DB's), so a
    # character loaded straight from the database arrives here as None and
    # composes exactly what `main` composes today; `session.py` is the only
    # place that fills it in, from the row's typed attributes.
    class_id: int | None = None
