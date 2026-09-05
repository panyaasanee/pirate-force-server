"""LANE-Q's Lua API namespaces (Player/Quest/Trigger/Party/Mob/Instance/Guild/Scene).

This package holds the frozen 160-name spec (:mod:`.spec`) and, as each
namespace grows real implementations instead of stubs, one module per
namespace (``lua_api/quest.py``, ``lua_api/trigger.py``, ...).  Nothing under
here is implemented yet (see ``docs/SCRIPT_LANE.md``) -- the spike round
only builds the stub surface in ``script_host.py`` that every future real
implementation replaces one method at a time.
"""
from . import spec

__all__ = ["spec"]
