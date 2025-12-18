/*
 * USB Descriptors for ASM2464PD
 */
#ifndef USB_DESCRIPTORS_H
#define USB_DESCRIPTORS_H

#include "types.h"

/* USB Descriptor Types */
#define USB_DESC_TYPE_DEVICE        0x01
#define USB_DESC_TYPE_CONFIG        0x02
#define USB_DESC_TYPE_STRING        0x03
#define USB_DESC_TYPE_INTERFACE     0x04
#define USB_DESC_TYPE_ENDPOINT      0x05

/* Descriptor arrays in code ROM */
extern __code const uint8_t usb_device_descriptor[18];
extern __code const uint8_t usb_config_descriptor[32];
extern __code const uint8_t usb_string_descriptor_0[4];
extern __code const uint8_t usb_string_descriptor_1[26];
extern __code const uint8_t usb_string_descriptor_2[16];
extern __code const uint8_t usb_string_descriptor_3[20];

/*
 * Get descriptor pointer and length by type and index
 * Returns pointer to descriptor in code ROM, sets *length
 */
__code const uint8_t* usb_get_descriptor(uint8_t type, uint8_t index, uint8_t *length);

#endif /* USB_DESCRIPTORS_H */
