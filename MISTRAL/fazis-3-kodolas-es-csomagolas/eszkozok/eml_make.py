"""eml_make.py - emlekrezet (06) blokk keszito.

Formatum: [0xC3][count][4 bajtos rekordok], rekord =
  [bitkod 0..31][ertek 0/1 (bit7 = elavulas)][nap 1..31][honap 1..12]

Hasznalat:
  python3 eml_make.py <out.bin> [bitkod:ertek:nap:honap ...]

Pelda (fejfajas = 1, 12. napon, 5. honapban):
  python3 eml_make.py eml.bin 0:1:12:5
"""
import sys


def rekord(s):
    k = s.split(":")
    if len(k) != 4:
        raise SystemExit(f"rossz parameter: {s} (alak: bitkod:ertek:nap:honap)")
    bit, ert, nap, hon = (int(x) for x in k)
    if not (0 <= bit <= 31):
        raise SystemExit("bitkod 0..31 kozotti legyen")
    if ert not in (0, 1):
        raise SystemExit("ertek 0 vagy 1 legyen")
    if not (1 <= nap <= 31 and 1 <= hon <= 12):
        raise SystemExit("nap 1..31, honap 1..12")
    return bytes([bit, ert, nap, hon])


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        raise SystemExit(1)
    rekordok = [rekord(s) for s in sys.argv[2:]]
    if len(rekordok) > 63:
        raise SystemExit("max 63 rekord fer az emlekezetzonaba")
    out = bytes([0xC3, len(rekordok)]) + b"".join(rekordok)
    with open(sys.argv[1], "wb") as f:
        f.write(out)
    print(f"eml block: {len(out)} bajt, {len(rekordok)} rekord -> {sys.argv[1]}")


if __name__ == "__main__":
    main()
