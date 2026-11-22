; ============================================================
; PIOCO AI — Z80 motor (4. fázis, v2)
; Cél Sinclair ZX81, 16 KB RAM
; Memóriatérkép: MISTRAL/fazis-2-tervezes-es-dizajn/01-memoria-terkep.md
;
; v2 újdonságok a v1-hez képest:
;  - 8 soros, teljes ZX81-billentyűtérkép (ENTER + SHIFT-bit),
;    port 0xFE, sorkiválasztás; minden leütés felengedés után adódik
;  - SHIFT-vezérlők: SHIFT+1..4 hőmérséklet, SHIFT+9 érvelés ki/be,
;    SHIFT+S mentés-stub, SHIFT+SPACE sor-megszakítás
;  - token-alapú generátor (bigramm, 1 bájt = 2 darab 4 bites súly,
;    hőmérséklet szerinti szavazás) a v1 vázlatszövegei helyett
;  - ALAPMAG-lánc keresés (0x6C00-on betöltött tudáscsomag) +
;    beépített KBTAB-tartalék
;
; NYELVI DÖNTÉS: a prototípus ANGOL nyelven fut (kevesebb bájt,
; ASCII-only); a magyar nyelvi finomítás a kiforrott modell után.
;
; v2.1 új: EMLÉKEZET (06 blokk, 0x6700) — 4 bájtos emlékrekordok,
; dátum-bekérés induláskor, fakt-felismerés, 14 napos elavulás,
; SHIFT+S mentés (PROFIL dátumbélyeg + későbbi kazetta-írás).
;
; v2.2 új: CHAT-napló (0x6001) inverz fejlécekkel (m:ss, token,
; generálási másodperc), SHIFT+5/6 görgetés; a nyomtatómag
; sor-/oszlopkurzoros — a hosszú sorok már nem írják felül a
; 0x76-orterminátorokat, és a 23. sornál a kép felfelé görget.
;
; v2.3 új: NAPTÁR és KÉPZELET — év-bekérés (PROF_YR, 0xFF = nincs),
; DOWGET héttag-számítás (Zeller-egyszerusités 2000-2099, TAB13 táblával;
; 36525 dátumra brute-force ellenőrizve), "what day" (intent 6) és
; "what time" (intent 7) válaszok; KÉPZELET-modul (IF/WOULD/COULD/WISH
; felismerés -> véletlen IMAGSEED-token a generátor indításakor);
; FACTTAB kiegészítés (SLEEP/TIRED/HUNGRY/ANGRY); statikus táblák a
; motorzónán kívül, TADAT blokkban (0x6B00, motor/tadat.asm).
; Motor: 4052 B (tartalék 44 B), TADAT: 125 B.
;
; v2.5 ÚJ (C/6 javítás): a kazetta a VALÓDI ZX81 ROM SAVE-képet használja
; (single image, 0x4009..E_LINE), a motort a '10 RAND USR 18176' launcher
; sor indítja. Ennek következményei:
;  - FRAMES javítva: a ROM a DISPLAY-1 (0x0229) közben a 0x4034 számítót
;    minden képkockán CSÖKKENTI (a 0x4025 a LAST_K volt!); eltelt idő =
;    BOOTFR - FRAMES (SNAPFR pillanatkép alapján).
;  - a motor a ROM D_FILE rendszerváltozójából (0x400C) veszi a képernyő
;    báziscímét (DFPTR), az írás a ROM képernyőzónájába megy; így a
;    kép a LOAD "" utáni ROM-állapotba illeszkedik.
;  - PROFIL 0x7E00 (az image-en kívül esik: E_LINE = 0x7F00).
; ============================================================

; ---- Zónák (fázis-2 memóriatérkép) ----
SYSVARS     EQU 0x4000
FRAMES      EQU 0x4034        ; 50 Hz óraszámító 2 B; a ROM DISPLAY-1 (0x0229)
                              ; minden képkockán CSÖKKENTI -> eltelt = BOOTFR - FRAMES
DFSYSV      EQU 0x400C        ; D_FILE rendszerváltozó (képernyő-báziscím)
PROFIL      EQU 0x7E00        ; PROFIL védett blokk (256 B; az image-en KÍVÜL)
MOTORBASE   EQU 0x4700        ; motor-zóna 0x4700..0x56FF = USR 18176 belépés
SZOTAR      EQU 0x5800        ; v2.6: szótár-zóna 0x5800..0x5FFF (a motor-zóna 0x4700..0x57FF)
KB_BASE     EQU 0x6C00        ; ALAPMAG: betöltött tudáslánc (kb_compile)
CHAT        EQU 0x6000
CHATM       EQU 0x6000           ; napló-mágnes (0xA5)
CHATM0      EQU 0x6001           ; itt indul az első rekord
; rekord: [fejléc][0][szöveg][0]
MUNKAT      EQU 0x6800
KB2T        EQU 0x7C00        ; v2.6: KB2-lánc (0x7C00..0x7CFF, 256 B)
TARTALEK    EQU 0x7D00
VEREMTOP    EQU 0x7FFF
TADAT       EQU 0x6B00        ; fix adattabla-blokk: PB-buferek es ALAPMAG kozott
TAB13       EQU TADAT         ; honap-index tabla (tadat.asm, T81 blokk tolto)
DOWTAB      EQU TADAT+0x0F    ; napnevek (4 bajt/nap)
TXTDAYP     EQU TADAT+0x2B    ; "it's "
TXTTIS      EQU TADAT+0x31    ; "time is "
WTAB        EQU TADAT+0x3A    ; "what day" szo-tabla
TIMTAB      EQU TADAT+0x46    ; "what time" szo-tabla
IMAGTAB     EQU TADAT+0x4C    ; kepzelet-aktivator tabla
IMAGSEED    EQU TADAT+0x61    ; kepzelet-indito szavak

; ---- PROFIL eltolások ----
PROF_NAME   EQU PROFIL+0x08
PROF_FLAGB  EQU PROFIL+0x1C
PROF_TEMP   EQU PROFIL+0x1D
; EMLÉKEZET dátumbélyegek a PROFILban (védve a betöltésektől)
PROF_FBDAY  EQU PROFIL+0x20      ; FLAG-B utolsó állításának napja
PROF_FBMON  EQU PROFIL+0x21      ; FLAG-B utolsó állításának hónapja
PROF_SVDAY  EQU PROFIL+0x22      ; utolsó MENTÉS napja
PROF_SVMON  EQU PROFIL+0x23      ; utolsó MENTÉS hónapja
PROF_DDAY   EQU PROFIL+0x24      ; aktuális dátum: nap (betöltéskor kérve)
PROF_DMON   EQU PROFIL+0x25      ; aktuális dátum: hónap
PROF_YR     EQU PROFIL+0x26      ; év utolsó két számjegye (0..99; 0xFF = nincs)

; ---- EMLÉKEZET zóna (CHAT vége előtt, 06 blokk célcíme) ----
EMSTORE     EQU 0x6700
EMMCNT      EQU EMSTORE+1        ; rekordszám (max 63)
EMREC0      EQU EMSTORE+2        ; első 4 bájtos rekord
; rekord: [bitkód 0..31][érték 0/1 + bit7 elavulás][nap][hónap]

; ---- Munkaterület puffer-alap ----
PB          EQU MUNKAT
BLINE       EQU PB+0x00       ; beviteli sor (64 B)
LINELEN     EQU PB+0x40
TOKBUF      EQU PB+0x48       ; token-ID-k (64 B)
TOKCNT      EQU PB+0x88
INTENT      EQU PB+0x89
DFROW       EQU PB+0xA0       ; kurzor sor (0..23)
DFCOL       EQU PB+0xA1       ; kurzor oszlop (0..31)
THINKFLG    EQU PB+0xA2
RNDSEED     EQU PB+0xA3
SHIFTF      EQU PB+0xA4       ; SHIFT lenyomva (GETKEY állítja)
RESP        EQU PB+0xB0       ; 32 bájtos válasz-puffer
RESPW       EQU PB+0xD0       ; 2 bájt: RESP írókurzor
BIGR        EQU PB+0xD2       ; 2 bájt: bigramm-tábla címe
ATTN        EQU PB+0xD4       ; fókusz-token (első szótári szó a sorban)
BGFROM      EQU PB+0xD5       ; bigramm-járás aktuális tokenje
NTTOK       EQU PB+0xD6       ; NXTENT: aktuális token dolgozóterülete
BESTT       EQU PB+0xD7       ; max-választás: legjobb token
BESTW       EQU PB+0xD8       ; max-választás: legjobb súly
RTARGET     EQU PB+0xD9       ; rulett: maradék cél-érték
NCOUNT      EQU PB+0xDA       ; CNTSUM: szavazók száma
WSUM        EQU PB+0xDB       ; CNTSUM: összsúly
DAPPID      EQU PB+0xDC       ; DICTAPP: keresett token-ID
PAR         EQU PB+0xDD       ; bigramm-párolvasás párossága (0/1)
ABRT        EQU PB+0xDE       ; megszakítás-jelző (SHIFT+SPACE)
DAYNOW      EQU PB+0xDF       ; aktuális nap (1..31)
MONNOW      EQU PB+0xE0       ; aktuális hónap (1..12)
EMLBIT      EQU PB+0xE1       ; FACTSET/EMSET: aktuális bitkód (0xFF = nincs)
EMLVAL      EQU PB+0xE2       ; EMSET: érték (0/1)
DOYNOW      EQU PB+0xE3       ; DOY30: nap-index az év elejétől
TMPW        EQU PB+0xE4       ; TMPHDR írópointer
ELAPS       EQU PB+0xE5       ; utolsó generálás eltelt másodperce
TOKSET      EQU PB+0xE6       ; a sorhoz tartozó token darabszám
GENCTR      EQU PB+0xE7       ; BGWORD hívások számlálója (max 99)
CHATW       EQU PB+0xE8       ; 2 bájt: CHAT-napló írópointer
FRSNAP      EQU PB+0xEA       ; 2 bájt: FRAMES-pillanatkép (GÉNESZ előtt)
HNDEX       EQU PB+0xEC       ; history-browser: mutatott üzenet sorszáma
CDIR        EQU PB+0xED       ; üzenet iránya: 0 = YOU, 1 = PIOCO
CMSG        EQU PB+0xEE       ; 2 bájt: tárolandó üzenet címe
TMPHDR      EQU PB+0xF0     ; 20 bájt: összerakott fejléc (0-zárt)
DFPTR       EQU PB+0x110    ; 2 bájt: ROM D_FILE báziscím (START-ból olvassa)
BOOTFR      EQU PB+0x112    ; 2 bájt: FRAMES-pillanat a teljes bekapcsoláskor
IMAGF       EQU PB+0xA5     ; képzelet-modul: jelző (REASON állítja)
IMAGSEEDT   EQU PB+0xA6     ; indító-token (BGWRITE induláskor elfogyasztja)
TRP2        EQU PB+0xA7     ; trigramm-kulcs elso fele (ketto valtast ezelott)
TRISET      EQU PB+0xA8     ; TRIGOTO talalat-jelzo (0/1)
TRIDE       EQU PB+0xA9     ; 2 bajt: trigramm koveto-csoport cime
TRIB        EQU PB+0xAB     ; 2 bajt: trigramm-tabla cime (0 = nincs)
FACTTAB     EQU TADAT+0x7D    ; fakt-kulcsszavak (tadat.asm)
NEGTAB      EQU TADAT+0xCC    ; tagnado szok (tadat.asm)
CLRTAB      EQU TADAT+0xD4    ; megszunes-jelzo szok (tadat.asm)
TXTNOTED    EQU TADAT+0xED    ; "[noted]" (tadat.asm)
ASKH        EQU 0x7D00        ; emlék-rákérdezés (tartalek.asm)
ASKS        EQU 0x7D1E
TXTDUNNO    EQU 0x7D39
TXTABORT    EQU 0x7D54

        ORG MOTORBASE

