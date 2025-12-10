/*
 * flash.h - SPI Flash Driver
 *
 * The flash subsystem manages the external SPI flash memory used for
 * firmware storage, configuration data, and runtime parameters. The
 * ASM2464PD boots from this flash and can update it at runtime.
 *
 * FLASH MEMORY MAP (typical):
 *   0x000000-0x00FFFF: Bank 0 firmware (64KB)
 *   0x010000-0x01FFFF: Bank 1 firmware (64KB)
 *   0x020000-0x02FFFF: Configuration data
 *   0x030000+: Reserved/User data
 *
 * REGISTER MAP (0xC89F-0xC8AF):
 *   0xC89F: REG_FLASH_CON      - Control register
 *   0xC8A1: REG_FLASH_ADDR_LO  - Flash address low byte
 *   0xC8A2: REG_FLASH_ADDR_MD  - Flash address middle byte
 *   0xC8A3: REG_FLASH_DATA_LEN - Data length low
 *   0xC8A4: REG_FLASH_DATA_LEN_HI - Data length high
 *   0xC8A9: REG_FLASH_CSR      - Control/Status register
 *   0xC8AA: REG_FLASH_CMD      - SPI command byte
 *   0xC8AB: REG_FLASH_ADDR_HI  - Flash address high byte
 *   0xC8AC: REG_FLASH_ADDR_LEN - Address length
 *   0xC8AD: REG_FLASH_MODE     - Mode register
 *   0xC8AE: REG_FLASH_BUF_OFFSET - Buffer offset
 *
 * SPI PROTOCOL:
 *   The driver implements standard SPI flash commands:
 *   - Read (0x03): Sequential read from address
 *   - Page Program (0x02): Write up to 256 bytes
 *   - Sector Erase (0x20): Erase 4KB sector
 *   - Write Enable (0x06): Required before write/erase
 *   - Read Status (0x05): Check busy/write-enable flags
 *
 * FLASH BUFFER (0x7000-0x7FFF):
 *   4KB buffer for data transfer between CPU and flash.
 *
 * USAGE:
 *   flash_read(0x1000, 16);           // Read 16 bytes from 0x1000
 *   uint8_t b = flash_get_buffer_byte(0);  // Get first byte
 *
 *   flash_write_enable();
 *   flash_set_buffer_byte(0, 0xAB);
 *   flash_write_page(0x2000, 1);      // Write 1 byte to 0x2000
 */
#ifndef _FLASH_H_
#define _FLASH_H_

#include "../types.h"

/* Flash math utilities */
uint8_t flash_div8(uint8_t dividend, uint8_t divisor);      /* 0x0c0f-0x0c1c */
uint8_t flash_mod8(uint8_t dividend, uint8_t divisor);      /* 0x0c0f-0x0c1c */

/* Flash memory operations */
void flash_add_to_xdata16(__xdata uint8_t *ptr, uint16_t val);  /* 0x0c64-0x0c79 */
void flash_write_word(__xdata uint8_t *ptr, uint16_t val);      /* 0x0c7a-0x0c86 */
void flash_write_idata_word(__idata uint8_t *ptr, uint16_t val);/* 0x0c87-0x0c8e */
void flash_write_r1_xdata_word(uint8_t r1_addr, uint16_t val);  /* 0x0c8f-0x0c98 */

/* Flash status and control */
void flash_poll_busy(void);                     /* 0xbe70-0xbe76 */
uint8_t flash_set_cmd(uint8_t cmd);             /* 0xb845-0xb84f */
void flash_set_mode_enable(void);               /* 0xb8ae-0xb8b8 */
void flash_set_mode_bit4(void);                 /* 0xb85b-0xb864 */
void flash_start_transaction(void);             /* 0xbe6a-0xbe76 */
void flash_clear_mode_bits(void);               /* 0xbe77-0xbe81 */
void flash_clear_mode_bits_6_7(void);           /* 0xbe82-0xbe8a */

/* Flash address setup */
void flash_set_addr_md(__xdata uint8_t *addr_ptr);  /* 0xb865-0xb872 */
void flash_set_addr_hi(__xdata uint8_t *addr_ptr);  /* 0xb873-0xb880 */
void flash_set_data_len(__xdata uint8_t *len_ptr);  /* 0xb888-0xb894 */

/* Flash transactions */
void flash_run_transaction(uint8_t cmd);        /* 0xbe36-0xbe8a */
uint8_t flash_wait_and_poll(void);              /* 0xb1a4-0xb1ca */
void flash_read_status(void);                   /* 0xe3f9-0xe418 */
uint8_t flash_read_buffer_and_status(void);     /* 0xb895-0xb8a1 */

/* Flash buffer access */
uint8_t flash_get_buffer_byte(uint16_t offset); /* inline */
void flash_set_buffer_byte(uint16_t offset, uint8_t val);  /* inline */

/* Flash write operations */
void flash_write_enable(void);                  /* 0xb8a2-0xb8ad */
void flash_write_page(uint32_t addr, uint8_t len);  /* TBD */
void flash_read(uint32_t addr, uint8_t len);    /* TBD */
void flash_erase_sector(uint32_t addr);         /* TBD */

/* Flash dispatch stubs */
void flash_dispatch_stub_873a(void);            /* 0x873a-0x8742 */
void flash_dispatch_stub_8743(void);            /* 0x8743-0x874b */
void flash_dispatch_stub_874c(void);            /* 0x874c-0x8754 */
void flash_dispatch_stub_8d6e(void);            /* 0x8d6e-0x8d76 */

/* Flash handlers */
void flash_command_handler(void);               /* 0xb8b9-0xbe35 */
void system_init_from_flash(void);              /* 0x0100-0x01ff */

#endif /* _FLASH_H_ */
