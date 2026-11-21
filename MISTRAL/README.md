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
└── fazis-4-tudas-trening-teszt/           nyelvváltás, trening, emulátorteszt-terv, csomagok
```

## Célplatform

- **Elsődleges:** Sinclair ZX81, 16 KB RAM, Z80 @ 3,25 MHz, `.T81` kazetta (multiload)
- **Távlati portok (most nem építünk rájuk):** Spectrum 48/128, Commodore 16/64/128,
  Amiga 500/1200, TVC 64, Enterprise 128, Primo 32, HT1080Z

## Nyelvi döntés

A 4. fázistól a prototípus **angol nyelven** fut (tömörebb szótár:
111 token / 740 B, ASCII-only, több szó fér be) — a magyar finomítás a
kiforrott modell után, motor-átírás nélkül:
`fazis-4-tudas-trening-teszt/01-nyelvvaltas-dontes.md`.

## Munkamódszer

- A tulaj nem másolgat kódot: minden kész működő eredmény repóba kerül.
- Fázisonként áttekinthető dokumentumok, rövid, tárgyilagos jelezéssel, ha a 16 KB
  valahol szűkös — mindig konkrét, működő alternatívával.
- Minden fenti mappához (motor, szótár, chat, tudás) 50–150 bájt tartalék tartozik.
