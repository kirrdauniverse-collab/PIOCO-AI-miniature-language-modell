# Fázisterv — PIOCO AI (MISTRAL munkaterület)

A mesterprompt szerint kb. 3–4 fázis; itt a konkrét, követésre alkalmas bontás
ellenőrzőlistával. A kommunikációs szabály: ha a 16 KB valahol szűkös, röviden,
tárgyilagosan jelezzük és működő megoldással haladunk — nem vitatkozunk sorokon.

---

## 1. fázis — Ötlet és koncepció ✅ (ez a dokumentum)

- [x] Koncepció rögzítése (valós generálás, token + toldalék, n-gram + vázak)
- [x] Realitásvizsgálat (mi fér be a 16 KB-ba, mit nem ígérünk)
- [x] Memória-kompromisszumok: multiload + kvantálás + RLE + tartalék (50–150 B/module)
- [x] Kiegészítés beépítése: D_FILE/0x76 maszk, 1 bit/tulajdonság
      (0x76-felülírás-védelem), agent-forgatókönyvek, turbo tape inaktívan
- [x] Vezérlők rögzítése (SHIFT+1..4, SHIFT+9, SHIFT+5/6, SHIFT+S, SHIFT+SPACE)

## 2. fázis — Tervezés, működés és dizájn ⏳ (következik)

- [ ] Végleges memóriatérkép (bájton pontos címtartományok + tartalékok)
- [ ] `.T81` sávstruktúra-formátum (blokkfejlécek, sávtípusok, ellenőrzőösszegek)
- [ ] Bitmező-térkép (PROFIL, EMLÉKEZET: melyik bit melyik tulajdonság)
- [ ] Képernyő-elrendezések: splash, csevegőpanel (inverz fejlécek, thinking sáv),
      útmutató, profil-kérdezőképernyő
- [ ] Agent-parancsok véglegesítése (`RAJZ`, `BASIC`, `EMLÉKEZZ`, `EMLÉKEZTET`,
      `MENT`, `TÖLT`)
- [ ] 0x76-tilalmi maszk pontos értékhalmaza (ehetetlen értékek listája)
- [ ] Chat-history rekordformátum + elavulás-kezelés szabályai

## 3. fázis — Kódolás és csomagolás ⬜

- [ ] Z80 motor (tokenizáló, generátor, reasoning, hőmérséklet, UI, szalag-I/O)
- [ ] PC-s eszközök: tokenizálótanító, csomaggenerátor, `.T81` író/olvasó
- [ ] `.T81` összeállítás (multiload; turbo tape forrásban kikapcsolva)
- [ ] Menet közbeni pontosítások a 16 KB-os valóság szerint

## 4. fázis — Tudásbázis, tréning, tesztelés ⬜

- [ ] Alaptudás-csomag (induláshoz elegendő, egyszerű beszélgetés)
- [ ] Témacsomagok tréningelése (tudomány, gasztronómia, egészség, szórakozás,
      retro korszak/technológia, jövőkutatás, tanulás, hobbi, csillagászat,
      irodalom, filmek, hírességek, művészet, munka, UFO)
- [ ] Tréning-eszköz a projekt utánra is (új csomagok készíthetőségéhez)
- [ ] Emulátoros + gyakorlati ellenőrzés: splash, multiload, PROFIL-megőrzés,
      0x76-mentesség, rajz-összeadás, BASIC-módosítás, emlékeztető, mentés/elavulás

## Szabály, ami minden fázisban él

Minden fő modul/szakasz mellett **50–150 bájt tartalék**; ha a 16 KB valahol
szűkös, jelezzük és konkrét, működő alternatívát adunk (részletes bontás a
`02-memoria-es-tombszabalyok.md`-ben).
