# -*- coding: utf-8 -*-
"""PIOCO AI — tokengen: ANGOL szótár generálása a 2. fázis 2.4-es elrendezése szerint.

Kimenet: kazetta/adat/szotar.bin (pontosan 2304 B)
  [tokenrekordok 1144 B] [betűtábla 16 B] [trigram súlytömb 1000 B] [tartalék 144 B]

Döntések (a fazis-2-terveles.md D-3.2 nyelvi fordulata szerint):
  - a prototípus nyelve ANGOL (ZX81 → csak NAGYBETŰK, ASCII-ben tárolva;
    a motor ASCII→ZX81 kódtáblája fordítja printkor — tartalma ROM-listából, ellenőrzés után);
  - 0x20–0x3B: 28 funkciószó/utótag (angol: THE, A, -S, -ED, -ING, -LY, 'S stb.);
  - 0x3C–0xEF: a korpusz leggyakoribb 180 tartalmi szava;
  - 0xF0–0xFF: a 16 leggyakoribb betű (ismeretlen szó → betűesés);
  - trigram rekord: [k1,k2,k3,w] — w alsó nibble = súly 0..7 (count-1), felső nibble tartalék.
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from crc16 import crc16

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KORPUSZ = os.path.join(BASE, "tudas", "alap_korpusz_en.txt")
OUT_BIN = os.path.join(BASE, "kazetta", "adat", "szotar.bin")
OUT_LISTA = os.path.join(BASE, "tudas", "szotar_en_lista.txt")

RECS_AREA = 1144
LETTERS_AREA = 16
TRIG_AREA = 1000
RESERVE_AREA = 144
TOTAL = RECS_AREA + LETTERS_AREA + TRIG_AREA + RESERVE_AREA
assert TOTAL == 2304

# Funkciószavak + utótagok a 0x20–0x3C sávhoz (D-3.10: RÖGZÍTETT ID-k —
# a korábbi, korpuszjelenléthez kötött kiosztás ID-eltolódást okozott volna,
# ha a korpusz változik; így a Z80 motor konstansként hivatkozhat rájuk).
# A szuffix-tokenek (-S/-ED/-ING/-LY) a bemenet oldali általánosításhoz
# kellenek: DREAMED → DREAM + -ED (a chat kör tokenizálója: egész szó,
# majd szár+utótag, majd betűesés) — így egy szótő 4 ragozott alakot ér.
FUNC = ["THE", "A", "AND", "IS", "ARE", "WAS", "I", "YOU", "NOT", "TO",
        "OF", "IN", "ON", "FOR", "IT", "THAT", "THIS", "WITH", "HAVE", "DO",
        "DOES", "MY", "YOUR", "-S", "-ED", "-ING", "-LY", "'S", ","]
assert len(FUNC) == 29
FUNK_END = 0x3D            # a tartalmi szavak kezdete (179 db → 0xEF-ig)

# D-3.10: kényszer-tartalmi szavak — a szándéktábla kulcsszavai és a
# kanonikus válaszok szavai mindig kapjanak ID-t, függetlenül a gyakoriságtól
# (a számok mint SZÖVEG-tokenek: 0–9 + gyakori időpontok, hogy a bemenet
# számjegyei ne vesszenek el a betűesésben)
FORCE = ["WHO", "MADE", "BUILT", "SAFAR", "SANDOR", "QWEN", "SPEAK", "ONLY",
         "ENGLISH", "GERMAN", "FRENCH", "HUNGARIAN", "SPANISH", "ITALIAN",
         "LANGUAGE", "HAHA", "WOW", "NOOO", ":)", ":(", ":O", "ONE",
         "SWALLOW", "SUMMER", "MAKE", "BUS", "DRIVER", "WRITER",
         "ASTRONOMER", "SORRY", "AGAIN", "FUNNY", "HAPPY", "SAD", "TRY",
         "SURPRISE", "GLAD", "UNDERSTAND",
         "0", "1", "2", "3", "4", "5", "6", "8", "9",
         "KI", "KESZITETT", "CSINALTA", "EMAIL", "MAGYARUL", "BESZEL"]

# Karakterszűrő: a ZX81-biztonságos ASCII készlet (0x20–0x5A — A-Z, számok, írásjelek)
def safe_word(w):
    return all(" " <= c <= "Z" for c in w)

def main():
    lines = [l.strip() for l in open(KORPUSZ, encoding="utf-8") if l.strip()]
    stream = []           # token-sorozat (sztringek)
    for l in lines:
        stream.extend(l.split())

    # --- frekvenciák ---
    freq = {}
    for t in stream:
        freq[t] = freq.get(t, 0) + 1

    # --- tartalmi szavak: kényszer-lista + gyakorisági top (D-3.10) ---
    forced = [(w, freq[w]) for w in FORCE if w in freq]
    missing = [w for w in FORCE if w not in freq]
    assert not missing, f"kényszer-szó nincs a korpuszban: {missing}"
    content = [(w, c) for w, c in freq.items()
               if w not in FUNC and safe_word(w) and not w.startswith("-")]
    content.sort(key=lambda x: (-x[1], x[0]))
    content = forced + [wc for wc in content if wc[0] not in {f[0] for f in forced}]
    content = content[:0xEF - FUNK_END + 1]   # 179 db (0x3D–0xEF)

    # --- betűk (csak A-Z) ---
    lc = {}
    for w, c in freq.items():
        for ch in w:
            if "A" <= ch <= "Z":
                lc[ch] = lc.get(ch, 0) + c
    letter_order = sorted(lc, key=lambda x: (-lc[x], x))[:16]
    letters = letter_order

    # --- ID-kiosztás (D-3.10: a 29 FUNC szó RÖGZÍTETT ID-n, jelenléttől
    #     függetlenül — így a Z80 konstansokat fordíthat rájuk) ---
    tok2id = {}
    for i, w in enumerate(FUNC):
        tok2id[w] = 0x20 + i
    for i, (w, _) in enumerate(content):
        tok2id[w] = FUNK_END + i
    for i, ch in enumerate(letters):
        if ch not in tok2id:      # "A"/"I" funkciószóként él tovább (D-3.10)
            tok2id[ch] = 0xF0 + i
    assert FUNK_END + len(content) - 1 <= 0xEF, "tartalmi szavak túlcsordultak a 0xEF-nél"

    # --- korpusz → ID-sorozat (ismeretlen szó: betűesés + szóhatár) ---
    ids = []
    covered = 0
    for t in stream:
        if t in tok2id:
            ids.append(tok2id[t]); covered += 1
        else:
            ids.append(0x01)  # SZÓHATÁR (vezérlőtoken)
            for ch in t:
                if ch in letter_order:
                    ids.append(0xF0 + letter_order.index(ch))
            ids.append(0x01)

    # --- trigramok ---
    trig = {}
    for i in range(len(ids) - 2):
        key = (ids[i], ids[i + 1], ids[i + 2])
        trig[key] = trig.get(key, 0) + 1
    top = sorted(trig.items(), key=lambda x: (-x[1], x[0]))[:250]

    # --- rekordok (ID-sorrend, hossz-prefix) ---
    # Csak a 0x20–0xEF közti SZÓ-ID-k kapnak rekordot (a 16 betűnek NEM kell:
    # az egymagyaros betű a keresésnél a betűesésre fut, a betűtábla pedig
    # külön, fix offszten áll). Ez az "A"/"I" kettősség (funkciószó ÉS betű)
    # miatti ütközést is feloldja, és a rekordterület folytonosságát
    # (ID = 0x20 + rekordsorszám) garantálja a Z80 keresőnek.
    recs = {}
    for w, i in tok2id.items():
        if i < 0xF0:
            recs[i] = w.encode("ascii")
    assert all(len(v) <= 18 for v in recs.values()), "túl hosszú rekord (max 18 B — SAFIZX810GMAIL.COM)"
    assert sorted(recs) == list(range(0x20, 0xF0)), \
        "rekord-ID-k nem folytonosak 0x20–0xEF közt (Z80-keresés feltétele)"

    out = bytearray(TOTAL)
    pos = 0
    for i in sorted(recs):
        if pos + 1 + len(recs[i]) > RECS_AREA:
            print(f"  FIGYELMEZTETÉS: rekordterület betelt ({i:#04x} ID-nél) — csökkentett szótár")
            break
        out[pos] = len(recs[i]); pos += 1
        out[pos:pos + len(recs[i])] = recs[i]; pos += len(recs[i])
    recs_used = pos

    # betűtábla (fix offset: RECS_AREA)
    for i, ch in enumerate(letters):
        out[RECS_AREA + i] = ord(ch)

    # trigram súlytömb (fix offset: RECS_AREA + LETTERS_AREA)
    off = RECS_AREA + LETTERS_AREA
    for (k1, k2, k3), c in top:
        w = min(7, c - 1)  # 0..7, alsó nibble
        out[off] = k1; out[off + 1] = k2; out[off + 2] = k3; out[off + 3] = w & 0x0F
        off += 4
    trig_used = (off - RECS_AREA - LETTERS_AREA) // 4

    # --- D-3.10: SZÁNDÉKTÁBLA a tartalék területre (2160–2303) ---
    # Bejegyzés: [kulcsszavak száma nk][k1][k2][k3][k4][alapmag-slot]
    # (6 B/db, használatlan kulcsszó-bájt = 0). Illesztési szabály a Z80 chat
    # körben: az a bejegyzés nyer, amelynek ÖSSZES kulcsszava megtalálható a
    # bemenet tokenjei közt; holtversenyben a több kulcsszavas; ezután jön
    # csak a trigram-os generálás (ez spórol memóriát és tokent — l. D-3.10).
    slot_names = {}
    with open(os.path.join(BASE, "tudas", "alapmag_slotok.txt"), encoding="utf-8") as sf:
        for ln in sf:
            idx, nm = ln.split()
            slot_names[nm] = int(idx)
    INTENTS = [
        (["WHO", "ARE", "YOU"], "pioco"),
        (["WHO", "MADE"], "creator"),
        (["WHO", "BUILT"], "creator"),
        (["WHO", "IS", "SAFAR"], "safar"),
        (["WHO", "SANDOR"], "safar"),
        (["SPEAK", "GERMAN"], "english"),
        (["SPEAK", "FRENCH"], "english"),
        (["SPEAK", "HUNGARIAN"], "english"),
        (["SPEAK", "SPANISH"], "english"),
        (["SPEAK", "ITALIAN"], "english"),
        (["SPEAK", "LANGUAGE"], "english"),
        (["HAHA"], "hahaha"),
        ([":)"], "hahaha"),
        (["WOW"], "wow"),
        ([":O"], "wow"),
        (["NOOO"], "nooo"),
        ([":("], "nooo"),
        (["ONE", "SWALLOW"], "proverb"),
        (["KI", "KESZITETT"], "creator"),
        (["KI", "CSINALTA"], "creator"),
        (["KI", "SAFAR"], "safar"),
        (["EMAIL"], "email"),
        (["BESZEL", "MAGYARUL"], "english"),
    ]
    ioff = RECS_AREA + LETTERS_AREA + TRIG_AREA       # 2160
    out[ioff] = len(INTENTS); ioff += 1
    for kws, slot in INTENTS:
        kw_ids = [tok2id[k] for k in kws]             # KeyError = nincs ID → hiba
        assert 1 <= len(kws) <= 4 and slot in slot_names, f"hibás szándék: {kws} → {slot}"
        out[ioff] = len(kws)
        for j in range(4):
            out[ioff + 1 + j] = kw_ids[j] if j < len(kws) else 0
        out[ioff + 5] = slot_names[slot]
        ioff += 6
    intent_used = ioff - (RECS_AREA + LETTERS_AREA + TRIG_AREA)
    assert ioff <= TOTAL, "szándéktábla túlcsordult a tartalék területen"

    os.makedirs(os.path.dirname(OUT_BIN), exist_ok=True)
    with open(OUT_BIN, "wb") as f:
        f.write(out)

    # --- emberi olvasmányú lista ---
    with open(OUT_LISTA, "w", encoding="utf-8") as f:
        f.write("PIOCO AI — angol szótár (prototípus) — generált lista\n")
        f.write(f"rekordterület: {recs_used}/{RECS_AREA} B\n")
        f.write(f"betűtábla: {''.join(letters)}\n")
        f.write(f"trigramok: {trig_used}/250\n\n")
        f.write("ID    típus      szöveg\n")
        f.write("-" * 40 + "\n")
        for i in sorted(recs):
            tipus = "FUNK" if 0x20 <= i < FUNK_END else ("SZO" if i < 0xF0 else "BETU")
            f.write(f"0x{i:02X}  {tipus:9}  {recs[i].decode()}\n")
        f.write(f"\nszándéktábla ({len(INTENTS)} bejegyzés, tartalék terület):\n")
        for kws, slot in INTENTS:
            f.write(f"  {'+'.join(kws):28} → slot {slot_names[slot]:2d} ({slot})\n")

    # --- statisztika + ellenőrzés ---
    total_tokens = len(stream)
    print(f"korpusz: {len(lines)} sor, {total_tokens} token")
    print(f"funkciószavak (0x20–0x3C, rögzített): {len(FUNC)}, "
          f"tartalmi szavak (0x3D–0xEF, {len(forced)} kényszerrel): {len(content)}, "
          f"betűk: {len(letters)}, szándék-bejegyzések: {len(INTENTS)} "
          f"({intent_used} B a tartalékból)")
    print(f"rekordterület: {recs_used}/{RECS_AREA} B, trigramok: {trig_used}/250")
    cov = covered / total_tokens * 100
    print(f"szó-level lefedettség (funkció+szó token): {cov:.1f}% (betűesés a maradék)")
    assert len(out) == 2304
    # 0x76-tilalom: a KIÍRHATÓ részekre (rekordszövegek + betűtábla) érvényes.
    # A token-ID-k és trigram-kulcsok lehetnek 0x76-osok — ezek belső azonosítók,
    # sosem kerülnek a képernyőre (print-tölcsér, fazis-2 5.3).
    assert 0x76 not in out[0:RECS_AREA + LETTERS_AREA], "0x76 a kiírható rekordokban tiltott!"
    assert crc16(out) == crc16(open(OUT_BIN, 'rb').read())
    print(f"OK: {OUT_BIN} (2304 B, CRC-16: 0x{crc16(out):04X})")

if __name__ == "__main__":
    main()
