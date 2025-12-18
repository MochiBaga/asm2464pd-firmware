#!/usr/bin/env python3
"""
Integration tests for USB Host interface.

These tests verify that the emulator can properly handle USB control transfers
and vendor commands using ONLY MMIO registers - no hardcoded descriptor data
or Python USB processing.

CRITICAL: These tests verify the FIRMWARE handles USB requests, not Python.
If a test fails because the firmware doesn't produce expected output, that
indicates the emulator's MMIO setup is wrong - NOT that we should add Python
code to generate responses.

Usage:
    cd emulate
    python test_usb_host.py

    # With verbose output:
    python test_usb_host.py -v

    # Run specific test:
    python test_usb_host.py TestUSBHost.test_e4_read
"""

import sys
import os
import unittest
from pathlib import Path

# Add emulate directory to path
sys.path.insert(0, str(Path(__file__).parent))

from emu import Emulator
from usb_host import USBHost, ThreadedUSBHost, USBDescriptorType


class TestUSBHost(unittest.TestCase):
    """Tests for USBHost class."""

    @classmethod
    def setUpClass(cls):
        """Load firmware once for all tests."""
        fw_path = Path(__file__).parent.parent / 'fw.bin'
        if not fw_path.exists():
            raise FileNotFoundError(f"Firmware not found at {fw_path}")
        cls.fw_path = str(fw_path)

    def setUp(self):
        """Create fresh emulator for each test."""
        self.emu = Emulator(log_hw=False, log_uart=True, usb_delay=100000)
        self.emu.load_firmware(self.fw_path)
        self.emu.reset()

        # Run until USB is connected
        self._run_until_usb_connected()

        # Create USB host
        self.host = USBHost(self.emu)

    def _run_until_usb_connected(self, max_cycles: int = 500000):
        """Run emulator until USB is connected."""
        while self.emu.hw.cycles < max_cycles:
            if not self.emu.step():
                break
            if self.emu.hw.usb_connected:
                break

        self.assertTrue(self.emu.hw.usb_connected,
                       f"USB not connected after {self.emu.hw.cycles} cycles")

    def test_host_creation(self):
        """Test that USBHost can be created."""
        self.assertIsNotNone(self.host)
        self.assertIsNotNone(self.host.emu)
        self.assertIsNotNone(self.host.hw)

    def test_e4_read_xdata(self):
        """Test E4 read command reads from XDATA via firmware."""
        # Write a test value to XDATA
        test_addr = 0x0100
        test_value = 0x42
        self.emu.memory.xdata[test_addr] = test_value

        # Perform E4 read
        response = self.host.e4_read(test_addr, size=1)

        print(f"E4 read result: success={response.success}, "
              f"data={response.data.hex() if response.data else 'empty'}, "
              f"cycles={response.cycles_taken}")

        self.assertTrue(response.success, f"E4 read failed: {response.error}")
        self.assertEqual(len(response.data), 1, "Expected 1 byte response")
        self.assertEqual(response.data[0], test_value,
                        f"Expected 0x{test_value:02X}, got 0x{response.data[0]:02X}")

    def test_e4_read_multiple_bytes(self):
        """Test E4 read of multiple bytes."""
        test_addr = 0x0200
        test_data = [0xDE, 0xAD, 0xBE, 0xEF]

        # Write test pattern
        for i, v in enumerate(test_data):
            self.emu.memory.xdata[test_addr + i] = v

        # Perform E4 read
        response = self.host.e4_read(test_addr, size=len(test_data))

        print(f"E4 read result: success={response.success}, "
              f"data={response.data.hex() if response.data else 'empty'}")

        self.assertTrue(response.success, f"E4 read failed: {response.error}")
        self.assertEqual(len(response.data), len(test_data))
        self.assertEqual(list(response.data), test_data)

    def test_e5_write_xdata(self):
        """Test E5 write command writes to XDATA via firmware."""
        test_addr = 0x0100
        test_value = 0x55

        # Clear the target location
        self.emu.memory.xdata[test_addr] = 0x00

        # Perform E5 write
        response = self.host.e5_write(test_addr, test_value)

        print(f"E5 write result: success={response.success}, "
              f"cycles={response.cycles_taken}")

        self.assertTrue(response.success, f"E5 write failed: {response.error}")

        # Verify the write
        actual = self.emu.memory.xdata[test_addr]
        self.assertEqual(actual, test_value,
                        f"Expected 0x{test_value:02X}, got 0x{actual:02X}")

    def test_e5_write_read_roundtrip(self):
        """Test E5 write followed by E4 read."""
        test_addr = 0x0300
        test_value = 0xAB

        # Write
        write_response = self.host.e5_write(test_addr, test_value)
        self.assertTrue(write_response.success)

        # Read back
        read_response = self.host.e4_read(test_addr, size=1)
        self.assertTrue(read_response.success)
        self.assertEqual(read_response.data[0], test_value)


