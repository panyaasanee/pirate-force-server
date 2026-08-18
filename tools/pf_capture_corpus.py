#!/usr/bin/env python3
"""Loader for ``docs/PF_CAPTURE_CORPUS.json`` - the project's single home for
*which capture files count as evidence*.

Pure stdlib.  No side effects on import.  Nothing here boots a server, opens a
socket, touches a database or writes into ``capture*/``.

Why this module exists (CORPUS-PIN-001, round 82)
-------------------------------------------------
Several static verifiers used to answer the question "which capture files am I
allowed to quote?" by **scanning a directory**::

    GAME_CAPTURES = sorted(glob.glob(os.path.join(_ROOT, "capture_v141", "GAME_*.txt")))
    LOGIN_CAPTURES = sorted(glob.glob(os.path.join(_ROOT, "**", "LOGIN_*.txt"), recursive=True))

and then pinned *the number that came back* into a published report.  Three
things are wrong with that, and all three bit us:

1.  **A directory scan has no expectation.**  On 2026-08-19 a headless replay
    job booted the server without ``--capture-root`` from the repository root.
    The frozen delivery snapshot builds its capture directory from a *relative*
    path (``current/pf_login_game_server_v141.py:7867`` -> ``Path("capture_v141")``),
    so fresh captures landed inside the golden corpus and grew it 69 -> 72.
    ``capture_v141/`` is git-ignored (``.gitignore:157`` ``**/capture*/``), so
    ``git status`` stayed clean, the v141 guard stayed green - and the only
    thing in the whole gate that noticed was a *count pinned by an unrelated
    milestone*, noticed by accident.  A scan cannot tell "the corpus" from
    "the corpus plus whatever else happens to be sitting there".

2.  **A glob does not know which files hold still.**  ``GAME_*.txt`` also
    matched ``GAME_LIVE.txt`` and ``GAME_EVENTS_LIVE.txt``, which the server
    *overwrites in place on every single run* (``v141:7372-7373``).  Two of the
    69 files in the published denominator were mutable.  The numerator was
    unaffected (neither live file carries the frame), but "44 of 69" was never
    a statement about 69 archived captures - it was 44 of 67 archived captures
    plus two scratch files.

3.  **Counts are not content.**  Even a correct count says nothing about
    whether a capture still holds the bytes the report quotes.

So: the *names* of the evidence files, their sizes and their sha256 are now
recorded in ``docs/PF_CAPTURE_CORPUS.json``, which is inside ``/docs/`` and
therefore tracked by git (``.gitignore:87-88`` allow-lists it) even though the
capture directories themselves are not.  A verifier asks this module for a set
by name; the module proves each file is present and byte-identical, and - the
part that would have caught the incident above on the spot - proves that the
directory contains **no capture outside the pinned set**.

Read the ``__doc__`` array at the top of the JSON for the admission rules for
new evidence.

Usage
-----
    from pf_capture_corpus import CaptureCorpus
    corpus = CaptureCorpus.load()
    paths = corpus.resolve("game_v141_archived")     # raises on drift
    corpus.assert_no_strays("game_v141_archived")    # raises on extra files

Regenerating (only when new evidence is admitted on purpose)::

    python3 tools/pf_capture_corpus.py --regenerate
    python3 tools/pf_capture_corpus.py --check       # exit 0 = corpus intact
"""
from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TABLE = ROOT / "docs" / "PF_CAPTURE_CORPUS.json"

CHUNK = 1 << 20


class CaptureCorpusError(Exception):
    """Raised when the pinned corpus and the files on disk disagree."""


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        while True:
            block = handle.read(CHUNK)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest().upper()


