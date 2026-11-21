# Bitmező-térkép — PROFIL és EMLÉKEZET (2. fázis)

**Egy bájt, egy bájtban élő bitek:** minden kétállapotú információ 1 biten él.
Szabály: a két legfelső bit (bit7, bit6) minden flag-bájtban **0-ra fixált
biztonsági bit** — így a flag-bájt értéke soha nem lépi át a `0x3F`-et,
garantáltan nem tud összeállni a `0x76`-tal.

---

## 1. PROFIL (0x4100–0x41FF, 256 bájt, védett)

| Eltolás | Tartalom | Jegyzet |
| ---: | --- | --- |
| 0x00 | mágikus bájt `0xC3` | ha nem ez, a PROFIL üres → profil-kérdezés indul |
| 0x01–0x06 | dátum/óra pontos másolat: év, hónap, nap, óra, perc (5 B) + ellenőrző | az induláskor beírt pontos idő |
| 0x08–0x17 | felhasználónév (16 bájt, ZX81-biztos karakterek, 0-val zárva) | |
| 0x18 | születési év (bájt, 1900-tól eltolva) | pl. 85 = 1985 |
| 0x19 | születési hónap (1–12; 0 = nem adta meg) | |
| 0x1A | születési nap (1–31; 0 = nem adta meg) | |
| 0x1B | FLAG-A (lásd 1.1) | |
| 0x1C | FLAG-B (állapot-bitek, lásd 1.2) | |
| 0x1D | hőmérséklet-beállítás (1–4, felső bitek nullázva) | |
| 0x1E–0x1F | XOR-ellenőrző + árnyék-zászló bájt | lásd 3. szakasz |
| 0x20–0x21 | FLAG-B dátumbélyeg: nap, hónap (minden FLAG-B bit egyszerre jelződik) | |
| 0x22–0x23 | utolsó MENT dátumbélyege: nap, hónap | |
| 0x24–0xFF | tartalék (~220 B) | utólagos bővítés (a mesterprompt 50–150 B szabályán felül) |

### 1.1 FLAG-A (0x1B) — személyes beállítások

| Bit | Név | 0 érték | 1 érték |
| ---: | --- | --- | --- |
| 0 | NEM | férfi | nő |
| 1 | KOR | gyerek | felnőtt |
| 2 | ÚTMUTATÓ | még kéri | már látta/átugorta |
| 3 | TURBO_TAPE | ki (alapért.) | be (csak teszt) |
| 4 | REASONING-jelzés | rejtett | látszik |
| 5 | EMLÉKEZTETŐ engedélye | ki | be |
| 6–7 | BIZTONSÁG | mindig 0 | mindig 0 |

### 1.2 FLAG-B (0x1C) — állapot-bitek (dátumbélyeg: 0x20–0x21)

| Bit | Jelentés | 0 | 1 |
| ---: | --- | --- | --- |
| 0 | fejfájás | nincs | fáj |
| 1 | általános rosszullét | nincs | van |
| 2 | hangulat: jó | nem | igen |
| 3 | vita zajlik | nem | igen |
| 4 | vitában a PIOCO álláspontja | ZX81 mellett* | PC mellett* |
| 5–7 | BIZTONSÁG | mindig 0 | mindig 0 |

\*) a bit csak akkor számít, ha bit3 = 1; a téma maga a CHAT-beli
vita-rekordból jön (lásd `05-agent-parancsok-es-chat-formatum.md`).

## 2. EMLÉKEZET-bitrekordok (a CHAT zóna végén, leltár-lista)

Minden rögzített kétállapotú tény egy 4 bájtos rekord:

```
bájt0: bitkód (0–31: melyik bit; a két felső bit 0)
bájt1: érték (0/1) + elavulás-riasztás jelző bit7
bájt2–3: dátumbélyeg ( nap, hónap )
```

- **Elavulási szabály:** ha a rögzítés napja és a mai nap között több mint
  14 nap telt el, VAGY a felhasználó azt mondja, hogy "elmúlt", a
  rekord érték-bitje nullázódik, bit7 jelzi az elavulást, és a rekord
  újrahasznosítható.
- A rekordok soros, 4 bájtos lépésben férnek el; leltárlista címét a motor
  tartja nyilván a MUNKATERÜLET-ben.

## 3. 0x76-biztonság — árnyék-zászló mechanizmus

1. Flag-bájt képzése után a motor ellenőrzi: ha az érték `0x76` lenne
   (a bit7/bit6 nulla miatt elvileg lehetetlen, de a kettős ellenőrzés így is megmarad),
   az első biztonsági bitet 1-re fordítja és az árnyék-zászló bájt
   megfelelő bitjét beállítja.
2. D_FILE-ba írásnál a maszk-rutin minden bájtját a **saját engedélyezési
   táblázatán** futtatja (nem tiltólista, hanem **engedélyező lista**:
   szóköz, egyszerű karakterek, grafikuskészlet, inverz változatok — csak ami
   a táblázatban van, az mehet ki).
3. Mentéskor a nyers nyers flag-bájtok soha nem mennek kiírásra — csak a
   CHAT szöveg komponensek, mind maszkolva.

---
*Rendelkezésre áll a 3. fázishoz: a táblázatok közvetlenül Z80-konstansokká
fordíthatók (.DEFINE sorok).*