; ================= INDULÁS =================
START:
        LD SP,VEREMTOP
        LD HL,(DFSYSV)          ; ROM D_FILE báziscím -> a képernyő-írások ide
        LD (DFPTR),HL
        LD HL,(FRAMES)
        LD (BOOTFR),HL          ; FRAMES lefelé számol, eltelt = BOOTFR - FRAMES
        XOR A
        LD (THINKFLG),A
        LD (RNDSEED),A
        LD A,(FRAMES)
        LD (RNDSEED),A
        LD A,(PROFIL)           ; mágikus bájt
        CP 0xC3
        JR Z,PROFOK
; üres PROFIL: alapértelmezések (a személyes kérdezés később, INPUT-tal)
        LD A,0xC3
        LD (PROFIL),A
        LD HL,DEFNAME
        LD DE,PROF_NAME
        LD BC,8
        LDIR
        XOR A
        LD (PROFIL+0x18),A
        LD (PROFIL+0x19),A
        LD (PROFIL+0x1A),A
        LD A,0x02
        LD (PROFIL+0x1B),A      ; FLAG-A: felnőtt
        XOR A
        LD (PROF_FLAGB),A       ; FLAG-B: minden állapotbit 0
        LD A,0x02
        LD (PROF_TEMP),A
        LD A,0xFF
        LD (PROF_YR),A          ; év: nincs meg (0xFF = jelző)
PROFOK:
        CALL BIGRBASE           ; bigramm-tábla címének kiszámítása
        CALL EMINIT             ; emlékezetzóna mágnes-ellenőrzés + dátumvétel
        CALL CLRSCR
        LD HL,TXTSPLASH
        CALL PRTLN
        CALL NEWLINE
        LD HL,TXTNAM
        CALL PRTLN
        LD HL,PROF_NAME
        CALL PRTLN
        CALL WAITKEY
        CALL CLRSCR
        LD HL,TXTHELLO
        CALL PRTLN
        CALL DATASK             ; datum-bekeres (nap/ho/ev), ha meg nincs
        CALL BOOTD              ; udbuszas: 'it's <nap> <datum>' kiiras
        CALL OBSSCAN            ; >14 napos emlekek elavultta tetele
        CALL REMCHK             ; releváns emlékre rákérdezés

; ================= FŐCIKLUS =================
MAINLOP:
        LD HL,TXTPROMPT
        CALL PRTLN
        CALL READLINE
        CALL TOKENIZE
        LD A,(TOKCNT)
        LD (TOKSET),A
        XOR A
        LD (ELAPS),A
        XOR A
        LD (GENCTR),A
        XOR A                   ; irány: YOU
        LD HL,BLINE
        CALL CHATADD            ; fejléc + sor a CHAT-naplóba és képernyőre
        LD A,(THINKFLG)
        OR A
        JR Z,NOSHOW
        LD HL,TXTTHINK
        CALL PRTLN
        CALL NEWLINE
NOSHOW:
        CALL SNAPFR
        CALL REASON
        CALL FACTSET
        CALL GENERATE
        CALL ELAPSEC
        LD A,(GENCTR)
        LD (TOKSET),A
        LD A,1                  ; irány: PIOCO
        LD HL,RESP
        CALL CHATADD
        JR MAINLOP

; ================= KÉPERNYŐ =================
; CLRSCR: 24 sor × (32 szóköz + 0x76-terminátor), majd D_FILE-lezáró 0x76
CLRSCR:
        LD HL,(DFPTR)
        LD B,24
CLRS_R:
        PUSH BC
        LD C,32
        XOR A
CLRS_C:
        LD (HL),A
        INC HL
        DEC C
        JR NZ,CLRS_C
        LD A,0x76               ; sorzáró: CSAK sor végén
        LD (HL),A
        INC HL
        POP BC
        DJNZ CLRS_R
        LD A,0x76               ; D_FILE lezárása
        LD (HL),A
        XOR A
        LD (DFROW),A
        LD (DFCOL),A
        RET

; CALCUR: HL = DFILE + 33×sor + oszlop (a kurzor tiszta címe);
; A megmarad (a hívó PUTA a karakter-kódot A-ban tartja)
CALCUR:
        PUSH AF
        PUSH DE
        LD A,(DFROW)
        LD L,A
        LD H,0
        LD D,H
        LD E,L
        ADD HL,HL
        ADD HL,HL
        ADD HL,HL
        ADD HL,HL
        ADD HL,HL               ; 32×sor
        ADD HL,DE               ; 33×sor
        LD DE,(DFPTR)
        ADD HL,DE
        LD A,(DFCOL)
        LD E,A
        LD D,0
        ADD HL,DE
        POP DE
        POP AF
        RET

; PUTA: A = már konvertált ZX81-kód kiírása; a 32. oszlopot nem lépi
; túl — sortörést és görgetést végez
PUTA:
        CP 0x76
        RET Z
        CP 0xC0
        RET NC
        PUSH DE
        CALL CALCUR
        LD (HL),A
        POP DE
        LD A,(DFCOL)
        CP 31
        JR NC,PUTA_N
        INC A
        LD (DFCOL),A
        RET
PUTA_N:
        CALL NEWLINE
        RET

; SCRUP: a 23 sor tartalmát eggyel felfelé, az utolsó sor üres lesz
SCRUP:
        PUSH BC
        LD HL,(DFPTR)
        LD D,H
        LD E,L                  ; DE = D_FILE bázis
        LD BC,33
        ADD HL,BC               ; HL = D_FILE + 33
        LD BC,759
SCR_L:
        LD A,(HL)
        LD (DE),A
        INC HL
        INC DE
        DEC BC
        LD A,B
        OR C
        JR NZ,SCR_L
        LD B,32
SCR_C:
        XOR A
        LD (DE),A
        INC DE
        DJNZ SCR_C
        LD A,0x76
        LD (DE),A
        POP BC
        RET

; PRTLN: HL = 0-val lezárt szöveg, biztonsági maszkon át a D_FILE-ra
PRTLN:
        LD A,(HL)
        OR A
        RET Z
        PUSH HL
        CALL SAFEPCHR
        POP HL
        INC HL
        JR PRTLN

; SAFEPCHR: A = ASCII -> ZX81-kód; 0x76 és 0xC0+ tiltva
SAFEPCHR:
        PUSH HL
        CALL ASC2ZX
        POP HL
        CALL PUTA
        RET

; PRTINV: HL = 0-val lezárt szöveg inverzen (ZX81 bit7);
; csak a 0x00–0x3F tartomány invertálható biztonságosan
PRTINV:
        LD A,(HL)
        OR A
        RET Z
        PUSH HL
        CALL ASC2ZX
        CP 0x40
        JR NC,PI_P
        OR 0x80
PI_P:   CALL PUTA
        POP HL
        INC HL
        JR PRTINV

; ASC2ZX: ASCII(32..127) -> ZX81-kód táblázattal
ASC2ZX:
        PUSH DE
        PUSH HL
        LD DE,ASCTAB
        SUB 32
        LD L,A
        LD H,0
        ADD HL,DE
        LD A,(HL)
        POP HL
        POP DE
        RET

; ================= VÁRAKOZÁS ÉS BEVITEL =================
WAITKEY:
        CALL GETKEY
        OR A
        JR Z,WAITKEY
        RET

; GETKEY: A = karakter vagy 0; SHIFTF-be írja a SHIFT-állapotot;
; minden leütés csak a felengedés után kerül visszaadásra
GETKEY:
        XOR A
        LD (SHIFTF),A
        LD HL,KEYROWS
        LD B,8
GK_R:
        LD A,(HL)
        PUSH HL
        PUSH BC
        LD B,A
        LD C,0xFE
        IN A,(C)
        POP BC
        POP HL
        CPL
        AND 0x1F
        JR Z,GK_NX
GK_HIT:
        PUSH AF                 ; aktív bitek
        LD A,8
        SUB B                   ; sorindex 0..7
        LD D,A
        POP AF
        LD C,0
GK_B:
        RRA
        JR C,GK_BH
        INC C
        JR GK_B
GK_BH:
        ; SHIFT-bájt: 0. sor, 0. bit
        LD A,D
        OR A
        JR NZ,GK_TBL
        LD A,C
        OR A
        JR NZ,GK_TBL
        LD A,1
        LD (SHIFTF),A
        JR GK_NX
GK_TBL:
        ; index = 5*sorindex + bitindex
        LD A,D
        ADD A,A
        ADD A,A
        ADD A,D                 ; 5×sorindex
        ADD A,C                 ; + bitindex
        LD E,A
        LD D,0
        LD HL,KEYTBL
        ADD HL,DE
        LD A,(HL)
        PUSH AF
GK_RL:
        CALL GCLEARED           ; várjuk meg a felengedést
        OR A
        JR NZ,GK_RL
        POP AF
        RET
GK_NX:
        INC HL
        DJNZ GK_R
        XOR A
        RET

; GCLEARED: A = 0, ha semelyik billentyű nincs lenyomva
GCLEARED:
        LD HL,KEYROWS
        LD B,8
GC_R:
        LD A,(HL)
        PUSH HL
        PUSH BC
        LD B,A
        LD C,0xFE
        IN A,(C)
        POP BC
        POP HL
        CPL
        AND 0x1F
        RET NZ
        INC HL
        DJNZ GC_R
        XOR A
        RET

