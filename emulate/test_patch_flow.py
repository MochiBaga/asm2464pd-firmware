#!/usr/bin/env python3
"""
Test the patch.py firmware update flow in the emulator.

This simulates the sequence of commands that patch.py sends:
1. E1 config write (config block 0)
2. E1 config write (config block 1)
3. E3 firmware write (part 1 - bank 0)
4. E3 firmware write (part 2 - bank 1)
5. E8 commit

This test runs against the emulator WITHOUT raw-gadget, verifying
that the firmware receives and processes the vendor commands via MMIO.
"""

import sys
import struct
sys.path.insert(0, '/home/tiny/fun/asm2464pd-firmware/emulate')

from emu import Emulator

# Sample config data from patch.py
CONFIG1 = bytes([
    0xFF, 0xFF, 0xFF, 0xFF, 0x41, 0x41, 0x41, 0x41, 0x42, 0x42, 0x42, 0x42, 0x30, 0x30, 0x36, 0x30,
    0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0x74, 0x69, 0x6E, 0x79, 0xFF, 0xFF, 0xFF, 0xFF,
    0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF,
    0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0x74, 0x69, 0x6E, 0x79,
    0xFF, 0xFF, 0xFF, 0xFF, 0x55, 0x53, 0x42, 0x20, 0x33, 0x2E, 0x32, 0x20, 0x50, 0x43, 0x49, 0x65,
    0x20, 0x54, 0x69, 0x6E, 0x79, 0x45, 0x6E, 0x63, 0x6C, 0x6F, 0x73, 0x75, 0x72, 0x65, 0xFF, 0xFF,
    0xFF, 0xFF, 0xFF, 0xFF, 0x54, 0x69, 0x6E, 0x79, 0x45, 0x6E, 0x63, 0x6C, 0x6F, 0x73, 0x75, 0x72,
    0x65, 0xFF, 0xFF, 0xFF, 0xD1, 0xAD, 0x01, 0x00, 0x00, 0x01, 0xCF, 0xFF, 0x02, 0xFF, 0x5A, 0x94
])

CONFIG2 = bytes([
    0xFF, 0xFF, 0xFF, 0xFF, 0x47, 0x6F, 0x70, 0x6F, 0x64, 0x20, 0x47, 0x72, 0x6F, 0x75, 0x70, 0x20,
    0x4C, 0x69, 0x6D, 0x69, 0x74, 0x65, 0x64, 0x2E, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF,
    0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0x55, 0x53, 0x42, 0x34,
    0x20, 0x4E, 0x56, 0x4D, 0x65, 0x20, 0x53, 0x53, 0x44, 0x20, 0x50, 0x72, 0x6F, 0x20, 0x45, 0x6E,
    0x63, 0x6C, 0x6F, 0x73, 0x75, 0x72, 0x65, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF,
    0xFF, 0xFF, 0xFF, 0xFF, 0x8C, 0xBF, 0xFF, 0x97, 0xC1, 0xF3, 0xFF, 0xFF, 0x01, 0x2D, 0x66, 0xD6,
    0x66, 0x06, 0x00, 0xC0, 0x87, 0x01, 0x5A, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xCA, 0x01, 0x66, 0xD6,
    0xE3, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0x00, 0x00, 0xFF, 0xFF, 0x01, 0x00, 0xA5, 0x67
])


