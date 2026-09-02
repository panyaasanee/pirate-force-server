"""Tests for gm/plugin_image_check.py -- built on synthetic PE32 images.

WHY SYNTHETIC BYTES AND NOT A REAL DLL
--------------------------------------
This clone has no client image, no GameMaster.dll, and no VC toolchain (see
the lane prompt: "no client image, no capture corpus"). A test that needed a
real DLL could only ever skip here, which is the same as not existing -- the
lane has already lost a round to a test that silently skipped on the machine
that mattered (see test_gm_skipif_argument.py's history).

So the fixtures below assemble PE32 images field by field. That is stricter
than a real DLL would be, not weaker: every failure mode P-3 cares about
(decorated export, forwarded export, missing manifest, PE32+, non-DLL,
truncation) can be produced deliberately, and a real GameMaster.dll can
produce at most one of them per build.

WHAT THE FIRST VERSION OF THIS FILE GOT WRONG (pf-adversary, round `lmqf69`)
---------------------------------------------------------------------------
It emitted ONE section, always with `VirtualSize == SizeOfRawData` and always
16 data directories, so six independent mutations of the parser -- dropping
VirtualSize, dropping SizeOfRawData, only ever looking at the first section,
deleting the ordinal-only guard, deleting the NumberOfRvaAndSizes bound,
deleting the no-import-directory early return -- all passed 30/30. A suite
that cannot fail is not evidence. `_build_pe` now emits three sections by
default, puts the export directory in the SECOND one, gives one section
`VirtualSize < SizeOfRawData` and another `VirtualSize > SizeOfRawData`, and
`directory_count` is a parameter. The mutation table in the round file lists
which test kills which mutant.

Layout produced by _build_pe:
    0x000  DOS header, e_lfanew = 0x80
    0x080  PE signature + COFF header + optional header
    0x???  three section headers: .text (padding), .rdata (all the tables),
           .data (uninitialised tail past its raw size)
    raw    .text at 0x400, .rdata after it, .data after that
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
import struct

import pytest

# Round `kv2vjk`: this module used to import `pirateforce_foundation` with no
# path of its own and got away with it, because SOME alphabetically earlier
# module in `tests/` inserts `src` for the whole session.  That is an ordering
# accident, not a path -- run this file alone and it dies at collection -- and
# a collection error is one of the two ways #611's work has already been lost.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))

from pf_preconditions import BRIDGE_SIBLING  # noqa: E402
from pirateforce_foundation.gm import plugin_image_check as pic  # noqa: E402


_PE_OFFSET = 0x80
_FILE_ALIGN = 0x200


def _resource_blob(
    *,
    type_field: int = pic._RT_MANIFEST,
    ids: tuple[int, ...] = (2,),
    named_ids: int = 0,
    subdirectory: bool = True,
    language_level: bool = True,
    subdir_offset: int | None = None,
    id_entry_count: int | None = None,
    decoy_table: bool = False,
) -> bytes:
    """A resource section shaped the way `mt.exe` actually leaves one.

    THREE levels, not two: type -> id -> LANGUAGE -> data entry. The earlier
    fixture in this file stopped at two and called it "the way a real image
    files a manifest", which pf-adversary (round `selrsl`, D9) measured as
    false -- and a two-level tree is exactly as unproducible by the real
    toolchain as the one-level tree it replaced. Every id-level assertion in
    this suite now stands on the shape `mt.exe -outputresource:...;#2` writes.

    Every offset is RELATIVE TO THE START OF THIS BLOB, which is what the
    resource directory's own offsets mean, so the blob can be placed at any
    RVA. `subdir_offset` and `id_entry_count` exist to build the malformed
    shapes the parser has to refuse (D4, D5-mutant) -- a real linker writes
    neither.
    """
    id_count = len(ids) + named_ids
    root_size = 16 + 8
    id_table_offset = root_size
    id_table_size = 16 + 8 * id_count
    language_offset = id_table_offset + id_table_size
    language_size = (16 + 8) if language_level else 0
    data_offset = language_offset + language_size * id_count

    if subdir_offset is not None:
        type_entry_offset = subdir_offset
    elif subdirectory:
        type_entry_offset = 0x80000000 | id_table_offset
    else:
        type_entry_offset = 0
    root = struct.pack("<IIHHHH", 0, 0, 0, 0, 0, 1) + struct.pack(
        "<II", type_field, type_entry_offset
    )

    id_entries = b""
    for index in range(id_count):
        named = index >= len(ids)
        name_field = (0x80000000 | 0x300) if named else ids[index]
        child = language_offset + language_size * index
        id_entries += struct.pack(
            "<II",
            name_field,
            (0x80000000 | child) if language_level else data_offset + 16 * index,
        )
    id_table = (
        struct.pack(
            "<IIHHHH",
            0,
            0,
            0,
            0,
            named_ids,
            len(ids) if id_entry_count is None else id_entry_count,
        )
        + id_entries
    )

    languages = b""
    if language_level:
        for index in range(id_count):
            languages += struct.pack("<IIHHHH", 0, 0, 0, 0, 0, 1) + struct.pack(
                "<II", 0x409, data_offset + 16 * index
            )

    # IMAGE_RESOURCE_DATA_ENTRY: nothing in this module reads it.
    data_entries = b"\x00" * (16 * id_count)
    blob = root + id_table + languages + data_entries
    if decoy_table:
        # Sixteen bytes that parse as a directory holding one id-2 entry,
        # sitting OUTSIDE the declared resource directory. This is what
        # pf-adversary planted in `.data` (round `selrsl`, D4): follow an
        # unbounded offset to it and the image reads as manifested when it
        # is not. `decoy_offset()` says where it lands.
        blob += struct.pack("<IIHHHH", 0, 0, 0, 0, 0, 1) + struct.pack(
            "<II", 2, 0
        )
    return blob


def _decoy_offset(**kwargs) -> int:
    """Offset of the decoy table inside a blob built with `decoy_table`."""
    return len(_resource_blob(**kwargs))


def _build_pe(
    *,
    exports: tuple[str, ...] = (pic.REQUIRED_EXPORT,),
    forwarders: tuple[str, ...] = (),
    imports: tuple[str, ...] = ("MSVCR90.dll", "MSVCP90.dll", "KERNEL32.dll"),
    machine: int = 0x014C,
    is_dll: bool = True,
    pe32: bool = True,
    with_export_dir: bool = True,
    with_manifest: bool = True,
    manifest_resource_ids: tuple[int, ...] = (2,),
    manifest_named_ids: int = 0,
    manifest_type_field: int = pic._RT_MANIFEST,
    manifest_subdirectory: bool = True,
    manifest_language_level: bool = True,
    manifest_subdir_offset: int | None = None,
    manifest_id_entry_count: int | None = None,
    manifest_decoy_table: bool = False,
    resource_directory_size: int | None = None,
    export_name_count: int | None = None,
    ordinals_rva: int | None = None,
    names_rva_zero: bool = False,
    rdata_virtual_size: int | None = None,
    directory_count: int = 16,
) -> bytes:
    """Assemble a minimal but structurally valid PE32(+) image.

    `forwarders` names exports whose function RVA points back inside the
    export directory -- what a `.def` file's `A = OTHER.B` produces.
    """
    # Sized from the directory count, the way the header actually defines
    # it: with fewer directories the section headers begin right after the
    # last one, so a parser that ignores NumberOfRvaAndSizes reads a
    # section header as a directory entry instead of a convenient zero.
    optional_size = (96 if pe32 else 112) + 8 * directory_count
    text_va, rdata_va, data_va = 0x1000, 0x2000, 0x3000

    body = bytearray()

    def place(payload: bytes, align: int = 4) -> int:
        while len(body) % align:
            body.append(0)
        rva = rdata_va + len(body)
        body.extend(payload)
        return rva

    export_dir_rva = 0
    export_dir_size = 0
    if with_export_dir:
        name_rvas = [place(name.encode("ascii") + b"\x00") for name in exports]
        dll_name_rva = place(b"GameMaster.dll\x00")
        names_array_rva = place(b"".join(struct.pack("<I", r) for r in name_rvas))
        ordinal_array_rva = place(
            b"".join(struct.pack("<H", index) for index in range(len(exports)))
        )
        # Function RVAs: real exports point into .text, forwarders point at a
        # string inside the export directory itself (filled in below).
        functions_placeholder = place(b"\x00" * (4 * len(exports)))
        count = len(exports) if export_name_count is None else export_name_count
        export_dir_rva = place(
            struct.pack(
                "<IIHHIIIIIII",
                0,  # Characteristics
                0,  # TimeDateStamp
                0,  # MajorVersion
                0,  # MinorVersion
                dll_name_rva,
                1,  # Base
                len(exports),  # NumberOfFunctions
                count,  # NumberOfNames
                functions_placeholder,
                0 if names_rva_zero else names_array_rva,
                ordinal_array_rva if ordinals_rva is None else ordinals_rva,
            )
        )
        forward_string_rva = place(b"OTHERDLL.Symbol\x00")
        export_dir_size = (forward_string_rva + 16) - export_dir_rva
        functions_offset = functions_placeholder - rdata_va
        for index, name in enumerate(exports):
            target = forward_string_rva if name in forwarders else text_va + 0x10
            struct.pack_into("<I", body, functions_offset + index * 4, target)

    import_dir_rva = 0
    if imports:
        import_name_rvas = [place(name.encode("ascii") + b"\x00") for name in imports]
        descriptors = b"".join(
            struct.pack("<IIIII", 0, 0, 0, rva, 0) for rva in import_name_rvas
        )
        import_dir_rva = place(descriptors + b"\x00" * 20)

    resource_dir_rva = 0
    resource_dir_size = 0
    if with_manifest:
        blob = _resource_blob(
            type_field=manifest_type_field,
            ids=manifest_resource_ids,
            named_ids=manifest_named_ids,
            subdirectory=manifest_subdirectory,
            language_level=manifest_language_level,
            subdir_offset=manifest_subdir_offset,
            id_entry_count=manifest_id_entry_count,
            decoy_table=manifest_decoy_table,
        )
        resource_dir_rva = place(blob)
        resource_dir_size = (
            len(blob) if resource_directory_size is None else resource_directory_size
        )

    rdata_raw = (len(body) + _FILE_ALIGN - 1) & ~(_FILE_ALIGN - 1) or _FILE_ALIGN
    rdata_body = bytes(body).ljust(rdata_raw, b"\x00")

    text_raw = _FILE_ALIGN
    data_raw = _FILE_ALIGN

    sections = [
        # name, VirtualSize, VA, SizeOfRawData, PointerToRawData
        # .text: VirtualSize SMALLER than raw size (linker padding).
        (b".text\x00\x00\x00", text_raw - 0x40, text_va, text_raw, 0x400),
        (
            b".rdata\x00\x00",
            len(body) if rdata_virtual_size is None else rdata_virtual_size,
            rdata_va,
            rdata_raw,
            0x400 + text_raw,
        ),
        # .data: VirtualSize LARGER than raw size (uninitialised tail).
        (
            b".data\x00\x00\x00",
            data_raw * 4,
            data_va,
            data_raw,
            0x400 + text_raw + rdata_raw,
        ),
    ]

    headers = bytearray(b"\x00" * 0x400)
    headers[0:2] = b"MZ"
    struct.pack_into("<I", headers, 0x3C, _PE_OFFSET)
    struct.pack_into("<4s", headers, _PE_OFFSET, b"PE\x00\x00")
    coff = _PE_OFFSET + 4
    struct.pack_into(
        "<HHIIIHH",
        headers,
        coff,
        machine,
        len(sections),
        0,
        0,
        0,
        optional_size,
        0x2000 if is_dll else 0x0002,
    )
    optional = coff + 20
    struct.pack_into("<H", headers, optional, 0x010B if pe32 else 0x020B)
    dir_count_offset = optional + (92 if pe32 else 108)
    struct.pack_into("<I", headers, dir_count_offset, directory_count)
    directories = dir_count_offset + 4
    if directory_count > pic._DIRECTORY_EXPORT:
        struct.pack_into(
            "<II",
            headers,
            directories + 8 * pic._DIRECTORY_EXPORT,
            export_dir_rva,
            export_dir_size,
        )
    if directory_count > pic._DIRECTORY_IMPORT:
        struct.pack_into(
            "<II",
            headers,
            directories + 8 * pic._DIRECTORY_IMPORT,
            import_dir_rva,
            0x14 if import_dir_rva else 0,
        )
    if directory_count > pic._DIRECTORY_RESOURCE:
        struct.pack_into(
            "<II",
            headers,
            directories + 8 * pic._DIRECTORY_RESOURCE,
            resource_dir_rva,
            resource_dir_size,
        )

    section_headers = optional + optional_size
    for index, (name, vsize, va, raw_size, raw_ptr) in enumerate(sections):
        struct.pack_into(
            "<8sIIII", headers, section_headers + index * 40, name, vsize, va, raw_size, raw_ptr
        )

    return bytes(headers) + b"\x00" * text_raw + rdata_body + b"\x00" * data_raw


def _write(tmp_path: Path, data: bytes, name: str = "GameMaster.dll") -> Path:
    target = tmp_path / name
    target.write_bytes(data)
    return target


# --- the happy path, and what it is careful NOT to claim -------------------


def test_a_well_formed_plugin_reads_image_ok(tmp_path: Path) -> None:
    report = pic.inspect_plugin_file(_write(tmp_path, _build_pe()))

    assert report.verdict == pic.VERDICT_IMAGE_OK
    assert report.ok
    assert report.pe is not None
    assert report.pe.exports == (pic.REQUIRED_EXPORT,)
    assert report.pe.forwarded_exports == ()
    assert "msvcr90.dll" in report.pe.imports_lowercase()
    assert report.pe.has_embedded_manifest
    assert report.advisories == ()
    assert report.problems == ()


def test_the_export_directory_is_not_in_the_first_section(tmp_path: Path) -> None:
    """Kills the "only ever look at sections[0]" mutant.

    A real MSVC DLL puts its export directory in `.rdata`, never in the first
    section, so a parser that only walks sections[0] passes a one-section
    suite and fails on every real build.
    """
    report = pic.inspect_plugin_file(_write(tmp_path, _build_pe()))

    assert report.verdict == pic.VERDICT_IMAGE_OK
    assert report.pe is not None and report.pe.exports == (pic.REQUIRED_EXPORT,)


def test_image_ok_still_prints_the_nonclaim(tmp_path: Path) -> None:
    """`image_ok` must never read as "the GM window works"."""
    report = pic.inspect_plugin_file(_write(tmp_path, _build_pe()))

    lines = pic.console_lines(report, "build")

    assert any("nonclaim=" in line and "says nothing" in line for line in lines)


def test_every_console_line_survives_the_bridge_console(tmp_path: Path) -> None:
    report = pic.inspect_plugin_file(_write(tmp_path, _build_pe()))

    for line in pic.console_lines(report, "build"):
        line.encode("cp874")  # raises UnicodeEncodeError if a glyph has no mapping


def test_a_non_ascii_export_name_does_not_kill_the_report(tmp_path: Path) -> None:
    """A corrupt or packed DLL must not take the tool down mid-report.

    The first version decoded names with errors="replace"; U+FFFD has no
    cp874 mapping, so `print()` raised UnicodeEncodeError after two lines --
    no verdict, no sha256, on the one console that matters.
    """
    # The fixture builder only accepts ASCII names, so plant an encodable
    # placeholder and drop a high byte on it in place.
    image = bytearray(_build_pe(exports=("CreateXameMaster", pic.REQUIRED_EXPORT)))
    index = bytes(image).find(b"CreateXameMaster")
    assert index > 0
    image[index + 6] = 0xE9

    report = pic.inspect_plugin_file(_write(tmp_path, bytes(image)))

    assert report.verdict == pic.VERDICT_IMAGE_OK
    for line in pic.console_lines(report, "build"):
        line.encode("cp874")


# --- the look-alike failures, told apart -----------------------------------


def test_a_missing_file_is_its_own_verdict(tmp_path: Path) -> None:
    report = pic.inspect_plugin_file(tmp_path / "GameMaster.dll")

    assert report.verdict == pic.VERDICT_MISSING
    assert not report.exists
    assert report.sha256 == ""


@pytest.mark.parametrize(
    "decorated",
    [
        "_CreateGameMaster",
        "CreateGameMaster@0",
        "_CreateGameMaster@0",
        "?CreateGameMaster@@YAPAXXZ",
    ],
)
def test_a_decorated_export_is_not_the_export(tmp_path: Path, decorated: str) -> None:
    """The failure the substring check in revision 1 green-lit.

    The C++-mangled spelling is the one a forgotten `extern "C"` produces --
    the likeliest real decoration, and the one the first version of this
    module reported as `export_missing` instead.
    """
    report = pic.inspect_plugin_file(_write(tmp_path, _build_pe(exports=(decorated,))))

    assert report.verdict == pic.VERDICT_EXPORT_DECORATED
    assert decorated in report.detail


def test_a_decorated_twin_next_to_the_real_export_still_passes(tmp_path: Path) -> None:
    """Both spellings exported is fine: GetProcAddress finds the exact one."""
    image = _build_pe(exports=("_CreateGameMaster", pic.REQUIRED_EXPORT))

    assert pic.inspect_plugin_file(_write(tmp_path, image)).verdict == pic.VERDICT_IMAGE_OK


def test_a_forwarded_export_is_not_a_working_export(tmp_path: Path) -> None:
    """`GetProcAddress` returns NULL when the forward target is absent."""
    image = _build_pe(
        exports=(pic.REQUIRED_EXPORT,), forwarders=(pic.REQUIRED_EXPORT,)
    )

    report = pic.inspect_plugin_file(_write(tmp_path, image))

    assert report.verdict == pic.VERDICT_EXPORT_FORWARDED
    assert report.pe is not None
    assert report.pe.forwarded_exports == (pic.REQUIRED_EXPORT,)
    assert any("forwarded=" in line for line in pic.console_lines(report, "build"))


def test_an_unrelated_export_set_is_export_missing(tmp_path: Path) -> None:
    report = pic.inspect_plugin_file(_write(tmp_path, _build_pe(exports=("DllMain",))))

    assert report.verdict == pic.VERDICT_EXPORT_MISSING
    assert "DllMain" in report.detail


def test_no_export_directory_at_all(tmp_path: Path) -> None:
    report = pic.inspect_plugin_file(_write(tmp_path, _build_pe(with_export_dir=False)))

    assert report.verdict == pic.VERDICT_NO_EXPORTS


def test_exports_by_ordinal_only_cannot_be_found_by_name(tmp_path: Path) -> None:
    """Kills the "delete the ordinal-only guard" mutant."""
    image = _build_pe(export_name_count=0)

    assert pic.inspect_plugin_file(_write(tmp_path, image)).verdict == pic.VERDICT_NO_EXPORTS


def test_a_sxs_build_without_a_manifest_never_loads(tmp_path: Path) -> None:
    """Imports MSVCR90, no RT_MANIFEST: LoadLibraryW answers 14001."""
    image = _build_pe(with_manifest=False)

    report = pic.inspect_plugin_file(_write(tmp_path, image))

    assert report.verdict == pic.VERDICT_MANIFEST_MISSING
    assert "14001" in report.detail
    assert report.pe is not None and not report.pe.has_embedded_manifest


def test_a_manifest_at_the_exe_id_is_not_a_manifest_for_a_dll(tmp_path: Path) -> None:
    """The gap pf-adversary reported in `hj2cry` D13, now closed.

    `mt.exe -outputresource:GameMaster.dll;1` writes a real RT_MANIFEST that
    the loader never reads: a DLL's activation context comes from id 2 alone,
    so the module still answers 14001. Before round `selrsl` this reported
    `image_ok` and sent a tester to look for a bug that was not in the code.
    """
    image = _build_pe(manifest_resource_ids=(1,))

    report = pic.inspect_plugin_file(_write(tmp_path, image))

    assert report.verdict == pic.VERDICT_MANIFEST_MISSING
    assert report.pe is not None
    assert not report.pe.has_embedded_manifest
    assert report.pe.manifest_resource_ids == (1,)
    # The tester gets the command that fixes it, not just the diagnosis.
    assert "id 1" in report.detail and ";#2" in report.detail
    # And a log alone tells the two shapes apart -- no file needed.
    assert any(
        "embedded_manifest=no manifest_ids=1" in line
        for line in pic.console_lines(report, "build")
    )


def test_a_manifest_at_both_ids_still_loads(tmp_path: Path) -> None:
    """Kills the "require id 2 to be the ONLY id" mutant.

    Nothing stops an image from carrying both, and the loader reads id 2
    whatever else sits beside it.
    """
    image = _build_pe(manifest_resource_ids=(1, 2))

    report = pic.inspect_plugin_file(_write(tmp_path, image))

    assert report.verdict == pic.VERDICT_IMAGE_OK
    assert report.pe is not None and report.pe.has_embedded_manifest
    # BOTH ids, which is the point: the old body built ONE and asserted one,
    # so the mutant it named (`ids == (2,)` exactly) survived it
    # (pf-adversary, round `selrsl`, D8).
    assert report.pe.manifest_resource_ids == (1, 2)


def test_a_subdirectory_offset_that_leaves_the_resource_directory_is_refused(
    tmp_path: Path,
) -> None:
    """pf-adversary, round `selrsl`, D4 -- measured, not hypothetical.

    The type-24 entry's `OffsetToData` is attacker- or corruption-chosen up
    to 0x7FFFFFFF. Pointed at `.data`, where sixteen bytes happen to parse as
    a directory with an id-2 entry, the first version of this descent
    answered `ids=(2,)` and `image_ok` for an image with no manifest anywhere
    -- the exact false green this round exists to remove, reintroduced by the
    fix for it. Offsets are bounded by the resource directory's own Size now,
    which `_need` (a FILE bound) cannot do.
    """
    # A real, well-formed id-2 table -- planted OUTSIDE the resource
    # directory the header declares, and pointed at by the type entry.
    honest_size = _decoy_offset(language_level=False)
    image = _build_pe(
        manifest_subdir_offset=0x80000000 | honest_size,
        manifest_language_level=False,
        manifest_decoy_table=True,
        resource_directory_size=honest_size,
    )

    report = pic.inspect_plugin_file(_write(tmp_path, image))

    assert report.verdict == pic.VERDICT_MANIFEST_MISSING
    assert report.pe is not None and report.pe.manifest_resource_ids == ()

    # Control: the very same table, INSIDE the declared directory, is read.
    # Without it this test could pass because the decoy is unreadable rather
    # than because the bound refused it.
    honest = _build_pe(manifest_language_level=False)
    control = pic.inspect_plugin_file(_write(tmp_path, honest, "Control.dll"))
    assert control.pe is not None and control.pe.manifest_resource_ids == (2,)


def test_a_subdirectory_offset_past_the_end_of_the_file_is_refused(
    tmp_path: Path,
) -> None:
    """Kills the "drop the file bound" mutant, which is a crash, not a lie.

    The directory Size is read from the header and can say anything: declare
    it enormous and the directory bound stops refusing, so only the file
    bound is left between a 2 GiB offset and `struct.error` out of the
    listener's report.
    """
    image = _build_pe(
        manifest_subdir_offset=0x80000000 | 0x7000000,
        resource_directory_size=0x7FFFFFF0,
    )

    report = pic.inspect_plugin_file(_write(tmp_path, image))

    assert report.verdict == pic.VERDICT_MANIFEST_MISSING
    assert report.pe is not None and report.pe.manifest_resource_ids == ()


def test_an_id_table_whose_entries_run_past_the_end_of_the_file_is_refused(
    tmp_path: Path,
) -> None:
    """The same bound, one field along: the header fits, the entries do not.

    5000 entries is 40,016 bytes in a file of a few kilobytes. Without the
    span bound the entry loop reads past the end and the report dies with a
    `struct.error` instead of answering.
    """
    image = _build_pe(
        manifest_id_entry_count=5000, resource_directory_size=0x7FFFFFF0
    )

    report = pic.inspect_plugin_file(_write(tmp_path, image))

    assert report.verdict == pic.VERDICT_MANIFEST_MISSING
    assert report.pe is not None and report.pe.manifest_resource_ids == ()


def test_a_root_resource_table_that_does_not_fit_is_loud(tmp_path: Path) -> None:
    """The ROOT table keeps the answer it had before this round.

    A root directory that does not parse is a statement about the IMAGE, so
    it stays `not_pe` -- unlike a malformed table under the type entry, which
    is answered quietly as "no manifest I will vouch for" (D12). Without this
    the two could be swapped and nothing would notice.
    """
    image = _build_pe(resource_directory_size=8)

    report = pic.inspect_plugin_file(_write(tmp_path, image))

    assert report.verdict == pic.VERDICT_NOT_PE


def test_a_manifest_under_a_type_that_is_not_rt_manifest_is_not_a_manifest(
    tmp_path: Path,
) -> None:
    """Kills the "descend into the FIRST type entry, whatever it is" mutant.

    A resource-rich DLL's first type is usually RT_ICON, whose ids run 1, 2,
    3... -- so a parser that ignores the type answers `image_ok` for a DLL
    with no manifest at all (pf-adversary, round `selrsl`, D6, which found
    every fixture here carrying exactly one type entry and it being 24).
    """
    image = _build_pe(manifest_type_field=3, manifest_resource_ids=(1, 2, 3))

    report = pic.inspect_plugin_file(_write(tmp_path, image))

    assert report.verdict == pic.VERDICT_MANIFEST_MISSING
    assert report.pe is not None and report.pe.manifest_resource_ids == ()


def test_a_string_named_type_entry_is_never_read_as_rt_manifest(
    tmp_path: Path,
) -> None:
    """Kills the "drop the high-bit test on the TYPE name" mutant.

    With the high bit set the field is an offset to a string, so comparing it
    to 24 compares an offset to a type id -- and a custom resource type whose
    name string happens to sit at offset 24 would read as RT_MANIFEST.
    """
    image = _build_pe(manifest_type_field=0x80000000 | pic._RT_MANIFEST)

    report = pic.inspect_plugin_file(_write(tmp_path, image))

    assert report.verdict == pic.VERDICT_MANIFEST_MISSING
    assert report.pe is not None and report.pe.manifest_resource_ids == ()


def test_a_string_named_id_entry_is_counted_but_never_satisfies_id_2(
    tmp_path: Path,
) -> None:
    """Kills the "drop the high-bit test on the ID name" mutant, and D11.

    A string-named entry cannot be id 2 and cannot be what the loader reads,
    but the image DOES carry a manifest -- so the message must not say "no
    embedded RT_MANIFEST" and send the reader looking in the wrong place.
    """
    image = _build_pe(manifest_resource_ids=(), manifest_named_ids=1)

    report = pic.inspect_plugin_file(_write(tmp_path, image))

    assert report.verdict == pic.VERDICT_MANIFEST_MISSING
    assert report.pe is not None
    assert report.pe.manifest_resource_ids == ()
    assert report.pe.manifest_named_resource_count == 1
    assert "string-named" in report.detail
    assert "no embedded RT_MANIFEST" not in report.detail


def test_an_id_table_claiming_more_entries_than_it_holds_is_refused_quietly(
    tmp_path: Path,
) -> None:
    """Kills the "delete the entry-count bound" mutant at the id level.

    And it is refused QUIETLY on purpose: a malformed table under the type
    entry says nothing about whether the file is a PE, so the export and
    import findings survive and only the manifest answer is withheld
    (pf-adversary, round `selrsl`, D12 -- the root table keeps its loud
    `not_pe`, which is a statement about the image itself).
    """
    image = _build_pe(manifest_id_entry_count=5000)

    report = pic.inspect_plugin_file(_write(tmp_path, image))

    assert report.verdict == pic.VERDICT_MANIFEST_MISSING
    assert report.pe is not None
    assert report.pe.manifest_resource_ids == ()
    # The rest of the report survives: only the manifest answer is withheld.
    assert report.pe.exports == (pic.REQUIRED_EXPORT,)
    assert report.pe.imports == ("MSVCR90.dll", "MSVCP90.dll", "KERNEL32.dll")


def test_a_two_level_tree_still_reads_even_though_mt_exe_writes_three(
    tmp_path: Path,
) -> None:
    """The shape the fixture used before `selrsl`, kept as its own case.

    Real images put a LANGUAGE level under the id, and the default fixture
    now does too. A two-level tree is not what `mt.exe` writes, but nothing
    in the parser needs the language level, and a hand-built resource section
    must not change the answer.
    """
    image = _build_pe(manifest_language_level=False)

    report = pic.inspect_plugin_file(_write(tmp_path, image))

    assert report.verdict == pic.VERDICT_IMAGE_OK
    assert report.pe is not None and report.pe.manifest_resource_ids == (2,)


def test_a_manifest_type_entry_with_no_id_level_is_not_a_manifest(
    tmp_path: Path,
) -> None:
    """Kills the "treat a leaf type entry as a manifest" mutant.

    A type entry pointing straight at data has no id level for the loader to
    match id 2 against. mt.exe cannot produce this shape; a hand-built or
    corrupted resource section can, and reading it as a manifest would put
    the old loose answer back through the side door.
    """
    image = _build_pe(manifest_subdirectory=False)

    report = pic.inspect_plugin_file(_write(tmp_path, image))

    assert report.verdict == pic.VERDICT_MANIFEST_MISSING
    assert report.pe is not None and report.pe.manifest_resource_ids == ()
    assert "no embedded RT_MANIFEST" in report.detail


def test_a_static_crt_build_is_not_failed_for_the_missing_import(tmp_path: Path) -> None:
    """A /MT build allocates from the CLIENT's CRT and is not wrong.

    The first version of this module returned `crt_missing` here, which is a
    red light for a DLL that works: revision 2 of the plug-in walks the
    client's import table for `operator new`/`delete` rather than using its
    own CRT's heap.
    """
    image = _build_pe(imports=("KERNEL32.dll",), with_manifest=False)

    report = pic.inspect_plugin_file(_write(tmp_path, image))

    assert report.verdict == pic.VERDICT_IMAGE_OK
    assert any("msvcr90.dll" in advisory for advisory in report.advisories)


def test_a_missing_msvcp90_is_an_advisory_not_a_failure(tmp_path: Path) -> None:
    """Revision 2 resolves the wstring ctor dynamically -- not fatal."""
    image = _build_pe(imports=("MSVCR90.dll", "KERNEL32.dll"))

    report = pic.inspect_plugin_file(_write(tmp_path, image))

    assert report.verdict == pic.VERDICT_IMAGE_OK
    assert any("msvcp90.dll" in advisory for advisory in report.advisories)


def test_an_image_with_no_import_directory(tmp_path: Path) -> None:
    """Kills the "delete the no-import-directory early return" mutant."""
    image = _build_pe(imports=())

    report = pic.inspect_plugin_file(_write(tmp_path, image))

    assert report.verdict == pic.VERDICT_IMAGE_OK
    assert report.pe is not None and report.pe.imports == ()


def test_an_image_with_only_one_data_directory(tmp_path: Path) -> None:
    """Kills the "delete the NumberOfRvaAndSizes bound" mutant.

    16 directories is a convention, not a rule; reading past
    NumberOfRvaAndSizes parses whatever follows the header as a directory.
    """
    image = _build_pe(directory_count=1)

    report = pic.inspect_plugin_file(_write(tmp_path, image))

    assert report.verdict == pic.VERDICT_IMAGE_OK
    assert report.pe is not None
    assert report.pe.imports == ()
    assert not report.pe.has_embedded_manifest


def test_a_section_whose_virtual_size_is_zero_is_still_readable(tmp_path: Path) -> None:
    """Kills the "trust VirtualSize alone" mutant.

    Older linkers (and object-copy tools) leave VirtualSize at 0 and describe
    the section with SizeOfRawData only. Every RVA in such a section is then
    outside `[VA, VA+VirtualSize)` and a parser that uses VirtualSize alone
    finds no section for the export directory at all.
    """
    image = _build_pe(rdata_virtual_size=0)

    report = pic.inspect_plugin_file(_write(tmp_path, image))

    assert report.verdict == pic.VERDICT_IMAGE_OK
    assert report.pe is not None and report.pe.exports == (pic.REQUIRED_EXPORT,)


def test_an_export_directory_with_no_name_table(tmp_path: Path) -> None:
    """Ordinal-only exports: NumberOfNames and AddressOfNames are both 0.

    Kills the "delete the ordinal-only guard" mutant: without the guard the
    reader maps RVA 0, which belongs to no section, and the file is reported
    as malformed instead of as a DLL with nothing to find by name.
    """
    image = _build_pe(export_name_count=0, names_rva_zero=True)

    report = pic.inspect_plugin_file(_write(tmp_path, image))

    assert report.verdict == pic.VERDICT_NO_EXPORTS
    assert report.pe is not None and report.pe.exports == ()


def test_a_64_bit_build_cannot_load_into_a_32_bit_client(tmp_path: Path) -> None:
    image = _build_pe(machine=0x8664, pe32=False)

    assert (
        pic.inspect_plugin_file(_write(tmp_path, image)).verdict
        == pic.VERDICT_WRONG_MACHINE
    )


def test_an_exe_is_not_a_dll(tmp_path: Path) -> None:
    image = _build_pe(is_dll=False)

    assert pic.inspect_plugin_file(_write(tmp_path, image)).verdict == pic.VERDICT_NOT_A_DLL


def test_every_blocking_problem_is_printed_not_just_the_first(tmp_path: Path) -> None:
    """One attended session cannot afford one problem per rebuild."""
    image = _build_pe(exports=("DllMain",), is_dll=False)

    report = pic.inspect_plugin_file(_write(tmp_path, image))
    lines = pic.console_lines(report, "build")

    assert len(report.problems) >= 2
    assert any("also_problem=" in line for line in lines)


# --- malformed input must produce a verdict, never a traceback -------------


def test_a_text_file_named_like_a_dll(tmp_path: Path) -> None:
    report = pic.inspect_plugin_file(_write(tmp_path, b"this is not a PE image\n"))

    assert report.verdict == pic.VERDICT_NOT_PE
    assert report.sha256  # still hashed: the tester needs to identify the file


def test_a_truncated_image_does_not_raise(tmp_path: Path) -> None:
    report = pic.inspect_plugin_file(_write(tmp_path, _build_pe()[:0x120]))

    assert report.verdict == pic.VERDICT_NOT_PE


def test_a_lying_export_name_count_does_not_hang(tmp_path: Path) -> None:
    """A count of 2**31 must be refused, not walked."""
    image = _build_pe(export_name_count=2**31)

    report = pic.inspect_plugin_file(_write(tmp_path, image))

    assert report.verdict == pic.VERDICT_NOT_PE
    assert "exceeds file size" in report.detail


def test_an_rva_pointing_into_an_uninitialised_tail_is_refused(tmp_path: Path) -> None:
    """Kills the "span = max(...) and read anyway" bug.

    `.data` here has VirtualSize four times its raw size. An RVA in that tail
    has no bytes in the file at all; mapping it by arithmetic would silently
    read the neighbouring section's bytes, and the file-level bounds check
    cannot see that.
    """
    image = bytearray(_build_pe())
    # Point the export directory at .data's uninitialised tail (VA 0x3000 +
    # raw size 0x200 .. +0x800).
    optional = _PE_OFFSET + 4 + 20
    directories = optional + 92 + 4
    struct.pack_into("<II", image, directories, 0x3000 + 0x600, 0x28)

    report = pic.inspect_plugin_file(_write(tmp_path, bytes(image)))

    assert report.verdict == pic.VERDICT_NOT_PE
    assert "uninitialised tail" in report.detail


def test_an_rva_in_no_section_is_refused(tmp_path: Path) -> None:
    image = bytearray(_build_pe())
    optional = _PE_OFFSET + 4 + 20
    directories = optional + 92 + 4
    struct.pack_into("<II", image, directories, 0x7F000000, 0x28)

    report = pic.inspect_plugin_file(_write(tmp_path, bytes(image)))

    assert report.verdict == pic.VERDICT_NOT_PE
    assert "not inside any section" in report.detail


def test_an_empty_file(tmp_path: Path) -> None:
    assert pic.inspect_plugin_file(_write(tmp_path, b"")).verdict == pic.VERDICT_NOT_PE


def test_a_directory_in_the_dlls_place(tmp_path: Path) -> None:
    (tmp_path / "GameMaster.dll").mkdir()

    assert pic.inspect_plugin_file(tmp_path / "GameMaster.dll").verdict == pic.VERDICT_MISSING


# --- the install side: which file does the game actually load --------------


def test_an_install_without_the_plugin_is_missing_and_says_where(tmp_path: Path) -> None:
    report = pic.inspect_client_install(tmp_path)

    assert report.verdict == pic.VERDICT_MISSING
    assert str(tmp_path) in report.path
    assert "RE-164" in report.detail


def test_a_client_dir_that_does_not_exist_is_not_a_finding_about_the_client(
    tmp_path: Path,
) -> None:
    """A mistyped or unquoted path must not manufacture the RE-164 note.

    `C:\\Pirate Force\\Client` unquoted on cmd.exe reaches this tool as
    `C:\\Pirate`, and the first version answered that with "no GameMaster.dll
    in C:\\Pirate -- the RE-164 operational note is confirmed for this
    machine".
    """
    report = pic.inspect_client_install(tmp_path / "no-such-client")

    assert report.verdict == pic.VERDICT_NO_SUCH_DIR
    assert "RE-164" not in report.detail
    assert "does not exist" in report.detail


def test_the_installed_copy_is_found_case_insensitively(tmp_path: Path) -> None:
    _write(tmp_path, _build_pe(), name="gamemaster.dll")

    report = pic.inspect_client_install(tmp_path)

    assert report.verdict == pic.VERDICT_IMAGE_OK
    assert report.path.lower().endswith("gamemaster.dll")


def test_an_exact_name_wins_over_a_case_variant(tmp_path: Path) -> None:
    """Two spellings in one directory only happens off Windows; be explicit."""
    _write(tmp_path, _build_pe(exports=("DllMain",)), name="gamemaster.dll")
    _write(tmp_path, _build_pe(), name="GameMaster.dll")

    report = pic.inspect_client_install(tmp_path)

    assert report.path.endswith("GameMaster.dll")
    assert report.verdict == pic.VERDICT_IMAGE_OK


def test_a_stale_install_is_visible_as_different_bytes(tmp_path: Path) -> None:
    """The re-test-yesterdays-binary trap the build script's sha256 exists for."""
    build_dir = tmp_path / "build"
    install_dir = tmp_path / "client"
    build_dir.mkdir()
    install_dir.mkdir()
    _write(build_dir, _build_pe())
    _write(install_dir, _build_pe(imports=("MSVCR90.dll", "KERNEL32.dll")))

    build = pic.inspect_plugin_file(build_dir / "GameMaster.dll")
    install = pic.inspect_client_install(install_dir)

    assert build.sha256 != install.sha256
    assert not pic.same_bytes(build, install)


