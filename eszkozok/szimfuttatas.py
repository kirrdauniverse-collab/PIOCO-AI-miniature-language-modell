# -*- coding: utf-8 -*-
"""PIOCO AI — szimfuttatas.py: a motor VÉGPONT-TESZTJE a z80sim szimulátoron.

A valódi binárisok futnak (boot.bin @ 0x4082, ahogy a ROM LOAD betöltené),
a pioco-0.1.tape blokkjait pedig a ROM IN-BYTE (0x034C) szerepét játszó
hook táplálja bájtonként. A .tape első blokkja (PIOCOBOOT, típus 1) kimarad:
a valóságban azt a ROM LOAD már betöltötte, mielőtt a gépi kód elindult.

Ellenőrzések:
  1. a futás eljut a MWAIT önugrásig (nem fagy le, nem téved el),
  2. a szalag pontosan elfogy (mind a 4 blokk beolvasásra került),
  3. a betöltött zónák bájtjukra egyeznek a PC-side binárisokkal,
  4. PERSIST: mágia + verzió + nullák + CRC-16 — a Z80-ban számolt CRC
     keresztesztje a Python crc16-tel (a motor saját CRC rutinának bizonyítéka),
  5. D_FILE: 24 sor × (32 engedélyezett kód + 0x76), a splash a helyén,
  6. minden írás az engedélyezett zónákba történt (zónaszért írás = hiba).

Kimenet: kazetta/kepernyokep_szimulacio.txt — a D_FILE dekódolt képe.
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from z80sim import Z80Sim
from crc16 import crc16
from csomaggen import parse_and_verify

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ADAT = os.path.join(BASE, "kazetta", "adat")
TAPE = os.path.join(BASE, "kazetta", "pioco-0.1.tape")
SCREENSHOT = os.path.join(BASE, "kazetta", "kepernyokep_szimulacio.txt")

DFILE = 0x4200
PERSIST = 0x7E00   # D-3.8: a 0x7F00-ról költözött — a ROM verem/ERR_SP/NMI-mentések a RAM tetején élnek

# ASCII → ZX81 (forrás: Wikipedia „ZX81 character set”, l. motor0.asm ASCTBL)
PUNCT = {'"': 0x0B, '$': 0x0D, ':': 0x0E, '?': 0x0F, '(': 0x10, ')': 0x11,
         '>': 0x12, '<': 0x13, '=': 0x14, '+': 0x15, '-': 0x16, '*': 0x17,
         '/': 0x18, ';': 0x19, ',': 0x1A, '.': 0x1B}

def a2z(c):
    if c == ' ':
        return 0x00
    if c.isdigit():
        return 0x1C + int(c)
    if 'A' <= c <= 'Z':
        return ord(c) - 0x1B
    return PUNCT.get(c, 0x00)

ZX2TXT = {}
for _c in ' 0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ" $:?<>=+-*/;,.':
    if _c != ' ':
        ZX2TXT.setdefault(a2z(_c), _c)
ZX2TXT[0x00] = ' '

def zx_to_txt(b):
    b &= 0x3F  # inverz videó (0x80-0xBF) ugyanaz a glif
    return ZX2TXT.get(b, '#')

def main():
    boot = open(os.path.join(ADAT, "boot.bin"), "rb").read()
    motor0 = open(os.path.join(ADAT, "motor0.bin"), "rb").read()
    szotar = open(os.path.join(ADAT, "szotar.bin"), "rb").read()
    alapmag = open(os.path.join(ADAT, "alapmag.bin"), "rb").read()
    tape = open(TAPE, "rb").read()

    blocks = parse_and_verify(tape)
    assert blocks[0][0] == 1, "az első blokk legyen a BOOT (típus 1)"
    # --- D-4.1 ELAVULÁSI KAPU: a szalag motor-blokkja az AKTUÁLIS
    #     motor0.bin legyen (a boot méretváltozása átmozgatja a LOADBLK-t,
    #     a régi szalagon pedig a stage-2 CALL-ja 3 bájttal beljebb esik a
    #     rutinba → fejléc-elcsúszás → a szótár a motor-kódra íródik) ---
    i, mot_payload = 0, None
    while i < len(tape):
        ttype, n = tape[i], tape[i + 2] | (tape[i + 3] << 8)
        if ttype == 2:
            mot_payload = tape[i + 4:i + 4 + n]
            break
        i += 6 + n
    assert mot_payload == motor0, ("szalag elavult: a motor-blokk nem az "
        "aktuális motor0.bin — futtass csomaggen-t a szimfuttatas ELŐTT!")
    stream = bytearray()
    for (ttype, ver, n, crc, _) in blocks[1:]:
        # payload: fejléc (4) + adat (n) + CRC (2)
        stream += tape_chunk(tape, ttype, n)
    print(f"szalag: {len(blocks)} blokk, a betöltőnek táplálva: {len(stream)} B "
          f"(PIOCOBOOT kimaradt — azt a ROM LOAD hozná be)")

    pos = [0]
    def inbyte(sim):
        if pos[0] >= len(stream):
            raise RuntimeError("szalag-kimerülés: a motor több bájtot olvasna, mint amennyi van")
        sim.C = stream[pos[0]]
        pos[0] += 1

    sim = Z80Sim()
    sim.mem[0x4082:0x4082 + len(boot)] = boot
    sim.SP = 0x7FFE           # D-4.1: a ROM veremén futunk (nincs SP-váltás)
    sim.push(0)               # RET-sentinel
    sim.PC = 0x4082
    sim.hooks[0x034C] = inbyte
    steps = sim.run()
    print(f"futás: {steps} lépés, leállás oka: {sim.halted}")

    # --- 1. a futás a MWAIT várakozó ciklusban áll meg ---
    assert sim.halted and sim.halted.startswith("önugrás"), \
        f"a motor nem a várakozó ciklusban állt meg: {sim.halted}"

    # --- 2. a szalag pontosan elfogyott ---
    assert pos[0] == len(stream), f"szalag-maradvány: {len(stream) - pos[0]} B olvasatlan"

    # --- 3. betöltött zónák bájt-hűsége ---
    assert bytes(sim.mem[0x4600:0x4600 + len(motor0)]) == motor0, "MOTOR zóna eltér"
    assert bytes(sim.mem[0x5400:0x5400 + len(szotar)]) == szotar, "SZÓTÁR zóna eltér"
    assert bytes(sim.mem[0x6300:0x6300 + len(alapmag)]) == alapmag, "ALAPMAG zóna eltér"
    assert bytes(sim.mem[0x6B00:0x6B40]) == bytes(64), "PACK zóna nem nullás"
    print("zónák: MOTOR/SZÓTÁR/ALAPMAG/PACK bájt-hűen betöltve a szalagról")

    # --- 4. PERSIST + CRC kereszteszt (Z80 rutin vs Python) ---
    m = sim.mem
    assert m[PERSIST] == 0x50 and m[PERSIST + 1] == 0x43 and m[PERSIST + 2] == 0x01, \
        "PERSIST mágia/verzió hibás"
    assert all(b == 0 for b in m[PERSIST + 3:PERSIST + 0xFC]), "PERSIST nullázatlan terület"
    z80_crc = m[PERSIST + 0xFC] | (m[PERSIST + 0xFD] << 8)
    py_crc = crc16(bytes(m[PERSIST:PERSIST + 0xFC]))
    assert z80_crc == py_crc, f"CRC eltérés: Z80=0x{z80_crc:04X} Python=0x{py_crc:04X}"
    print(f"PERSIST: mágia PC, verzió 1, nullák rendben; CRC-16 kereszteszt OK (0x{py_crc:04X})")

    # --- 5. D_FILE szerkezet + splash (ROM-standard 25 sor + záró 0x76) ---
    for row in range(25):
        base = DFILE + row * 33
        assert m[base + 32] == 0x76, f"{row}. sor: nincs sorzáró 0x76"
        for col in range(32):
            b = m[base + col]
            assert b <= 0x3F or 0x80 <= b <= 0xBF, f"tiltott kód a D_FILE-ban: {b:#04X} ({row},{col})"
    assert m[DFILE + 25 * 33] == 0x76, "hiányzik a záró stop-bájt a 25. sor után"
    def expect_at(row, col, text):
        base = DFILE + row * 33 + col
        got = [m[base + i] for i in range(len(text))]
        want = [a2z(c) for c in text]
        assert got == want, f"splash eltérés ({row},{col}): {got} != {want}"
    expect_at(2, 5, "PIOCO AI")
    expect_at(7, 9, "16K  PIOCO  0.6")
    print("D_FILE: 25 sor (24 tartalmi + 1 alsó), soronként 32 engedélyezett kód + 0x76, záró stop-bájt; splash-ok a helyükön")

    # --- 6. írás-zóna-ellenőrzés ---
    zones = [(0x400C, 0x400F), (0x4082, 0x41FF), (0x4200, 0x4539),
             (0x4600, 0x53FF),           # MOTOR kód
             (0x5400, 0x5CFF), (0x6300, 0x6AFF), (0x6B00, 0x6B3F),
             (0x7E00, 0x7EFF),           # PERSIST (D-3.8)
             (0x7F00, 0x7FFF)]           # a ROM vereme — a boot CALL-keretei (D-4.1)
    bad = [a for a, _ in sim.writes if not any(lo <= a <= hi for lo, hi in zones)]
    assert not bad, f"zónaszért írás: {[hex(a) for a in bad[:8]]}"
    nw = len(sim.writes)
    print(f"írások: {nw} db, mind az engedélyezett zónákban (boot-adat, D_FILE, "
          f"betöltött zónák, verem)")

    # --- képernyőkép ---
    lines = ["+" + "-" * 32 + "+"]
    for row in range(24):
        base = DFILE + row * 33
        lines.append("|" + "".join(zx_to_txt(m[base + col]) for col in range(32)) + "|")
    lines.append("+" + "-" * 32 + "+")
    art = "PIOCO AI 0.6 — D_FILE a Z80-szimulációs végpont-teszt után\n" + "\n".join(lines) + "\n"
    with open(SCREENSHOT, "w", encoding="utf-8") as f:
        f.write(art)
    print(art)
    print(f"OK: minden ellenőrzés zöld — {SCREENSHOT}")

def tape_chunk(tape, ttype, n):
    """Adott típusú blokk teljes payload-ja (fejléc+adat+CRC) a .tape-ből."""
    i = 0
    while i < len(tape):
        lo, hi = tape[i + 2], tape[i + 3]
        ln = lo | (hi << 8)
        if tape[i] == ttype:
            return tape[i:i + 6 + ln]
        i += 6 + ln
    raise KeyError(ttype)

if __name__ == "__main__":
    main()
