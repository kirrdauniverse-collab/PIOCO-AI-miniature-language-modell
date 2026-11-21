"""PIOCO.T81 összeállító — a 2. fázisban leírt blokkformátummal.

Használat:
  python3 t81_build.py <motor.bin> <szotar.bin> <alapmag.bin> <out.T81> [<csomag.bin> <nev> [<eml.bin> [<tadat.bin>]]]

Blokk: ['P','I'][típus][címL][címH][méretL][mérH][XOR][adat...]
Típusok: 01=BOOT, 02=MOTOR, 03=SZÓTÁR, 04=ALAPMAG, 05=TÉMACSOMAG, 06=EMLÉKEZET, 07=TADAT

Védőellenőrzések építéskor (ugyanaz, amit a motor betöltéskor is csinál):
  - egyetlen blokk sem célozhatja a PROFIL zónát (0x4100-0x41FF),
  - egyetlen blokk sem lóghat ki a 16 KB-os RAM-határon,
  - a BOOT képernyő-szövegei 0x76 / 0xC0+ kódoktól mentes lesz.
"""
import sys

MAGIC = b"PI"
TIPUSOK = {"BOOT": 1, "MOTOR": 2, "SZOTAR": 3, "ALAPMAG": 4, "CSOMAG": 5, "EMLEKEZET": 6,
           "TADAT": 7}
CELOK = {"BOOT": 0x4600, "MOTOR": 0x4600, "SZOTAR": 0x5600, "ALAPMAG": 0x6C00,
         "CSOMAG": 0x7800, "EMLEKEZET": 0x6700, "TADAT": 0x6B00}
PROFIL_ZONA = (0x4100, 0x41FF)
RAM_MAX = 0x7FFF


def kepernyo_biztos(adat):
    out = bytearray()
    for b in adat:
        if b == 0x76 or b >= 0xC0:
            out.append(0x1B)          # biztonságos cserekarakter
        else:
            out.append(b)
    return bytes(out)


def block(tipus, adat, kepernyo=False):
    if kepernyo:
        adat = kepernyo_biztos(adat)
    cel = CELOK[tipus]
    veg = cel + len(adat) - 1
    if veg > RAM_MAX:
        raise SystemExit(f"TÚLCÍMZÉS: {tipus} blokk {veg:#06x}-nál érne véget")
    (p0, p1) = PROFIL_ZONA
    if cel <= p1 and veg >= p0:
        raise SystemExit(f"PROFIL-VÉDELEM: {tipus} blokk a védett zónába írna!")
    xor = 0
    for b in adat:
        xor ^= b
    return (MAGIC + bytes([TIPUSOK[tipus], cel & 0xFF, cel >> 8,
                           len(adat) & 0xFF, len(adat) >> 8, xor]) + adat)


def read(path):
    with open(path, "rb") as f:
        return f.read()


def build(out_path, motor, szotar, alapmag, csomag=None, csomagnev=b"", eml=None, tadat=None):
    parts = []
    boot = (b"PIOCO AI BOOT\x00"
            b"BETOLTES: MOTOR+SZOTAR+ALAPMAG\x00"
            b"PROFIL MEGVEDVE.\x00")
    parts.append(block("BOOT", boot, kepernyo=True))
    parts.append(block("MOTOR", motor))
    if tadat:
        if len(tadat) > 256:
            raise SystemExit("TADAT tul nagy: %d B (max 256)" % len(tadat))
        parts.append(block("TADAT", tadat))
    parts.append(block("SZOTAR", szotar))
    parts.append(block("ALAPMAG", alapmag))
    if csomag:
        head = csomagnev[:16].ljust(16, b"\x00")
        parts.append(block("CSOMAG", head + csomag))
    if eml:
        parts.append(block("EMLEKEZET", eml))
    kazo = bytearray()
    for i, p in enumerate(parts, start=1):
        kazo.extend(bytes([0x02, 0x80, i]))   # pilóta-jeles sorszám
        kazo.extend(p)
    with open(out_path, "wb") as f:
        f.write(bytes(kazo))
    print(f"kazetta: {out_path}, {len(kazo)} bájt, {len(parts)} blokk")


if __name__ == "__main__":
    motor = read(sys.argv[1])
    szotar = read(sys.argv[2])
    alapmag = read(sys.argv[3])
    out = sys.argv[4]
    csomag = read(sys.argv[5]) if len(sys.argv) > 5 else None
    cnev = sys.argv[6].encode() if len(sys.argv) > 6 else b""
    eml = read(sys.argv[7]) if len(sys.argv) > 7 else None
    tadat = read(sys.argv[8]) if len(sys.argv) > 8 else None
    build(out, motor, szotar, alapmag, csomag, cnev, eml, tadat)