def test_identical_copies_compare_equal(tmp_path: Path) -> None:
    build_dir = tmp_path / "build"
    install_dir = tmp_path / "client"
    build_dir.mkdir()
    install_dir.mkdir()
    image = _build_pe()
    _write(build_dir, image)
    _write(install_dir, image)

    assert pic.same_bytes(
        pic.inspect_plugin_file(build_dir / "GameMaster.dll"),
        pic.inspect_client_install(install_dir),
    )


def test_two_missing_files_are_never_called_identical(tmp_path: Path) -> None:
    """Empty sha256 on both sides must not read as "the same file"."""
    left = pic.inspect_plugin_file(tmp_path / "a.dll")
    right = pic.inspect_plugin_file(tmp_path / "b.dll")

    assert not pic.same_bytes(left, right)


# --- the CLI, which is the only part the bridge actually runs --------------


def test_cli_returns_zero_only_when_every_path_is_ok(tmp_path: Path, capsys) -> None:
    good = _write(tmp_path, _build_pe())

    assert pic.main(["--dll", str(good)]) == 0
    assert "verdict=image_ok" in capsys.readouterr().out


def test_cli_returns_nonzero_on_a_decorated_export(tmp_path: Path, capsys) -> None:
    bad = _write(tmp_path, _build_pe(exports=("_CreateGameMaster",)))

    assert pic.main(["--dll", str(bad)]) == 1
    assert "verdict=export_decorated" in capsys.readouterr().out


