"""V2.6 beszelgetes-vegponti teszt: tenyleges gombnyomasokkal a motorral.

A kazetta_teszt betolto/boothivasaival a PIOCO.T81-et felrakja, majd a
mini-billentyuzet-matrixon keresztul VALOS karaktereket gepel be, es
ellenorzi a v2.6 nyelvi ujitasait:

  1. READLINE-javitas: a leutott karakterek tenyleg a BLINE-ba kerulnek
     (eddig ures sor maradt, a REASON/TOKENIZE sosem latott semmit);
  2. KB2-lanc: "WHO MADE" -> "Sandor Safar, with GLM's help.";
  3. hangulat: "HAHA" -> "Haha! Glad.";
  4. 'S'-to-visszavonas: "CATS" -> CAT token (egy szo-token, nem betuk);
  5. DO/DOES-intent: "DOES IT WORK" sor rendben fut keresztul (BLINE jo).

Futtatas:
    python3 beszelgetes_teszt.py [/ut/vonal/zx81.rom]

A ROM binaris szerzoi jogvedett, NEM kerul a repoba.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "eszkozok"))

import kazetta_teszt as kt                          # noqa: E402
from kazetta_teszt import (rom_helye, kontener_kiszed, varj_loadhatara,  # noqa: E402
                           rom_load, asctab_zx)

import t81_build                                    # noqa: E402

# a motor KeyT tablaajanak masa: karakter -> (port, bit)
KEYMAP = {
    "Z": (0xFE, 0x02), "X": (0xFE, 0x04), "C": (0xFE, 0x08), "V": (0xFE, 0x10),
    "A": (0xFD, 0x01), "S": (0xFD, 0x02), "D": (0xFD, 0x04), "F": (0xFD, 0x08),
    "G": (0xFD, 0x10),
    "Q": (0xFB, 0x01), "W": (0xFB, 0x02), "E": (0xFB, 0x04), "R": (0xFB, 0x08),
    "T": (0xFB, 0x10),
    "1": (0xF7, 0x01), "2": (0xF7, 0x02), "3": (0xF7, 0x04), "4": (0xF7, 0x08),
    "5": (0xF7, 0x10),
    "0": (0xEF, 0x01), "9": (0xEF, 0x02), "8": (0xEF, 0x04), "7": (0xEF, 0x08),
    "6": (0xEF, 0x10),
    "P": (0xDF, 0x01), "O": (0xDF, 0x02), "I": (0xDF, 0x04), "U": (0xDF, 0x08),
    "Y": (0xDF, 0x10),
    "L": (0xBF, 0x02), "K": (0xBF, 0x04), "J": (0xBF, 0x08), "H": (0xBF, 0x10),
    " ": (0x7F, 0x01), ".": (0x7F, 0x02), "M": (0x7F, 0x04), "N": (0x7F, 0x08),
    "B": (0x7F, 0x10),
}
ENTER = (0xBF, 0x01)

PB = 0x6800
BLINE = PB
LINELEN = PB + 0x40
TOKBUF = PB + 0x48
TOKCNT = PB + 0x88

CHUNK = 200           # a kazetta_teszt chunk-hossza


def futtat(sim, tick):
    """tick 200-os chunkban fut, EAR-beallitassal (a kazetta_teszt mintaja)."""
    veg = sim.ticks + tick
    while sim.ticks < veg:
        sim.m.ticks_to_stop = CHUNK
        sim.m.run()
        sim._advance()
        sim.ear_level = sim.ear_at(sim.ticks)


def gepel(sim, szoveg):
    """A szoveg karaktereit lenyomas/felengedes ciklussal viszi be.

    Event-driven: minden karaktert addig nyomogatunk rovid segur valid
    (pollhato) leutessel, amig a READLINE nem nyilvantartja (LINELEN
    novekszik) — igy a motor foglaltsaga (generativas) sem veszi el a
    karaktert. Lenyomas idopontja: a leutott karakter BLINE-ba irasa a
    v2.6-os READLINE-javitas kozvetlen bizonyiteka. Visszateresi ertek:
    a BLINE tartalma ENTER elott (0-lezarasig) bytes-kent.
    """
    szavak = szoveg.rstrip("\n")
    for idx, ch in enumerate(szavak):
        cukcs = KEYMAP.get(ch)
        assert cukcs is not None, f"ismeretlen karakter: {ch!r}"
        cel = idx + 1
        for kiserlet in range(20):
            sim.pressed.add(cukcs)
            futtat(sim, CHUNK * 25)
            sim.pressed.discard(cukcs)
            sim.m.ticks_to_stop = CHUNK
            kezd = sim.ticks
            while sim.ticks - kezd < 1_000_000:
                if sim.m.memory[LINELEN] == cel:
                    break
                sim.m.ticks_to_stop = CHUNK
                sim.m.run()
                sim._advance()
            else:
                sok = True
                continue
            break
        else:
            raise AssertionError(
                f"a karakter nem ert a BLINE-ba: idx={idx} ch={ch!r} "
                f"LINELEN={sim.m.memory[LINELEN]} "
                f"BLINE={bytes(sim.m.memory[BLINE:BLINE + 16]).hex(' ')} "
                f"PC={sim.m.pc:#06x}")
    elvart = szavak.encode("ascii") + b"\x00"
    kapott = bytes(sim.m.memory[BLINE:BLINE + len(elvart)])
    assert kapott == elvart, \
        f"BLINE ENTER elott: {kapott!r} (elvart: {elvart!r})"
    # ENTER-lezaras felengedessz, egy szabad READLINE-ig futtat
    sim.pressed.add(ENTER)
    futtat(sim, CHUNK * 25)
    sim.pressed.discard(ENTER)
    kezd = sim.ticks
    while sim.ticks - kezd < 60_000_000:
        if sim.m.memory[LINELEN] == 0 and sim.m.memory[BLINE] == 0:
            break
        futtat(sim, CHUNK * 25)
    else:
        raise AssertionError("a sor lezarasa utan nem all vissza READLINE")
    return kapott


def kepernyo(sim):
    """A D_FILE tartalma ASCII-vonalkent (0x76 sorvegekkel lezarva)."""
    mem = sim.m.memory
    dfile = sim.word(0x400C)
    tab = asctab_zx(_motor())
    ellen = {kod: chr(c + 32) for c, kod in enumerate(tab)}
    sorok = []
    p = dfile
    for _ in range(24):
        sor = bytearray()
        while mem[p] != 0x76:
            sor.append(mem[p])
            p += 1
        p += 1
        sorok.append("".join(ellen.get(b, "_") for b in sor))
    return "\n".join(sorok)


_MOTOR = None


def _motor():
    global _MOTOR
    if _MOTOR is None:
        p = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "..", "kazetta", "motor.bin")
        _MOTOR = open(p, "rb").read()
    return _MOTOR


def varj_szovegre(sim, resz, tickmax=30_000_000):
    """futtat, amig a kepernyon meg nem jelenik a resz szoveg."""
    kezd = sim.ticks
    while sim.ticks - kezd < tickmax:
        futtat(sim, CHUNK * 50)
        if resz in kepernyo(sim):
            return sim.ticks - kezd
    raise AssertionError(f"nem jott a kepernyore: {resz!r}\n{kepernyo(sim)}")


def main():
    hely = rom_helye()
    if hely is None:
        print("SKIP: nincs ZX81 ROM (l. kazetta_teszt.py fejlec)")
        return 0

    kaz_p = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "..", "kazetta", "PIOCO.T81")
    blokkok = kontener_kiszed(kaz_p)
    nev, szalag = blokkok[0]
    kep = szalag[6:]

    from zx81sim import ZX81Sim
    sim = ZX81Sim(hely)
    varj_loadhatara(sim)
    rom_load(sim, szalag, kep)
    kt.motor_boot(sim, _motor())          # splash + ENTER-togglo boot
    sim.pressed.clear()
    print("OK: motor felkapcsol (kazetta_teszt boothivasaval)")

    mem = sim.m.memory

    # a boot-parbeszed zárása: a DATASK ev-bekerese a sor (PROF_DDAY a
    # 0xA5-sentinel miatt nem kerul), egysegesen: "-78" evvel a beast MAINLOPba
    gepel(sim, "\n")          # ha valami WAITKEY/-maradek van, azt engedjuk at
    gepel(sim, "78\n")         # ev: a DATASK ev-kerase lezarul -> MAINLOP

    # ---- 1. WHO MADE -> KB2 azonosito ----
    # (a gepel maga is allitja: a BLINE ENTER elott "WHO MADE\0")
    sor = gepel(sim, "WHO MADE\n")
    assert sor.rstrip(b"\x00") == b"WHO MADE", f"gepel visszateres: {sor!r}"
    varj_szovegre(sim, "Sandor Safar")
    varj_szovegre(sim, "with GLM")
    print("OK: READLINE a BLINE-ba ir + WHO MADE -> Sandor Safar valasz")

    # ---- 2. HAHA -> hangulat valasz ----
    gepel(sim, "HAHA\n")
    varj_szovegre(sim, "Haha! Glad")
    print("OK: HAHA -> Haha! Glad.")

    # ---- 3. CATS -> 'S'-to-visszavonas (egy szo-token) ----
    gepel(sim, "CATS\n")
    tokn = mem[TOKCNT]
    tok0 = mem[TOKBUF]
    assert tokn == 1, f"CATS tokenek szama: {tokn} (1 kell, tove-vagassal)"
    assert tok0 < 0x80, f"CATS elso tokene betu-token (0x80+): {tok0:#x}"
    print(f"OK: CATS -> 1 szo-token (ID {tok0}), a tove-vagas mukodik")

    # ---- 4. DOES IT WORK -> DO-prefix intent, rendben lefut ----
    gepel(sim, "DOES IT WORK\n")
    varj_szovegre(sim, "YOU", tickmax=3_000_000)   # a prompt vagy valasz
    print("OK: DOES IT WORK rendben feldolgozasra kerult")

    kt.dfile_jogszeru(mem, sim.word(0x400C), sim.word(0x4010))
    print("OK: D_FILE jogszeru maradt az egesz beszelgetes alatt")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
