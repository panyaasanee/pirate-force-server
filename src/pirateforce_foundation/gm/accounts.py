"""Server-side GM allowlist.

Default = nobody is GM.  The client has no message that requests GM status
for itself (LANE-GM static survey, notes_to_chief 20260826_1630: no ``/xxx``
command strings anywhere in the client image, and no client->server "make me
GM" vital exists in the registry) -- GM status can only ever be granted by
this module reading a server-side config, never by anything a client sends.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

DEFAULT_CONFIG_PATH = "config/gm_accounts.json"
ENV_OVERRIDE = "PF_GM_ACCOUNTS_CONFIG"


def _resolve_path(config_path: str | os.PathLike | None) -> Path:
    if config_path is not None:
        return Path(config_path)
    env_path = os.environ.get(ENV_OVERRIDE)
    if env_path:
        return Path(env_path)
    return Path(DEFAULT_CONFIG_PATH)


def load_gm_accounts(config_path: str | os.PathLike | None = None) -> frozenset[str]:
    """Load the gm_accounts allowlist.

    A missing file is not an error: it means the allowlist is empty, which is
    the required default (no one is GM until an operator explicitly lists an
    account).  A present file with a malformed ``gm_accounts`` key is an
    error, so a typo does not silently resolve to "nobody is GM" and hide
    itself from whoever configured it.
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
    accounts = data.get("gm_accounts", [])
    if not isinstance(accounts, list):
        raise ValueError(
            f"{path}: 'gm_accounts' must be a JSON list, got {type(accounts).__name__}"
        )
    for entry in accounts:
        if not isinstance(entry, str):
            raise ValueError(f"{path}: 'gm_accounts' entries must be strings, got {entry!r}")
    return frozenset(accounts)


def is_gm_account(account_name: str, config_path: str | os.PathLike | None = None) -> bool:
    """True only if ``account_name`` is listed verbatim in the server-side allowlist.

    Matching is exact and case-sensitive on purpose: this project has no
    proven account-name normalization rule (see AGENTS.md on not inventing
    identity semantics), so silently case-folding a GM allowlist would grant
    GM status to an account nobody explicitly listed.

    pf-adversary (gm/ package sweep): the check below used to be
    ``isinstance(account_name, str)``, which admits any ``str`` subclass --
    the exact bug shape this package spent five documented rounds hardening
    for ``GmCommand.args`` (``type(args) is not tuple``, never
    ``isinstance``), but that lesson had never reached the one check this
    entire package's security invariant is ultimately gated on. A ``str``
    subclass overriding ``__eq__``/``__hash__`` to always compare equal and
    hash to a real listed account's value passed the old ``isinstance``
    check and then made the ``in`` test below true for an account name that
    was never actually listed (``frozenset.__contains__`` hashes then
    ``==``s the query object, trusting whatever dunders it defines).
    ``type(account_name) is str`` rejects any subclass outright, so the
    object handed to ``in`` below is always a real, final ``str`` whose
    ``__eq__``/``__hash__`` cannot have been overridden.
    """
    if type(account_name) is not str:
        raise TypeError("account_name must be a str")
    return account_name in load_gm_accounts(config_path)
