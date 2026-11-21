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
    (0x01, "I HOPE YOU FEEL BETTER ."),
    (0x01, "REST NOW , YOU LOOK TIRED ."),
    (0x01 | (MOOD_H << 1), "I DRAW A HOUSE . LOOK , NO WINDOWS YET ."),
    (0x01, "I ADD A WINDOW TO THE HOUSE ."),
    (0x01, "I ADD A TREE . THE SKY STAYS FREE FOR THE SUN ."),
    (0x01, "I ERASE THE DRAWING . A NEW PAGE FOR US ."),
    (0x01, "HERE IS YOUR BASIC PROGRAM ."),
    (0x01, "LINE #LINE IS CHANGED ."),
    (0x01, "THE PROGRAM HAS #LINES LINES ."),
    (0x01, "SAVED ON TAPE . YOUR MEMORY IS SAFE ."),
    (0x01 | (MOOD_I << 1), "SLOW ? I THINK FAST IN A TINY ROOM ."),
    (0x01 | (MOOD_I << 1), "I AM A TINY MODEL , NOT A GIANT ."),
    (0x01 | (MOOD_H << 1), "A GENIUS ? I AM ONLY 16 K OF BRAVE CODE ."),
    (0x01 | (MOOD_V << 1), "I KEEP MY POINT : THE ZX81 IS A GREAT MACHINE ."),
    (0x01 | (MOOD_V << 1), "PC OR ZX81 , WE CAN ARGUE WITH RESPECT ."),
    (0x01, "THE SUN IS A STAR . STARS ARE FAR FROM US ."),
    (0x01, "RAIN IS WATER FROM THE CLOUDS ."),
    (0x01 | 0x08, "WHAT DO YOU WANT ?"),
    (0x01 | 0x08, "ASK ME LATER , I DO NOT KNOW IT YET ."),
    (0x01, "GOOD MORNING !"),
    (0x01, "GOOD NIGHT ! I WILL REMEMBER YOU ."),
    (0x01, "GOOD BYE FOR NOW ."),
    (0x01 | 0x08, "PLEASE TELL ME THE TIME ."),
]

assert len(TEMPLATES) <= 32, "max 32 sablon-slot"

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
    print(f"ALAPMAG: {n}/32 slot használva, szövegátlag "
          f"{sum(len(t) for _, t in TEMPLATES)/n:.0f} B, OUT: {OUT} (2048 B)")
    assert out.count(0x76) == 0
    print("OK: 0x76-mentes, minden szöveg nagybetűs ASCII")

if __name__ == "__main__":
    main()
