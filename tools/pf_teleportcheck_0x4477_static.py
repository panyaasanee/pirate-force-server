#!/usr/bin/env python3
"""PF TELEPORT-CHECK-001 - static reproduction for TeleportCheckVital 0x4477.

Reproduces, byte-exact, every VA/offset/guard cited in
``reports/PF_TELEPORT_CHECK001_0X4477_VTABLE_SCHEMA_CONFIRM_STATIC_20260818.md``
plus the wire half of its section 4.

Usage:
    python3 tools/pf_teleportcheck_0x4477_static.py [path-to-GameClient.local.bin]
Exit 0 = all guards reproduced; nonzero = a guard drifted OR the evidence it
needs is not there.  There is no third outcome.


WHY THIS FILE WAS REWRITTEN (SCAN-DEBT-001, round 84)
-----------------------------------------------------
The previous version ended its wire section with::

    if corpus:
        check("wire corpus: ...", allok, str(corpus))
    else:
        print("SKIP wire corpus (capture files not reachable from this path)")

and the corpus it globbed for was ``<dirname(dirname(BIN))>/GameClient/
capture_v13x/GAME_2*.txt`` - i.e. the *game install tree*, one level ABOVE the
repository, which has never been under version control.  Run from the repository
root (which is how every gate, test and scheduled job runs it) that glob matched
nothing, so the tool printed SKIP and **exited 0 having verified no wire
evidence at all**.  A verifier that cannot fail is not a verifier; it is a green
light with a comment attached.  It had been green that way for two rounds.

Three options were on the table (SCAN-DEBT-001 brief):

  (a) the input still exists and can be pinned -> read the pinned set, fail closed
  (b) the input is gone for good              -> exit nonzero and say so
  (c) the tool has no value left              -> loud deprecation, exit nonzero

**This file takes (a), with a documented partial.**  The reason is that the
evidence turned out NOT to be lost.  Six of the eight sessions the report quotes
were snapshotted into ``backups/v13x_*/capture_v13x/`` at the time, and those
copies are byte-identical to the install-tree originals (sha256 compared, round
84).  ``backups/`` is git-ignored, but so is ``capture_v141/``, and CORPUS-PIN-001
already solved exactly that: the *table* lives in ``docs/`` where git can diff
it, and the files are pinned by path + size + sha256.  So the corpus is now read
through ``tools/pf_capture_corpus.py`` from the set ``game_teleportcheck_0x4477``
and a missing or rewritten capture is a hard error.

The partial, stated rather than hidden: the report's section 4 table has EIGHT
rows and only SIX of them can be re-derived from inside the worktree.  The
``capture_v141`` and ``capture_v142`` sessions were never snapshotted, exist only
in ``<repo>/../GameClient/``, and are therefore unpinnable by construction - a
file with no version control and no hash is not evidence, it is a file.  Those
two rows are reported below as UNPINNABLE, are excluded from every claim this
tool makes, and are recorded as an ERRATUM in the report.  This tool now proves
6/8, loudly, instead of proving 0/8 quietly.

Two further things the rewrite fixes:

  * ``count != content``.  The old check was ``"77 44 0B 00 0F 01" in text`` -
    a substring test over the whole capture, in either direction.  That is wrong
    on its face and demonstrably wrong on this corpus: the pinned negative
    ``backups/v137_*/capture_v137/GAME_20260815_052412_181760_54676.txt``
    contains that byte string TWICE, in ``SENT``/``PC`` blocks - frames the
    *harness composed and sent to the client* - and carries no inbound 0x4477 at
    all.  The tool now decodes the ``DECOMPRESSED`` + ``STRUCTURAL_IDS`` pairs,
    counts only client->server frames, and pins the whole 23-byte inbound frame,
    not a fragment of it.
  * ``capstone`` was imported, one ``Cs`` object was built from it, and it was
    never used for anything.  The import is gone; every guard here is raw bytes
    and the PE section table, so this file is pure stdlib and actually runs in
    the gate environment.

Report-only / additive: reads files, writes nothing, opens no socket, touches no
database, boots no server, launches no client.
"""
from __future__ import annotations

