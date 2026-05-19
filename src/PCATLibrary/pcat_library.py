"""Keyword library that wraps the PCAT command line tool.

The implementation intentionally keeps a small surface area around subprocess execution:
keywords build a PCAT argument list, then one runner handles logging, dry-run, timeout,
and failure behavior consistently.
"""

from __future__ import annotations

import shlex
import subprocess
from pathlib import Path
from typing import Any, Iterable

from robot.api import logger
from robot.api.deco import keyword, library


PCAT_FLASH_SUCCESS_MARKERS = ["FLASH SUCCESS", "NO ERROR"]


@library(scope="GLOBAL", version="0.1.0", auto_keywords=False)
class PCATLibrary:
    """Robot Framework library for PCAT CLI workflows."""

    ROBOT_LIBRARY_SCOPE = "GLOBAL"
    ROBOT_LIBRARY_VERSION = "0.1.0"

    def __init__(
        self,
        pcat_path: str = "PCAT",
        timeout: int | float = 600,
        dry_run: bool = False,
        check: bool = True,
        flash_success_markers: str | Iterable[str] | None = None,
    ) -> None:
        self.pcat_path = str(pcat_path)
        self.timeout = float(timeout)
        self.dry_run = self._to_bool(dry_run)
        self.check = self._to_bool(check)
        self.flash_success_markers = self._normalize_markers(
            flash_success_markers if flash_success_markers is not None else PCAT_FLASH_SUCCESS_MARKERS
        )

    @keyword("Run PCAT")
    def run_pcat(
        self,
        *args: Any,
        timeout: int | float | None = None,
        check: bool | None = None,
        dry_run: bool | None = None,
    ) -> dict[str, Any]:
        """Run PCAT with raw arguments.

        Examples:
        | ${result}= | Run PCAT | -HELP |
        | ${result}= | Run PCAT | -HELP | -PLUGIN | SD |
        """

        command = [self.pcat_path, *self._normalize_args(args)]
        return self._run(command, timeout=timeout, check=check, dry_run=dry_run)

    @keyword("Get Version")
    def get_version(self) -> dict[str, Any]:
        """Display PCAT version information."""

        return self.run_pcat("-VERSION")

    @keyword("Show Help")
    def show_help(self, plugin: str | None = None) -> dict[str, Any]:
        """Show PCAT help, optionally for a plugin name or ID."""

        args: list[Any] = ["-HELP"]
        if plugin:
            args.extend(["-PLUGIN", plugin])
        return self.run_pcat(*args)

    @keyword("List Plugins")
    def list_plugins(self) -> dict[str, Any]:
        """List licensed PCAT plugins or add-ons."""

        return self.run_pcat("-PLUGINS")

    @keyword("List Devices")
    def list_devices(self) -> dict[str, Any]:
        """List available Qualcomm devices on the machine."""

        return self.run_pcat("-DEVICES")

    @keyword("List Protocols")
    def list_protocols(self, device: str) -> dict[str, Any]:
        """List available protocols on a device."""

        return self.run_pcat("-PROTOCOLS", "-DEVICE", device)

    @keyword("Reset Device")
    def reset_device(self, device: str) -> dict[str, Any]:
        """Reset a device."""

        return self._device_mode("RESET", device)

    @keyword("Crash Device")
    def crash_device(self, device: str) -> dict[str, Any]:
        """Crash a device."""

        return self._device_mode("CRASH", device)

    @keyword("Force EDL")
    def force_edl(self, device: str) -> dict[str, Any]:
        """Force a device to EDL mode."""

        return self._device_mode("EDL", device)

    @keyword("Monitor Memory Dump")
    def monitor_memory_dump(
        self,
        dump_dir: str | None = None,
        reset: bool | str | None = None,
        skip_8k: bool | str | None = None,
        skip_9k: bool | str | None = None,
        unique_timestamp: bool | str | None = None,
    ) -> dict[str, Any]:
        """Monitor connected devices and download memory dumps."""

        args: list[Any] = ["-MONITORMEMDUMP"]
        self._add_optional(args, "-DUMPDIR", dump_dir)
        self._add_optional_bool(args, "-RESET", reset)
        self._add_optional_bool(args, "-SKIP8K", skip_8k)
        self._add_optional_bool(args, "-SKIP9K", skip_9k)
        self._add_optional_bool(args, "-UNIQUETS", unique_timestamp)
        return self.run_pcat(*args)

    @keyword("Collect Memory Dump")
    def collect_memory_dump(
        self,
        device: str,
        dump_dir: str | None = None,
        reset: bool | str | None = True,
        skip_8k: bool | str | None = None,
        skip_9k: bool | str | None = None,
        unique_timestamp: bool | str | None = None,
        device_type: str | None = None,
    ) -> dict[str, Any]:
        """Collect crash/RAM dump from a device using the Crash Collection plugin."""

        args = self._plugin_args("CC", device, device_type)
        self._add_optional(args, "-DUMPDIR", dump_dir)
        self._add_optional_bool(args, "-RESET", reset)
        self._add_optional_bool(args, "-SKIP8K", skip_8k)
        self._add_optional_bool(args, "-SKIP9K", skip_9k)
        self._add_optional_bool(args, "-UNIQUETS", unique_timestamp)
        return self.run_pcat(*args)

    @keyword("Backup XQCN")
    def backup_xqcn(
        self,
        device: str,
        file_path: str,
        spc: str = "000000",
        timeout_ms: int | str | None = 120000,
        device_type: str | None = None,
    ) -> dict[str, Any]:
        """Backup XQCN contents from the device."""

        return self._xqcn(
            device,
            mode="BACKUP",
            file_path=file_path,
            spc=spc,
            timeout_ms=timeout_ms,
            device_type=device_type,
        )

    @keyword("Restore XQCN")
    def restore_xqcn(
        self,
        device: str,
        file_path: str | Iterable[str],
        spc: str = "000000",
        timeout_ms: int | str | None = 120000,
        esn_mismatch: bool | str | None = True,
        reset: bool | str | None = True,
        filter_value: str | None = None,
        multiple_xqcns: bool | str | None = None,
        device_type: str | None = None,
    ) -> dict[str, Any]:
        """Restore one or more XQCN files to the device."""

        if not isinstance(file_path, str):
            file_path = ";".join(str(path) for path in file_path)
            if multiple_xqcns is None:
                multiple_xqcns = True
        return self._xqcn(
            device,
            mode="RESTORE",
            file_path=file_path,
            spc=spc,
            timeout_ms=timeout_ms,
            esn_mismatch=esn_mismatch,
            reset=reset,
            filter_value=filter_value,
            multiple_xqcns=multiple_xqcns,
            device_type=device_type,
        )

    @keyword("Backup CEFS")
    def backup_cefs(
        self,
        device: str,
        file_path: str,
        file_system: str = "PRI",
        device_type: str | None = None,
    ) -> dict[str, Any]:
        """Backup CEFS/MBN contents from the device."""

        return self._xqcn(
            device,
            mode="BACKUP",
            file_path=file_path,
            xqcn_type="CEFS",
            file_system=file_system,
            device_type=device_type,
        )

    @keyword("List EFS")
    def list_efs(
        self,
        device: str,
        value: str = "/",
        file_system: str = "PRI",
        view: str = "TABLE",
        device_type: str | None = None,
    ) -> dict[str, Any]:
        """Read EFS items from the device."""

        args = self._efs_base(device, file_system, device_type)
        args.extend(["-VIEW", view, "-VALUE", value])
        return self.run_pcat(*args)

    @keyword("Create EFS Directory")
    def create_efs_directory(
        self,
        device: str,
        path: str,
        file_system: str = "PRI",
        device_type: str | None = None,
    ) -> dict[str, Any]:
        """Create an EFS directory on the device."""

        return self._efs_action(device, "CREATE", "DIR", file_system, value=path, device_type=device_type)

    @keyword("Create EFS File")
    def create_efs_file(
        self,
        device: str,
        host_path: str,
        device_path: str,
        file_system: str = "PRI",
        device_type: str | None = None,
    ) -> dict[str, Any]:
        """Create an EFS file from host machine to the device."""

        return self._efs_action(
            device,
            "CREATE",
            "FILE",
            file_system,
            from_path=host_path,
            to_path=device_path,
            device_type=device_type,
        )

    @keyword("Copy File To EFS")
    def copy_file_to_efs(
        self,
        device: str,
        host_path: str,
        device_path: str,
        file_system: str = "PRI",
        override: bool | str | None = None,
        device_type: str | None = None,
    ) -> dict[str, Any]:
        """Copy a file from host machine to EFS."""

        return self._efs_action(
            device,
            "COPY",
            "FILE",
            file_system,
            from_path=host_path,
            to_path=device_path,
            override=override,
            device_type=device_type,
        )

    @keyword("Copy File From EFS")
    def copy_file_from_efs(
        self,
        device: str,
        device_path: str,
        host_path: str,
        file_system: str = "PRI",
        override: bool | str | None = None,
        device_type: str | None = None,
    ) -> dict[str, Any]:
        """Copy a file from EFS to host machine."""

        return self._efs_action(
            device,
            "COPY",
            "FILE",
            file_system,
            from_path=device_path,
            to_path=host_path,
            override=override,
            device_type=device_type,
        )

    @keyword("Delete EFS Path")
    def delete_efs_path(
        self,
        device: str,
        path: str,
        path_type: str = "FILE",
        file_system: str = "PRI",
        override: bool | str | None = None,
        device_type: str | None = None,
    ) -> dict[str, Any]:
        """Delete an EFS file or directory."""

        return self._efs_action(
            device,
            "DELETE",
            path_type,
            file_system,
            value=path,
            override=override,
            device_type=device_type,
        )

    @keyword("List MBN")
    def list_mbn(
        self,
        device: str,
        view: str = "TABLE",
        type_filter: str | None = None,
        data_filter: str | None = None,
        over_diag: bool | str | None = None,
        device_type: str | None = None,
    ) -> dict[str, Any]:
        """Read MBN items from the device."""

        args = self._plugin_args("MD", device, device_type)
        args.extend(["-VIEW", view])
        self._add_optional(args, "-TYPEFILTER", type_filter)
        self._add_optional(args, "-DATAFILTER", data_filter)
        self._add_optional_bool(args, "-OVERDIAG", over_diag)
        return self.run_pcat(*args)

    @keyword("Select MBN")
    def select_mbn(
        self,
        device: str,
        mbn_id: str,
        subscription: int | str = 0,
        device_type: str | None = None,
    ) -> dict[str, Any]:
        """Select an MBN item by ID or description."""

        return self._mbn_mode(device, "SEL", mbn_id, subscription, device_type)

    @keyword("Activate MBN")
    def activate_mbn(
        self,
        device: str,
        mbn_id: str,
        subscription: int | str = 0,
        device_type: str | None = None,
    ) -> dict[str, Any]:
        """Activate an MBN item by ID or description."""

        return self._mbn_mode(device, "ACT", mbn_id, subscription, device_type)

    @keyword("Deactivate MBN")
    def deactivate_mbn(
        self,
        device: str,
        mbn_id: str,
        subscription: int | str = 0,
        device_type: str | None = None,
    ) -> dict[str, Any]:
        """Deactivate an MBN item by ID or description."""

        return self._mbn_mode(device, "DEACT", mbn_id, subscription, device_type)

    @keyword("Load MBN")
    def load_mbn(self, device: str, mbn_path: str, device_type: str | None = None) -> dict[str, Any]:
        """Load an MBN file to the device."""

        args = self._plugin_args("MD", device, device_type)
        args.extend(["-LOAD", mbn_path])
        return self.run_pcat(*args)

    @keyword("Remove MBN")
    def remove_mbn(self, device: str, mbn_id: str, device_type: str | None = None) -> dict[str, Any]:
        """Remove an MBN item from the device."""

        args = self._plugin_args("MD", device, device_type)
        args.extend(["-REMOVE", mbn_id])
        return self.run_pcat(*args)

    @keyword("Read NV Item")
    def read_nv_item(
        self,
        device: str,
        nv_item: int | str,
        subscription: int | str | None = None,
        device_type: str | None = None,
    ) -> dict[str, Any]:
        """Read an NV item by number or name."""

        args = self._nv_base(device, "READ", nv_item, subscription, device_type)
        return self.run_pcat(*args)

    @keyword("Write NV Item")
    def write_nv_item(
        self,
        device: str,
        nv_item: int | str,
        value: str,
        subscription: int | str | None = None,
        json_value: bool | str | None = None,
        device_type: str | None = None,
    ) -> dict[str, Any]:
        """Write an NV item by number or name."""

        args = self._nv_base(device, "WRITE", nv_item, subscription, device_type)
        self._add_optional_bool(args, "-JSON", json_value)
        args.extend(["-VALUE", value])
        return self.run_pcat(*args)

    @keyword("Flatten Meta Build")
    def flatten_meta_build(
        self,
        build: str,
        memory_type: str,
        flavor: str,
        out_dir: str,
        device_programmer: str | None = None,
    ) -> dict[str, Any]:
        """Flatten a meta build."""

        args: list[Any] = [
            "-FLATTEN",
            "-BUILD",
            build,
            "-MEMORYTYPE",
            memory_type,
            "-FLAVOR",
            flavor,
            "-OUT",
            out_dir,
        ]
        self._add_optional(args, "-DEVICEPROG", device_programmer)
        return self.run_pcat(*args)

    @keyword("Create Digest")
    def create_digest(
        self,
        build: str,
        memory_type: str,
        out_dir: str,
        erase: bool | str | None = True,
        reset: bool | str | None = None,
        slot: int | str | None = 0,
        digest_type: str | None = "VIP",
        digest_header_type: str | None = None,
        flavor: str | None = None,
        device_programmer: str | None = None,
        raw_program: str | Iterable[str] | None = None,
        patch_program: str | Iterable[str] | None = None,
    ) -> dict[str, Any]:
        """Create a digest file for VIP or build validation download."""

        args: list[Any] = ["-DIGEST", "-BUILD", build, "-MEMORYTYPE", memory_type]
        self._add_optional(args, "-FLAVOR", flavor)
        self._add_optional(args, "-DEVICEPROG", device_programmer)
        self._add_optional_bool(args, "-ERASE", erase)
        self._add_optional_bool(args, "-RESET", reset)
        self._add_optional(args, "-SLOT", slot)
        self._add_optional(args, "-DIGESTTYPE", digest_type)
        self._add_optional(args, "-DIGESTHEADERTYPE", digest_header_type)
        self._add_optional(args, "-RAWPROG", self._join_paths(raw_program))
        self._add_optional(args, "-PATCHPROG", self._join_paths(patch_program))
        args.extend(["-OUT", out_dir])
        return self.run_pcat(*args)

    @keyword("Download Build")
    def download_build(
        self,
        device: str,
        build: str,
        memory_type: str | None = None,
        flavor: str | None = None,
        reset: bool | str | None = None,
        device_programmer: str | None = None,
        skip_sahara: bool | str | None = None,
        erase: bool | str | None = None,
        read_images: bool | str | None = None,
        read_image_path: str | None = None,
        remote_efs_path: str | None = None,
        validation_mode: int | str | None = None,
        chained_digest: str | None = None,
        signed_digest: str | None = None,
        ufs_provision: bool | str | None = None,
        ufs_provision_xml: str | None = None,
        send_xml: str | None = None,
        raw_program: str | Iterable[str] | None = None,
        patch_program: str | Iterable[str] | None = None,
        slot: int | str | None = None,
        flatten: bool | str | None = None,
        flash_info: bool | str | None = None,
        firehose_init_time: int | str | None = None,
        cdt: str | None = None,
        active_partition: str | None = None,
        firehose_rx_timeout: int | str | None = None,
        partition_index: str | None = None,
        device_type: str | None = None,
    ) -> dict[str, Any]:
        """Download a meta, flat, or flashless build using Software Download plugin."""

        args = self._plugin_args("SD", device, device_type)
        args.extend(["-BUILD", build])
        self._add_download_options(
            args,
            memory_type=memory_type,
            flavor=flavor,
            reset=reset,
            device_programmer=device_programmer,
            skip_sahara=skip_sahara,
            erase=erase,
            read_images=read_images,
            read_image_path=read_image_path,
            remote_efs_path=remote_efs_path,
            validation_mode=validation_mode,
            chained_digest=chained_digest,
            signed_digest=signed_digest,
            ufs_provision=ufs_provision,
            ufs_provision_xml=ufs_provision_xml,
            send_xml=send_xml,
            raw_program=raw_program,
            patch_program=patch_program,
            slot=slot,
            flatten=flatten,
            flash_info=flash_info,
            firehose_init_time=firehose_init_time,
            cdt=cdt,
            active_partition=active_partition,
            firehose_rx_timeout=firehose_rx_timeout,
            partition_index=partition_index,
        )
        return self.run_pcat(*args)

    @keyword("Flash Meta Build")
    def flash_meta_build(
        self,
        device: str,
        contents_xml: str,
        memory_type: str = "UFS",
        flavor: str = "asic",
        reset: bool | str | None = True,
        erase: bool | str | None = None,
        slot: int | str | None = None,
        validation_mode: int | str | None = None,
        device_programmer: str | None = None,
        cdt: str | None = None,
        active_partition: str | None = None,
        flatten: bool | str | None = None,
        fetch_log: bool | str = True,
        verify_success: bool | str = True,
        success_markers: str | Iterable[str] | None = None,
        device_type: str | None = None,
    ) -> dict[str, Any]:
        """Flash a PCAT meta build and optionally print/validate the resulting PCAT log.

        The default success markers are stored in the module-level
        ``PCAT_FLASH_SUCCESS_MARKERS`` variable and copied into each library instance.
        """

        result = self.download_build(
            device,
            contents_xml,
            memory_type=memory_type,
            flavor=flavor,
            reset=reset,
            erase=erase,
            slot=slot,
            validation_mode=validation_mode,
            device_programmer=device_programmer,
            cdt=cdt,
            active_partition=active_partition,
            flatten=flatten,
            device_type=device_type,
        )
        if self._to_bool(fetch_log):
            result["pcat_log"] = self.fetch_pcat_log(result)
        if self._to_bool(verify_success) and not result["dry_run"]:
            log_text = result.get("pcat_log") or self._result_log(result)
            verification = self.verify_flash_log_success(log_text, success_markers=success_markers)
            result.update(
                {
                    "success": verification["success"],
                    "success_markers": verification["required_markers"],
                    "missing_success_markers": verification["missing_markers"],
                }
            )
        return result

    @keyword("Get Flash Info")
    def get_flash_info(
        self,
        device: str,
        build: str | None = None,
        memory_type: str | None = None,
        device_programmer: str | None = None,
        slot: int | str | None = None,
        device_type: str | None = None,
    ) -> dict[str, Any]:
        """Retrieve flash storage information."""

        args = self._plugin_args("SD", device, device_type)
        self._add_optional(args, "-BUILD", build)
        self._add_optional(args, "-DEVICEPROG", device_programmer)
        self._add_optional(args, "-MEMORYTYPE", memory_type)
        self._add_optional(args, "-SLOT", slot)
        args.extend(["-FLASHINFO", "TRUE"])
        return self.run_pcat(*args)

    @keyword("Read Images")
    def read_images(
        self,
        device: str,
        build: str,
        read_image_path: str,
        memory_type: str,
        flavor: str | None = None,
        device_type: str | None = None,
    ) -> dict[str, Any]:
        """Read firmware images from the device."""

        return self.download_build(
            device,
            build,
            memory_type=memory_type,
            flavor=flavor,
            read_images=True,
            read_image_path=read_image_path,
            device_type=device_type,
        )

    @keyword("UFS Provision")
    def ufs_provision(
        self,
        device: str,
        build: str,
        provision_xml: str,
        memory_type: str = "UFS",
        flavor: str | None = None,
        reset: bool | str | None = None,
        fetch_log: bool | str = True,
        verify_success: bool | str = False,
        success_markers: str | Iterable[str] | None = None,
        device_type: str | None = None,
    ) -> dict[str, Any]:
        """Perform UFS provisioning and optionally print/validate the resulting PCAT log."""

        result = self.download_build(
            device,
            build,
            memory_type=memory_type,
            flavor=flavor,
            reset=reset,
            ufs_provision=True,
            ufs_provision_xml=provision_xml,
            device_type=device_type,
        )
        if self._to_bool(fetch_log):
            result["pcat_log"] = self.fetch_pcat_log(result)
        if self._to_bool(verify_success) and not result["dry_run"]:
            log_text = result.get("pcat_log") or self._result_log(result)
            verification = self.verify_flash_log_success(log_text, success_markers=success_markers)
            result.update(
                {
                    "success": verification["success"],
                    "success_markers": verification["required_markers"],
                    "missing_success_markers": verification["missing_markers"],
                }
            )
        return result

    @keyword("Fetch PCAT Log")
    def fetch_pcat_log(self, source: dict[str, Any] | str | Path) -> str:
        """Fetch PCAT log text from a command result or a log file path and print it to console."""

        if isinstance(source, dict):
            log_text = self._result_log(source)
        else:
            log_text = Path(source).read_text(encoding="utf-8", errors="replace")

        if log_text.strip():
            logger.console(log_text)
        return log_text

    @keyword("Verify Flash Log Success")
    def verify_flash_log_success(
        self,
        log_text: str,
        success_markers: str | Iterable[str] | None = None,
        case_sensitive: bool | str = False,
    ) -> dict[str, Any]:
        """Verify that a flash log contains all configured success markers."""

        required_markers = self._normalize_markers(
            success_markers if success_markers is not None else self.flash_success_markers
        )
        haystack = log_text if self._to_bool(case_sensitive) else log_text.upper()
        missing_markers = [
            marker
            for marker in required_markers
            if (marker if self._to_bool(case_sensitive) else marker.upper()) not in haystack
        ]
        if missing_markers:
            raise AssertionError(
                "PCAT flash log is missing success marker(s): "
                + ", ".join(missing_markers)
            )
        return {
            "success": True,
            "required_markers": required_markers,
            "missing_markers": missing_markers,
        }

    @keyword("Set Flash Success Markers")
    def set_flash_success_markers(self, *markers: str) -> list[str]:
        """Set the success markers used by flash log verification."""

        self.flash_success_markers = self._normalize_markers(markers)
        return self.flash_success_markers

    @keyword("Get Flash Success Markers")
    def get_flash_success_markers(self) -> list[str]:
        """Return the success markers used by flash log verification."""

        return list(self.flash_success_markers)

    def _run(
        self,
        command: list[str],
        timeout: int | float | None = None,
        check: bool | None = None,
        dry_run: bool | None = None,
    ) -> dict[str, Any]:
        dry_run_value = self.dry_run if dry_run is None else self._to_bool(dry_run)
        result = {
            "command": command,
            "command_line": self._command_line(command),
            "rc": 0,
            "stdout": "",
            "stderr": "",
            "dry_run": dry_run_value,
        }
        if dry_run_value:
            return result

        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=self.timeout if timeout is None else float(timeout),
            check=False,
        )
        result.update(
            {
                "rc": completed.returncode,
                "stdout": completed.stdout,
                "stderr": completed.stderr,
            }
        )

        check_value = self.check if check is None else self._to_bool(check)
        if check_value and completed.returncode != 0:
            raise AssertionError(
                f"PCAT command failed with rc={completed.returncode}: "
                f"{result['command_line']}\n{completed.stderr}"
            )
        return result

    def _device_mode(self, mode: str, device: str) -> dict[str, Any]:
        return self.run_pcat("-MODE", mode, "-DEVICE", device)

    def _plugin_args(
        self,
        plugin: str,
        device: str,
        device_type: str | None = None,
    ) -> list[Any]:
        args: list[Any] = ["-PLUGIN", plugin, "-DEVICE", device]
        self._add_optional(args, "-DEVICETYPE", device_type)
        return args

    def _xqcn(
        self,
        device: str,
        mode: str,
        file_path: str,
        xqcn_type: str | None = None,
        spc: str | None = None,
        timeout_ms: int | str | None = None,
        filter_value: str | None = None,
        esn_mismatch: bool | str | None = None,
        reset: bool | str | None = None,
        multiple_xqcns: bool | str | None = None,
        file_system: str | None = None,
        device_type: str | None = None,
    ) -> dict[str, Any]:
        args = self._plugin_args("DC", device, device_type)
        args.extend(["-MODE", mode, "-FILEPATH", file_path])
        self._add_optional(args, "-TYPE", xqcn_type)
        self._add_optional(args, "-SPC", spc)
        self._add_optional(args, "-TIMEOUT", timeout_ms)
        self._add_optional(args, "-FILTER", filter_value)
        self._add_optional_bool(args, "-ESNMISMATCH", esn_mismatch)
        self._add_optional_bool(args, "-RESET", reset)
        self._add_optional_bool(args, "-MULXQCNS", multiple_xqcns)
        self._add_optional(args, "-FS", file_system)
        return self.run_pcat(*args)

    def _efs_base(
        self,
        device: str,
        file_system: str,
        device_type: str | None = None,
    ) -> list[Any]:
        args = self._plugin_args("EE", device, device_type)
        args.extend(["-FS", file_system])
        return args

    def _efs_action(
        self,
        device: str,
        mode: str,
        path_type: str,
        file_system: str,
        value: str | None = None,
        from_path: str | None = None,
        to_path: str | None = None,
        override: bool | str | None = None,
        device_type: str | None = None,
    ) -> dict[str, Any]:
        args = self._efs_base(device, file_system, device_type)
        args.extend(["-MODE", mode, "-TYPE", path_type])
        self._add_optional(args, "-VALUE", value)
        self._add_optional(args, "-FROM", from_path)
        self._add_optional(args, "-TO", to_path)
        self._add_optional_bool(args, "-OVERRIDE", override)
        return self.run_pcat(*args)

    def _mbn_mode(
        self,
        device: str,
        mode: str,
        mbn_id: str,
        subscription: int | str,
        device_type: str | None = None,
    ) -> dict[str, Any]:
        args = self._plugin_args("MD", device, device_type)
        args.extend(["-MODE", mode, "-SUB", subscription, "-ID", mbn_id])
        return self.run_pcat(*args)

    def _nv_base(
        self,
        device: str,
        mode: str,
        nv_item: int | str,
        subscription: int | str | None = None,
        device_type: str | None = None,
    ) -> list[Any]:
        args = self._plugin_args("NB", device, device_type)
        args.extend(["-MODE", mode, "-NVITEM", nv_item])
        self._add_optional(args, "-SUB", subscription)
        return args

    def _add_download_options(self, args: list[Any], **options: Any) -> None:
        mapping = [
            ("-MEMORYTYPE", "memory_type", False),
            ("-FLAVOR", "flavor", False),
            ("-RESET", "reset", True),
            ("-DEVICEPROG", "device_programmer", False),
            ("-SKIPSAHARA", "skip_sahara", True),
            ("-ERASE", "erase", True),
            ("-READIMAGES", "read_images", True),
            ("-READIMAGEPATH", "read_image_path", False),
            ("-REMOTEEFSPATH", "remote_efs_path", False),
            ("-VALDMODE", "validation_mode", False),
            ("-CHAINEDDIGEST", "chained_digest", False),
            ("-SIGNEDDIGEST", "signed_digest", False),
            ("-UFSPROV", "ufs_provision", True),
            ("-UFSPROVXML", "ufs_provision_xml", False),
            ("-SENDXML", "send_xml", False),
            ("-RAWPROG", "raw_program", False),
            ("-PATCHPROG", "patch_program", False),
            ("-SLOT", "slot", False),
            ("-FLATTEN", "flatten", True),
            ("-FLASHINFO", "flash_info", True),
            ("-FHINITTIME", "firehose_init_time", False),
            ("-CDT", "cdt", False),
            ("-ACTIVEPARTITION", "active_partition", False),
            ("-FHRXTIMEOUT", "firehose_rx_timeout", False),
            ("-PARTITIONINDEX", "partition_index", False),
        ]
        for flag, key, is_bool in mapping:
            value = options[key]
            if key in {"raw_program", "patch_program"}:
                value = self._join_paths(value)
            if is_bool:
                self._add_optional_bool(args, flag, value)
            else:
                self._add_optional(args, flag, value)

    @staticmethod
    def _add_optional(args: list[Any], flag: str, value: Any) -> None:
        if value is not None and value != "":
            args.extend([flag, value])

    def _add_optional_bool(self, args: list[Any], flag: str, value: Any) -> None:
        if value is not None and value != "":
            args.extend([flag, self._pcat_bool(value)])

    @staticmethod
    def _normalize_args(args: Iterable[Any]) -> list[str]:
        normalized: list[str] = []
        for arg in args:
            if arg is None or arg == "":
                continue
            if isinstance(arg, Path):
                normalized.append(str(arg))
            else:
                normalized.append(str(arg))
        return normalized

    @staticmethod
    def _join_paths(value: str | Iterable[str] | None) -> str | None:
        if value is None or isinstance(value, str):
            return value
        return ";".join(str(item) for item in value)

    @staticmethod
    def _normalize_markers(markers: str | Iterable[str]) -> list[str]:
        if isinstance(markers, str):
            marker_items = markers.split("|") if "|" in markers else markers.split(",")
        else:
            marker_items = list(markers)
        return [str(marker).strip() for marker in marker_items if str(marker).strip()]

    @staticmethod
    def _result_log(result: dict[str, Any]) -> str:
        stdout = result.get("stdout") or ""
        stderr = result.get("stderr") or ""
        return "\n".join(part for part in (stdout, stderr) if part)

    @staticmethod
    def _to_bool(value: bool | str | int | None) -> bool:
        if isinstance(value, bool):
            return value
        if value is None:
            return False
        if isinstance(value, int):
            return value != 0
        return str(value).strip().lower() in {"1", "true", "yes", "y", "on", "${true}"}

    def _pcat_bool(self, value: bool | str | int) -> str:
        if isinstance(value, str) and value.strip().upper() in {"TRUE", "FALSE"}:
            return value.strip().upper()
        return "TRUE" if self._to_bool(value) else "FALSE"

    @staticmethod
    def _command_line(command: list[str]) -> str:
        return " ".join(shlex.quote(part) for part in command)
