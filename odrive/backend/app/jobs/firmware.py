"""Guarded firmware update to the official ODrive 0.5.6 release (v3.6-56V build).

Flow: preconditions -> download .elf -> convert to .hex -> user checklist ->
release the usb device -> run `odrivetool dfu` -> reconnect -> verify the
version and the bus-voltage scaling against a multimeter reading.
"""

from __future__ import annotations

import asyncio
import hashlib
import os
import struct
import sys
from pathlib import Path

import requests
from intelhex import IntelHex

from ..paths import FIRMWARE_DIR
from ..storage import list_backups
from . import JobCtx, job

RELEASE = "fw-v0.5.6"
ASSET = "ODriveFirmware_v3.6-56V.elf"
URL = f"https://github.com/odriverobotics/ODrive/releases/download/{RELEASE}/{ASSET}"


def elf_to_hex(elf: bytes) -> IntelHex:
    """Convert the loadable segments of a 32-bit little-endian ELF into Intel HEX.

    Args:
        elf: raw .elf file contents.
    Returns:
        an IntelHex object addressed by the segments' physical (flash) addresses.
    """
    if elf[:4] != b"\x7fELF" or elf[4] != 1 or elf[5] != 1:
        raise ValueError("not a 32-bit little-endian ELF file")
    phoff, = struct.unpack_from("<I", elf, 0x1C)
    phentsize, phnum = struct.unpack_from("<HH", elf, 0x2A)
    ih = IntelHex()
    for i in range(phnum):
        p_type, p_offset, _vaddr, p_paddr, p_filesz, _memsz, _flags, _align = struct.unpack_from("<8I", elf, phoff + i * phentsize)
        # PT_LOAD segments with file content are what gets flashed
        if p_type == 1 and p_filesz > 0:
            ih.frombytes(elf[p_offset:p_offset + p_filesz], offset=p_paddr)
    if not len(ih):
        raise ValueError("ELF has no loadable segments")
    return ih


def _odrivetool() -> list[str]:
    """Command prefix that runs odrivetool from this python environment."""
    if getattr(sys, "frozen", False):
        raise ValueError("firmware flashing needs the source install (python run.py), not the packaged exe")
    scripts = Path(sys.executable).parent
    tool = scripts / "odrivetool"
    return [sys.executable, str(tool)]


@job("firmware_flash", "Firmware update to 0.5.6 (v3.6-56V)", energizes=False, confirm=True)
async def firmware_flash(ctx: JobCtx, params: dict) -> dict:
    """Flash the official 0.5.6 56V firmware with every precondition checked first."""
    w = ctx.worker
    info = w.info.to_json() if w.info else {}
    if not w.connected:
        raise ValueError("device not connected")
    if not info.get("hw", "").startswith("3.6-56"):
        raise ValueError(f"board reports hw {info.get('hw')}; this job only flashes v3.6-56V")
    if ctx.safety.active_axes:
        raise ValueError("disarm all axes first")
    backups = [b for b in list_backups() if (b.get("device") or {}).get("serial") == info.get("serial")]
    if not backups:
        raise ValueError("make a config backup of this board first (Firmware > Backup config)")
    ctx.log(f"latest config backup: {backups[0]['id']}")

    FIRMWARE_DIR.mkdir(parents=True, exist_ok=True)
    elf_path = FIRMWARE_DIR / f"{RELEASE}_{ASSET}"
    hex_path = elf_path.with_suffix(".hex")
    if not elf_path.exists():
        ctx.log(f"downloading {URL}")
        resp = await asyncio.to_thread(requests.get, URL, timeout=60)
        resp.raise_for_status()
        elf_path.write_bytes(resp.content)
    elf = elf_path.read_bytes()
    sha = hashlib.sha256(elf).hexdigest()
    ih = elf_to_hex(elf)
    ih.write_hex_file(str(hex_path))
    ctx.log(f"firmware {ASSET}: {len(elf)} bytes, sha256 {sha[:16]}..., flash range 0x{ih.minaddr():08X}-0x{ih.maxaddr():08X}")
    if ih.minaddr() != 0x08000000:
        raise ValueError("unexpected start address; refusing to flash")
    ctx.progress(0.2)

    ans = await ctx.ask(
        "Before flashing a clone board, confirm ALL of these:\n"
        "1. You dumped the full flash and OTP (0x1FFF7800) with an ST-Link (only way back to the Flipsky firmware).\n"
        "2. The motor is idle and the bus supply is stable.\n"
        "3. On Windows, 'STM32 BOOTLOADER' (VID 0483 PID DF11) has the WinUSB driver (Zadig), or the flash will stall.\n"
        "Flashing official firmware on a Flipsky board can fail if its hardware differs.",
        ["I confirm all three, flash now", "Cancel"],
    )
    if ans.get("choice") != "I confirm all three, flash now":
        ctx.log("cancelled by user")
        return {"flashed": False}

    old_fw = info.get("fw")
    ctx.log("releasing the usb device")
    w.request_reconnect(mode="off")
    for _ in range(50):
        if not w.connected:
            break
        await asyncio.sleep(0.1)
    env = dict(os.environ)
    try:
        import libusb_package

        env["PATH"] = str(Path(libusb_package.get_library_path()).parent) + os.pathsep + env.get("PATH", "")
    except Exception:
        pass
    cmd = _odrivetool() + ["dfu", str(hex_path)]
    ctx.log("running: " + " ".join(cmd))
    proc = await asyncio.create_subprocess_exec(*cmd, stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
                                                stderr=asyncio.subprocess.STDOUT, env=env)
    proc.stdin.write(b"y\n")
    await proc.stdin.drain()
    try:
        while True:
            line = await asyncio.wait_for(proc.stdout.readline(), timeout=240)
            if not line:
                break
            text = line.decode(errors="replace").strip()
            if text:
                ctx.log(text)
        rc = await asyncio.wait_for(proc.wait(), timeout=30)
    except asyncio.TimeoutError:
        proc.kill()
        rc = -1
        ctx.log("odrivetool timed out", "alarm")
    finally:
        w.request_reconnect(mode="auto")
    ctx.progress(0.8)
    if rc != 0:
        raise RuntimeError(f"odrivetool dfu exited with {rc}; the board may be in DFU mode - power-cycle it or retry")

    for _ in range(100):
        if w.connected:
            break
        await asyncio.sleep(0.2)
    if not w.connected:
        raise RuntimeError("board did not come back after flashing")
    new_fw = w.info.to_json()["fw"]
    ctx.log(f"firmware {old_fw} -> {new_fw}")
    vbus = float(await ctx.read1(ctx.p("vbus")))
    ans = await ctx.ask(f"The board reads {vbus:.2f} V on the DC bus. Measure the bus with a multimeter and enter it.", ["Check"],
                        [{"key": "vbus_meter", "label": "multimeter", "unit": "V"}])
    meter = float((ans.get("values") or {}).get("vbus_meter", 0))
    ok = meter > 0 and abs(vbus - meter) / meter < 0.03
    ctx.log(f"vbus scaling {'OK' if ok else 'WRONG'}: board {vbus:.2f} V vs meter {meter:.2f} V", "info" if ok else "alarm")
    if not ok:
        ctx.log("a large mismatch means the voltage divider differs (wrong board variant); do not energize", "alarm")
    ctx.progress(1.0)
    return {"flashed": True, "old_fw": old_fw, "new_fw": new_fw, "vbus_board": vbus, "vbus_meter": meter, "vbus_ok": ok,
            "note": "restore your settings from the config backup; 0.5.6 renamed some paths"}
