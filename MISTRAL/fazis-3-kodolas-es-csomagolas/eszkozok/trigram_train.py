"""Trigram-tanito: korpuszbol sulyozott (t1,t2) -> t3 tablat epit (tri.bin).

Mukodes:
  1. szotar.bin-bol kiolvassa a szo -> token-id hozzarendeles,
  2. a korpuszt token-sorozatta alakitja (ismeretlen szo kihagyva),
  3. a (t1,t2) -> t3 atmeneteket megszamolja,
  4. csak azokat a kulcsokat tartja meg, ahol a kovetok szama legalabb
     2 (vagyis ahol a trigram valoban tobbet tud, mint a bigram),
     es kulcsonkent legfeljebb MAXFOLL kovetot oriz,
  5. a kovetok sulyat 4 bites kvantalassal (1..15), a bigramhoz hasonloan,
     gyakorisag szerint rendezve csomagolja.

tri.bin formatuma:
  kulcsonkent: [t1][t2][n][(t,w)-parok nibble-csomagolva][0 vegjel]
    - a (t,w) parok pontosan ugyaticalakulnak, mint a bigramm-csoportok
      ([tA][tB][wAB]-harmasok, wAB felso nibble = A sulya),
    - paratlan elemszamnal az utolso elem par-padded ([tX][0][wX<<4]),
    - a kulcs-koveto lista utan egy 0x00 vegjel jon,
  tabla-vegjel: egyetlen 0x00 (a kovetkezo kulcs helyen t1 = 0).
  A motor a bg.bin VEGE UTANI elso bajttal kezdodo tablat olvassa (TRIB cim);
  ezt a bg.bin fejlecuben az extra eltolás adja meg (lasd bigram_train.py).

Hasznalat:
  python3 trigram_train.py tudas/alapcorpus.txt kazetta/szotar.bin kazetta/tri.bin
"""
import sys
from collections import Counter

MAXFOLL = 15
MINKUPCSON = 2


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
        if len(ids) >= 3:
            sorok.append(ids)

    # (t1,t2) -> {t3: darab} atmenetek
    tri = {}
    for ids in sorok:
        for t1, t2, t3 in zip(ids, ids[1:], ids[2:]):
            tri.setdefault((t1, t2), Counter())[t3] += 1

    # csak ismetelt contextusok + kovetok szaritasa
    kulcsok = {}
    for (t1, t2), szaml in tri.items():
        if len(szaml) < MINKUPCSON:
            continue
        lista = sorted(szaml.items(), key=lambda kv: (-kv[1], -kv[0]))[:MAXFOLL]
        ossz = sum(darab for _, darab in lista)
        elems = [(t3, max(1, round(15 * darab / ossz))) for t3, darab in lista]
        kulcsok[(t1, t2)] = elems

    blob = bytearray()
    for (t1, t2), elems in sorted(kulcsok.items()):
        blob.append(t1 & 0xFF)
        blob.append(t2 & 0xFF)
        blob.append(len(elems) & 0xFF)
        i = 0
        while i < len(elems):
            ta, wa = elems[i]
            tb = wb = 0
            if i + 1 < len(elems):
                tb, wb = elems[i + 1]
            blob.append(ta & 0xFF)
            blob.append(tb & 0xFF)
            blob.append(((wa & 0x0F) << 4) | (wb & 0x0F))
            i += 2
        blob.append(0)
    blob.append(0)
    open(out_path, "wb").write(bytes(blob))
    parok = sum(len(v) for v in kulcsok.values())
    print(f"trigramm: {len(kulcsok)} kulcs, {parok} kovetoadat, "
          f"{len(blob)} bajt -> {out_path}")


if __name__ == "__main__":
    main()