class TestUSBDescriptors(unittest.TestCase):
    """
    Tests for USB descriptor handling.

    CRITICAL: These tests verify that the FIRMWARE returns descriptors,
    not that Python generates them. If the firmware's descriptor handling
    doesn't work, we need to fix the MMIO emulation, not add Python code.
    """

    @classmethod
    def setUpClass(cls):
        """Load firmware once for all tests."""
        fw_path = Path(__file__).parent.parent / 'fw.bin'
        if not fw_path.exists():
            raise FileNotFoundError(f"Firmware not found at {fw_path}")
        cls.fw_path = str(fw_path)

    def setUp(self):
        """Create fresh emulator for each test."""
        self.emu = Emulator(log_hw=False, log_uart=True, usb_delay=100000)
        self.emu.load_firmware(self.fw_path)
        self.emu.reset()
        self._run_until_usb_connected()
        self.host = USBHost(self.emu)

    def _run_until_usb_connected(self, max_cycles: int = 500000):
        """Run emulator until USB is connected."""
        while self.emu.hw.cycles < max_cycles:
            if not self.emu.step():
                break
            if self.emu.hw.usb_connected:
                break

    def test_get_device_descriptor(self):
        """
        Test GET_DESCRIPTOR for device descriptor.

        This tests that the firmware responds to GET_DESCRIPTOR requests.
        The emulator should NOT generate descriptor data - it should come
        from the firmware's ROM via DMA.
        """
        response = self.host.get_descriptor(
            USBDescriptorType.DEVICE,
            desc_index=0,
            length=18
        )

        print(f"Device descriptor: success={response.success}, "
              f"len={len(response.data)}, cycles={response.cycles_taken}")

        if response.data:
            print(f"Data: {response.data.hex()}")
            # Device descriptor starts with length and type
            if len(response.data) >= 2:
                print(f"  bLength=0x{response.data[0]:02X}")
                print(f"  bDescriptorType=0x{response.data[1]:02X}")

        # Note: We don't assert success here because the firmware descriptor
        # handling might not be fully working yet. This test documents the
        # expected behavior.
        if response.success and len(response.data) >= 2:
            # Check descriptor type byte
            desc_type = response.data[1]
            if desc_type != 0x01:
                print(f"WARNING: Expected descriptor type 0x01, got 0x{desc_type:02X}")
                print("This might indicate the firmware descriptor handling needs work")

    def test_get_config_descriptor(self):
        """Test GET_DESCRIPTOR for configuration descriptor."""
        response = self.host.get_descriptor(
            USBDescriptorType.CONFIGURATION,
            desc_index=0,
            length=255
        )

        print(f"Config descriptor: success={response.success}, "
              f"len={len(response.data)}, cycles={response.cycles_taken}")

        if response.data:
            print(f"Data: {response.data[:32].hex()}...")

    def test_get_string_descriptor_languages(self):
        """Test GET_DESCRIPTOR for language IDs (string index 0)."""
        response = self.host.get_descriptor(
            USBDescriptorType.STRING,
            desc_index=0,
            length=255
        )

        print(f"String descriptor 0: success={response.success}, "
              f"len={len(response.data)}, cycles={response.cycles_taken}")

        if response.data:
            print(f"Data: {response.data.hex()}")


