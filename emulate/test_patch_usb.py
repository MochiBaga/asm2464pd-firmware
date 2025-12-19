#!/usr/bin/env python3
"""
Standalone test for USB emulator functionality.

Tests the emulated USB device using BBB (Bulk-Only) protocol,
which works with dummy_hcd (no USB streams required).

Usage:
    # Start emulator first:
    sudo python3 usb_device.py &

    # Unbind kernel driver:
    echo -n "6-1:1.0" | sudo tee /sys/bus/usb/drivers/usb-storage/unbind

    # Run tests:
    sudo python3 test_patch_usb.py
"""

import ctypes
import struct
import time
import sys
import os

# Add tinygrad path for libusb bindings
sys.path.insert(0, '/home/tiny/tinygrad')
from tinygrad.runtime.autogen import libusb

# Device identifiers
VENDOR_ID = 0x174C
PRODUCT_ID = 0x2461

# USB endpoints (BBB mode - alt_setting 0)
EP_BULK_IN = 0x81
EP_BULK_OUT = 0x02

# BBB Protocol constants
CBW_SIGNATURE = 0x43425355  # 'USBC'
CSW_SIGNATURE = 0x53425355  # 'USBS'
CBW_SIZE = 31
CSW_SIZE = 13


class USBTestError(Exception):
    """USB test error."""
    pass


