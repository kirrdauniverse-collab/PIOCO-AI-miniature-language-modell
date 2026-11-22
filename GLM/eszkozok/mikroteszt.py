# -*- coding: utf-8 -*-
"""Mikrotesztek a romvizsgálathoz: (1) LD (HL) RAM-írás, (2) (IY+d) írás,
(3) a 0x0A6B-0x0A76 ROM-bájtok (mi ugrik 0xFFFF-re)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from romsim import ZX81, FRAME_T   # noqa: E402

zx = ZX81()

# (1) LD (HL),n RAM-írás: kód a 0x5000-ba, PC=0x5000
zx.cpu.mem[0x5000:0x5006] = bytes.fromhex("2107402E42 76".replace(" ", ""))
zx.cpu.PC = 0x5000
zx.tick(200)
print("(1) LD (HL),0x42 @0x4007 → mem[0x4007] =", hex(zx.cpu.mem[0x4007]))

# (2) (IY+d) írás: LD IY,0x4000 / LD (IY+7),0x42 / HALT
zx2 = ZX81()
zx2.cpu.mem[0x5000:0x5009] = bytes.fromhex("FD210040FD3607 42 76".replace(" ", ""))
zx2.cpu.PC = 0x5000
zx2.tick(200)
print("(2) LD (IY+7),0x42 → mem[0x4007] =", hex(zx2.cpu.mem[0x4007]))

# (3) ROM-bájtok a CLS utáni zónában
zx3 = ZX81()
print("(3) ROM 0x0A6B-0x0A75:", zx3.cpu.mem[0x0A6B:0x0A76].hex(" "))
print("    ROM 0x0A6F-0x0A75:", zx3.cpu.mem[0x0A6F:0x0A76].hex(" "))