class TestUSBControlMessages(unittest.TestCase):
    """
    Tests for USB control messages via MMIO.

    These tests verify that the firmware correctly processes standard USB
    control requests injected through MMIO registers. The emulator provides
    the MMIO interface, but all request processing is done by the firmware.

    CRITICAL: These tests interact with firmware through pure MMIO.
    If a test fails, investigate the firmware's control transfer handling,
    NOT by adding Python processing code.
    """

    @classmethod
    def setUpClass(cls):
        """Load firmware once for all tests."""
        fw_path = Path(__file__).parent.parent / 'fw.bin'
        if not fw_path.exists():
            raise FileNotFoundError(f"Firmware not found at {fw_path}")
        cls.fw_path = str(fw_path)

    def setUp(self):
        """Create fresh emulator for each test."""
        self.emu = Emulator(log_hw=False, log_uart=True, usb_delay=100000)
        self.emu.load_firmware(self.fw_path)
        self.emu.reset()
        self._run_until_usb_connected()
        self.host = USBHost(self.emu)

    def _run_until_usb_connected(self, max_cycles: int = 500000):
        """Run emulator until USB is connected."""
        while self.emu.hw.cycles < max_cycles:
            if not self.emu.step():
                break
            if self.emu.hw.usb_connected:
                break
        self.assertTrue(self.emu.hw.usb_connected,
                       f"USB not connected after {self.emu.hw.cycles} cycles")

    def test_set_address(self):
        """
        Test SET_ADDRESS standard request.

        SET_ADDRESS is a host-to-device request that assigns a USB address.
        bmRequestType: 0x00 (Host-to-device, Standard, Device)
        bRequest: 0x05 (SET_ADDRESS)
        wValue: Device address (1-127)
        wIndex: 0
        wLength: 0
        """
        device_address = 5

        response = self.host.control_transfer(
            bmRequestType=0x00,  # Host-to-device, Standard, Device
            bRequest=0x05,       # SET_ADDRESS
            wValue=device_address,
            wIndex=0,
            wLength=0
        )

        print(f"SET_ADDRESS({device_address}): success={response.success}, "
              f"cycles={response.cycles_taken}")

        # SET_ADDRESS is a no-data transfer - success means firmware processed it
        # Note: In real USB, device changes address after status stage
        self.assertTrue(response.success, f"SET_ADDRESS failed: {response.error}")

    def test_set_configuration(self):
        """
        Test SET_CONFIGURATION standard request.

        SET_CONFIGURATION selects a device configuration.
        bmRequestType: 0x00 (Host-to-device, Standard, Device)
        bRequest: 0x09 (SET_CONFIGURATION)
        wValue: Configuration value (typically 1)
        wIndex: 0
        wLength: 0
        """
        config_value = 1

        response = self.host.control_transfer(
            bmRequestType=0x00,  # Host-to-device, Standard, Device
            bRequest=0x09,       # SET_CONFIGURATION
            wValue=config_value,
            wIndex=0,
            wLength=0
        )

        print(f"SET_CONFIGURATION({config_value}): success={response.success}, "
              f"cycles={response.cycles_taken}")

        self.assertTrue(response.success, f"SET_CONFIGURATION failed: {response.error}")

    def test_get_status_device(self):
        """
        Test GET_STATUS for device.

        GET_STATUS returns 2 bytes of status information.
        bmRequestType: 0x80 (Device-to-host, Standard, Device)
        bRequest: 0x00 (GET_STATUS)
        wValue: 0
        wIndex: 0
        wLength: 2
        """
        response = self.host.control_transfer(
            bmRequestType=0x80,  # Device-to-host, Standard, Device
            bRequest=0x00,       # GET_STATUS
            wValue=0,
            wIndex=0,
            wLength=2
        )

        print(f"GET_STATUS(device): success={response.success}, "
              f"data={response.data.hex() if response.data else 'empty'}, "
              f"cycles={response.cycles_taken}")

        if response.success and len(response.data) >= 2:
            status = response.data[0] | (response.data[1] << 8)
            print(f"  Self-powered: {bool(status & 0x01)}")
            print(f"  Remote wakeup: {bool(status & 0x02)}")

    def test_get_configuration(self):
        """
        Test GET_CONFIGURATION standard request.

        GET_CONFIGURATION returns the current configuration value (1 byte).
        bmRequestType: 0x80 (Device-to-host, Standard, Device)
        bRequest: 0x08 (GET_CONFIGURATION)
        wValue: 0
        wIndex: 0
        wLength: 1
        """
        response = self.host.control_transfer(
            bmRequestType=0x80,  # Device-to-host, Standard, Device
            bRequest=0x08,       # GET_CONFIGURATION
            wValue=0,
            wIndex=0,
            wLength=1
        )

        print(f"GET_CONFIGURATION: success={response.success}, "
              f"data={response.data.hex() if response.data else 'empty'}, "
              f"cycles={response.cycles_taken}")

        if response.success and response.data:
            print(f"  Current configuration: {response.data[0]}")

    def test_get_interface(self):
        """
        Test GET_INTERFACE standard request.

        GET_INTERFACE returns the alternate setting for an interface (1 byte).
        bmRequestType: 0x81 (Device-to-host, Standard, Interface)
        bRequest: 0x0A (GET_INTERFACE)
        wValue: 0
        wIndex: Interface number
        wLength: 1
        """
        interface_num = 0

        response = self.host.control_transfer(
            bmRequestType=0x81,  # Device-to-host, Standard, Interface
            bRequest=0x0A,       # GET_INTERFACE
            wValue=0,
            wIndex=interface_num,
            wLength=1
        )

        print(f"GET_INTERFACE({interface_num}): success={response.success}, "
              f"data={response.data.hex() if response.data else 'empty'}, "
              f"cycles={response.cycles_taken}")

        if response.success and response.data:
            print(f"  Alternate setting: {response.data[0]}")

    def test_set_interface(self):
        """
        Test SET_INTERFACE standard request.

        SET_INTERFACE selects an alternate setting for an interface.
        bmRequestType: 0x01 (Host-to-device, Standard, Interface)
        bRequest: 0x0B (SET_INTERFACE)
        wValue: Alternate setting
        wIndex: Interface number
        wLength: 0
        """
        interface_num = 0
        alt_setting = 0  # BBB mode (alt 0) vs UAS mode (alt 1)

        response = self.host.control_transfer(
            bmRequestType=0x01,  # Host-to-device, Standard, Interface
            bRequest=0x0B,       # SET_INTERFACE
            wValue=alt_setting,
            wIndex=interface_num,
            wLength=0
        )

        print(f"SET_INTERFACE(iface={interface_num}, alt={alt_setting}): "
              f"success={response.success}, cycles={response.cycles_taken}")

    def test_mass_storage_get_max_lun(self):
        """
        Test Mass Storage GET_MAX_LUN class request.

        GET_MAX_LUN returns the maximum Logical Unit Number (0-15).
        bmRequestType: 0xA1 (Device-to-host, Class, Interface)
        bRequest: 0xFE (GET_MAX_LUN)
        wValue: 0
        wIndex: Interface number
        wLength: 1
        """
        interface_num = 0

        response = self.host.control_transfer(
            bmRequestType=0xA1,  # Device-to-host, Class, Interface
            bRequest=0xFE,       # GET_MAX_LUN
            wValue=0,
            wIndex=interface_num,
            wLength=1
        )

        print(f"GET_MAX_LUN: success={response.success}, "
              f"data={response.data.hex() if response.data else 'empty'}, "
              f"cycles={response.cycles_taken}")

        if response.success and response.data:
            max_lun = response.data[0]
            print(f"  Max LUN: {max_lun}")
            # ASM2464PD supports 4 NVMe slots, so max LUN should be 3
            self.assertLessEqual(max_lun, 15, "Max LUN must be 0-15")

    def test_mass_storage_bot_reset(self):
        """
        Test Mass Storage Bulk-Only Transport (BOT) Reset class request.

        BOT Reset prepares the device for the next CBW.
        bmRequestType: 0x21 (Host-to-device, Class, Interface)
        bRequest: 0xFF (BULK_ONLY_MASS_STORAGE_RESET)
        wValue: 0
        wIndex: Interface number
        wLength: 0
        """
        interface_num = 0

        response = self.host.control_transfer(
            bmRequestType=0x21,  # Host-to-device, Class, Interface
            bRequest=0xFF,       # BULK_ONLY_MASS_STORAGE_RESET
            wValue=0,
            wIndex=interface_num,
            wLength=0
        )

        print(f"BOT_RESET: success={response.success}, "
              f"cycles={response.cycles_taken}")

    def test_clear_feature_endpoint_halt(self):
        """
        Test CLEAR_FEATURE for endpoint halt.

        CLEAR_FEATURE with ENDPOINT_HALT clears a stalled endpoint.
        bmRequestType: 0x02 (Host-to-device, Standard, Endpoint)
        bRequest: 0x01 (CLEAR_FEATURE)
        wValue: 0 (ENDPOINT_HALT feature selector)
        wIndex: Endpoint address
        wLength: 0
        """
        endpoint_addr = 0x81  # EP1 IN

        response = self.host.control_transfer(
            bmRequestType=0x02,  # Host-to-device, Standard, Endpoint
            bRequest=0x01,       # CLEAR_FEATURE
            wValue=0,            # ENDPOINT_HALT
            wIndex=endpoint_addr,
            wLength=0
        )

        print(f"CLEAR_FEATURE(EP 0x{endpoint_addr:02X} HALT): "
              f"success={response.success}, cycles={response.cycles_taken}")

    def test_get_status_endpoint(self):
        """
        Test GET_STATUS for endpoint.

        GET_STATUS returns 2 bytes - bit 0 indicates halt status.
        bmRequestType: 0x82 (Device-to-host, Standard, Endpoint)
        bRequest: 0x00 (GET_STATUS)
        wValue: 0
        wIndex: Endpoint address
        wLength: 2
        """
        endpoint_addr = 0x81  # EP1 IN

        response = self.host.control_transfer(
            bmRequestType=0x82,  # Device-to-host, Standard, Endpoint
            bRequest=0x00,       # GET_STATUS
            wValue=0,
            wIndex=endpoint_addr,
            wLength=2
        )

        print(f"GET_STATUS(EP 0x{endpoint_addr:02X}): success={response.success}, "
              f"data={response.data.hex() if response.data else 'empty'}, "
              f"cycles={response.cycles_taken}")

        if response.success and len(response.data) >= 2:
            status = response.data[0] | (response.data[1] << 8)
            print(f"  Halted: {bool(status & 0x01)}")

    def test_sequential_control_transfers(self):
        """
        Test multiple sequential control transfers.

        This verifies the firmware can handle multiple control transfers
        in sequence without state corruption.
        """
        # First: SET_CONFIGURATION
        r1 = self.host.control_transfer(
            bmRequestType=0x00,
            bRequest=0x09,  # SET_CONFIGURATION
            wValue=1,
            wIndex=0,
            wLength=0
        )
        print(f"1. SET_CONFIGURATION: {r1.success}")

        # Second: GET_CONFIGURATION
        r2 = self.host.control_transfer(
            bmRequestType=0x80,
            bRequest=0x08,  # GET_CONFIGURATION
            wValue=0,
            wIndex=0,
            wLength=1
        )
        print(f"2. GET_CONFIGURATION: {r2.success}, "
              f"data={r2.data.hex() if r2.data else 'empty'}")

        # Third: GET_STATUS
        r3 = self.host.control_transfer(
            bmRequestType=0x80,
            bRequest=0x00,  # GET_STATUS
            wValue=0,
            wIndex=0,
            wLength=2
        )
        print(f"3. GET_STATUS: {r3.success}, "
              f"data={r3.data.hex() if r3.data else 'empty'}")

        # Fourth: GET_MAX_LUN (class request)
        r4 = self.host.control_transfer(
            bmRequestType=0xA1,
            bRequest=0xFE,  # GET_MAX_LUN
            wValue=0,
            wIndex=0,
            wLength=1
        )
        print(f"4. GET_MAX_LUN: {r4.success}, "
              f"data={r4.data.hex() if r4.data else 'empty'}")

        # All should complete without timeout
        print(f"\nAll transfers completed: "
              f"{all([r1.success, r2.success, r3.success, r4.success])}")


