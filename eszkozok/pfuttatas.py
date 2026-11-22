# -*- coding: utf-8 -*-
"""PIOCO AI — pfuttatas.py: VIRTUÁLIS EMULÁTOR-TESZT a pioco-0.3.p fájlon.

v2 — a v1 teszt az elavult (REM-hordozós, 6 soros) felépítést nézte;
az új, C/6-javított elrendezést vizsgálja:
  1. a .P betöltése a memóriába (0x4009-től — ROM LOAD-szimuláció),
  2. sysvar-lánc és a 2 soros program szerkezetének ellenőrzése
     (1 REM <boot> 0x76-mentes testtel, 2 RAND USR 16514 a szám
     jegyeivel + 0x7E + FP bájtokkal),
  3. a RESCOPY-ba patchelt források a betöltött adatra mutatnak-e,
  4. a RUN CLS-lépésének utánzata (képernyő kifejtése a D_FILE-nál),
  5. `RAND USR 16514` végrehajtása a z80sim-ben — saját veremmel
     (SP=0x5400, ahogy a boot a valódi gépen állítja),
  6. minden zóna, PERSIST CRC-kereszteszt, D_FILE/DF_CC mutatók,
     írás-zónák + képernyőkép. Rezidens módban az IN-BYTE hívás tiltott.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from z80sim import Z80Sim
from crc16 import crc16
from z80asm import assemble
from szimfuttatas import a2z, zx_to_txt

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ADAT = os.path.join(BASE, "kazetta", "adat")
PFILE = os.path.join(BASE, "kazetta", "pioco-0.3.p")
SCREENSHOT = os.path.join(BASE, "kazetta", "kepernyokep_p.txt")

DFILE = 0x4200
PERSIST = 0x7E00   # D-3.8: a 0x7F00-ról költözött — a ROM verem/ERR_SP/NMI-mentések a RAM tetején élnek
XORKEY = 0x40      # D-3.9: a hordozó kódolt bájtjainak kulcsa (l. pgen.py)

def main():
    pf = open(PFILE, "rb").read()
    assert len(pf) > 0x74 + 100, "túl rövid a .P"

    # --- 1. ROM LOAD: a fájl a 0x4009-től visszakerül a memóriába ---
    sim = Z80Sim()
    sim.mem[0x4009:0x4009 + len(pf)] = pf
    m = sim.mem
    word = lambda a: m[a] | (m[a + 1] << 8)
    d_file, vars_, e_line = word(0x400C), word(0x4010), word(0x4014)
    end = 0x4009 + len(pf) - 1
    print(f".P betöltve: {len(pf)} B (0x4009–0x{end:04X}); D_FILE=0x{d_file:04X}, "
          f"VARS=0x{vars_:04X}, E_LINE=0x{e_line:04X}, CDFLAG=0x{m[0x403B]:02X}")
    assert vars_ == d_file + 25 and e_line == vars_ + 1, "sysvar-lánc hibás"
    assert m[vars_] == 0x80, "VARS-záró 0x80 hiányzik"
    assert m[d_file:d_file + 25] == b"\x76" * 25, "az összezsugorított képernyő hiányzik"
    assert m[0x403B] == 0x40, "CDFLAG nem SLOW"

    # --- 2. a 2 soros program szerkezete ---
    boot, blab = assemble(open(os.path.join(BASE, "motor", "boot.asm"), encoding="utf-8").read())
    motor0 = open(os.path.join(ADAT, "motor0.bin"), "rb").read()
    szotar = open(os.path.join(ADAT, "szotar.bin"), "rb").read()
    alapmag = open(os.path.join(ADAT, "alapmag.bin"), "rb").read()
    p, lines = 0x407D, []
    for _ in range(2):        # pontosan 2 sor — utána pad + adatterület jön
        n = (m[p] << 8) | m[p + 1]
        ln = m[p + 2] | (m[p + 3] << 8)
        body = bytes(m[p + 4:p + 4 + ln - 1])
        assert m[p + 4 + ln - 1] == 0x76, f"{n}. sor: nincs sorzáró 0x76"
        assert 0x76 not in body, f"{n}. sor: 0x76 a törzsben (D-3.6 megsértve)"
        lines.append((n, p + 4, ln, body))
        p += 4 + ln
    assert [n for n, _, _, _ in lines] == [1, 2], "nem a 2 elvárt sor"
    assert lines[0][3][0] == 0xEA and lines[0][1] + 1 == 0x4082, "az 1. sor nem REM @16514"
    l2 = lines[1][3]
    assert l2 == bytes([0xF9, 0xD4, 0x1D, 0x22, 0x21, 0x1D, 0x20,
                        0x7E, 0x8F, 0x01, 0x04, 0x00, 0x00]), \
        "a 2. sor nem bájtonként a zmakebas-referenciának megfelelő RAND USR 16514"
    print("program: 1 REM 0x76-mentes testtel, 2 RAND USR 16514 — "
          "a sorkar bájtonként egyezik a zmakebas referenciával")

    # --- 3. RESCOPY patchek: a források a betöltött adatra mutatnak ---
    # D-3.9: a hordozó a .P-ben XOR 0x40-kódolt bájtokként utazik — a
    # hordozó-pozíción a KÓDOLT, a végleges címeken (RESCOPY után) a NYERS
    # bájtokat várjuk.
    off = lambda lbl: blab[lbl] - 0x4082
    src_mot = word(0x4082 + off("SRC_MOT") + 1)
    src_szo = word(0x4082 + off("SRC_SZO") + 1)
    src_alap = word(0x4082 + off("SRC_ALAP") + 1)
    src_pack = word(0x4082 + off("SRC_PACK") + 1)
    enc = lambda blob: bytes(x ^ XORKEY for x in blob)
    assert bytes(m[src_mot:src_mot + len(motor0)]) == enc(motor0), "SRC_MOT nem a (kódolt) motorra mutat"
    assert bytes(m[src_szo:src_szo + len(szotar)]) == enc(szotar), "SRC_SZO nem a (kódolt) szótárra mutat"
    assert bytes(m[src_alap:src_alap + len(alapmag)]) == enc(alapmag), "SRC_ALAP nem a (kódolt) alapmagra mutat"
    assert bytes(m[src_pack:src_pack + 64]) == enc(bytes(64)), "SRC_PACK nem a (kódolt) packra mutat"
    assert word(0x4082 + off("SRC_MOTN") + 1) == len(motor0), "SRC_MOTN hossz hibás"
    assert m[0x4082 + off("BOOTMODE")] == 1, "BOOTMODE nincs rezidensre állítva"
    print(f"adatterület @0x{src_mot:04X}: motor/szótár/alapmag/pack a helyén "
          f"(XOR 0x{XORKEY:02X}-kódoltan); RESCOPY-források és BOOTMODE rendben")

    # --- 4. RUN/CLS utánzata: összezsugorított képernyő kifejtése ---
    hl = d_file
    for _ in range(25):
        for i in range(32):
            m[hl + i] = 0x00
        m[hl + 32] = 0x76
        hl += 33
    m[hl] = 0x76
    m[0x4010], m[0x4011] = (d_file + 826) & 0xFF, (d_file + 826) >> 8
    m[0x4014], m[0x4015] = (d_file + 827) & 0xFF, (d_file + 827) >> 8
    print(f"CLS-utánzat: képernyő kifejtve 0x{d_file:04X}-től (826 B)")

    # --- 5. RAND USR 16514: a valódi motor fut (saját veremmel) ---
    sim.SP = 0x5400           # a boot első utasítása ugyanezt állítja (D-3.5)
    sim.push(0)               # RET-sentinel
    sim.PC = 0x4082
    def inbyte_forbidden(sim_):
        raise RuntimeError("REZIDENS módban a motor nem olvashat szalagot (IN-BYTE hívás)!")
    sim.hooks[0x034C] = inbyte_forbidden
    steps = sim.run()
    print(f"futás: {steps} lépés, leállás oka: {sim.halted}")
    assert sim.halted and sim.halted.startswith("önugrás"), \
        f"a motor nem a várakozó ciklusban állt meg: {sim.halted}"

    # --- 6. ellenőrzések ---
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

    assert word(0x400C) == 0x4200 and word(0x400E) == 0x4201, "D_FILE/DF_CC mutatók hibásak"
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
             (0x4600, 0x53FF),           # MOTOR kód + saját verem (D-3.5)
             (0x5400, 0x5CFF), (0x6300, 0x6AFF), (0x6B00, 0x6B3F),
             (0x7E00, 0x7EFF)]           # PERSIST (D-3.8) — a 0x7F00+ a ROM-é
    bad = [a for a, _ in sim.writes if not any(lo <= a <= hi for lo, hi in zones)]
    assert not bad, f"zónaszért írás: {[hex(a) for a in bad[:8]]}"
    print(f"írások: {len(sim.writes)} db, mind az engedélyezett zónákban — szalagolvasás nem volt")

    # --- képernyőkép ---
    lines_out = ["+" + "-" * 32 + "+"]
    for row in range(24):
        base = DFILE + row * 33
        lines_out.append("|" + "".join(zx_to_txt(m[base + col]) for col in range(32)) + "|")
    lines_out.append("+" + "-" * 32 + "+")
    art = ("PIOCO AI 0.3 — a pioco-by-GLM-0.2.p virtuális emulátor-futása után\n"
           + "\n".join(lines_out) + "\n")
    with open(SCREENSHOT, "w", encoding="utf-8") as f:
        f.write(art)
    print(art)
    print(f"OK: a rezidens .P minden ellenőrzése zöld — {SCREENSHOT}")

if __name__ == "__main__":
    main()
