# -*- coding: utf-8 -*-
"""PIOCO AI — pfuttatas.py: VIRTUÁLIS EMULÁTOR-TESZT a pioco-0.1.p fájlon.

Úgy futtatja a .P-t, ahogy egy valódi ZX81-emulátor tenné:
  1. a fájl betöltése a memóriába (0x4009-től — ROM LOAD),
  2. a betöltött sysvar-állapot ellenőrzése (D_FILE, VARS, E_LINE …),
  3. a RUN CLS-lépésének utánzása: az összezsugorított 25×0x76 képernyő
     kifejtése teljes 826 B-os formára a D_FILE címen (a ROM ezt teszi),
  4. a 6. sor (RAND USR 16514) végrehajtása a z80sim-ben — innentől a
     valódi boot.bin/motor0.bin fut: RESCOPY → SCRFILL → splash → MWAIT,
  5. minden zóna, a PERSIST CRC-kereszteszt, a D_FILE sysvar-mutatók és
     az írás-zónák ellenőrzése + képernyőkép.

A rezidens módban a szalagolvasás (ROM IN-BYTE 0x034C) TILOS — ha a
motor mégis hívná, a teszt azonnal hibát dob.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from z80sim import Z80Sim
from crc16 import crc16
from z80asm import assemble
from szimfuttatas import a2z, zx_to_txt

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PFILE = os.path.join(BASE, "kazetta", "pioco-0.1.p")
SCREENSHOT = os.path.join(BASE, "kazetta", "kepernyokep_p.txt")

DFILE = 0x4200
PERSIST = 0x7F00

def main():
    pf = open(PFILE, "rb").read()
    assert len(pf) > 0x74 + 100, "túl rövid a .P"

    # --- 1. ROM LOAD: a fájl a 0x4009-től visszakerül a memóriába ---
    sim = Z80Sim()
    sim.mem[0x4009:0x4009 + len(pf)] = pf
    m = sim.mem
    d_file = m[0x400C] | (m[0x400D] << 8)
    vars_ = m[0x4010] | (m[0x4011] << 8)
    e_line = m[0x4014] | (m[0x4015] << 8)
    end = 0x4009 + len(pf) - 1
    print(f".P betöltve: {len(pf)} B (0x4009–0x{end:04X}); "
          f"D_FILE=0x{d_file:04X}, VARS=0x{vars_:04X}, E_LINE=0x{e_line:04X}, CDFLAG=0x{m[0x403B]:02X}")
    assert d_file + 25 == vars_ and vars_ + 1 == e_line, "sysvar-lánc hibás"
    assert m[vars_] == 0x80, "VARS-záró 0x80 hiányzik"
    assert d_file == 0x4009 + 0x74 + (d_file - 0x407D) and m[0x403B] == 0x40, "fejléc-ellentmondás"

    # --- 2. REM-terjesztés szerkezete: hol van a gépi kód? ---
    boot, blab = assemble(open(os.path.join(BASE, "motor", "boot.asm"), encoding="utf-8").read())
    p = 0x407D
    lines = {}
    for _ in range(6):
        n = (m[p] << 8) | m[p + 1]
        ln = m[p + 2] | (m[p + 3] << 8)
        lines[n] = (p + 4, ln)          # (törzs_kezdet, hossz a 0x76-tal)
        p += 4 + ln
    assert p == d_file, "a 6. sor után nem a képernyő jön"
    assert m[lines[1][0]] == 0xEA and lines[1][0] + 1 == 0x4082, "az 1. sor nem REM @16514"
    src_mot, src_szo = lines[2][0] + 1, lines[3][0] + 1
    src_alap, src_pack = lines[4][0] + 1, lines[5][0] + 1
    assert m[lines[6][0]] == 0xF9 and m[lines[6][0] + 1] == 0xD4, "a 6. sor nem RAND USR"
    # a RESCOPY-ba patchelt források a tényleges REM-testekre mutatnak-e?
    off = lambda lbl: blab[lbl] - 0x4082
    rd16 = lambda at: m[0x4082 + at] | (m[0x4082 + at + 1] << 8)
    assert rd16(off("SRC_SZO") + 1) == src_szo, "SRC_SZO patchelés hibás"
    assert rd16(off("SRC_ALAP") + 1) == src_alap, "SRC_ALAP patchelés hibás"
    assert rd16(off("SRC_PACK") + 1) == src_pack, "SRC_PACK patchelés hibás"
    assert rd16(off("SRC_MOT") + 1) == src_mot, "SRC_MOT patchelés hibás"
    assert m[0x4082 + off("BOOTMODE")] == 1, "BOOTMODE nincs rezidensre állítva"
    print(f"REM-testek: motor@0x{src_mot:04X}, szótár@0x{src_szo:04X}, "
          f"alapmag@0x{src_alap:04X}, pack@0x{src_pack:04X} — a patchek egyeznek")

    # --- 3. RUN/CLS utánzása: összezsugorított képernyő kifejtése ---
    hl = d_file
    for _ in range(25):
        for i in range(32):
            m[hl + i] = 0x00
        m[hl + 32] = 0x76
        hl += 33
    m[hl] = 0x76
    # a ROM a felsőbb sysvarokat eltolja (VARS/E_LINE a kifejtett képernyő után)
    m[0x4010], m[0x4011] = (d_file + 826) & 0xFF, (d_file + 826) >> 8
    m[0x4014], m[0x4015] = (d_file + 827) & 0xFF, (d_file + 827) >> 8
    print(f"CLS-utánzat: képernyő kifejtve 0x{d_file:04X}-től (826 B)")

    # --- 4. RAND USR 16514: a valódi motor fut ---
    sim.SP = 0xFFFE
    sim.push(0)              # RET-sentinel
    sim.PC = 0x4082
    def inbyte_forbidden(sim_):
        raise RuntimeError("REZIDENS módban a motor nem olvashat szalagot (IN-BYTE hívás)!")
    sim.hooks[0x034C] = inbyte_forbidden
    steps = sim.run()
    print(f"futás: {steps} lépés, leállás oka: {sim.halted}")
    assert sim.halted and sim.halted.startswith("önugrás"), \
        f"a motor nem a várakozó ciklusban állt meg: {sim.halted}"

    # --- 5. ellenőrzések ---
    motor0 = open(os.path.join(BASE, "kazetta", "adat", "motor0.bin"), "rb").read()
    szotar = open(os.path.join(BASE, "kazetta", "adat", "szotar.bin"), "rb").read()
    alapmag = open(os.path.join(BASE, "kazetta", "adat", "alapmag.bin"), "rb").read()
    assert bytes(m[0x4600:0x4600 + len(motor0)]) == motor0, "MOTOR nem a helyén (RESCOPY?)"
    assert bytes(m[0x5400:0x5400 + len(szotar)]) == szotar, "SZÓTÁR nem a helyén"
    assert bytes(m[0x6300:0x6300 + len(alapmag)]) == alapmag, "ALAPMAG nem a helyén"
    assert bytes(m[0x6B00:0x6B40]) == bytes(64), "PACK zóna nem nullás"
    print("RESCOPY: MOTOR/SZÓTÁR/ALAPMAG/PACK bájt-hűen a végleges címeken")

    assert m[PERSIST] == 0x50 and m[PERSIST + 1] == 0x43 and m[PERSIST + 2] == 0x01
    assert all(x == 0 for x in m[PERSIST + 3:PERSIST + 0xFC]), "PERSIST nullázatlan terület"
    z80_crc = m[PERSIST + 0xFC] | (m[PERSIST + 0xFD] << 8)
    py_crc = crc16(bytes(m[PERSIST:PERSIST + 0xFC]))
    assert z80_crc == py_crc, f"CRC eltérés: Z80=0x{z80_crc:04X} Python=0x{py_crc:04X}"
    print(f"PERSIST: mágia PC, verzió 1; CRC-16 kereszteszt OK (0x{py_crc:04X})")

    assert (m[0x400C] | (m[0x400D] << 8)) == 0x4200, "D_FILE sysvar nem 0x4200"
    assert (m[0x400E] | (m[0x400F] << 8)) == 0x4201, "DF_CC sysvar nem 0x4201"
    print("D_FILE/DF_CC sysvar-mutatók a saját képernyőre állnak (0x4200/0x4201)")

    for row in range(25):
        base = DFILE + row * 33
        assert m[base + 32] == 0x76, f"{row}. sor: nincs sorzáró 0x76"
        for col in range(32):
            b = m[base + col]
            assert b <= 0x3F or 0x80 <= b <= 0xBF, f"tiltott kód a D_FILE-ban: {b:#04X} ({row},{col})"
    assert m[DFILE + 825] == 0x76, "hiányzik a záró stop-bájt"
    def expect_at(row, col, text):
        base = DFILE + row * 33 + col
        got = [m[base + i] for i in range(len(text))]
        want = [a2z(c) for c in text]
        assert got == want, f"splash eltérés ({row},{col}): {got} != {want}"
    expect_at(2, 5, "PIOCO AI")
    expect_at(7, 9, "16K  PIOCO  0.1")
    print("D_FILE: 25 sor + záró stop-bájt; splash-ok a helyükön")

    zones = [(0x400C, 0x400F), (0x4082, 0x41FF), (0x4200, 0x4539),
             (0x4600, 0x4600 + len(motor0) - 1),
             (0x5400, 0x5CFF), (0x6300, 0x6AFF), (0x6B00, 0x6B3F),
             (0x7F00, 0x7FFF), (0xFF00, 0xFFFF)]
    bad = [a for a, _ in sim.writes if not any(lo <= a <= hi for lo, hi in zones)]
    assert not bad, f"zónaszért írás: {[hex(a) for a in bad[:8]]}"
    print(f"írások: {len(sim.writes)} db, mind az engedélyezett zónákban — szalagolvasás nem volt")

    # --- képernyőkép ---
    lines_out = ["+" + "-" * 32 + "+"]
    for row in range(24):
        base = DFILE + row * 33
        lines_out.append("|" + "".join(zx_to_txt(m[base + col]) for col in range(32)) + "|")
    lines_out.append("+" + "-" * 32 + "+")
    art = ("PIOCO AI 0.1 — a pioco-0.1.p virtuális emulátor-futása után\n"
           + "\n".join(lines_out) + "\n")
    with open(SCREENSHOT, "w", encoding="utf-8") as f:
        f.write(art)
    print(art)
    print(f"OK: a rezidens .P minden ellenőrzése zöld — {SCREENSHOT}")

if __name__ == "__main__":
    main()
