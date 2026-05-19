from PCATLibrary import PCATLibrary
from PCATLibrary.pcat_library import PCAT_FLASH_SUCCESS_MARKERS


def test_download_build_command_contains_expected_options():
    library = PCATLibrary(dry_run=True)

    result = library.download_build(
        "8c937456",
        r"C:\build\contents.xml",
        memory_type="UFS",
        flavor="asic",
        slot=1,
        validation_mode=1,
    )

    assert result["dry_run"] is True
    assert result["command"] == [
        "PCAT",
        "-PLUGIN",
        "SD",
        "-DEVICE",
        "8c937456",
        "-BUILD",
        r"C:\build\contents.xml",
        "-MEMORYTYPE",
        "UFS",
        "-FLAVOR",
        "asic",
        "-VALDMODE",
        "1",
        "-SLOT",
        "1",
    ]


def test_restore_multiple_xqcn_joins_paths_and_sets_flag():
    library = PCATLibrary(dry_run=True)

    result = library.restore_xqcn("dev1", [r"C:\a.xqcn", r"C:\b.xqcn"], reset=True)

    assert "-MULXQCNS" in result["command"]
    assert result["command"][result["command"].index("-FILEPATH") + 1] == r"C:\a.xqcn;C:\b.xqcn"
    assert result["command"][result["command"].index("-RESET") + 1] == "TRUE"


def test_copy_file_to_efs_command():
    library = PCATLibrary(dry_run=True)

    result = library.copy_file_to_efs(
        "dev1",
        r"C:\TEMP\test.txt",
        "/test.txt",
        override=True,
    )

    assert result["command"] == [
        "PCAT",
        "-PLUGIN",
        "EE",
        "-DEVICE",
        "dev1",
        "-FS",
        "PRI",
        "-MODE",
        "COPY",
        "-TYPE",
        "FILE",
        "-FROM",
        r"C:\TEMP\test.txt",
        "-TO",
        "/test.txt",
        "-OVERRIDE",
        "TRUE",
    ]


def test_create_digest_joins_raw_and_patch_program_lists():
    library = PCATLibrary(dry_run=True)

    result = library.create_digest(
        r"C:\build",
        "UFS",
        r"C:\out",
        raw_program=[r"C:\build\rawprogram0.xml", r"C:\build\rawprogram1.xml"],
        patch_program=[r"C:\build\patch0.xml", r"C:\build\patch1.xml"],
    )

    assert result["command"][result["command"].index("-RAWPROG") + 1] == (
        r"C:\build\rawprogram0.xml;C:\build\rawprogram1.xml"
    )
    assert result["command"][result["command"].index("-PATCHPROG") + 1] == (
        r"C:\build\patch0.xml;C:\build\patch1.xml"
    )


def test_flash_meta_build_uses_software_download_plugin():
    library = PCATLibrary(dry_run=True)

    result = library.flash_meta_build(
        "dev1",
        r"C:\build\contents.xml",
        memory_type="UFS",
        flavor="asic",
        reset=True,
    )

    assert result["command"] == [
        "PCAT",
        "-PLUGIN",
        "SD",
        "-DEVICE",
        "dev1",
        "-BUILD",
        r"C:\build\contents.xml",
        "-MEMORYTYPE",
        "UFS",
        "-FLAVOR",
        "asic",
        "-RESET",
        "TRUE",
    ]


def test_ufs_provision_command_contains_provision_options():
    library = PCATLibrary(dry_run=True)

    result = library.ufs_provision(
        "dev1",
        r"C:\build",
        r"C:\build\provision.xml",
        flavor="asic",
    )

    assert result["command"] == [
        "PCAT",
        "-PLUGIN",
        "SD",
        "-DEVICE",
        "dev1",
        "-BUILD",
        r"C:\build",
        "-MEMORYTYPE",
        "UFS",
        "-FLAVOR",
        "asic",
        "-UFSPROV",
        "TRUE",
        "-UFSPROVXML",
        r"C:\build\provision.xml",
    ]


def test_verify_flash_log_success_uses_global_default_markers():
    library = PCATLibrary()

    result = library.verify_flash_log_success("flash success\nno error")

    assert result["required_markers"] == PCAT_FLASH_SUCCESS_MARKERS
    assert result["success"] is True


def test_set_flash_success_markers_accepts_multiple_values():
    library = PCATLibrary()

    markers = library.set_flash_success_markers("FLASH SUCCESS", "NO ERROR", "DONE")

    assert markers == ["FLASH SUCCESS", "NO ERROR", "DONE"]
