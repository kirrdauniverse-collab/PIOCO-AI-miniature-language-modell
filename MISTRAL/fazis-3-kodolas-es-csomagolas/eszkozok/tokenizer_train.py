"""Tokenizáló-tanító: magyar szövegből szótárat épít.

Kimenet: dict.bin — futásidejű szótárforma:
  header: token-szám (1 bájt)
  tételek: [hossz][karakterek][token-id], a blob vége: 0x00

Forma: a gyakoribb szavak kisebb token-ID-t kapnak (id = rangsor szerint),
a 0-es ID fenntartott (szó-leválasztó).
Tokén-szűkítés: legfeljebb 254 szótartoken; minden szó kisbetűs, ékezet nélküli.
"""
import re
import sys
from collections import Counter


def normal(word):
    table = str.maketrans({
        "á": "a", "é": "e", "í": "i", "ó": "o", "ö": "o", "ő": "o",
        "ú": "u", "ü": "u", "ű": "u",
    })
    return word.lower().translate(table).strip(".,!:;?()\"'")


def train(corpus_path, out_path, max_tokens=254):
    words = Counter()
    for line in open(corpus_path, encoding="utf-8"):
        for w in line.split():
            w = normal(w)
            if len(w) >= 3 and w.isalnum():
                words[w] += 1
    vocab = [w for w, _ in words.most_common(max_tokens)]
    blob = bytearray()
    blob.append(len(vocab) & 0xFF)
    for i, w in enumerate(vocab, start=1):
        wb = w.encode("ascii")
        blob.append(len(wb))
        blob.extend(wb)
        blob.append(i & 0xFF)
    blob.append(0)     # szótár-végjel
    open(out_path, "wb").write(bytes(blob))
    print(f"szótár: {len(vocab)} token, {len(blob)} bájt -> {out_path}")


if __name__ == "__main__":
    train(sys.argv[1], sys.argv[2])
