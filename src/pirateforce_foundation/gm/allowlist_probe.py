"""Say OUT LOUD, once per process, why an inbound 0x51E9 was refused.

WHY THIS MODULE EXISTS -- the cost is measured, not hypothetical.  The
attended boot R322B (pf_bridge letter
`notes_to_chief/20260907_0123_KA1A-R322B-RESULTS-*`, 2026-09-07 01:17)
spent an owner-machine session establishing that the real client DOES send
`GM_RunGMCommandVital` (0x51E9): the panel's row widgets are radio buttons
and the sender is the EXECUTE button in the bottom-right corner, and three
real frames went out.  The server answered every one of them with an empty
`RuntimeRes` and no `capture/gm_command_capture` directory ever appeared
under the boot tree.  The letter had to record the result as
`CAPTURED-CLIENT-NEGATIVE-SERVER` with an open question in it -- "we must
find where the frame went: the v141 path, or the account allowlist" --
because from outside, a frame that never reached the hook, a hook that
never fired, and a frame refused by the allowlist all look identical: a
silent server and an empty disk.

They are not identical, and the server already knew which one it was.
`gm/accounts.py`'s `load_gm_accounts` treats a MISSING allowlist file as an
empty allowlist -- deliberately, and this module does not change that: no
one is GM until an operator lists an account, and rule (1) of this lane is
that the client can never elevate itself.  `config/gm_accounts.json` is not
in the shipped tree, so on that boot the allowlist was empty, every send
was `REFUSAL_NOT_GM`, and the refusal was correct.  What was wrong is that
it was INVISIBLE: `gm/dispatch.py` returns the reason in a dataclass field
and `lane_hooks/lane_gm_run_command.py` appends it to `session.events`,
which is a structure nobody at a game client is reading at 01:17.

So this prints one console line the first time a GM command is refused for
that reason in a process, naming the file the server actually looked for,
how it chose that path, and whether it was there.  It is the difference
between an attended boot ending in an open question and an attended boot
ending in "add your account to this file and press EXECUTE again".

WHAT IT DELIBERATELY DOES NOT DO
- It does not grant anything.  It reads the allowlist and reports; there is
  no code path here that makes an account GM, and there is no input from
  the client anywhere in it.
- It does not send a frame.  The refusal stays silent ON THE WIRE: a
  non-GM player must not be able to tell a GM-capable server from any
  other server by pressing a button, so the client learns nothing new.
  This line goes to the operator's console only.
- It does not print account NAMES from the allowlist, only how many there
  are.  The one name it prints is the name of the account that just sent
  the frame -- which is the operator's own, and is what makes the line
  actionable ("`admin` is not on the list") instead of merely informative.
- It prints ONCE per process (`reset_for_tests` exists so tests are not
  order-dependent).  The rate limiter in `gm/dispatch.py` bounds how often
  a refusal can even happen; the latch bounds it to one line regardless,
  because an operator holding the EXECUTE button must not lose the line
  that matters in a scroll of identical ones.
"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

from .accounts import DEFAULT_CONFIG_PATH, ENV_OVERRIDE, load_gm_accounts
from .command_capture import _fold_line_breaking_controls, _quote_console_field
from .login_scene_override import console_safe

# Same grep-anchor discipline as `command_capture._UNLINK_STUCK_CONSOLE_TOKEN`:
# a fixed ASCII first word, so an operator (or a tool) can find this line on a
# cp874 console without knowing anything else about it.  docs/GM_LANE.md names
# this token; the test below pins it to the literal so renaming it here cannot
# leave the documentation pointing at a word that no longer prints (the D4
# lesson from round `vxr32s`).
GM_ALLOWLIST_CONSOLE_TOKEN = "GM_COMMAND_REFUSED_NOT_GM"

_ANNOUNCED = False


@dataclass(frozen=True)
class GmAllowlistStatus:
    """What the server looked for, how it chose, and what it found.

    ``account_count`` is None when the file exists but could not be read as
    an allowlist -- ``error`` then carries the reason.  That case is NOT the
    same as an empty allowlist and must not print as one: a malformed config
    is an operator typo that `gm/accounts.py` raises on by design, and an
    operator who is told "0 accounts" for a file they just wrote will go
    looking in the wrong place.
    """

    resolved_path: Path
    source: str
    exists: bool
    account_count: int | None
    error: str | None


def describe_gm_allowlist(config_path: str | os.PathLike | None = None) -> GmAllowlistStatus:
    """Resolve the allowlist the way `gm/accounts.py` does, and report on it.

    The resolution order is duplicated from `accounts._resolve_path` on
    purpose ONLY in the sense that it must agree with it; the test module
    pins the two against each other so a change to one that is not mirrored
    here turns a test red rather than printing a path the server never
    opened -- which is the one failure mode that would make this line worse
    than saying nothing at all.
    """
    if config_path is not None:
        resolved, source = Path(config_path), "argument"
    else:
        env_path = os.environ.get(ENV_OVERRIDE)
        if env_path:
            resolved, source = Path(env_path), "env"
        else:
            resolved, source = Path(DEFAULT_CONFIG_PATH), "default"
    exists = resolved.is_file()
    if not exists:
        return GmAllowlistStatus(resolved, source, False, 0, None)
    try:
        count = len(load_gm_accounts(resolved))
    except Exception as exc:  # a malformed config must not crash the dispatch
        return GmAllowlistStatus(resolved, source, True, None, repr(exc))
    return GmAllowlistStatus(resolved, source, True, count, None)


def format_allowlist_refusal_line(
    status: GmAllowlistStatus, account_name: str, stream=None,
) -> str:
    """Compose the one line, under the same grammar as the capture line.

    Both operator-controlled values (the account name, and the resolved path
    -- which comes from a config value or an environment variable, not from
    this project's own fixtures) go through the same two steps
    `command_capture` pays for: fold what can break a LINE, then quote so a
    value cannot forge a neighbouring FIELD, then hand the result to
    `console_safe` for what the stream can actually encode.  Reusing those
    functions rather than re-typing the composition is the point: the two
    rounds of pf-adversary findings that hardened them (`nfbat1` D-list,
    `vxr32s` D2/D3) apply to this line for free, and a third round that
    hardens them further does not have to find this file to fix it too.
    """
    stream = sys.stderr if stream is None else stream
    safe_account = console_safe(
        _fold_line_breaking_controls(account_name) or "(unknown)", stream,
    )
    safe_path = console_safe(
        _fold_line_breaking_controls(str(status.resolved_path)), stream,
    )
    if status.account_count is None:
        found = "unreadable"
    elif not status.exists:
        found = "missing"
    else:
        found = str(status.account_count)
    return (
        f"{GM_ALLOWLIST_CONSOLE_TOKEN} "
        f"account={_quote_console_field(safe_account)} "
        f"allowlist={_quote_console_field(safe_path)} "
        f"source={status.source} accounts={found} -- this account is not on "
        f"the server-side GM allowlist, so the command was refused and "
        f"nothing was captured; add it to that file and restart the server. "
        f"The client is told nothing either way (see docs/GM_LANE.md)"
    )


def announce_not_gm_once(
    account_name: str,
    *,
    config_path: str | os.PathLike | None = None,
    stream=None,
) -> bool:
    """Print the line if it has not been printed yet; report whether it was.

    Returns True only on the call that actually printed, so a caller (and
    the test below) can tell the latch worked.  Every failure inside is
    swallowed: this is a diagnostic on a refusal path, and a console that
    refuses the write must never turn a correctly-refused GM command into an
    exception travelling back up through `lane_hooks.fire()` into the
    connection handler.
    """
    global _ANNOUNCED
    if _ANNOUNCED:
        return False
    try:
        target = sys.stderr if stream is None else stream
        print(
            format_allowlist_refusal_line(
                describe_gm_allowlist(config_path), account_name, target,
            ),
            file=target,
        )
    except Exception:
        # THE LATCH CLOSES ON A DELIVERED LINE, NOT ON AN ATTEMPT (self-
        # review, round `wxh2tw`). Setting it before the print reads as the
        # safer order and is the wrong one here: a console that is briefly
        # unwritable at the moment of the FIRST refusal would then consume
        # the only line this process will ever print, and the operator --
        # who is standing at a game client pressing EXECUTE, which is the
        # entire situation this exists for -- gets silence again. Retrying
        # costs one swallowed exception per refusal, and `gm/dispatch.py`'s
        # rate limiter already bounds how often a refusal can happen.
        return False
    _ANNOUNCED = True
    return True


def reset_for_tests() -> None:
    """Clear the once-per-process latch.  Tests only."""
    global _ANNOUNCED
    _ANNOUNCED = False
