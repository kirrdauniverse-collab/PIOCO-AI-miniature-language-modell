# Képernyő-elrendezések és vezérlők (2. fázis)

Képernyő: **32 × 24 karakter**. Minden kiírás a 0x76-maszk engedélyező
táblázatán megy át (lásd `03-bitmezo-terkep.md` 3. szakasz).

---

## 1. Splash (bejelentkező kép, Sáv 1)

```
0 ─────────────────────────────
   ▓▒░ (pörgő karakter-zóna, 2 sor) ░▒▓

          P I O C O  A I
   miniatűr generáló nyelvi modell
        ZX81 · 16 KB RAM · 2026

   Saját dátum, óra, név, nem és
   születési adat betöltése következik.

   Ha gépelési útmutatót kér:  U
   Tovább:                     SPACE
23 ─────────────────────────────
```

- A pörgő karakter-zóna a D_FILE felső harmadának **első 8 oszlopában** fut;
  csak engedélyezett kódokat válogat.
- A profil-kérdezés eredménye a PROFIL-ba kerül (védett blokk).

## 2. Csevegőpanel (fő képernyő)

```
0 ─────────────────────────────────
   ▓ pörgő zóna / státusz (2 sor) ▓
   [KEZDŐ: 12:41  T:18  V:0.3s]
   na, tényleg gondolkodsz, vagy csak vársz?
   [PIOCO: 12:41  T:52  V:1.1s]
   Nem siettetlek — 3,25 MHz-en a
   gondolkodás is versenyt fut...
   ▓ GONDOLKODOM… (thinking sáv) ▓
22 ─────────────────────────────────
   INPUT-line (ROM INPUT, karakteres mód)
```

- **Inverz fejléc** minden üzenetnél (felhasználó és modell egyaránt):
  órabélyeg + felhasznált tokenek (`T:`) + válaszidő (`V:`).
- **Thinking sáv:** `GONDOLKODOM…` jelzés a reasoning fázis alatt
  (SHIFT+9-gyel ki/be — FLAG-A bit4).
- **Görgetés:** SHIFT+5 vissza, SHIFT+6 előre — a CHAT rekordlistán lépdel,
  nem a D_FILE-t másolja újra.
- **INPUT:** a ZX81 ROM karakteres INPUT rutinja; a beírt sor tokenhosszát
  a motor számolja, a fejlécbe kerül.

## 3. Vezérlők (végleges)

| Beállítás | Billentyű | Tárolás |
| --- | --- | --- |
| Hőmérséklet 1–4 | `SHIFT+1..4` | PROFIL 0x1D |
| Reasoning jelzés ki/be | `SHIFT+9` | FLAG-A bit4 |
| Görgetés vissza/előre | `SHIFT+5` / `SHIFT+6` | nem tárolt (utas) |
| Mentés kazettára | `SHIFT+S` | PROFIL 0x22–0x23 bélyeg |
| Válasz/gondolkodás megszakítása | `SHIFT+SPACE` | nem tárolt |
| Turbo tape ki/be | `M TURBO` parancs | FLAG-A bit3 (alap: ki) |

## 4. D_FILE-használat szabályai

- Felső harmad (0–7. sor): pörgő zóna + státusz; a motor ez sorokat
  "munkaterületként" is jelöli — de csak a maszkolt értékekkel ír.
- Középső rész (8–21. sor): csevegőpanel.
- Alsó sor (22–23.): INPUT-line + státusz.
- Sorrögzítő szabály: minden sorvége normál sorlezáró `0x76` — az csak
  a sorvég-jelölés helyén állhat, tartalmi bájt soha.