def test_cli_fails_when_the_install_is_not_the_build_even_if_both_are_ok(
    tmp_path: Path, capsys
) -> None:
    """Two healthy DLLs that are not the same file is still a red light.

    The first version printed `same_bytes=no` and exited 0, so the trap the
    comparison exists to catch -- testing yesterday's binary -- passed green.
    """
    build_dir = tmp_path / "build"
    install_dir = tmp_path / "client"
    build_dir.mkdir()
    install_dir.mkdir()
    _write(build_dir, _build_pe())
    _write(install_dir, _build_pe(imports=("MSVCR90.dll", "KERNEL32.dll")))

    exit_code = pic.main(
        ["--dll", str(build_dir / "GameMaster.dll"), "--client-dir", str(install_dir)]
    )
    out = capsys.readouterr().out

    assert exit_code == 1
    assert "same_bytes=no" in out
    assert "verdict=stale_install" in out


def test_cli_is_green_when_the_install_is_the_build(tmp_path: Path, capsys) -> None:
    build_dir = tmp_path / "build"
    install_dir = tmp_path / "client"
    build_dir.mkdir()
    install_dir.mkdir()
    image = _build_pe()
    _write(build_dir, image)
    _write(install_dir, image)

    exit_code = pic.main(
        ["--dll", str(build_dir / "GameMaster.dll"), "--client-dir", str(install_dir)]
    )

    assert exit_code == 0
    assert "same_bytes=yes" in capsys.readouterr().out


