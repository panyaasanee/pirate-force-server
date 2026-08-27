"""GM-005: per-account login-scene override (PANYA-ORDER path A, fast path).

Purpose: let an operator point one already-listed GM account at a specific
scene_id on login, so a tester can see a non-default map without needing the
GM in-game editor widget (still gated behind ``RE-104``) or cross-scene
``TeleportVital`` (still gated behind ``RE-090``'s unproven field semantics
and ``CORE-REQUEST-011``'s same-scene-only wiring).  This is a shortcut to a
test-ready state, not a warp feature -- callers and test entries that use it
must say so (see docs/GM_LANE.md "Nonclaim rule").

Default = no override for anyone.  An account gets an override through
EITHER of two independent paths, each checked fresh on every call, never
cached:

1. GM-gated path (``gm_login_scene``): BOTH the account is listed in
   ``gm/accounts.py``'s ``gm_accounts`` allowlist AND it has an entry in
   this module's own config naming a scene_id present in
   ``gm/scene_catalog.py``'s committed table.  This path always rides
   alongside full GM status (``is_gm_account`` stays the caller's own
   concern -- this module never sets it, only reads it).

2. Standalone path (``standalone_login_scene``, [สมมติของสาย GM - รอ COO
   ยืนยัน], added 2026-08-28 answering the KA1A-NOTE at
   ``notes_to_chief/20260827_2240_KA1A-NOTE-GT110-unsafe-until-0x5A19-payload-fixed-plus-M1P-jobs-staged.md``):
   an account listed ONLY in this module's own standalone config, by name,
   with no ``gm_accounts.json`` membership at all.  This exists so a scene
   can be exercised on login (e.g. `GT-110`) without also triggering
   `GM_UpdateGMStateVital` (``0x5A19``) -- that frame is gated purely on
   ``is_gm_account()`` at the ``runtime.py`` call site (``CORE-REQUEST-016``)
   and this path deliberately never makes that predicate true.  A standalone
   entry grants a login scene_id and NOTHING else -- no GM status, no GM
   command surface, no `GM_UpdateGMStateVital` frame; it is a pure spawn-
   position convenience, gated by its own allowlist, off by default.

Either path alone is enough; an account does not need both.  A non-GM
account is invisible to path 1 even if someone puts its name in the
``gm_login_scene`` config by mistake -- that config alone can never grant
anything; ``gm_accounts.json`` remains the single place that grants GM
status.  This mirrors ``gm/accounts.py``'s own fail-closed default and its
"a typo does not silently resolve to nobody is GM" rule: a present config
with a malformed shape is an error, not a silent no-op -- true for both
paths' config files independently.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from .accounts import is_gm_account
from .scene_catalog import is_known_scene_id

DEFAULT_CONFIG_PATH = "config/gm_login_scene.json"
ENV_OVERRIDE = "PF_GM_LOGIN_SCENE_CONFIG"

STANDALONE_DEFAULT_CONFIG_PATH = "config/gm_login_scene_standalone.json"
STANDALONE_ENV_OVERRIDE = "PF_GM_LOGIN_SCENE_STANDALONE_CONFIG"
STANDALONE_JSON_KEY = "standalone_login_scene"


def _resolve_path(
    config_path: str | os.PathLike | None,
    default_path: str = DEFAULT_CONFIG_PATH,
    env_var: str = ENV_OVERRIDE,
) -> Path:
    if config_path is not None:
        return Path(config_path)
    env_path = os.environ.get(env_var)
    if env_path:
        return Path(env_path)
    return Path(default_path)


def _load_scene_id_map(
    path: Path, json_key: str
) -> dict[str, int]:
    if not path.is_file():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(
            f"{path}: top-level JSON must be an object, got {type(data).__name__}"
        )
    overrides = data.get(json_key, {})
    if not isinstance(overrides, dict):
        raise ValueError(
            f"{path}: '{json_key}' must be a JSON object, "
            f"got {type(overrides).__name__}"
        )
    result: dict[str, int] = {}
    for account_name, scene_id in overrides.items():
        if not isinstance(account_name, str):
            raise ValueError(
                f"{path}: '{json_key}' keys must be strings, got {account_name!r}"
            )
        if not isinstance(scene_id, int) or isinstance(scene_id, bool):
            raise ValueError(
                f"{path}: '{json_key}'[{account_name!r}] must be an int scene_id, "
                f"got {scene_id!r}"
            )
        if not is_known_scene_id(scene_id):
            raise ValueError(
                f"{path}: '{json_key}'[{account_name!r}] = {scene_id} is not a "
                "known scene_id in gm/scene_catalog.py's committed table"
            )
        result[account_name] = scene_id
    return result


def load_login_scene_overrides(
    config_path: str | os.PathLike | None = None,
) -> dict[str, int]:
    """Load the GM-gated account -> scene_id override map.

    A missing file means the map is empty (no override for anyone), the
    same "absence is the safe default" rule ``gm/accounts.py`` uses. A
    present file with a malformed ``gm_login_scene`` key, a non-int
    scene_id, or a scene_id absent from the committed GM scene catalog is
    an error -- fail loud instead of silently sending an operator's typo to
    an unreviewed scene.  An entry here still needs ``gm_accounts.json``
    membership too -- see ``get_login_scene_override``. For an override that
    does NOT require or imply GM status, see
    ``load_standalone_login_scene_overrides``.
    """
    path = _resolve_path(config_path, DEFAULT_CONFIG_PATH, ENV_OVERRIDE)
    return _load_scene_id_map(path, "gm_login_scene")


def load_standalone_login_scene_overrides(
    config_path: str | os.PathLike | None = None,
) -> dict[str, int]:
    """Load the standalone account -> scene_id override map.

    [สมมติของสาย GM - รอ COO ยืนยัน] Same shape and same fail-loud-on-
    malformed-config rules as ``load_login_scene_overrides``, but a
    SEPARATE file/env var/JSON key, and listing here never touches
    ``gm_accounts.json`` and never implies GM status -- it grants a login
    scene_id and nothing else. Default = empty (no file = no override for
    anyone), same safe default as every other config in this lane.
    """
    path = _resolve_path(
        config_path, STANDALONE_DEFAULT_CONFIG_PATH, STANDALONE_ENV_OVERRIDE
    )
    return _load_scene_id_map(path, STANDALONE_JSON_KEY)


def get_login_scene_override(
    account_name: str,
    gm_accounts_config_path: str | os.PathLike | None = None,
    login_scene_config_path: str | os.PathLike | None = None,
    standalone_config_path: str | os.PathLike | None = None,
) -> int | None:
    """The scene_id ``account_name`` should log into instead of the default.

    Checks two independent paths, in order, each fresh on every call, never
    cached:

    1. GM-gated: the account is BOTH a listed GM account AND has an entry
       in ``login_scene_config_path`` (``gm_login_scene.json``).
    2. Standalone: the account has an entry in ``standalone_config_path``
       (``gm_login_scene_standalone.json``) -- no GM listing required or
       implied.  [สมมติของสาย GM - รอ COO ยืนยัน] see module docstring.

    Returns ``None`` if neither path has an entry for this account, so a
    config edit (either file) takes effect on the next login without a
    restart-order dependency between any of the files involved.

    pf-adversary (gm/ package sweep): ``type(account_name) is not str``,
    not ``isinstance`` -- both dict lookups below (``overrides.get``,
    ``standalone_overrides.get``) hash then ``==`` the query object the same
    way ``accounts.is_gm_account``'s own allowlist test does, so a ``str``
    subclass lying through ``__eq__``/``__hash__`` could otherwise resolve
    to a different account's override entry. See ``accounts.is_gm_account``
    for the full failure scenario this closes.
    """
    if type(account_name) is not str:
        raise TypeError("account_name must be a str")
    if is_gm_account(account_name, gm_accounts_config_path):
        overrides = load_login_scene_overrides(login_scene_config_path)
        scene_id = overrides.get(account_name)
        if scene_id is not None:
            return scene_id
    standalone_overrides = load_standalone_login_scene_overrides(
        standalone_config_path
    )
    return standalone_overrides.get(account_name)
