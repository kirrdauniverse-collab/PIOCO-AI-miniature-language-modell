# Trening-útmutató — új tudáscsomag készítése (kódírás nélkül)

Ez a leírás neked szól: **egy szövegfájl és három parancs** ennyi az egésze
egy új témacsomagnak. A tréning PC-n fut, az eredmény bináris csomag lesz,
amelyet a `.T81`-építő a CSOMAGTERÜLET-re tölt.

---

## 1. Készítsd el a forrást

Hozz létre egy fájlt a `tudas/` mappában, például `astronomy.txt`.
Formátum (fejléc): az első két sor magyarázat — a fordító **tabulátort** tartalmazó
sorokat olvas, a többit kihagyja.

```
ASTRONOMY theme package...
<keyword><TAB><fact text>
telescope	A telescope collects light with a lens or a mirror.
mars	Mars is the fourth planet; its red color comes from iron oxide.
saturn	Saturn has rings made mostly of ice and rock.
```

## Szabályok (mindet a fordító betartat)

- **kulcsszó** — egy szó, apró betűknél angol; ez a KB-keresés kulcsa.
- **tényszöveg** — legfeljebb kb. 100 karakter; tömör mondat.
- A csomag **max. 1536 bájt** lehet (a CSOMAGTERÜLET zóna mérete) — a
  fordító erre figyelmezeti, ha túlvagod.
- Biztonsági automatika: a 0x76-tilalmi és 0xC0+ bájtok
  biztonságos cserekarakterre (0x1B) cserélődnek.

## 2. Fordíts csomagná

```
python3 eszkozok/kb_compile.py tudas/astronomy.txt kazetta/astronomy.bin
```

## 3. Építsd be a kazettába

Válaszd ki, melyik csomag kerüljön a kazettára (felülírja az előzőt):

```
python3 eszkozok/t81_build.py kazetta/motor.bin kazetta/szotar.bin kazetta/science.bin \
        kazetta/PIOCO.T81 kazetta/astronomy.bin ASTRONOMY
python3 tesztek/ellenorzes.py kazetta/motor.bin kazetta/szotar.bin kazetta/PIOCO.T81
```

Ha az ellenőrzés "MINDEN ELLENŐRZÉS RENDBEN"-et ír, a csomag beépítve van.

## 4. Szó-hozzáadás (tokenizálás)

Ha a csomag ÚJ szavakat hoz (pl. "telescope", "mars"), told hozzá őket az
`alapcorpus.txt`-hez (egyszerű szólista), és tréningeld újra a szótárt:

```
python3 eszkozok/tokenizer_train.py tudas/alapcorpus.txt kazetta/szotar.bin
```

Így a modell az új szavakat tokenként is felismeri.
