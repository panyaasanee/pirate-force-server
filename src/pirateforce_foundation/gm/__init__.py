"""Lane GM: GM/developer tooling that only ever reaches gm_accounts.

Nothing in this package changes what a normal player sees or can do.
Every function here is inert unless the caller supplies an account id that
is already present in the server-side gm_accounts allowlist (see
accounts.py). There is no client-side path that can set that membership.
"""