def test_cli_needs_at_least_one_target() -> None:
    with pytest.raises(SystemExit):
        pic.main([])


# --- the exact CLI contract `patches/gm_plugin/install.bat` depends on ------
#
# install.bat revision 3 (COO-DECISION `20260902_2342` item 3) no longer just
# recommends this tool -- it RUNS it, and decides whether to copy a DLL into
# the owner's client folder from the tokens below, read with `findstr /c:`.
# `findstr /c:` is a SUBSTRING match with no anchoring, and the batch cannot
# import anything from this module, so every one of these assertions is the
# only thing standing between a rename here and a silent regression there:
# a changed token sends install.bat down its "no verdict line" branch, which
# WARNS AND CONTINUES. The failure would be invisible on both sides.


def test_the_cli_prints_the_exact_token_install_bat_greps_for(
    tmp_path: Path, capsys
) -> None:
    good = _write(tmp_path, _build_pe())

    assert pic.main(["--dll", str(good)]) == 0
    out = capsys.readouterr().out

    # Byte for byte what install.bat passes to `findstr /c:`.
    assert "GM_PLUGIN_IMAGE build verdict=" in out
    assert "GM_PLUGIN_IMAGE build verdict=image_ok" in out


def test_a_manifest_at_the_exe_id_makes_the_cli_refuse_by_token_and_by_code(
    tmp_path: Path, capsys
) -> None:
    """The one failure the `.rsrc` check in install.bat cannot see.

    A manifest embedded at `;#1` leaves an `.rsrc` section in the image, so
    `dumpbin /headers | findstr .rsrc` says [ok] and the DLL still answers
    LoadLibraryW with 14001. install.bat's refusal for this shape rests
    entirely on the two facts asserted here.
    """
    bad = _write(tmp_path, _build_pe(manifest_resource_ids=(1,)))

    exit_code = pic.main(["--dll", str(bad)])
    out = capsys.readouterr().out

    assert exit_code != 0
    assert "GM_PLUGIN_IMAGE build verdict=manifest_missing" in out


