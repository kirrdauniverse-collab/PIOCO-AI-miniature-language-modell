; ============================================================
; PIOCO AI — Z80 motor (3. fázis, első működő kivágás)
; Cél: Sinclair ZX81, 16 KB RAM
; Memóriatérkép: MISTRAL/fazis-2-tervezes-es-dizajn/01-memoria-terkep.md
;
; v1-megjegyzések (a 4. fázis emulátortesztje véglegesíti):
; NYELVI DÖNTÉS: a prototípus ANGOL nyelven fut (kevesebb bájt, ASCII-only);
; a magyar nyelvi finomítás a kiforrott modell utáni fázis.
;
;  - a billentyűzet bitf át/jelentése (port 0xFE, sorkiválasztás)
;  - az ASCII -> ZX81 karakterkód-tábla pontos értékei
; ============================================================

; ---- Zónák (fázis-2 memóriatérkép) ----
SYSVARS     EQU 0x4000
FRAMES      EQU 0x4025        ; 50 Hz óraszámláló
PROFIL      EQU 0x4100        ; PROFIL védett blokk (256 B)
DFILE       EQU 0x4200
MOTORBASE   EQU 0x4600
SZOTAR      EQU 0x5600
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
; üres PROFIL: alapértelmezések (a személyes kérdezés a 4. fázis INPUT-jával)
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

; GETKEY: A = ASCII billentyű vagy 0 (v1: legszélső beütésenként)
GETKEY:
        LD HL,KEYROWS
        LD B,5
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
        JR GK_HIT
GK_NX:
        INC HL
        DJNZ GK_R
        XOR A
        RET
GK_HIT:
        PUSH AF                 ; aktív bitek
        LD A,5
        SUB B                   ; sorindex 0..4
        LD D,A                  ; D = sorindex (megmarad)
        POP AF
        LD C,0
GK_B:
        RRA
        JR C,GK_BH
        INC C
        JR GK_B
GK_BH:
        ; index = 5*sorindex + bitindex
        LD A,D
        LD E,A
        ADD A,A
        ADD A,A
        ADD A,E                 ; 5×sorindex
        ADD A,C                 ; + bitindex
        LD E,A
        LD D,0
        LD HL,KEYTBL
        ADD HL,DE
        LD A,(HL)
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
RD_L:
        CALL GETKEY
        OR A
        JR Z,RD_L
        CP 13
        JR Z,RD_DONE
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

; CHARFALL: az aktuális szó betűtokenekré bontása (0x80+c)
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
        PUSH BC
        LD B,A
        INC DE
DL_S1:
        INC DE
        DJNZ DL_S1
        INC DE                  ; token-ID bájt
        POP BC
        JR DL_L
DL_CMP:
        PUSH HL
        PUSH DE
        PUSH BC
DL_C1:
        LD A,(DE)
        CP (HL)
        JR NZ,DL_NM
        INC DE
        INC HL
        DEC C
        JR NZ,DL_C1
        POP BC
        LD B,C                  ; B = hossz; az id-ig kell lépni
        POP DE                  ; DE = eredeti hossz-bájt pozíció
        POP HL
        PUSH BC
        INC DE
DL_S2:
        INC DE
        DJNZ DL_S2
        LD A,(DE)               ; token-ID
        POP BC
        LD B,A
        POP HL
        POP DE
        RET
DL_NM:
        POP BC
        POP DE
        POP HL
        JR DL_STEP
DL_MISS:
        LD B,0
        POP HL
        POP DE
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

; ================= REASONING (v1) =================
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

; ================= GENERÁLÁS (v1) =================
GENERATE:
        LD A,(INTENT)
        CP 2
        JR Z,GEN_KB
        CALL PICKFRAME
        CALL PRTRESP
        RET
GEN_KB:
        CALL KBLOOK
        RET

; PICKFRAME: 2 váz közül véletlen (R + FRANCES keverék), RESP-be
PICKFRAME:
        PUSH HL
        PUSH DE
        PUSH BC
        CALL RND
        AND 1
        LD HL,FRAMES0
        OR A
        JR Z,PF_0
        LD HL,FRAMES1
PF_0:
        LD DE,RESP
        LD BC,40
        LDIR
        POP BC
        POP DE
        POP HL
        RET

; RND: A = véletlen bájt (R regiszter + FRAMES + seed)
RND:
        PUSH DE
        LD A,R
        LD E,A
        LD A,(0x4025)
        XOR E
        LD HL,RNDSEED
        ADD A,(HL)
        RRCA
        LD (RNDSEED),A
        POP DE
        RET

