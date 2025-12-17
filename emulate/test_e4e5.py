#!/usr/bin/env python3
"""
Test E4/E5 vendor commands via control transfers.

This tests the emulated USB device by sending E4 (read) and E5 (write)
vendor commands through control transfers.

Usage:
  sudo python emulate/test_e4e5.py

Requires the emulated device to be running (python emulate/usb_device.py).
"""

import usb.core
import usb.util
import sys
import time

# ASMedia ASM2464PD VID:PID
VID = 0x174C
PID = 0x2462

def find_device():
    """Find the ASM2464PD device."""
    dev = usb.core.find(idVendor=VID, idProduct=PID)
    if dev is None:
        print(f"Device {VID:04X}:{PID:04X} not found")
        print("Make sure usb_device.py is running")
        return None
    print(f"Found device: {dev.manufacturer} {dev.product}")
    return dev

def e4_read(dev, addr: int, size: int = 1) -> bytes:
    """
    E4 read command - read from XDATA.

    Sent as vendor control transfer:
    - bmRequestType = 0xC0 (vendor, device-to-host)
    - bRequest = 0xE4
    - wValue = size
    - wIndex = addr
    """
    try:
        data = dev.ctrl_transfer(
            bmRequestType=0xC0,  # Vendor, IN
            bRequest=0xE4,
            wValue=size,
            wIndex=addr,
            data_or_wLength=size,
            timeout=1000
        )
        return bytes(data)
    except usb.core.USBError as e:
        print(f"E4 read error: {e}")
        return b''

def e5_write(dev, addr: int, value: int) -> bool:
    """
    E5 write command - write to XDATA.

    Sent as vendor control transfer:
    - bmRequestType = 0x40 (vendor, host-to-device)
    - bRequest = 0xE5
    - wValue = value
    - wIndex = addr
    """
    try:
        dev.ctrl_transfer(
            bmRequestType=0x40,  # Vendor, OUT
            bRequest=0xE5,
            wValue=value,
            wIndex=addr,
            data_or_wLength=None,
            timeout=1000
        )
        return True
    except usb.core.USBError as e:
        print(f"E5 write error: {e}")
        return False

def main():
    print("E4/E5 Vendor Command Test")
    print("=" * 40)

    dev = find_device()
    if dev is None:
        sys.exit(1)

    # Test addresses (safe XDATA locations)
    test_addr = 0x0600  # Scratch area

    print(f"\n1. Reading 4 bytes from 0x{test_addr:04X}")
    data = e4_read(dev, test_addr, 4)
    if data:
        print(f"   Read: {data.hex()}")
    else:
        print("   Read failed")

    print(f"\n2. Writing 0x42 to 0x{test_addr:04X}")
    if e5_write(dev, test_addr, 0x42):
        print("   Write OK")
    else:
        print("   Write failed")

    print(f"\n3. Reading back from 0x{test_addr:04X}")
    data = e4_read(dev, test_addr, 1)
    if data:
        print(f"   Read: 0x{data[0]:02X}")
        if data[0] == 0x42:
            print("   SUCCESS: Value matches!")
        else:
            print(f"   MISMATCH: Expected 0x42, got 0x{data[0]:02X}")
    else:
        print("   Read failed")

    # Test reading firmware info area
    print(f"\n4. Reading firmware info at 0x0000 (8 bytes)")
    data = e4_read(dev, 0x0000, 8)
    if data:
        print(f"   Data: {data.hex()}")

    print("\nTest complete!")

if __name__ == "__main__":
    main()