; READLINE: karakteres sorbevitel (ENTER-ig), BLINE/LINELEN
READLINE:
        LD HL,BLINE
        LD C,64
        XOR A
RD_CL:
        LD (HL),A
        INC HL
        DEC C
        JR NZ,RD_CL
        XOR A
        LD (LINELEN),A
        LD (ATTN),A
        LD (ABRT),A
RD_L:
        CALL GETKEY
        OR A
        JR Z,RD_L
        CP 13
        JR Z,RD_DONE
        LD B,A
        LD A,(SHIFTF)
        OR A
        JR Z,RD_CH
        LD A,B
        CALL SHIFTCMD           ; SHIFT+billentyű: vezérlő
        JR RD_L
RD_CH:
; v2.6: a karakter beirasa a BLINE-ba is (BLINE + LINELEN), majd 0-lezaras;
; eddig csak kepernyore ment — igy a REASON/FACTSET/TOKENIZE ures sort latott
        LD A,B                  ; A = kiirando karakter
        PUSH AF
        CALL SAFEPCHR
        POP AF
        LD A,(LINELEN)
        CP 62
        JR Z,RD_L               ; 62 darab karakter utan mar csak nyomtat
        PUSH HL
        PUSH DE
        LD HL,BLINE
        LD E,A
        LD D,0
        ADD HL,DE               ; HL = BLINE + LINELEN
        LD A,B
        LD (HL),A
        INC HL
        LD (HL),0               ; 0-lezaras a beirt karakter utan
        POP DE
        POP HL
        LD A,(LINELEN)
        INC A
        LD (LINELEN),A
        JR RD_L
RD_DONE:
        CALL NEWLINE
        RET

; SHIFTCMD: A = SHIFT+billentyű karaktere; vezérlőket kezel
SCMDTAB:
SC_TAB: db "1",1
        db "2",2
        db "3",3
        db "4",4
        db "5",12
        db "6",13
        db "9",9
        db "S",10
        db " ",11
        db 0
SHIFTCMD:
        PUSH HL
        PUSH DE
        PUSH BC
        PUSH AF
        LD B,A
        LD HL,SC_TAB
SC_L:
        LD A,(HL)
        OR A
        JP Z,SC_X
        CP B
        JR Z,SC_F
        INC HL
        INC HL
        JR SC_L
SC_F:
        INC HL
        LD A,(HL)               ; parancskód
        CP 9
        JR NC,SC_BIG
; 1..4: hőmérséklet
        LD (PROF_TEMP),A
        PUSH AF
        LD HL,TXTTEMPSET
        CALL PRTLN
        POP AF
        PUSH AF
        ADD A,'0'
        CALL SAFEPCHR
        LD A,']'
        CALL SAFEPCHR
        CALL NEWLINE
        POP AF
        POP BC
        POP DE
        POP HL
        RET
SC_BIG:
        CP 9
        JR Z,SC_TOG
        CP 10
        JR Z,SC_SAVE
        CP 12
        JR Z,SC_HB              ; SHIFT+5: history one step back
        CP 13
        JR Z,SC_HF              ; SHIFT+6: history one step forward
        ; 11: megszakítás — sor eldobása
        LD A,1
        LD (ABRT),A
        XOR A
        LD (LINELEN),A
        LD HL,TXTABORT
        CALL PRTLN
        CALL NEWLINE
        POP AF
        POP BC
        POP DE
        POP HL
        RET
SC_TOG:
        LD A,(THINKFLG)
        XOR 1
        LD (THINKFLG),A
        OR A
        LD HL,TXTREASON0
        JR Z,SC_TG2
        LD HL,TXTREASON1
SC_TG2:
        CALL PRTLN
        CALL NEWLINE
        POP AF
        POP BC
        POP DE
        POP HL
        RET
SC_SAVE:
        CALL SAVEMEM            ; dátumbélyeg + később kazetta-írás
        LD HL,TXTSAVED
        CALL PRTLN
        CALL NEWLINE
        POP AF
        POP BC
        POP DE
        POP HL
        RET
SC_HB:
        CALL HISTB
        POP AF
        POP BC
        POP DE
        POP HL
        RET
SC_HF:
        CALL HISTB
        POP AF
        POP BC
        POP DE
        POP HL
        RET
SC_X:
        POP AF
        POP BC
        POP DE
        POP HL
        RET

NEWLINE:
; kurzor a következő sor elejére; a 23. sornál a kép felfelé görget
        PUSH AF
        LD A,(DFROW)
        CP 23
        JR Z,NL_SC
        INC A
        LD (DFROW),A
        JR NL_D
NL_SC:  CALL SCRUP
NL_D:   XOR A
        LD (DFCOL),A
        POP AF
        RET

; ================= TOKENIZÁLÓ =================
TOKENIZE:
        XOR A
        LD (TOKCNT),A
        LD HL,BLINE
        LD DE,TOKBUF
TOK_L:
        LD A,(HL)
        OR A
        RET Z
        CP 32
        JR Z,TOK_SEP
        PUSH HL
        PUSH DE
        CALL DICTLOOK           ; B = token, vagy 0
        POP DE
        POP HL
        LD A,B
        OR A
        JR Z,TOK_CH
TOK_ST: LD A,B
        LD (DE),A
        INC DE
        LD A,(ATTN)             ; fókusz: az első szótári szó
        OR A
        JR NZ,TOK_CNT
        LD A,B
        LD (ATTN),A
TOK_CNT:
        CALL TOKCOUNT
        CALL WORDSKIP
        JR TOK_L
TOK_SEP:
        INC HL
        JR TOK_L
TOK_CH:
; v2.6: szotar-miss utan 'S'-vegzodesu szo: tovere ujra kereses (tobbes alak)
        CALL TOKSTRIP
        LD A,B
        OR A
        JR Z,TOK_FALL
        JR TOK_ST
TOK_FALL:
        CALL CHARFALL
        JR TOK_L

; TOKSTRIP: HL = szó eleje (BLINE-ban); a szotar-miss utan hivandó.
; Ha a szó hossza >= 4 és 'S'-re végződik, a tövére (utolsó karakter
; ideiglenes levágásával) újra DICTLOOK fut; B = token-ID vagy 0.
; HL, DE, BC és a flagok romolhatnak; csak B a kimenet.
; v2.6b javítás: az előző változat kétszer PUSHolta HL-t (a 'S'-ellenőrzés
; előtt is), de csak egyszer popta ki, így a záró RET a mentett DE
; értékére (TOKBUF-pointer) ugrott = wild jump. Új terv: egyetlen
; PUSH/POP pár ('S' visszaállításához), a szó-elejet SBC-vel számoljuk.
TOKSTRIP:
        CALL WORDLEN            ; A = hossz; HL helyben marad; C=romlik
        CP 4
        JR C,TS_R0
        LD B,0
        LD C,A
        DEC C                   ; BC = hossz-1
        ADD HL,BC               ; HL = az utolsó karakter címe
        LD A,(HL)
        CP 'S'
        JR Z,TS_CUT
TS_R0:  LD B,0                  ; nincs töve-vágás -> betű-tokenek jönnek
        RET
TS_CUT:
        LD (HL),0               ; töve vágás a BLINE-ban (ideiglenes)
        PUSH HL                 ; az 'S' helye a visszaállításhoz
        OR A                    ; carry törlése
        SBC HL,BC               ; HL = szó eleje (hossz-1-tel vissza)
        CALL DICTLOOK           ; B = token vagy 0
        POP HL                  ; az 'S' címe visszajön
        LD (HL),0x53            ; 'S' visszaállítása
        RET

TOKCOUNT:
        PUSH HL
        LD HL,TOKCNT
        INC (HL)
        POP HL
        RET

WORDSKIP:
        LD A,(HL)
        OR A
        RET Z
        CP 32
        RET Z
        INC HL
        JR WORDSKIP

; CHARFALL: az aktuális szó betűtokenekre bontása (0x80+c)
CHARFALL:
        LD A,(HL)
        OR A
        RET Z
        CP 32
        RET Z
        ADD A,0x80
        LD (DE),A
        INC DE
        CALL TOKCOUNT
        INC HL
        JR CHARFALL

; DICTLOOK: HL = szó; B = token-ID vagy 0
; szótár: [hossz][karakterek][id] ... vége: 0x00
DICTLOOK:
        PUSH DE
        PUSH HL
        PUSH BC
        LD DE,SZOTAR
        INC DE
        CALL WORDLEN
        LD C,A                  ; C = szóhossz
DL_L:
        LD A,(DE)
        OR A
        JR Z,DL_MISS
        CP C
        JR Z,DL_CMP
DL_STEP:
        LD A,(DE)               ; A = tételhossz (helyreállítás)
        ADD A,2                 ; teljes tétel: [len]+[chars]+[id]
        PUSH BC
        PUSH HL
        LD L,E
        LD H,D
        ADD A,L
        LD L,A
        JR NC,DL_ST
        INC H
DL_ST:
        EX DE,HL                ; DE = következő tétel len-bájtja
        POP HL
        POP BC
        JR DL_L
DL_CMP:
        PUSH HL
        PUSH DE
        PUSH BC
        INC DE                  ; lépés a tétel első karakterére
DL_C1:
        LD A,(DE)
        CP (HL)
        JR NZ,DL_NM
        INC DE
        INC HL
        DEC C
        JR NZ,DL_C1
        LD A,(DE)               ; DE = id-bájt -> token-ID
        POP BC
        POP DE
        POP HL
        LD B,A
        RET
DL_NM:
        POP BC
        POP DE
        POP HL
        JR DL_STEP
DL_MISS:
        POP BC
        POP DE
        POP HL
        LD B,0
        RET

; WORDLEN: C = szóhossz; HL marad a szó elején
WORDLEN:
        PUSH HL
        LD C,0
WL_L:
        LD A,(HL)
        OR A
        JR Z,WL_END
        CP 32
        JR Z,WL_END
        INC HL
        INC C
        JR WL_L
WL_END:
        POP HL
        LD A,C
        RET

; ================= REASONING (intent) =================
REASON:
        XOR A
        LD (INTENT),A
        LD HL,BLINE
        LD DE,INTKWTAB
RE_L:
        LD A,(DE)
        OR A
        RET Z
        PUSH DE
        PUSH HL
        CALL KWDEQ
        POP HL
        POP DE
        OR A
        JR Z,RE_NOM
        INC DE                  ; a lezáró 0-n túl: intent bájt
        LD A,(DE)
        LD (INTENT),A
        RET