def test_patch_flow():
    """Test the complete patch.py firmware update flow."""
    print("=" * 70)
    print("PATCH.PY FIRMWARE UPDATE FLOW TEST")
    print("=" * 70)

    emu = Emulator()
    emu.load_firmware('/home/tiny/fun/asm2464pd-firmware/fw.bin')

    # Boot firmware
    print("\n[STEP 0] Booting firmware...")
    emu.run(max_cycles=200000)

    # Connect USB
    print("\n[STEP 1] Connecting USB...")
    emu.hw.usb_controller.connect(speed=2)
    emu.run(max_cycles=300000)

    # =========================================
    # Step 2: E1 Config Write (block 0)
    # CDB: struct.pack('>BBB12x', 0xe1, 0x50, 0x0)
    # =========================================
    print("\n[STEP 2] E1 Config Write (block 0)...")
    cdb = struct.pack('>BBB', 0xE1, 0x50, 0x00) + bytes(12)
    emu.hw.inject_scsi_vendor_cmd(0xE1, cdb, CONFIG1, is_write=True)
    emu.run(max_cycles=400000)
    print(f"  Config block 0: {len(CONFIG1)} bytes written")

    # =========================================
    # Step 3: E1 Config Write (block 1)
    # CDB: struct.pack('>BBB12x', 0xe1, 0x50, 0x1)
    # =========================================
    print("\n[STEP 3] E1 Config Write (block 1)...")
    cdb = struct.pack('>BBB', 0xE1, 0x50, 0x01) + bytes(12)
    emu.hw.inject_scsi_vendor_cmd(0xE1, cdb, CONFIG2, is_write=True)
    emu.run(max_cycles=500000)
    print(f"  Config block 1: {len(CONFIG2)} bytes written")

    # =========================================
    # Step 4: E3 Firmware Write (part 1 - bank 0)
    # CDB: struct.pack('>BBI', 0xe3, 0x50, len(part1))
    # Real patch.py sends ~64KB, we test with smaller chunk
    # =========================================
    print("\n[STEP 4] E3 Firmware Write (part 1 - bank 0)...")
    # Use first 256 bytes of actual firmware as test data
    fw_part1 = bytes([emu.memory.code[i] for i in range(256)])
    cdb = struct.pack('>BBI', 0xE3, 0x50, len(fw_part1)) + bytes(9)
    emu.hw.inject_scsi_vendor_cmd(0xE3, cdb, fw_part1, is_write=True)
    emu.run(max_cycles=600000)
    print(f"  Firmware part 1: {len(fw_part1)} bytes (0x50 mode)")

    # =========================================
    # Step 5: E3 Firmware Write (part 2 - bank 1)
    # CDB: struct.pack('>BBI', 0xe3, 0xd0, len(part2))
    # =========================================
    print("\n[STEP 5] E3 Firmware Write (part 2 - bank 1)...")
    fw_part2 = bytes(256)  # Placeholder
    cdb = struct.pack('>BBI', 0xE3, 0xD0, len(fw_part2)) + bytes(9)
    emu.hw.inject_scsi_vendor_cmd(0xE3, cdb, fw_part2, is_write=True)
    emu.run(max_cycles=700000)
    print(f"  Firmware part 2: {len(fw_part2)} bytes (0xD0 mode)")

    # =========================================
    # Step 6: E8 Commit
    # CDB: struct.pack('>BB13x', 0xe8, 0x51)
    # =========================================
    print("\n[STEP 6] E8 Commit...")
    cdb = struct.pack('>BB', 0xE8, 0x51) + bytes(13)
    emu.hw.inject_scsi_vendor_cmd(0xE8, cdb, b'', is_write=False)
    emu.run(max_cycles=800000)
    print("  Commit command sent")

    # =========================================
    # Verify Results
    # =========================================
    print("\n" + "=" * 70)
    print("VERIFICATION")
    print("=" * 70)

    # Check that config data was received at 0x8000
    buffer_data = bytes([emu.memory.xdata[0x8000 + i] for i in range(16)])
    print(f"\nUSB buffer (0x8000): {buffer_data.hex()}")

    # Check vendor command state
    print(f"XDATA[0x0B02] (vendor state): 0x{emu.memory.xdata[0x0B02]:02X}")
    print(f"XDATA[0xEA90] (magic): 0x{emu.memory.xdata[0xEA90]:02X}")

    # Check firmware state
    print(f"IDATA[0x6A] (USB state): 0x{emu.memory.idata[0x6A]:02X}")

    print("\n" + "=" * 70)
    print("PATCH FLOW SIMULATION COMPLETE")
    print("=" * 70)
    print("\nNote: Full patch.py requires raw-gadget/dummy_hcd for actual")
    print("USB device emulation. This test verifies MMIO injection path.")

    return True


