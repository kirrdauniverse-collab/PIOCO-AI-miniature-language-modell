"""Bigramm-tanito: korpuszbol sulyozott szo-atmeneti tablat epit (bg.bin).

Mukodes:
  1. dict.bin-bol kiolvassa a szo -> token-id hozzarendeleset,
  2. a korpuszt token-sorozatta alakitja (ismeretlen szo kihagyva),
  3. a szomszedos szavak atmeneteit megszamolja,
  4. tokenenkent csoportot epit: suly = max(1, round(15*count/osszes)),
     vagyis 4 bites kvantalas (0..15),
  5. kettesevel csomagol: [tA][tB][wAB] harmasok, ahol wAB felso nibble
     az A sulya, also nibble a B sulya (1 bajt = 2 darab 4 bites suly).
     Paratlan elemszamnal az utolso elem par-padded (tB = 0).

bg.bin formatuma:
  [ntok(1)][2 bajtos eltolas tokenenkent, a bg.bin elejehez kepest]
  [csoportok...]
  Csoport: [t1][t2][w12][t3][t4][w34]... t = 0 -> csoport vege.
  Az eltolas 0 azt jelenti: nincs atmenet errol a tokenrol.
  A motor a szotar-vegjel UTANI elso bajttal kezdodo tablat olvassa
  (BIGR cim), ezert a szotar.bin es a bg.bin egymas utan kerul a
  SZOTAR-blokdba.

Hasznalat:
  python3 bigram_train.py tudas/alapcorpus.txt kazetta/szotar.bin kazetta/bg.bin
"""
import sys
from collections import Counter


def olvas_dict(path):
    data = open(path, "rb").read()
    n = data[0]
    szavak = {}
    i = 1
    while i < len(data) and data[i] != 0:
        h = data[i]
        szo = data[i + 1:i + 1 + h].decode("ascii")
        szavak[szo] = data[i + 1 + h]
        i += h + 2
    return n, szavak


ECHARS = str.maketrans({
    "á": "a", "é": "e", "í": "i", "ó": "o", "ö": "o", "ő": "o",
    "ú": "u", "ü": "u", "ű": "u",
})


def normal(word):
    return word.lower().translate(ECHARS).strip(".,!:;?()\"'")


def main():
    corpus_path, dict_path, out_path = sys.argv[1], sys.argv[2], sys.argv[3]
    n, szavak = olvas_dict(dict_path)

    sorok = []
    for line in open(corpus_path, encoding="utf-8"):
        ids = []
        for w in line.split():
            w = normal(w)
            tid = szavak.get(w)
            if tid:
                ids.append(tid)
        if len(ids) >= 2:
            sorok.append(ids)

    # atmenetek megszamolasa
    szamlalo = {}
    for ids in sorok:
        for a, b in zip(ids, ids[1:]):
            szamlalo.setdefault(a, Counter())[b] += 1

    # csoportok: 4 bites kvantalt sulyok, gyakorisag szerint rendezve
    csoportok = {}
    for a, szaml in szamlalo.items():
        ossz = sum(szaml.values())
        lista = sorted(szaml.items(), key=lambda kv: (-kv[1], -kv[0]))
        elems = []
        for b, darab in lista:
            w = max(1, round(15 * darab / ossz))
            elems.append((b, w))
        csoportok[a] = elems

    ntok = n
    fejl = bytearray()
    fejl.append(ntok & 0xFF)
    fejl.extend(b"\x00\x00" * ntok)
    adat = bytearray()
    for a in sorted(csoportok):
        idx = 1 + 2 * (a - 1)
        off = len(fejl) + len(adat)
        if off > 0xFFFF:
            raise SystemExit("a bigramm-tabla tul nagy")
        fejl[idx] = off & 0xFF
        fejl[idx + 1] = (off >> 8) & 0xFF
        elems = csoportok[a]
        i = 0
        while i < len(elems):
            ta, wa = elems[i]
            tb = wb = 0
            if i + 1 < len(elems):
                tb, wb = elems[i + 1]
            adat.append(ta & 0xFF)
            adat.append(tb & 0xFF)
            adat.append(((wa & 0x0F) << 4) | (wb & 0x0F))
            i += 2
    blob = bytes(fejl + adat)
    open(out_path, "wb").write(blob)
    darab = sum(len(v) for v in csoportok.values())
    print(f"bigramm: {len(csoportok)} csoport, {darab} atmenet, "
          f"{len(blob)} bajt -> {out_path}")


if __name__ == "__main__":
    main()
