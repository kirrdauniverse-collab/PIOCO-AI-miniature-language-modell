"""Szalag-protokoll teszt: bajton pontos LOAD a valodi ZX81 ROM-mal.

A null-nev LOAD (LOAD "") utvonalat uzemeltetve egy 104 bajtos allapoton:
  1. elso IN-BYTE: a csend alatt TIMEOUT -> RESTART (D elfogadva)
  2. IN-NAME: D bite 7 = 1, ezert nincs nev-egyeztetes, csak a lezaro
     bit7-es bajtot keresi
  3. IN-PROG: a kepet 0x4009-tol tolti; a LOAD/SAVE (0x01FC) az
     E_LINE rendszervaltoronall all meg
  4. ellenorzes: az eredeti boot-allapot bajtponosan viszatoltodik,
     bar a teszt 0xEE-vel szemetezte a programteruletet

Futtatas:
    python3 szalag_teszt.py [/ut/vonal/zx81.rom]

A ROM binaris szerzoi jogvevedett, NEM kerul a repoba. Ha nincs meg,
a teszt SKIP-pel kilep. ROM-forras: sajat emulatorod ROM fajlja
(pl. EightyOne ROM mappaja).
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from zx81sim import ZX81Sim, stream_to_ear, set_tape   # noqa: E402

E_LINE = 0x406D        # a kep vege: ennyiig kell bejoenie a sajatoltnak
NEV = b"PIO"


def rom_helye():
    if len(sys.argv) > 1 and os.path.exists(sys.argv[1]):
        return sys.argv[1]
    for hely in ("/tmp/zx81.rom", "zx81.rom"):
        if os.path.exists(hely):
            return hely
    return None


def main():
    hely = rom_helye()
    if hely is None:
        print("SKIP: nincs ZX81 ROM (l. szalag_teszt.py fejlec)")
        return 0

    sim = ZX81Sim(hely)
    sim.boot(ticks=30_000_000)
    assert sim.word(0x4014) == 0x42C1, "boot E_LINE hibas"
    assert sim.word(0x400C) == 0x407D, "boot D_FILE hibas"
    regi = bytes(sim.m.memory[0x4009:E_LINE])

    kep = bytearray(regi)
    kep[0x4014 - 0x4009] = E_LINE & 0xFF
    kep[0x4015 - 0x4009] = E_LINE >> 8
    szalag = NEV + b"\x80" + bytes(kep)

    atmenetek = stream_to_ear(szalag)
    set_tape(sim, atmenetek)
    sim.m.memory[0x4040:E_LINE] = b"\xEE" * (E_LINE - 0x4040)
    kezd = sim.ticks

    sim.m.d = 0x80            # bit7 szet: a nev-egyeztetes kihagyasa
    sim.m.e = 0x00
    sim.m.pc = 0x0347         # NEXT-PROG: a LOAD "" ut racsatolasa

    veg = False
    while sim.ticks - kezd < 40_000_000:
        sim.m.ticks_to_stop = 200
        sim.m.run()
        sim._advance()
        sim.ear_level = sim.ear_at(sim.ticks)
        if sim.m.pc == 0x01FC and sim.m.hl >= E_LINE - 1:
            veg = True
            break

    kaptunk = bytes(sim.m.memory[0x4009:E_LINE])
    assert veg, "a LOAD nem fejezodott be a kijelolt idokeretben"
    assert kaptunk == bytes(kep), "a betoltott kep nem egyezik"
    print(f"OK: {len(kep)} bajt bajtponosan betoltve, "
          f"{(sim.ticks - kezd) / 3.25e6:.2f} vaslagmp szalagido")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
