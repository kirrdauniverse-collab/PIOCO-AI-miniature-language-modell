# MISTRAL — fejlesztői munkaterület

Ez a **MISTRAL** fejlesztési munkaterület a PIOCO AI miniature language modell projektben
(a korábbi `GLM/` elnevezés helyett — a tulaj kérése alapján).

Ide kerül az általam készített tervezési és fejlesztési anyag, fázisonként, mappákba
rendezve. A repó gyökerében lévő `docs/`, `motor/`, `eszkozok/`, `tudas/`, `kazetta/`
mappák a **kanonikus, véglegesített** projektstruktúrát hordozzák; a `MISTRAL/`
munkaterületből kerülnek oda a jóváhagyott részek.

```
MISTRAL/
├── fazis-1-otlet-es-koncepcio/            koncepció, memória/0x76, agent-viselkedés, fázisterv
├── fazis-2-tervezes-es-dizajn/            memóriatérkép, .T81 formátum, bitmezők, képernyők, chat
└── fazis-3-kodolas-es-csomagolas/         motor (Z80), eszközök, PIOCO.T81, tesztek
└── fazis-4-tudas-trening-teszt/           nyelvváltás, trening, emulátorteszt-terv, csomagok, emlékezet
```

## Célplatform

- **Elsődleges:** Sinclair ZX81, 16 KB RAM, Z80 @ 3,25 MHz, `.T81` kazetta (multiload)
- **Távlati portok (most nem építünk rájuk):** Spectrum 48/128, Commodore 16/64/128,
  Amiga 500/1200, TVC 64, Enterprise 128, Primo 32, HT1080Z

## Nyelvi döntés

A 4. fázistól a prototípus **angol nyelven** fut (tömörebb szótár:
129 token / 852 B, ASCII-only, több szó fér be) — a magyar finomítás a
kiforrott modell után, motor-átírás nélkül:
`fazis-4-tudas-trening-teszt/01-nyelvvaltas-dontes.md`.

## Munkamódszer

- A tulaj nem másolgat kódot: minden kész működő eredmény repóba kerül.
- Fázisonként áttekinthető dokumentumok, rövid, tárgyilagos jelezéssel, ha a 16 KB
  valahol szűkös — mindig konkrét, működő alternatívával.
- Minden fenti mappához (motor, szótár, chat, tudás) 50–150 bájt tartalék tartozik.

## Jelenlegi állapot (v2.4)

- `PIOCO.T81`: **7219 B / 8 blokk** — BOOT, MOTOR (3976 B), TADAT (245 B),
  SZÓTÁR (1828 B = szótár + bigramm + **trigramm**), ALAPMAG, CSOMAG,
  EMLÉKEZET, TARTALEK (új, 0x7E00, 92 B)
- Szótár **140 token / 924 B**, bigrammtábla **791 B / 229 átmenet**
  (4 bites súly, csoport-végjellel), **trigrammtábla 113 B / 16 kulcs / 32
  követőadat**
- Új a v2.4-ben: **trigram-lépés** — `eszkozok/trigram_train.py`, a motorban
  `TRIGOTO` (kulcskeresés) + `TRIINIT` (a bg-fejléc extra eltolásából veszi a
  tri-tábla címét); a generátor trigram-találatnál a trigramm-követőcsoportból
  szavaz, egyébként bigrammal folytat. Javítva a v2.2 óta lappangó két hiba:
  BGCHOOSE A-regiszter-clobbering és szellemt átmenetek a csoport-végjel
  hiányában (mostantól minden páros csoport után 0x00 végjel van).
  Részletek: `eszkozok/trigram_train.py`, `motor/pico.asm` (TRIGOTO/TRIINIT)
- Motor-tartalék: **120 B** (a 4096-os zónahatárig); a következő adat-bővítések
  már a TADAT/TARTALEK zónákba mennek, nem a motorba
- Következő lépés: emulatoros teszt a generálandó válaszminőségre, majd
  tudáscsomag-bővítés
