"""GM allowlist: the one gate every other module in this package trusts.

Default is the empty set -- nobody is a GM until an operator puts an
account_id in the allowlist source. The client cannot add itself: there is
no wire path in this package (or anywhere in gm/) that writes to this set,
only ones that read it.
"""
import json
import os
from pathlib import Path

GM_ACCOUNTS_ENV = "PF_GM_ACCOUNTS_PATH"


def load_gm_accounts(path: str | Path | None = None) -> frozenset[int]:
    """Load the GM allowlist from a JSON file: a list of account_id ints.

    Missing env var, missing file, or a file that fails to parse as a JSON
    list of ints all resolve to the empty set -- fail closed, not open.
    """
    source = path if path is not None else os.environ.get(GM_ACCOUNTS_ENV)
    if not source:
        return frozenset()
    try:
        raw = Path(source).read_text(encoding="utf-8")
        parsed = json.loads(raw)
    except (OSError, ValueError):
        return frozenset()
    if not isinstance(parsed, list):
        return frozenset()
    return frozenset(item for item in parsed if isinstance(item, int) and not isinstance(item, bool))


def is_gm(account_id: int, gm_accounts: frozenset[int]) -> bool:
    """True only if account_id is literally in the allowlist passed in."""
    return account_id in gm_accounts
