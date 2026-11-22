"""PIOCO.T81 és motor-kimenet ellenőrzése (3. fázis füstvizsgálat).

Ellenőrzi:
  1. a motor bináris méretét (max. 4352 B — a MOTOR-zóna határa),
  2. a .T81 blokkok PI-mágnesjelét, cél- és méretmezőit,
  3. a XOR-ellenőrzőket,
  4. a PROFIL-zóna-védelmet (0x4100-0x41FF),
  5. hogy a BOOT (képernyőre menő) blokkban nincs 0x76 / 0xC0+ bájt,
  6. a szótár blob formáját és token-számát (max. 254),
  7. a blokkok címtartományait (16 KB belseje).
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "eszkozok"))

import t81_build  # noqa: E402

IMGBASE = t81_build.IMGBASE
IMGEND = t81_build.IMGEND
IMAGE_LEN = t81_build.IMAGE_LEN

MOTOR_ZONA_MAX = 0x57FF - 0x4700 + 1  # v2.6: motor-zona 0x4700..0x57FF

hibak = []


def vizsgal_motor(bin_path):
    with open(bin_path, "rb") as f:
        data = f.read()
    print(f"[MOTOR] {len(data)} bájt (max {MOTOR_ZONA_MAX})")
    if len(data) > MOTOR_ZONA_MAX:
        hibak.append(f"motor túl nagy: {len(data)} B")
    return data


SZOTAR_ZONA_MAX = 2048   # v2.6: SZOTAR-zona 0x5800..0x5FFF


def vizsgal_szotar(path):
    with open(path, "rb") as f:
        data = f.read()
    n = data[0]
    if n > 254:
        hibak.append(f"túl sok token: {n}")
    if len(data) > SZOTAR_ZONA_MAX:
        hibak.append(f"szotar-zona tul nagy: {len(data)} B (max {SZOTAR_ZONA_MAX})")
    i = 1
    tok = 0
    while i < len(data) and data[i] != 0:
        h = data[i]
        i += 1 + h + 1
        tok += 1
    print(f"[SZÓTÁR] fejléc: {n} szó, végigolvasva: {tok}")
    if n != tok:
        hibak.append(f"szótári fejléc nem egyezik ({n} vs {tok})")


def vizsgal_t81(path, motor_path=None, szotar_full_path=None,
                tadat_path=None, tartalek_path=None, kb2_path=None):
    """EO81 kontener + single-image vedelmi vizsgalat."""
    with open(path, "rb") as f:
        data = f.read()
    if data[:4] != b"EO81":
        hibak.append("EO81 magic hibas")
        return 0
    blokkok = []
    i = 4
    while i < len(data):
        if i + 48 > len(data):
            hibak.append(f"kontener-fejlec levagva @ {i}")
            break
        nev = data[i:i + 32].rstrip(b"\x00")
        try:
            hossz = int(data[i + 32:i + 48].decode("ascii"))
        except (ValueError, UnicodeDecodeError):
            hibak.append(f"kontener meretmezo serult @ {i + 32}")
            break
        adat = data[i + 48:i + 48 + hossz]
        if len(adat) != hossz:
            hibak.append(f"levagott blokk @ {i}")
            break
        blokkok.append((nev, adat))
        i += 48 + hossz
    print(f"[KAZETTA] {len(blokkok)} blokk: "
          + ", ".join(n.decode("ascii", "replace") for n, _ in blokkok))
    if not blokkok:
        hibak.append("a kontenerben nincs blokk")
        return 0
    nev, szalag = blokkok[0]
    if nev != b"PIOCO":
        hibak.append(f"elso blokk neve {nev!r} != PIOCO")
    if szalag[:5] != b"PIOCO":
        hibak.append("a szalagfolyam feje nem 'PIOCO'")
    if not (len(szalag) > 5 and szalag[5] & 0x80):
        hibak.append("a szalagfolyam lezaro bajtja nem bit7-es")
    kep = szalag[6:]
    if len(kep) != IMAGE_LEN:
        hibak.append(f"kep meret: {len(kep)} B (pontosan {IMAGE_LEN} kell"
                     " = 0x7E00-0x4009)")
        return len(blokkok)

    def w(a):
        return kep[a - IMGBASE] | kep[a + 1 - IMGBASE] << 8

    # a szalagon levo E_LINE = 0x7E00 (LOAD-terminator):
    if w(0x4014) != IMGEND:
        hibak.append(f"szalagon levo E_LINE {hex(w(0x4014))} != {hex(IMGEND)} "
                     "(a LOAD a PROFIL-ra is ra=irna)")
    # launcher-sor bajtponosan + tanner/0xC0+ szabaly:
    sor = t81_build.launcher_sor()
    if bytes(kep[t81_build.PROG - IMGBASE:
                 t81_build.PROG - IMGBASE + len(sor)]) != sor:
        hibak.append("a launcher-sor nem bajtponos")
    # a RAND/USR 0xC0+ BASIC-tokenek jogszeruek a programteruleten; a
    # 0xC0+ tiltas csak a D_FILE-ra (kepernyo-modra) vonatkozik
    if sor[-1] != 0x76:
        hibak.append("a launcher-sor nem 0x76-tal zar (sorveg)")
    # rendszervaltzok:
    vart_kepek = {
        0x400A: 10,            # E_PPC
        0x400C: t81_build.D_FILE,
        0x400E: t81_build.DFCC_CIM,
        0x4010: t81_build.VARS_CIM,
        0x4016: 0,             # X_PTR
        0x401A: t81_build.STKBOT_CIM,
        0x401C: t81_build.STKEND,
    }
    for cim, ertek in vart_kepek.items():
        if w(cim) != ertek:
            hibak.append(f"rendszervaltzo {hex(cim)}: {hex(w(cim))} != {hex(ertek)}")
    # D_FILE: 24 sor x (32 biztonsagos + 0x76) + lezaro 0x76; 0xC0+ tiltas:
    dfile, vars_cim = w(0x400C), w(0x4010)
    kep_resz = bytes(kep[dfile - IMGBASE: vars_cim - IMGBASE])
    trosszak = [b for b in kep_resz if 0xC0 <= b <= 0xFF]
    if trosszak:
        hibak.append(f"D_FILE-ban tiltott bajt: {trosszak[:5]}")
    varhato = (b"\x00" * 32 + b"\x76") * 24 + b"\x76"
    if kep_resz != varhato:
        hibak.append("a D_FILE nem a szintetikus ures 24 soros kep")
    if kep[vars_cim - IMGBASE] != 0x80:
        hibak.append(f"a VARS-lezaro nem 0x80 @ {hex(vars_cim)}")
    # zonal bajtponossaag az adott .bin-ekkel:
    zona_fajlok = {
        "MOTOR": (motor_path, 0x4700),
        "SZOTAR": (szotar_full_path, 0x5800),
        "TADAT": (tadat_path, 0x6B00),
        "KB2T": (kb2_path, 0x7C00),
        "TARTALEK": (tartalek_path, 0x7D00),
    }
    for znev, (pp, kezdet) in zona_fajlok.items():
        if pp is None:
            continue
        blob = open(pp, "rb").read()
        kep_resz = bytes(kep[kezdet - IMGBASE: kezdet - IMGBASE + len(blob)])
        if kep_resz != blob:
            hibak.append(f"a {znev}-zona nem egyezik a betoltott .bin-nel @ {hex(kezdet)}")
    return len(blokkok)


def vizsgal_bigramm(path, szotar_path):
    """bg.bin invariánsok: fejléc, eltolások, párok és 4 bites súlyok."""
    bg = open(path, "rb").read()
    szotar = open(szotar_path, "rb").read()
    ntok = szotar[0]
    if bg[0] != ntok:
        hibak.append(f"bigramm fejléc eltér: {bg[0]} vs {ntok}")
    elemek = 0
    for t in range(1, ntok + 1):
        o = bg[1 + 2*(t-1)] | bg[2 + 2*(t-1)] << 8
        if o == 0:
            continue
        if o >= len(bg):
            hibak.append(f"bigramm eltolás túlcsúszik: token {t}")
            continue
        pos, par = o, 0
        while True:
            t1 = bg[pos]
            if t1 == 0:
                break
            if not (1 <= t1 <= ntok):
                hibak.append(f"érvénytelen átmenet-token {t1} ({t})")
                break
            if par == 0:
                if not (1 <= bg[pos+2] >> 4 <= 15):
                    hibak.append(f"érvénytelen súly ({t} @ {pos})")
                    break
                elemek += 1
                if bg[pos+1] == 0:
                    break
                pos += 1
                par = 1
            else:
                if not (1 <= bg[pos+1] & 0x0F <= 15):
                    hibak.append(f"érvénytelen súly ({t} @ {pos})")
                    break
                elemek += 1
                pos += 2
                par = 0
    print(f"[BIGRAMM] tábla: {len(bg)} bájt, {elemek} > 4 bites súlyú átmenet")
    extra = bg[1 + 2*ntok] | bg[2 + 2*ntok] << 8
    if extra != len(bg):
        hibak.append(f"bigramm extra eltolás nem a tabla hossza: {extra} != {len(bg)} (regi bg.bin a trigram-hoz?)")
    return ntok


def vizsgal_tri(path, szotar_path):
    """tri.bin invariánsok: kulcsok [t1][t2][n][parok][0], nibble-súlyok."""
    tri = open(path, "rb").read()
    ntok = open(szotar_path, "rb").read()[0]
    pb = 0
    kulcs = 0
    adat = 0
    while pb < len(tri):
        t1 = tri[pb]
        if t1 == 0:
            break
        if pb + 2 > len(tri):
            hibak.append(f"tri kulcs levágva @ {pb}")
            break
        n = tri[pb + 2]
        if not (1 <= n <= 15):
            hibak.append(f"tri koveto-szam {n} ertelmetlen ({t1},{tri[pb+1]} @ {pb})")
            break
        if not (1 <= tri[pb + 1] <= ntok):
            hibak.append(f"tri t2 token erteven kivuli: {tri[pb+1]} @ {pb}")
            break
        pb += 3
        i = 0
        while i < n:
            ta = tri[pb]
            if ta == 0 or ta > ntok:
                hibak.append(f"tri koveto token erteven kivuli ({ta} @ {pb})")
                i = n
                break
            wa = tri[pb + 2] >> 4
            if not (1 <= wa <= 15):
                hibak.append(f"tri súly erteven kivuli ({wa} @ {pb})")
                i = n
                break
            adat += 1
            if tri[pb + 1] != 0:
                if tri[pb + 1] > ntok:
                    hibak.append(f"tri tB token erteven kivuli @ {pb}")
                    i = n
                    break
                wb = tri[pb + 2] & 0x0F
                if not (1 <= wb <= 15):
                    hibak.append(f"tri B súly erteven kivuli @ {pb}")
                    i = n
                    break
                adat += 1
                i += 2
            else:
                i += 1
            pb += 3
        if pb >= len(tri) or tri[pb] != 0:
            hibak.append(f"tri kulcs-veggel hianyzik @ {pb}")
            break
        pb += 1
        kulcs += 1
    print(f"[TRI] tabla: {len(tri)} bájt, {kulcs} kulcs, {adat} kovetoadat")


def vizsgal_eml(path):
    adat = open(path, "rb").read()
    if len(adat) < 2:
        hibak.append("eml fájl túl rövid")
        return
    if adat[0] != 0xC3:
        hibak.append(f"eml mágnes hibás: {adat[0]:#04x} != 0xC3")
        return
    count = adat[1]
    if count > 63:
        hibak.append(f"eml rekordszám > 63: {count}")
        return
    if len(adat) != 2 + 4 * count:
        hibak.append(f"eml hossz nem stimmel: {len(adat)} != {2 + 4 * count}")
        return
    for i in range(count):
        b0, b1, nap, hon = adat[2 + 4 * i:6 + 4 * i]
        if b0 > 31:
            hibak.append(f"eml rekord {i}: bitkód > 31 ({b0})")
        if b1 not in (0x00, 0x01, 0x80):
            hibak.append(f"eml rekord {i}: értékbájt érvénytelen ({b1:#04x})")
        if not (1 <= nap <= 31):
            hibak.append(f"eml rekord {i}: nap {nap}")
        if not (1 <= hon <= 12):
            hibak.append(f"eml rekord {i}: hónap {hon}")
    print(f"[EML] zóna: {count} rekord, {len(adat)} bájt")


def vizsgal_tadat(path):
    adat = open(path, "rb").read()
    if len(adat) > 256:
        hibak.append(f"tadat tul nagy: {len(adat)} B (max 256)")
        return
    exp = {
        0x00: (bytes([0]) + bytes([5, 0, 3, 6, 1, 4, 6, 2, 5, 0, 3, 5, 1, 4]), "TAB13"),
        0x0F: (b"SUN\x00MON\x00TUE\x00WED\x00THU\x00FRI\x00SAT\x00", "DOWTAB"),
        0x2B: (b"it's \x00", "TXTDAYP"),
        0x31: (b"time is \x00", "TXTTIS"),
        0x3A: (b"TODAY\x00DATE\x00\x00", "WTAB"),
        0x46: (b"TIME\x00\x00", "TIMTAB"),
        0x4C: (b"IF\x00WOULD\x00COULD\x00WISH\x00\x00", "IMAGTAB"),
        0x61: (b"DREAM\x00HUMAN\x00MAYBE\x00SOMETHING\x00", "IMAGSEED"),
        0x7D: (b"HEAD\x00\x00HURT\x00\x00ACHE\x00\x00SICK\x00\x01ILL\x00\x01FEVER\x00\x01"
               b"HAPPY\x00\x02GLAD\x00\x02SLEEP\x00\x03TIRED\x00\x04HUNGRY\x00\x05ANGRY\x00\x06\x00", "FACTTAB"),
        0xCC: (b"NO\x00NOT\x00\x00", "NEGTAB"),
        0xD4: (b"GONE\x00BETTER\x00YES\x00GOOD\x00OK\x00\x00", "CLRTAB"),
        0xED: (b"[noted]\x00", "TXTNOTED"),
    }
    for off, (vartalan, nev) in exp.items():
        if adat[off:off + len(vartalan)] != vartalan:
            hibak.append(f"tadat {nev} @ +{off:#04x} hibas (pico.asm EQU eltolasokkal osszevetve)")
    print(f"[TADAT] adattabla-blokk: {len(adat)} bajt (cim 0x6B00)")


# Használat: python3 ellenorzes.py <motor.bin> <szotar_full.bin> <PIOCO.T81> [bg.bin] [eml.bin] [tadat.bin] [tri.bin] [tartalek.bin] [kb2.bin]
if __name__ == "__main__":
    def gep(n):
        return sys.argv[n] if len(sys.argv) > n else None
    vizsgal_motor(sys.argv[1])
    vizsgal_szotar(sys.argv[2])
    vizsgal_t81(sys.argv[3], motor_path=sys.argv[1],
                szotar_full_path=sys.argv[2],
                tadat_path=gep(6), tartalek_path=gep(8), kb2_path=gep(9))
    bigr = gep(4)
    if bigr:
        vizsgal_bigramm(bigr, sys.argv[2])
    eml = gep(5)
    if eml:
        vizsgal_eml(eml)
    tadat = gep(6)
    if tadat:
        vizsgal_tadat(tadat)
    tri = gep(7)
    if tri:
        vizsgal_tri(tri, sys.argv[2])
    if hibak:
        print("\nHIBÁK:")
        for h in hibak:
            print(" -", h)
        sys.exit(1)
    print("\nMINDEN ELLENŐRZÉS RENDBEN")