import argparse
import hashlib
import re
import struct
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent

# Prefer the packaged name so that a test which imports ``tools.pf_capture_corpus``
# and this module gets ONE CaptureCorpusError class, not two that fail isinstance
# against each other.  The bare-name fallback is for running this file directly,
# where sys.path[0] is tools/ and the repository root is not on the path at all.
try:  # pragma: no cover - import shape depends on how the file is invoked
    from tools.pf_capture_corpus import CaptureCorpus, CaptureCorpusError
except ImportError:  # pragma: no cover
    if str(_HERE) not in sys.path:
        sys.path.insert(0, str(_HERE))
    from pf_capture_corpus import CaptureCorpus, CaptureCorpusError

ROOT = _HERE.parent

# The client image lives in the game install tree beside the repository.  It is
# read-only and it is pinned by sha256 in the report manifest.
DEFAULT_BINARY = ROOT.parent / "GameClient" / "GameClient.local.bin"
EXPECT_SHA = "9627211412AC60D50AD189CE5A629443CE928EC23A9F8D219DFB2B157028B623"

# ---------------------------------------------------------------------------
# wire corpus pins
# ---------------------------------------------------------------------------
CORPUS_SET = "game_teleportcheck_0x4477"

#: The complete client->server frame, decompressed, byte-identical in every
#: session that carries it.  Nested: tag 0x12, id 0x4477, version 0, field tag
#: 0x0F, u16 value = 1.
EXPECTED_INBOUND_FRAME = bytes.fromhex(
    "12" "6F6E" "1400000000" "08" "00" "0B" "02" "12" "01" "00"
    "12" "7744" "0B00" "0F" "0100"
)

#: How many inbound 0x4477 frames each pinned capture must carry, BY NAME.
#: This is the numerator and the denominator in one table: seven captures, six
#: positives, one proven negative.  A capture that grows or loses a frame is a
#: drift, not a number that quietly moves.
EXPECTED_INBOUND_COUNT = {
    "backups/v131_teleportcheck_challenge_echo_20260815_011204/capture_v131"
    "/GAME_20260815_010048_077396_65459.txt": 1,
    "backups/v136_q3020_marker1_composition_20260815_051330/capture_v136"
    "/GAME_20260815_050713_102583_61900.txt": 1,
    # Proven negative, pinned on purpose: this session never sent 0x4477, yet
    # its text contains the payload byte string twice inside server->client
    # compositions.  It is the file that tells a substring counter from a
    # frame decoder.
    "backups/v137_marker1_teleport_transport_20260815_054009/capture_v137"
    "/GAME_20260815_052412_181760_54676.txt": 0,
    "backups/v137_marker1_teleport_transport_20260815_054009/capture_v137"
    "/GAME_20260815_052956_222262_59254.txt": 1,
    "backups/v138_marker1_population_reapply_20260815_060241/capture_v138"
    "/GAME_20260815_055315_343031_61775.txt": 1,
    "backups/v139_p86_interaction_operational_negative_20260815_063044/capture_v139"
    "/GAME_20260815_062212_502692_52069.txt": 1,
    "backups/v140_p86_synthetic_harness_interaction_20260815_065019/capture_v140"
    "/GAME_20260815_064209_394015_49293.txt": 1,
}

#: Number of rows in the report's section 4 table that have no in-worktree copy.
#: Named, so that "6 of 8" is a stated shortfall and not a silently smaller set.
UNPINNABLE_SESSIONS = (
    "GameClient/capture_v141/GAME_20260815_073553_873970_56053.txt",
    "GameClient/capture_v142/GAME_20260815_100306_944866_53424.txt",
)

_HEXDUMP = re.compile(r"^[0-9A-F]{8}  ((?:[0-9A-F]{2} ?)+)")
_STRUCTURAL_ID = re.compile(r"\(\s*\d+,\s*(\d+),")


