/*
 * power.h - Power management driver declarations
 */
#ifndef _POWER_H_
#define _POWER_H_

#include "../types.h"

/* Power state control */
void power_set_suspended(void);
void power_clear_suspended(void);
void power_set_state(void);
uint8_t power_get_status_bit6(void);

/* Clock control */
void power_enable_clocks(void);
void power_disable_clocks(void);
void power_set_clock_bit1(void);

/* Power initialization */
void power_config_init(void);
void power_check_status_e647(void);
void power_check_status(uint8_t param);

/* Power state machine */
uint8_t power_state_machine_d02a(uint8_t max_iterations);
uint8_t power_check_state_dde2(void);

/* Power event handlers */
void power_set_suspended_and_event_cad6(void);
void power_toggle_usb_bit2_caed(void);
void power_set_phy_bit1_cafb(void);
void phy_power_init_d916(uint8_t param);
void power_clear_init_flag(void);
void power_set_event_ctrl(void);

/* USB power */
void usb_power_init(void);

/* Power status */
uint8_t power_get_state_nibble_cb0f(void);
void power_set_link_status_cb19(void);
void power_set_status_bit6_cb23(void);
void power_clear_interface_flags_cb2d(void);

/* PHY power configuration */
void power_phy_init_config_cb37(void);
void power_check_event_ctrl_c9fa(void);
void power_reset_sys_state_c9ef(void);
void power_config_d630(uint8_t param);

#endif /* _POWER_H_ */