RE_NOM:
        INC DE                  ; lezáró 0
        INC DE                  ; intent bájt
        JR RE_L

; KWDEQ: DE = kulcsszó(0-lezárva); HL = BLINE; A = 1 egyezés, 0 nem
KWDEQ:
        PUSH DE
        PUSH HL
KQ_L:
        LD A,(DE)
        OR A
        JR Z,KQ_YES
        CP (HL)
        JR NZ,KQ_NO
        INC DE
        INC HL
        JR KQ_L
KQ_YES:
        LD A,1
        POP HL
        POP DE
        RET
KQ_NO:
        XOR A
        POP HL
        POP DE
        RET

; ================= GENERÁLÁS =================
GENERATE:
        LD A,(INTENT)
        CP 5
        JR Z,GEN_FACT
        CP 6
        JR Z,GEN_DAY
        CP 7
        JR Z,GEN_TIME
        CP 2
        JP Z,GEN_KB             ; membran: JR mar nem fut be (GEN_KB > 127)
        LD A,(IMAGF)
        OR A
        JR Z,GEN_PL
        CALL IMAGPICK
GEN_PL: CALL BGWRITE
        RET
GEN_FACT:
        CALL EMSET              ; fakt rögzítése az emlékezetzónába
        OR A
        JR Z,GEN_PL
        LD HL,TXTNOTED          ; talált fakt: rögzítve-jelzés
        CALL PRTLN
        CALL NEWLINE
        RET

; GEN_DAY: "what day" -> ha a datum es az ev megvan, napnev + datum;
; egyebkent sima generalas
GEN_DAY:
        CALL DOWGET
        CP 0xFF
        JR Z,GEN_PL
        CALL DP_SHOW
        RET

; GEN_TIME: munkamenet-ora (bekapcsolastol eltelt szamolt masodperc);
; dokumentalt egyszerusites: FRAMES-bol szamolva (a ROM lefelé szamol):
GEN_TIME:
        LD HL,TXTTIS
        CALL PRTLN
        LD HL,(BOOTFR)
        EX DE,HL
        LD HL,(FRAMES)
        OR A
        SBC HL,DE               ; HL = eltelt keretek (FRAMES lefelé számol)
        PUSH BC
        LD BC,50
        CALL DIV16             ; DE = masodpercek, HL = maradek
        PUSH DE
        EX DE,HL
        LD BC,60
        CALL DIV16             ; DE = percek, HL = masodpercek
        EX DE,HL
        LD A,L                 ; percek (0..21)
        CALL PRT2S
        LD A,':'
        CALL SAFEPCHR
        LD A,E                 ; E = masodpercek (0..49)
        CALL PRT2S
        POP DE
        POP BC
        CALL NEWLINE
        RET

; IMAGPICK: kepzetmod-modul (IMAGF = 1: a sorban IF/WOULD/COULD/WISH volt).
; Egy veletlan IMAGSEED-szot szotari tokenre fordit; a BGWRITE ezt a tokent
; hasznalja indulaskor, igy a valasz a kepzelet-temaju kapcsolasokba fut bele.
IMAGPICK:
        CALL RND
        AND 3
        LD E,A                 ; E = kivalasztott sorszam (0..3)
        LD HL,IMAGSEED
IMGF_N: LD A,E
        OR A
        JR Z,IMGF_F
        DEC E
IMGF_A: LD A,(HL)
        INC HL
        OR A
        JR NZ,IMGF_A
        JR IMGF_N
IMGF_F: PUSH BC
        PUSH DE
        PUSH HL
        CALL DICTLOOK          ; HL = szo; B = token-ID vagy 0
        POP HL
        POP DE
        POP BC
        LD A,B
        OR A
        JR Z,IMGF_E
        LD (IMAGSEEDT),A
IMGF_E: XOR A
        LD (IMAGF),A
        RET

GEN_KB:
        LD HL,KB_BASE           ; betöltött tudáslánc (ALAPMAG)
        CALL KBWALK
        OR A
        RET NZ
        LD HL,KBTAB             ; beépített tartalék
        CALL KBWALK
        OR A
        RET NZ
        LD HL,KB2T              ; v2.6: KB2-lanc (0x7C00): azonosito, Safar, hangulat
        CALL KBWALK
        OR A
        RET NZ
        JR BGWRITE              ; nincs tudás: generálás

; KBWALK: HL = [kulcsszó][0][tény][0]... lánc; kiírja a találatot,
; A = 1 (találat) vagy 0 (nincs)
KBWALK:
        PUSH BC
        PUSH DE
KW_L:
        LD A,(HL)
        OR A
        JR Z,KW_N
        PUSH HL
        EX DE,HL
        LD HL,BLINE
        CALL KWDEQ
        POP HL
        OR A
        JR NZ,KW_H
        PUSH BC
        LD B,0
KW_S1:
        LD A,(HL)
        INC HL
        OR A
        JR NZ,KW_S1
KW_S2:
        LD A,(HL)
        INC HL
        OR A
        JR NZ,KW_S2
        POP BC
        JR KW_L
KW_H:
        INC HL
        CALL PRTLN
        CALL NEWLINE
        POP DE
        POP BC
        LD A,1
        RET
KW_N:
        XOR A
        POP DE
        POP BC
        RET

; PRTRESP: RESP puffer kiírása
PRTRESP:
        LD HL,RESP
        CALL PRTLN
        CALL NEWLINE
        RET

; ================= GENERÁTOR (bigramm) =================
; RESP feltöltése token-folyammal: indulás ATTN (a felhasználó első
; szótári szava) vagy STARTTAB-szó, majd súlyozott átmenetek.

; BGWRITE: komponálás + kiírás
BGWRITE:
        LD HL,RESP
        LD (RESPW),HL
        XOR A
        LD (HL),A
        XOR A
        LD (BGFROM),A
        XOR A
        LD (TRP2),A             ; trigramm: az elso szotol csak bigram indul
        LD A,(IMAGSEEDT)
        OR A
        JR Z,BG_NIMG
        LD (BGFROM),A           ; kepzelet-modul: az IMAGPICK tokennel indul
        XOR A
        LD (IMAGSEEDT),A
        CALL BGWORD             ; a kepzelet-token az elso kiirt szo
        JR BG_LOOP
BG_NIMG:
        LD A,(ATTN)
        OR A
        JR NZ,BG_S2
        CALL STARTSEED
        OR A
        JR Z,BG_VOID
BG_S2:
        LD (BGFROM),A
        CALL BGWORD
BG_LOOP:
        LD A,(ABRT)
        OR A
        JR Z,BG_GO
        ; megszakítva: jelző törlése, jel kiírása
        XOR A
        LD (ABRT),A
        LD HL,TXTABORT
        CALL PRTLN
        CALL NEWLINE
        RET
BG_GO:
        CALL TRIGOTO            ; (TRP2, BGFROM) kulcs -> TRISET/TRIDE
        CALL BGCHOOSE
        OR A
        JR Z,BG_END
        PUSH AF
        LD A,(BGFROM)
        LD (TRP2),A             ; a kovetkezo korban a trigramm-kulcs elso fele
        POP AF
        LD (BGFROM),A
        CALL BGWORD
        JR BG_LOOP
BG_END:
        CALL PRTRESP
        RET
BG_VOID:
        LD HL,TXTDUNNO
        CALL PRTLN
        CALL NEWLINE
        RET

; BGCHOOSE: A = induló-token -> A = következő token (0 = lánc vége)
; szavazás a hőmérséklet szerint:
;   1: legnagyobb súly, 2: súlyozott rulett,
;   3: rulett + 1/4-es újdonság-löket, 4: egyenletes szavazás
BGCHOOSE:
        LD A,(PROF_TEMP)
        CP 2
        JR C,BGC_MAX
        JR Z,BGC_ROUL
        CP 4
        JR NC,BGC_UNI
        CALL RND
        AND 3
        CP 3
        JR Z,BGC_UNI
        JR BGC_ROUL
BGC_MAX:
        CALL SELMAX
        RET
BGC_ROUL:
        CALL SELROUL
        RET
BGC_UNI:
        CALL SELUNI
        RET

; BGGOTO: DE = csoport címe a BGFROM-tokenhez (DE=0, ha nincs átmenet);
; a tokent nem A-ban veszi, hanem a BGFROM-ból olvassa — így a hőmérséklet-
; elágazás után maradó A-érték sem ronthatja el a csoport-választást;
; ha TRISET=1, a TRIGOTO talált trigramm-követőcsoportot, azt adja.
; PAR nullázva (az olvasás mindig párosan indul)
; bigramm-tábla: [ntok][2 bájtos eltolások tokenenként + 1 extra][csoportok...]
BGGOTO:
        PUSH BC
        PUSH HL
        LD A,(TRISET)
        OR A
        JR Z,BG_BB
        LD DE,(TRIDE)
        JR BG_EP
BG_BB:
        XOR A
        LD (PAR),A
        LD A,(BGFROM)
        DEC A
        ADD A,A
        INC A                   ; BC = 1 + 2*(id-1) (ntok-bájt után)
        LD C,A
        LD B,0
        LD HL,(BIGR)
        ADD HL,BC
        LD A,(HL)
        INC HL
        LD L,A
        LD H,(HL)
        LD A,H
        OR L
        JR Z,BG_GZ
        LD DE,(BIGR)
        PUSH HL
        EX DE,HL
        POP DE
        ADD HL,DE
        EX DE,HL
        POP HL
        POP BC
        RET
BG_GZ:
        LD DE,0
BG_EP:
        XOR A
        LD (PAR),A
        POP HL
        POP BC
        RET

; TRIGOTO: a (TRP2, BGFROM) trigramm-kulcsot keresi a TRIB-ben álló
; tabla [t1][t2][n][parok][0] bejegyzései között; találat: TRISET=1 és
; TRIDE = követőcsoport cime (a BGCHOOSE trigrammból szavaz), missz:
; TRISET=0 (a BGGOTO nagyramban folytat). A/BC/DE/HL megmarad.
TRIGOTO:
        PUSH AF
        PUSH BC
        PUSH DE
        PUSH HL
        XOR A
        LD (TRISET),A
        LD HL,(TRIB)
        LD A,H
        OR L
        JR Z,TRG_E
        LD A,(TRP2)
        OR A
        JR Z,TRG_E
        LD B,A
        LD A,(BGFROM)
        LD C,A
TRG_L:
        LD A,(HL)
        OR A
        JR Z,TRG_E
        CP B
        JR Z,TRG_T2
        INC HL
        JR TRG_N
TRG_T2:
        INC HL
        LD A,(HL)
        CP C
        JR Z,TRG_NH
