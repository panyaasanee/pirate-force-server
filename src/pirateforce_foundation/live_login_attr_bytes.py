"""The value the ORDINARY LOGIN PATH sends today, for one character, for
every ``attr_wire.unnamed_field_x()`` row login actually touches.

CORE-REQUEST-GM's ``LOGIN_BYTES_READ_POINT`` (``attr_wire.py`` line ~1091,
ordered by ``COO-DECISION 20260904_0216``): the second half of "(b'')"
(see ``gm/attr_wire.py``'s module docstring). A ``known=False`` row may not
go out unset -- an unset mask bit is a ZERO on the client (``RE-222``), the
exact mechanism ``GT-218`` priced -- so every unnamed row a live send wants
must carry SOME byte, and the only byte this house has ever measured a real
client surviving for a row it has no name for is whatever the login path
already sends this character every single day.  This module is that
source; the point lanes actually call is
``lane_hooks.current_login_attr_bytes``, which holds nothing but a
registration slot -- same split as ``live_named_attr_values.py`` /
``lane_hooks.current_named_attr_values``.

WHAT THIS MODULE CAN AND CANNOT ANSWER, measured (not guessed) by tracing
the real login composer end to end: ``runtime.py``'s ``START_GAME_REQ``
handler -> ``session.py``'s ``select_and_start`` -> ``legacy_bridge.py``'s
``LegacyProjector.start_game`` -> ``player_wire.py``'s
``_make_actor_attr_with_name_and_class`` (the one function every login-
adjacent call site in this repository reaches through, per
``player_wire.make_actor_attr_with_name_and_class`` /
``make_actor_attr_with_name_class_and_faction``).

``login_mask.login_field_x(legacy)`` (derived by parsing the REAL bytes
that composer emits, not by reading a comment) intersects
``attr_wire.unnamed_field_x()`` in EXACTLY TWO rows:

  * x=7 ``basic_f32_54`` (movement speed) -- ``login_speed.
    resolve_for_character(store, character_id, fallback=player_wire.
    PLAYER_LOGIN_MOVEMENT_SPEED)``, the same per-character resolver the
    login composer itself calls (``session.py:242-246``).  Never fails a
    login (that function's own docstring): the worst case is the fallback
    constant, which is exactly what an unreadable row means to the login
    path too.
  * x=10 ``basic_q60`` -- the character's ``position.scene_seq`` column
    (``store.get_character(character_id).position.scene_seq``), the same
    row the login composer reads through ``legacy_bridge.py``.

EVERY OTHER UNNAMED ROW HAS NO LOGIN-TIME SOURCE AT ALL, and this is a
structural fact about the composer, not a gap in this module's search: the
login composer's mask never sets those bits, so there is no literal
anywhere in this repository to mirror.  This module does not invent one.
``gm.attr_wire.live_login_bytes`` already refuses the whole send when a
wanted row is absent (``missing_login_rows: ...``) -- that refusal is
correct and this module does not try to silence it, only to shrink the
list of rows it names as missing from 28 to 26, the same shape
``live_named_attr_values.py`` already shrank its own list.

NEVER RAISES, same contract as ``live_named_attr_values.values_for``: an
unknown character, a store that has not migrated, or a database error is
"this row is not answerable", which becomes an absent key here and a named
per-row refusal one layer up in ``attr_wire``.  Never silent either: every
swallow names itself on ``stream`` (default stderr), ASCII only -- the
bridge console is cp874.
"""
from __future__ import annotations

import sys
from typing import Any, Callable

#: The one token a console grep can look for when this module answers less
#: than it should.  ASCII, and it never carries a character's data.
READ_REFUSED_CONSOLE_TOKEN = "LIVE_LOGIN_ATTR_READ_REFUSED"

#: Which failure kinds have already been announced in this process.
#: Bounded on purpose, same reasoning as ``live_named_attr_values._ANNOUNCED``.
_ANNOUNCED: set = set()


def reset_console_announcements() -> None:
    """Forget what has been announced.  For tests, which share a process."""
    _ANNOUNCED.clear()


def _say(stream, kind: str, text: str) -> None:
    """One ASCII line about a swallowed failure, once per kind per process.

    Never raises, same reason as ``live_named_attr_values._say``: a module
    that exists to keep a listener thread alive may not die reporting that
    it nearly did.
    """
    if kind in _ANNOUNCED:
        return
    _ANNOUNCED.add(kind)
    try:
        print("".join(c for c in text if 32 <= ord(c) <= 126),
              file=sys.stderr if stream is None else stream)
    except Exception:  # noqa: BLE001 - a broken stream is not this bug
        pass


def values_for(store, character_id, *, stream=None) -> dict:
    """The login-sent bytes this repository really knows for
    ``character_id``, keyed by ``x``: ``{7: <speed>, 10: <scene_seq>}`` when
    both resolve, fewer keys if one read failed, never a key this module
    cannot back with the login composer's own source.

    NEVER RAISES -- see module docstring.  An empty dict is a real answer
    (nothing could be read for this character), not an error signal, same
    as ``live_named_attr_values.values_for``.
    """
    from . import login_speed, player_wire  # noqa: PLC0415 - see docstring

    values: dict[int, Any] = {}

    try:
        resolved = login_speed.resolve_for_character(
            store, character_id,
            fallback=player_wire.PLAYER_LOGIN_MOVEMENT_SPEED,
        )
    except Exception as error:  # noqa: BLE001 - see docstring
        _say(stream, "speed",
             f"{READ_REFUSED_CONSOLE_TOKEN} speed {type(error).__name__}")
    else:
        values[7] = resolved.value

    try:
        scene_seq = store.get_character(character_id).position.scene_seq
    except Exception as error:  # noqa: BLE001 - see docstring
        _say(stream, "scene_seq",
             f"{READ_REFUSED_CONSOLE_TOKEN} scene_seq {type(error).__name__}")
    else:
        values[10] = scene_seq

    return values


def source_for_store(store) -> Callable[[Any], dict]:
    """The callable ``lane_hooks.register_login_attr_bytes_source`` wants.

    Bound to one store, same reasoning as
    ``live_named_attr_values.source_for_store``: the character id is what
    selects a character, so a single process-wide source serves every
    connection without any of them reading another's row by accident.
    """
    def read_live_login_attr_bytes(character_id) -> dict:
        return values_for(store, character_id)

    read_live_login_attr_bytes.__qualname__ = (
        "live_login_attr_bytes.source_for_store.read_live_login_attr_bytes"
    )

    return read_live_login_attr_bytes
