/*
 * phy.h - PHY driver declarations
 */
#ifndef _PHY_H_
#define _PHY_H_

#include "../types.h"

/* PHY initialization */
void phy_init_sequence(void);
void phy_config_link_params(void);
void phy_register_config(void);
void phy_link_training(void);

/* PHY status */
uint8_t phy_poll_link_ready(void);
uint8_t phy_check_usb_state(void);

/* PCIe control state (in phy.c) */
void pcie_save_ctrl_state(void);
void pcie_restore_ctrl_state(void);
void pcie_lane_config(uint8_t lane_mask);

/* Bank operations */
void bank_read(void) __naked;
void bank_write(void) __naked;

#endif /* _PHY_H_ */
