"""Tudás-csomag fordító: <kulcsszó><tab><tényszöveg> sorokból
[kkulcsszó][0][tény][0]... bináris formátum (a motor KBLOOK-lánca ezt olvassa).
A kimenet bájtjait az 0x76-tiltás és a vezérlőkód-szűrés kezeli
(a motor SAFEPCHR-rutinjának szabályaival megegyezően).
"""
import sys

TILTOTT = set([0x76] + list(range(0xC0, 0x100)))


def biztos_szoveg(s):
    out = bytearray()
    for ch in s.encode("ascii", errors="replace"):
        out.append(0x1B if ch in TILTOTT else ch)
    return bytes(out)


def fordit(path, out_path, max_hossz=1500):
    blob = bytearray()
    for line in open(path, encoding="utf-8"):
        line = line.rstrip("\n")
        if not line or line.startswith('#'):
            continue
        if "\t" not in line:
            continue
        kw, fact = line.split("\t", 1)
        if not kw or not fact:
            continue
        kb = biztos_szoveg(kw.strip().lower())
        fb = biztos_szoveg(fact.strip())
        blob.extend(kb)
        blob.append(0)
        blob.extend(fb)
        blob.append(0)
        if len(blob) + 1 > max_hossz:
            print(f"VIGYÁZAT: csomag a {max_hossz} bájtot meghaladná — "
                  f"a következő tételek már nem férnek be.")
            break
    blob.append(0)     # láncalezáró
    open(out_path, "wb").write(bytes(blob))
    print(f"csomag: {out_path}, {len(blob)} bájt")


if __name__ == "__main__":
    fordit(sys.argv[1], sys.argv[2])
