# -*- coding: utf-8 -*-
"""PIOCO AI — alapmag_gen: az ALAPMAG (válasz-vázsablonok) 2048 B-s binárisa.

Elrendezés: 32 slot × 64 B. Slot: [zászló][ASCII szöveg max 63 B]
  zászló bit0 = használt; bit1–2 = hangulat (0 semleges, 1 humoros, 2 ingerült, 3 vita);
  bit3 = kérdés várakozás (ASK); bit4 = emlékeztető-sablon.
A szöveg nagybetűs ASCII (ZX81-fürdetés a motorban: ASCII→ZX81 tábla).
A táblát a mesterprompt viselkedési példái (humor, ingerlés, vita, emlékeztető) fedik.
"""
import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, "kazetta", "adat", "alapmag.bin")

MOOD_N, MOOD_H, MOOD_I, MOOD_V = 0, 1, 2, 3

TEMPLATES = [
    (0x01, "HELLO , I AM PIOCO . I RUN IN 16 K ."),
    (0x01 | (MOOD_H << 1), "MY MEMORY IS SMALL BUT MY DREAMS ARE BIG ."),
    (0x01, "HOW ARE YOU TODAY ?"),
    (0x01 | 0x08, "WHAT IS YOUR NAME ?"),
    (0x01, "THE TIME NOW IS #TIME ."),
    (0x01 | 0x10, "I WILL REMEMBER : AT #TIME #TASK ."),
    (0x01 | 0x10, "IT IS #TIME NOW . TIME TO #TASK !"),
    (0x01, "I REMEMBER IT ."),
    (0x01, "YOUR HEAD ACHED ON #DAY . HOW IS IT NOW ?"),
    (0x01, "REST NOW . I HOPE YOU FEEL BETTER ."),
    (0x01 | (MOOD_H << 1), "I DRAW A HOUSE . LOOK , NO WINDOWS YET ."),
    (0x01, "I ADD A WINDOW TO THE HOUSE ."),
    (0x01, "I ADD A TREE . THE SKY STAYS FREE FOR THE SUN ."),
    (0x01, "I ERASE THE DRAWING . A NEW PAGE FOR US ."),
    (0x01, "HERE IS YOUR BASIC PROGRAM ."),
    (0x01, "LINE #LINE IS CHANGED . THE PROGRAM HAS #LINES LINES ."),
    (0x01, "SAVED ON TAPE . YOUR MEMORY IS SAFE ."),
    (0x01 | (MOOD_I << 1), "SLOW ? I AM A TINY MODEL , NOT A GIANT , BUT FAST ."),
    (0x01 | (MOOD_H << 1), "A GENIUS ? I AM ONLY 16 K OF BRAVE CODE ."),
    (0x01 | (MOOD_V << 1), "I KEEP MY POINT : THE ZX81 IS A GREAT MACHINE ."),
    (0x01, "THE SUN IS A STAR . RAIN IS WATER FROM THE CLOUDS ."),
    (0x01 | 0x08, "WHAT DO YOU WANT ?"),
    (0x01 | 0x08, "ASK ME LATER , I DO NOT KNOW IT YET ."),
    (0x01, "GOOD MORNING ! OR GOOD NIGHT ? TELL ME THE TIME ."),
    (0x01, "GOOD BYE FOR NOW ."),
    # --- D-3.10: szándékhoz kötött válaszok (a tokengen szándéktáblája
    #     hivatkozik rájuk név szerint — l. SLOT_NAMES / alapmag_slotok.txt) ---
    (0x01, "I WAS MADE BY SAFAR SANDOR , WITH HELP FROM QWEN ."),
    (0x01, "HE IS A HUNGARIAN BUS DRIVER , AMATEUR WRITER AND ASTRONOMER ."),
    (0x01, "I SPEAK ONLY ENGLISH . SORRY ."),
    (0x01 | (MOOD_H << 1), "HAHA ! I AM GLAD YOU LIKE IT ."),
    (0x01 | (MOOD_H << 1), "WOW ! YOU SURPRISE ME ."),
    (0x01, "NOOO ? I AM SORRY . LET US TRY AGAIN ."),
    (0x01, "ONE SWALLOW DOES NOT MAKE A SUMMER ."),
]

# A slotok nevei — a tokengen szándéktáblája ezzel a manifesttel hivatkozik
# a slotokra (nincs kézzel tartott sorszám-kettőzés). 32 név, pontos sorrend.
SLOT_NAMES = [
    "pioco", "dream", "howareyou", "askname", "time", "remember", "remind",
    "remembered", "headache", "rest", "drawhouse", "window", "tree", "erase",
    "basic", "line", "saved", "slow", "genius", "argue", "nature", "want",
    "asklater", "daygreet", "bye", "creator", "safar", "english", "hahaha",
    "wow", "nooo", "proverb",
]

assert len(TEMPLATES) <= 32, "max 32 sablon-slot"
assert len(SLOT_NAMES) == len(TEMPLATES), "SLOT_NAMES a TEMPLATES-szel egy hosszú"

def main():
    out = bytearray(2048)
    n = 0
    for flags, text in TEMPLATES:
        b = text.encode("ascii")
        assert len(b) <= 63, f"túl hosszú sablon ({len(b)} B): {text}"
        off = n * 64
        out[off] = flags
        out[off + 1:off + 1 + len(b)] = b
        n += 1
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "wb") as f:
        f.write(out)
    # --- D-3.10: slot-manifeszt a tokengen szándéktáblája számára ---
    slot_id = lambda nm: SLOT_NAMES.index(nm)
    manifest = os.path.join(BASE, "tudas", "alapmag_slotok.txt")
    with open(manifest, "w", encoding="utf-8") as f:
        for i, name in enumerate(SLOT_NAMES):
            f.write(f"{i}\t{name}\n")
    print(f"ALAPMAG: {n}/32 slot használva, szövegátlag "
          f"{sum(len(t) for _, t in TEMPLATES)/n:.0f} B, OUT: {OUT} (2048 B)")
    print(f"slot-manifeszt: {manifest} (creator={slot_id('creator')}, "
          f"safar={slot_id('safar')}, english={slot_id('english')}, "
          f"hahaha/wow/nooo={slot_id('hahaha')}/{slot_id('wow')}/{slot_id('nooo')}, "
          f"proverb={slot_id('proverb')})")
    assert out.count(0x76) == 0
    print("OK: 0x76-mentes, minden szöveg nagybetűs ASCII")

if __name__ == "__main__":
    main()