TRG_N:
        INC HL                  ; HL -> n
        LD A,(HL)
        INC A
        AND A                   ; carry torles (RRA előtt)
        RRA                     ; A = ceil(n/2)
        LD E,A
        ADD A,A
        ADD A,E                 ; A = 3*ceil(n/2)
        INC A                   ; + vegjel
        LD E,A
        LD D,0
        ADD HL,DE               ; HL -> kovetkezo kulcs
        JR TRG_L
TRG_NH:
        INC HL                  ; HL -> elso par
        LD A,(HL)
        OR A
        JR Z,TRG_E
        LD (TRIDE),HL
        LD A,1
        LD (TRISET),A
TRG_E:
        POP HL
        POP DE
        POP BC
        POP AF
        RET

; NXTENT: következő bigramm-elem beolvasása
; DE = futópálya, PAR = párosság (0: páros elem, 1: páratlan)
; csoportformátum: [t1][t2][w12][t3][t4][w34]...
; 1 bájt (w12) = 2 darab 4 bites súly; páratlan lezárás: [tX][0][wX<<4]
; kimenet: A = token (0 = csoport vége), B = súly (0..15)
NXTENT:
        LD A,(DE)
        OR A
        JR Z,NE_Z
        LD (NTTOK),A
        LD A,(PAR)
        OR A
        JR Z,NE_EVEN
NE_LO:
        INC DE
        LD A,(DE)
        AND 0x0F
        LD B,A
        INC DE
        XOR A
        JR NE_SET
NE_EVEN:
        PUSH DE
        INC DE
        INC DE
        LD A,(DE)
        RLCA
        RLCA
        RLCA
        RLCA
        LD B,A
        POP DE
        INC DE
        LD A,1
NE_SET:
        LD (PAR),A
        LD A,(NTTOK)
        RET
NE_Z:
        LD B,0
        XOR A
        RET

; CNTSUM: csoport bejárása -> NCOUNT (darab), WSUM (összsúly)
CNTSUM:
        XOR A
        LD (NCOUNT),A
        LD (WSUM),A
CS_L:
        CALL NXTENT
        OR A
        JR Z,CS_E
        LD A,(NCOUNT)
        INC A
        LD (NCOUNT),A
        LD A,B
        LD HL,WSUM
        ADD A,(HL)
        LD (HL),A
        JR CS_L
CS_E:
        RET

; SELMAX: legnagyobb súlyú tokent adja (hőmérséklet 1)
SELMAX:
        CALL BGGOTO
        XOR A
        LD (BESTW),A
        LD (BESTT),A
SMX_L:
        CALL NXTENT
        OR A
        JR Z,SMX_E
        LD A,B
        LD HL,BESTW
        CP (HL)
        JR C,SMX_L
        LD (HL),A
        LD A,(NTTOK)
        LD (BESTT),A
        JR SMX_L
SMX_E:
        LD A,(BESTT)
        RET

; SELROUL: súlyozott rulett (hőmérséklet 2 és 3)
SELROUL:
        CALL BGGOTO
        CALL CNTSUM
        LD A,(WSUM)
        OR A
        RET Z
        LD C,A
        CALL RND
SRL_M:
        CP C
        JR C,SRL_GO
        SUB C
        JR SRL_M
SRL_GO:
        LD (RTARGET),A
        CALL BGGOTO
SRL_W:
        CALL NXTENT
        OR A
        JR Z,SRL_Z
        LD A,(RTARGET)
        CP B
        JR C,SRL_H
        SUB B
        LD (RTARGET),A
        JR SRL_W
SRL_H:
        LD A,(NTTOK)
        RET
SRL_Z:
        XOR A
        RET

; SELUNI: egyenletes szavazás (hőmérséklet 4)
SELUNI:
        CALL BGGOTO
        CALL CNTSUM
        LD A,(NCOUNT)
        OR A
        RET Z
        LD C,A
        CALL RND
SUN_M:
        CP C
        JR C,SUN_OK
        SUB C
        JR SUN_M
SUN_OK:
        INC A                   ; DJNZ-hez: 1..N
        LD B,A
        CALL BGGOTO
SUN_W:
        CALL NXTENT
        OR A
        RET Z
        DJNZ SUN_W
        RET

; BGWORD: A = token-ID -> a szó a RESP végére + szóköz (ha még fér)
BGWORD:
        PUSH HL
        PUSH DE
        PUSH BC
        PUSH AF
        PUSH BC
        LD A,(GENCTR)
        CP 99
        JR NC,BGWC_1
        INC A
        LD (GENCTR),A
BGWC_1: POP BC
        LD A,(RESPW)
        SUB RESP
        CP 30
        JR NC,BGW_E
        CALL DICTAPP
BGW_E:
        POP AF
        POP BC
        POP DE
        POP HL
        RET

; DICTAPP: A = token-ID -> a szótári szó a RESP végére + szóköz
DICTAPP:
        PUSH HL
        PUSH DE
        PUSH BC
        PUSH AF
        LD (DAPPID),A
        LD HL,SZOTAR
        INC HL
DA_L:
        LD A,(HL)
        OR A
        JR Z,DA_MIS
        LD C,(HL)               ; hossz
        INC HL
        PUSH HL                 ; karakterek címe
        LD B,0
        ADD HL,BC               ; HL -> id-bájt
        LD A,(HL)
        LD D,A
        LD A,(DAPPID)
        CP D
        JR Z,DA_HIT
        POP HL
        DEC HL
        INC BC
        INC BC
        ADD HL,BC
        JR DA_L
DA_HIT:
        POP HL                  ; karakterek címe
        LD DE,(RESPW)
        LDIR                    ; C bájt másolása
        LD A,0x20
        LD (DE),A
        INC DE
        XOR A
        LD (DE),A
        EX DE,HL
        LD (RESPW),HL
        EX DE,HL
DA_OK:
        POP AF
        POP BC
        POP DE
        POP HL
        RET
DA_MIS:
        POP AF
        POP BC
        POP DE
        POP HL
        RET

; STARTSEED: véletlen induló-szo token-ID-je (STARTTAB-ból)
STARTSEED:
        PUSH HL
        PUSH DE
        PUSH BC
        CALL RND
        AND 3
        LD E,A
        OR A
        LD HL,STARTTAB
        JR Z,SS_LK
SS_W:
        LD A,(HL)
        INC HL
        OR A
        JR NZ,SS_W
        DEC E
        JR NZ,SS_W
SS_LK:
        CALL DICTLOOK
        LD A,B
        POP BC
        POP DE
        POP HL
        RET

; BIGRBASE: BIGR = a szótár-végjel utáni első bájt (a bigramm-tábla);
; utána TRIINIT: a bigramm-fejléc extra eltolásából (index ntok+1) TRIB =
; a trigramm-tábla címe (0 = nincs trigramm-tábla)
BIGRBASE:
        LD HL,SZOTAR
        INC HL
BB_L:
        LD A,(HL)
        OR A
        JR Z,BB_E
        LD C,(HL)
        LD B,0
        INC BC
        INC BC
        ADD HL,BC
        JR BB_L
BB_E:
        INC HL
        LD (BIGR),HL
        LD A,(HL)               ; a bg-fejléc ntok bájtja
        LD C,A
        ADD A,A
        INC A                   ; BC = 1 + 2*ntok (extra eltolás helye)
        LD C,A
        LD B,0
        INC HL
        ADD HL,BC
        LD A,(HL)
        INC HL
        LD L,A
        LD H,(HL)
        PUSH HL
        POP DE                  ; DE = eltolás (0 = nincs)
        LD HL,(BIGR)
        ADD HL,DE
        LD A,H
        OR L
        JR Z,BB_N
        LD (TRIB),HL
        RET
BB_N:
        LD HL,0
        LD (TRIB),HL
        RET

; RND: A = véletlen bájt (R regiszter + FRAMES + seed)
RND:
        PUSH DE
        LD A,R
        LD E,A
        LD A,(FRAMES)
        XOR E
        LD HL,RNDSEED
        ADD A,(HL)
        RRCA
        LD (RNDSEED),A
        POP DE
        RET

; ================= EMLEKEZET (06 blokk) =================
; EMINIT: az emlekezzonat gyakornokosztja a magansaval; ha a PROFILban
; mar van datum, atveszi DAYNOW/MONNOW-ba, kulonben az ertekek 0-k.
EMINIT:
        LD HL,EMSTORE
        LD A,(HL)
        CP 0xC3
        JR Z,EMI_D
        LD A,0xC3
        LD (HL),A
        INC HL
        XOR A
        LD (HL),A
EMI_D:  LD HL,PROF_DDAY
        LD A,(HL)
        OR A
        RET Z
        LD HL,PROF_DMON
        LD A,(HL)
        LD (MONNOW),A
        LD HL,PROF_DDAY
        LD A,(HL)
        LD (DAYNOW),A
        RET

; DATASK: ha nincs datum (nap = 0), addig ker be "dd mm" alakban,
; amig ervenyes nem lesz; else maradt: semmi.
DATASK:
        LD HL,PROF_DDAY
        LD A,(HL)
        OR A
        JR NZ,DS_Y
DS_L:   LD HL,TXTDATEQ
        CALL PRTLN
        CALL READLINE
        CALL PARSEDATE
        OR A
        JR Z,DS_L
DS_Y:   LD HL,PROF_YR
        LD A,(HL)
        CP 0xFF
        RET NZ
DS_YL:  LD HL,TXTYEARQ
        CALL PRTLN
        CALL READLINE
        CALL PARYEAR
        OR A
        JR Z,DS_YL
        RET

; PARYEAR: a BLINE egy eves szamot olvas (0..99); siker eseten A = 1
; es tarolja PROF_YR-ba, egyebkent A = 0
PARYEAR:
        LD HL,BLINE
        CALL SKNPC
        LD A,(HL)
        OR A
        JR Z,PY_N
        CALL RDNUM
        OR A
        JR Z,PY_N
        LD A,E
        LD (PROF_YR),A
        LD A,1
        RET
PY_N:   XOR A
        RET

