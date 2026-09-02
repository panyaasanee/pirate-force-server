"""P-3 support: read a GM plug-in DLL's own bytes and name the failure mode.

WHY THIS EXISTS
---------------
P-3 ("the GM button must actually do something when clicked") has, since
RE-104 on 2026-08-27, produced exactly one observation on screen: the button
is visible and the click is silent. RE-164 finally listed the ways a client
can produce that one observation, and the list is the problem -- several
different, unrelated failures look identical from the player's chair:

  1. ``GameMaster.dll`` is not next to the client at all      [GM-IMG-001]
  2. it is there, but ``GetProcAddress("CreateGameMaster")``
     misses because the linker decorated the export           [GM-IMG-001]
  3. it is there and undecorated, but ``LoadLibraryW`` never
     maps it (side-by-side CRT with no embedded manifest,
     error 14001 -- the plug-in README's own triage row)      [GM-IMG-001]
  4. it loads and the export resolves, but slot ``+0x04``
     hands back an empty/NULL key, so the dispatcher
     returns before the factory                               [GM-IMG-002/003/006]
  5. everything above is fine and the gate that stops the
     window is somewhere else entirely (``GMModule_Client
     +0x19``, current-UI key, ...)                            [RE-104, RE-118, RE-126]

Cases 1-3 are decidable from the file on disk, before the game boots. Case 4
is not decidable here (it needs the process). Case 5 is not decidable here
either, and this module says so rather than implying a clean bill of health.

``patches/gm_plugin/build_vs2008.bat`` already checks the export name and the
CRT imports of a FRESH BUILD, on the bridge, with ``dumpbin``. That check
cannot run on:

  * the DLL that is actually installed beside the client (the build directory
    copy and the installed copy are two files, and at most one of them is the
    one under test),
  * a machine without the VC toolchain,
  * this repository's test suite.

and it reads ``dumpbin``'s human-readable text with ``findstr`` word
boundaries, which is a spelling contest, not a parse. This module reads the
PE export directory itself.

EVIDENCE TIER -- READ BEFORE QUOTING THIS MODULE
------------------------------------------------
Everything here is a statement about BYTES IN A FILE. A verdict of
``image_ok`` means "none of the file-level failure modes this module can see
is present in this file". It is NOT evidence that the GM window opens, and it
must never be carried into a milestone claim. The client-observable half of
P-3 needs a person at the screen (the GT ticket asked for in
``notes_to_chief/20260901_2225_LANE-GM-DELIVERY-gamemaster-plugin-source-*``).

The claim "GameMaster.dll is missing from the owner's client install" is, per
RE-164 and this lane's own 21:32 letter, an UNPINNED OPERATIONAL observation
-- not IMAGE/DATA evidence. This module does not settle it and never says it
has: it reports what it found at a path, and whether that path is the one the
client runs from is the reader's fact to establish, not this module's.

WHAT IT DOES NOT DO
-------------------
No disassembly: the ``ret 8`` / ``ret`` / ``ret 4`` epilogue question of
[GM-IMG-012, -006, -014] needs a disassembler. (``build_vs2008.bat`` check 3
greps the whole image for those opcodes and so cannot attribute them to a
particular slot -- do not read this module's silence on the ABI as that check
having covered it. Nothing in this project verifies the per-slot epilogue
today.) This module never writes, never installs, never overwrites; it opens
files read-only.

HOW TO RUN IT (there is no installed package; ``src`` is not on sys.path)
------------------------------------------------------------------------
From the ``pirate-force-server`` checkout root, with ABSOLUTE paths for
anything living in ``pf_bridge`` or in the client install::

    PYTHONPATH=src python -m pirateforce_foundation.gm.plugin_image_check \\
        --dll  C:/pf_bridge/patches/gm_plugin/GameMaster.dll \\
        --client-dir "C:/Program Files/Pirate Force/Client"

On the bridge (cmd.exe) that is ``set PYTHONPATH=src`` first, and quote any
path containing a space -- an unquoted ``C:\\Pirate Force\\Client`` splits and
this tool would then report on ``C:\\Pirate``, which is why a directory that
does not exist gets its own verdict below instead of being folded into
"no plug-in here".
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import hashlib
import struct

# The exact ASCII string the client passes to GetProcAddress [GM-IMG-001].
REQUIRED_EXPORT = "CreateGameMaster"

# The file name the client passes to LoadLibraryW [GM-IMG-001].
PLUGIN_FILE_NAME = "GameMaster.dll"

# A /MD VC9 build imports these by name. NEITHER IS REQUIRED: revision 2 of
# the plug-in allocates the object it returns from the CLIENT's CRT (it walks
# the client's import table to find the module that owns `operator delete`)
# and resolves the wstring constructor dynamically, so a /MT build hands back
# an object from the right heap too. Both are therefore advisory, not
# verdicts -- an earlier revision of this module failed a /MT build outright,
# which would have been a red light for a DLL that works.
ADVISORY_IMPORT_CRT = "msvcr90.dll"
ADVISORY_IMPORT_CXX = "msvcp90.dll"

_IMAGE_FILE_MACHINE_I386 = 0x014C
_IMAGE_FILE_DLL = 0x2000
_PE32_MAGIC = 0x010B
_PE32PLUS_MAGIC = 0x020B
_RT_MANIFEST = 24
# Under RT_MANIFEST the resource id selects who the manifest is FOR: 1 is
# CREATEPROCESS_MANIFEST_RESOURCE_ID (an EXE), 2 is
# ISOLATIONAWARE_MANIFEST_RESOURCE_ID -- the only one a DLL's activation
# context is built from.
_MANIFEST_ID_EXE = 1
_MANIFEST_ID_DLL = 2

# Which rules THIS revision of the module actually enforces, printed on every
# report so a caller can refuse an answer from an older copy of this file.
#
# WHY A CALLER WOULD NEED THAT (pf-adversary, round `b8xrod`, H2):
# `patches/gm_plugin/install.bat` revision 3 decides whether to copy a DLL
# into the owner's client folder from this module's console output, and it
# finds the module by LOOKING FOR A FOLDER -- `%PF_SERVER_REPO%\\src`, then two
# guessed sibling checkouts. Any checkout older than round `selrsl` prints
# `verdict=image_ok` AND exits 0 for a manifest embedded at resource id 1
# (see `test_a_manifest_at_the_exe_id_is_not_a_manifest_for_a_dll`, which says
# so in its own docstring), so the two tokens the batch reads cannot tell a
# module that enforces the id-2 rule from one that does not. This line can:
# an old checkout does not print it at all, and the batch refuses to proceed
# on an answer it cannot attribute.
#
# APPEND-ONLY, and never rename an entry: a reader older than a new rule must
# still find the rule names it knows.
CONSOLE_RULES = ("pe32_dll", "export_exact", "manifest_id2")

_DIRECTORY_EXPORT = 0
_DIRECTORY_IMPORT = 1
_DIRECTORY_RESOURCE = 2

# Verdicts. Order here is the order `inspect_plugin_file` tests them in, but
# no code reads the ordering -- each verdict is decided by an explicit branch.
VERDICT_MISSING = "missing"
VERDICT_NO_SUCH_DIR = "no_such_dir"
VERDICT_UNREADABLE = "unreadable"
VERDICT_NOT_PE = "not_pe"
VERDICT_WRONG_MACHINE = "wrong_machine"
VERDICT_NOT_A_DLL = "not_a_dll"
VERDICT_NO_EXPORTS = "no_exports"
VERDICT_EXPORT_DECORATED = "export_decorated"
VERDICT_EXPORT_FORWARDED = "export_forwarded"
VERDICT_EXPORT_MISSING = "export_missing"
# A DLL that binds the side-by-side CRT without a manifest never loads.
VERDICT_MANIFEST_MISSING = "manifest_missing"
VERDICT_IMAGE_OK = "image_ok"


class PluginImageError(Exception):
    """The bytes are not a PE32 image this module can read.

    Carries the verdict it maps to, so callers never re-derive it from the
    message text.
    """

    def __init__(self, verdict: str, detail: str) -> None:
        super().__init__(detail)
        self.verdict = verdict
        self.detail = detail


@dataclass(frozen=True)
class PeFacts:
    """Only the fields P-3 turns on. Not a general-purpose PE model."""

    machine: int
    is_dll: bool
    is_pe32: bool
    exports: tuple[str, ...]
    forwarded_exports: tuple[str, ...]
    imports: tuple[str, ...]
    has_embedded_manifest: bool
    # Every id filed under RT_MANIFEST. Kept beside the bool because
    # "a manifest, at the wrong id" and "no manifest at all" need different
    # instructions on screen, and the tester cannot see the difference.
    manifest_resource_ids: tuple[int, ...] = ()
    # How many entries under RT_MANIFEST carry a STRING name instead of an
    # id. They can never be id 2, but "there is a manifest here" and "there
    # is no manifest here" are different sentences to print (pf-adversary,
    # round `selrsl`, D11).
    manifest_named_resource_count: int = 0

    def imports_lowercase(self) -> tuple[str, ...]:
        return tuple(name.lower() for name in self.imports)


@dataclass(frozen=True)
class PluginImageReport:
    """What one file on disk says about the look-alike failures.

    `verdict` is the first blocking problem found; `problems` lists EVERY
    blocking problem, because a tester with one attended session should not
    have to discover them one rebuild at a time.
    """

    path: str
    exists: bool
    verdict: str
    detail: str
    size_bytes: int = 0
    sha256: str = ""
    pe: PeFacts | None = None
    advisories: tuple[str, ...] = field(default_factory=tuple)
    problems: tuple[str, ...] = field(default_factory=tuple)

    @property
    def ok(self) -> bool:
        return self.verdict == VERDICT_IMAGE_OK


def _u16(data: bytes, offset: int) -> int:
    _need(data, offset, 2)
    return struct.unpack_from("<H", data, offset)[0]


def _u32(data: bytes, offset: int) -> int:
    _need(data, offset, 4)
    return struct.unpack_from("<I", data, offset)[0]


def _need(data: bytes, offset: int, length: int) -> None:
    if offset < 0 or length < 0 or offset + length > len(data):
        raise PluginImageError(
            VERDICT_NOT_PE,
            "truncated image: wanted %d byte(s) at 0x%X, file is %d byte(s)"
            % (length, offset, len(data)),
        )


def _cstring(data: bytes, offset: int, limit: int = 512) -> str:
    """Read a NUL-terminated name as ASCII, escaping anything that is not.

    `backslashreplace`, not `replace`: U+FFFD has no cp874 mapping, so a
    corrupt or packed DLL whose export names carry high bytes would kill this
    tool inside `print()` on the bridge console -- after two lines of output
    and before any verdict. Escapes stay printable in every code page.
    """
    if offset < 0 or offset >= len(data):
        raise PluginImageError(
            VERDICT_NOT_PE, "string offset 0x%X is outside the file" % offset
        )
    end = data.find(b"\x00", offset, min(offset + limit, len(data)))
    if end < 0:
        raise PluginImageError(
            VERDICT_NOT_PE, "unterminated string at 0x%X" % offset
        )
    return data[offset:end].decode("ascii", errors="backslashreplace")


@dataclass(frozen=True)
class _Section:
    virtual_address: int
    virtual_size: int
    raw_pointer: int
    raw_size: int


def _rva_to_offset(sections: tuple[_Section, ...], rva: int) -> int:
    """Map an RVA to a file offset, or raise.

    A section is matched on the larger of its two sizes (a linker may pad the
    raw bytes past VirtualSize, or leave an uninitialised tail past
    SizeOfRawData -- both are ordinary), but the bytes are only readable
    inside SizeOfRawData. Anything past that has no file offset at all, and
    returning one would silently read the NEXT section's bytes: `_need` bounds
    the file, not the section, so it cannot catch that.
    """
    for section in sections:
        span = max(section.virtual_size, section.raw_size)
        if section.virtual_address <= rva < section.virtual_address + span:
            delta = rva - section.virtual_address
            if section.raw_size and delta >= section.raw_size:
                raise PluginImageError(
                    VERDICT_NOT_PE,
                    "RVA 0x%X falls in the uninitialised tail of the section "
                    "at 0x%X -- it has no bytes in the file"
                    % (rva, section.virtual_address),
                )
            return section.raw_pointer + delta
    raise PluginImageError(
        VERDICT_NOT_PE, "RVA 0x%X is not inside any section" % rva
    )


def read_pe_facts(data: bytes) -> PeFacts:
    """Parse just enough of a PE32 image to answer P-3's questions.

    Raises PluginImageError (carrying its own verdict) on anything malformed.
    """
    if len(data) < 0x40 or data[:2] != b"MZ":
        raise PluginImageError(VERDICT_NOT_PE, "no MZ signature")
    pe_offset = _u32(data, 0x3C)
    _need(data, pe_offset, 24)
    if data[pe_offset : pe_offset + 4] != b"PE\x00\x00":
        raise PluginImageError(
            VERDICT_NOT_PE, "no PE signature at e_lfanew 0x%X" % pe_offset
        )

    coff = pe_offset + 4
    machine = _u16(data, coff + 0)
    section_count = _u16(data, coff + 2)
    optional_size = _u16(data, coff + 16)
    characteristics = _u16(data, coff + 18)

    optional = coff + 20
    magic = _u16(data, optional)
    is_pe32 = magic == _PE32_MAGIC
    if magic not in (_PE32_MAGIC, _PE32PLUS_MAGIC):
        raise PluginImageError(
            VERDICT_NOT_PE, "unknown optional header magic 0x%04X" % magic
        )
    # NumberOfRvaAndSizes sits at a different offset in the two layouts, and
    # the directory array follows it in both.
    dir_count_offset = optional + (92 if is_pe32 else 108)
    directories_offset = dir_count_offset + 4
    directory_count = _u32(data, dir_count_offset)

    sections_offset = optional + optional_size
    sections: list[_Section] = []
    for index in range(section_count):
        header = sections_offset + index * 40
        _need(data, header, 40)
        sections.append(
            _Section(
                virtual_size=_u32(data, header + 8),
                virtual_address=_u32(data, header + 12),
                raw_size=_u32(data, header + 16),
                raw_pointer=_u32(data, header + 20),
            )
        )
    frozen_sections = tuple(sections)

    exports, forwarded = _read_exports(
        data, frozen_sections, directories_offset, directory_count
    )
    imports = _read_imports(data, frozen_sections, directories_offset, directory_count)
    manifest_ids, manifest_named = _manifest_resource_ids(
        data, frozen_sections, directories_offset, directory_count
    )

    return PeFacts(
        machine=machine,
        is_dll=bool(characteristics & _IMAGE_FILE_DLL),
        is_pe32=is_pe32,
        exports=exports,
        forwarded_exports=forwarded,
        imports=imports,
        has_embedded_manifest=_MANIFEST_ID_DLL in manifest_ids,
        manifest_resource_ids=manifest_ids,
        manifest_named_resource_count=manifest_named,
    )


def _directory(
    data: bytes, directories_offset: int, directory_count: int, index: int
) -> tuple[int, int]:
    """(rva, size) of one data directory; (0, 0) when the image has none.

    NumberOfRvaAndSizes is genuinely variable (16 is a convention, not a
    rule): reading past it would parse whatever follows the header as a
    directory entry.
    """
    if index >= directory_count:
        return (0, 0)
    entry = directories_offset + index * 8
    return (_u32(data, entry), _u32(data, entry + 4))


def _read_exports(
    data: bytes,
    sections: tuple[_Section, ...],
    directories_offset: int,
    directory_count: int,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """(named exports, of which these are forwarders).

    A forwarder is a name whose function RVA points back INSIDE the export
    directory (the bytes there are "OTHERDLL.Symbol", not code). It is
    byte-identical to a real export in the name table, and GetProcAddress
    returns NULL for it when the forward target cannot be resolved -- so it
    has to be told apart here or `image_ok` would cover it.
    """
    rva, size = _directory(data, directories_offset, directory_count, _DIRECTORY_EXPORT)
    if rva == 0:
        return ((), ())
    table = _rva_to_offset(sections, rva)
    _need(data, table, 40)
    function_count = _u32(data, table + 20)
    name_count = _u32(data, table + 24)
    functions_rva = _u32(data, table + 28)
    names_rva = _u32(data, table + 32)
    ordinals_rva = _u32(data, table + 36)
    if name_count == 0 or names_rva == 0:
        # Exports by ordinal only. GetProcAddress by name cannot hit them, so
        # for this module's purpose that is the same as "no named exports".
        return ((), ())
    # A name count larger than the file cannot be honest; refuse rather than
    # spending minutes walking a bogus loop.
    if name_count > len(data):
        raise PluginImageError(
            VERDICT_NOT_PE,
            "export name count %d exceeds file size %d" % (name_count, len(data)),
        )
    names_offset = _rva_to_offset(sections, names_rva)
    ordinals_offset = (
        _rva_to_offset(sections, ordinals_rva) if ordinals_rva else 0
    )
    functions_offset = (
        _rva_to_offset(sections, functions_rva) if functions_rva else 0
    )

    found: list[str] = []
    forwarded: list[str] = []
    for index in range(name_count):
        name_rva = _u32(data, names_offset + index * 4)
        name = _cstring(data, _rva_to_offset(sections, name_rva))
        found.append(name)
        if not (ordinals_offset and functions_offset and size):
            continue
        ordinal = _u16(data, ordinals_offset + index * 2)
        if ordinal >= function_count:
            # The name/ordinal tables disagree; GetProcAddress would read the
            # same garbage. Report it as a forwarder-class problem rather than
            # blessing the name.
            forwarded.append(name)
            continue
        function_rva = _u32(data, functions_offset + ordinal * 4)
        if rva <= function_rva < rva + size:
            forwarded.append(name)
    return (tuple(found), tuple(forwarded))


def _read_imports(
    data: bytes,
    sections: tuple[_Section, ...],
    directories_offset: int,
    directory_count: int,
) -> tuple[str, ...]:
    rva, _size = _directory(data, directories_offset, directory_count, _DIRECTORY_IMPORT)
    if rva == 0:
        return ()
    table = _rva_to_offset(sections, rva)
    found: list[str] = []
    index = 0
    while True:
        descriptor = table + index * 20
        _need(data, descriptor, 20)
        fields = struct.unpack_from("<IIIII", data, descriptor)
        if not any(fields):
            break
        name_rva = fields[3]
        if name_rva:
            found.append(_cstring(data, _rva_to_offset(sections, name_rva)))
        index += 1
        if index > 4096:
            raise PluginImageError(
                VERDICT_NOT_PE, "import descriptor table is not terminated"
            )
    return tuple(found)


def _manifest_resource_ids(
    data: bytes,
    sections: tuple[_Section, ...],
    directories_offset: int,
    directory_count: int,
) -> tuple[tuple[int, ...], int]:
    """`(ids under RT_MANIFEST, how many of them are string-named)`.

    A /MD VC9 build binds to the MSVCR90 side-by-side assembly, and without
    the manifest the loader answers LoadLibraryW with 14001 and the plug-in
    never runs a single instruction -- indistinguishable on screen from the
    DLL not being there at all.

    ~~"build_vs2008.bat never invokes mt.exe and install.bat copies one file,
    so this is a live failure mode for this package"~~ -- STRUCK as of round
    `hj2cry`: `pf_bridge/patches/gm_plugin/build_vs2008.bat` revision 5 embeds
    the manifest and `install.bat` refuses to copy a DLL without one
    (COO-DECISION `20260902_1948` item 2, from ka1-A's attended measurement of
    exactly the failure this function names).  It was live for every build
    that script made before that round, which is why the check exists at all
    and why it stays.

    ~~"IT ANSWERS 'AN RT_MANIFEST EXISTS', NOT 'THE ONE THE LOADER READS'"~~
    -- STRUCK as of round `selrsl`: this function returns the ids, and
    `inspect_plugin_file` requires id 2.  A manifest hand-embedded at id 1 --
    the EXE id, an easy slip when someone runs
    `mt.exe -outputresource:GameMaster.dll;1` -- used to report `image_ok`
    here.  Tightened under COO-DECISION `20260902_2147` item 2.

    !! THE ID-2 RULE ITSELF IS UNMEASURED ON THIS PROJECT, and pf-adversary
    (round `selrsl`, D5) is right to say so: nobody here has handed a Windows
    loader a DLL whose manifest sits at id 1 and watched what it does.  What
    IS measured is the other side -- the DLL ka1-A got to load in attended
    `GT-207` was embedded with `-outputresource:GameMaster.dll;#2`.  The
    reason this ships as a blocking verdict rather than an advisory is the
    cost of being wrong in each direction, and it is asymmetric: the remedy
    this verdict prints (re-embed at `;#2`) is the CORRECT thing to do for a
    DLL whether or not the loader would also have accepted id 1, and it costs
    one `mt.exe` invocation -- while the false GREEN it replaces cost an
    attended round already (ka1-A's 14001).  THE NEGATIVE CONTROL THAT WOULD
    REFUTE IT, stated so it can be run: build one DLL embedded at `;#1`, load
    it on the owner's machine, and see whether `LoadLibraryW` succeeds.  If it
    does, this rule is wrong and the wrong-id case must drop to an advisory.
    Asked in `notes_to_chief/20260902_2252_LANE-GM-ASK-COO-id-2-*`.

    !! IT READS THE RESOURCE TREE, NOT THE MANIFEST TEXT.  An id-2 entry
    whose XML names the wrong assembly version still reads as present.  No
    round has measured that shape, so no verdict claims it.

    EVERY OFFSET IS BOUNDED BY THE RESOURCE DIRECTORY'S OWN SIZE, not by the
    file length (pf-adversary, round `selrsl`, D4, which built a DLL whose
    type-24 entry pointed into `.data` at a planted 16-byte table and got
    `image_ok` with no manifest anywhere in the image).  `_need` bounds the
    FILE, so it cannot catch that -- the same trap `_rva_to_offset`'s own
    docstring names.  An offset that leaves the directory is not a manifest.
    """
    rva, size = _directory(
        data, directories_offset, directory_count, _DIRECTORY_RESOURCE
    )
    if rva == 0:
        return ((), 0)
    root = _rva_to_offset(sections, rva)
    entries = _resource_table_entries(data, root, 0, size)
    if entries is None:
        # The ROOT table keeps the loud answer it had before this round: a
        # root that does not parse is a statement about the image, not about
        # its manifest.
        raise PluginImageError(
            VERDICT_NOT_PE, "resource directory is malformed or truncated"
        )
    for name_field, offset_field in entries:
        # High bit set = a string name; RT_MANIFEST is an integer id.
        if name_field & 0x80000000 or name_field != _RT_MANIFEST:
            continue
        if not offset_field & 0x80000000:
            # A type entry that points straight at data has no id level at
            # all: mt.exe cannot produce it, and the loader has nothing to
            # match id 2 against, so it counts as no usable manifest.
            continue
        relative = offset_field & 0x7FFFFFFF
        children = _resource_table_entries(data, root + relative, relative, size)
        if children is None:
            # Malformed BELOW the type entry is fail-closed and quiet: the
            # image is still a readable PE, it just has no manifest this
            # module will vouch for.
            return ((), 0)
        ids = tuple(name for name, _child in children if not name & 0x80000000)
        named = sum(1 for name, _child in children if name & 0x80000000)
        return (ids, named)
    return ((), 0)


def _resource_table_entries(
    data: bytes, table: int, offset_in_directory: int, directory_size: int
) -> tuple[tuple[int, int], ...] | None:
    """(Name, OffsetToData) of one IMAGE_RESOURCE_DIRECTORY, or None.

    None means "this is not a table I can trust": it does not fit inside the
    resource data directory, or it claims more entries than any real image
    carries.  The CALLER decides what that means -- loud for the root table,
    fail-closed for anything under it -- because the two answers are about
    different things.
    """
    # Two bounds, and each one is the only thing standing between a hostile
    # offset and a wrong answer -- so each is killable on its own by a test.
    # The FILE bound guards the read itself; the DIRECTORY bound (below,
    # after the header names the size) is the one that answers pf-adversary's
    # planted table in `.data` (round `selrsl`, D4). A third "header fits in
    # the directory" pre-check used to sit here: it could never fire without
    # the span bound firing too, so it was removed rather than left as
    # unkillable cover.
    if offset_in_directory < 0 or table < 0 or table + 16 > len(data):
        return None
    named = _u16(data, table + 12)
    by_id = _u16(data, table + 14)
    total = named + by_id
    # No separate "claims too many entries" bound: `total` is two u16 fields,
    # so the two span checks below subsume it exactly. A bound-shaped check
    # that can never fire is worse than none -- a reader asking "is this
    # offset bounded?" finds it and stops looking (pf-adversary, round
    # `selrsl`, D7, about the dead `table < root` check this replaced).
    span = 16 + total * 8
    if offset_in_directory + span > directory_size:
        return None
    if table + span > len(data):
        return None
    entries = []
    for index in range(total):
        entry = table + 16 + index * 8
        entries.append((_u32(data, entry), _u32(data, entry + 4)))
    return tuple(entries)


def _decorated_spellings(exports: tuple[str, ...]) -> tuple[str, ...]:
    """Near-misses that make GetProcAddress return NULL [GM-IMG-001/002].

    Covers the three the linker produces from a missing .def
    (`_CreateGameMaster`, `CreateGameMaster@0`, both) and the one a missing
    `extern "C"` produces (`?CreateGameMaster@@YAPAXXZ` and friends).
    """
    hits = []
    for name in exports:
        if name == REQUIRED_EXPORT:
            continue
        bare = name.lstrip("_")
        if bare == REQUIRED_EXPORT:
            hits.append(name)
            continue
        if "@" in bare and bare.split("@", 1)[0] == REQUIRED_EXPORT:
            hits.append(name)
            continue
        # MSVC C++ mangling: '?' + name + '@@' + signature.
        if name.startswith("?") and name[1:].split("@@", 1)[0] == REQUIRED_EXPORT:
            hits.append(name)
    return tuple(hits)


def inspect_plugin_file(path: str | Path) -> PluginImageReport:
    """Read one candidate GameMaster.dll and name its failure mode."""
    file_path = Path(path)
    text_path = str(file_path)
    if not file_path.is_file():
        return PluginImageReport(
            path=text_path,
            exists=False,
            verdict=VERDICT_MISSING,
            detail=(
                "no readable file at this path (check the path itself before "
                "concluding anything about the client: a mistyped or "
                "space-split path reaches this same line)"
            ),
            problems=("no file at %s" % text_path,),
        )
    try:
        data = file_path.read_bytes()
    except OSError as error:
        return PluginImageReport(
            path=text_path,
            exists=True,
            verdict=VERDICT_UNREADABLE,
            detail="cannot read the file: %s" % error,
            problems=("unreadable: %s" % error,),
        )

    digest = hashlib.sha256(data).hexdigest()
    try:
        pe = read_pe_facts(data)
    except PluginImageError as error:
        return PluginImageReport(
            path=text_path,
            exists=True,
            verdict=error.verdict,
            detail=error.detail,
            size_bytes=len(data),
            sha256=digest,
            problems=(error.detail,),
        )

    problems: list[str] = []
    advisories: list[str] = []

    if pe.machine != _IMAGE_FILE_MACHINE_I386 or not pe.is_pe32:
        problems.append(
            "machine 0x%04X / %s -- the client is a 32-bit process and cannot "
            "load this" % (pe.machine, "PE32" if pe.is_pe32 else "PE32+")
        )
        first = VERDICT_WRONG_MACHINE
    else:
        first = ""
    if not pe.is_dll:
        problems.append("IMAGE_FILE_DLL is not set in the COFF characteristics")
        first = first or VERDICT_NOT_A_DLL
    if not pe.exports:
        problems.append(
            "the export directory names nothing -- GetProcAddress by name "
            "cannot succeed"
        )
        first = first or VERDICT_NO_EXPORTS
    elif REQUIRED_EXPORT in pe.forwarded_exports:
        problems.append(
            "%s is a forwarder, not code in this image -- GetProcAddress "
            "returns NULL unless the forward target resolves" % REQUIRED_EXPORT
        )
        first = first or VERDICT_EXPORT_FORWARDED
    elif REQUIRED_EXPORT not in pe.exports:
        decorated = _decorated_spellings(pe.exports)
        if decorated:
            problems.append(
                "exports %s but not the exact name %s -- GetProcAddress "
                "returns NULL and the on-screen result is identical to the "
                "bug this plug-in exists to fix"
                % (", ".join(decorated), REQUIRED_EXPORT)
            )
            first = first or VERDICT_EXPORT_DECORATED
        else:
            problems.append(
                "no export named %s (exports: %s)"
                % (REQUIRED_EXPORT, ", ".join(pe.exports) or "<none>")
            )
            first = first or VERDICT_EXPORT_MISSING

    lowered = pe.imports_lowercase()
    if ADVISORY_IMPORT_CRT in lowered and not pe.has_embedded_manifest:
        # A side-by-side CRT binding with no manifest the loader will read:
        # it refuses the module (14001) and nothing this plug-in does ever
        # runs. Same verdict either way -- the DLL does not load -- but the
        # two shapes need different next steps, so they say different things.
        if pe.manifest_resource_ids or pe.manifest_named_resource_count:
            where = ", ".join(str(one) for one in pe.manifest_resource_ids)
            if pe.manifest_named_resource_count:
                # A string-named entry cannot be id 2 and cannot be what the
                # loader reads, but saying "no manifest" about an image that
                # visibly carries one sends the reader looking in the wrong
                # place (pf-adversary, round `selrsl`, D11).
                named = "%d string-named entr%s" % (
                    pe.manifest_named_resource_count,
                    "y" if pe.manifest_named_resource_count == 1 else "ies",
                )
                where = "%s, %s" % (where, named) if where else named
            problems.append(
                "imports %s and carries an RT_MANIFEST at resource id %s, but "
                "a DLL's activation context is built from id %d alone -- the "
                "side-by-side loader answers LoadLibraryW with 14001 exactly "
                "as if there were no manifest. Re-embed with "
                "`mt.exe -manifest GameMaster.dll.manifest "
                "-outputresource:GameMaster.dll;#%d` (note the ;#%d, not ;#%d)"
                % (
                    ADVISORY_IMPORT_CRT,
                    where,
                    _MANIFEST_ID_DLL,
                    _MANIFEST_ID_DLL,
                    _MANIFEST_ID_DLL,
                    _MANIFEST_ID_EXE,
                )
            )
        else:
            problems.append(
                "imports %s but carries no embedded RT_MANIFEST -- the "
                "side-by-side loader answers LoadLibraryW with 14001 and the "
                "plug-in never runs. Rebuild with build_vs2008.bat revision 5 "
                "or later, which calls mt.exe and embeds at ;#%d"
                % (ADVISORY_IMPORT_CRT, _MANIFEST_ID_DLL)
            )
        first = first or VERDICT_MANIFEST_MISSING
    if ADVISORY_IMPORT_CRT not in lowered:
        advisories.append(
            "does not import %s: not a /MD VC9 build. Revision 2 allocates "
            "the returned object from the CLIENT's CRT, so this is not by "
            "itself wrong -- read the plug-in's own [GM_PLUGIN] line to see "
            "which CRT it bound to at run time" % ADVISORY_IMPORT_CRT
        )
    if ADVISORY_IMPORT_CXX not in lowered:
        advisories.append(
            "%s is not imported; revision 2 resolves the wstring constructor "
            "dynamically, so this is not fatal by itself" % ADVISORY_IMPORT_CXX
        )

    verdict = first or VERDICT_IMAGE_OK
    if verdict == VERDICT_IMAGE_OK:
        detail = (
            "PE32 DLL exporting %s exactly -- none of the file-level failure "
            "modes this module can see is present in these bytes"
            % REQUIRED_EXPORT
        )
    else:
        detail = problems[0]
    return PluginImageReport(
        path=text_path,
        exists=True,
        verdict=verdict,
        detail=detail,
        size_bytes=len(data),
        sha256=digest,
        pe=pe,
        advisories=tuple(advisories),
        problems=tuple(problems),
    )



def find_installed_plugin(client_dir: str | Path) -> Path | None:
    """Locate GameMaster.dll in a client directory, case-insensitively.

    Windows opens ``gamemaster.dll`` and ``GameMaster.dll`` as the same file;
    a Linux clone does not. Matching case-insensitively here keeps one answer
    on both, which matters because the report travels between them.
    """
    directory = Path(client_dir)
    if not directory.is_dir():
        return None
    wanted = PLUGIN_FILE_NAME.lower()
    exact = directory / PLUGIN_FILE_NAME
    if exact.is_file():
        return exact
    for entry in sorted(directory.iterdir()):
        if entry.is_file() and entry.name.lower() == wanted:
            return entry
    return None


def inspect_client_install(client_dir: str | Path) -> PluginImageReport:
    """Answer 'is the plug-in in THIS directory, and is it well formed'.

    A directory that does not exist gets its own verdict. Folding it into
    "no plug-in here" is how a mistyped or unquoted path turns into a
    statement about the client install -- and the RE-164 note this feeds is
    exactly the kind of claim that must not be manufactured by a typo.
    """
    directory = Path(client_dir)
    if not directory.is_dir():
        return PluginImageReport(
            path=str(directory),
            exists=False,
            verdict=VERDICT_NO_SUCH_DIR,
            detail=(
                "this directory does not exist (or is not a directory) -- "
                "this says NOTHING about the client install; fix the path and "
                "run again"
            ),
            problems=("no such directory: %s" % directory,),
        )
    installed = find_installed_plugin(directory)
    if installed is None:
        return PluginImageReport(
            path=str(directory / PLUGIN_FILE_NAME),
            exists=False,
            verdict=VERDICT_MISSING,
            detail=(
                "the directory exists and holds no %s. If this is the "
                "directory the client runs from, that is the state RE-164's "
                "operational note describes -- establishing that it IS that "
                "directory is the reader's job, not this tool's"
                % PLUGIN_FILE_NAME
            ),
            problems=("no %s in %s" % (PLUGIN_FILE_NAME, directory),),
        )
    return inspect_plugin_file(installed)


def same_bytes(left: PluginImageReport, right: PluginImageReport) -> bool:
    """True when both reports read a file and the two files are identical.

    The build script prints a sha256 for exactly one reason: a rebuild whose
    flag never reached the compiler produces a byte-identical DLL, and the
    tester then re-tests yesterday's binary and records a new-looking result.
    This is that comparison for the installed copy.
    """
    if not left.sha256 or not right.sha256:
        return False
    return left.sha256 == right.sha256


def _console_safe(line: str) -> str:
    """Escape anything a cp874 console cannot encode.

    !! THIS IS A FALSE-GREEN FIX, not tidiness (pf-adversary, round `b8xrod`,
    M1).  `path=` is the ONLY field on these lines carrying text this module
    did not author, it sits on the VERDICT LINE ITSELF, and `install.bat`
    redirects this output to a file -- which on a Thai Windows makes
    `sys.stdout` a cp874 stream.  One character outside cp874 in the path (an
    accented folder name, a pasted en dash) made `print()` raise
    UnicodeEncodeError on the FIRST line, leaving the batch with a file that
    holds a traceback and no verdict token at all -- which is exactly the
    branch that WARNS AND COPIES.  A DLL could not reach that branch through
    its bytes (50,000 fuzzed images, zero escapes); it reached it through its
    own path.  Escaping here closes it for every caller instead of asking each
    one to remember.
    """
    return line.encode("ascii", "backslashreplace").decode("ascii")


def console_lines(report: PluginImageReport, label: str) -> list[str]:
    """Grep-able console output, one token per line, cp874-safe ASCII."""
    lines = [
        "GM_PLUGIN_IMAGE %s rules=%s" % (label, ",".join(CONSOLE_RULES)),

        "GM_PLUGIN_IMAGE %s verdict=%s path=%s" % (label, report.verdict, report.path)
    ]
    if report.sha256:
        lines.append(
            "GM_PLUGIN_IMAGE %s sha256=%s size=%d"
            % (label, report.sha256, report.size_bytes)
        )
    if report.pe is not None:
        lines.append(
            "GM_PLUGIN_IMAGE %s exports=%s"
            % (label, ",".join(report.pe.exports) or "<none>")
        )
        if report.pe.forwarded_exports:
            lines.append(
                "GM_PLUGIN_IMAGE %s forwarded=%s"
                % (label, ",".join(report.pe.forwarded_exports))
            )
        lines.append(
            "GM_PLUGIN_IMAGE %s imports=%s"
            % (label, ",".join(report.pe.imports) or "<none>")
        )
        lines.append(
            "GM_PLUGIN_IMAGE %s embedded_manifest=%s manifest_ids=%s "
            "manifest_named_ids=%d"
            % (
                label,
                "yes" if report.pe.has_embedded_manifest else "no",
                ",".join(str(one) for one in report.pe.manifest_resource_ids)
                or "none",
                report.pe.manifest_named_resource_count,
            )
        )
    lines.append("GM_PLUGIN_IMAGE %s detail=%s" % (label, report.detail))
    # Every blocking problem, not just the first: one attended session cannot
    # afford to discover them a rebuild at a time.
    for problem in report.problems[1:]:
        lines.append("GM_PLUGIN_IMAGE %s also_problem=%s" % (label, problem))
    for advisory in report.advisories:
        lines.append("GM_PLUGIN_IMAGE %s advisory=%s" % (label, advisory))
    if report.ok:
        lines.append(
            "GM_PLUGIN_IMAGE %s nonclaim=file-level only; this says nothing "
            "about whether the GM window opens, and nothing about whether the "
            "manifest at id 2 CONTAINS a usable assembly reference -- an "
            "empty or wrong-version manifest still answers 14001" % label
        )
    return [_console_safe(line) for line in lines]


def main(argv: list[str] | None = None) -> int:
    """CLI: one command on the bridge, before the game boots.

    See the module docstring for the exact invocation (``PYTHONPATH=src``,
    absolute paths). Exit code 0 only when every path asked about reads
    ``image_ok`` AND every build/install pair compared holds the same bytes.
    """
    import argparse

    parser = argparse.ArgumentParser(
        prog="plugin_image_check",
        description=(
            "Read a GM plug-in DLL and name which of the look-alike P-3 "
            "failures it is. File-level evidence only."
        ),
    )
    parser.add_argument("--dll", action="append", default=[], metavar="PATH")
    parser.add_argument("--client-dir", action="append", default=[], metavar="DIR")
    args = parser.parse_args(argv)

    if not args.dll and not args.client_dir:
        parser.error("give at least one --dll or --client-dir")

    reports: list[tuple[str, PluginImageReport]] = []
    for path in args.dll:
        reports.append(("build", inspect_plugin_file(path)))
    for directory in args.client_dir:
        reports.append(("install", inspect_client_install(directory)))

    for label, report in reports:
        for line in console_lines(report, label):
            print(line)

    builds = [r for label, r in reports if label == "build"]
    installs = [r for label, r in reports if label == "install"]
    mismatched = False
    for build in builds:
        for install in installs:
            if same_bytes(build, install):
                print(
                    "GM_PLUGIN_IMAGE compare same_bytes=yes build=%s install=%s"
                    % (build.path, install.path)
                )
            elif build.sha256 and install.sha256:
                mismatched = True
                print(
                    "GM_PLUGIN_IMAGE compare same_bytes=no build=%s install=%s "
                    "-- these are two different files; at most one of them is "
                    "the DLL your next observation is about (which one the "
                    "loader maps also depends on the DLL search order and on "
                    "any module of that base name already mapped)"
                    % (build.path, install.path)
                )
    if mismatched:
        # Not cosmetic: this is the re-test-yesterday's-binary trap, and a
        # green exit code here is how it goes unnoticed.
        print(
            "GM_PLUGIN_IMAGE compare verdict=stale_install -- install the "
            "build you just made, then run this again"
        )

    every_ok = all(report.ok for _label, report in reports)
    return 0 if (every_ok and not mismatched) else 1


if __name__ == "__main__":  # pragma: no cover - exercised through main()
    raise SystemExit(main())
