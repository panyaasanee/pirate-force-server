"""GM-005: per-account login-scene override (PANYA-ORDER path A, fast path).

Purpose: let an operator point one already-listed GM account at a specific
scene_id on login, so a tester can see a non-default map without needing the
GM in-game editor widget (still gated behind ``RE-104``) or cross-scene
``TeleportVital`` (still gated behind ``RE-090``'s unproven field semantics
and ``CORE-REQUEST-011``'s same-scene-only wiring).  This is a shortcut to a
test-ready state, not a warp feature -- callers and test entries that use it
must say so (see docs/GM_LANE.md "Nonclaim rule").

Default = no override for anyone.  An account only ever gets an override if
BOTH of the following hold, checked every call, not cached:

1. It is listed in ``gm/accounts.py``'s ``gm_accounts`` allowlist (the same
   config this whole lane's GM status already gates on).
2. It has an entry in this module's own config, and that entry names a
   scene_id present in ``gm/scene_catalog.py``'s 330-row committed table.

A non-GM account is invisible to this module even if someone puts its name
in the override config by mistake -- the config alone can never grant
anything; ``gm_accounts.json`` remains the single place that grants GM
status.  This mirrors ``gm/accounts.py``'s own fail-closed default and its
"a typo does not silently resolve to nobody is GM" rule: a present config
with a malformed shape is an error, not a silent no-op.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from .accounts import is_gm_account
from .scene_catalog import is_known_scene_id

DEFAULT_CONFIG_PATH = "config/gm_login_scene.json"
ENV_OVERRIDE = "PF_GM_LOGIN_SCENE_CONFIG"


def _resolve_path(config_path: str | os.PathLike | None) -> Path:
    if config_path is not None:
        return Path(config_path)
    env_path = os.environ.get(ENV_OVERRIDE)
    if env_path:
        return Path(env_path)
    return Path(DEFAULT_CONFIG_PATH)


def load_login_scene_overrides(
    config_path: str | os.PathLike | None = None,
) -> dict[str, int]:
    """Load the account -> scene_id override map.

    A missing file means the map is empty (no override for anyone), the
    same "absence is the safe default" rule ``gm/accounts.py`` uses. A
    present file with a malformed ``gm_login_scene`` key, a non-int
    scene_id, or a scene_id absent from the committed GM scene catalog is
    an error -- fail loud instead of silently sending an operator's typo to
    an unreviewed scene.
    """
    path = _resolve_path(config_path)
    if not path.is_file():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(
            f"{path}: top-level JSON must be an object, got {type(data).__name__}"
        )
    overrides = data.get("gm_login_scene", {})
    if not isinstance(overrides, dict):
        raise ValueError(
            f"{path}: 'gm_login_scene' must be a JSON object, "
            f"got {type(overrides).__name__}"
        )
    result: dict[str, int] = {}
    for account_name, scene_id in overrides.items():
        if not isinstance(account_name, str):
            raise ValueError(
                f"{path}: 'gm_login_scene' keys must be strings, got {account_name!r}"
            )
        if not isinstance(scene_id, int) or isinstance(scene_id, bool):
            raise ValueError(
                f"{path}: 'gm_login_scene'[{account_name!r}] must be an int scene_id, "
                f"got {scene_id!r}"
            )
        if not is_known_scene_id(scene_id):
            raise ValueError(
                f"{path}: 'gm_login_scene'[{account_name!r}] = {scene_id} is not a "
                "known scene_id in gm/scene_catalog.py's committed table"
            )
        result[account_name] = scene_id
    return result


def get_login_scene_override(
    account_name: str,
    gm_accounts_config_path: str | os.PathLike | None = None,
    login_scene_config_path: str | os.PathLike | None = None,
) -> int | None:
    """The scene_id ``account_name`` should log into instead of the default.

    Returns ``None`` unless the account is BOTH a listed GM account AND has
    an override entry -- checked fresh on every call, not cached, so a
    config edit takes effect on the next login without a restart-order
    dependency between the two files.
    """
    if not isinstance(account_name, str):
        raise TypeError("account_name must be a str")
    if not is_gm_account(account_name, gm_accounts_config_path):
        return None
    overrides = load_login_scene_overrides(login_scene_config_path)
    return overrides.get(account_name)