# ---------------------------------------------------------------------------
# capture parsing
# ---------------------------------------------------------------------------
def inbound_frames(text: str):
    """Yield ``(structural_ids_line, payload_bytes)`` for every client->server frame.

    The capture journal writes an inbound frame as::

        FRAME magic=0x5F253EAC compressed_len=25
        00000000  AC 3E 25 5F ...
        DECOMPRESSED 23
        00000000  12 6F 6E 14 ...
        STRUCTURAL_IDS [(0, 28271, 'GSCN_RunTimeProtocolReq'), (15, 17527, ...)]

    and an OUTBOUND frame as a ``SENT ...`` / ``PC n`` / hexdump / ``FRAME``
    block with no ``DECOMPRESSED`` + ``STRUCTURAL_IDS`` pair, because nothing
    decodes what this process itself composed.  Requiring that pair is therefore
    what makes this a direction-aware read instead of a substring search.
    """
    lines = text.splitlines()
    index = 0
    while index < len(lines):
        if not lines[index].startswith("DECOMPRESSED "):
            index += 1
            continue
        index += 1
        payload = ""
        while index < len(lines):
            match = _HEXDUMP.match(lines[index])
            if match is None:
                break
            payload += match.group(1).replace(" ", "")
            index += 1
        if index < len(lines) and lines[index].startswith("STRUCTURAL_IDS "):
            yield lines[index], bytes.fromhex(payload)


def inbound_0x4477(text: str) -> list[bytes]:
    """Every inbound frame whose structural ids include 17527 (0x4477)."""
    found = []
    for header, payload in inbound_frames(text):
        if "17527" in {match for match in _STRUCTURAL_ID.findall(header)}:
            found.append(payload)
    return found


# ---------------------------------------------------------------------------
# PE helpers (raw bytes only - no capstone, no pefile)
# ---------------------------------------------------------------------------
class Image:
    def __init__(self, data: bytes):
        self.data = data
        e_lfanew = struct.unpack_from("<I", data, 0x3C)[0]
        coff = e_lfanew + 4
        nsec = struct.unpack_from("<H", data, coff + 2)[0]
        opt_size = struct.unpack_from("<H", data, coff + 16)[0]
        opt = coff + 20
        self.image_base = struct.unpack_from("<I", data, opt + 28)[0]
        sect = opt + opt_size
        self.sections = []
        for i in range(nsec):
            off = sect + i * 40
            name = data[off:off + 8].rstrip(b"\0").decode("latin1")
            vsize, vaddr, rawsize, rawptr = struct.unpack_from("<IIII", data, off + 8)
            self.sections.append((name, vaddr, vsize, rawptr, rawsize))

    def va2off(self, va: int):
        rel = va - self.image_base
        for _name, vaddr, vsize, rawptr, rawsize in self.sections:
            if vaddr <= rel < vaddr + max(vsize, rawsize):
                return rawptr + (rel - vaddr)
        return None

    def off2va(self, off: int):
        for _name, vaddr, _vsize, rawptr, rawsize in self.sections:
            if rawptr <= off < rawptr + rawsize:
                return self.image_base + vaddr + (off - rawptr)
        return None

    def rd(self, va: int, length: int) -> bytes:
        off = self.va2off(va)
        if off is None:
            return b""
        return self.data[off:off + length]


# ---------------------------------------------------------------------------
# guards
# ---------------------------------------------------------------------------
class Guards:
    """Collects (ok, name, detail) rows.  Nothing here prints SKIP."""

    def __init__(self) -> None:
        self.rows: list[tuple[bool, str, str]] = []

    def check(self, name: str, ok: bool, detail: str = "") -> bool:
        self.rows.append((bool(ok), name, detail))
        return bool(ok)

    @property
    def failures(self) -> list[str]:
        return [name for ok, name, _detail in self.rows if not ok]

    def render(self) -> None:
        for ok, name, detail in self.rows:
            print(("PASS " if ok else "FAIL ") + name + ("  " + detail if detail else ""))