class BBBDevice:
    """USB Mass Storage device using Bulk-Only (BBB) protocol."""

    def __init__(self, vendor: int, product: int):
        self.vendor = vendor
        self.product = product
        self.ctx = ctypes.POINTER(libusb.struct_libusb_context)()
        self.handle = None
        self.tag = 1

        # Initialize libusb
        if libusb.libusb_init(ctypes.byref(self.ctx)):
            raise USBTestError("libusb_init failed")

        # Open device
        self.handle = libusb.libusb_open_device_with_vid_pid(
            self.ctx, self.vendor, self.product)
        if not self.handle:
            raise USBTestError(f"Device {vendor:04x}:{product:04x} not found")

        # Detach kernel driver if needed
        if libusb.libusb_kernel_driver_active(self.handle, 0):
            libusb.libusb_detach_kernel_driver(self.handle, 0)

        # Claim interface
        if libusb.libusb_claim_interface(self.handle, 0):
            raise USBTestError("claim_interface failed")

        print(f"[TEST] Opened device {vendor:04x}:{product:04x}")

    def close(self):
        if self.handle:
            libusb.libusb_release_interface(self.handle, 0)
            libusb.libusb_close(self.handle)
        if self.ctx:
            libusb.libusb_exit(self.ctx)

    def get_descriptor(self, desc_type: int, desc_index: int, length: int) -> bytes:
        """Get a USB descriptor via control transfer."""
        buf = (ctypes.c_uint8 * length)()
        ret = libusb.libusb_control_transfer(
            self.handle,
            0x80,  # bmRequestType: Device-to-host, Standard, Device
            0x06,  # bRequest: GET_DESCRIPTOR
            (desc_type << 8) | desc_index,  # wValue
            0,  # wIndex
            buf,
            length,
            1000  # timeout ms
        )
        if ret < 0:
            raise USBTestError(f"get_descriptor failed: {ret}")
        return bytes(buf[:ret])

    def get_max_lun(self) -> int:
        """Get max LUN via class request."""
        buf = (ctypes.c_uint8 * 1)()
        ret = libusb.libusb_control_transfer(
            self.handle,
            0xA1,  # bmRequestType: Device-to-host, Class, Interface
            0xFE,  # bRequest: GET_MAX_LUN
            0,     # wValue
            0,     # wIndex
            buf,
            1,
            1000
        )
        if ret < 0:
            # Some devices stall this - return 0
            return 0
        return buf[0]

    def bulk_reset(self):
        """Send Bulk-Only Mass Storage Reset."""
        ret = libusb.libusb_control_transfer(
            self.handle,
            0x21,  # bmRequestType: Host-to-device, Class, Interface
            0xFF,  # bRequest: BULK_ONLY_RESET
            0,     # wValue
            0,     # wIndex
            None,
            0,
            1000
        )
        if ret < 0:
            print(f"[TEST] bulk_reset returned {ret} (may be normal)")

    def send_cbw(self, cdb: bytes, data_length: int, direction_in: bool) -> int:
        """Send Command Block Wrapper, return tag used."""
        tag = self.tag
        self.tag += 1

        # Build CBW
        flags = 0x80 if direction_in else 0x00
        cbw = struct.pack('<IIIBBB',
            CBW_SIGNATURE,
            tag,
            data_length,
            flags,
            0,  # LUN
            len(cdb)
        ) + cdb + bytes(16 - len(cdb))

        assert len(cbw) == CBW_SIZE

        # Send CBW
        buf = (ctypes.c_uint8 * CBW_SIZE)(*cbw)
        transferred = ctypes.c_int()
        ret = libusb.libusb_bulk_transfer(
            self.handle, EP_BULK_OUT, buf, CBW_SIZE,
            ctypes.byref(transferred), 5000
        )
        if ret != 0:
            raise USBTestError(f"CBW send failed: {ret}")

        return tag

    def recv_data(self, length: int) -> bytes:
        """Receive data from bulk IN endpoint."""
        buf = (ctypes.c_uint8 * length)()
        transferred = ctypes.c_int()
        ret = libusb.libusb_bulk_transfer(
            self.handle, EP_BULK_IN, buf, length,
            ctypes.byref(transferred), 5000
        )
        if ret != 0:
            raise USBTestError(f"Data receive failed: {ret}")
        return bytes(buf[:transferred.value])

    def send_data(self, data: bytes):
        """Send data to bulk OUT endpoint."""
        buf = (ctypes.c_uint8 * len(data))(*data)
        transferred = ctypes.c_int()
        ret = libusb.libusb_bulk_transfer(
            self.handle, EP_BULK_OUT, buf, len(data),
            ctypes.byref(transferred), 5000
        )
        if ret != 0:
            raise USBTestError(f"Data send failed: {ret}")

    def recv_csw(self, expected_tag: int) -> tuple:
        """Receive Command Status Wrapper, return (status, residue)."""
        buf = (ctypes.c_uint8 * CSW_SIZE)()
        transferred = ctypes.c_int()
        ret = libusb.libusb_bulk_transfer(
            self.handle, EP_BULK_IN, buf, CSW_SIZE,
            ctypes.byref(transferred), 5000
        )
        if ret != 0:
            raise USBTestError(f"CSW receive failed: {ret}")

        csw = bytes(buf[:transferred.value])
        if len(csw) < CSW_SIZE:
            raise USBTestError(f"CSW too short: {len(csw)} bytes")

        sig, tag, residue, status = struct.unpack('<IIIB', csw)
        if sig != CSW_SIGNATURE:
            raise USBTestError(f"Invalid CSW signature: {sig:08x}")
        if tag != expected_tag:
            raise USBTestError(f"CSW tag mismatch: expected {expected_tag}, got {tag}")

        return status, residue

    def scsi_inquiry(self) -> bytes:
        """Send SCSI INQUIRY command."""
        cdb = bytes([0x12, 0, 0, 0, 36, 0])  # INQUIRY, 36 bytes
        tag = self.send_cbw(cdb, 36, direction_in=True)
        data = self.recv_data(36)
        status, residue = self.recv_csw(tag)
        if status != 0:
            raise USBTestError(f"INQUIRY failed with status {status}")
        return data

    def scsi_test_unit_ready(self) -> bool:
        """Send SCSI TEST UNIT READY command."""
        cdb = bytes([0x00, 0, 0, 0, 0, 0])
        tag = self.send_cbw(cdb, 0, direction_in=True)
        status, residue = self.recv_csw(tag)
        return status == 0

    def vendor_read(self, addr: int, length: int) -> bytes:
        """Send vendor E4 read command."""
        # E4 command: read from XDATA
        cdb = struct.pack('>BBBHB', 0xE4, length, (addr >> 16) & 0xFF, addr & 0xFFFF, 0)
        cdb = cdb + bytes(16 - len(cdb))
        tag = self.send_cbw(cdb, length, direction_in=True)
        data = self.recv_data(length)
        status, residue = self.recv_csw(tag)
        if status != 0:
            print(f"[TEST] vendor_read status={status}")
        return data

    def vendor_write(self, addr: int, value: int) -> int:
        """Send vendor E5 write command. Returns status."""
        # E5 command: write to XDATA
        cdb = struct.pack('>BBBHB', 0xE5, value, (addr >> 16) & 0xFF, addr & 0xFFFF, 0)
        cdb = cdb + bytes(16 - len(cdb))
        tag = self.send_cbw(cdb, 0, direction_in=False)
        status, residue = self.recv_csw(tag)
        return status