; PARSEDATE: a BLINE "dd mm" mintajat vizsgalja; sikernel A = 1
; es tarol (DAYNOW/MONNOW + PROFIL), sikertelennel A = 0.
PARSEDATE:
        LD HL,BLINE
        CALL SKNPC
        LD A,(HL)
        OR A
        JR Z,PD_N
        CALL RDNUM
        OR A
        JR Z,PD_N
        LD A,E
        CP 1
        JR C,PD_N
        CP 32
        JR NC,PD_N
        LD A,E
        LD (DAYNOW),A
        CALL SKNPC
        LD A,(HL)
        OR A
        JR Z,PD_N
        CALL RDNUM
        OR A
        JR Z,PD_N
        LD A,E
        CP 1
        JR C,PD_N
        CP 13
        JR NC,PD_N
        LD A,E
        LD (MONNOW),A
        CALL PARYEAR            ; ev: ha nincs a sorban, PROF_YR marad
        LD HL,PROF_DDAY
        LD A,(DAYNOW)
        LD (HL),A
        LD HL,PROF_DMON
        LD A,(MONNOW)
        LD (HL),A
        LD A,1
        RET
PD_N:   XOR A
        RET

; SKNPC: HL-ben erkezo poziciotol ugras a kovetkezo szamjegyig
; (vagy sorvegeig); HL fejlettebb ponttal ter vissza
SKNPC:
        LD A,(HL)
        OR A
        RET Z
        CP 0x30
        JR NC,SK_OK
        INC HL
        JR SKNPC
SK_OK:  CP 0x3A
        RET C
        INC HL
        JR SKNPC

; RDNUM: HL-tol at most 2 szamjegy; sikernel A = 1 (ertek E-ben,
; HL a szamok utanra all), sikertelennel A = 0
RDNUM:  XOR A
        LD E,A
        LD A,(HL)
        CP 0x30
        JR C,RD_N
        CP 0x3A
        JR NC,RD_N
        SUB 0x30
        LD E,A
        INC HL
        LD A,(HL)
        CP 0x30
        JR C,RD2_L
        CP 0x3A
        JR NC,RD2_L
        SUB 0x30
        LD B,A
        LD A,E
        ADD A,A
        LD D,A
        ADD A,A
        ADD A,A
        ADD A,D
        ADD A,B
        LD E,A
        INC HL
RD2_L:   LD A,1
        RET
RD_N:   XOR A
        RET

; OBSSCAN: indulaskor a 14 napnal regi emlekrekordok ertekbitjenek
; torlese (b1 = 0x80: ertek 0, elavulas-jel). Honap-kulonbseggel
; szamol, 16 bites matek nelkul; a honapokat egysegesen 30 nappal
; kozeliti (dokumentalt egyszerusites).
OBSSCAN:
        LD HL,PROF_DDAY
        LD A,(HL)
        OR A
        RET Z
        LD A,(EMMCNT)
        OR A
        RET Z
        LD B,A
        LD HL,EMREC0
OS_L:   PUSH BC
        LD A,(HL)
        INC HL
        INC HL
        LD C,(HL)               ; C = rekord napja
        INC HL
        LD D,(HL)               ; D = rekord honapja
        PUSH HL
        LD HL,PROF_DMON
        LD E,(HL)               ; E = aktualis honap
        LD HL,PROF_DDAY
        LD A,(HL)               ; A = aktualis nap
        LD H,D
        LD D,A                  ; D = aktualis nap, H = rekord honapja
        LD A,E
        CP H
        JR Z,OS_SAME
        JR C,OS_OBS             ; rekord jovobeli datum -> elavult
        SUB H
        CP 2
        JR NC,OS_OBS
        LD A,D
        SUB C
        JR NC,OS_A30
        XOR A
OS_A30: ADD A,30
        JR OS_CHK
OS_SAME:
        LD A,D
        SUB C
        JR NC,OS_CHK
        XOR A
OS_CHK: CP 15
        JR C,OS_OK
OS_OBS: POP HL
        DEC HL
        DEC HL
        LD A,0x80
        LD (HL),A
        JR OS_NX
OS_OK:  POP HL
OS_NX:  INC HL
        POP BC
        DJNZ OS_L
        RET

; EMFIND: A = bitkod -> HL = a kereseett rekord b0-cime, vagy HL = 0
EMFIND:
        PUSH BC
        PUSH DE
        LD E,A
        LD A,(EMMCNT)
        OR A
        JR Z,EF_N
        LD B,A
        LD HL,EMREC0
EF_L:   LD A,(HL)
        CP E
        JR Z,EF_F
        INC HL
        INC HL
        INC HL
        INC HL
        DJNZ EF_L
EF_N:   XOR A
        LD H,A
        LD L,A
EF_F:   POP DE
        POP BC
        RET

; EMSET: az EMLBIT/EMLVAL paros tarolasa az emlekezetzonaban.
; Ha mar van rekord ugyanazzal a bitkoddal, frissit; kulonben ujat
; fuz hozza (max 63 db). A = 1 sikeres tarolas, 0 = hiba/nincs fakt.
EMSET:
        LD A,(EMLBIT)
        CP 0xFF
        JR Z,ES_0
        CALL EMFIND
        LD A,H
        OR L
        JR NZ,ES_UPD
        LD A,(EMMCNT)
        CP 63
        JR NC,ES_0
        LD L,A
        LD H,0
        ADD HL,HL
        ADD HL,HL
        LD DE,EMREC0
        ADD HL,DE
        LD A,(EMMCNT)
        INC A
        LD (EMMCNT),A
ES_UPD:
        LD A,(EMLBIT)
        LD (HL),A
        INC HL
        LD A,(EMLVAL)
        AND 1
        LD (HL),A
        INC HL
        LD HL,DAYNOW
        LD A,(HL)
        EX DE,HL
        LD (HL),A
        EX DE,HL
        INC HL
        LD HL,MONNOW
        LD A,(HL)
        EX DE,HL
        LD (HL),A
        EX DE,HL
        CALL MASKOF
        LD A,1
        RET
ES_0:   XOR A
        RET

; MASKOF: az EMLBIT szerinti bit be-/kikapcsolasa PROF_FLAGB-ban az
; EMLVAL ertek szerint; az 5-7-es bitek fixen 0-k (0x76-vedelem)
MASKOF:
        LD A,(EMLBIT)
        AND 7
        CP 5
        RET NC
        LD B,A
        LD A,1
        JR Z,MK_D
MK_L:   ADD A,A
        DJNZ MK_L
MK_D:   LD B,A
        LD A,(EMLVAL)
        OR A
        JR Z,MK_C
        LD HL,PROF_FLAGB
        LD A,(HL)
        OR B
        LD (HL),A
        RET
MK_C:   LD A,B
        CPL
        LD B,A
        LD HL,PROF_FLAGB
        LD A,(HL)
        AND B
        LD (HL),A
        RET

; REMCHK: emlek-raKERDEZO ketto fakt: fejfajas (0) es rosszullszerint (1)
REMCHK:
        XOR A
        LD DE,ASKH
        CALL REMONE
        LD A,1
        LD DE,ASKS
        JR REMONE

; REMONE: A = bitkod, DE = kerdessor. Ha aktiv (ertek = 1) a rekord,
; raKERDEZ; ha a valaszban szerepel CLRTAB-szo, 0-ra allitja.
REMONE:
        PUSH BC
        PUSH DE
        PUSH HL
        LD (EMLBIT),A
        CALL EMFIND
        LD A,H
        OR L
        JR Z,RM_E
        INC HL
        LD A,(HL)
        DEC HL
        CP 1
        JR NZ,RM_E
        EX DE,HL
        CALL PRTLN
        CALL NEWLINE
        CALL READLINE
        LD HL,BLINE
        LD DE,CLRTAB
RM_L:   LD A,(DE)
        OR A
        JR Z,RM_E
        PUSH DE
        PUSH HL
        CALL KWGET
        POP HL
        POP DE
        OR A
        JR NZ,RM_Y
        PUSH BC
        LD B,0
RM_S:   LD A,(DE)
        INC DE
        OR A
        JR NZ,RM_S
        POP BC
        JR RM_L
RM_Y:   XOR A
        LD (EMLVAL),A
        CALL EMSET
RM_E:   POP HL
        POP DE
        POP BC
        RET

; FACTSET: fakt-kulcsszavak keresese a sorban; talalatnal INTENT = 5
; es EMLBIT/EMLVAL beallitasa (NEGTAB-szo: ertek 0)
FACTSET:
        LD A,0xFF
        LD (EMLBIT),A
        XOR A
        LD (EMLVAL),A
        LD HL,FACTTAB
FS_L:   LD A,(HL)
        OR A
        JR Z,FS_0
        PUSH HL
        EX DE,HL
        LD HL,BLINE
        CALL KWGET
        POP HL
        OR A
        JR Z,FS_NX
        PUSH BC
        LD B,0
FS_S:   LD A,(HL)
        INC HL
        OR A
        JR NZ,FS_S
        LD A,(HL)
        LD (EMLBIT),A
        POP BC
        LD A,1
        LD (EMLVAL),A
        LD HL,BLINE
        LD DE,NEGTAB
FS_NL:  LD A,(DE)
        OR A
        JR Z,FS_E2
        PUSH DE
        PUSH HL
        CALL KWGET
        POP HL
        POP DE
        OR A
        JR Z,FS_NN
        XOR A
        LD (EMLVAL),A
        JR FS_E2
FS_NN:  PUSH BC
        LD B,0
FS_S2:  LD A,(DE)
        INC DE
        OR A
        JR NZ,FS_S2
        POP BC
        JR FS_NL
FS_E2:  LD A,(INTENT)
        OR A
        RET NZ                  ; v2.6: a REASON-szandekot (kerdes/hangulat)
        LD A,5                  ; nem irjuk felul fakt-tal
        LD (INTENT),A
        RET
FS_NX:  PUSH BC
        LD B,0
FS_S3:  LD A,(HL)
        INC HL
        OR A
        JR NZ,FS_S3
        INC HL
        INC HL
        POP BC
        JR FS_L
FS_0:   LD HL,BLINE
        LD DE,WTAB
        CALL KWGTAB
        JR Z,FS_T
        LD A,6
        LD (INTENT),A           ; "what day": naptar-valasz
        RET
FS_T:   LD HL,BLINE
        LD DE,TIMTAB
        CALL KWGTAB
        JR Z,FS_I
        LD A,7
        LD (INTENT),A           ; "what time": ora-valasz
        RET
FS_I:   LD HL,BLINE
        LD DE,IMAGTAB
        CALL KWGTAB
        RET Z
        LD A,1
        LD (IMAGF),A            ; kepzelt-modul aktiv (nem valtoztat INTENT-et)
        RET

; KWGTAB: DE = [szo][0]...[0] tabla (ures tetelemmel zarva); BLINE-ban keres;
; A = 1, ha barmelyik szo benne van a sorban, kulonben 0; BC/DE/HL megmaradnak
KWGTAB:
        PUSH BC
        PUSH DE
        PUSH HL
