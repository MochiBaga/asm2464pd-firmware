/*
 * uart.h - UART driver declarations
 */
#ifndef _UART_H_
#define _UART_H_

#include "../types.h"

/* UART output functions */
void uart_putc(uint8_t ch);
void uart_newline(void);
void uart_puthex(uint8_t val);
void uart_putdigit(uint8_t digit);
void uart_puts(__code const char *str);

/* Debug output */
void debug_output_handler(void);

/* Low-level UART functions */
uint8_t uart_read_byte_dace(void);
uint8_t uart_write_byte_daeb(uint8_t b);
uint8_t uart_write_daff(void);
void uart_wait_tx_ready(void);

/* Delay */
void delay_function(void);

#endif /* _UART_H_ */
