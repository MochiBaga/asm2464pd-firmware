/*
 * power.h - Power Management Driver
 *
 * The power management subsystem controls device power states, clock
 * gating, and suspend/resume handling for the ASM2464PD bridge. It
 * coordinates power transitions between USB, PCIe, and internal blocks.
 *
 * POWER STATES:
 *   Active (D0):    Full operation, all clocks running
 *   Idle:           Reduced activity, some clocks gated
 *   Suspended (D3): Minimal power, wake-on-event capability
 *
 * USB POWER STATES:
 *   U0: Active operation
 *   U1: Standby (fast exit latency)
 *   U2: Sleep (longer exit latency)
 *   U3: Suspend (lowest power, host-initiated wake)
 *
 * PCIE POWER STATES:
 *   L0:  Active
 *   L0s: Standby (fast recovery)
 *   L1:  Low power idle
 *   L2:  Auxiliary power only
 *
 * REGISTER MAP (0x92C0-0x92CF):
 *   0x92C0: Power Control 0 - Main power enable
 *   0x92C1: Power Control 1 - Clock config
 *   0x92C2: Power Status - State flags (bit 6: suspended)
 *   0x92C5: Power Control 5 - PHY power
 *   0x92C6: Power Control 6 - Clock gating
 *   0x92C7: Power Control 7 - Clock gating extension
 *
 * STATE MACHINE:
 *   power_state_machine_d02a() implements the main power state
 *   transitions, coordinating between USB and PCIe link states.
 *
 * USAGE:
 *   power_config_init();          // Initialize power subsystem
 *   power_enable_clocks();        // Enable all clocks
 *   // ... normal operation ...
 *   power_set_suspended();        // Enter suspend
 *   // ... wake event ...
 *   power_clear_suspended();      // Resume operation
 */
#ifndef _POWER_H_
#define _POWER_H_

#include "../types.h"

/* Power state control */
void power_set_suspended(void);                 /* 0xcb23-0xcb2c */
void power_clear_suspended(void);               /* 0xcb2d-0xcb36 */
void power_set_state(void);                     /* 0x53c0-0x53d3 */
uint8_t power_get_status_bit6(void);            /* 0x3023-0x302e */

/* Clock control */
void power_enable_clocks(void);                 /* 0xcb6f-0xcb87 */
void power_disable_clocks(void);                /* 0xcb88-0xcb9a */
void power_set_clock_bit1(void);                /* 0xcb4b-0xcb53 */

/* Power initialization */
void power_config_init(void);                   /* 0xcb37-0xcb4a */
void power_check_status_e647(void);             /* 0xe647-0xe65e (Bank 1) */
void power_check_status(uint8_t param);         /* stub */

/* Power state machine */
uint8_t power_state_machine_d02a(uint8_t max_iterations);   /* 0xd02a-0xd07e */
uint8_t power_check_state_dde2(void);           /* 0xdde2-0xde15 */

/* Power event handlers */
void power_set_suspended_and_event_cad6(void);  /* 0xcad6-0xcaec */
void power_toggle_usb_bit2_caed(void);          /* 0xcaed-0xcafa */
void power_set_phy_bit1_cafb(void);             /* 0xcafb-0xcb08 */
void phy_power_init_d916(uint8_t param);        /* 0xd916-0xd995 */
void power_clear_init_flag(void);               /* 0xcb09-0xcb14 */
void power_set_event_ctrl(void);                /* 0xcb15-0xcb22 */

/* USB power */
void usb_power_init(void);                      /* 0x0327-0x032a */

/* Power status */
uint8_t power_get_state_nibble_cb0f(void);      /* 0xcb0f-0xcb14 */
void power_set_link_status_cb19(void);          /* 0xcb19-0xcb22 */
void power_set_status_bit6_cb23(void);          /* 0xcb23-0xcb2c */
void power_clear_interface_flags_cb2d(void);    /* 0xcb2d-0xcb36 */

/* PHY power configuration */
void power_phy_init_config_cb37(void);          /* 0xcb37-0xcb4a */
void power_check_event_ctrl_c9fa(void);         /* 0xc9fa-0xca0d */
void power_reset_sys_state_c9ef(void);          /* 0xc9ef-0xc9f9 */
void power_config_d630(uint8_t param);          /* 0xd630-0xd6a0 */

#endif /* _POWER_H_ */
