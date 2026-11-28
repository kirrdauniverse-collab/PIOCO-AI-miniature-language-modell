# Emulátoros tesztterv — mit ellenőrizni a ZX81-emulátorban

**Javasolt emulátorok:** eightyone (ZX81-emulátor Windows/Linux), b51,
vagy ox (a vegyes támogatás miatt a 0x76-biztonság itt válik igazán
bizonyítottá).

**Betöltés:** a `kazetta/PIOCO.T81`-t vágd be az emulátor szalag-bemenetére.

---

## Tesztmenet (sorrendben, minden pont pipálható)

### A. Indulás

- [ ] a szalag betölt; a BOOT-blokk fut (még nincs motor-effekt)
- [ ] nincs képernyő-fagyás, képszakadás vagy sérült karaktercsík
- [ ] a PROFIL mágikus bájtja 0xC3-ként inicializálódik (friss 16 KB-ban)

### B. Splash és üdvözlet

- [ ] a splash szöveg látszik: "P I O C O  A I"
- [ ] az üdvözlet a GUEST névvel jön (első futás)
- [ ] a pörgő zóna nem ír parancskódot vagy 0x76-ot a sorokba

### C. Beszélgetés

- [ ] `HELLO` → "Hello there! Nice to meet you." (KB-keresés)
- [ ] `WHAT IS ENERGY` → tudás-válasz a betöltött csomaggal (SCIENCE betöltve)
- [ ] `CAT` gyors válasz (motor-KB)
- [ ] ismeretlen bevitel → "Still learning about that."
- [ ] két futtatás között a válasz-választás teljesen azonos bevitelre
      is variálódhat (R+FRAMES véletlen — a hőmérséklet 1-en ritkábban)

### D. Biztonság (0x76)

- [ ] hosszú, olvashatatlan bevitel (véletlen karakterek) → a képernyő
  érintetlen marad; fagyás nincs
- [ ] 64+ karakteres sor → a védőhatár (62) megállítja

### E. Multiload

- [ ] második blokkból (MOTOR) betöltve a PROFIL-adatok megmaradnak
      (név ugyanaz)
- [ ] TÉMACSOMAG-csere: új csomag betöltése után a régi tények a
      CSOMAGTERÜLET-ből eltűnnek, az újak megtalálhatók

### F. Mentés / Beállítások

- [ ] `MENT` után a CHAT-blokk korrekt módon visszatölthető (06-os típus)
- [ ] FLAG-B bitek elavulása dátumvetéssel a 14 napos szabály szerint
- [ ] SHIFT+1..4 hőmérséklet-váltás után a válaszvariáció megváltozik

## Hibás működés esetén

Jelezd vissza a pont betűjelét (A–F), a jelenséget (mit láttál, mit
vártál) és a betöltött blokk nevét — ebből tudjuk javítani a motort.