class CaptureSet:
    """One named group of evidence files."""

    def __init__(self, name: str, spec: dict, root: Path):
        self.name = name
        self.root = root
        self.description = spec.get("description", "")
        self.scan_dir = spec["scan_dir"]
        self.pattern = spec["pattern"]
        self.recursive = bool(spec.get("recursive", False))
        # Directory names never descended into while scanning.  ``.git`` is
        # always pruned; anything else is spelled out in the JSON so the scan
        # stays auditable.
        self.prune_dirs = set(spec.get("prune_dirs", [])) | {".git"}
        # Files the scan matches that are deliberately NOT evidence, listed by
        # exact name with the reason.  Anything matched by the pattern that is
        # neither pinned nor excluded is a stray.
        self.excluded = dict(spec.get("excluded", {}))
        self.files = list(spec["files"])

    # -- basic views --------------------------------------------------------
    @property
    def relative_paths(self) -> list[str]:
        return [entry["path"] for entry in self.files]

    def __len__(self) -> int:
        return len(self.files)

    # -- the three proofs ---------------------------------------------------
    def resolve(self, verify: bool = True) -> list[Path]:
        """Return the pinned files as absolute paths, in pinned order.

        With ``verify`` (the default) every file must exist and match the
        pinned size and sha256.  A capture that was rewritten in place is a
        hard error, not a silently different number.
        """
        resolved: list[Path] = []
        problems: list[str] = []
        for entry in self.files:
            path = self.root / entry["path"]
            if not path.is_file():
                problems.append("missing: %s" % entry["path"])
                continue
            if verify:
                size = path.stat().st_size
                if size != entry["size"]:
                    problems.append(
                        "size drift: %s (pinned %d, on disk %d)"
                        % (entry["path"], entry["size"], size))
                    continue
                digest = sha256_of(path)
                if digest != entry["sha256"]:
                    problems.append(
                        "content drift: %s (pinned %s.., on disk %s..)"
                        % (entry["path"], entry["sha256"][:16], digest[:16]))
                    continue
            resolved.append(path)
        if problems:
            raise CaptureCorpusError(
                "capture set %r does not match docs/PF_CAPTURE_CORPUS.json:\n  %s"
                % (self.name, "\n  ".join(problems)))
        return resolved

    def scan(self) -> list[str]:
        """Every path under ``scan_dir`` matching ``pattern``, repo-relative.

        This is the *only* place a directory scan survives, and its result is
        never counted - it is only ever compared against the pinned set.
        """
        base = self.root / self.scan_dir
        if not base.is_dir():
            raise CaptureCorpusError(
                "capture set %r scans %s, which does not exist"
                % (self.name, self.scan_dir))
        found = []
        if not self.recursive:
            for entry in sorted(base.iterdir()):
                if entry.is_file() and fnmatch.fnmatch(entry.name, self.pattern):
                    found.append(entry.relative_to(self.root).as_posix())
            return sorted(found)
        # os.walk (not Path.rglob) so that pruned directories are never
        # descended into and an unreadable entry cannot abort the whole scan -
        # a corpus check that dies half way through is a corpus check that
        # reports "no strays".
        errors: list[str] = []
        for dirpath, dirnames, filenames in os.walk(
                base, onerror=lambda exc: errors.append(str(exc))):
            dirnames[:] = sorted(d for d in dirnames if d not in self.prune_dirs)
            for filename in filenames:
                if fnmatch.fnmatch(filename, self.pattern):
                    rel = Path(dirpath, filename).relative_to(self.root)
                    found.append(rel.as_posix())
        if errors:
            raise CaptureCorpusError(
                "capture set %r could not be scanned completely, so 'no "
                "strays' cannot be asserted:\n  %s"
                % (self.name, "\n  ".join(errors[:5])))
        return sorted(found)

    def strays(self) -> list[str]:
        """Files the scan finds that are neither pinned nor excluded."""
        known = set(self.relative_paths) | set(self.excluded)
        return [path for path in self.scan() if path not in known]

    def vanished(self) -> list[str]:
        """Pinned files the scan no longer finds."""
        found = set(self.scan())
        return [path for path in self.relative_paths if path not in found]

    def assert_no_strays(self) -> None:
        strays = self.strays()
        if strays:
            raise CaptureCorpusError(
                "capture set %r: %d file(s) under %s match %r but are not "
                "pinned in docs/PF_CAPTURE_CORPUS.json.\n"
                "  Either a job wrote into read-only evidence (see the module "
                "docstring), or new evidence was added without admitting it.\n"
                "  %s"
                % (self.name, len(strays), self.scan_dir, self.pattern,
                   "\n  ".join(strays[:10])))