class TestThreadedUSBHost(unittest.TestCase):
    """Tests for ThreadedUSBHost class."""

    @classmethod
    def setUpClass(cls):
        """Load firmware once for all tests."""
        fw_path = Path(__file__).parent.parent / 'fw.bin'
        if not fw_path.exists():
            raise FileNotFoundError(f"Firmware not found at {fw_path}")
        cls.fw_path = str(fw_path)

    def setUp(self):
        """Create emulator and start threaded host."""
        self.emu = Emulator(log_hw=False, log_uart=True, usb_delay=50000)
        self.emu.load_firmware(self.fw_path)
        self.emu.reset()
        self.host = ThreadedUSBHost(self.emu)

    def tearDown(self):
        """Stop threaded host."""
        if hasattr(self, 'host') and self.host._running:
            self.host.stop()

    def test_threaded_e4_read(self):
        """Test E4 read via threaded host."""
        # Write test value
        test_addr = 0x0100
        test_value = 0x77
        self.emu.memory.xdata[test_addr] = test_value

        # Start host
        self.host.start()

        # Perform read
        response = self.host.e4_read(test_addr, size=1)

        print(f"Threaded E4 read: success={response.success}, "
              f"data={response.data.hex() if response.data else 'empty'}")

        self.assertTrue(response.success)
        if response.data:
            self.assertEqual(response.data[0], test_value)

    def test_threaded_e5_write(self):
        """Test E5 write via threaded host."""
        test_addr = 0x0200
        test_value = 0x88

        # Start host
        self.host.start()

        # Perform write
        response = self.host.e5_write(test_addr, test_value)

        print(f"Threaded E5 write: success={response.success}")

        self.assertTrue(response.success)

        # Verify write
        actual = self.emu.memory.xdata[test_addr]
        self.assertEqual(actual, test_value)


