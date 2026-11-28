"""Boot-sablon kimérése a valódi ZX81 ROM-ból.

A PIOCO kazetta-építő (t81_build.py) ennek a telepedett boot-állapotnak a
bájtjait használja fel a kép fej- és képernyőrészéhez (0x4009..0x42C2,
698 bájt). A fogási pont a rendszer első telepedett állapota: E_LINE=0x42C1,
D_FILE=0x407D, VARS=0x42C0, STKBOT=0x42C3 — ez az az állapot, amiben egy
valódi ZX81 a LOAD ""-t várja.

Determinisztikus: nincs billentyű-bemenet, a z80-emulátor ugyanarra az
állapotra fut (ellenőrizve: két futtatás bájtponosan azonos, ~3,24M tick).

A ROM bináris (szerzői jogvédett) NEM kerül a repóba; helye /tmp/zx81.rom
vagy a parancssori argumentum.

Futtató:
    python3 sablon_keszit.py [/ut/vonal/zx81.rom]
Eredmény:
    ../kazetta/boot_sablon.bin
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tesztek"))

from zx81sim import ZX81Sim   # noqa: E402

E_LINE = 0x42C1
D_FILE = 0x407D
VARS = 0x42C0
STKBOT = 0x42C3


def rom_helye():
    if len(sys.argv) > 1 and os.path.exists(sys.argv[1]):
        return sys.argv[1]
    for hely in ("/tmp/zx81.rom", os.path.join(os.path.dirname(__file__), "zx81.rom")):
        if os.path.exists(hely):
            return hely
    return None


def varj_magra(sim):
    """Futtatja a bootot, amíg a telepedett editor-állapot meg nem jelenik."""
    while True:
        sim.m.ticks_to_stop = 200
        sim.m.run()
        sim._advance()
        mem = sim.m.memory
        w = lambda a: mem[a] | (mem[a + 1] << 8)
        if (w(0x4014) == E_LINE and w(0x400C) == D_FILE and
                w(0x4010) == VARS and w(0x401A) == STKBOT):
            return


def main():
    hely = rom_helye()
    if hely is None:
        print("SKIP: nincs ZX81 ROM")
        return 1

    sim = ZX81Sim(hely)
    sim.m.pc = 0x0000
    varj_magra(sim)
    sablon = bytes(sim.m.memory[0x4009:0x42C3])

    ketto = ZX81Sim(hely)
    ketto.m.pc = 0x0000
    varj_magra(ketto)
    assert bytes(ketto.m.memory[0x4009:0x42C3]) == sablon, \
        "a boot-sablon nem determinisztikus"

    kit = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "kazetta",
                       "boot_sablon.bin")
    with open(kit, "wb") as f:
        f.write(sablon)
    print(f"OK: {os.path.abspath(kit)}: {len(sablon)} bajt (0x4009..0x42C2)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