def _every_blocking_verdict() -> tuple[str, ...]:
    """Read the blocking verdicts off the module, never off a hand list.

    pf-adversary, round `b8xrod`, M2: the first version of the test below
    hand-listed eight shapes, claimed in its own docstring to cover "every
    blocking verdict", and missed three. Mutants that planted the string
    `verdict=image_ok` in the `export_forwarded` and `unreadable` messages
    both survived the whole suite.
    """
    return tuple(
        getattr(pic, name)
        for name in sorted(dir(pic))
        if name.startswith("VERDICT_") and getattr(pic, name) != pic.VERDICT_IMAGE_OK
    )


def _refusal_cases(tmp_path: Path) -> dict[str, list[str]]:
    """One CLI invocation per blocking verdict. Keys are checked for coverage."""
    absent = tmp_path / "gone" / "GameMaster.dll"
    no_dir = tmp_path / "not-a-client-folder"
    shapes = {
        pic.VERDICT_MANIFEST_MISSING: _build_pe(manifest_resource_ids=(1,)),
        pic.VERDICT_EXPORT_DECORATED: _build_pe(exports=("_CreateGameMaster",)),
        pic.VERDICT_EXPORT_FORWARDED: _build_pe(
            forwarders=(pic.REQUIRED_EXPORT,)
        ),
        pic.VERDICT_EXPORT_MISSING: _build_pe(exports=("SomethingElse",)),
        pic.VERDICT_NO_EXPORTS: _build_pe(with_export_dir=False),
        pic.VERDICT_WRONG_MACHINE: _build_pe(machine=0x8664, pe32=False),
        pic.VERDICT_NOT_A_DLL: _build_pe(is_dll=False),
        pic.VERDICT_NOT_PE: b"not a PE at all, just text",
    }
    cases: dict[str, list[str]] = {}
    for verdict, image in shapes.items():
        path = _write(tmp_path, image, name="GameMaster_%s.dll" % verdict)
        cases[verdict] = ["--dll", str(path)]
    cases[pic.VERDICT_MISSING] = ["--dll", str(absent)]
    cases[pic.VERDICT_NO_SUCH_DIR] = ["--client-dir", str(no_dir)]
    # `unreadable` needs the open to fail, which no file shape can arrange
    # under a test run as root; the caller patches `read_bytes` for it.
    cases[pic.VERDICT_UNREADABLE] = ["--dll", str(_write(tmp_path, _build_pe()))]
    return cases