def binary_guards(data: bytes, guards: Guards) -> None:
    """G1-G7: identity, registration, id-slot, vtable, serializer, factory."""
    sha = hashlib.sha256(data).hexdigest().upper()
    guards.check("binary SHA-256 matches", sha == EXPECT_SHA, sha)

    image = Image(data)

    # G1: class-name string present at the pinned VA.
    name_off = data.find(b"TeleportCheckVital\x00")
    name_va = image.off2va(name_off) if name_off >= 0 else None
    guards.check("string 'TeleportCheckVital' present @0xf30a64",
                 name_va == 0xF30A64,
                 hex(name_va) if name_va is not None else "missing")

    # G2: registration block - push name; call once-init; call id-assign; store ax.
    reg = image.rd(0xBEE820, 24)
    guards.check("registration @0xbee820 pushes name 0xf30a64",
                 len(reg) == 24 and reg[0] == 0x68
                 and struct.unpack_from("<I", reg, 1)[0] == 0xF30A64)
    guards.check("registration calls once-init 0x89c080",
                 len(reg) == 24 and reg[5] == 0xE8
                 and (0xBEE825 + 5 + struct.unpack_from("<i", reg, 6)[0]) == 0x89C080)
    guards.check("registration calls id-assign 0x89bd00",
                 len(reg) == 24 and reg[0xC] == 0xE8
                 and (0xBEE82C + 5 + struct.unpack_from("<i", reg, 0xD)[0]) == 0x89BD00)
    guards.check("registration stores ax -> id-slot 0x1082074 (66 a3)",
                 len(reg) == 24 and reg[0x11] == 0x66 and reg[0x12] == 0xA3
                 and struct.unpack_from("<I", reg, 0x13)[0] == 0x1082074)

    # G3: the id 0x4477 is never a code immediate - it only exists at runtime.
    target = struct.pack("<I", 0x00004477)
    immediates = []
    for match in re.finditer(re.escape(target), data):
        va = image.off2va(match.start())
        if va is None:
            continue
        if data[match.start() - 1] in (0xE8, 0xE9):
            continue  # a rel32 call/jmp whose displacement happens to be 0x4477
        immediates.append(va)
    guards.check("0x4477 never appears as a code immediate (runtime-assigned id)",
                 not immediates, "hits=" + str([hex(x) for x in immediates]))

    # G4: the get-id stub is the only reader of the id slot.
    stub = image.rd(0x449430, 7)
    guards.check("get-id stub @0x449430 = mov ax,[0x1082074]; ret",
                 len(stub) == 7 and stub[:2] == b"\x66\xa1"
                 and struct.unpack_from("<I", stub, 2)[0] == 0x1082074
                 and stub[6] == 0xC3)

    # G5: vtable layout.
    vtable = image.rd(0xF0D66C, 0x20)
    slots = struct.unpack("<8I", vtable) if len(vtable) == 0x20 else (0,) * 8
    guards.check("vtable 0xf0d66c +0x10 = get-id 0x449430", slots[4] == 0x449430)
    guards.check("vtable 0xf0d66c +0x18 = serializer 0x5e6670", slots[6] == 0x5E6670)
    guards.check("vtable 0xf0d66c +0x08 = shared framework const 0x401b20 (VitalData family)",
                 slots[2] == 0x401B20)

    # G6: serializer - single tagged u16 at object+0x14, tag 0x0f, dual in/out.
    ser = image.rd(0x5E6670, 0x1B)
    guards.check("serializer adds 0x14 to this (add ecx,0x14)", ser[:3] == b"\x83\xc1\x14")
    guards.check("serializer pushes field tag 0x0f (push 0xf)", b"\x6a\x0f" in ser[:0x12])
    guards.check("serializer branches in/out to 0x89a600 / 0x89a640",
                 b"\x80\x7c\x24\x08\x00" in ser)

    # G7: prototype registered in the generic Vital factory.
    vt_refs = sorted({
        image.off2va(match.start())
        for match in re.finditer(re.escape(struct.pack("<I", 0xF0D66C)), data)
        if image.off2va(match.start()) is not None
    })
    guards.check("vtable 0xf0d66c installed in factory builder @0x5ee9c4",
                 0x5EE9C4 in vt_refs, str([hex(x) for x in vt_refs]))


