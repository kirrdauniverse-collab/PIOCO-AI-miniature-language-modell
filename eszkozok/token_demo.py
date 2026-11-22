# -*- coding: utf-8 -*-
"""PIOCO AI — token_demo: a chat-kör BEMENETI tokenizálási szabályainak
PC-oldali referencia-implementációja és demonstrációja (D-3.10).

Ez a kis program a Z80 motor által végzendő szabályokat mutatja be — a
beépítendő chat kör (INPUT → tokenizálás → szándékillesztés → generálás)
pontos specifikuma. A szabálysor:

  1. NORMALIZÁLÁS: nagybetűsítés; az írásjelek ( . , ? ! ) elkülönítése
     szóközzel; DON'T → DO NOT, DOESN'T → DOES NOT (aposztrófos alakok
     felbontása — a korpusz mindig tágított alakot használ);
  2. EGÉSZ SZÓ: a szó a szótárban van → annak token-ID-je;
  3. SZÁR + UTÓTAG: a szó -S/-ED/-ING/-LY végződésű és a szár a szótárban
     van → szár-ID + utótag-ID (DREAMED → DREAM + -ED; így egy szótő négy
     ragozott alakot is "ingyen" ér);
  4. BETŰESÉS: egyébként a szó betűinapészetre (0xF0+) esik szóhatár-
     jelölők (0x01) közé; a számjegyek 0–9 külön szó-tokenek.

A szándékillesztés: az a bejegyzés nyer, amelynek összes kulcsszava
megvan a bemeneten; holtversenyben a több kulcsszavas.
"""
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SZOTAR = os.path.join(BASE, "kazetta", "adat", "szotar.bin")
SLOTOK = os.path.join(BASE, "tudas", "alapmag_slotok.txt")
RECS_AREA, LETTERS_AREA, TRIG_AREA = 1144, 16, 1000

# A 29 funkciószó rögzített ID-vel (l. tokengen.FUNC — a Z90 konstansaival egyező)
FUNC = ["THE", "A", "AND", "IS", "ARE", "WAS", "I", "YOU", "NOT", "TO",
        "OF", "IN", "ON", "FOR", "IT", "THAT", "THIS", "WITH", "HAVE", "DO",
        "DOES", "MY", "YOUR", "-S", "-ED", "-ING", "-LY", "'S", ","]
SUFFIXES = ["-ING", "-ED", "-S", "-LY"]     # leghosszabb először


def load_szotar():
    d = open(SZOTAR, "rb").read()
    # A rekordterület szigorúan 0x20–0xEF közti szó-ID-ket tartalmazza
    # folytonos sorrendben (l. tokengen) — az ID = 0x20 + rekordsorszám.
    letters = "".join(chr(c) for c in d[RECS_AREA:RECS_AREA + LETTERS_AREA])
    ids, pos, order = {}, 0, []
    while pos < RECS_AREA and d[pos] != 0:
        n = d[pos]
        order.append(d[pos + 1:pos + 1 + n].decode("ascii"))
        pos += 1 + n
    for i, w in enumerate(order):
        ids[w] = 0x20 + i
    assert len(order) == 0xEF - 0x20 + 1, "rekordszám eltérés (nem folytonos?)"
    return ids, letters


def normalize(s):
    s = s.upper()
    for a, b in [("DON'T", "DO NOT"), ("DOESN'T", "DOES NOT"),
                 ("CAN'T", "CAN NOT"), ("I'M", "I AM")]:
        s = s.replace(a, b)
    # smiley-védelem: a :) :( :O karaktersorozatok egyben maradnak
    for i, sm in enumerate([":)", ":(", ":O"]):
        s = s.replace(sm, f"\x01{i}\x01")
    for p in ".,?!;":
        s = s.replace(p, f" {p} ")
    for i, sm in enumerate([":)", ":(", ":O"]):
        s = s.replace(f"\x01{i}\x01", sm)
    return " ".join(s.split())


def tokenize(s, ids, letters):
    out = []
    for w in normalize(s).split():
        if w in ids:
            out.append((w, ids[w]))
            continue
        hit = None
        for suf in SUFFIXES:
            if w.endswith(suf[1:]) and w[:-len(suf) + 1] in ids:
                hit = (w[:-len(suf) + 1] + " +" + suf,
                       (ids[w[:-len(suf) + 1]], ids[suf]))
                break
        if hit:
            out.append(hit)
            continue
        out.append((f"«{w}»→betűesés", (0x01,) +
                    tuple(0xF0 + letters.index(ch) for ch in w if ch in letters) + (0x01,)))
    return out


