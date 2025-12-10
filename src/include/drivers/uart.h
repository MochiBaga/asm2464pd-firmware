/*
 * uart.h - UART Debug Interface Driver
 *
 * The UART subsystem provides serial debug output for firmware
 * development and diagnostics. It uses a dedicated UART controller
 * (NOT standard 8051 SBUF) for character-based output.
 *
 * HARDWARE CONFIGURATION:
 *   - Baud rate: 921600 fixed
 *   - Data format: 8N1 (8 data bits, no parity, 1 stop bit)
 *   - Mode: TX-only debug output (no RX handling)
 *   - TX pin: B21, RX pin: A21
 *   - 16-byte transmit FIFO
 *
 * REGISTER MAP (0xC000-0xC00F):
 *   0xC001: THR (WO) - Transmit Holding Register
 *           RBR (RO) - Receive Buffer Register
 *   0xC006: TFBF    - Transmit FIFO Buffer Full
 *   0xC009: LSR     - Line Status Register
 *
 * OUTPUT FUNCTIONS:
 *   uart_putc()     - Single character output
 *   uart_puthex()   - Byte as 2-digit hex (e.g., "A5")
 *   uart_puts()     - Null-terminated string from CODE memory
 *   uart_newline()  - CR+LF sequence
 *
 * DEBUG OUTPUT FORMAT:
 *   Debug messages are typically formatted as:
 *   [SUBSYSTEM] message: value
 *
 *   Example: "[PCIE] Link speed: 03"
 *
 * USAGE:
 *   uart_puts("Status: ");
 *   uart_puthex(status_byte);
 *   uart_newline();
 *
 * NOTE: UART output is synchronous and will block until
 * the transmit buffer is ready. Use sparingly in
 * performance-critical code paths.
 */
#ifndef _UART_H_
#define _UART_H_

#include "../types.h"

/* UART output functions */
void uart_putc(uint8_t ch);                     /* 0x5398-0x53a0 (inline) */
void uart_newline(void);                        /* 0xaf5e-0xaf66 (Bank 1) */
void uart_puthex(uint8_t val);                  /* 0x51c7-0x51e5 */
void uart_putdigit(uint8_t digit);              /* 0x51e6-0x51ee */
void uart_puts(__code const char *str);         /* 0x538d-0x53a6 */

/* Debug output */
void debug_output_handler(void);                /* 0xaf5e-0xb030 (Bank 1) */

/* Low-level UART functions */
uint8_t uart_read_byte_dace(void);              /* 0xdace-0xdaea */
uint8_t uart_write_byte_daeb(uint8_t b);        /* 0xdaeb-0xdafe */
uint8_t uart_write_daff(void);                  /* 0xdaff-0xdb0f */
void uart_wait_tx_ready(void);                  /* 0xdb10-0xdb1a */

/* Delay */
void delay_function(void);                      /* 0xe529-0xe52e (Bank 1) */

#endif /* _UART_H_ */
