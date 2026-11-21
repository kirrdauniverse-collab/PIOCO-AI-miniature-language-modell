# -*- coding: utf-8 -*-
"""PIOCO AI — csomaggen: blokkok összeállítása a fázis-2 6.2-es formátum szerint.

Blokk-payload: [típus][verzió][hossz_lo][hossz_hi] + adat + CRC-16 (fejléc+adat, little-endian).
A kiadás: kazetta/adat/<NÉV>.blk egyenként és kazetta/pioco-0.1.tape (folyamatos blokkfolyam).
MEGJEGYZÉS (őszinte státusz): a .tape a saját 6.2 blokkformátum nyers bájtja; a pulse-réteg
(pilot/sync a ZX81 ROM SAVE kódolásában) és a ROM-LOAD-kompatibilis .p/.T81 burkolás a
következő kör emulátor-ellenőrzésével készül — enélkül nem hazudunk .T81 kiterjesztést.
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from crc16 import crc16

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ADAT = os.path.join(BASE, "kazetta", "adat")
TAPE = os.path.join(BASE, "kazetta", "pioco-0.1.tape")

PROTECTED = (0x4100, 0x41FF)
TYPES = {
    1: ("PIOCOBOOT", 0x4082),
    2: ("PIOCOMOT",  0x4600),
    3: ("PIOCOSZO",  0x5400),
    4: ("PIOCOALAP", 0x6300),
    5: ("PIOCOPACK", 0x6B00),
}

def make_block(ttype, data, version=1):
    hdr = bytes([ttype, version, len(data) & 0xFF, (len(data) >> 8) & 0xFF])
    c = crc16(hdr + data)
    return hdr + data + bytes([c & 0xFF, (c >> 8) & 0xFF])

def parse_and_verify(tape):
    blocks = []
    i = 0
    while i < len(tape):
        assert i + 6 <= len(tape), "csonka fejléc"
        ttype, ver, lo, hi = tape[i], tape[i + 1], tape[i + 2], tape[i + 3]
        n = lo | (hi << 8)
        assert i + 6 + n <= len(tape), "csonka adat"
        data = tape[i + 4:i + 4 + n]
        crc = tape[i + 4 + n] | (tape[i + 5 + n] << 8)
        assert crc16(tape[i:i + 4 + n]) == crc, f"CRC hiba blokk {ttype}"
        blocks.append((ttype, ver, n, crc, data[:0]))
        i += 6 + n
    return blocks

def main():
    plan = []
    boot = os.path.join(ADAT, "boot.bin")
    if os.path.exists(boot):
        plan.append((1, open(boot, "rb").read()))
    mot = os.path.join(ADAT, "motor0.bin")
    if os.path.exists(mot):
        plan.append((2, open(mot, "rb").read()))
    plan.append((3, open(os.path.join(ADAT, "szotar.bin"), "rb").read()))
    plan.append((4, open(os.path.join(ADAT, "alapmag.bin"), "rb").read()))
    plan.append((5, bytes(64)))  # PIOCOPACK váz (üres csomagterület-váz)

    tape = bytearray()
    rows = []
    for ttype, data in plan:
        name, target = TYPES[ttype]
        if ttype in (2, 3, 4, 5):
            lo, hi = PROTECTED
            assert not (target <= hi and target + len(data) > lo), \
                f"{name}: cél a védett PERSIST tartományba esne!"
        blk = make_block(ttype, data)
        with open(os.path.join(ADAT, f"{name}.blk"), "wb") as f:
            f.write(blk)
        tape += blk
        rows.append((name, ttype, len(data), target, crc16(blk[:4 + len(data)])))

    with open(TAPE, "wb") as f:
        f.write(tape)

    # visszatöltés-teszt: a .tape-ből újraépítve minden CRC rendben?
    parsed = parse_and_verify(bytes(tape))
    print(f"{'blokk':10} {'típus':>5} {'adat':>6} {'cél':>7} {'CRC':>7}")
    for name, ttype, n, target, c in rows:
        print(f"{name:10} {ttype:>5} {n:>6} {hex(target):>7} {hex(c):>7}")
    print(f"visszatöltés-teszt: {len(parsed)} blokk, minden CRC OK")
    print(f"OK: {TAPE} ({len(tape)} B) + {len(rows)} .blk fájl")
    assert len(parsed) == len(rows)

if __name__ == "__main__":
    main()