; KBLOOK: [kulcsszó][0][tény][0] lánc bejárása ALAPMAG-elmé? (v1: táblám)
KBLOOK:
        LD HL,KBTAB
KB_L:
        LD A,(HL)
        OR A
        JR Z,KB_NONE
        PUSH HL
        PUSH DE
        EX DE,HL
        LD HL,BLINE
        CALL KWDEQ
        POP DE
        POP HL
        OR A
        JR NZ,KB_HIT
        ; kulcsszó átugrása: 0-ig, majd a tény 0-ja után
        PUSH BC
        XOR A
        LD B,0
KB_S1:
        LD A,(HL)
        INC HL
        OR A
        JR NZ,KB_S1
KB_S2:
        LD A,(HL)
        INC HL
        OR A
        JR NZ,KB_S2
        POP BC
        JR KB_L
KB_HIT:
        INC HL                  ; a tény-szöveg eleje
        CALL PRTLN
        CALL NEWLINE
        RET
KB_NONE:
        LD HL,TXTDUNNO
        CALL PRTLN
        CALL NEWLINE
        RET

; PRTRESP: RESP puffer (szöveges vázk) kiírása
PRTRESP:
        LD HL,RESP
        CALL PRTLN
        CALL NEWLINE
        RET

; ================= ADATOK =================
DEFNAME:    db "GUEST",0
TXTSPLASH:  db "P I O C O  A I",0
TXTHELLO:   db "Hi! Ask me anything.",0
TXTPROMPT:  db "> ",0
TXTTHINK:   db "[thinking]",0
TXTDUNNO:   db "Still learning about that.",0
TXTNAM:     db "",0

; vázlatszövegek (token-alapú generátor a 4. fázisban lép helyette)
FRAMES0:    db "Interesting question, let me think.",0
FRAMES1:    db "I have my own answer for that.",0
RESP:       EQU PB+0xB0             ; 32 bájtos válasz-puffer

; keyword -> intent: [keyword][0][intent]
INTKWTAB:
        db "WHAT",0,2
        db "WHO",0,2
        db "WHY",0,2
        db "REMEMBER",0,5
        db "DRAW",0,8
        db "SAVE",0,8
        db 0

; knowledge table: [keyword][0][fact][0]
KBTAB:
        db "HELLO",0,"Hello there! Nice to meet you.",0
        db "CAT",0,"Cats are lovely companions.",0
        db "ZX81",0,"I think at 3.25 MHz with 16 KB of RAM.",0
        db 0

; ASCII(32..127) -> ZX81-kód; SAFEPCHR tiltja a 0x76-ot és 0xC0+ kódokat
; (végső értékeket a 4. fázis emulátor-összevetése véglegesíti)
ASCTAB:
        db 0x00,0x0B,0x14,0x0D,0x15,0x13,0x16,0x12   ; 0x20..0x27
        db 0x1A,0x1B,0x1B,0x0C,0x0D,0x1B,0x1B,0x1B   ; 0x28..0x2F
        db 0x1C,0x1D,0x1E,0x1F,0x20,0x21,0x22,0x23   ; 0..7
        db 0x24,0x25,0x1B,0x1B,0x1B,0x1B,0x1B,0x1B   ; 8..9 : ; < = >
        db 0x1B,0x26,0x27,0x28,0x29,0x2A,0x2B,0x2C   ; @ A..G
        db 0x2D,0x2E,0x2F,0x30,0x31,0x32,0x33,0x34   ; H..O
        db 0x35,0x36,0x37,0x38,0x39,0x3A,0x3B,0x3C   ; P..W
        db 0x3D,0x3E,0x3F,0x1B,0x1B,0x1B,0x1B,0x1B   ; X Y Z [ \ ] ^ _
        db 0x1B,0x26,0x27,0x28,0x29,0x2A,0x2B,0x2C   ; ` a..g
        db 0x2D,0x2E,0x2F,0x30,0x31,0x32,0x33,0x34   ; h..o
        db 0x35,0x36,0x37,0x38,0x39,0x3A,0x3B,0x3C   ; p..w
        db 0x3D,0x3E,0x3F,0x1B,0x1B,0x1B,0x1B,0x1B   ; x y z { | } ~

; billentyűzet sorai és bit->ASCII térképe (4. fázison véglegesítés)
KEYROWS: db 0xEF,0xF7,0xFB,0xFD,0xFE
KEYTBL:  db "12345"
         db "QWERT"
         db "ASDFG"
         db "ZXCVB"
         db "09876"
