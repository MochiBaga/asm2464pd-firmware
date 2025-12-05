We are reimplementing the firmware of the ASM2464PD chip in C in the src directory. The official firmware is in fw.bin.

We are trying to match each function in the original firmware to ours, giving good names to the functions and registers and structuring the src directory well.

Our firmware should build and the output should match fw.bin as close as possible. The firmware we build should run on the device.

You can use radare on the fw.bin files to get the 8051 assembly.

registers.h is some reverse engineer registers. They may be wrong.

ghidra.c is ghidra's attempt at C disassembly of the functions, you are welcome to reference it. Note: all the names in there may be wrong.

usb-to-pcie-re is an attempt to reverse engineer this chip.

usb.py is tinygrad's library that talks to this chip.