KGT_L:  LD A,(DE)
        OR A
        JR Z,KGT_N
        PUSH DE
        PUSH HL
        LD HL,BLINE
        CALL KWGET
        POP HL
        POP DE
        OR A
        JR NZ,KGT_Y
KGT_S:  LD A,(DE)
        INC DE
        OR A
        JR NZ,KGT_S
        INC DE
        JR KGT_L
KGT_Y:  POP HL
        POP DE
        POP BC
        LD A,1
        RET
KGT_N:  POP HL
        POP DE
        POP BC
        XOR A
        RET

; KWGET: DE = kulcsszo, HL = sor; A = 1, ha a sorban van keresett szo;
; BC/DE/HL megmaradnak
KWGET:
        PUSH BC
        PUSH DE
        PUSH HL
KG_W:   LD A,(HL)
        OR A
        JR Z,KG_N
        PUSH DE
        PUSH HL
        CALL KWDE2
        POP HL
        POP DE
        OR A
        JR NZ,KG_Y
KG_S:   LD A,(HL)
        OR A
        JR Z,KG_N
        CP 0x20
        JR Z,KG_E
        INC HL
        JR KG_S
KG_E:   INC HL
        JR KG_W
KG_Y:   POP HL
        POP DE
        POP BC
        LD A,1
        RET
KG_N:   POP HL
        POP DE
        POP BC
        XOR A
        RET

; KWDE2: DE = kulcsszo, HL = szo eleje; A = 1, ha teljes egyezes
; (szovegvege = szokoz vagy 0); kis-/nagybetu-kevertten is mukodik
KWDE2:
        PUSH BC
        LD A,(DE)
        OR A
        JR Z,KD_E
        AND 0xDF
        LD B,A
        LD A,(HL)
        AND 0xDF
        CP B
        JR NZ,KD_N
        INC DE
        INC HL
        POP BC
        JR KWDE2
KD_E:   LD A,(HL)
        OR A
        JR Z,KD_Y
        CP 0x20
        JR Z,KD_Y
KD_N:   POP BC
        XOR A
        RET
KD_Y:   POP BC
        LD A,1
        RET

; SAVEMEM: MENTES dátumbélyege a PROFILban (a kazettaira iras kesobb)
SAVEMEM:
        LD HL,PROF_DDAY
        LD A,(HL)
        LD HL,PROF_SVDAY
        LD (HL),A
        LD HL,PROF_DMON
        LD A,(HL)
        LD HL,PROF_SVMON
        LD (HL),A
        RET