def test_the_refusal_case_table_covers_every_blocking_verdict(
    tmp_path: Path,
) -> None:
    """The coverage claim itself, so it cannot rot silently again."""
    missing = set(_every_blocking_verdict()) - set(_refusal_cases(tmp_path))
    assert not missing, "no refusal case for: %s" % sorted(missing)


def test_a_refused_image_never_prints_the_substring_that_would_install_it(
    tmp_path: Path, capsys, monkeypatch
) -> None:
    """`findstr /c:` matches anywhere on any line, including inside prose.

    If any advisory, detail or remedy string ever contained the words
    `verdict=image_ok`, install.bat would copy a DLL this tool just refused.
    Checked for EVERY blocking verdict, derived from the module.
    """
    cases = _refusal_cases(tmp_path)
    for verdict, argv in cases.items():
        if verdict == pic.VERDICT_UNREADABLE:
            def _boom(self, *args, **kwargs):
                raise OSError(13, "permission denied")

            monkeypatch.setattr(Path, "read_bytes", _boom)
        exit_code = pic.main(argv)
        out = capsys.readouterr().out
        monkeypatch.undo()

        assert exit_code != 0, verdict
        assert "GM_PLUGIN_IMAGE" in out, verdict
        assert "verdict=%s" % verdict in out, (verdict, out)
        assert "verdict=image_ok" not in out, (verdict, out)


def test_asking_only_about_the_build_is_green_with_no_install_anywhere(
    tmp_path: Path, capsys
) -> None:
    """Why install.bat passes `--dll` alone and must never add `--client-dir`.

    It runs BELOW the [STOP] guard, which has already proved the target folder
    holds no GameMaster.dll. Adding `--client-dir "%TARGET%"` there would read
    `verdict=missing` and exit 1 on every clean folder -- a permanent refusal
    to install, on exactly the folder an install is for. This test pins the
    other half: with `--dll` alone the tool is green and invents no report
    about a client directory it was not asked about.
    """
    good = _write(tmp_path, _build_pe())

    assert pic.main(["--dll", str(good)]) == 0
    out = capsys.readouterr().out

    assert "GM_PLUGIN_IMAGE build verdict=image_ok" in out
    assert "GM_PLUGIN_IMAGE install" not in out
    assert "verdict=missing" not in out
    assert "same_bytes" not in out


def test_the_client_dir_flag_would_refuse_the_very_folder_installs_are_for(
    tmp_path: Path, capsys
) -> None:
    """The negative half of the rule above, measured rather than asserted.

    Kept as a test so that anyone who "helpfully" adds `--client-dir` to
    install.bat has this failure written down before they spend an attended
    round on it.
    """
    build_dir = tmp_path / "build"
    clean_target = tmp_path / "client"
    build_dir.mkdir()
    clean_target.mkdir()
    _write(build_dir, _build_pe())

    exit_code = pic.main(
        [
            "--dll",
            str(build_dir / "GameMaster.dll"),
            "--client-dir",
            str(clean_target),
        ]
    )
    out = capsys.readouterr().out

    assert exit_code == 1
    assert "GM_PLUGIN_IMAGE install verdict=missing" in out


def test_every_console_line_encodes_on_a_thai_console_even_from_a_latin_path(
    tmp_path: Path, capsys
) -> None:
    """pf-adversary, round `b8xrod`, M1 -- a measured false-green, not a nit.

    `install.bat` redirects this tool's output to a file, so on a Thai Windows
    `sys.stdout` is a cp874 stream. `path=` is the only field carrying text
    this module did not author and it sits on the verdict line itself, so one
    character outside cp874 in the folder name used to raise UnicodeEncodeError
    on the FIRST line: the batch then found a traceback with no verdict token,
    took its "the checker said nothing" branch, and COPIED THE DLL UNCHECKED.

    The older `test_every_console_line_survives_the_bridge_console` cannot see
    this: pytest's `tmp_path` is always ASCII, so it is green by construction.
    """
    latin = tmp_path / "José"
    latin.mkdir()
    report = pic.inspect_plugin_file(_write(latin, _build_pe()))

    for line in pic.console_lines(report, "build"):
        line.encode("cp874")  # raises UnicodeEncodeError if this ever regresses
        assert line.isascii()

    assert pic.main(["--dll", str(latin / "GameMaster.dll")]) == 0
    out = capsys.readouterr().out
    out.encode("cp874")
    assert "GM_PLUGIN_IMAGE build verdict=image_ok" in out


def test_the_report_names_which_rules_this_copy_of_the_module_enforces(
    tmp_path: Path, capsys
) -> None:
    """pf-adversary, round `b8xrod`, H2.

    `install.bat` finds this module by guessing folder names. A checkout older
    than round `selrsl` prints `verdict=image_ok` and exits 0 for a manifest at
    resource id 1 -- see `test_a_manifest_at_the_exe_id_is_not_a_manifest_for_a
    _dll`, which says exactly that in its docstring -- so the verdict token
    alone cannot tell an enforcing copy from a permissive one. This line can,
    by being absent from the old one.
    """
    assert "manifest_id2" in pic.CONSOLE_RULES

    assert pic.main(["--dll", str(_write(tmp_path, _build_pe()))]) == 0
    out = capsys.readouterr().out

    assert "GM_PLUGIN_IMAGE build rules=" in out
    for rule in pic.CONSOLE_RULES:
        assert rule in out


def test_the_rules_line_is_printed_for_a_refusal_too(tmp_path: Path, capsys) -> None:
    """A caller must be able to attribute a REFUSAL as well as a pass."""
    bad = _write(tmp_path, _build_pe(manifest_resource_ids=(1,)))

    assert pic.main(["--dll", str(bad)]) != 0

    assert "GM_PLUGIN_IMAGE build rules=" in capsys.readouterr().out


# --- the other half of the contract: read install.bat itself ---------------
#
# pf-adversary, round `b8xrod`, M3: every assertion above pins the module and
# none of them opens the batch file, so renaming the literal inside
# `findstr /c:"..."` leaves the whole suite green while every install silently
# falls into warn-and-copy. These read the batch.
#
# `pf_bridge` is a SEPARATE repository and the Windows gate clones this one
# alone, so these tests skip there. The skip is named and counted below, never
# silent (a bare skip is what closed #601 with 3,534 lines of work in it).
#
# ROUND `kv2vjk`, AND THIS IS WHY #611 DIED WITH THE WHOLE ROUND IN IT.  The
# first version of this block raised a BARE `pytest.skip`, which carries no
# `[precondition:...]` token, so `tools/pf_pytest_precondition_census.py`
# filed it as `UNDECLARED SKIP ... x 3` and `skip_census` exited 1 while
# `pytest_subset` was green at 7158 passed.  A bare skip cannot be pinned in
# either place without lying about one of the two machines:
#
#   * as a `design_skips` entry it would be expected UNCONDITIONALLY, so the
#     bridge -- where `../pf_bridge` IS beside this clone and these three
#     tests RUN -- would observe 0 against a pin of 3 and go red there
#     instead;
#   * and it is not a design decision in the first place.  It is exactly the
#     shape `tests/pf_preconditions.py` was written for: evidence that lives
#     outside this repository, present on one machine and absent on the other.
#
# So the guard asks `BRIDGE_SIBLING` and reports ITS reason.  Absent -> three
# declared skips pinned in `docs/PYTEST_SKIP_PINS.json` under `preconditions`,
# which the census expects to be ZERO on any machine that has the sibling.
#
# The key is `bridge_sibling` and not a narrower one for `install.bat` itself,
# because a narrower key would need a new entry in `tests/pf_preconditions.py`
# -- another lane's file -- and because the two answers must not be merged: a
# checkout that HAS `../pf_bridge` and does not have the batch file is not a
# machine short of evidence, it is a deleted `install.bat`, and that is the
# regression these three tests exist to catch.  It fails loudly below.


