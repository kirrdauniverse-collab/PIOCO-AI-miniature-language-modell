# -*- coding: utf-8 -*-
"""CRC-16/CCITT-FALSE (polinom 0x1021, kezdőérték 0xFFFF) — a PIOCO blokkformátumhoz.
Az implementáció öntesztje a szabványos ellenőrző-vektort használja:
a "123456789" bájtlista CRC-je 0x29B1 (közzétett standard vektor).
"""

def crc16(data, crc=0xFFFF):
    for b in data:
        crc ^= b << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ 0x1021) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return crc

def crc16_file(path):
    with open(path, "rb") as f:
        return crc16(f.read())

def _selftest():
    v = crc16(b"123456789")
    assert v == 0x29B1, f"CRC önteszt HIBA: {hex(v)} (0x29B1 várt)"
    assert crc16(b"") == 0xFFFF, "üres bemenet → kezdőérték"
    assert crc16(b"A", 0xFFFF) == crc16(b"A"), "alapértelmezett init"
    print("CRC-16 önteszt OK (123456789 -> 0x%04X)" % v)

if __name__ == "__main__":
    _selftest()