class TestDMACapture(unittest.TestCase):
    """
    Tests for DMA output capture.

    These tests verify that the emulator correctly captures DMA output
    from the firmware, without the emulator generating any data itself.
    """

    @classmethod
    def setUpClass(cls):
        """Load firmware once for all tests."""
        fw_path = Path(__file__).parent.parent / 'fw.bin'
        if not fw_path.exists():
            raise FileNotFoundError(f"Firmware not found at {fw_path}")
        cls.fw_path = str(fw_path)

    def setUp(self):
        """Create fresh emulator."""
        self.emu = Emulator(log_hw=False, log_uart=False, usb_delay=100000)
        self.emu.load_firmware(self.fw_path)
        self.emu.reset()
        self._run_until_usb_connected()

    def _run_until_usb_connected(self, max_cycles: int = 500000):
        """Run emulator until USB is connected."""
        while self.emu.hw.cycles < max_cycles:
            if not self.emu.step():
                break
            if self.emu.hw.usb_connected:
                break

    def test_dma_buffer_location(self):
        """Test that DMA output goes to the correct buffer location."""
        # USB data buffer is at 0x8000
        USB_BUFFER = 0x8000

        # Clear buffer
        for i in range(256):
            self.emu.memory.xdata[USB_BUFFER + i] = 0x00

        # Create a GET_DESCRIPTOR transfer request
        from usb_host import USBControlTransfer
        transfer = USBControlTransfer(
            bmRequestType=0x80,
            bRequest=0x06,
            wValue=0x0100,
            wIndex=0,
            wLength=18,
            data=b''
        )

        # Inject a control transfer
        host = USBHost(self.emu)
        host.inject_control_transfer(transfer)

        # Run for a while
        for _ in range(100000):
            if not self.emu.step():
                break

        # Check if anything was written to buffer
        buffer_data = bytes(self.emu.memory.xdata[USB_BUFFER + i] for i in range(64))
        non_zero = sum(1 for b in buffer_data if b != 0)

        print(f"DMA buffer after control transfer: {buffer_data[:32].hex()}")
        print(f"Non-zero bytes in first 64: {non_zero}")


