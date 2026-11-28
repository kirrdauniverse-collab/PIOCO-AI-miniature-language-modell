"""Diagnosztika: motor-boot derail keresése single-step trace-vel.

Betölti a PIOCO.T81-et a valódi ROM-mal (mint kazetta_teszt), aztán
PC=0x4700-tól single-step lépked, és az első PC<0x2000 (ROM) pillanatnál
kiírja az utolsó ~64 motorbeli PC/SP-ért a derail előtti állapotot.
"""
import os
import sys
from collections import deque

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "eszkozok"))

from zx81sim import ZX81Sim, stream_to_ear, set_tape  # noqa: E402
import t81_build  # noqa: E402

MOTORBASE = 0x4700
SZALAG_ELINE = 0x7E00
MOTOR = open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "..", "kazetta", "motor.bin"), "rb").read()
MOTOREND = MOTORBASE + len(MOTOR)

KAZ = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "..", "kazetta", "PIOCO.T81")


import kazetta_teszt  # noqa: E402


def betolt(kaz_path, rom_path):
    blocks = kazetta_teszt.kontener_kiszed(kaz_path)
    szalag = blocks[0][1]
    kep = szalag[6:]
    sim = ZX81Sim(rom_path)
    kazetta_teszt.varj_loadhatara(sim)
    kazetta_teszt.rom_load(sim, szalag, kep)
    print(f"LOAD ok ({len(kep)} B), tick = {sim.ticks}")
    return sim


def szimprint(sim, pc):
    m = sim.m
    return (f"pc={pc:04X} sp={m.sp:04X} bc={m.bc:04X} de={m.de:04X} "
            f"hl={m.hl:04X} a={m.a:02X} ix={m.ix:04X} iy={m.iy:04X} "
            f"h-med={sim.word(0x400C):04X}")


def main():
    rom = sys.argv[1] if len(sys.argv) > 1 else "/tmp/zx81.rom"
    sim = betolt(KAZ, rom)
    mem = sim.m.memory

    sim.m.sp = 0x7FFF
    sim.m.pc = MOTORBASE

    nyom = deque(maxlen=64)
    teljes = 0
    elso_rom = None
    LEPES = 400_000
    while teljes < LEPES:
        sim.m.ticks_to_stop = 4
        sim.m.run()
        pc = sim.m.pc
        teljes += 1
        if pc < 0x2000:
            elso_rom = pc
            break
        nyom.append((pc, sim.m.sp))
        if sp := sim.m.sp:
            if sp < 0x7C00:
                print(f"SP kornyek veves: {hex(sp)} @ {hex(pc)}")
                break

    print(f"lepesek: {teljes}")
    if elso_rom is None or elso_rom >= 0x2000:
        print("nem talaltunk ROM-derail-t a kereten belul")
        print("utolso 12 lepes:")
        for pc, sp in list(nyom)[-12:]:
            print(f"  {szimprint(sim, pc)}")
        print("motor vege:", hex(MOTOREND))
        return

    print(f"ELSO ROM-PC: {elso_rom:04X}")
    print("utolso ~64 lepes (pc, sp):")
    for pc, sp in nyom:
        print(f"  pc={pc:04X} sp={sp:04X}")
    print("motor hatar:", hex(MOTORBASE), "-", hex(MOTOREND))


if __name__ == "__main__":
    main()
