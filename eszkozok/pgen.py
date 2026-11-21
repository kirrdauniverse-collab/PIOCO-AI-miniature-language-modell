# -*- coding: utf-8 -*-
"""PIOCO AI — pgen.py: REZIDENS .P terjesztési fájl (pioco-0.1.p) generálása.

A .P formátum FORRÁS-HITELESÍTVE (zx81-utils p2txt/rem2bin + a zmakebas
ZX81 mód forráskódja alapján, 2026-11-21):
  .P = [116 B (0x74) sysvars, a 0x4009-től] [program] [25×0x76 össze-
  zsugorított képernyő] [0x80 VARS-záró] — a fájl itt ér véget; a ROM
  LOAD a 0x80-nál áll le. A fejléc sysvar-címei és értékei a zmakebas
  receptjét követik (D_FILE @0x400C, DF_CC @0x400E, CDFLAG=0x40=SLOW …).

A terjesztés a klasszikus REM-terjesztés:
  1 REM <boot.bin + NOP-kitöltés>   — a gépi kód @ 0x4082 (16514)
  2 REM <motor0.bin>                } a boot RESCOPY rutinja másolja
  3 REM <szotar.bin>                } a végleges címekre (BOOTMODE=1)
  4 REM <alapmag.bin>               }
  5 REM <pack: 64×0>                }
  6 RAND USR 16514                  — szám: 0x7E + 5 B FP (dbl2spec)
A sorok formátuma: [sorszám BE:2][hossz LE:2][törzs…0x76], a hossz a
törzzsel és a záró 0x76-tal együtt.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from z80asm import assemble

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ADAT = os.path.join(BASE, "kazetta", "adat")
OUT = os.path.join(BASE, "kazetta", "pioco-0.1.p")

PROG = 0x407D          # a programterület kezdete (REM-törzs: 0x4082 = 16514)
L1_BODY = 512          # az 1. sor REM-teste (boot + NOP-kitöltés) — fix méret
REM, RAND, USR = 0xEA, 0xF9, 0xD4

def dbl2spec(num):
    """ZX81 lebegőpontos kódolás — a zmakebas dbl2spec() hű átírása
    (ZX81 módban nincs small-integer rövid út, mindig FP)."""
    exp, num = 0, float(abs(num))
    while num >= 1.0:
        num /= 2.0
        exp += 1
    while num != 0 and num < 0.5:
        num *= 2.0
        exp -= 1
    e = (128 + exp) if num != 0 else 0
    num *= 2.0
    man = 0
    for _ in range(32):
        man = (man << 1) | int(num)
        num = (num - int(num)) * 2.0
    return e, man

def line(n, body):
    assert len(body) + 1 <= 0xFFFF
    ln = len(body) + 1
    return bytes([(n >> 8) & 0xFF, n & 0xFF, ln & 0xFF, (ln >> 8) & 0xFF]) + body + b"\x76"

def main():
    boot, blab = assemble(open(os.path.join(BASE, "motor", "boot.asm"), encoding="utf-8").read())
    motor0 = open(os.path.join(ADAT, "motor0.bin"), "rb").read()
    szotar = open(os.path.join(ADAT, "szotar.bin"), "rb").read()
    alapmag = open(os.path.join(ADAT, "alapmag.bin"), "rb").read()
    pack = bytes(64)
    assert len(szotar) == 2304 and len(alapmag) == 2048, "bináris méreteltérés a boot.asm konstansaihoz"
    # Megjegyzés: a REM-testekben bármilyen bájt megengedett (a sorfeldolgozás
    # hosszvezérelt — a boot saját LD (HL),0x76 kódja is tartalmaz 0x76-ot);
    # a D_FILE-ra futás közben csak a print-tölcsör íráskódokat enged.
    for name, blob in [("szotar", szotar), ("alapmag", alapmag)]:
        n76 = blob.count(0x76)
        if n76:
            print(f"  info: {name} {n76} db 0x76 adatbájtot tartalmaz (REM-testben engedélyezett)")
    assert len(boot) <= L1_BODY, f"boot túl nagy a {L1_BODY} B-es REM-testhez"

    # --- REM-testek címei a programterületen (determinisztikus elrendezés) ---
    l1 = L1_BODY + 6                     # hdr 4 + REM token 1 + test + 0x76
    l2, l3, l4 = len(motor0) + 6, len(szotar) + 6, len(alapmag) + 6
    l5 = len(pack) + 6
    src_mot = PROG + l1 + 5
    src_szo = PROG + l1 + l2 + 5
    src_alap = PROG + l1 + l2 + l3 + 5
    src_pack = PROG + l1 + l2 + l3 + l4 + 5
    prog_len = l1 + l2 + l3 + l4 + l5 + 13   # 13. sor: hdr 4 + törzs 8 + 0x76
    d_file = PROG + prog_len

    # --- másolási sorrend statikus ellenőrzése (a boot.asm sorrendjével) ---
    # minden forrástartománynek mentesnek kell lennie a KORÁBBAK célterületeitől
    copies = [("ALAPMAG", src_alap, 0x6300, len(alapmag)),
              ("PACK", src_pack, 0x6B00, len(pack)),
              ("SZOTAR", src_szo, 0x5400, len(szotar)),
              ("MOTOR", src_mot, 0x4600, len(motor0))]
    done_dst = []
    for name, s, d, n in copies:
        for (pd, pn) in done_dst:
            assert not (s < pd + pn and pd < s + n), \
                f"{name} forrása (0x{s:04X}) átfedi egy korábbi célt (0x{pd:04X}) — sorrend hibás"
        done_dst.append((d, n))

    # --- boot patchelése: RESCOPY források, motorhossz, rezidens mód ---
    b = bytearray(boot)
    off = lambda lbl: blab[lbl] - 0x4082
    wr16 = lambda at, v: (b.__setitem__(at, v & 0xFF), b.__setitem__(at + 1, (v >> 8) & 0xFF))
    wr16(off("SRC_SZO") + 1, src_szo)      # LD HL,nn → immediate a címke+1-nél
    wr16(off("SRC_ALAP") + 1, src_alap)
    wr16(off("SRC_PACK") + 1, src_pack)
    wr16(off("SRC_MOT") + 1, src_mot)
    wr16(off("SRC_MOTN") + 1, len(motor0))
    b[off("BOOTMODE")] = 1                  # rezidens mód
    body1 = bytes(b) + b"\x00" * (L1_BODY - len(b))   # NOP-kitöltés

    # --- program összeállítása ---
    prog = line(1, bytes([REM]) + body1)
    prog += line(2, bytes([REM]) + motor0)
    prog += line(3, bytes([REM]) + szotar)
    prog += line(4, bytes([REM]) + alapmag)
    prog += line(5, bytes([REM]) + pack)
    e, man = dbl2spec(16514)
    numtok = bytes([0x7E, e, (man >> 24) & 0xFF, (man >> 16) & 0xFF, (man >> 8) & 0xFF, man & 0xFF])
    prog += line(6, bytes([RAND, USR]) + numtok)
    assert len(prog) == prog_len, f"{len(prog)} != {prog_len}"

    # --- sysvars fejléc (zmakebas recept) ---
    hd = bytearray(0x74)
    hw = lambda at, v: (hd.__setitem__(at, v & 0xFF), hd.__setitem__(at + 1, (v >> 8) & 0xFF))
    hw(3, d_file)            # D_FILE
    hw(5, d_file + 1)        # DF_CC
    hw(7, d_file + 25)       # VARS (a 25 B-es összezsugorított képernyő után)
    hw(11, d_file + 26)      # E_LINE
    hw(13, d_file + 25)      # CH_ADD
    hw(17, d_file + 26)      # STKBOT
    hw(19, d_file + 26)      # STKEND
    hw(22, 0x405D)           # MEM
    hd[25] = 2               # DF_SZ
    hw(26, 1)                # S_TOP
    hd[28] = 0xFF            # LAST_K (3 bájt: FF FF FF)
    hw(29, 0xFFFF)
    hd[31] = 55              # MARGIN
    hw(32, d_file)           # NXTLIN
    hw(39, 0x0C8D)           # T_ADDR
    hw(43, 0xFFFF)           # FRAMES
    hd[47] = 0xBC            # PR_CC
    hd[48], hd[49] = 33, 24  # S_POSN
    hd[50] = 0x40            # CDFLAG — SLOW mód

    out = bytes(hd) + prog + b"\x76" * 25 + b"\x80"
    with open(OUT, "wb") as f:
        f.write(out)

    # --- önteszt: a fájl visszapolgatása (hosszvezérelt sorbejárás) ---
    assert out[0x74 + 5:0x74 + 5 + len(boot)] == bytes(b), "REM-törzs nem a 0x4082-re esik"
    p, lineno = 0x74, []
    for _ in range(6):
        n = (out[p] << 8) | out[p + 1]
        ln = out[p + 2] | (out[p + 3] << 8)
        lineno.append(n)
        p += 4 + ln
    assert lineno == [1, 2, 3, 4, 5, 6], f"sorszámok hibásak: {lineno}"
    assert p == 0x74 + prog_len and out[p:p + 25] == b"\x76" * 25 and out[p + 25] == 0x80, \
        "a program után nem az összezsugorított képernyő + 0x80 záró áll"
    # szám-visszaolvasás: 16514 == 2^14 + 130 → standard alak 0.50396…×2^15
    assert e == 0x8F, f"exponens eltérés: {e:#04x}"
    print(f"OK: {OUT} ({len(out)} B)")
    print(f"  program {prog_len} B @0x{PROG:04X} (6 sor), D_FILE=0x{d_file:04X}, "
          f"REM-testek: motor@0x{src_mot:04X}, szótár@0x{src_szo:04X}, "
          f"alapmag@0x{src_alap:04X}, pack@0x{src_pack:04X}")
    print(f"  boot {len(boot)} B (patchelve), RAND USR 16514 = 7E {e:02X} "
          f"{(man >> 24) & 0xFF:02X} {(man >> 16) & 0xFF:02X} {(man >> 8) & 0xFF:02X} {man & 0xFF:02X}")

if __name__ == "__main__":
    main()
