#!/usr/bin/env python3
"""
Test SCSI vendor command injection via MMIO.

Tests the E1, E3, E8 vendor commands used by patch.py for firmware updates.
These commands should be injected through MMIO to the firmware.
"""

import sys
import struct
sys.path.insert(0, '/home/tiny/fun/asm2464pd-firmware/emulate')

from emu import Emulator

def test_e1_config_write():
    """Test E1 Config Write command injection."""
    print("=" * 70)
    print("TEST: E1 Config Write Command")
    print("=" * 70)

    emu = Emulator()
    emu.load_firmware('/home/tiny/fun/asm2464pd-firmware/fw.bin')

    # Boot
    emu.run(max_cycles=200000)

    # Connect USB
    emu.hw.usb_controller.connect(speed=2)
    emu.run(max_cycles=300000)

    # Build E1 command CDB (from patch.py: struct.pack('>BBB12x', 0xe1, 0x50, 0x0))
    # E1 50 00 - Config write to block 0
    cdb = struct.pack('>BBB', 0xE1, 0x50, 0x00) + bytes(12)

    # Config data (128 bytes)
    config_data = bytes([0x41 + (i % 26) for i in range(128)])  # ABC...

    print(f"Injecting E1 command: CDB={cdb[:3].hex()}")
    print(f"Config data: {config_data[:16].hex()}... ({len(config_data)} bytes)")

    # Inject the command
    emu.hw.inject_scsi_vendor_cmd(0xE1, cdb, config_data, is_write=True)

    # Run firmware to process
    emu.run(max_cycles=500000)

    # Check what happened
    print(f"\nAfter firmware processing:")
    print(f"  IDATA[0x6A] = 0x{emu.memory.idata[0x6A]:02X} (USB state)")
    print(f"  XDATA[0x0002] = 0x{emu.memory.xdata[0x0002]:02X} (CDB opcode)")
    print(f"  XDATA[0x0B02] = 0x{emu.memory.xdata[0x0B02]:02X} (vendor state)")
    print(f"  XDATA[0x8000] = {bytes([emu.memory.xdata[0x8000 + i] for i in range(16)]).hex()} (buffer)")

    return True

def test_e3_firmware_write():
    """Test E3 Firmware Write command injection."""
    print("\n" + "=" * 70)
    print("TEST: E3 Firmware Write Command")
    print("=" * 70)

    emu = Emulator()
    emu.load_firmware('/home/tiny/fun/asm2464pd-firmware/fw.bin')

    # Boot
    emu.run(max_cycles=200000)

    # Connect USB
    emu.hw.usb_controller.connect(speed=2)
    emu.run(max_cycles=300000)

    # Build E3 command CDB (from patch.py: struct.pack('>BBI', 0xe3, 0x50, len(part1)))
    # E3 50 length(4 bytes) - Firmware write part 1
    fw_length = 256  # Test with small chunk
    cdb = struct.pack('>BBI', 0xE3, 0x50, fw_length) + bytes(9)

    # Firmware data
    fw_data = bytes([i & 0xFF for i in range(fw_length)])

    print(f"Injecting E3 command: CDB={cdb[:6].hex()}")
    print(f"Firmware data: {fw_data[:16].hex()}... ({len(fw_data)} bytes)")

    # Inject the command
    emu.hw.inject_scsi_vendor_cmd(0xE3, cdb, fw_data, is_write=True)

    # Run firmware to process
    emu.run(max_cycles=500000)

    # Check what happened
    print(f"\nAfter firmware processing:")
    print(f"  IDATA[0x6A] = 0x{emu.memory.idata[0x6A]:02X} (USB state)")
    print(f"  XDATA[0x0002] = 0x{emu.memory.xdata[0x0002]:02X} (CDB opcode)")
    print(f"  XDATA[0x0B02] = 0x{emu.memory.xdata[0x0B02]:02X} (vendor state)")
    print(f"  XDATA[0x8000] = {bytes([emu.memory.xdata[0x8000 + i] for i in range(16)]).hex()} (buffer)")

    return True

