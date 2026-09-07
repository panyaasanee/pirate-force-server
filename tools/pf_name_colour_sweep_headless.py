#!/usr/bin/env python3
"""Print the name-colour sweep's composition token, headless, no client.

WHY THIS EXISTS.  Rule ``0159`` (PANYA 2026-09-07) wants every attended ticket
to carry a console token measured on the CURRENT main commit, proving the
mechanism the ticket tests is armed in the target scene before a boot is spent
on it.  The ALL / ALL-NOID sweep cannot produce the boot-time
``NAME_COLOUR_SWEEP_ARMED`` line here: that line is printed by the arrival
census inside ``runtime.py``, which needs a real client attaching.

What CAN be measured without a client is the half this lane owns: whether the
armed value composes bodies at all, how many boards it draws, and that the
unarmed boot draws none.  That is what this prints, in one line per set, so
LANE-K and ka1-A can re-run the identical command on whatever commit they are
holding and compare tokens instead of taking a round file's word for it.

    python3 tools/pf_name_colour_sweep_headless.py

Exit status is 0 when every armed set composes at least one board and the
unarmed boot composes none, 1 otherwise.  Nothing is sent, scheduled or
persisted: this calls the same pure ``sweep_actors``/``sweep_entries`` the
census calls and prints what came back.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import name_colour_sweep  # noqa: E402
from pirateforce_foundation.legacy_bridge import load_legacy  # noqa: E402

LEGACY = ROOT / "current" / "pf_login_game_server_v141.py"


def _commit() -> str:
    try:
        return subprocess.run(
            ["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
    except Exception:  # noqa: BLE001
        return "unknown"


def main() -> int:
    legacy = load_legacy(LEGACY)
    commit = _commit()
    ok = True

    unarmed = name_colour_sweep.sweep_actors(legacy, {})
    print(f"NAME_COLOUR_SWEEP_UNARMED actors={len(unarmed)} commit={commit}")
    if unarmed:
        ok = False

    for value in name_colour_sweep.KNOWN_SETS:
        actors = name_colour_sweep.sweep_actors(
            legacy, {name_colour_sweep.SWEEP_ENV: value})
        entries = name_colour_sweep.sweep_entries(
            legacy, {name_colour_sweep.SWEEP_ENV: value})
        labels = ",".join(actor.label for actor in actors)
        print(
            f"NAME_COLOUR_SWEEP_COMPOSED set={value} actors={len(actors)} "
            f"entries={len(entries)} bytes={sum(len(e) for e in entries)} "
            f"commit={commit}"
        )
        print(f"  labels={labels}")
        if not actors:
            ok = False

    print("NAME_COLOUR_SWEEP_HEADLESS " + ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
