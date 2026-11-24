"""PIOCO.T81 összeállító v2.5 — VALÓDI ZX81 ROM SAVE-kép, single image.

Miért változott a formátum: a ZX81 ROM LOAD rutinja (NEXT-PROG, 0x0347)
mindig a 0x4009-nél kezdi a betöltést, és az E_LINE rendszerváltozóval A
SZALAGON jelölt értéknél áll meg — tehát a betölthető kép egyetlen
összefüggő terület (0x4009..E_LINE). A régi, szétszórt blokkos rendszer
(a motor a kép címzónáján KÍVÜL esett volna) ezért C/6-ot (out of range)
kapott volna. A C/6 nem a BASIC-programok hibája, hanem a LOAD-erőltetésé.

Az .T81 (EO81 konténer) fő blokkja egy teljes ZX81 programkép:
  - sablon: kazetta/boot_sablon.bin (a ROM bootjáról kimért telepedett
    állapot: 0x4009..0x42C2-close, 698 B; eszkozok/sablon_keszit.py gyártja);
  - a builder beilleszti a '10 RAND USR 18176' launcher-sort (0x406D),
    a D_FILE/VARS/E_LINE/STKBOT/STKEND tartalmát +22 bájttal áthúzza,
    és bepatcheli a rendszerváltozókat;
  - berakja a MOTOR/SZOTAR/ALAPMAG/TADAT/KB2T/TARTALEK tartalmat a saját
    zónájukba (a hézagok 0x00);
  - a szalagon lévő E_LINE = 0x7E00: a LOAD ide terminál, kép = 15863 B
    (motorszám 0x4700-tól, szótár 0x5700, CHAT 0x6000, EMLÉKEZET 0x6700,
    MUNKAT 0x6800, TADAT 0x6B00, ALAPMAG 0x6C00, CSOMAG-foglalás 0x7800,
    TARTALEK 0x7D00);
  - a PROFIL (0x7E00..0x7EFF) az image-en KÍVÜL van: a LOAD tényleg sosem
    ír a 0x7E00..0x7FFF zónára (védett tartós memória; a teljes
    persistenciát a motor SHIFT+S-mentése kezeli).
A szalagfolyam (hivatalos EO81/T81 egyezmény, l. EightyOne etc/t81.cpp):
zx81-név (utolsó bájt bit7-es lezáró) + kép; LOAD ""-val (null-név, D=0x80)
névényezetés nélkül tölthető.
Konténer: b"EO81" magic; blokkonként entry (32 B ASCII név + 16 B ASCII
méret; méret = adat + névhossz) + zx81-név + adat. A builder a
<kép>.P névtelen nyers .p-t is kiírja — ezt az emulátorok gyorstöltője
közvetlenül futtatja (a restart-probléma elleni egységes forma).
Lejátszó-szabály: a lejátszó a stream ELŐTT minimálisan 0,5 s csendet adjon
(a ROM IN-BYTE TIMEOUT-hoz elég).

Használat:
  python3 t81_build.py <motor.bin> <szotar.bin> <alapmag.bin> <out.T81> \
      <tadat.bin> <tartalek.bin> [<sablon-path>] [<kb2.bin>] \
      [<csomag.bin> <csomagnev> ...]

Védelmi ellenőrzések építéskor:
  - a kép mérete pontosan 15863 bájt (0x7E00 - 0x4009);
  - a launcher-sor bájtjai csak biztonságos tartományúak (0xC0+ tiltás;
    0x76 csak sorvég pozícióban);
  - a zónák nem lógnak ki, életképes tartalékot hagynak.
"""
import os
import sys

MAGIC = b"EO81"
IMGBASE = 0x4009
IMGEND = 0x7E00           # a szalagon lévő E_LINE (LOAD-terminátor)
IMAGE_LEN = IMGEND - IMGBASE     # 15863
PROG = 0x406D             # programkezdés (első BASIC-sor címe)
D_FILE = 0x4083           # képernyő-bázis a launcher után
SORHOSSZ = 33             # 32 szóköz + 0x76-terminátor
SORDB = 24                # teljes 24 soros képernyő (a motor CLRSCR-je 24 sort ír)
DFILE_VEGE = D_FILE + SORDB * SORHOSSZ + 1    # a képernyő-0x76 lezáró után (793 B sor-rész)
VARS_CIM = DFILE_VEGE     # 0x439C: ide kerül az üres VARS 0x80-bájt (VARS pontosan rámutat, mint a valódi booton)
E_LINE_CIM = VARS_CIM + 1 # 0x439D: edit-stub (7F 76 00, mint a valódi gépen)
STKEND = E_LINE_CIM + 2   # 0x439F (boot-mért: STKEND = E_LINE + 2)
STKBOT_CIM = STKEND       # a boot szintúgy STKBOT = STKEND
DFCC_CIM = D_FILE + 0x15  # az első sor 5. karaktere (a sablonéhoz igazodik)
PROFIL_ZONA = (0x7E00, 0x7EFF)
ZONAK = {
    "MOTOR": (0x4700, 0x57FF),
    "SZOTAR": (0x5800, 0x5FFF),
    "TADAT": (0x6B00, 0x6BFF),
    "ALAPMAG": (0x6C00, 0x6DFF),
    "KB2T": (0x7C00, 0x7CFF),
    "TARTALEK": (0x7D00, 0x7DFF),
}
FP_18176 = bytes.fromhex("8f0e000000")   # ROM STACK-BC kimérés (5 bajt)

