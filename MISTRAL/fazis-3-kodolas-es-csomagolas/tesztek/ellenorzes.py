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


if __name__ == "__main__":
    vizsgal_motor(sys.argv[1])
    vizsgal_szotar(sys.argv[2])
    vizsgal_t81(sys.argv[3])
    if hibak:
        print("\nHIBÁK:")
        for h in hibak:
            print(" -", h)
        sys.exit(1)
    print("\nMINDEN ELLENŐRZÉS RENDBEN")
