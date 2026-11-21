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
; ============================================================

; ---- Zónák (fázis-2 memóriatérkép) ----
SYSVARS     EQU 0x4000
FRAMES      EQU 0x4025        ; 50 Hz óraszámáló
PROFIL      EQU 0x4100        ; PROFIL védett blokk (256 B)
DFILE       EQU 0x4200
MOTORBASE   EQU 0x4600
SZOTAR      EQU 0x5600
KB_BASE     EQU 0x6C00        ; ALAPMAG: betöltött tudáslánc (kb_compile)
CHAT        EQU 0x6000
MUNKAT      EQU 0x6800
TARTALEK    EQU 0x7E00
VEREMTOP    EQU 0x7FFF

; ---- PROFIL eltolások ----
PROF_NAME   EQU PROFIL+0x08
PROF_FLAGB  EQU PROFIL+0x1C
PROF_TEMP   EQU PROFIL+0x1D

; ---- Munkaterület puffer-alap ----
PB          EQU MUNKAT
BLINE       EQU PB+0x00       ; beviteli sor (64 B)
LINELEN     EQU PB+0x40
TOKBUF      EQU PB+0x48       ; token-ID-k (64 B)
TOKCNT      EQU PB+0x88
INTENT      EQU PB+0x89
DFCUR       EQU PB+0xA0       ; 2 bájt: D_FILE-kurzor
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

        ORG MOTORBASE

; ================= INDULÁS =================
START:
        LD SP,VEREMTOP
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
PROFOK:
        CALL BIGRBASE           ; bigramm-tábla címének kiszámítása
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

; ================= FŐCIKLUS =================
MAINLOP:
        LD HL,TXTPROMPT
        CALL PRTLN
        CALL READLINE
        LD A,(THINKFLG)
        OR A
        JR Z,NOSHOW
        LD HL,TXTTHINK
        CALL PRTLN
        CALL NEWLINE
NOSHOW:
        CALL TOKENIZE
        CALL REASON
        CALL GENERATE
        JR MAINLOP

; ================= KÉPERNYŐ =================
; CLRSCR: 24 sor × (32 szóköz + 0x76-terminátor), majd D_FILE-lezáró 0x76
CLRSCR:
        LD HL,DFILE
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
        LD (DFCUR),HL
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
        CP 0x76
        JR Z,SPC_OUT
        CP 0xC0
        JR NC,SPC_OUT
        LD HL,(DFCUR)
        LD (HL),A
        INC HL
        LD (DFCUR),HL
SPC_OUT:
        POP HL
        RET

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
        LD DE,64
        XOR A
RD_CL:
        LD (HL),A
        INC HL
        DEC DE
        LD A,E
        OR D
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
        LD A,B
        PUSH AF
        CALL SAFEPCHR
        POP AF
        LD A,(LINELEN)
        CP 62
        JR Z,RD_L
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
        JR Z,SC_X
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
        LD HL,TXTSAVED
        CALL PRTLN
        CALL NEWLINE
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
; kurzor a következő sor elejére (a 0x76 terminátor a helyén marad)
        PUSH AF
        LD HL,(DFCUR)
        LD A,L
        AND 0x1F
        CPL
        ADD A,33                ; a sor hátralévő része (32 + terminátor)
        LD E,A
        LD D,0
        ADD HL,DE
        LD (DFCUR),HL
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
        LD A,B
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
        CALL CHARFALL
        JR TOK_L

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
        CP 2
        JR Z,GEN_KB
        CALL BGWRITE
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
        LD A,(BGFROM)
        CALL BGCHOOSE
        OR A
        JR Z,BG_END
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

; BGGOTO: A = token-ID -> DE = csoport címe (DE=0, ha nincs átmenet);
; PAR nullázva (az olvasás mindig párosan indul)
; bigramm-tábla: [ntok][2 bájtos eltolások tokenenként][csoportok...]
BGGOTO:
        PUSH BC
        PUSH HL
        LD C,A                  ; A-window: token elmentve
        XOR A
        LD (PAR),A
        LD A,C
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
        POP HL
        POP BC
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

; BIGRBASE: BIGR = a szótár-végjel utáni első bájt (a bigramm-tábla)
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

; ================= ADATOK =================
DEFNAME:    db "GUEST",0
TXTSPLASH:  db "P I O C O  A I",0
TXTHELLO:   db "Hi! Ask me anything.",0
TXTPROMPT:  db "> ",0
TXTTHINK:   db "[thinking]",0
TXTDUNNO:   db "Still learning about that.",0
TXTNAM:     db "",0
TXTTEMPSET: db "[temp ",0
TXTREASON0: db "[reasoning off]",0
TXTREASON1: db "[reasoning on]",0
TXTSAVED:   db "[save stub: later]",0
TXTABORT:   db "[abort]",0

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
