# -*- coding: utf-8 -*-
"""PIOCO AI — romvizsgalo: az "azonnali restart" vadászata (D-4.0).

Két átépítés:
  1. stop@0x0041: megáll az ELSŐ WAIT-INT belépésnél, és kiírja a
     bevezető utasítás-nyomot (pc_ring), a regisztereket és a
     rendszerváltozó-terület nyers dumpját.
  2. ha az első átadás nem találja (nincs 0x0041-lépés), vad-PC vadászat.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from romsim import ZX81, FRAME_T, Halt   # noqa: E402


def dump_sysvars(zx):
    b = zx.cpu.mem[0x4000:0x4026]
    print("sysvar-terület 0x4000-0x4025:", b.hex(" "))


def main():
    zx = ZX81()
    zx.stop_at = 0x0041
    try:
        zx.tick(FRAME_T * 450)
        print(f"nincs 0x0041-lépés 450 képkockán (PC=0x{zx.cpu.PC:04X})")
        print("állapot:", zx.state())
        dump_sysvars(zx)
        return
    except Halt as e:
        print(f"ELSŐ WAIT-INT belépés: {e}")
        print("PC-nyom (utolsó 40):", " ".join(f"{p:04X}" for p in zx.pc_ring[-40:]))
        c = zx.cpu
        print(f"SP=0x{c.SP:04X} IY=0x{c.IY:04X} HL=0x{c.HL:04X} "
              f"BC=0x{c.BC:04X} DE=0x{c.DE:04X} A=0x{c.A:02X} F=0x{c.F:02X}")
        print("FD-írások:", zx.fd_writes[-8:])
        print("állapot:", zx.state())
        dump_sysvars(zx)
        # a verem teteje: mit Pop-olna a handler?
        print("verem (0x7FF0-0x7FFF):", zx.cpu.mem[0x7FF0:0x7FFF].hex(" "))


if __name__ == "__main__":
    main()