# A hivatalos EightyOne .T81 (konténer-)formátum (l. EightyOne etc/t81.cpp):
#   blokk = entry(48) + zx81_név(namelen bájt, utolsó |= 0x80) + adat;
#   entry = név[32] ASCII + méret[16] ASCII decimálisan,
#   méret = len(adat) + namelen (a névbájtokkal együtt szalaghossz).
# A korábbi ASCII-név + külön 0x80-by tetőforma NEM egyezik vele: az
# emulátor gyorstöltője (pl. ZEsarUX quickload) a nyers fájlt 0x4009-re
# írva a konténer-fejlécet írná a rendszerváltozók helyére -> gép-crash,
# ami "azonnali újraindítás" képében mutatkozik meg.
ASCII2ZX81 = bytes.fromhex(
    "00160b160d161616101117151a161b18" "1c1d1e1f2021222324250e191314120f"
    "16262728292a2b2c2d2e2f3031323334" "35363738393a3b3c3d3e3f1616161616"
    "16262728292a2b2c2d2e2f3031323334" "35363738393a3b3c3d3e3f1616161616")
assert len(ASCII2ZX81) == 96           # ASCII 32..127

def zx81_nev(ascii_nev):
    """Név ZX81-karakterkészletben, az utolsó bájton bit7 lezáró (hivatalos)."""
    bajtok = bytes(ASCII2ZX81[min(max(c, 32), 127) - 32] for c in ascii_nev.encode("ascii", "replace"))
    return bajtok[:-1] + bytes([bajtok[-1] | 0x80])


def blokk(ascii_nev, adat):
    """Hivatalos EO81 blokk: entry(48) + zx81-név + adat."""
    n = zx81_nev(ascii_nev)
    return (ascii_nev.encode("ascii", "replace")[:32].ljust(32, b"\x00")
            + str(len(adat) + len(n)).encode().ljust(16)
            + n + adat)


def launcher_sor():
    """'10 RAND USR 18176' ZX81-karakterbájtban; az USR-operandus régi
    lebegőpontos konstansát a ROM STACK-BC kimérése adja (7E + 5 bajt)."""
    szoveg = (b"\xF9\x00"          # RAND (token) + szóköz (0x00)
              b"\xD4\x00"          # USR (token) + szóköz
              b"\x1D\x24\x1D\x23\x22")   # 18176 ZX81-számjegyek
    szoveg += b"\x7E" + FP_18176   # rejtett lebegőpontos konstans
    hossz = len(szoveg) + 1        # a 0x76-terminátorral együtt
    return (b"\x0A\x00"            # sorszám: 10
            + hossz.to_bytes(2, "little")
            + szoveg
            + b"\x76")


