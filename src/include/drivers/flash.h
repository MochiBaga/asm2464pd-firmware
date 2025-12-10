/*
 * flash.h - Flash driver declarations
 */
#ifndef _FLASH_H_
#define _FLASH_H_

#include "../types.h"

/* Flash math utilities */
uint8_t flash_div8(uint8_t dividend, uint8_t divisor);
uint8_t flash_mod8(uint8_t dividend, uint8_t divisor);

/* Flash memory operations */
void flash_add_to_xdata16(__xdata uint8_t *ptr, uint16_t val);
void flash_write_word(__xdata uint8_t *ptr, uint16_t val);
void flash_write_idata_word(__idata uint8_t *ptr, uint16_t val);
void flash_write_r1_xdata_word(uint8_t r1_addr, uint16_t val);

/* Flash status and control */
void flash_poll_busy(void);
uint8_t flash_set_cmd(uint8_t cmd);
void flash_set_mode_enable(void);
void flash_set_mode_bit4(void);
void flash_start_transaction(void);
void flash_clear_mode_bits(void);
void flash_clear_mode_bits_6_7(void);

/* Flash address setup */
void flash_set_addr_md(__xdata uint8_t *addr_ptr);
void flash_set_addr_hi(__xdata uint8_t *addr_ptr);
void flash_set_data_len(__xdata uint8_t *len_ptr);

/* Flash transactions */
void flash_run_transaction(uint8_t cmd);
uint8_t flash_wait_and_poll(void);
void flash_read_status(void);
uint8_t flash_read_buffer_and_status(void);

/* Flash buffer access */
uint8_t flash_get_buffer_byte(uint16_t offset);
void flash_set_buffer_byte(uint16_t offset, uint8_t val);

/* Flash write operations */
void flash_write_enable(void);
void flash_write_page(uint32_t addr, uint8_t len);
void flash_read(uint32_t addr, uint8_t len);
void flash_erase_sector(uint32_t addr);

/* Flash dispatch stubs */
void flash_dispatch_stub_873a(void);
void flash_dispatch_stub_8743(void);
void flash_dispatch_stub_874c(void);
void flash_dispatch_stub_8d6e(void);

/* Flash handlers */
void flash_command_handler(void);
void system_init_from_flash(void);

#endif /* _FLASH_H_ */
