# Port status (v0.2.2)

Legend: **tested** = built and run in this repo's CI/sandbox;
**compiles** = build path provided, binary not produced here;
**source** = HAL written, needs the platform toolchain; **skeleton** =
structure + platform notes, entry points to verify.

| port | status | model class | console | disk | tape | learning |
|------|--------|-------------|---------|------|------|----------|
| host | tested | A/B/C/D | stdio | files | .rtp pulse file | mem + finetune |
| c64 (cc65) | source | C | kernal BSOUT | kernal LOAD + .d64 writer | kernal LOAD, turbo spec | mem |
| amiga (vbcc) | source | A/B/C | DOS console | AmigaDOS | serial stream (doc'd) | mem + finetune |
| zxspectrum (z88dk) | skeleton | C | z88dk stdio | DOS via HAL (todo) | RT-turbo (.tzx) + ROM (.tap) | mem |
| zx81 (z88dk) | built (16K T81 v0.5) | G | own D-file layer | - (model in image) | named multiload + ROM SAVE | profile + 10 events |
| c16 (cc65) | skeleton | D (C on Plus4) | kernal | 1551 (rare) | kernal tape | mem |
| enterprise (z88dk/sdcc) | skeleton | B | EXOS console | EXDOS | EXOS channel | mem |
| tvc | skeleton | C | ROM print | TDC (rare) | ROM cassette | mem |

## What IS proven (host-tested, bit-exact)

- The whole engine: int8 forward pass, per-row shifts, sampling, chat
  loop, fact memory, tape codec, fine-tuning, topic router, clock,
  dated journal, screen-RAM scratch tier (11/11 test suites green).
- The C engine is bit-identical to the numpy integer simulator
  (`tests/test_golden.c`): float model -> pack.py -> int8 blob -> same
  argmax/logits in C as in Python, on 100 golden vectors per class.
- RT-turbo round-trip incl. CRC rejection of an in-transit flipped bit
  and +-16% speed wobble.
- d64 images verified by read-back (5 files).

## Porting a new machine (checklist)

1. Copy the closest `ports/<machine>/hal_<machine>.c`.
2. Implement the 12 `rt_hal.h` functions. Console + tape-loading are the
   minimum; disk saves can return -1.
3. Pick the model class and set `-DRT_MAX_* -DRT_APP_MODEL_MAX` limits in
   the port Makefile (see BINARY_FORMAT.md for sizes).
4. Build with the engine .c files as-is; no engine edits are ever needed.
5. Test: `/info`, then a chat line, then `/teach` + ask, then `/load`.

Timing (measured patterns, see the plan PDF for details): the engine cost
per character is one int8 MAC per parameter; a Class C model is ~2-3 s per
character on a 1 MHz 6502 with software multiply, Class A ~1-2 s on a
7 MHz 68000.

## v0.2.2: screen-RAM scratch tier (docs/SCRATCH.md)

| machine | cells | bits | bytes | visual cost |
|---------|-------|------|-------|-------------|
| ZX Spectrum | 2048 | 8 | 2048 | top 8 rows show garbage |
| C64 | 200 | 8 | 200 | top 5 rows show garbage |
| C16/Plus4 | 200 | 8 | 200 | top 5 rows show garbage |
| ZX81 | 256 | 6 | 192 | top 8 rows show glyph noise |
| Amiga / Enterprise / TVC | - | - | - | OS/banking owns the screen |

Engine side is host-tested (unit tests + an end-to-end "power cycle"
through the emulated tier). The port-side cell addressing (Spectrum
thirds, ZX81 D-file layout, screen-code tables) follows the platform
manuals but is NOT hardware-validated yet - same status as the ports
themselves.


## v0.5.0: 16K ZX81 edition - boot chain, memory, cassette save

Layout (all addresses derived or scanned at runtime; D_FILE moved to
$7C00 so the model zone reaches $7BEF):

- $4009-0x407C sysvars (ROM-verified: IY=$4000, VERSN=$4009,
  D_FILE=$400C, RAMTOP=$4026)
- line 1: REM + engine (13 766 B) + 48-B persist tail (inside the
  line, below any line-2 edit point -> the ROM's own SAVE writes it)
- line 2: IF USR 16514 = 1 THEN LOAD "RTxxxxxx" ($7E+FP tails after
  every number literal - the S-STK-DEC requirement; the "2" literal
  in line 3 is $1E, not $20)
- line 3: IF USR 16514 = 2 THEN SAVE "RTBASE16" (the /save handoff)
- model: class G (ctx 8, emb 8, h1 5, 832 params, 1030-B blob) at
  the chain end, found by an "RTLM" magic scan ($7AFF..$4090) -
  immune to NEW/quickload rebuilding the display file elsewhere
- tag + name table (14 x 8 display-code names) follow the blob
- $7C00 D-file: rows 0-2 packed state ('RT2', 72 B -> 96 cells of
  6 bits), rows 3-7 the 5-row scrollback mirror; every cell
  0x00-0x3F (never $76, never >= $40 - the freeze rule)

Cassette: 15 blocks (RTBOOT01 boot + RTBASE16 + 13 Hungarian topic
packs). The boot asks date/time/name/gender, packs the profile into
the work rows and chains. app16 mines the user's lines for emotion
keywords (faj/boldog/szomoru/faradt/szerelmes) into 10 two-byte
events with a 14-day decay; /save mirrors the state into the line-1
tail and returns 2 so BASIC runs the ROM's SAVE over the rewound
tape position. SHIFT+1..4 set the sampling sharpness, SHIFT+9 the
two-pass reasoning toggle, SHIFT+5/0 page the scrollback.

The v0.4.5 pack/unpack lost byte b1's bits 6-7 (cell2 mask $03 on
pack vs $0F on unpack) - the state magic could never survive a
round trip. v0.5 fixes it in one place per binary (boot C, app asm
and $F0 + rrca x4) and sim_v05.py proves the full boot -> base ->
memory -> save -> reload round trip.

## v0.5.1 hotfix: instant emulator reset on load

Root cause: the v0.5.0 multiload's FIRST block (the boot) was a SHORT
image - the display file at $7C00 was not in the image, so on a freshly
reset machine the ROM's display generator ran away over uninitialized
RAM and the emulator auto-reset. Fix, back on the v0.4-proven pattern:
D_FILE restored to $7B00 (477 B of machine stack, the proven budget),
the boot and EVERY standalone .p are FULL images (pad + blank display
file + VARS marker - all fourteen .p files are 15 889 B, exactly the
size of the user's working v0.4.5 base), and inside the multiload only
the boot is FULL while the other fourteen blocks stay SHORT so the
packed state rows and the scrollback survive block swaps. The 48-B
line-1 REM tail is gone: the ROM's own SAVE already writes the D-file
(the state rows live inside the $4009..VARS-end save range), verified
by sim section 4. Engine 13 533 B. t81check16_v05 + sim_v05 green.

## v0.5.2 hotfix: the freeze root cause - the stack-top word at the wrong sysvar offset

Byte-comparing the new images against THREE independent references (the
z88dk appmake +zx81 canonical .P, the user's WORKING v0.4.5 rt16_base.p,
and the emulator-written demo.T81) exposed the real v0.5.0 regression:
the rewritten sysvars() had moved the $7FFD stack-top word from $4026 to
$4028 (a bogus "DF_SZ" write clobbered it). The emulator's quickload
takes the machine stack pointer from the word at $4026 - with $0002
there every call pushed into the ROM area and the machine died silently.
Also fixed: MSIZE 1970->1030 in app16.c (TAG_AT/NAMTAB_AT pointed 940 B
past the real tag/table, so the /topic name poke could never work) and
the unpack_state() asm, where the cell temporaries were loaded into D/E
while DE was the b[] target pointer - decoded state went to the ROM/void
instead of the state block, so profiles and memories never restored.
Sysvar region now byte-equal to the working v0.4.5 (one benign byte at
$4019 = appmake's canonical 0). Version strings on screen: v0.5.2.
Checker + sim green. Working dir marked GLM per the user's request.

## v0.5.3: the flicker fix - the ROM's lower screen respected

The user reported a FAST-like flashing picture ("only occasionally
visible"). The binary analysis showed the crt0 DOES call SLOW ($0F2B)
and never FAST - the flash came from the display-file/ROM state
mismatch: our files carried DF_SZ=0 while the canonical state (z88dk
appmake AND the emulator-written demo.T81, both) is DF_SZ=2 at $4022 -
the ROM owns the last TWO display rows as the lower screen, and our HAL
printed into rows 8-23 including those. Fixes: DF_SZ=2 in the builder
sysvars, HAL console narrowed to rows 8-21 (22-23 = the ROM's lower
screen, never written), the boot's hal_msleep pauses removed (an
infinite FRAMES busy-wait if the NMI ever stalls), banners v0.5.3.
Per the user's request every output file name now carries GLM + the
version (GLM_v053_rt16_*.p/.t81, GLM_v053_RT16_TOPICS.t81); the
standalone boot cassette is gone (a boot-only tape has nothing to chain
to - that was the "RT16_BOOT.T81 does nothing" report). Checker + sim
green.

## v0.5.4: the FAST symptom's real root cause - display re-assert in every block

The user still saw the FAST-mode behaviour after v0.5.3 ("the picture
only flashes for a moment when keys are pressed"). Binary analysis of
our v0.5.3 images AND the user's WORKING v0.4.0 reference (from their
uploaded "müködő alapok" zip) ruled out two earlier hypotheses: the
crt0's SLOW call is present and correct in both, and the compiled
code's IY usage is byte-identical between the working and the broken
build (5x PUSH IY, 0x IX - the -IXIY z80asm swap; not the cause). The
structural difference is the multiload chain itself: the ZX81 ROM's
tape LOAD command runs with the display deliberately OFF (FAST) for
read-timing, and after each block swap nothing re-enabled the
continuous NMI display - so the only frames ever generated were the
ones during getk()'s ROM keyboard scans, exactly one flash per key
poll. Fix: boot16.c and app16.c now re-assert the display at the very
start of main() - LD IY,$4000 (the ROM sysvar base, written as
"ld ix,$4000" because the -IXIY z80asm swap turns it into FD 21 00 40)
followed by CALL $0F2B (SLOW). This covers every entry path: emulator
quickload, the ROM's USR, and the post-LOAD chain continuation. The
checker now asserts the 7-byte sequence in all 15 blocks; engine
13542 B (was 13535 B), blocks 14899 B short, tape 225199 B, banners
v0.5.4, output names GLM_v054_*. Checker + sim green.

## v0.5.4: handover document for the next chat session

A dedicated handover document (in Hungarian, per the user's language)
was generated for continuing the work in a new chat:
docs/plan/GLM-retro-tinyllm-v0.5.4-atadasi-dokumentum.pdf. It freezes
the state this commit represents (main = 8c40c92, checker + sim green
on the built files) and carries everything a fresh session needs: the
project overview, the full version history with the root-cause lessons
(T81 container, FP tails after number literals, MAKE-ROOM/D_FILE
derivation, FULL vs SHORT multiload images, the $4026 stack-top word,
DF_SZ=2 and the lower screen, the FAST/NMI display re-assert), the
memory/tape/screen map (sysvars, RTLM scan, work rows), the rebuild and
check pipeline with the version-bump checklist, the GLM/GitHub
collaboration rules (naming, tabu files, PAT push), the open test
checklist for the user's real machine (the "something is not right"
report arrived without a concrete symptom; the banner version and the
dfile= diagnostic are the first questions), and the quick-start steps
for the new session. The generator lives in the workspace scripts/
(gen_atadas_pdf.py + atadas_cover.html, HTML/Playwright cover per the
pdf skill).

## v0.5.5: the constant-FAST symptom's REAL root cause - CDFLAG in the image header

The user reported v0.5.4 still ran "constantly in FAST mode" (one flash per
keypress, trembling CRT). The v0.5.4 theory (the ROM's tape LOAD leaving the
display off) was incomplete: the engines really do re-assert SLOW, but the
machine is switched to FAST EARLIER, at LOAD time, by our own image. Root
cause, proven three independent ways:

1. THE ROM: the ZX81's tape LOAD (IN-PROG, $037B) copies the whole image
   from $4009 (VERSN) over the system variables - INCLUDING CDFLAG at
   $403B. Bit 6 of CDFLAG is the SLOW/FAST mode flag (SLOW = $0F2B does
   SET 6,(IY+$3B); FAST = $0F23 does RES 6; the $0207 SLOW/FAST core
   gates the NMI display field on it). Our builder wrote 0x00 there, so
   every freshly loaded block left the machine in FAST: black screen,
   and because the keyboard polls (IN $FE) run with the NMI generator
   off, each poll breaks the hsync - hence the flash per keypress and
   the trembling picture. The ROM's own INITIAL routine ($03E5) stores
   exactly $40 into CDFLAG at every boot ("LD (CDFLAG),+40").
2. THE REFERENCES: the user's working cassettes (tinyllm-16k.p,
   rtframe_ok.p, retro_tinyllm.p) all carry 0x40 at $403B; all our built
   images carried 0x00 (a byte nobody compared before - the earlier
   three-way checks stopped below $402B, and the handover map even put
   CDFLAG at the wrong address $4034; $4034 is FRAMES, CDFLAG is $403B).
3. THE SIMULATOR: a ROM-level harness (scripts/zx81sim.js - the
   EightyOne-derived TypeScript core compiled headless + the real ZX81
   ROM + a named-load tape model) replays the whole user flow. With
   CDFLAG=0x00 the machine after LOAD is FAST/blank (CDFLAG=0, NMI
   generator off); with 0x40 the editor listing is visible immediately
   (report 0/0), and after RUN the boot block shows its logo and
   questions on a steady screen ("RETRO-TINYLLM 16K V0.5.5 / UJRA ITT
   VAGYOK UTMUTATO KELL? (I/N)").

Fix: tools/t81build16.py sysvars() now stores 0x40 at $403B in every
image (boot, base, topics - 15 blocks). The v0.5.4 in-code re-assert
(LD IY,$4000 + CALL $0F2B at each main() start) is kept as belt and
braces; the crt0 SLOW call was already present and correct (verified:
byte-identical between the user's working v0.4.5 and v0.5.4 - it was
never the problem). Version bump to v0.5.5: banners patched in
rtchat16.bin / rboot16.bin (byte-length-preserving, sources updated to
match), every output renamed GLM_v055_*. The checker was recreated as
tools/t81check16_v05.py (the sandbox copy was lost with the recycling)
and now also asserts CDFLAG=$403B=0x40 in every block - it rejects the
v0.5.4 files on exactly that byte. Checker green: 14 .p + 14 .t81 +
the 15-block GLM_v055_RT16_TOPICS.t81 (225199 B, sizes unchanged).
The ROM-level harness is the new sim: scripts/zx81sim.js (needs the
emulator core: git clone andrivet/zx81-typescript-emulator + tsc, see
its header).

## v0.5.6: the chain-load crash and the input/model fixes - three more root causes

The user tested v0.5.5: the FAST symptom was gone, but after the boot the
screen cleared and "nothing happened"; keypresses made the picture tremble.
Three independent bugs were found and fixed, plus one architectural issue
was pinned down and partially remedied:

1. unpack_state() (app16.c #asm) pushed cell2+cell3 but popped THREE times
   ("cell2 again" in a comment - the author assumed a second push that is
   not there). Net +2 bytes of caller stack per group, 24 groups: the RETs
   landed on garbage right after the chain LOAD -> the "screen clears,
   nothing happens" death. Fix: a length-preserving 62-byte rewrite of the
   loop at $4691 (one balanced push/pop, correct b0/b1/b2 reconstruction);
   the source was updated to match the binary.
2. The model blobs' embedded charset[0] is 0x0A ("\n", the training
   rtcharset.py), but the engine binary was compiled with "\r" (0x0D) -
   the lost build script's transformation. rt_model_load() rejected every
   blob at the charset compare (-6), so model_find() scanned the whole RAM
   for 10+ seconds and reported "no model". Fix: the 14 models16_v05 blobs
   now carry 0x0D with recomputed checksums (scripts/patch_models_nl.py;
   when the engine is recompiled from the current sources, the blobs must
   go back to 0x0A).
3. The ZX81 ROM's display machinery is register-hostile to long compiled
   C code: the NMI chain reads sysvars via (IY+n) - IY is the sccz80 frame
   pointer - and the $0038 maskable handler exits with POP + JP (HL),
   which derails user code (the CPU ends up executing the D-file's NOPs
   and $76 HALTs). v0.5.6 installs the z88dk "altint" remedy: a
   register-preserving copy of the display chain (tools/altint_v057.bin,
   178 B at $7A40, assembled from z88dk 2.5's zx81_altint sources with
   -mz80 -IXIY), called from every main() via the patched 7-byte #asm
   block (CALL $7A40). With it the engine starts, loads its model and
   prints the banner + chat prompt at a sane speed (proven repeatedly in
   the ROM-level simulator).
   REMAINING KNOWN ISSUE: the $0038's JP (HL) still strikes user code
   between display fields; runs are therefore unstable (the banner appears
   in some runs; in others a derailed switch dispatch jumps to $0000 and
   the machine cold-restarts). The complete fix is a z88dk 2.5 rebuild
   with the startup=2 environment (scripts/build_engine_v057.sh + the
   toolchain built from source at /tmp/z88dk): the proof program
   /tmp/zxtest/work.P (20 iterations of printf + 500 multiply-compute per
   line) runs flawlessly with it in the same simulator. That rebuild
   (17.7 KB vs the 13.5 KB budget - needs the custom minimal crt0 +
   layout work) is the next task.

Also fixed along the way: the checker now asserts the altint blob and the
CALL $7A40 sequence in every block. Sizes: the SHORT blocks 14899 ->
15081 B, the tape 225199 -> 227747 B (the altint blob + the rebuilt
images).

## v0.5.7: the v0.5.6 binaries were CORRUPTED - rebuilt cleanly + the input saga

The user's v0.5.6 report: the machine cold-restarted IMMEDIATELY on every
cassette (.p and .t81 alike). Root cause found by byte-diffing against the
v0.5.5 originals: both binaries were ONE BYTE SHORT (engine 13541 vs 13542,
boot 5136 vs 5137), the first divergence at $4279. A v0.5.6-era patch
experiment wrote 7 bytes over an 8-byte slice (the bytearray shrank), and
the later "revert" wrote 8 bytes back over 8 - restoring the length but
CONSUMING the innocent byte at the junction (the first byte of the
'LD HL,-1' in hal_getchar). Everything from $4279 on shifted one byte
down, so every absolute CALL/JP in the compiled code landed one byte into
the wrong instruction -> immediate, deterministic crash to $0000 on every
block. The TAPE STRUCTURE was always fine (the checker validated it) - the
embedded binaries were not, and the checker's length constants could not
catch it (the SHORT images are padded, so the sizes matched).

v0.5.7 = the clean rebuild from the pristine v0.5.5 binaries
(scripts/rebuild_binaries_v057.py - every patch step asserts the file
size), re-applying all four fixes:

1. version strings -> v0.5.7;
2. the unpack_state 62-byte stack-balance rewrite;
3. the altint CALL ($7A40) in every main();
4. the input helper at $41C8 (over the dead zx81_ascii body).

The builder now HARD-ASSERTS the binary sizes (engine 13542, boot 5137) so
a shifted/corrupted binary can never be packaged again. Verified in the
ROM-level simulator: the boot logo + questions, and the base banner
('TINYLLM V0.5.7', 'UDV /HELP', 'YOU>') both display reliably.

THE INPUT (the honest state, heavily investigated this session):
- The lib getk() returns ASCII but the old zx81_ascii() expected a ZX81
  glyph code -> every key decoded to -1 (dead input since v0.4.5!). A
  trampoline now routes hal_getchar to a 62-byte helper: getk for the
  letters (they echo correctly - 'SZIA' verified), plus a raw-port check
  for the NEWLINE key (getk misdecodes it as 'R').
- REMAINING LIMIT: the ROM's $0038 maskable-interrupt handler exits via
  POP + JP (HL). Under the engine (long C code) it fires ~every 24 T-states
  and randomly derails multi-instruction sequences: the raw ENTER check
  and the release-wait loops get corrupted often enough that the ENTER
  does not reliably submit the line (it echoes as 'R' and the wait loops
  can stall). DI/EI does not help (the ROM display chain itself executes
  EI); a 5-read majority vote was not enough. The complete fix is the
  interrupt-handler takeover (IM2 with a vector outside the stack area,
  e.g. the $79FF page-boundary word) - fully analysed, deliberately
  deferred to the next session with the z88dk 2.5 rebuild
  (scripts/build_engine_v057.sh + the work.P proof program).

## v0.5.8: the FAST-like picture loss fixed (MARGIN churn) + the input saga

The user's v0.5.7 report: the picture appeared ONLY while a key was held
(FAST-mode-like), the date/time/name questions accepted nothing, and the
machine froze after the gender answer. Root causes found and fixed:

1. THE PICTURE (fixed): the v0.5.7 poll loop called the lib getk ~1000x/s
   (the poll loop is actually ~30 kHz, gated only by the getk's own cost);
   every getk runs the ROM KEYBOARD which REWRITES MARGIN ($4028). That
   ~50-writes-per-field churn destroyed the display timing whenever the
   helper was NOT inside a key-wait - exactly "picture only while a key
   is held". Fix: a /64 rate gate (a counter byte at $4266) gives ~100 Hz
   getk slots - about twice the ROM editor's own keyboard cadence. The
   simulator now shows SLOW on 96-97% of frames with NO key held (was
   ~43%).
2. THE FREEZE (fixed): every multi-step release-wait loop we tried was
   eventually derailed by the $0038 chaos. There are NO wait loops at
   all now: after a key is reported, an 8-slot lockout (~40-80 ms)
   suppresses repeats (auto-repeat feel), and the flow can never hang.
3. THE CRASH (fixed): the raw-scan experiment (no ROM KEYBOARD at all)
   crashed deterministically 3/3 - the ROM display choreography NEEDS
   periodic keyboard calls to keep MARGIN updated. The getk stays, just
   rate-limited.

THE REMAINING LIMIT (honest, heavily investigated): the ROM's $0038
maskable handler does POP + register dance + JP (HL) per interrupt line.
Inside the ~500-cycle getk it lands mid-KEYBOARD/DECODE and corrupts the
H/L row data - the $0038's own B/C/H bookkeeping collides with the C
code's registers. Measured: letters often decode right ('n' processed,
"DATUM: EV?" reached), but digits and the NEWLINE key misdecode often
('2'->'4'/'R', the ENTER vanishing). Three takeover attempts were built
and rejected with evidence: (a) IM2 + bare RETI - the video died (the
$0038's 'LD R,A' IS the video output); (b) IM2 + hybrid handler (RETI
for C-code PCs, ROM dance for D-file PCs) - the display worked but the
C code starved (the NMI-CONT HALT launch depends on the $0038 dance);
(c) DI around the getk - forbidden: DI during the SLOW display deadlocks
the NMI-CONT's HALT on real hardware (the maskable INT is the wake
source). The REAL fix is the z88dk 2.5 rebuild with the proper crt0
(scripts/build_engine_v057.sh - its work.P proof program already runs
flawlessly), deferred to the next session with all this analysis.

State: boot logo + questions and the base banner/prompt display reliably
without keys; the flow advances past the I/N question; typing letters
works; digits/ENTER are unreliable (documented above).

## v0.5.9: the typing finally works (and what it took)

The user's v0.5.8 report: the picture trembles as soon as a question
polls input (stable while the logo draws), keys repeat insanely fast,
the same key gives different letters, and SHIFT+0 (RUBOUT/delete) does
nothing. Findings and fixes:

1. TREMBLE: every ROM KEYBOARD call inside getk rewrites MARGIN
   ($4028); at v0.5.8's ~100 Hz slot rate that is ~2 random-time
   writes per display field. v0.5.9's /255 gate gives ~25 Hz (~0.3
   extra writes/field; the ROM chain's own synchronous 1/field write
   is present in the stable logo phase too). Reduced, though only a
   full interrupt takeover could zero it - see below.
2. TOO-FAST REPEATS: v0.5.8's lockout decremented once per POLL
   (microseconds!). Now a 16-bit lockout word (~1792 polls ~ 300 ms)
   gates each reported key.
3. WRONG LETTERS: the $0038 chaos corrupts a single getk decode ~50%.
   Two consecutive getks must now AGREE or the result is discarded.
4. ENTER: the COMPILED getlines compare against CR (13) - visible as
   LD DE,$000D in both binaries (the checked-in .c sources say '\n';
   they were never recompiled). v0.5.8's LF was a regression. getk
   decodes NEWLINE as 'R' (82); a 3-read majority of the raw NEWLINE
   port line breaks the tie -> 13.
5. SHIFT+0: probed raw (both key lines) -> 8, before any getk call.

VERIFIED IN THE SIMULATOR: the complete boot interview - the I/N
answer, the full date 2026-12-25, the time 14:30, the name "dani",
the gender "f" - all typed, all ENTERs submitted, 3/3 runs without a
crash, the display stable (99.4% frames) throughout.

THE HONEST REMAINDER - the delete key: delivering the 8 into the
compiled getline needed a machine-code patch in the getline's filter
(the sources cannot be recompiled in the patch pipeline). Every
variant of that patch correlated with a flaky NaN crash (the $0038
chaos interacting with the patched hot path), so it is DISABLED in
the shipped build: the 8 falls through the <' ' filter harmlessly
and SHIFT+0 currently does nothing. Also documented: an 8-iteration
attempt to replace getk with a pure raw keyboard scan (zero MARGIN
writes = zero tremble) - every design hit the same wall: without
periodic ROM KEYBOARD calls the NMI display launch's row bookkeeping
degenerates and the D-file row traps in an endless loop. The full
analysis (the $0038 dance, the C==0 stale-HL self-lock, the emulator's
missing Z80 EI-delay, the row-stretch trap) is in this file's history
and the commit messages. The real fix for BOTH remaining issues is
the z88dk 2.5 rebuild with a proper crt0 (scripts/build_engine_v057.sh
- its work.P proof runs flawlessly) so the C sources (which already
handle '\n', backspace and clean input) can be compiled in.

## v0.6.0: the typing feels human (no repeats, no idle tremble)

The user's v0.5.9 report: typing is STILL too fast to use, and the
picture always trembles slightly. Both root causes found and fixed -
plus a testing bug of my own that had been hiding the truth:

1. TOO FAST: v0.5.9's lockout word decremented once per hal_getchar
   CALL - and the compiled input loops call it ~10 kHz, so the
   "300 ms" lockout was really ~60-150 ms and a normally-held key
   auto-repeated 3-10x. v0.6.0 removes auto-repeat entirely: a key
   is delivered once, and the next delivery requires the 'released'
   flag - set only after the any-key check sees every row empty.
   Verified: the full boot interview typed with 200 ms holds, 3/3
   runs, every digit and letter exactly once ("202612251430DANIF").
2. IDLE TREMBLE: NOT the MARGIN value (measured: it sits at a
   constant $37; every write is a value no-op). It is the
   R-register PHASE: the display rows' HALTs wake on the R&64
   interrupt, so any variable-size code burst between the rows
   shifts the following rows' pixel timing. The ROM editor is
   stable because its between-row code is fixed-size; v0.5.8/9 ran
   a getk (~1-2 ms variable ROM burst) at every poll - even idle -
   so the phase wandered constantly. v0.6.0's idle path is a fixed
   9-byte sequence (one port read with A=0 selects ALL 8 keyboard
   rows at once - the emulator models the full wired-AND) and zero
   ROM calls; the getk burst fires only on an actual new keypress.
   Measured: idle $02BB (ROM KEYBOARD) calls dropped from ~94 per
   300 idle frames (v0.5.9) to ~4 (all from the one real keypress).
3. THE TESTING BUG: my simulator harness's --sched option had
   started parsing "2150:2" as keycode 2 instead of the character
   '2' - three design revisions looked broken ("no echo!") while
   the wrapper was fine and the harness was pressing a nonexistent
   key. Found by sampling the raw IN result during the press
   (kbmap=0 with the key held). Also ruled out along the way: the
   $FD32 "trap" was the NORMAL display generation seen by an
   over-cap sampler; the C=1 experiment was abandoned (the $0038
   clean-return path DEC-erodes the caller's B register -> wild
   returns -> stack drift); LD C,8 stretches the NMI launch's
   first row. The wrapper now touches no registers the $0038 dance
   depends on and behaves exactly like every proven getk build.

Also fixed in the wrapper: the 'released' flag now starts at 1
(the image byte at $426B is initialized) - otherwise the very
first keystroke after boot was suppressed.

Kept from v0.5.9: the double-getk agreement, the raw NEWLINE
majority probe (ENTER=13), the raw RUBOUT probe (SHIFT+0 -> 8,
still inert in the getline - the BS patch remains disabled), and
shifted keys (SHIFT+1..4 hofok) reaching getk as in v0.5.8.

Known and unchanged: the engine's long generation runs can still
fall into the display-only starvation state (the pre-existing
chaos lottery, documented under v0.5.8/9) - the fix remains the
z88dk 2.5 rebuild with a proper crt0.

## v0.6.1: questions on separate lines + the ENTER gate before loading

The user's first real v0.6.0 report: typing finally works, but (1)
every question runs into the next on one line, (2) the end message
after the interview vanished immediately (the BASIC LOAD "RTBASE16"
started at once) and could not be read, and (3) after the loading
continued, the emulator appeared to reset - the text was lost.

1. QUESTIONS: the compiled boot had no leading newline on the
   question strings, so question + typed answer + next question all
   shared one row. Binary patch: all seven questions (and the end
   message) rewritten IN PLACE with a leading 0x0D - each exactly the
   same length as the original (the packed string table does not
   shift; one dropped trailing space or colon pays for the \r).
   Verified in the simulator: the first question now opens its own
   row (a blank row appears where the wrapped "(I/N)" used to run
   into it). The later questions cannot be verified in the sim: its
   interrupt model is harsher than real hardware (see below) and the
   compiled flow derails past the first getnum - but on the user's
   real machine all the questions print (that is what "they run
   together" means), so the same in-place leading-0x0D applies.
2. THE ENTER GATE: main()'s epilogue (LD HL,1 at $4E0B) is patched
   into a JP to a 14-byte stub in the corpse zone ($426E) that spins
   on hal_getchar until ENTER (13), then restores the original
   epilogue. The end message ("tekerj a rtbase16-hoz!
   enter=toltes") now stays on screen until the user has read it and
   positioned the tape - exactly the missing ingredient for a real
   tape workflow. The stub sits in both images (dead code in the
   engine); the released flag moved to $426B where the wrapper
   actually reads it (the v0.6.0 build had init=1 land on $426D by
   mistake - harmless, because the wrapper's no-key path writes the
   flag anyway, but now correct).
3. THE "RESET": this code path (the post-interview LOAD) had never
   been executed by anyone - until v0.6.0 fixed typing, no build
   could get through the interview. Analysis of the chain: the boot's
   BASIC line 2 (LOAD "RTBASE16") matches the tape's block name
   exactly (the builder maps both through zx_name()); the tape's base
   block is SHORT (no D-file), so the packed profile rows survive the
   block swap by design. The most likely causes of what the user saw:
   (a) the emulator's tape had nothing more to play after the boot
   block, so the ROM's LOAD looped forever on silence - a blank
   FAST-mode screen looks exactly like a reset; (b) the engine's
   start lost a chaos lottery (it has started reliably on real
   hardware since v0.4.5, so this is the less likely path); (c) a
   load error report. The ENTER gate mitigates (a) directly: the
   message now tells the user to wind the tape to the RTBASE16 block
   BEFORE pressing ENTER, and the separate GLM_v061_rt16_base.t81 can
   be loaded as its own tape at that point (its block name matches
   the LOAD). The engine's start cannot be verified in this
   simulator: its interrupt generation (the R&64 model firing in the
   blank too) is harsher than real hardware - the engine's main()
   dies within 3 frames of the quickload in EVERY version including
   the original v0.4.5 .p, while the same binary has always worked
   for the user on a real emulator. That divergence also explains
   why the sim cannot verify the later question rows (the flow
   derails after the first getnum) while the real machine prints
   them all.

## v0.6.2: SHIFT tremble, DELETE key, the chain-restart defense

The user's v0.6.1 hardware report: the boot loader runs perfectly and
typing is perfect, but (1) there is no delete key, (2) holding SHIFT
makes the screen tremble, and (3) after the ENTER gate the machine
"loads something for a moment" and then restarts.

1. SHIFT TREMBLE (root cause found in the wrapper): the any-key check
   read the keyboard with ALL 8 rows selected and tested the 5 column
   bits - SHIFT alone pulls column bit 0 low, so holding SHIFT made
   every poll think a key was down and run the full ROM getk scan
   (hundreds of T-states per poll); the display lines were starved
   and the picture juddered. v0.6.2 wrapper: the any-key check reads
   rows 1-7 (LD A,$01) and, separately, row 0 masked with $1E (Z X C
   V - bit 0 is SHIFT). SHIFT alone now reads as "no key": the idle
   path is two IN instructions and nothing else. Verified in the
   simulator: 900 frames of held SHIFT produce ZERO getk calls
   (v0.6.1 would have run thousands). SHIFT+another key still works
   (the other key's own row/col fires the check), SHIFT+0 still
   returns RUBOUT (the 0 key is in row 4).
2. DELETE (root cause: the compiled getline discarded every char
   below 32, so the wrapper's RUBOUT code 8 was thrown away - delete
   never existed in any version). The binary patch redirects the
   getline's 'c < space' branch ($4681, JP C) to a 33-byte stub in
   the corpse zone ($4238): if the char is 8 and n>0 it decrements
   the getline's n (found at SP+2 in the filter's stack layout,
   decoded from the compiled code) and erases visually by backing the
   putchar cursor variable ($4290) one step and printing a space over
   the last character. Verified in the simulator: typing 2, then
   SHIFT+0, then 2026 + ENTER yields the accepted year 2026 (without
   the fix the buffer would be 22026 and the getnum would re-ask).
   The delete key is SHIFT+0 - the ZX81's native RUBOUT position.
3. THE RESTART AFTER LOADING (defense-in-depth): disassembly of the
   ROM's $0038 interrupt handler shows the danger window: DEC C /
   JP NZ leads to a path that DISCARDS the pushed PC (POP DE) and
   jumps into the display chain - with C != 0 an interrupt during
   user code derails it; C == 0 continues to POP HL / DEC B / RET Z,
   the clean return. The rebuilt binaries call ALTINT_ON (the
   register-preserving chain, $7A40) at the very start of main(), so
   the raw-ROM window is only the crt0's span between its SLOW call
   and main: the SP save, the sysvar sets, the CALL - about 100
   T-states, 1-2 raw interrupts, with B/C whatever the SLOW and the
   load context left. A chained LOAD (a LOAD statement executed from
   a running program, which is what the boot's line 2 does) leaves a
   different register context than an editor LOAD - that difference
   is the leading suspect for "loads a moment, then restarts".
   v0.6.2 inserts LD B,1 / LD C,1 via a 7-byte stub ($4259) right
   after the crt0's SLOW call (the dead 'LD ($4110),SP' at $4094 -
   a write-only variable, nothing ever reads it - becomes the JP to
   the stub): one raw interrupt inside the window now takes the
   clean DEC C -> 0 / POP HL / DEC B -> 0 / RET Z path instead of
   the chaos launch. The engine's start cannot be verified in this
   simulator (its quickload lacks the ROM's CDFLAG context and the
   NMI model diverges from hardware), so this ships as a
   theory-backed defense - the definitive test is the user's real
   chain run.
   Also fixed along the way: the v0.6.2 wrapper's not-released path
   returned through the no-key label (which SETS released=1) - that
   would have re-enabled delivery while a key was still held and
   produced endless key repeats (caught in the simulator as a screen
   full of '2's; the path now jumps straight to the -1 return).

## v0.6.3: the English brain, the magyar topic pack

The user asked when there would be an evaluable version, plus seven
questions (tenses, plurals, numbers, mood expressions, other
languages, identity answers, DO/DOES) and proposed switching the model
to English for efficiency.

Facts established by probing the deployed blobs: the 14 deployed
models were HUNGARIAN and produced loop-gibberish ("a memem a kegyok")
- Hungarian morphology needs far more than 832 params. The corpus
generator in training/ is the generic English one for the other ports;
the 16k Hungarian corpora were never in the repo.

What shipped:
- training/corpus_gen16.py: deterministic English corpora, 12 core
  pairs (base) + 13 topic packs, all terse (<=15 chars answers: with
  ctx=8 the question tail anchors the answer's first ~7 chars, longer
  answers drift into generic english - measured), plus the user's
  asks: haha/wow/nooo/:( :) :O moods, do/does/did forms, past tense,
  plurals, the identity Q&A ("who made you?" -> "qwen and safar."),
  the language Q&A, and hungarian bridges.
- training/qat16.py: quantization-aware fine-tuning (q-dq + STE + Q7
  clip, scales rebuilt exactly like pack.py). Without it the float
  val 0.39 packed to int8 mush; with it the float-equivalent loss on
  the deployed path = 0.32.
- The magyar topic pack (RT-MAGYR, replaces RT-ELETV/"elet" - the
  engine label string patched to "magy"): szia, hogy vagy, ki
  keszitett -> "qwen es safar sandor", ki az a safar -> "buszsofor es
  csillagasz", beszelsz magyarul -> "persze, egy kicsit".
- Architecture hunt: h1=6 (1162 B) and h1=5 (1056 B) models learned
  verbatim (7/12 and 6/12 pairs on the base) BUT the builder's altint
  assert proved the true blob cap is the original 1030 B (the fixed
  $7A40 altint chain + the name table). The shipped 1030-B models
  (832 params) give fuzzy-but-English answers; exact verbatim needs
  either the interceptor or moving the altint - next round.
- Seed selection by packed-verbatim hits (scripts/train16_final.py),
  not float val-loss.
- MSIZE stayed 1030; t81build16/t81check16 swapped the lifestyle topic
  for magyar. ALL CHECKS PASSED.

## v0.6.4: the black screen and the once-only rubout - both fixed, sim-proven

The user tested v0.6.3 on their emulator: (A) only one character could
be deleted in the boot questions, (B) after the interview the chain
load flashed and the screen went fully black.

### Bug B - the black screen (FOUR stacked root causes, all real)

1. TAPE NAME ENCODING: EightyOne's LoadT81File generates the tape
   name record from the ASCII EO81 header via its ZXCharTable - which
   is off by one vs the real ZX81 code page (EO 'A'->0x27; the ROM
   char generator at $1E00 proves 'A'=0x26, and the user's own working
   screens confirm it). The ROM's IN-NAME compares tape bytes with the
   line-2 name slot byte-for-byte, so an EO-generated name never
   matches -> the ROM searches the tape forever -> blank screen (NMIs
   off during the search). FIX: every .t81 block payload now embeds
   OUR correctly-coded name record ([ZX codes, last byte |0x80]) at
   its start; when the first byte is not 0x00/0x01/0xFF EightyOne
   passes the payload through verbatim (zxnamelen=0) and the ROM
   consumes our record instead.
2. BLOCK TAIL TRUNCATION: EightyOne's loader scans back from the
   payload end for the last 0x80 byte and truncates everything after
   it. Our SHORT blocks ended with the name table (0x00 0x00) - 16 B
   of the altint chain were silently cut. FIXED by the same 0x80
   marker that now ends every SHORT image.
3. E_LINE INCONSISTENCY: the ZX81 ROM has NO block-end signal - the
   LOAD loop (the $01FC LOAD/SAVE check) runs until the write pointer
   reaches E_LINE. Our SHORT images ended at $7AF4 but carried the
   boot's E_LINE=$7E1A, so a real tape kept loading PAST our block,
   overwriting the display file with the next block's bytes. FIX:
   short_image() - E_LINE = the image end, VARS -> the 0x80 marker,
   the whole payload is a valid ZX81 program image.
4. NO AUTO-START: after a mid-program LOAD the ROM returns via the
   (live) ERR_SP frame into the NEXT-LINE loop ($0676), which walks
   one line past NXTLIN ($4029) and runs it. Our images carried the
   NEW-machine sentinel $7B00 there -> STOP-LINE -> the editor: the
   loaded engine never started. FIX: NXTLIN = $407D (line 1) -> the
   loop runs line 2 -> USR 16514 -> the chat starts.
   Also: the fresh model blobs needed the v0.5.7 charset[0] 0x0A->0x0D
   alignment (the old engine binary's compiled table) - without it
   rt_model_load rejected every blob ("NO MODEL DFILE=...").

   The sim now models all of this (the EO backscan truncation, the
   embedded name record, the ROM IN-NAME consumption) and the FULL
   chain is proven: LOAD "" -> boot interview -> ENTER gate ->
   LOAD "RTBASE16" (name match!) -> auto-start -> "TINYLLM V0.6.4"
   banner -> the chat prompt, with the boot's display file preserved.

### Bug A - the once-only rubout (a ONE-BYTE bug!)

Reproduced in sim (3x SHIFT+0 deleted one char). The wrapper delivered
all three rubouts (HL=8 x3 - logged!); the v0.6.2 getline BS stub
DECREMENTED THE WRONG STACK SLOT: `LD HL,2; ADD HL,SP` after popping
the char, but the frame layout (its own docstring!) has n at SP after
the pop - so the DEC hit a random stack byte (0x41->0x40->0x39,
logged!) and the line length NEVER shrank; the visual erase was
cosmetic only. FIX: the immediate 02 -> 00 in the boot's stub
($423F). Sim-proven: n goes 5->4->3->2 for three rubouts.

### Known gaps (next round)

- The /topic swap: the engine parses /topic 2, prints "toltom a
  temat...", returns BC=1 (the ZX81 USR convention - verified), and
  the ROM LOAD command runs - but the line-2 name slot still read
  RTBASE16 (the runtime poke did not fire) and the tape search did
  not complete in sim. Needs the poke_load_name path debugged.
- The engine's chat getline has NO delete yet (only the boot's was
  patched in v0.6.2) - SHIFT+0 in the chat is discarded by the
  compiled c<32 filter.
