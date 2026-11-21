# Elkészült csomagok állapottáblája (4. fázis, angol prototípus)

Motor: 1 118 bájt · szótár: 90 token / 661 B · kazetta: 2 814 B / 5 blokk
Mindet a futó eszközlánc építette és a füstvizsgát zölden hozta.

| # | Csomag | Forrás | Méret | Állapot |
| ---: | --- | --- | ---: | --- |
| — | ALAPMAG (rezidens) | `tudas/alapcorpus.txt` + motor-KBTAB | 451 B | ✅ betöltött (B4 blokk) |
| 1 | SCIENCE | `tudas/science.txt` | 451 B | ✅ lefordítva, kazettán (B5) |
| 2 | HEALTH | `tudas/health.txt` | 313 B | ✅ lefordítva (bármelyik újraépített kazettára betehető) |
| 3 | RETRO | `tudas/retro.txt` | 340 B | ✅ lefordítva (bármelyik újraépített kazettára betehető) |

## További tervezett csomagok (a trening-útmutatóval elkészíthetők)

- astronomy (csillagászat) · cooking (gasztronómia) · entertainment
  (szórakozás) · retro-tech · futurewatch (jövőkutatás) · learning
  (tanulás) · hobby · literature (irodalom) · movies (filmek) · celebrities
  (hírességek) · art (művészet) · work (munka) · ufo

*(A magyar nyelvű csomagok a kiforrott modell után jönnek — lásd
`01-nyelvvaltas-dontes.md`.)*

## Általános mértékadó szabály

Egy csomag max. **1536 bájt**; ha nagyobb, szekciókra bontjuk (07-es
SZAKASZ-típus, a 2. fázisbeli .T81-formátum szerint) és kétmenetben töltjük.
