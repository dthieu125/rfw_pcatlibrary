# Robot Framework PCAT Library

Robot Framework library này bọc PCAT command line interface để automation các workflow thường gặp:

- Liệt kê device, protocol, plugin và đọc version PCAT.
- Reset, crash, hoặc đưa device vào EDL.
- Thu crash dump/RAM dump.
- Backup/restore xQCN hoặc CEFS.
- Thao tác EFS: list, create, copy, delete.
- Thao tác MBN: list, load, select, activate, deactivate, remove.
- Read/write NV item.
- Flatten meta build, tạo digest, software download, đọc flash info, UFS provision.

> Repository này cố ý không chứa user manual hoặc text trích xuất từ manual.

## Install

```powershell
python -m pip install -e .
```

PCAT CLI cần được cài trên máy chạy test và có thể gọi bằng lệnh `PCAT`, hoặc truyền path qua `pcat_path`.

## Robot Framework usage

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

Download Meta Build
    Download Build
    ...    ${DEVICE}
    ...    C:\\build\\contents.xml
    ...    memory_type=UFS
    ...    flavor=asic
    ...    reset=${TRUE}
```

## Dry-run mode

`dry_run=True` chỉ trả về command đã build, không gọi PCAT. Chế độ này hữu ích cho CI hoặc review keyword.

```robot
*** Settings ***
Library    PCATLibrary    dry_run=${TRUE}

*** Test Cases ***
Preview Command
    ${result}=    Download Build    8c937456    C:\\build\\contents.xml    memory_type=UFS    flavor=asic
    Log    ${result.command_line}
```

## Python usage

```python
from PCATLibrary import PCATLibrary

pcat = PCATLibrary(dry_run=True)
result = pcat.download_build("8c937456", r"C:\build\contents.xml", memory_type="UFS", flavor="asic")
print(result["command"])
```

## Return value

Mỗi keyword trả về dictionary:

- `command`: list argument đã gửi cho subprocess.
- `command_line`: command đã quote để dễ log.
- `rc`: exit code.
- `stdout`: standard output.
- `stderr`: standard error.
- `dry_run`: `True/False`.

Khi `check=True` và PCAT trả exit code khác 0, keyword sẽ fail bằng `AssertionError`.