def _install_bat() -> Path | None:
    """`../pf_bridge/patches/gm_plugin/install.bat`, or None.

    One relative candidate and no absolute fallback, deliberately: the two
    repositories sit side by side both on the bridge
    (`...\\Pirate Force\\pf_bridge` beside `...\\Pirate Force\\Pirate Force
    ServerProject`) and in every cloud clone, so an absolute path would only
    hide the skip from a rehearsal of the machine that actually skips.
    """
    candidate = (
        Path(__file__).resolve().parents[2]
        / "pf_bridge"
        / "patches"
        / "gm_plugin"
        / "install.bat"
    )
    return candidate if candidate.is_file() else None


INSTALL_BAT_TESTS = 4
"""How many tests in this file skip together when pf_bridge is not beside us."""


def _missing_install_bat_message(sibling_present: bool) -> str:
    """What to say when the batch file is not there, per machine.

    Split out and given the answer as an ARGUMENT so both branches can be read
    back by a test.  Round `kv2vjk`, pf-adversary D4: the first draft stated
    "../pf_bridge is checked out beside this repository but install.bat is not
    in it" unconditionally, and that sentence is false on the gate -- it would
    send the next reader hunting for a deleted file inside a directory that
    does not exist.
    """
    if sibling_present:
        where = (
            "../pf_bridge IS beside this repository and "
            "patches/gm_plugin/install.bat is not in it"
        )
    else:
        where = (
            "../pf_bridge is NOT beside this repository at all, which means "
            "this helper was reached from outside InstallBatContractTests -- "
            "that class's guard is the only thing allowed to answer for an "
            "absent sibling, and a fourth caller outside it would skip "
            "undeclared, exactly as pirate-force-server#611 did"
        )
    return (
        "%s.  This is NOT a missing-evidence skip and must never become one: "
        "the batch file is this lane's own, it landed in pf_bridge#909, and "
        "the %d tests in InstallBatContractTests are the only thing standing "
        "between a renamed findstr literal and an install that silently "
        "warns-and-copies.  Restore the file, or move these tests to whatever "
        "replaced it." % (where, INSTALL_BAT_TESTS)
    )


def _install_bat_text() -> str:
    path = _install_bat()
    if path is None:
        raise AssertionError(_missing_install_bat_message(
            BRIDGE_SIBLING.present))
    return path.read_text(encoding="ascii").replace("\r\n", "\n")


# --- reading a .bat as a graph, because a refusal is a control-flow claim ---
#
# Small on purpose: it models the three things a `goto`/`exit` batch actually
# does and nothing else -- labels, jumps, and FALL-THROUGH into the next label.
# `if ... goto X` is an edge; so is the next label, unless the block ends in an
# unconditional `goto` or `exit`.  `call` is not modelled (the batch has none),
# and neither are variables in label names; if either appears, this walker
# under-reports and the test that uses it must be revisited rather than
# trusted.


def _batch_blocks(text: str) -> dict:
    """`{label: block text}` in file order, block = up to the next label."""
    blocks, label, lines = {}, None, []
    for line in text.splitlines():
        stripped = line.strip()
        if (stripped.startswith(":") and not stripped.startswith("::")
                and len(stripped) > 1 and " " not in stripped):
            if label is not None:
                blocks[label] = "\n".join(lines)
            label, lines = stripped[1:], []
            continue
        if label is not None:
            lines.append(line)
    if label is not None:
        blocks[label] = "\n".join(lines)
    return blocks


def _batch_successors(block: str, fallthrough: str | None) -> set:
    targets, ends = set(), False
    for line in block.splitlines():
        stripped = line.strip()
        if stripped.upper().startswith(("REM ", "ECHO ", "::")):
            continue
        lowered = stripped.lower()
        at = lowered.find("goto ")
        if at != -1:
            target = stripped[at + len("goto "):].split()[0].lstrip(":")
            targets.add(target.lower())
            if at == 0:
                ends = True
        elif lowered.startswith("exit"):
            ends = True
    if not ends and fallthrough is not None:
        targets.add(fallthrough)
    targets.discard("eof")
    return targets


def _labels_reachable_from(text: str, start: str) -> set:
    blocks = _batch_blocks(text)
    order = list(blocks)
    seen, queue = set(), [start]
    while queue:
        label = queue.pop()
        if label in seen or label not in blocks:
            continue
        seen.add(label)
        index = order.index(label)
        after = order[index + 1] if index + 1 < len(order) else None
        queue.extend(_batch_successors(blocks[label], after))
    seen.discard(start)
    return seen


@BRIDGE_SIBLING.skip_unless_present()
class InstallBatContractTests(unittest.TestCase):
    """The three tests that read the batch file, guarded as ONE site.

    A `unittest.TestCase` with a class decorator, in a module that is
    otherwise plain pytest functions, and that is not a style lapse -- it is
    the only shape `tests/test_pytest_precondition_census.py` can grade.  Its
    `guarded_tests()` walker counts guard sites inside `ast.ClassDef` and
    nowhere else, ON PURPOSE (its own comment: guards in module-level code
    "produce skips that cannot be pinned per test name, so a module using them
    goes red here until it is restructured").  Measured this round: with these
    three as module-level functions calling `pytest.skip` from a helper, the
    walker derived 0 guards against a pin of 3 and TWO tests in that file went
    red -- the same class of gate failure that closed #611, caught one step
    earlier.
    """

    def setUp(self) -> None:
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        self.tmp_path = Path(holder.name)

    def test_install_bat_greps_for_the_tokens_this_module_actually_prints(
        self,
    ) -> None:
        text = _install_bat_text()
        lines = pic.console_lines(
            pic.inspect_plugin_file(_write(self.tmp_path, _build_pe())),
            "build",
        )

        verdict_line = next(line for line in lines if " verdict=" in line)
        pass_token = verdict_line.split(" path=")[0]
        assert pass_token == "GM_PLUGIN_IMAGE build verdict=image_ok"

        # The three literals the batch's decision rests on, derived here.
        assert 'findstr /c:"GM_PLUGIN_IMAGE build verdict="' in text
        assert 'findstr /c:"%s"' % pass_token in text
        assert 'findstr /c:"GM_PLUGIN_IMAGE build rules="' in text
        assert 'findstr /c:"manifest_id2"' in text
        assert any(
            line.startswith("GM_PLUGIN_IMAGE build rules=") for line in lines
        )

    def test_install_bat_never_asks_about_a_client_dir_when_it_installs(
        self,
    ) -> None:
        """It runs below the [STOP] guard, on a folder proven to hold no
        plug-in.

        `--client-dir` there reads `verdict=missing` and exits 1 every time: a
        permanent refusal to install, on exactly the clean folder an install is
        for. Written down here so the next person to "helpfully" add the flag
        has to delete a test that says why.
        """
        text = _install_bat_text()
        invocations = [
            line
            for line in text.splitlines()
            if "-m pirateforce_foundation.gm.plugin_image_check" in line
            and not line.strip().upper().startswith(("REM", "ECHO"))
        ]

        assert len(invocations) == 1, invocations
        assert "--dll" in invocations[0]
        assert "--client-dir" not in invocations[0]

    def test_install_bat_refuses_rather_than_warns_when_the_checker_answers_no(
        self,
    ) -> None:
        """The fail-closed half of COO-DECISION `20260902_2342` item 3.

        A refusal must end the script, not reach the copy -- BY ANY ROUTE.

        The first version of this test forbade the literal `goto do_copy`
        inside the refusal block and nothing else.  pf-adversary, round
        `kv2vjk`, D5 named the input that passes it with the feature broken:
        `COO-DECISION 20260903_0148` §7 amends `2342` to make the batch honour
        `PFGM_FORCE=1` and copy anyway, and the obvious way to write that is
        `goto pfgm_forced_copy` -- a different literal, the same fall-through,
        and this test measured GREEN on a rewritten batch where a refusal
        really could copy.  Forbidding one spelling is not grading a property.

        So the block graph is walked instead.  FALL-THROUGH IS AN EDGE: a
        batch label runs into the next one unless the block ends the script or
        jumps unconditionally, so deleting the `exit /b 1` alone drops control
        into `:pfgm_stale_tool`, which goes straight to `:do_copy`.  That is
        the mutation the string test could not see either.

        REVISION 4 NARROWS THIS, IT DOES NOT DROP IT.  `COO-DECISION
        20260903_0148` §7 asks the batch to honour `PFGM_FORCE=1` and copy
        anyway, so "no route at all" is no longer the property -- the property
        is that EVERY route from the refusal to the copy is conditional on
        that variable.  An unconditional `goto`, a fall-through, or a jump
        guarded by anything else still fails here, which is the whole content
        of "not fail-open": the owner has to type the variable.
        """
        text = _install_bat_text()
        assert "\n:pfgm_refuse\n" in text
        block = _batch_blocks(text)["pfgm_refuse"]
        assert "exit /b 1" in block

        escapes = []
        for line in block.splitlines():
            stripped = line.strip()
            if stripped.upper().startswith(("REM ", "ECHO ", "::")):
                continue
            at = stripped.lower().find("goto ")
            if at == -1:
                continue
            target = stripped[at + len("goto "):].split()[0].lstrip(":")
            if target.lower() != "do_copy" and "do_copy" not in (
                _labels_reachable_from(text, target.lower())
            ):
                continue
            # Reaching the copy from a refusal is allowed on exactly one
            # condition, and the line itself has to carry it.
            assert "PFGM_FORCE" in stripped, stripped
            assert '=="1"' in stripped.replace(" ", ""), stripped
            escapes.append(target.lower())

        assert len(escapes) == 1, escapes
        forced = _batch_blocks(text)[escapes[0]]
        # A forced install that does not say what was refused is the fail-open
        # this whole branch was allowed in order to avoid.
        assert "[FORCED]" in forced
        assert "%PFGM_VERDICT%" in forced
        assert "%PFGM_RULES%" in forced

    def test_install_bat_forces_only_the_checker_and_reads_the_real_tokens(
        self,
    ) -> None:
        """The other three things `PFGM_FORCE=1` must not become.

        1. It must name the REAL verdict and the REAL failing rules, which
           means reading the tokens this module prints rather than a literal
           re-typed into the batch.  A forced install whose evidence line says
           `rules=` and nothing after it is a forced install nobody can report.
        2. It must not reach the `[STOP]` guard on an existing GameMaster.dll.
           That guard is about destroying the original plug-in, which no
           environment variable may override.
        3. Its fallback for an older checker must be a sentence, not an empty
           value -- and must carry no `<` or `>`, because `echo %VAR%` with an
           angle bracket in the value REDIRECTS the one line the owner was
           asked to report.
        """
        image = _write(self.tmp_path, _build_pe(manifest_resource_ids=(1,)))
        lines = pic.console_lines(pic.inspect_plugin_file(image), "build")
        rules_line = next(line for line in lines if " failed_rules=" in line)
        assert rules_line == "GM_PLUGIN_IMAGE build failed_rules=manifest_id2"

        text = _install_bat_text()
        assert 'findstr /c:"GM_PLUGIN_IMAGE build failed_rules="' in text
        # `failed_rules=manifest_id2` -> `rules=manifest_id2`, derived, so the
        # printed token cannot drift from the token that was read.
        assert 'set "PFGM_RULES=%PFGM_RULES:failed_=%"' in text

        stop = text.index("[STOP] A GameMaster.dll ALREADY EXISTS")
        assert "PFGM_FORCE" not in text[stop:text.index("exit /b 1", stop)]

        for line in text.splitlines():
            if 'set "PFGM_RULES=rules=' not in line:
                continue
            assert "<" not in line and ">" not in line, line
            assert not line.rstrip().endswith('set "PFGM_RULES=rules="'), line
            break
        else:  # pragma: no cover - the fallback is the point of the branch
            raise AssertionError("no PFGM_RULES fallback for an old checker")


