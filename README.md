# ASM2464PD Firmware Reimplementation

Open-source C firmware for the ASM2464PD USB4/Thunderbolt to NVMe bridge controller, reverse-engineered to match the original 8051-based firmware.

## Target Hardware

**ASM2464PD** - A multi-interface bridge IC featuring:
- USB 3.2 Gen2x2 / USB4 / Thunderbolt host interface
- PCIe 4.0 x4 NVMe storage interface
- 8051 CPU (~114 MHz, 1T architecture)
- 98KB firmware in two 64KB code banks

## Building

Requires SDCC (Small Device C Compiler).

```bash
make              # Build firmware.bin
make wrapped      # Build with ASM2464 header (checksum + CRC)
make compare      # Compare against original fw.bin
make clean        # Clean build artifacts
```

Output: `build/firmware.bin`

## Project Structure

```
src/
├── main.c              # Entry point and initialization
├── utils.c             # Utility functions
├── registers.h         # Hardware register definitions (0x6000+)
├── globals.h           # Global variables (<0x6000)
├── sfr.h               # 8051 Special Function Registers
├── types.h             # Type definitions
└── drivers/
    ├── usb.c           # USB protocol and endpoints
    ├── dma.c           # DMA engine control
    ├── nvme.c          # NVMe command interface
    ├── pcie.c          # PCIe/Thunderbolt interface
    ├── scsi.c          # SCSI command handler
    ├── flash.c         # SPI flash controller
    ├── timer.c         # Hardware timers
    ├── uart.c          # Debug UART (921600 baud)
    ├── power.c         # Power management
    ├── phy.c           # PHY/link layer
    ├── protocol.c      # Main protocol state machine
    ├── cmd.c           # Command processing
    ├── bank1.c         # Bank 1 functions (0x10000+)
    ├── buffer.c        # Buffer management
    ├── interrupt.c     # Interrupt handling
    ├── error_log.c     # Error logging
    └── state_helpers.c # State machine helpers
```

## Current Status

| Metric | Value |
|--------|-------|
| Built firmware size | 10,436 bytes |
| Original firmware size | 98,012 bytes |
| Completion | ~10.6% by size |
| Functions implemented | ~170 of ~785 |

### Subsystem Progress

- **USB**: Core enumeration, endpoint dispatch, Mass Storage BOT
- **DMA**: Channel configuration, transfer setup
- **NVMe**: Command interface, queue management
- **PCIe**: Link layer, Thunderbolt support (partial)
- **Flash**: SPI operations, configuration storage
- **Timers**: Hardware timer control

### Major Remaining Work

- USB protocol stack completion (~80 functions)
- NVMe command processing (~60 functions)
- DMA completion handlers (~40 functions)
- Bank 1 functions (~100 functions)
- Dispatch stubs (~80 functions)

## Reference Materials

- `fw.bin` - Original firmware binary, hash `a8ce063d425ef32af31a655949993b0a9b0dd6ad`
- `ghidra.c` - Ghidra decompilation reference
- `usb-to-pcie-re/` - Reverse engineering documentation
- `usb.py` - Python USB communication library (tinygrad)

## Memory Map

```
CODE Bank 0: 0x00000-0x0FFFF (direct access)
CODE Bank 1: 0x10000-0x17F12 (via DPX banking, mapped at 0x8000)
XDATA:       0x0000-0x5FFF  (globals/work area)
REGISTERS:   0x6000-0xFFFF  (memory-mapped I/O)
```

## Development Guidelines

1. Each function should match a function in the original firmware
2. Include address range comments before each function
3. Use `REG_` prefix for registers, `G_` prefix for globals
4. Use `radare2` or Ghidra to analyze `fw.bin`
5. Build and compare regularly to track progress

## License

Reverse engineering project for educational and interoperability purposes.
