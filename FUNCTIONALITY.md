# ASM2464PD USB4 eGPU Functionality

## Overview

The original firmware supports USB4 PCIe tunneling. Key functions:

| Function | Address | Status | Location |
|----------|---------|--------|----------|
| pcie_tunnel_enable | 0xC00D | DONE | drivers/pcie.c |
| pcie_tunnel_setup | 0xCD6C | Stub | app/dispatch.c |
| pcie_adapter_config | 0xC8DB | TODO | - |
| pcie_lane_config | 0xD436 | DONE | drivers/phy.c |

## PCIe Tunnel Adapter Registers (0xB400-0xB4FF)

| Register | Address | Function |
|----------|---------|----------|
| REG_PCIE_TUNNEL_CTRL | 0xB401 | Tunnel control (bit 0 = enable) |
| REG_PCIE_CTRL_B402 | 0xB402 | PCIe control flags |
| REG_PCIE_LINK_PARAM | 0xB404 | Link parameters |
| REG_PCIE_ADAPTER_10 | 0xB410 | Adapter config byte 0 |
| REG_PCIE_ADAPTER_11 | 0xB411 | Adapter config byte 1 |
| REG_PCIE_ADAPTER_12 | 0xB412 | Adapter config byte 2 |
| REG_PCIE_ADAPTER_13 | 0xB413 | Adapter config byte 3 |
| REG_PCIE_ADAPTER_15 | 0xB415 | Adapter config |
| REG_PCIE_ADAPTER_1A | 0xB41A | Link config low |
| REG_PCIE_ADAPTER_1B | 0xB41B | Link config high |
| REG_PCIE_ADAPTER_20 | 0xB420 | Data register |
| REG_PCIE_ADAPTER_22 | 0xB422 | Status byte 0 |
| REG_PCIE_ADAPTER_23 | 0xB423 | Status byte 1 |
| REG_PCIE_ADAPTER_25 | 0xB425 | Config |
| REG_PCIE_ADAPTER_2A | 0xB42A | Additional config |
| REG_PCIE_LINK_STATE | 0xB430 | Link state (bit 0 = up) |
| REG_PCIE_LANE_CONFIG | 0xB436 | Lane configuration |
| REG_PCIE_ADAPTER_82 | 0xB482 | Adapter mode (0xF0 = tunnel) |

### Other Registers

| Register | Address | Function |
|----------|---------|----------|
| REG_PCIE_TLP_CTRL | 0xB298 | TLP control (bit 4 = tunnel enable) |
| REG_CPU_MODE_NEXT | 0xCA06 | CPU mode (bit 4 = NVMe, clear for tunnel) |

## Implemented Functions

### pcie_tunnel_enable (0xC00D) - DONE

Located in `drivers/pcie.c`. Enables USB4 PCIe tunneling:

```c
void pcie_tunnel_enable(void) {
    if (G_STATE_FLAG_06E6 == 0) return;

    // Clear state flags
    G_STATE_FLAG_06E6 = 0;
    XDATA8(0x06E7) = 1;
    XDATA8(0x06E8) = 1;

    // Clear PCIe transaction state
    G_PCIE_TXN_COUNT_HI = 0;
    XDATA8(0x06EB) = 0;
    XDATA8(0x05AC) = 0;
    XDATA8(0x05AD) = 0;

    // Clear tunnel control bit 0
    REG_PCIE_TUNNEL_CTRL &= 0xFE;

    // Call tunnel setup
    pcie_tunnel_setup();  // 0xCD6C

    // Clear CPU mode bit 4 (exit NVMe mode)
    REG_CPU_MODE_NEXT &= 0xEF;

    // Configure all 4 lanes
    pcie_lane_config(0x0F);  // 0xD436

    // Clear state
    IDATA8(0x62) = 0;
    G_MAX_LOG_ENTRIES = 0;
}
```

### pcie_tunnel_setup (0xCD6C) - Stub

Currently a dispatch stub in `app/dispatch.c`. Needs full implementation:

```c
void pcie_tunnel_setup(void) {
    // Clear CPU mode bit 4
    REG_CPU_MODE_NEXT &= 0xEF;

    // Configure adapter (0xC8DB)
    pcie_adapter_config();

    // Set tunnel control via helper
    pcie_helper_99e4(0xB401);

    // Configure adapter mode - set high nibble to 0xF0
    REG_PCIE_ADAPTER_82 = (REG_PCIE_ADAPTER_82 & 0x0F) | 0xF0;

    // Clear tunnel control bit 0
    REG_PCIE_TUNNEL_CTRL &= 0xFE;

    // Clear link state bit 0
    REG_PCIE_LINK_STATE &= 0xFE;

    // Set TLP control bit 4
    REG_PCIE_TLP_CTRL |= 0x10;
}
```

### pcie_adapter_config (0xC8DB) - TODO

Writes adapter config from globals to hardware registers:

```c
void pcie_adapter_config(void) {
    // Copy config from 0x0A52-0x0A54 to adapter registers
    REG_PCIE_ADAPTER_10 = XDATA8(0x0A53);
    REG_PCIE_ADAPTER_11 = XDATA8(0x0A52);
    REG_PCIE_ADAPTER_13 = XDATA8(0x0A54);
    REG_PCIE_ADAPTER_22 = XDATA8(0x0A53);
    REG_PCIE_ADAPTER_23 = XDATA8(0x0A52);
    REG_PCIE_ADAPTER_1A = XDATA8(0x0A53);
    REG_PCIE_ADAPTER_1B = XDATA8(0x0A52);
    // ... plus helpers for 0xB412, 0xB415, 0xB420, 0xB425, 0xB42A
}
```

### pcie_lane_config (0xD436) - DONE

Located in `drivers/phy.c`. Configures PCIe x4 lane setup.

## Data Flow

```
USB4 Host                   ASM2464PD                      GPU
   |                           |                            |
   | USB4 Tunnel Packets       |                            |
   |==========================>|                            |
   |                           | 0xB4xx Adapter             |
   |                           | (hardware passthrough)     |
   |                           |===========================>|
   |                           |                            |
   |                           |<===========================|
   |<==========================|                            |

8051 role: Setup only, not in data path
```

## Initialization Flow

```
main()
  └─> process_init_table()
  └─> main_loop()
        └─> phy_init_sequence_0720()
              └─> pcie_tunnel_setup()      // 0xCD6C
              └─> G_STATE_FLAG_06E6 = 1
        └─> [flag check]
              └─> pcie_tunnel_enable()     // 0xC00D
                    └─> pcie_tunnel_setup()
                    └─> pcie_lane_config(0x0F)
```

## Remaining Work

1. **Implement pcie_tunnel_setup body** - Currently just a dispatch stub, needs full 0xCD6C logic
2. **Implement pcie_adapter_config** (0xC8DB) - Copy config to 0xB4xx registers
3. **Add adapter registers** to registers.h:
   ```c
   #define REG_PCIE_ADAPTER_10    XDATA_REG8(0xB410)
   #define REG_PCIE_ADAPTER_11    XDATA_REG8(0xB411)
   #define REG_PCIE_ADAPTER_12    XDATA_REG8(0xB412)
   #define REG_PCIE_ADAPTER_13    XDATA_REG8(0xB413)
   #define REG_PCIE_ADAPTER_82    XDATA_REG8(0xB482)
   ```
4. **Test** with TB3/USB4 host and GPU
