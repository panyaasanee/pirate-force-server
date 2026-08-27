"""Server-side allowlist for the GT-114 five-object diagnostic boot.

Default = nobody gets the diagnostic.  This is the gate
``mob_diag_multi_object.GT_DIAG_MULTI_OBJECT_WIRING`` asks for in its very
first clause -- "behind a diagnostic-only boot config (env var, same shape as
PF_GM_ACCOUNTS_CONFIG -- never on by default)" -- and it is a deliberate,
line-for-line copy of :mod:`pirateforce_foundation.gm.accounts` rather than a
new design: same env-var override, same relative default path, same
missing-file-means-empty rule, same loud refusal on a malformed file, same
exact case-sensitive matching.  A second config loader that behaved even
slightly differently from the one this project already ships would be a
second thing to reason about for no gain.

WHY AN ALLOWLIST AND NOT A SCENARIO FLAG.  The five diagnostic objects are
composed by a lane-B module and placed in the LIVE bg0001 census, on the
default runtime path -- there is no ``--something-scenario`` in front of them.
The only thing that may decide whether a given boot carries them is the
server's own on-disk config naming the attended tester's account, so that a
production login by anyone else is byte-for-byte the login that shipped
yesterday.  No client message can ask for this, exactly as no client message
can ask for GM.

THIS REPOSITORY SHIPS NO ``config/diag_multi_object.json``.  That absence IS
the off switch, and ``tests/test_diag_multi_object_config.py`` pins it: the
file is created by the operator on the machine that runs the attended test,
never committed here.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

DEFAULT_CONFIG_PATH = "config/diag_multi_object.json"
ENV_OVERRIDE = "PF_DIAG_MULTI_OBJECT_CONFIG"
CONFIG_KEY = "diag_multi_object_accounts"

# Convention marker only; nothing in this tree branches on it.
production_allowed = True
test_only = False


def _resolve_path(config_path: str | os.PathLike | None) -> Path:
    if config_path is not None:
        return Path(config_path)
    env_path = os.environ.get(ENV_OVERRIDE)
    if env_path:
        return Path(env_path)
    return Path(DEFAULT_CONFIG_PATH)


def load_diag_multi_object_accounts(
    config_path: str | os.PathLike | None = None,
) -> frozenset[str]:
    """Load the diagnostic-boot allowlist.

    A missing file is not an error: it means the allowlist is empty, which is
    the required default (nobody gets the five diagnostic objects until an
    operator explicitly lists an account).  A present file with a malformed
    ``diag_multi_object_accounts`` key is an error, so a typo does not
    silently resolve to "the diagnostic is off" and hide itself from whoever
    configured it the night before an attended test.
    """
    path = _resolve_path(config_path)
    if not path.is_file():
        return frozenset()
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(
            f"{path}: top-level JSON must be an object, got {type(data).__name__}"
        )
    accounts = data.get(CONFIG_KEY, [])
    if not isinstance(accounts, list):
        raise ValueError(
            f"{path}: '{CONFIG_KEY}' must be a JSON list, got {type(accounts).__name__}"
        )
    for entry in accounts:
        if not isinstance(entry, str):
            raise ValueError(
                f"{path}: '{CONFIG_KEY}' entries must be strings, got {entry!r}"
            )
    return frozenset(accounts)


def is_diag_multi_object_account(
    account_name: str, config_path: str | os.PathLike | None = None,
) -> bool:
    """True only if ``account_name`` is listed verbatim in the allowlist.

    Matching is exact and case-sensitive on purpose, the same choice
    ``gm.accounts.is_gm_account`` makes and for the same reason: this project
    has no proven account-name normalization rule (see AGENTS.md on not
    inventing identity semantics), so silently case-folding this allowlist
    would put five extra bodies in the town of an account nobody listed.
    """
    if not isinstance(account_name, str):
        raise TypeError("account_name must be a str")
    return account_name in load_diag_multi_object_accounts(config_path)
