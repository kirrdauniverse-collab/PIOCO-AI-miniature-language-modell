# Elkészült csomagok állapottáblája (4. fázis, angol prototípus)

Motor: **1 819 bájt (v2)** · szótár: **111 token / 740 B** · bigramm:
**550 B, 212 átmenet** · kazetta: **4 144 B / 5 blokk**
Mindet a futó eszközlánc építette és a füstvizsgálat zölden hozta
(most már a bigramm-forma ellenőrzéssel együtt).

| # | Csomag | Forrás | Méret | Állapot |
| ---: | --- | --- | ---: | --- |
| — | ALAPMAG (rezidens) | `tudas/science.txt` | 451 B | ✅ betöltött (B4 blokk) |
| 1 | SCIENCE | `tudas/science.txt` | 451 B | ✅ lefordítva, kazettán (B5) |
| 2 | HEALTH | `tudas/health.txt` | 313 B | ✅ lefordítva (bármelyik újraépített kazettára betehető) |
| 3 | RETRO | `tudas/retro.txt` | 340 B | ✅ lefordítva (bármelyik újraépített kazettára betehető) |
| 4 | ASTRONOMY | `tudas/astronomy.txt` | 316 B | ✅ lefordítva |
| 5 | COOKING | `tudas/cooking.txt` | 295 B | ✅ lefordítva |
| 6 | ENTERTAINMENT | `tudas/entertainment.txt` | 286 B | ✅ lefordítva |
| 7 | FUTURE | `tudas/future.txt` | 326 B | ✅ lefordítva |
| 8 | LEARNING | `tudas/learning.txt` | 303 B | ✅ lefordítva |
| 9 | HOBBY | `tudas/hobby.txt` | 305 B | ✅ lefordítva |
| 10 | LITERATURE | `tudas/literature.txt` | 267 B | ✅ lefordítva |
| 11 | MOVIES | `tudas/movies.txt` | 286 B | ✅ lefordítva |
| 12 | CELEBRITIES | `tudas/celebrities.txt` | 312 B | ✅ lefordítva |
| 13 | ART | `tudas/art.txt` | 259 B | ✅ lefordítva |
| 14 | WORK | `tudas/work.txt` | 273 B | ✅ lefordítva |
| 15 | UFO | `tudas/ufo.txt` | 313 B | ✅ lefordítva |

A cseréhez a B5-CSOMAG blokkot más bin-re érdemes építeni, például:

```
python3 eszkozok/t81_build.py kazetta/motor.bin kazetta/szotar_full.bin \
        kazetta/science.bin kazetta/PIOCO.T81 kazetta/health.bin HEALTH
```

*(A magyar nyelvű csomagok a kiforrott modell után jönnek — lásd
`01-nyelvvaltas-dontes.md`.*)

## Általános mértékadó szabály

Egy csomag max. **1536 bájt**; ha nagyobb, szekciókra bontjuk (07-es
SZAKASZ-típus, a 2. fázisbeli .T81-formátum szerint) és kétmenetben töltjük.
Eddig a legnagyobb lefordított csomag 451 B — bőven van tartalék.
