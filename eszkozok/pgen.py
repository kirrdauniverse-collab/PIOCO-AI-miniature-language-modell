# -*- coding: utf-8 -*-
"""PIOCO AI — pgen.py: REZIDENS .P terjesztési fájl (pioco-0.5.p) generálása.

v2 — a C/6-os hibajelentés (valódi emulátorból) utáni áttervezés:
  - a `RAND USR 16514` sor számformátuma a zmakebas forrása szerint készül:
    a szám JEGYEI karakterként a sorban + 0x7E jelölő + 5 B lebegőpontos
    érték (dbl2spec) — a jegyek hiánya tette a ROM kiértékelője számára
    hibás kifejezéssé a sort (C/6 a 6. sornál);
  - az adatok (motor, szótár, alapmag, pack) NEM REM-sorokban, hanem a
    program UTÁNI adatterületen utaznak (az összezsugorított képernyő
    előtt) — bármilyen bájtot tartalmazhatnak (a régi ROM REM-korlátja,
    a beágyazott 0x76, ezért nem érinti őket) — D-3.6;
  - a boot maga marad az 1. sor REM-testében: 0x76-mentes kód
    (a képernyő 0x76-os bájtjait a boot aritmetikailag állítja elő).

A .P formátum (forrás-hitelesítve a zx81-utils p2txt/rem2bin és a
zmakebas ZX81 mód forrásakódjából):
  .P = [116 B (0x74) sysvars a 0x4009-től][program][adatterület]
       [25×0x76 összezsugorított képernyő][0x80 VARS-záró]
Sorformátum: [sorszám BE:2][hossz LE:2][törzs…0x76] (a hossz a 0x76-tal).
A repóbeli kimenet neve pioco-0.5.p; a felhasználónak átadott
másolat a pioco-by-GLM-0.3.p nevet viseli (névkonvenció, 2026-11-21).
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from z80asm import assemble

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ADAT = os.path.join(BASE, "kazetta", "adat")
OUT = os.path.join(BASE, "kazetta", "pioco-0.5.p")
# D-3.9: a hordozó XOR-kulcsa a motor/boot.asm-ből olvasva (egyetlen forrás —
# a BLKCPY kódja és ez a generátor nem csúszhat szét). A 0x80 a .P formátumban
# a VARS-záró bájt, ezért a fájltest egyetlen 0x80-at sem tartalmazhat; a
# kulcs előképe (0x80^XORKEY) nem fordulhat elő a nyers hordozóban (kapu).
import re as _re
BOOT_ASM = os.path.join(BASE, "motor", "boot.asm")
_m = _re.search(r"^XORKEY\s+EQU\s+(0x[0-9A-Fa-f]+)",
                open(BOOT_ASM, encoding="utf-8").read(), _re.M)
assert _m, "boot.asm: 'XORKEY EQU 0x..' sor hiányzik"
XORKEY = int(_m.group(1), 16)

PROG = 0x407D          # programterület kezdete (REM-törzs: 0x4082 = 16514)
REM, RAND, USR, NUMMARK = 0xEA, 0xF9, 0xD4, 0x7E

def dbl2spec(num):
    """ZX81 lebegőpontos kódolás — a zmakebas dbl2spec() hű átírása,
    a 33. bitre való kerekítéssel és a jelbit nullázásával (utóbbi
    kritikus: beágyazott számban a mantissza felső bitje jelbit, és ha
    1 marad, a ROM negatív számként értelmezi — ez okozta a C/6-ot)."""
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
    if int(num) and man != 0xFFFFFFFF:        # kerekítés a 33. bitre
        man = (man + 1) & 0xFFFFFFFF
    man &= 0x7FFFFFFF                          # jelbit törlése
    return e, man

def line(n, body):
    ln = len(body) + 1
    return bytes([(n >> 8) & 0xFF, n & 0xFF, ln & 0xFF, (ln >> 8) & 0xFF]) + body + b"\x76"

def main():
    boot, blab = assemble(open(os.path.join(BASE, "motor", "boot.asm"), encoding="utf-8").read())
    motor0 = open(os.path.join(ADAT, "motor0.bin"), "rb").read()
    szotar = open(os.path.join(ADAT, "szotar.bin"), "rb").read()
    alapmag = open(os.path.join(ADAT, "alapmag.bin"), "rb").read()
    pack = bytes(64)
    assert len(szotar) == 2304 and len(alapmag) == 2048, "bináris méreteltérés"
    assert 0x76 not in boot, "boot.bin nem 0x76-mentes (epites.py is ellenőrzi)"

    # --- 2. sor törzse: RAND USR 16514 (jegyek karakterként + 0x7E + FP) ---
    digits = bytes([0x1C + int(c) for c in "16514"])       # ZX81 számjegykódok
    e, man = dbl2spec(16514)
    numtok = bytes([NUMMARK, e, (man >> 24) & 0xFF, (man >> 16) & 0xFF,
                    (man >> 8) & 0xFF, man & 0xFF])
    l2body = bytes([RAND, USR]) + digits + numtok
    assert 0x76 not in l2body and e == 0x8F, "hibás számkódolás a 2. sorban"

    # --- patchek: RESCOPY források + motorhossz + rezidens mód ---
    # pad-ciklus: ha valamelyő immediate-érték 0x76-os bájtba esne, 1 bájtos
    # csúsztatással arrébb toljuk az adatterület kezdetét a program után
    off = lambda lbl: blab[lbl] - 0x4082
    for k in range(0, 256):
        b = bytearray(boot)
        wr16 = lambda at, v: (b.__setitem__(at, v & 0xFF), b.__setitem__(at + 1, (v >> 8) & 0xFF))
        ds = PROG + len(boot) + 6 + 18 + k          # program (2 sor) után
        wr16(off("SRC_ALAP") + 1, ds + len(motor0) + len(szotar))
        wr16(off("SRC_PACK") + 1, ds + len(motor0) + len(szotar) + len(alapmag))
        wr16(off("SRC_SZO") + 1, ds + len(motor0))
        wr16(off("SRC_MOT") + 1, ds)
        wr16(off("SRC_MOTN") + 1, len(motor0))
        b[off("BOOTMODE")] = 1                      # rezidens mód
        if 0x76 not in b:
            break
    else:
        raise AssertionError("az adatkezdő-cím 0x76-mentesítése 256 lépésben sem sikerült")
    data_start, d_file = ds, ds + len(motor0) + len(szotar) + len(alapmag) + len(pack)
    raw = motor0 + szotar + alapmag + pack
    if (0x80 ^ XORKEY) in raw:
        valid = [K for K in range(1, 256) if (0x80 ^ K) not in raw]
        raise AssertionError(
            f"D-3.9: a boot.asm XORKEY (0x{XORKEY:02X}) előképe előfordul a nyers "
            f"hordozóban — a motor/boot.asm 'XORKEY EQU' sorát írd át; érvényes "
            f"kulcsok most pl.: {[hex(k) for k in valid[:8]]}")
    data = bytes(x ^ XORKEY for x in raw)   # 0x80-mentes hordozó a fájlban
    prog = line(1, bytes([REM]) + bytes(b)) + line(2, l2body)
    prog_len = len(prog)
    assert prog_len == len(boot) + 6 + 18, "programhossz-eltérés"

    # --- sysvars fejléc (zmakebas recept) ---
    hd = bytearray(0x74)
    hw = lambda at, v: (hd.__setitem__(at, v & 0xFF), hd.__setitem__(at + 1, (v >> 8) & 0xFF))
    hw(3, d_file)            # D_FILE — az adatterület után
    hw(5, d_file + 1)        # DF_CC
    hw(7, d_file + 25)       # VARS (az összezsugorított képernyő után)
    hw(11, d_file + 26)      # E_LINE
    hw(13, d_file + 25)      # CH_ADD
    hw(17, d_file + 26)      # STKBOT
    hw(19, d_file + 26)      # STKEND
    hw(22, 0x405D)           # MEM
    hd[25] = 2               # DF_SZ
    hw(26, 1)                # S_TOP
    hd[28] = 0xFF            # LAST_K (3 bájt)
    hw(29, 0xFFFF)
    hd[31] = 55              # MARGIN
    hw(32, data_start)       # NXTLIN — a program utáni első bájt
    hw(39, 0x0C8D)           # T_ADDR
    hw(43, 0xFFFF)           # FRAMES
    hd[47] = 0xBC            # PR_CC
    hd[48], hd[49] = 33, 24  # S_POSN
    hd[50] = 0x40            # CDFLAG — SLOW mód

    out = bytes(hd) + prog + bytes(k) + data + b"\x76" * 25 + b"\x80"
    with open(OUT, "wb") as f:
        f.write(out)

    # --- önteszt: a fájl visszapolgatása ---
    assert out[0x74 + 5:0x74 + 5 + len(b)] == bytes(b), "REM-törzs nem a 0x4082-re esik"
    p, lineno = 0x74, []
    for _ in range(2):
        n = (out[p] << 8) | out[p + 1]
        ln = out[p + 2] | (out[p + 3] << 8)
        body = out[p + 4:p + 4 + ln - 1]
        assert out[p + 4 + ln - 1] == 0x76 and 0x76 not in body, f"{n}. sor: 0x76 a törzsben"
        lineno.append(n)
        p += 4 + ln
    assert lineno == [1, 2], f"sorszámok hibásak: {lineno}"
    assert p == 0x74 + prog_len and out[p:p + k] == bytes(k), "pad eltérés"
    # a fájlban az adat ténylegesen a kiszámított címeken áll-e?
    foff = lambda addr: addr - 0x4009            # fájl-offset = cím − 0x4009
    for name, src, blob in [("motor", data_start, motor0), ("szótár", data_start + len(motor0), szotar),
                            ("alapmag", data_start + len(motor0) + len(szotar), alapmag),
                            ("pack", data_start + len(motor0) + len(szotar) + len(alapmag), pack)]:
        assert out[foff(src):foff(src) + len(blob)] == bytes(x ^ XORKEY for x in blob), \
            f"{name}: a kódolt adat nem a kiszámított címen"
    assert bytes(x ^ XORKEY for x in out[foff(data_start):foff(data_start) + len(raw)]) == raw, \
        "D-3.9: a hordozó vissza-XOR-olása nem a nyers adatot adja"
    assert out[-26:] == b"\x76" * 25 + b"\x80", "záró (képernyő + 0x80) eltérés"
    # D-3.9 KAPU: a .P fájltestben pontosan egy 0x80 van — a legvégén (VARS-záró).
    # (A .P formátumspecifikáció a fájlt az első 0x80-nál zárja le: ha a testben
    # 0x80 ülne, a spec-hű betöltők csonkolnák a fájlt — pontosan a C/F080 hiba.)
    assert out.count(0x80) == 1 and out[-1] == 0x80, \
        "D-3.9 KAPU: 0x80 bájt a fájltestben!"
    print(f"OK: {OUT} ({len(out)} B)")
    print(f"  program {prog_len} B @0x{PROG:04X} (1 REM {len(b)} B + 2 RAND USR 16514), "
          f"pad {k} B, adat {len(data)} B @0x{data_start:04X}, D_FILE=0x{d_file:04X}")
    print(f"  REM-törzs 0x76-mentes; hordozó XOR 0x{XORKEY:02X}-kódolva; "
          f"0x80-szám: {out.count(0x80)} (a záró); a 2. sor száma: "
          f"{' '.join(f'{x:02X}' for x in digits + numtok)}")

if __name__ == "__main__":
    main()
