XDATA should not be used anywhere outside registers.h and globals.h unless you absolutely need to. Registers should be defined in the headers and used. Add bit defines as apppropriate also.

Functions and registers should not have names like helper_XXXX or handler_XXXX or reg_XXXX. Give them a name based on what the function or register does, but only if you are confident.

extern void should not be used to call functions. The proper header file should be included.

All functions should be functionally the same as the ones in the real firmware and should be reconstructed from the real firmware. They should have headers like
```
/*
 * pcie_clear_address_regs - Clear address offset registers
 * Address: 0x9a9c-0x9aa2 (7 bytes)
 *
 * Clears IDATA locations 0x63 and 0x64 (address offset).
 *
 * Original disassembly:
 *   9a9c: clr a
 *   9a9d: mov r0, #0x63
 ...

For bank 1 it should look like
```
/*
 * pcie_addr_store - Store PCIe address with offset adjustment
 * Bank 1 Address: 0x839c-0x83b8 (29 bytes) [actual addr: 0x1039c]
 *
 * Calls e902 helper, loads current address from 0x05AF,
 ```