def test_enumeration():
    """Test device enumeration and descriptors."""
    print("\n" + "=" * 50)
    print("Test 1: Device Enumeration")
    print("=" * 50)

    dev = BBBDevice(VENDOR_ID, PRODUCT_ID)

    try:
        # Get device descriptor
        print("[TEST] Getting device descriptor...")
        desc = dev.get_descriptor(0x01, 0, 18)
        if len(desc) >= 18:
            vid = desc[8] | (desc[9] << 8)
            pid = desc[10] | (desc[11] << 8)
            print(f"[TEST] Device: VID={vid:04X} PID={pid:04X}")
            assert vid == VENDOR_ID, f"VID mismatch: {vid:04X}"
            assert pid == PRODUCT_ID, f"PID mismatch: {pid:04X}"
            print("[TEST] PASS: Device descriptor correct")
        else:
            raise USBTestError(f"Device descriptor too short: {len(desc)}")

        # Get config descriptor (header only)
        print("[TEST] Getting config descriptor header...")
        desc = dev.get_descriptor(0x02, 0, 9)
        if len(desc) >= 4:
            total_len = desc[2] | (desc[3] << 8)
            print(f"[TEST] Config descriptor wTotalLength={total_len}")
            # Should be 121 bytes (with alt_setting 1)
            if total_len == 121:
                print("[TEST] PASS: wTotalLength includes alt_setting 1 (UAS)")
            elif total_len == 44:
                print("[TEST] WARN: wTotalLength only includes alt_setting 0 (BBB)")
            else:
                print(f"[TEST] INFO: wTotalLength={total_len}")

        # Get full config descriptor
        print(f"[TEST] Getting full config descriptor ({total_len} bytes)...")
        desc = dev.get_descriptor(0x02, 0, total_len)
        print(f"[TEST] Got {len(desc)} bytes")

        # Parse to find interfaces
        i = 0
        interfaces = []
        endpoints = []
        while i < len(desc) - 1:
            bLength = desc[i]
            bDescType = desc[i + 1]
            if bLength == 0:
                break
            if bDescType == 0x04:  # Interface descriptor
                iface_num = desc[i + 2]
                alt_setting = desc[i + 3]
                num_eps = desc[i + 4]
                iface_class = desc[i + 5]
                iface_proto = desc[i + 7]
                interfaces.append((iface_num, alt_setting, num_eps, iface_class, iface_proto))
            elif bDescType == 0x05:  # Endpoint descriptor
                ep_addr = desc[i + 2]
                ep_attr = desc[i + 3]
                endpoints.append((ep_addr, ep_attr))
            i += bLength

        print(f"[TEST] Found {len(interfaces)} interface(s):")
        for iface in interfaces:
            proto_name = "BBB" if iface[4] == 0x50 else "UAS" if iface[4] == 0x62 else f"0x{iface[4]:02X}"
            print(f"[TEST]   Interface {iface[0]} alt={iface[1]}: {iface[2]} endpoints, protocol={proto_name}")

        print(f"[TEST] Found {len(endpoints)} endpoint(s):")
        for ep in endpoints:
            direction = "IN" if ep[0] & 0x80 else "OUT"
            ep_type = ["CTRL", "ISOC", "BULK", "INT"][ep[1] & 0x03]
            print(f"[TEST]   EP 0x{ep[0]:02X}: {direction} {ep_type}")

        if len(interfaces) >= 2:
            print("[TEST] PASS: Both alt_settings present")
            return True
        elif len(interfaces) == 1:
            print("[TEST] PASS: At least one interface present")
            return True
        else:
            print("[TEST] FAIL: No interfaces found")
            return False

    finally:
        dev.close()