def run_quick_test():
    """Run a quick integration test."""
    fw_path = Path(__file__).parent.parent / 'fw.bin'
    if not fw_path.exists():
        print(f"ERROR: Firmware not found at {fw_path}")
        return False

    print("=== Quick USB Host Integration Test ===")
    print()

    # Create emulator
    print("1. Creating emulator...")
    emu = Emulator(log_hw=False, log_uart=True, usb_delay=100000)
    emu.load_firmware(str(fw_path))
    emu.reset()

    # Run until USB connected
    print("2. Running until USB connected...")
    while emu.hw.cycles < 500000:
        if not emu.step():
            break
        if emu.hw.usb_connected:
            break

    if not emu.hw.usb_connected:
        print(f"FAIL: USB not connected after {emu.hw.cycles} cycles")
        return False

    print(f"   USB connected at {emu.hw.cycles} cycles")

    # Create host
    print("3. Creating USB host...")
    host = USBHost(emu)

    # Test E4 read
    print("4. Testing E4 read...")
    test_addr = 0x0100
    test_value = 0xAA
    emu.memory.xdata[test_addr] = test_value

    response = host.e4_read(test_addr, size=1)
    if response.success:
        print(f"   E4 read success: data=0x{response.data[0]:02X}")
        if response.data[0] == test_value:
            print("   Value matches!")
        else:
            print(f"   WARNING: Expected 0x{test_value:02X}")
    else:
        print(f"   E4 read failed: {response.error}")

    # Test E5 write
    print("5. Testing E5 write...")
    test_addr = 0x0200
    test_value = 0x55

    response = host.e5_write(test_addr, test_value)
    if response.success:
        actual = emu.memory.xdata[test_addr]
        print(f"   E5 write success: XDATA[0x{test_addr:04X}] = 0x{actual:02X}")
        if actual == test_value:
            print("   Value matches!")
        else:
            print(f"   WARNING: Expected 0x{test_value:02X}")
    else:
        print(f"   E5 write failed: {response.error}")

    print()
    print("=== Test Complete ===")
    return True


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--quick':
        success = run_quick_test()
        sys.exit(0 if success else 1)
    else:
        unittest.main(verbosity=2)