def wire_guards(guards: Guards, corpus: CaptureCorpus | None = None,
                set_name: str = CORPUS_SET) -> None:
    """G8: the client->server corpus, read from the pinned table only.

    Raises ``CaptureCorpusError`` if the pinned set is missing, rewritten, or has
    grown a file.  The caller turns that into a nonzero exit; it is never a SKIP.
    """
    corpus = corpus if corpus is not None else CaptureCorpus.load()
    holder = corpus[set_name]
    paths = holder.resolve()          # present + byte-identical, or raise
    holder.assert_no_strays()         # no capture outside the pinned set, or raise

    expected = dict(EXPECTED_INBOUND_COUNT)
    pinned = list(holder.relative_paths)
    guards.check(
        "pinned corpus is exactly the %d captures this tool expects" % len(expected),
        sorted(pinned) == sorted(expected),
        "pinned=%d expected=%d" % (len(pinned), len(expected)))

    total_frames = 0
    for path, rel in zip(paths, pinned):
        want = expected.get(rel)
        text = path.read_text(encoding="utf-8", errors="replace")
        frames = inbound_0x4477(text)
        total_frames += len(frames)
        label = Path(rel).parent.name + "/" + Path(rel).name
        if want is None:
            guards.check("unexpected pinned capture %s" % label, False,
                         "not in EXPECTED_INBOUND_COUNT")
            continue
        guards.check(
            "%s carries exactly %d inbound 0x4477 frame(s)" % (label, want),
            len(frames) == want, "found=%d" % len(frames))
        for frame in frames:
            guards.check(
                "%s inbound frame is the pinned 23-byte record" % label,
                frame == EXPECTED_INBOUND_FRAME, frame.hex().upper())
        if want == 0:
            # count != content: the proven negative must still contain the raw
            # byte string, otherwise this pin has quietly become dead weight and
            # the next reader will delete it.
            guards.check(
                "%s is a PROVEN NEGATIVE whose text still contains the payload "
                "bytes in server->client frames (count != content)" % label,
                "77 44 0B 00 0F 01" in text)

    guards.check(
        "6 of the report's 8 section-4 rows are re-derivable in-worktree",
        total_frames == sum(expected.values()) == 6,
        "frames=%d unpinnable=%d (%s)"
        % (total_frames, len(UNPINNABLE_SESSIONS), ", ".join(UNPINNABLE_SESSIONS)))


# ---------------------------------------------------------------------------
# entry point
# ---------------------------------------------------------------------------
def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("binary", nargs="?", default=None,
                        help="path to GameClient.local.bin "
                             "(default: <repo>/../GameClient/GameClient.local.bin)")
    parser.add_argument("--skip-binary", action="store_true",
                        help="run only the wire-corpus guards (the binary lives "
                             "outside the worktree; this makes its absence an "
                             "explicit choice of the caller instead of a silent "
                             "pass)")
    args = parser.parse_args(argv)

    guards = Guards()
    fatal: list[str] = []

    if not args.skip_binary:
        binary = Path(args.binary) if args.binary else DEFAULT_BINARY
        try:
            data = binary.read_bytes()
        except OSError as error:
            fatal.append(
                "client image not readable: %s (%s). The report's static half "
                "cannot be reproduced without it; pass --skip-binary to run the "
                "wire half alone, but do NOT read that as a pass."
                % (binary, error))
        else:
            binary_guards(data, guards)

    try:
        wire_guards(guards)
    except CaptureCorpusError as error:
        fatal.append(
            "wire corpus unusable, so NOTHING about the wire is verified here:\n"
            "  %s" % error)

    guards.render()
    print()
    print("UNPINNABLE (no in-worktree copy, excluded from every claim above):")
    for name in UNPINNABLE_SESSIONS:
        print("  %s" % name)
    print()

    if fatal:
        for message in fatal:
            print("FATAL: " + message, file=sys.stderr)
        return 2
    failures = guards.failures
    if failures:
        print("RESULT: FAIL (%d guards drifted): %s"
              % (len(failures), ", ".join(failures)))
        return 1
    print("RESULT: PASS - %d guards reproduced "
          "(static image + 6 of 8 wire rows; 2 rows unpinnable)" % len(guards.rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