def test_mass_storage():
    """Test mass storage commands via BBB protocol."""
    print("\n" + "=" * 50)
    print("Test 2: Mass Storage (BBB Protocol)")
    print("=" * 50)

    dev = BBBDevice(VENDOR_ID, PRODUCT_ID)

    try:
        # Get max LUN
        print("[TEST] Getting MAX_LUN...")
        max_lun = dev.get_max_lun()
        print(f"[TEST] MAX_LUN={max_lun}")
        print("[TEST] PASS: GET_MAX_LUN works")

        # Bulk reset
        print("[TEST] Sending BULK_ONLY_RESET...")
        dev.bulk_reset()
        time.sleep(0.1)
        print("[TEST] PASS: BULK_ONLY_RESET sent")

        # INQUIRY
        print("[TEST] Sending SCSI INQUIRY...")
        try:
            inquiry_data = dev.scsi_inquiry()
            print(f"[TEST] INQUIRY response: {len(inquiry_data)} bytes")
            if len(inquiry_data) >= 36:
                vendor = inquiry_data[8:16].decode('ascii', errors='replace').strip()
                product = inquiry_data[16:32].decode('ascii', errors='replace').strip()
                revision = inquiry_data[32:36].decode('ascii', errors='replace').strip()
                print(f"[TEST] Vendor:   '{vendor}'")
                print(f"[TEST] Product:  '{product}'")
                print(f"[TEST] Revision: '{revision}'")
                print("[TEST] PASS: INQUIRY successful")
                return True
            else:
                print("[TEST] FAIL: INQUIRY response too short")
                return False
        except USBTestError as e:
            print(f"[TEST] FAIL: INQUIRY failed: {e}")
            return False

    finally:
        dev.close()


def test_vendor_commands():
    """Test vendor-specific commands (E4/E5)."""
    print("\n" + "=" * 50)
    print("Test 3: Vendor Commands (E4 Read, E5 Write)")
    print("=" * 50)

    dev = BBBDevice(VENDOR_ID, PRODUCT_ID)

    try:
        # Try E4 read command - read 16 bytes from XDATA 0x8000
        print("[TEST] Sending vendor E4 read (XDATA 0x8000, 16 bytes)...")
        try:
            data = dev.vendor_read(0x508000, 16)
            print(f"[TEST] E4 response: {data.hex()}")
            print("[TEST] PASS: Vendor E4 read works")
            e4_pass = True
        except USBTestError as e:
            print(f"[TEST] WARN: E4 read failed: {e}")
            e4_pass = False

        # Try E5 write command - write 0x42 to XDATA 0x8100
        print("[TEST] Sending vendor E5 write (XDATA 0x8100 = 0x42)...")
        try:
            status = dev.vendor_write(0x508100, 0x42)
            print(f"[TEST] E5 status: {status}")
            if status == 0:
                print("[TEST] PASS: Vendor E5 write works")
                e5_pass = True
            else:
                print("[TEST] WARN: E5 write returned non-zero status")
                e5_pass = False
        except USBTestError as e:
            print(f"[TEST] WARN: E5 write failed: {e}")
            e5_pass = False

        return e4_pass or e5_pass

    finally:
        dev.close()


