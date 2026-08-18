#!/usr/bin/env python3
"""The project's single definition of "a client UI model file".

Pure stdlib.  No side effects on import.  Reads only; writes nothing, opens no
socket, touches no database.

Why this module exists (SCAN-DEBT-001, round 84)
------------------------------------------------
``PF_SPLIT_OPERATE003`` closes its caption route with a **negative**: there is no
``.model`` file in the client's UI model directory whose name contains "split"
or "divide", therefore the split caption is not in the GUI and only a live
capture can pin it.  A negative is only as good as the set it is a negative over,
and that set was being built twice, differently:

    tools/pf_split_operate_verb_panels_static.py:197
        models = os.listdir(GUI_MODEL)                    -> 573 entries
    tests/test_split_operate_verb_panels_static.py:154
        {p.name.lower() for p in GUI_MODEL.glob("*.model")} -> 534 files

573 = 534 ``.model`` + 37 ``.project`` + 1 ``.fsl`` + 1 ``.tip``.  Both sides
happened to reach the same verdict today (no match either way), so nothing was
red; but the tool and the test that is supposed to regression-guard it were
answering the question over two different denominators, and neither of them had
written down which one the report meant.  The next asset drop is what turns that
into a real disagreement.

So the definition lives here, once, in prose and in code, and both callers ask
this module.

The definition
--------------
A **UI model file** is a *regular file* sitting *directly* in
``GameClient/Data/GUI/Model`` whose name ends with ``.model``, compared
case-insensitively.

What that includes and excludes, and why:

* **``.model`` only.**  The claim in the report is about UI *model* documents -
  the plaintext ``<UIControlData>`` XML that defines a control.  The 37
  ``.project`` files, the ``.fsl`` and the ``.tip`` beside them are editor
  sidecars; a caption cannot be defined in them, so counting them widens the
  denominator without widening the evidence.
* **Case-insensitive.**  ``Path.glob("*.model")`` is case-sensitive on Linux and
  case-insensitive on Windows.  This project runs its verifiers on both (gate in
  the Linux sandbox, commits from the Windows bridge), and a negative that means
  something different on the two machines is not a negative.  Today no name in
  the directory varies in case, so this costs nothing and removes a way for the
  two to diverge later without anybody noticing.
* **Regular files only, no recursion.**  A subdirectory called ``Split.model``
  is not a model, and the report's claim is about that one directory, not the
  tree under it.
* **Missing directory is an error, not an empty answer.**  The old tool printed
  ``SKIP  GUI/Model dir not reachable from this cwd (packaging layout)`` and
  carried on, which turns "I could not look" into "I looked and found nothing" -
  the exact shape of negative this project has been burned by.  ``model_files``
  raises instead.

Note on where the directory lives: ``GameClient/Data/GUI/`` sits in the game
install tree beside the repository, has never been under version control, and is
not hashed in any manifest.  That is a real limitation of every claim built on
it and it is written down in the report rather than papered over here.
"""
from __future__ import annotations

from pathlib import Path

#: ``<repo>/../GameClient/Data/GUI/Model`` - the game install tree, read-only.
DEFAULT_MODEL_DIR = (
    Path(__file__).resolve().parents[2] / "GameClient" / "Data" / "GUI" / "Model"
)

MODEL_SUFFIX = ".model"


class ClientAssetsUnavailable(Exception):
    """The client asset directory is not readable, so nothing may be concluded."""


def model_files(model_dir: Path | str | None = None) -> list[Path]:
    """Every UI model file in ``model_dir``, sorted, per the definition above.

    Raises ``ClientAssetsUnavailable`` if the directory is missing.  "I could not
    look" and "I looked and found nothing" are different answers and this
    function refuses to conflate them.
    """
    directory = Path(model_dir) if model_dir is not None else DEFAULT_MODEL_DIR
    if not directory.is_dir():
        raise ClientAssetsUnavailable(
            "client UI model directory not readable: %s\n"
            "  It lives in the game install tree beside the repository and is "
            "not under version control.  Every negative in "
            "PF_SPLIT_OPERATE003 is a statement about this directory, so its "
            "absence is a FAILURE to verify, never a pass." % directory)
    return sorted(
        entry for entry in directory.iterdir()
        if entry.is_file() and entry.name.lower().endswith(MODEL_SUFFIX)
    )


def model_names(model_dir: Path | str | None = None) -> set[str]:
    """``model_files`` as a set of lower-cased file names."""
    return {path.name.lower() for path in model_files(model_dir)}


def models_named(needles, model_dir: Path | str | None = None) -> list[str]:
    """Every model file name containing any of ``needles`` (case-insensitive).

    This is the shape the split_stack negative is actually stated in: "no model
    is named split or divide".  Returning the offending names rather than a
    boolean is deliberate - a guard that fails should say what it found.
    """
    wanted = [needle.lower() for needle in needles]
    return sorted(
        name for name in model_names(model_dir)
        if any(needle in name for needle in wanted)
    )


if __name__ == "__main__":  # pragma: no cover - a convenience, not a verifier
    import sys

    try:
        files = model_files(sys.argv[1] if len(sys.argv) > 1 else None)
    except ClientAssetsUnavailable as error:
        raise SystemExit(str(error))
    print("%d UI model files in %s" % (len(files), DEFAULT_MODEL_DIR))
