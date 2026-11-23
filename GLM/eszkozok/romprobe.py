# -*- coding: utf-8 -*-
"""romprobe.py — a romsim szanitás-őrös nyomkövetése.

A SLOW/FAST belépésnél (0x0207) elindulunk, majd lépésenként futtatjuk a
CPU-t és minden lépés után ellenőrizzük a sysvar-láncot (D_FILE, DF_CC,
VARS, E_LINE a [0x4000,0x8000) tartományban; SP nem süllyed 0x7E00 alá).
Az első rendellenességnél kiíratjuk az utolsó 30 PC-t — így pontosan
látható, melyik utasítás rontja el az állapotot."""
import romsim
from romsim import ZX81, FRAME_T

zx = ZX81()
zx.hard_reset()
zx.tripwire = False
zx.watch = {}
zx.stop_at = 0x099E          # az első MAKE-ROOM (az init CLS-e nyitja a képernyőt)
try:
    zx.tick(4_000_000)
    print("HOPPÁ: nem érte el a 0x099E-et 4M T alatt?")
    raise SystemExit
except romsim.Halt:
    pass
zx.stop_at = None
c = zx.cpu
print(f"MAKE-ROOM-nál: T={c.t} HL=0x{c.HL:04X} BC=0x{c.BC:04X} DE=0x{c.DE:04X} "
      f"SP=0x{c.SP:04X} STKEND=0x{c.rd16(0x401C):04X} D_FILE=0x{c.rd16(0x400C):04X}")
for i in range(96):
    pc0, hl0, bc0, de0, sp0 = c.PC, c.HL, c.BC, c.DE, c.SP
    try:
        c.step()
    except romsim.Halt as e:
        print(f"  HIBA: {e}")
        break
    op = c.mem[pc0] if pc0 < 0x2000 else c.rd(pc0)
    print(f"{i:2d}. PC=0x{pc0:04X} op={op:02X} HL=0x{hl0:04X} DE=0x{de0:04X} "
          f"BC=0x{bc0:04X} SP=0x{sp0:04X} → PC=0x{c.PC:04X} HL=0x{c.HL:04X} "
          f"DE=0x{c.DE:04X} BC=0x{c.BC:04X}")
    if c.PC == 0x0940 or c.PC == 0x0943:
        print("  (a 0x0940-es nullázó hurok — a gyanúsított!)")
        break