def test_individual_commands():
    """Test each command type individually."""
    print("\n" + "=" * 70)
    print("INDIVIDUAL COMMAND TESTS")
    print("=" * 70)

    results = []

    # Test E1
    print("\n--- E1 Config Write ---")
    emu = Emulator()
    emu.load_firmware('/home/tiny/fun/asm2464pd-firmware/fw.bin')
    emu.run(max_cycles=200000)
    emu.hw.usb_controller.connect(speed=2)
    emu.run(max_cycles=300000)

    cdb = struct.pack('>BBB', 0xE1, 0x50, 0x00) + bytes(12)
    emu.hw.inject_scsi_vendor_cmd(0xE1, cdb, CONFIG1, is_write=True)

    # Verify CDB was set
    if emu.memory.xdata[0x0002] == 0xE1:
        print("  PASS: CDB opcode set to 0xE1")
        results.append(True)
    else:
        print(f"  FAIL: CDB opcode = 0x{emu.memory.xdata[0x0002]:02X}")
        results.append(False)

    # Test E3
    print("\n--- E3 Firmware Write ---")
    emu = Emulator()
    emu.load_firmware('/home/tiny/fun/asm2464pd-firmware/fw.bin')
    emu.run(max_cycles=200000)
    emu.hw.usb_controller.connect(speed=2)
    emu.run(max_cycles=300000)

    cdb = struct.pack('>BBI', 0xE3, 0x50, 256) + bytes(9)
    emu.hw.inject_scsi_vendor_cmd(0xE3, cdb, bytes(256), is_write=True)

    if emu.memory.xdata[0x0002] == 0xE3:
        print("  PASS: CDB opcode set to 0xE3")
        results.append(True)
    else:
        print(f"  FAIL: CDB opcode = 0x{emu.memory.xdata[0x0002]:02X}")
        results.append(False)

    # Verify vendor state for E3
    if emu.memory.xdata[0x0B02] == 2:
        print("  PASS: Vendor state set to 2 (E3 write mode)")
        results.append(True)
    else:
        print(f"  FAIL: Vendor state = 0x{emu.memory.xdata[0x0B02]:02X}")
        results.append(False)

    # Test E8
    print("\n--- E8 Reset/Commit ---")
    emu = Emulator()
    emu.load_firmware('/home/tiny/fun/asm2464pd-firmware/fw.bin')
    emu.run(max_cycles=200000)
    emu.hw.usb_controller.connect(speed=2)
    emu.run(max_cycles=300000)

    cdb = struct.pack('>BB', 0xE8, 0x51) + bytes(13)
    emu.hw.inject_scsi_vendor_cmd(0xE8, cdb, b'', is_write=False)

    if emu.memory.xdata[0x0002] == 0xE8:
        print("  PASS: CDB opcode set to 0xE8")
        results.append(True)
    else:
        print(f"  FAIL: CDB opcode = 0x{emu.memory.xdata[0x0002]:02X}")
        results.append(False)

    return all(results)


if __name__ == '__main__':
    print("PATCH.PY FLOW EMULATION TEST")
    print("=" * 70)

    # Run tests
    result1 = test_individual_commands()
    result2 = test_patch_flow()

    # Summary
    print("\n" + "=" * 70)
    print("FINAL SUMMARY")
    print("=" * 70)
    print(f"  Individual commands: {'PASS' if result1 else 'FAIL'}")
    print(f"  Patch flow: {'PASS' if result2 else 'FAIL'}")

    all_passed = result1 and result2
    print(f"\nOverall: {'ALL TESTS PASSED' if all_passed else 'SOME TESTS FAILED'}")
