"""LANE-Q's Lua API namespaces (Player/Quest/Trigger/Party/Mob/Instance/Guild/Scene).

This package holds the frozen 160-name spec (:mod:`.spec`) and, as each
namespace grows real implementations instead of stubs, one module per
namespace.  ``.trigger`` is the first (round after ``s2fxf6``): 5 of
``Trigger``'s 17 names are real, backed by a process-memory status registry.
``.instance`` is the second (round ``4fxvsq``): 7 of ``Instance``'s 9 names
are real, same shape.  See each module's own docstring and
``docs/SCRIPT_LANE.md`` for what is and is not done.  Every other namespace
is still all-stub, built by ``script_host.py``'s generic
``ApiNamespaceStub``.
"""
from . import spec
from . import trigger
from . import instance

__all__ = ["spec", "trigger", "instance"]