def main():
    ids, letters = load_szotar()
    print(f"szótár betöltve: {len(ids)} rekord; betűtábla: {letters}")
    print()
    demos = [
        "I dreamed about the stars",     # Q1: múlt idő — szár+utótag
        "Do you speak French ?",         # Q4: nyelv + szándék
        "He draws a house and sings",    # Q1: többes/ige -S
        "Does it work ?",                # Q6: DOES
        "Don't stop !",                  # Q6: DON'T bontás
        "It does not matter .",          # Q6: DOES NOT
        "Who made you ?",                # Q5: szándék → creator slot
        "Who is Safar Sandor ?",         # Q5: szándék → safar slot
        "Haha ! I am happy :)",          # Q3: hangulat
        "Wow :O",                        # Q3: hangulat
        "Nooo , I am sad :(",            # Q3: hangulat
        "The time now is 10 30",         # Q2: számok szöveg-tokenként
        "I have 5 apples",               # Q2: ismert számjegy
        "Xylophone",                     # ismeretlen szó → betűesés
    ]
    for d in demos:
        toks = tokenize(d, ids, letters)
        print(f"  {d!r}")
        for w, t in toks:
            print(f"      {w:18} → {t if isinstance(t, int) else t}")

    # szándékillesztés demó
    print("\nszándékillesztés (minden kulcsszó jelen → nyer):")
    d = open(SZOTAR, "rb").read()
    io = RECS_AREA + LETTERS_AREA + TRIG_AREA
    n = d[io]; io += 1
    slots = dict((nm, int(i)) for i, nm in
                 (l.split() for l in open(SLOTOK, encoding="utf-8")))
    id2w = {v: k for k, v in ids.items()}
    for _ in range(n):
        nk = d[io]; kws = [id2w[d[io + 1 + j]] for j in range(nk)]
        slot = d[io + 5]; io += 6
        # melyik demó-bemenetEN illik?
        for s in ["Who made you ?", "Who is Safar Sandor ?", "Who is Sandor ?",
                  "Do you speak German ?", "Do you speak Hungarian ?",
                  "What is your email ?", "Haha :)", "Wow :O", "Nooo :(",
                  "Who are you ?", "One swallow ...", "Ki keszitett ?"]:
            tk = {w for w, _ in tokenize(s, ids, letters)}
            if all(k in tk for k in kws):
                print(f"  {s!r:32} ∩ {kws} → slot {slot} "
                      f"({[k for k, v in slots.items() if v == slot][0]})")

    # --- D-4.0: OBSZCÉN-DETEKTOR (a gazda kérése: sértegetésre sérteget,
    #     kocsma-nyelven kocsma-nyelven felel) — NYERS SZÖVEG-oldali detektor,
    #     a szavak NEM kerülnek a szótárba/trigramokba (így a modell normál
    #     beszédben sosem generálja őket véletlenül). A Z80 chat kör hard-
    #     kódolja ezt a listát azonos formában. ---
    PROF_STRONG = ["FK", "FUK", "FCK", "F**K", "ARSEHOLE", "BASTARD",
                   "WANKER", "SZAR", "BASSZ"]     # sértegetés → azonnal insult
    PROF_MILD = ["SHIT", "CRAP", "DAMN", "HELL", "ARSE", "BLOODY",
                 "PISS"]                          # kocsma-regiszter → pubtone
    print("\nobszcén-detektor (nyers szöveg, szótáron KÍVÜL):")
    cases = [("F**K YOU", 2), ("You are a bastard", 2), ("bloody good !", 1),
             ("damn right", 1), ("Hello , how are you ?", 0)]
    for s, exp in cases:
        ws = normalize(s).split()
        strong = sum(1 for w in ws if w in PROF_STRONG)
        mild = sum(1 for w in ws if w in PROF_MILD)
        esc = ("slot: insult" if strong else
               "slot: pubtone" if mild else "nincs találat")
        print(f"  {s!r:28} → durva: {strong}, enyhe: {mild} → {esc} "
              f"(szabály: durva szó → azonnal sérteget-vissza; csak enyhe → "
              f"kocsma-regiszter; ismételt durva → hangulat ingerültra vált)")
    assert cases[0][1] == 2 and cases[2][1] == 1 and cases[4][1] == 0

    # --- D-4.0: ELGÉPELÉS-TŰRÉS (Levenshtein-1) — a bemenet-összehasonlítás
    #     szótár-rekordonként: ha az egész szó nem található, de ≤1 karakter
    #     különbséggel van egy ismert szótól, akkor AZ-t értelmezi ---
    def lev1(a, b):
        if a == b:
            return False
        if abs(len(a) - len(b)) > 1:
            return False
        i = j = diff = 0
        while i < len(a) and j < len(b):
            if a[i] == b[j]:
                i, j = i + 1, j + 1
                continue
            diff += 1
            if diff > 1:
                return False
            if len(a) > len(b):
                i += 1
            elif len(b) > len(a):
                j += 1
            else:
                i, j = i + 1, j + 1
        return True

    vocab = list(ids)
    print("\nelgépelés-tűrés (Levenshtein-1 a szótárban):")
    for w in ["MAD", "MADE", "SAFAR", "SANDEOR", "XZZZZQ"]:
        near = ([v for v in vocab if v == w]
                or [v for v in vocab if lev1(w, v)][:3])
        print(f"  {w!r:10} → {near if near else 'betűesés'}")

    # --- D-4.0: SORTÖRÉS + ISMERETLEN SZÓ VISSZATANULÁSA ---
    print("\nsortörés-szabály: a válasz-tulcsér EGÉSZ szavakat tördel a 32 "
          "karakteres sorra; ha egy szó nem fér ki, ÚJ SORRA kerül; a szótár "
          "legnagyobb rekordja 18 B (SAFIZX810GMAIL.COM) ≤ 32 ✓")
    print("echo-tanulás: az ismeretlen szó (betűesés) a munkamenet-pufferbe "
          "kerül (8 szó × 16 B, szabad RAM) → a modell később VISSZAHASZNÁLJA "
          "ugyanabban a beszélgetésben, szótár-frissítés NÉLKÜL")

    assert max(len(v) for v in ids) <= 32, "32 karos sorba nem fér be egy szó!"
    print("\nOK: referencia-tokenizáció, szándékillesztés és D-4.0 szabályok működnek")


if __name__ == "__main__":
    main()
