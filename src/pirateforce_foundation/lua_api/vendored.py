"""The one exception type that means A VENDORED FILE OF OURS IS BROKEN.

WHY A BASE CLASS AND NOT A LIST.  ``script_host._host_side_error_types()``
used to be a hand-maintained tuple naming each vendored file's own error
class, with nothing anywhere asserting the tuple was COMPLETE: a third
mirror added next year would raise an error nobody had listed, fall through
to the generic ``except Exception``, and be logged ``LUA_SCRIPT <file> ERR``
against whichever quest script happened to be loading -- the exact defect
pf-adversary D11 (round 7kxfe9) was raised to fix, arriving again through
the door the fix left open.  Deriving the classification from a base class
makes the tuple complete BY CONSTRUCTION: any loader that raises a subclass
of :class:`VendoredDataError` is host-side, whether or not anyone remembered
to add it to a list.

It also keeps ``script_host.py`` from having to name a per-namespace error
class, which matters for a second, unrelated reason: the quest/shop symbol
guard in ``tests/test_npc_interaction_wire.py`` reads every identifier in
that module, and a chief-granted exemption list is not the right price for
an import line.
"""
from __future__ import annotations


class VendoredDataError(RuntimeError):
    """A mirror in THIS repository is missing, unreadable, or corrupt.

    Deliberately not something a Lua script can provoke: it means go fix
    this checkout, not go read that quest file.
    """
