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

from pathlib import Path
import struct

import pytest

from pirateforce_foundation.gm import plugin_image_check as pic


_PE_OFFSET = 0x80
_FILE_ALIGN = 0x200


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
    if with_manifest:
        # Root directory: 16-byte header, then one id entry for RT_MANIFEST.
        resource_dir_rva = place(
            struct.pack("<IIHHHH", 0, 0, 0, 0, 0, 1)
            + struct.pack("<II", pic._RT_MANIFEST, 0)
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
            0x18 if resource_dir_rva else 0,
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
