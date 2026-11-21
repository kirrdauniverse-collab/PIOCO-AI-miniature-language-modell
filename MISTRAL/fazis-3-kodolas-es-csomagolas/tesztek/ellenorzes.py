"""PIOCO.T81 és motor-kimenet ellenőrzése (3. fázis füstvizsgálat).

Ellenőrzi:
  1. a motor bináris méretét (max. 4096 B — a MOTOR-zóna határa),
  2. a .T81 blokkok PI-mágnesjelét, cél- és méretmezőit,
  3. a XOR-ellenőrzőket,
  4. a PROFIL-zóna-védelmet (0x4100-0x41FF),
  5. hogy a BOOT (képernyőre menő) blokkban nincs 0x76 / 0xC0+ bájt,
  6. a szótár blob formáját és token-számát (max. 254),
  7. a blokkok címtartományait (16 KB belseje).
"""
import sys

MOTOR_ZONA_MAX = 0x55FF - 0x4600 + 1
PROFIL_ZONA = (0x4100, 0x41FF)
TIPUSOK = {1: "BOOT", 2: "MOTOR", 3: "SZOTAR", 4: "ALAPMAG", 5: "CSOMAG", 6: "EMLEKEZET"}

hibak = []


def vizsgal_motor(bin_path):
    with open(bin_path, "rb") as f:
        data = f.read()
    print(f"[MOTOR] {len(data)} bájt (max 4096)")
    if len(data) > MOTOR_ZONA_MAX:
        hibak.append(f"motor túl nagy: {len(data)} B")
    return data


def vizsgal_szotar(path):
    with open(path, "rb") as f:
        data = f.read()
    n = data[0]
    if n > 254:
        hibak.append(f"túl sok token: {n}")
    i = 1
    tok = 0
    while i < len(data) and data[i] != 0:
        h = data[i]
        i += 1 + h + 1
        tok += 1
    print(f"[SZÓTÁR] fejléc: {n} szó, végigolvasva: {tok}")
    if n != tok:
        hibak.append(f"szótári fejléc nem egyezik ({n} vs {tok})")


def vizsgal_t81(path):
    with open(path, "rb") as f:
        data = f.read()
    i = 0
    n_blokk = 0
    while i < len(data):
        if data[i] != 0x02 or data[i + 1] != 0x80:
            hibak.append(f"pilóta-jeles fejléc sérült @ {i}")
            break
        idx = data[i + 2]
        i += 3
        if data[i:i + 2] != b"PI":
            hibak.append(f"nincs PI-mágnesjel @ {i}")
            break
        tipus = data[i + 2]
        cel = data[i + 3] | data[i + 4] << 8
        hossz = data[i + 5] | data[i + 6] << 8
        xor = data[i + 7]
        adat = data[i + 8:i + 8 + hossz]
        if len(adat) < hossz:
            hibak.append(f"levágott blokk @ {i}")
            break
        x = 0
        for b in adat:
            x ^= b
        if x != xor:
            hibak.append(f"XOR-hiba: {TIPUSOK.get(tipus)}")
        p0, p1 = PROFIL_ZONA
        if cel <= p1 and cel + hossz - 1 >= p0:
            hibak.append(f"PROFIL-sértés: {TIPUSOK.get(tipus)} @ {cel:#06x}")
        if cel + hossz - 1 > 0x7FFF:
            hibak.append(f"RAM-túlcímzés: {TIPUSOK.get(tipus)}")
        if tipus == 1:
            rossz = [b for b in adat if b == 0x76 or b >= 0xC0]
            if rossz:
                hibak.append(f"BOOT-blokkban 0x76/0xC0+ bájt: {len(rossz)} db")
        print(f"[BLOKK {idx}] {TIPUSOK.get(tipus, tipus)} cél={cel:#06x} "
              f"hossz={hossz} XOR-{'OK' if x == xor else 'HIBA'}")
        i += 8 + hossz
        n_blokk += 1
    print(f"[KAZETTA] {n_blokk} blokk")
    return n_blokk


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


if __name__ == "__main__":
    vizsgal_motor(sys.argv[1])
    vizsgal_szotar(sys.argv[2])
    vizsgal_t81(sys.argv[3])
    bigr = sys.argv[4] if len(sys.argv) > 4 else None
    if bigr:
        vizsgal_bigramm(bigr, sys.argv[2])
    eml = sys.argv[5] if len(sys.argv) > 5 else None
    if eml:
        vizsgal_eml(eml)
    if hibak:
        print("\nHIBÁK:")
        for h in hibak:
            print(" -", h)
        sys.exit(1)
    print("\nMINDEN ELLENŐRZÉS RENDBEN")