# --- what the census tests upstream cannot answer --------------------------
#
# `tests/test_pytest_precondition_census.py` already re-derives the count AND
# the test names for every pin straight from this file's AST, so a second copy
# of that comparison here would only be a slower duplicate.  What it cannot do
# is ask the MACHINE anything: it never touches `../pf_bridge`.  These two do
# exactly that and nothing else.  Both run everywhere, need no artifact, and
# are deliberately outside `InstallBatContractTests` so the guarded count in
# that class stays 3.


def _pin_entry() -> dict:
    pins = json.loads(
        (ROOT / "docs" / "PYTEST_SKIP_PINS.json").read_text(encoding="utf-8")
    )
    module = "tests/" + Path(__file__).name
    matches = [
        entry for entry in pins["preconditions"]
        if entry["key"] == "bridge_sibling"
        and entry["module"].replace("\\", "/") == module
    ]
    assert len(matches) == 1, (
        "expected exactly one bridge_sibling pin for %s, found %d"
        % (module, len(matches))
    )
    return matches[0]


def test_the_module_constant_and_the_pin_say_the_same_number():
    """`INSTALL_BAT_TESTS` is quoted in a failure message, so it can lie.

    The pin file and the class are graded against each other upstream; this
    constant is graded against neither, and it is the number the
    `AssertionError` in `_install_bat_text` tells a human.
    """
    methods = [
        name for name in vars(InstallBatContractTests)
        if name.startswith("test")
    ]
    assert len(methods) == INSTALL_BAT_TESTS, sorted(methods)
    assert _pin_entry()["count"] == INSTALL_BAT_TESTS


def test_a_bridge_beside_this_clone_really_does_carry_install_bat():
    """The premise the whole guard rests on, asked of THIS machine.

    `bridge_sibling` answers "is `../pf_bridge` there", and the class above
    treats that as "the batch file is readable".  Those are two different
    questions, and the gap between them is where a false RUN lives: a checkout
    that has the sibling and not the file would reach `_install_bat_text` and
    die.  That is the intended outcome -- a deleted `install.bat` IS a
    regression -- but it must be legible, so it is named here rather than
    arriving as a stray AssertionError from a helper.
    """
    assert "[precondition:bridge_sibling]" in BRIDGE_SIBLING.reason
    if not BRIDGE_SIBLING.present:
        assert _install_bat() is None
        return
    assert _install_bat() is not None, (
        "../pf_bridge is beside this clone but "
        "patches/gm_plugin/install.bat is missing from it"
    )


def test_a_missing_install_bat_raises_loudly_instead_of_skipping(monkeypatch):
    """The `AssertionError` branch, which no machine reaches on its own.

    pf-adversary, round `kv2vjk`, D2: on the gate the class is skipped before
    that line; on the bridge the file is there.  So the one line the whole
    guard argument rests on -- "a sibling without the batch file is a deleted
    file, not missing evidence" -- had never executed anywhere, and replacing
    it with a bare `pytest.skip` left BOTH machines fully green.  That is the
    shape that closed #611, re-installed in latent form.  It executes here.
    """
    monkeypatch.setattr(sys.modules[__name__], "_install_bat", lambda: None)
    with pytest.raises(AssertionError) as raised:
        _install_bat_text()
    assert "must never become one" in str(raised.value)


def test_the_missing_install_bat_message_tells_the_two_machines_apart():
    """D4: the sentence must not assert a sibling nobody looked for."""
    present = _missing_install_bat_message(True)
    absent = _missing_install_bat_message(False)
    assert "IS beside this repository" in present
    assert "is NOT beside this repository" in absent
    assert "InstallBatContractTests" in absent
    for message in (present, absent):
        assert str(INSTALL_BAT_TESTS) in message


_REFUSAL_SHAPED_BATCH = """@echo off
if not "%PFGM_RC%"=="0" goto pfgm_refuse
echo [ok] verdict=image_ok
goto do_copy

:pfgm_refuse
echo [FAIL] refused. Nothing was copied.
exit /b 1

:pfgm_stale_tool
echo [warn] old copy, treated as no checker at all.
goto do_copy

:do_copy
copy /y "GameMaster.dll" "%TARGET%\\GameMaster.dll" >nul
"""


def test_the_refusal_walker_sees_the_two_ways_a_refusal_can_reach_the_copy():
    """The walker is the witness for `pfgm_refuse`, so it needs one too.

    Synthetic text, not the real batch: this runs on the gate, where
    `../pf_bridge` is absent, and a fourth reader of the real file would
    either skip undeclared (breaking the pin at 3) or die.  The shape below
    is the real one -- refusal, a warn label after it that goes to the copy,
    and the copy -- which is all the walker is asked about.

    Both mutations are ones the old literal `goto do_copy` test measured GREEN
    on: a differently-spelled jump, and a deleted `exit /b 1` that falls
    through into the next label.
    """
    assert "do_copy" not in _labels_reachable_from(
        _REFUSAL_SHAPED_BATCH, "pfgm_refuse")

    forced = _REFUSAL_SHAPED_BATCH.replace(
        "exit /b 1", "if defined PFGM_FORCE goto pfgm_stale_tool\nexit /b 1", 1)
    assert forced != _REFUSAL_SHAPED_BATCH
    assert "do_copy" in _labels_reachable_from(forced, "pfgm_refuse")

    dropped = _REFUSAL_SHAPED_BATCH.replace("exit /b 1", "", 1)
    assert dropped != _REFUSAL_SHAPED_BATCH
    assert "do_copy" in _labels_reachable_from(dropped, "pfgm_refuse")