class CaptureCorpus:
    """Parsed view of ``docs/PF_CAPTURE_CORPUS.json``."""

    def __init__(self, data: dict, root: Path = ROOT):
        self.data = data
        self.root = root
        self.sets = {
            name: CaptureSet(name, spec, root)
            for name, spec in data["sets"].items()
        }

    @classmethod
    def load(cls, table: Path = DEFAULT_TABLE, root: Path = ROOT) -> "CaptureCorpus":
        if not table.is_file():
            raise CaptureCorpusError("capture corpus table not found: %s" % table)
        with open(table, encoding="utf-8") as handle:
            data = json.load(handle)
        if "sets" not in data:
            raise CaptureCorpusError("%s has no 'sets' object" % table)
        return cls(data, root)

    def __getitem__(self, name: str) -> CaptureSet:
        try:
            return self.sets[name]
        except KeyError:
            raise CaptureCorpusError(
                "unknown capture set %r (known: %s)"
                % (name, ", ".join(sorted(self.sets)))) from None

    def resolve(self, name: str, verify: bool = True) -> list[Path]:
        return self[name].resolve(verify=verify)

    def assert_no_strays(self, name: str) -> None:
        self[name].assert_no_strays()

    def assert_intact(self, name: str) -> list[Path]:
        """resolve() + assert_no_strays() - the pair a verifier wants."""
        paths = self[name].resolve()
        self[name].assert_no_strays()
        return paths


# --------------------------------------------------------------------------
# regeneration / self-check
# --------------------------------------------------------------------------
def _regenerate(table: Path, root: Path) -> int:
    with open(table, encoding="utf-8") as handle:
        data = json.load(handle)
    for name, spec in data["sets"].items():
        holder = CaptureSet(name, spec, root)
        excluded = set(holder.excluded)
        entries = []
        for rel in holder.scan():
            if rel in excluded:
                continue
            path = root / rel
            entries.append({
                "path": rel,
                "size": path.stat().st_size,
                "sha256": sha256_of(path),
            })
        spec["files"] = entries
        spec["file_count"] = len(entries)
        print("%-24s %4d files" % (name, len(entries)))
    with open(table, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(data, handle, indent=1, ensure_ascii=False)
        handle.write("\n")
    print("wrote %s" % table)
    return 0


def _check(table: Path, root: Path, as_json: bool) -> int:
    corpus = CaptureCorpus.load(table, root)
    report = {}
    failed = False
    for name, holder in sorted(corpus.sets.items()):
        entry = {
            "pinned": len(holder),
            "excluded": sorted(holder.excluded),
            "scan_matches": len(holder.scan()),
            "strays": holder.strays(),
            "vanished": holder.vanished(),
            "drift": [],
        }
        try:
            holder.resolve()
        except CaptureCorpusError as exc:
            entry["drift"] = str(exc).splitlines()[1:]
        if entry["strays"] or entry["vanished"] or entry["drift"]:
            failed = True
        report[name] = entry
    if as_json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        for name, entry in sorted(report.items()):
            print("%s: %d pinned, %d excluded, %d scan matches"
                  % (name, entry["pinned"], len(entry["excluded"]),
                     entry["scan_matches"]))
            for label in ("strays", "vanished", "drift"):
                for line in entry[label]:
                    print("  %-8s %s" % (label.upper(), line))
        print()
        print("RESULT: %s" % ("corpus DRIFTED" if failed
                              else "corpus intact (exit 0)"))
    return 1 if failed else 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--table", default=str(DEFAULT_TABLE))
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--regenerate", action="store_true",
                        help="re-pin sizes and hashes from what is on disk "
                             "(only for deliberately admitted evidence)")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    table, root = Path(args.table), Path(args.root)
    if args.regenerate:
        return _regenerate(table, root)
    return _check(table, root, args.json)


if __name__ == "__main__":
    sys.exit(main())