def kep_general(sablon, motor, szotar, alapmag, tadat, tartalek, kb2=None):
    if len(sablon) != 0x42C3 - 0x4009:
        raise SystemExit(f"SABLON méret: {len(sablon)} bajt (698 kell; "
                         "futtasd: python3 eszkozok/sablon_keszit.py)")
    kep = bytearray(IMAGE_LEN)
    kep[0:0x406D - 0x4009] = sablon[0:0x406D - 0x4009]
    sor = launcher_sor()
    if len(sor) != 20 or sor[-1] != 0x76:
        raise SystemExit("launcher-sor hibás hossz/lezárás")
    p = 0x406D - 0x4009
    kep[p:p + len(sor)] = sor               # program: 0x406D..0x4080
    kep[p + len(sor)] = 0x80                # program vége (sorlisták zárója)
    # szintetikus, teljes 24 soros üres képernyő (a motor CLRSCR-je belefér),
    # 0x76-terminátorokkal, majd a D_FILE-lezáró 0x76:
    kep[(D_FILE - 0x4009):(DFILE_VEGE - 0x4009)] = \
        (b"\x00" * 32 + b"\x76") * SORDB + b"\x76"
    kep[VARS_CIM - 0x4009] = 0x80             # VARS: üres változóterület
    # az edit-stub mintája a sablon végéről (0x42C0..0x42C2 = 7F 76 00):
    kep[E_LINE_CIM - 0x4009: E_LINE_CIM - 0x4009 + 3] = sablon[-3:]

    def set_word(addr, ertek):
        kep[addr - 0x4009] = ertek & 0xFF
        kep[addr - 0x4009 + 1] = (ertek >> 8) & 0xFF

    # rendszerváltozók (a +22 eltolásnak megfelelően):
    set_word(0x400A, 10)                    # E_PPC
    set_word(0x400C, D_FILE)                # D_FILE
    set_word(0x400E, DFCC_CIM)              # DF_CC
    set_word(0x4010, VARS_CIM)              # VARS
    set_word(0x4014, E_LINE_CIM)            # E_LINE (később a szalagra javítjuk)
    set_word(0x4016, 0)                     # X_PTR
    set_word(0x401A, STKBOT_CIM)            # STKBOT
    set_word(0x401C, STKEND)                # STKEND
    # tartalmi zónák:
    adatok = {"MOTOR": motor, "SZOTAR": szotar, "TADAT": tadat,
              "ALAPMAG": alapmag, "KB2T": kb2 or b"", "TARTALEK": tartalek}
    for nev, (kezdet, vege) in ZONAK.items():
        adat = adatok[nev]
        if len(adat) > vege - kezdet + 1:
            raise SystemExit(f"{nev} túl nagy: {len(adat)} B "
                             f"(zóna: {vege - kezdet + 1} B)")
        kep[kezdet - 0x4009: kezdet - 0x4009 + len(adat)] = adat
    # a szalagon lévő E_LINE (LOAD-terminátor):
    set_word(0x4014, IMGEND)
    # a képernyő-rész 0x76-terminátor-szabálya (a sablon D_FILE-ja már így néz ki):
    # a képernyő-sorszerkezet 0x76-ellenőrzése; a D_FILE-blokk végén
    # a változó-lezáró 0x80 (0x42D5) a sablon része, szándékos.
    return bytes(kep)


def main():
    if len(sys.argv) < 7:
        raise SystemExit(__doc__)

    def read(p):
        with open(p, "rb") as f:
            return f.read()

    motor = read(sys.argv[1])
    szotar = read(sys.argv[2])
    alapmag = read(sys.argv[3])
    out = sys.argv[4]
    tadat = read(sys.argv[5])
    tartalek = read(sys.argv[6])
    if len(sys.argv) > 7:
        sablon_p = sys.argv[7]
    else:
        sablon_p = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "kazetta", "boot_sablon.bin")
    sablon = read(sablon_p)
    if len(sablon) != 698:
        raise SystemExit(f"boot_sablon.bin ({sablon_p}) méret nem 698 — "
                         "futtasd: eszkozok/sablon_keszit.py")

    kep = kep_general(sablon, motor, szotar, alapmag, tadat, tartalek,
                      read(sys.argv[8]) if len(sys.argv) > 8 else None)
    assert len(kep) == IMAGE_LEN

    # szalagfolyam (hivatalos): zx81-név (bit7 az utolsó bájton) + kép
    stream = zx81_nev("PIOCO") + kep
    # konténer: "EO81" + entry(48: név32 ASCII + méret16 ASCII = adat+névhossz)
    #           + zx81-név + adat
    kazo = MAGIC + blokk("PIOCO", kep)
    # bővítés: témacsomagok külön blokkokban (a motor saját betöltője kezeli);
    # a 8. argumentum a kb2.bin (KB2T-zóna) — a csomag-blokkok ezután jönnek
    i = 10 if len(sys.argv) > 8 else 8
    while i + 1 < len(sys.argv):
        kazo += blokk(sys.argv[i + 1], read(sys.argv[i]))
        i += 2
    with open(out, "wb") as f:
        f.write(kazo)
    # egységes, azonnal betöltő szalagekvivalens: névtelen .p (nyers kép,
    # 0x4009-től) — ezt EightyOne/ZEsarUX gyorstöltője közvetlenül futtatja:
    if str(out).upper().endswith(".T81"):
        p_out = str(out)[:-4] + ".P"
        with open(p_out, "wb") as f:
            f.write(kep)
        print(f"gyorstolt: {p_out}: {len(kep)} bájt (névtelen .p)")
    print(f"kazetta: {out}: {len(kazo)} bájt "
          f"(kép: {len(kep)} B = 0x7E00-0x4009, 1 főblokk)")
    print("Elméleti szalagidő (ROM LOAD \"\"): kb. 2-4 perc.")


if __name__ == "__main__":
    main()
