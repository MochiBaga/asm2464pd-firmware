#!/usr/bin/env python3
"""
Debug USB descriptor handling.
Traces what happens when GET_DESCRIPTOR is sent to firmware.
"""

import sys
import os
import threading
import time

sys.path.insert(0, os.path.dirname(__file__))
from emu import Emulator


def test_get_device_descriptor():
    """Test GET_DESCRIPTOR for device descriptor."""
    print("=" * 60)
    print("Testing GET_DESCRIPTOR (device descriptor)")
    print("=" * 60)

    # Create emulator
    emu = Emulator(log_uart=True)
    emu.reset()

    # Try our firmware first
    fw_path = os.path.join(os.path.dirname(__file__), '..', 'build', 'firmware.bin')
    if not os.path.exists(fw_path):
        fw_path = os.path.join(os.path.dirname(__file__), '..', 'fw.bin')
    print(f"Loading firmware: {fw_path}")
    emu.load_firmware(fw_path)

    # Enable some debug logging
    emu.hw.log_writes = False  # Keep output manageable

    # Run boot sequence
    print("\nRunning boot sequence...")
    emu.run(max_cycles=100000)
    print(f"After boot: PC=0x{emu.cpu.pc:04X}, cycles={emu.cpu.cycles}")

    # Check initial state of USB buffer
    buf_before = bytes(emu.memory.xdata[0x8000:0x8020])
    print(f"\nUSB buffer (0x8000) before: {buf_before.hex()}")

    # Inject GET_DESCRIPTOR request via MMIO
    print("\n" + "=" * 60)
    print("Injecting GET_DESCRIPTOR (device, type=0x01)")
    print("=" * 60)

    hw = emu.hw

    # Use the USB controller's inject method
    hw.usb_controller.inject_control_transfer(
        bmRequestType=0x80,  # Device-to-host, standard, device
        bRequest=0x06,       # GET_DESCRIPTOR
        wValue=0x0100,       # Device descriptor (type=0x01, index=0)
        wIndex=0x0000,
        wLength=18,          # Device descriptor is 18 bytes
        data=b''
    )

    # Set up interrupt
    hw._pending_usb_interrupt = True
    emu.cpu._ext0_pending = True

    # Enable interrupts
    ie = emu.memory.read_sfr(0xA8)
    ie |= 0x81  # EA + EX0
    emu.memory.write_sfr(0xA8, ie)

    # Track PC to see what code path is taken
    pcs_seen = set()
    key_pcs = {
        0x0003: "EXT0 vector",
        0x1A4B: "USB ISR entry (our fw)",
        0x1A75: "ISR: check USB periph status",
        0x1B18: "ISR: peripheral handler path",
        0x1B1C: "ISR: read 0x9301",
        0x1B21: "ISR: check 0x9301 bit 6",
        0x1B24: "ISR: calling dispatch_0359",
        0x89D9: "dispatch_0359 (our addr)",
        0x89CB: "dispatch_0359 target",
        0xD088: "USB descriptor handler (main loop)",
    }

    print("\nRunning firmware to process request...")
    print("Key addresses to watch:")
    for addr, name in sorted(key_pcs.items()):
        print(f"  0x{addr:04X}: {name}")
    print()

    # Add more trace points
    emu.trace_pcs = set(key_pcs.keys())

    # Run in chunks, tracking all key PCs hit
    cycles_start = emu.cpu.cycles
    pc_trace = []
    for chunk in range(50):
        try:
            # Step instruction by instruction to catch all key PCs
            for _ in range(1000):
                emu.step()
                pc = emu.cpu.pc
                if pc in key_pcs and pc not in pcs_seen:
                    print(f"  [{emu.cpu.cycles:8d}] Hit 0x{pc:04X}: {key_pcs[pc]}")
                    pcs_seen.add(pc)
                    pc_trace.append((emu.cpu.cycles, pc))

                if emu.cpu.cycles - cycles_start > 50000:
                    break
        except Exception as e:
            print(f"Error at PC=0x{emu.cpu.pc:04X}: {e}")
            break

        if emu.cpu.cycles - cycles_start > 50000:
            break

    cycles_run = emu.cpu.cycles - cycles_start
    print(f"\nRan {cycles_run} cycles, final PC=0x{emu.cpu.pc:04X}")

    # Check MMIO registers that firmware should have written
    print("\n" + "=" * 60)
    print("Checking MMIO state after processing")
    print("=" * 60)

    print(f"0x905B (DMA addr hi): 0x{hw.regs.get(0x905B, 0):02X}")
    print(f"0x905C (DMA addr lo): 0x{hw.regs.get(0x905C, 0):02X}")
    dma_addr = (hw.regs.get(0x905B, 0) << 8) | hw.regs.get(0x905C, 0)
    print(f"DMA source address: 0x{dma_addr:04X}")

    print(f"0xD800 (DMA control): 0x{hw.regs.get(0xD800, 0):02X}")
    print(f"0xD807 (DMA length): 0x{hw.regs.get(0xD807, 0):02X}")

    print(f"0x9301 (EP0 arm): 0x{hw.regs.get(0x9301, 0):02X}")
    print(f"0x9101 (USB int flags): 0x{hw.regs.get(0x9101, 0):02X}")

    # Check USB buffer after
    buf_after = bytes(emu.memory.xdata[0x8000:0x8020])
    print(f"\nUSB buffer (0x8000) after: {buf_after.hex()}")

    if buf_after == buf_before:
        print("WARNING: USB buffer unchanged - firmware didn't write response!")
    elif all(b == 0 for b in buf_after):
        print("WARNING: USB buffer is all zeros!")
    else:
        print("SUCCESS: USB buffer has data!")
        # Parse device descriptor
        if buf_after[0] == 0x12 and buf_after[1] == 0x01:
            print("  Valid device descriptor detected!")
            print(f"  bLength: {buf_after[0]}")
            print(f"  bDescriptorType: {buf_after[1]}")
            vid = buf_after[8] | (buf_after[9] << 8)
            pid = buf_after[10] | (buf_after[11] << 8)
            print(f"  idVendor: 0x{vid:04X}")
            print(f"  idProduct: 0x{pid:04X}")

    # Check what's at the expected descriptor location in code ROM
    print("\n" + "=" * 60)
    print("Checking descriptor locations in code ROM")
    print("=" * 60)

    # Device descriptor should be at 0x0627 in original firmware
    # Check if flash mirror is working
    desc_addr = 0x0627
    if hasattr(emu.hw, 'code') and len(emu.hw.code) > desc_addr:
        print(f"Code ROM at 0x{desc_addr:04X}: {bytes(emu.hw.code[desc_addr:desc_addr+18]).hex()}")

    # Check flash mirror region
    flash_mirror = bytes(emu.memory.xdata[0xE400:0xE420])
    print(f"Flash mirror (0xE400): {flash_mirror.hex()}")

    return buf_after