; ================= NAPTAR =================
; DOWGET: A = 0..6 (0 = vasarnap), vagy 0xFF = nincs ev (PROF_YR = 0xFF);
; Zeller-egyszerusites a 2000-2099 idosavra (J = 20 => 5J + J/4 7-tel osztva 0):
; A = (nap + TAB13[m'] + K + K/4 + jan2000-korrektes) mod 7.
; A TAB13 tablat a teljes 2000-2099 tartomanyra brute-force ellenoriztuk a
; Python calendar moduljaval (36525 datum, 0 hiba).
DOWGET:
        LD HL,PROF_YR
        LD A,(HL)
        CP 0xFF
        RET Z
        LD B,A                  ; B = K
        LD HL,PROF_DDAY
        LD A,(HL)
        LD C,A                  ; C = nap
        XOR A
        LD D,A                  ; Jan/Feb 2000-korrektes (0/1)
        LD A,(PROF_DMON)
        CP 3
        JR C,DW_JF
        LD L,A                  ; m' = honap
        LD H,0
        JR DW_TAB
DW_JF:  LD A,B
        OR A
        JR NZ,DW_J1
        LD B,99                 ; honapjan 2000: K = 99, dunykep +1
        INC D
        JR DW_J2
DW_J1:  DEC B
DW_J2:  LD A,(PROF_DMON)
        ADD A,12
        LD L,A
        LD H,0
DW_TAB: LD DE,TAB13
        ADD HL,DE
        LD A,(HL)               ; A = TAB13[m']
        ADD A,C                 ; + nap
        LD E,A                  ; E = TAB13 + nap
        LD A,B                  ; A = K
        AND A
        RRA
        AND A
        RRA                     ; A = K/4 (logikai jobblepes nullzott carry-vel)
        ADD A,B                 ; A = K + K/4
        ADD A,E                 ; + TAB13 + nap
        ADD A,D                 ; with the Jan 2000 correction
        ADD A,6
DW_MOD: CP 7
        JR C,DW_E
        SUB 7
        JR DW_MOD
DW_E:   RET

; PRT2S: A = 0..99 ket decimalis szamjegykent a kepernyore (kurzor JTextre)
PRT2S:
        PUSH BC
        PUSH DE
        PUSH HL
        LD E,A
        XOR A
        LD B,A
P2_L:   LD A,E
        CP 10
        JR C,P2_D
        SUB 10
        LD E,A
        INC B
        JR P2_L
P2_D:   LD A,B
        ADD A,'0'
        CALL SAFEPCHR
        LD A,E
        ADD A,'0'
        CALL SAFEPCHR
        POP HL
        POP DE
        POP BC
        RET

; DP_SHOW: a DOWGET altal visszaadott A-val 'it's <nap> <nn> <mm> <yy>' kiiras
DP_SHOW:
        PUSH BC
        PUSH DE
        PUSH HL
        PUSH AF               ; a PRTLN torolja A-t, a napnevet meg kell orizni
        LD HL,TXTDAYP
        CALL PRTLN
        POP AF
        ADD A,A
        ADD A,A
        LD E,A
        LD D,0
        LD HL,DOWTAB
        ADD HL,DE
        CALL PRTLN
        LD A,' '
        CALL SAFEPCHR
        LD A,(PROF_DDAY)
        CALL PRT2S
        LD A,' '
        CALL SAFEPCHR
        LD A,(PROF_DMON)
        CALL PRT2S
DP_N:   CALL NEWLINE
        POP HL
        POP DE
        POP BC
        RET

; BOOTD: indulaskor ha a datum es az ev is megvan, kiirja az aktualis napnevet
BOOTD:
        LD A,(PROF_DDAY)
        OR A
        RET Z
        CALL DOWGET
        CP 0xFF
        RET Z
        CALL DP_SHOW
        RET

; DOY30: A = honap, C = nap -> nap-index az ev elejetol (30-dal szamol,
; elemi korlatlan kozelites, eleg az elavulasiteshoz)
DOY30:  PUSH BC
        DEC A
        JR Z,DY_E
        LD B,A
        XOR A
DY_L:   LD E,A
        LD A,30
        ADD A,E
        DJNZ DY_L
DY_E:   ADD A,C
        POP BC
        RET

; ================= CHAT-NAPLÓ =================
; CHATADD: A = irány (0 = YOU, 1 = PIOCO); HL = üzenet (0-zárt);
; TOKSET/ELAPS már beállítva. Fejléc a TMPHDR-be, tárolás a CHAT-zónába
; (0x6001–0x66FF, elölről íródik, ha tele), fejléc inverzen képernyőre.
CHATADD:
        PUSH BC
        PUSH DE
        PUSH HL
        LD (CMSG),HL
        LD (CDIR),A
        CALL MKHDR
        LD A,(CHATM)
        CP 0xA5
        JR Z,CA_OK
        LD A,0xA5
        LD (CHATM),A
        LD HL,CHATM0
        LD (CHATW),HL
CA_OK:  LD HL,(CHATW)
        LD DE,TMPHDR
        CALL ADDLEN
        LD DE,(CMSG)
        CALL ADDLEN
        LD A,H
        CP 0x67
        JR C,CA_ST
        LD HL,CHATM0
        LD (CHATW),HL
CA_ST:  LD DE,(CHATW)
        LD HL,TMPHDR
        CALL CSTRCPY
        LD HL,(CMSG)
        CALL CSTRCPY
        LD HL,TMPHDR
        CALL PRTINV
        CALL NEWLINE
        POP HL
        POP DE
        POP BC
        RET

; ADDLEN: HL += strlen(DE)+1
ADDLEN:
        PUSH BC
        LD B,0
ADL_L:  LD A,(DE)
        OR A
        JR Z,ADL_E
        INC DE
        INC B
        JR ADL_L
ADL_E:  INC B
        LD A,B
        ADD A,L
        LD L,A
        JR NC,ADL_2
        INC H
ADL_2:  POP BC
        RET

; CSTRCPY: HL = forrás, DE = cél; a 0-t is átmásolja; CHATW = utána
CSTRCPY:
        LD A,(HL)
        LD (DE),A
        INC HL
        INC DE
        OR A
        JR NZ,CSTRCPY
        LD A,E
        LD (CHATW),A
        LD A,D
        LD (CHATW+1),A
        RET

; MKHDR: fejléc a TMPHDR-be (0-zárva)
;   YOU m:ss [tt]       — felhasználó
;   PIOCO m:ss [tt] sS  — modell (S = generálás másodperce)
MKHDR:
        XOR A
        LD (TMPW),A
        LD A,(CDIR)
        OR A
        JR Z,MKH_Y
        LD HL,TXTPCO
        CALL APPSZ
        JR MKH_T
MKH_Y:  LD HL,TXTYOU
        CALL APPSZ
MKH_T:  LD A,' '
        CALL APPCH
        LD HL,(BOOTFR)
        EX DE,HL
        LD HL,(FRAMES)
        OR A
        SBC HL,DE
        PUSH BC
        LD BC,50
        CALL DIV16             ; DE = másodpercek, HL = maradék
        PUSH DE
        EX DE,HL
        LD BC,60
        CALL DIV16             ; DE = percek, HL = másodpercek
        EX DE,HL
        CALL DECOUT            ; percek
        LD A,':'
        CALL APPCH
        LD A,E                 ; E = másodpercek (0..49)
        CALL APP2
        POP DE
        LD A,' '
        CALL APPCH
        LD A,'['
        CALL APPCH
        LD A,(TOKSET)
        CALL APP2
        LD A,']'
        CALL APPCH
        LD A,(CDIR)
        OR A
        JR Z,MKH_E
        LD A,' '
        CALL APPCH
        LD A,'s'
        CALL APPCH
        LD A,(ELAPS)
        CALL APP2
MKH_E:  XOR A
        CALL APPCH
        POP BC
        RET

; APPSZ: HL = 0-zárt szöveg a TMPHDR-be
APPSZ:
        LD A,(HL)
        OR A
        RET Z
        PUSH HL
        CALL APPCH
        POP HL
        INC HL
        JR APPSZ

; APPCH: A = ASCII-bájt a TMPHDR-be (TMPW követi)
APPCH:
        PUSH HL
        PUSH DE
        LD E,A
        LD A,(TMPW)
        LD HL,TMPHDR
        ADD A,L
        LD L,A
        JR NC,APC_1
        INC H
APC_1:  LD A,E
        LD (HL),A
        LD A,(TMPW)
        INC A
        LD (TMPW),A
        POP DE
        POP HL
        RET

; APP2: A = 0..99, két számjegyre
APP2:
        PUSH BC
        PUSH DE
        LD E,A
        XOR A
        LD B,A
AP2_L:  LD A,E
        CP 10
        JR C,AP2_D
        SUB 10
        LD E,A
        INC B
        JR AP2_L
AP2_D:  LD A,B
        ADD A,'0'
        CALL APPCH
        LD A,E
        ADD A,'0'
        CALL APPCH
        POP DE
        POP BC
        RET

; DIV16: HL / BC -> DE = hányados, HL = maradék (ismételt kivonás)
DIV16:
        PUSH AF
        LD DE,0
DV_L:   LD A,H
        CP B
        JR C,DV_E
        JR NZ,DV_S
        LD A,L
        CP C
        JR C,DV_E
DV_S:   LD A,L
        SUB C
        LD L,A
        LD A,H
        SBC A,B
        LD H,A
        INC DE
        JR DV_L
DV_E:   POP AF
        RET

; DECOUT: HL = érték (0..9999) -> ASCII a TMPHDR-be
DECOUT:
        PUSH BC
        PUSH DE
        PUSH AF
        XOR A
        LD D,A                ; vezető-nullák kihagyása
        LD BC,1000
        CALL DOD
        LD BC,100
        CALL DOD
        LD BC,10
        CALL DOD
        LD A,L
        ADD A,'0'
        CALL APPCH
        POP AF
        POP DE
        POP BC
        RET
DOD:
        PUSH DE
        LD E,0
DD_L:   LD A,H
        CP B
        JR C,DD_E
        JR NZ,DD_S
        LD A,L
        CP C
        JR C,DD_E
DD_S:   LD A,L
        SUB C
        LD L,A
        LD A,H
        SBC A,B
        LD H,A
        INC E
        JR DD_L
DD_E:   LD A,E
        OR D
        JR Z,DD_0
        ADD A,'0'
        CALL APPCH
        LD D,1
DD_0:   POP DE
        RET

; SNAPFR / ELAPSEC: válaszidő-mérés (FRAMES = 50 Hz)
SNAPFR:
        LD HL,(FRAMES)
        LD (FRSNAP),HL
        RET
ELAPSEC:
        LD HL,(FRSNAP)
        PUSH BC
        EX DE,HL
        LD HL,(FRAMES)
        OR A
        SBC HL,DE           ; HL = FRSNAP - FRAMES = eltelt keretek
        CALL DIV16
        LD A,E
        CP 100
        JR C,ELS_1
        LD A,99
ELS_1:  LD (ELAPS),A
        POP BC
        RET

; ================= GÖRGETÉS (SHIFT+5/6) =================
; HISTB: a CHAT-napló böngészője; belépéskor az utolsó üzenet,
; SHIFT+5 = időben vissza, SHIFT+6 = előre, más billentyű = kilépés
HISTB:
        CALL HMCONTS
        OR A
        RET Z
        DEC A
        LD (HNDEX),A
HB_L:   LD A,(HNDEX)
        CALL HSHOWI
        CALL GETKEY
        OR A
        JR Z,HB_L
        PUSH AF
        LD A,(SHIFTF)
        OR A
        POP AF
        JR Z,HB_E
        CP '5'
        JR Z,HB_B
        CP '6'
        JR Z,HB_F
HB_E:   CALL CLRSCR
        RET
HB_B:
        LD A,(HNDEX)
        OR A
        JR Z,HB_L
        DEC A
        LD (HNDEX),A
        JR HB_L
HB_F:
        LD A,(HNDEX)
        INC A
        LD E,A
        CALL HMCONTS
        CP E
        JR C,HB_L
        JR Z,HB_L
        LD A,E
        LD (HNDEX),A
        JR HB_L

; HMCONTS: A = üzenetek száma a CHAT-naplóban
HMCONTS:
        PUSH BC
        PUSH DE
        PUSH HL
        LD B,0
        LD HL,CHATM0
HC_L:   LD DE,(CHATW)
        LD A,D
        CP H
        JR C,HC_E
        JR NZ,HC_N
        LD A,E
        CP L
        JR C,HC_E
        JR Z,HC_E
HC_N:   INC B
        PUSH BC
        CALL HMSKIP
        POP BC
        JR HC_L
HC_E:   LD A,B
        POP HL
        POP DE
        POP BC
        RET

; HMSKIP: HL -> a következő rekord eleje (két 0-zárt szöveg)
HMSKIP:
        PUSH BC
        LD B,0
HMS1:   LD A,(HL)
        INC HL
        OR A
        JR NZ,HMS1
        LD B,0
HMS2:   LD A,(HL)
        INC HL
        OR A
        JR NZ,HMS2
        POP BC
        RET

; HMSGI: A = 0-tól indexelt üzenet -> HL = rekordcíme (vagy 0)
HMSGI:
        PUSH BC
        PUSH DE
        LD C,A
        LD HL,CHATM0
HG_L:   LD DE,(CHATW)
        LD A,D
        CP H
        JR C,HG_0
        JR NZ,HG_N
        LD A,E
        CP L
        JR C,HG_0
        JR Z,HG_0
HG_N:   XOR A
        CP C
        JR Z,HG_F
        PUSH BC
        CALL HMSKIP
        POP BC
        DEC C
        JR HG_L
HG_0:   XOR A
        LD H,A
        LD L,A
HG_F:   POP DE
        POP BC
        RET

; HSHOWI: A = üzenet-index -> képernyőre (fejléc inverzen, szöveg normál)
HSHOWI:
        CALL HMSGI
        LD A,H
        OR L
        RET Z
        PUSH HL
        CALL CLRSCR
        POP HL
        PUSH HL
        CALL PRTINV
        CALL NEWLINE
        POP HL
        PUSH BC
        LD B,0
HS_S:   LD A,(HL)
        INC HL
        OR A
        JR NZ,HS_S
        POP BC
        CALL PRTLN
        CALL NEWLINE
        RET

; ================= ADATOK =================
DEFNAME:    db "GUEST",0
TXTSPLASH:  db "P I O C O  A I",0
TXTHELLO:   db "Hi! Ask me anything.",0
TXTPROMPT:  db "> ",0
TXTTHINK:   db "[thinking]",0
TXTNAM:     db "",0
TXTTEMPSET: db "[temp ",0
TXTREASON0: db "[reasoning off]",0
TXTREASON1: db "[reasoning on]",0
TXTSAVED:   db "[memory saved]",0
TXTYOU:     db "YOU",0
TXTPCO:     db "PIOCO",0

; ---- EMLEKEZET tablak es szovegek ----
; a TAB13/DOWTAB/TXTDAYP/TXTTIS/WTAB/TIMTAB/IMAGTAB/IMAGSEED tablak a
; TADAT (0x6B00) blokkban vannak (motor/tadat.asm) — a motorzonan kivul

; FACTTAB/NEGTAB/CLRTAB/TXTNOTED a TADAT-ban (tadat.asm); ASKH/ASKS/
; TXTDUNNO/TXTABORT a TARTALEK-zonaban (tartalek.asm)
TXTDATEQ:   db "enter date as dd mm yy:",0
TXTYEARQ:   db "enter year as yy:",0

; véletlen válaszindítók (mind szótári szó)
STARTTAB:
        db "HELLO",0
        db "THE",0
        db "MY",0
        db "YOU",0

; keyword -> intent: [keyword][0][intent]
INTKWTAB:
        db "WHAT",0,2
        db "WHO",0,2
        db "WHY",0,2
        db "REMEMBER",0,5
        db "DRAW",0,8
        db "SAVE",0,8
; v2.6: DO-prefix (DO/DOES/DOES NOT lefedi), CAN (nyelvi kerdes + KB2)
        db "DO",0,2
        db "CAN",0,2
; v2.6: hangulat-szavak (KB2-valaszok, prefix alapjan) — intent 2 = GEN_KB
        db "HAHA",0,2
        db "WOW",0,2
        db "NOO",0,2
        db "HAPPY",0,2
        db "SAD",0,2
        db 0

; beépített tudás-tartalék: [keyword][0][fact][0]
KBTAB:
        db "HELLO",0,"Hello there! Nice to meet you.",0
        db "CAT",0,"Cats are lovely companions.",0
        db "ZX81",0,"I think at 3.25 MHz with 16 KB of RAM.",0
        db 0

; ASCII(32..127) -> ZX81-kód; SAFEPCHR tiltja a 0x76-ot és 0xC0+ kódokat
; (végső értékeket az emulátor-összevetés véglegesíti)
ASCTAB:
        db 0x00,0x0B,0x14,0x0D,0x15,0x13,0x16,0x12   ; 0x20..0x27
        db 0x1A,0x1B,0x1B,0x0C,0x0D,0x1B,0x1B,0x1B   ; 0x28..0x2F
        db 0x1C,0x1D,0x1E,0x1F,0x20,0x21,0x22,0x23   ; 0..7
        db 0x24,0x25,0x1B,0x1B,0x1B,0x1B,0x1B,0x1B   ; 8..9 : ; < = >
        db 0x1B,0x26,0x27,0x28,0x29,0x2A,0x2B,0x2C   ; @ a..g
        db 0x2D,0x2E,0x2F,0x30,0x31,0x32,0x33,0x34   ; h..o
        db 0x35,0x36,0x37,0x38,0x39,0x3A,0x3B,0x3C   ; p..w
        db 0x3D,0x3E,0x3F,0x1B,0x1B,0x1B,0x1B,0x1B   ; x y z { | } ~

; billentyűzet-mátrix (port 0xFE; sormezők 0..7; bit0 = a sor "utolsó" gombja)
; 0xFE: (0)=SHIFT 1=z 2=x 3=c 4=v    -> a 0 helye a táblában: 0
; 0xFD: A S D F G   0xFB: Q W E R T
; 0xF7: 1 2 3 4 5   0xEF: 0 9 8 7 6
; 0xDF: P O I U Y   0xBF: ENTER L K J H
; 0x7F: SPACE . M N B
KEYROWS: db 0xFE,0xFD,0xFB,0xF7,0xEF,0xDF,0xBF,0x7F
KEYTBL:  db 0,"ZXCV"
         db "ASDFG"
         db "QWERT"
         db "12345"
         db "09876"
         db "POIUY"
         db 13,"LKJH"
         db " .MNB"