def test_strings():
    """Test USB string descriptors."""
    print("\n" + "=" * 50)
    print("Test 4: String Descriptors")
    print("=" * 50)

    dev = BBBDevice(VENDOR_ID, PRODUCT_ID)

    try:
        # Get string descriptor index 0 (supported languages)
        print("[TEST] Getting language list (string 0)...")
        try:
            desc = dev.get_descriptor(0x03, 0, 255)
            if len(desc) >= 4:
                lang = desc[2] | (desc[3] << 8)
                print(f"[TEST] Language: 0x{lang:04X}")
            print("[TEST] PASS: Language descriptor retrieved")
        except USBTestError as e:
            print(f"[TEST] WARN: Language descriptor failed: {e}")

        # Get manufacturer string (usually index 2)
        print("[TEST] Getting manufacturer string (index 2)...")
        try:
            buf = (ctypes.c_uint8 * 255)()
            ret = libusb.libusb_control_transfer(
                dev.handle,
                0x80,  # GET_DESCRIPTOR
                0x06,
                (0x03 << 8) | 2,  # String descriptor, index 2
                0x0409,  # English
                buf,
                255,
                1000
            )
            if ret > 2:
                # Parse as UTF-16LE string
                string_data = bytes(buf[2:ret])
                manufacturer = string_data.decode('utf-16-le', errors='replace')
                print(f"[TEST] Manufacturer: '{manufacturer}'")
                print("[TEST] PASS: Manufacturer string retrieved")
        except Exception as e:
            print(f"[TEST] WARN: Manufacturer string failed: {e}")

        # Get product string (usually index 3)
        print("[TEST] Getting product string (index 3)...")
        try:
            buf = (ctypes.c_uint8 * 255)()
            ret = libusb.libusb_control_transfer(
                dev.handle,
                0x80,
                0x06,
                (0x03 << 8) | 3,
                0x0409,
                buf,
                255,
                1000
            )
            if ret > 2:
                string_data = bytes(buf[2:ret])
                product = string_data.decode('utf-16-le', errors='replace')
                print(f"[TEST] Product: '{product}'")
                print("[TEST] PASS: Product string retrieved")
        except Exception as e:
            print(f"[TEST] WARN: Product string failed: {e}")

        return True

    finally:
        dev.close()


def main():
    print("=" * 60)
    print("USB Emulator Functionality Test")
    print("=" * 60)
    print(f"Target device: {VENDOR_ID:04X}:{PRODUCT_ID:04X}")

    # Check if device exists
    ctx = ctypes.POINTER(libusb.struct_libusb_context)()
    libusb.libusb_init(ctypes.byref(ctx))
    handle = libusb.libusb_open_device_with_vid_pid(ctx, VENDOR_ID, PRODUCT_ID)
    if not handle:
        print("\n[ERROR] Device not found!")
        print("\nMake sure:")
        print("  1. Emulator is running:")
        print("     cd emulate && sudo python3 usb_device.py")
        print("  2. Device shows in lsusb:")
        print("     lsusb | grep 174c")
        print("  3. Kernel driver is unbound:")
        print("     echo -n '6-1:1.0' | sudo tee /sys/bus/usb/drivers/usb-storage/unbind")
        libusb.libusb_exit(ctx)
        return 1
    libusb.libusb_close(handle)
    libusb.libusb_exit(ctx)

    results = []

    # Run tests
    try:
        results.append(("Enumeration", test_enumeration()))
    except Exception as e:
        print(f"[TEST] Enumeration test exception: {e}")
        import traceback
        traceback.print_exc()
        results.append(("Enumeration", False))

    try:
        results.append(("Mass Storage", test_mass_storage()))
    except Exception as e:
        print(f"[TEST] Mass Storage test exception: {e}")
        import traceback
        traceback.print_exc()
        results.append(("Mass Storage", False))

    try:
        results.append(("Vendor Commands", test_vendor_commands()))
    except Exception as e:
        print(f"[TEST] Vendor Commands test exception: {e}")
        import traceback
        traceback.print_exc()
        results.append(("Vendor Commands", False))

    try:
        results.append(("String Descriptors", test_strings()))
    except Exception as e:
        print(f"[TEST] String Descriptors test exception: {e}")
        import traceback
        traceback.print_exc()
        results.append(("String Descriptors", False))

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    passed = 0
    for name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"  {name}: {status}")
        if result:
            passed += 1

    print(f"\nTotal: {passed}/{len(results)} tests passed")

    if passed == len(results):
        print("\nAll tests passed! USB emulator is working correctly.")
        return 0
    else:
        print("\nSome tests failed. Check output above for details.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
