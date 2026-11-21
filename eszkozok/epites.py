# -*- coding: utf-8 -*-
"""PIOCO AI — epites.py: a motor építése (assemble + korlát-ellenőrzés).

1. boot.asm  → boot.bin  (stage-1, ORG 0x4082) — KORLÁT: vége < 0x4200 (382 B)
2. a LOADBLK cím beinjektálása a motor0.asm-be (STG1LOAD)
3. motor0.asm → motor0.bin (stage-2, ORG 0x4600) — KORLÁT: ≤ 3584 B
Kimenet: kazetta/adat/boot.bin, kazetta/adat/motor0.bin (ezután: csomaggen.py)
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from z80asm import assemble

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ADAT = os.path.join(BASE, "kazetta", "adat")
BOOT_END = 0x4200          # a D_FILE-zóna kezdete — a stage-1 nem nőhet át
STG2 = 0x4600
STG2_MAX = 3584            # MOTOR zóna

def main():
    os.makedirs(ADAT, exist_ok=True)

    code, lab = assemble(open(os.path.join(BASE, "motor", "boot.asm"), encoding="utf-8").read())
    end = 0x4082 + len(code)
    assert end <= BOOT_END, f"stage-1 túl nagy: vége 0x{end:04X} > 0x4200"
    assert lab["BOOT"] == 0x4082 and lab["LOADBLK"] < BOOT_END
    with open(os.path.join(ADAT, "boot.bin"), "wb") as f:
        f.write(code)
    print(f"stage-1 (boot.bin):  {len(code)} B (0x4082–0x{end-1:04X}, {BOOT_END-end} B ráhagyás)")

    src = open(os.path.join(BASE, "motor", "motor0.asm"), encoding="utf-8").read()
    assert lab["BOOTMODE"] < BOOT_END, "BOOTMODE a boot-zónán kívülre esne"
    for old, new in [("STG1LOAD EQU 0x0000", f"STG1LOAD EQU 0x{lab['LOADBLK']:04X}"),
                     ("BOOTMODE EQU 0x0000", f"BOOTMODE EQU 0x{lab['BOOTMODE']:04X}")]:
        assert old in src, f"motor0.asm: hiányzik az @EPITES@ jelölő ({old})"
        src = src.replace(old, new)
    mcode, mlab = assemble(src)
    mend = STG2 + len(mcode)
    assert len(mcode) <= STG2_MAX, f"stage-2 túl nagy: {len(mcode)} B"
    assert mlab["MOT0"] == STG2
    with open(os.path.join(ADAT, "motor0.bin"), "wb") as f:
        f.write(mcode)
    print(f"stage-2 (motor0.bin): {len(mcode)} B (0x4600–0x{mend-1:04X}, {STG2_MAX-len(mcode)} B ráhagyás)")
    print(f"STG1LOAD = 0x{lab['LOADBLK']:04X}, BOOTMODE = 0x{lab['BOOTMODE']:04X} (motor0 ezeket használja)")
    print("OK: motor/ források assemble-elve — futás emulátorban a következő körben")

if __name__ == "__main__":
    main()