def test_with_threaded_emulator():
    """Test with emulator running in background thread."""
    print("\n" + "=" * 60)
    print("Testing with threaded emulator")
    print("=" * 60)

    emu = Emulator(log_uart=False)
    emu.reset()

    fw_path = os.path.join(os.path.dirname(__file__), '..', 'build', 'firmware.bin')
    if not os.path.exists(fw_path):
        fw_path = os.path.join(os.path.dirname(__file__), '..', 'fw.bin')
    emu.load_firmware(fw_path)

    # Run boot in main thread first
    emu.run(max_cycles=100000)
    print(f"Boot complete: PC=0x{emu.cpu.pc:04X}")

    # Thread to run emulator
    emu_running = threading.Event()
    emu_stop = threading.Event()

    def emu_thread():
        while not emu_stop.is_set():
            try:
                emu.run(max_cycles=emu.cpu.cycles + 1000)
            except Exception as e:
                print(f"Emu thread error: {e}")
                break
            time.sleep(0.001)  # Yield to other threads

    # Start emulator thread
    t = threading.Thread(target=emu_thread, daemon=True)
    t.start()

    # Give it a moment to start
    time.sleep(0.1)

    # Inject GET_DESCRIPTOR
    print("Injecting GET_DESCRIPTOR from main thread...")
    emu.hw.usb_controller.inject_control_transfer(
        bmRequestType=0x80,
        bRequest=0x06,
        wValue=0x0100,
        wIndex=0x0000,
        wLength=18,
        data=b''
    )

    # Trigger interrupt
    emu.hw._pending_usb_interrupt = True
    emu.cpu._ext0_pending = True
    ie = emu.memory.read_sfr(0xA8)
    ie |= 0x81
    emu.memory.write_sfr(0xA8, ie)

    # Wait for processing
    time.sleep(0.5)

    # Stop emulator
    emu_stop.set()
    t.join(timeout=1.0)

    # Check result
    buf = bytes(emu.memory.xdata[0x8000:0x8020])
    print(f"USB buffer: {buf.hex()}")

    if all(b == 0 for b in buf):
        print("FAIL: Buffer is all zeros")
    else:
        print("Data in buffer!")

    return buf


if __name__ == "__main__":
    result1 = test_get_device_descriptor()
    print("\n\n")
    result2 = test_with_threaded_emulator()
