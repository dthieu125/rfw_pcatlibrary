# Robot Framework PCAT Library

This Robot Framework library wraps the PCAT command line interface for common device
automation workflows:

- List devices, protocols, licensed plugins, and PCAT version information.
- Reset, crash, or force a device into EDL mode.
- Collect crash dumps and RAM dumps.
- Back up or restore xQCN and CEFS files.
- Work with EFS files and directories: list, create, copy, and delete.
- Work with MBN configurations: list, load, select, activate, deactivate, and remove.
- Read and write NV items.
- Flatten meta builds, create digest files, run software downloads, read flash info, and
  perform UFS provisioning.
- Flash a meta build, print the PCAT log to the Robot console, and validate success markers.

> This repository intentionally does not include the PCAT user manual or extracted manual text.

## Install

```powershell
python -m pip install -e .
```

PCAT CLI must be installed on the test machine and callable as `PCAT`, or you can pass an
explicit executable path through `pcat_path`.

## Robot Framework Usage

```robot
*** Settings ***
Library    PCATLibrary    pcat_path=PCAT    timeout=1800

*** Variables ***
${DEVICE}    8c937456

*** Test Cases ***
Read Device And NV
    ${devices}=    List Devices
    Log    ${devices.stdout}
    ${nv}=    Read NV Item    ${DEVICE}    esn
    Should Be Equal As Integers    ${nv.rc}    0

Backup XQCN
    Backup XQCN    ${DEVICE}    C:\\TEMP\\backup.xqcn    spc=000000
```

## Flash Meta Build

`Flash Meta Build` is a convenience keyword for flashing `contents.xml` through the Software
Download plugin. After the flash, it prints the PCAT output to the Robot console and checks the
configured success markers.

```robot
*** Settings ***
Library    PCATLibrary    pcat_path=PCAT    timeout=3600

*** Variables ***
${DEVICE}        8c937456
${CONTENTS_XML}  C:\\build\\contents.xml

*** Test Cases ***
Flash Meta Build Successfully
    ${result}=    Flash Meta Build
    ...    ${DEVICE}
    ...    ${CONTENTS_XML}
    ...    memory_type=UFS
    ...    flavor=asic
    ...    reset=${TRUE}
    Should Be True    ${result.success}
```

The default success markers are defined in code as:

```python
PCAT_FLASH_SUCCESS_MARKERS = ["FLASH SUCCESS", "NO ERROR"]
```

You can override them from Robot when you learn the full set of required PCAT log strings:

```robot
Set Flash Success Markers    FLASH SUCCESS    NO ERROR    YOUR_NEXT_MARKER
```

You can also validate a saved log file or a command result:

```robot
${log}=    Fetch PCAT Log    C:\\TEMP\\pcat_flash.log
Verify Flash Log Success    ${log}
```

## UFS Provisioning

```robot
*** Test Cases ***
Provision UFS
    ${result}=    UFS Provision
    ...    ${DEVICE}
    ...    C:\\build
    ...    C:\\build\\provision.xml
    ...    memory_type=UFS
    ...    flavor=asic
```

## Dry-Run Mode

`dry_run=True` returns the command that would be executed without calling PCAT. This is useful
for CI checks and keyword review.

```robot
*** Settings ***
Library    PCATLibrary    dry_run=${TRUE}

*** Test Cases ***
Preview Command
    ${result}=    Flash Meta Build    8c937456    C:\\build\\contents.xml    memory_type=UFS
    Log    ${result.command_line}
```

## Python Usage

```python
from PCATLibrary import PCATLibrary

pcat = PCATLibrary(dry_run=True)
result = pcat.flash_meta_build("8c937456", r"C:\build\contents.xml", memory_type="UFS")
print(result["command"])
```

## Return Value

Each keyword returns a dictionary:

- `command`: argument list sent to subprocess.
- `command_line`: shell-quoted command for logging.
- `rc`: exit code.
- `stdout`: standard output.
- `stderr`: standard error.
- `dry_run`: `True/False`.
- `pcat_log`: combined PCAT output for flash-related keywords when log fetching is enabled.
- `success`: flash log verification result for flash keywords when verification is enabled.
- `success_markers`: success markers used for flash log verification.
- `missing_success_markers`: missing success markers, if any.

When `check=True` and PCAT returns a non-zero exit code, the keyword fails with `AssertionError`.
