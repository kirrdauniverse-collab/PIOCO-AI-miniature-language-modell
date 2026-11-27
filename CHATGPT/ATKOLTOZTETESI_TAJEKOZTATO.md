# ChatGPT munkaterület — részleges költözési tájékoztató

**Dátum:** 2026-11-27  
**Állapot:** RÉSZLEGES KÖLTÖZÉS — a régi források megőrzendők

A ChatGPT-oldali PIOCO AI dokumentáció és referenciafájlok külön, sorszámozott munkaterületbe kerültek:

- **Új cél:** `kirrdauniverse-collab/micro-ai-models-for-retro-computers`
- **Új útvonal:** `chatgpt/zx-81/chatgpt-3/`
- **Munkához tartozó ág:** `migration/chatgpt-3-pio-co-ai-zx81`
- **Áttekintés:** https://github.com/kirrdauniverse-collab/micro-ai-models-for-retro-computers/pull/1

A régi `CHATGPT/` könyvtár hét UTF-8 fájlját átmásoltuk az új `legacy-chatgpt/` könyvtárba. Mind a hét célfájl Git blob SHA-azonosítója egyezik az eredeti forrásfájl SHA-jával.

## Fontos korlátozás

A PICO AI-hoz tartozó két további bináris állomány (`.T81` kazetta és build ZIP) még nincs feltöltve az új GitHub-munkaterületre. Ezeket külön folytonossági csomagban megőriztük; a bináris GitHubra másolása és ellenőrzése még hátravan.

Ezért a költözés **nem tekinthető teljesnek**. Az új munkaterület dokumentációja és a hét átmásolt fájl ellenőrzött, de a régi könyvtár maradjon meg változatlan történeti példányként, amíg a bináris átadás és a végső ellenőrzés nem zárul le.

## Megőrzési szabály

- A régi repóban semmit ne törölj, ne nevezz át és ne írj felül.
- A régi fájlok maradjanak rendelkezésre álló kontrollpéldányként.
- A GLM, Grok és más modellek könyvtárai nem részei ennek a ChatGPT-költözésnek, és nem módosíthatók e tájékoztató alapján.
- A folytatás az új `chatgpt-3` munkaterületben történjen, de a bináris migráció befejezéséig a régi forrás továbbra is szükséges hivatkozási alap.

**Ez a tájékoztató nem jelent törlési vagy archiválási engedélyt.**