def test_e8_reset():
    """Test E8 Reset/Commit command injection."""
    print("\n" + "=" * 70)
    print("TEST: E8 Reset/Commit Command")
    print("=" * 70)

    emu = Emulator()
    emu.load_firmware('/home/tiny/fun/asm2464pd-firmware/fw.bin')

    # Boot
    emu.run(max_cycles=200000)

    # Connect USB
    emu.hw.usb_controller.connect(speed=2)
    emu.run(max_cycles=300000)

    # Build E8 command CDB (from patch.py: struct.pack('>BB13x', 0xe8, 0x51))
    # E8 51 - Commit flashed firmware
    cdb = struct.pack('>BB', 0xE8, 0x51) + bytes(13)

    print(f"Injecting E8 command: CDB={cdb[:2].hex()}")

    # Inject the command (no data)
    emu.hw.inject_scsi_vendor_cmd(0xE8, cdb, b'', is_write=False)

    # Run firmware to process
    emu.run(max_cycles=500000)

    # Check what happened
    print(f"\nAfter firmware processing:")
    print(f"  IDATA[0x6A] = 0x{emu.memory.idata[0x6A]:02X} (USB state)")
    print(f"  XDATA[0x0002] = 0x{emu.memory.xdata[0x0002]:02X} (CDB opcode)")
    print(f"  XDATA[0x0B02] = 0x{emu.memory.xdata[0x0B02]:02X} (vendor state)")

    return True

def test_mmio_setup():
    """Test that MMIO registers are properly set up."""
    print("\n" + "=" * 70)
    print("TEST: MMIO Register Setup")
    print("=" * 70)

    emu = Emulator()
    emu.load_firmware('/home/tiny/fun/asm2464pd-firmware/fw.bin')

    # Boot
    emu.run(max_cycles=200000)

    # Connect USB
    emu.hw.usb_controller.connect(speed=2)
    emu.run(max_cycles=300000)

    # Build E1 command
    cdb = struct.pack('>BBB', 0xE1, 0x50, 0x00) + bytes(12)
    config_data = bytes(128)

    # Inject but don't run
    emu.hw.inject_scsi_vendor_cmd(0xE1, cdb, config_data, is_write=True)

    # Check MMIO registers
    print("\nMMIO Registers after injection:")
    print(f"  0x910D (CDB[0])  = 0x{emu.hw.regs.get(0x910D, 0):02X} (should be 0xE1)")
    print(f"  0x910E (CDB[1])  = 0x{emu.hw.regs.get(0x910E, 0):02X} (should be 0x50)")
    print(f"  0x910F (CDB[2])  = 0x{emu.hw.regs.get(0x910F, 0):02X} (should be 0x00)")
    print(f"  0x9000 (USB)     = 0x{emu.hw.regs.get(0x9000, 0):02X} (should have bit 0/7 set)")
    print(f"  0x9101 (Status)  = 0x{emu.hw.regs.get(0x9101, 0):02X} (should be 0x21)")
    print(f"  0xC802 (Int)     = 0x{emu.hw.regs.get(0xC802, 0):02X} (should be 0x05)")
    print(f"  0x9096 (EP0)     = 0x{emu.hw.regs.get(0x9096, 0):02X} (should be 0x01)")

    # Check RAM setup
    print("\nXDATA after injection:")
    print(f"  XDATA[0x0002] = 0x{emu.memory.xdata[0x0002]:02X} (CDB opcode, should be 0xE1)")
    print(f"  XDATA[0x0003] = 0x{emu.memory.xdata[0x0003]:02X} (flags, should be 0x08)")
    print(f"  XDATA[0x0B02] = 0x{emu.memory.xdata[0x0B02]:02X} (vendor state)")
    print(f"  XDATA[0xEA90] = 0x{emu.memory.xdata[0xEA90]:02X} (magic, should be 0x5A)")
    print(f"  IDATA[0x6A]   = 0x{emu.memory.idata[0x6A]:02X} (USB state, should be 0x02)")

    # Verify key values
    success = True
    if emu.hw.regs.get(0x910D, 0) != 0xE1:
        print("FAIL: CDB[0] not set correctly")
        success = False
    if emu.memory.xdata[0x0002] != 0xE1:
        print("FAIL: XDATA CDB opcode not set")
        success = False
    if emu.memory.xdata[0xEA90] != 0x5A:
        print("FAIL: Magic value not set")
        success = False
    if emu.memory.idata[0x6A] != 0x02:
        print("FAIL: USB state not set to 0x02")
        success = False

    if success:
        print("\nPASS: All MMIO registers and RAM setup correctly")
    return success

if __name__ == '__main__':
    print("SCSI Vendor Command Injection Tests")
    print("=" * 70)

    results = []
    results.append(("MMIO Setup", test_mmio_setup()))
    results.append(("E1 Config Write", test_e1_config_write()))
    results.append(("E3 Firmware Write", test_e3_firmware_write()))
    results.append(("E8 Reset/Commit", test_e8_reset()))

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    for name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"  {name}: {status}")

    all_passed = all(r for _, r in results)
    print("\n" + ("ALL TESTS PASSED" if all_passed else "SOME TESTS FAILED"))
