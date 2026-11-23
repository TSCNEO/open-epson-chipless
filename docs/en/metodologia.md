# Methodology: how patch points are located

This is the document that lets you extend the project to another version or another model. It does
not list addresses: it teaches the procedure by which they were obtained. Addresses without a
method expire with the manufacturer's next build; the method does not.

Everything is done on the official firmware, without hardware and without proprietary tools.

## Shortcut: `tools/descubrir.py`

The procedure in this document is automated. On any official firmware:

```sh
python3 tools/descubrir.py FW.efu                                     # report
python3 tools/descubrir.py FW.efu --trampolin <va> --flush <va> \
        --emitir-spec data/patches/<familia>/<version>.json           # spec draft
```

On its own, by fingerprints of the binary and not by table, it finds:

| What it looks for | How it recognises it |
|---|---|
| Chip read wrapper | prologue with `lr` + retry counter 3 + error code `0x2A` |
| Chip write wrapper | sibling with the same prologue in the following 1 KiB |
| Presence function | asks for registers `0x67` and `0x68`, combines them with shift `#2` and compares against `1` |
| Patch point of the presence | the `mov rD, #0` of the false exit |
| Aggregator | the function that calls the presence and walks the channels with `cmp #4` |
| Calls to the aggregator | every `bl` to that address, with its context |
| Free space | longest run of `0xFF` in the prefix, aligned to 256 |
| Boot hooks | `ldr pc, [pc, #-4]` whose pointer falls in RAM |

Tool validation: on `EF20J9` it rediscovers the 5 core points of the table that was tested on
hardware, with the same original opcode and the same new opcode, the same free space
(`0x00032100`), the same boot destination (`0x41EAD6E8`) and the same 34 calls to the aggregator.

**What it does not guess, and why:**

- **The boot hook.** There are 61 `ldr pc, [pc, #-4]` veneers identical in structure; the valid one
  is the one that actually executes at boot, and that cannot be deduced from the binary without
  tracing the boot. It is passed with `--trampolin` and confirmed on hardware (if the ink
  indicators are still measuring, the hook did not run).
- **The D-cache cleaning function.** The tool lists the candidates (`mcr` primitive and
  wrappers), but choosing the correct signature affects stability: it is passed with `--flush`.
- **Which calls to the aggregator to neutralise.** It lists all 34 with context; the selection is a
  human judgement and has to be justified.

Everything else — which is the hard part — comes out automatically.

---

## Step 0. Before looking for anything: understand the boot

A patch in RAM only works if you know **when** the code you want to touch executes and
**from where** it executes. Two questions:

1. Which regions are compressed and to what address are they expanded?
2. Is there an entry point at which everything is already expanded, RAM is writable and the
   business logic has not run yet?

You answer that by reading the IPL header and its segment descriptors (`./arquitectura.md`,
sections 2 and 4). In this family the answer is a two-instruction trampoline at the end of the
prefix:

```
0x0001633C   E51FF004   ldr pc, [pc, #-4]
0x00016340   <puntero>  -> destino
```

**How to find it without knowing it in advance:** look for the pattern `04 F0 1F E5` (little
endian) in the part of flash that is *not* compressed. An `ldr pc,[pc,#-4]` is rare in normal
code: it is almost always a table jump or a hook point. Confirm that the pointer that follows it
falls inside a region that the boot decompresses, and you have the spot.

## Step 1. Look for physical free space in the prefix

You need room for your routine that will not be overwritten, and that is in an executable area.

- Walk the prefix (XIP region) looking for the longest run of `0xFF`.
- Discard any area that is referenced by a pointer: check that the start address does not appear as
  a little endian word anywhere in the prefix or in the headers.
- In `EF20J9` there are 57 320 B free from `0x00032018`; `0x00032100` is chosen (aligned to 16 and
  with margin ahead) and 196 B of routine plus 1 800 B of slack fit.

## Step 2. Decompress the block that contains the logic

The `CROM` containers are inside `seg1`. For each one:

1. Locate the `CROM` signature and the `FF D8` block that gives its length.
2. Decode the Huffman tables (`FF C4`, three JPEG DHT-style tables with ids `0xF0/0xF1/0xF2`).
3. Decode the Huffman stream (`FF B1`): triplets that produce literals or LZ77 copies.
4. Concatenate the literals from `FF B2` at their corresponding position.

`tools/epson_rcx.py` does exactly that in `_decompress_crom_part`. Always check it against the
SHA-256 of the decompressed block: if it changes, you are looking at another binary and any address
from an earlier table is poison.

## Step 3. Locate the cartridge subsystem without symbols

There are no names here. You navigate with clues that the compiler leaves behind and that are
stable across versions:

**a) The error code.** When an operation against the chip fails, the firmware records a code. In
this family it is `0x2A`, and it appears on the failure path of both access wrappers. Look for
`mov rX, #0x2A` followed by a `str` to a global variable: that gives you the access function and,
by proximity, its sibling (read and write are usually contiguous, with the same structure).

**b) The retry counter.** The wrappers retry a small number of times (3). That `cmp rX, #3` with a
loop that decrements is another recognisable signature.

**c) The "present" bits.** The firmware reads two registers from the chip and combines them:

```
presente = ((reg_67 << 2) | reg_68) == 1
```

By looking for the constants `0x67` and `0x68` together and a left shift by 2, the function that
computes that value and its output appear.

**d) The aggregator.** It is the function that calls the previous computation **once per channel**
and returns true only if all of them answer true. Find it by counting references: it is the
function that receives the most `bl` from different places in the block. In `EF20J9` it has 34
calls.

## Step 4. Choose what to patch (and what not to)

Rule: **patch the decision, not the sensor.**

| Strategy | Effect | Risk |
|---|---|---|
| Disable the chip read | No read succeeds | Paths that distinguish "error" from "absent" are left inconsistent |
| Force the "present" value in the comparison | Every query answers present | It is the point used by the whole block: minimal impact |
| Disable the calls to the aggregator | Those specific calls stop blocking | You only cover the ones you patch |

The three are combined, but with judgement:

- Read and write wrappers: return success immediately (`mov r0,#0` + `bx lr`). That way no error
  path fires.
- The "present" computation: force the return to `1`. It is a single point and it affects all the
  channels.
- The calls to the aggregator that trigger a block or a warning: replace the `bl` with `mov r0,#0`.
  **Do not replace them all blindly**: if one of those calls governs something else (a calibration,
  for example), breaking it introduces faults that are hard to diagnose. In this project 9 of 34
  are neutralised and the rest are documented as unverified.

## Step 5. Verify every opcode before writing

For each candidate address:

1. Decode the instruction and check it by hand: is it a function prologue, a `bl`, a `mov`?
   If you expect a `bl` and there is a `strb`, you have arrived 4 bytes late.
2. Check the context: the 2 preceding instructions and the 2 following ones must make sense
   with what you believe the function does.
3. Store the **original** opcode in the patch table. Not as documentation: as a control. The
   builder compares it before writing and aborts if it does not match.

That control is what prevents the classic failure: reusing a table from another build. Between two
versions of this same family, inserting a literal shifts the code and three of the fifteen points
end up 4 bytes further on; patching there corrupts neighbouring instructions and the printer does
not boot.

## Step 6. Design the hook routine

Requirements it must meet, in this order:

1. **Preserve registers.** Save and restore everything you touch, including `lr`. The original
   destination expects the CPU state exactly as it was.
2. **Write the words to RAM, not to flash.** The block is already decompressed at this point.
3. **Flush caches.** ARM926 processors with Harvard caches need, after writing code:
   - `mcr p15,0,r0,c7,c10,0` — clean + invalidate D-cache
   - `mcr p15,0,r0,c7,c5,0` — invalidate I-cache
   - `mcr p15,0,r0,c7,c5,6` — flush BTB
   - `mcr p15,0,r0,c7,c5,4` — prefetch flush
   Without this, the CPU executes old instructions from the cache and the patch "does nothing"
   intermittently, which is the worst possible fault to diagnose.
4. **Jump to the original destination**, not do a `bx lr`: the trampoline replaces a jump, not a
   call.

The table of `(address, opcode)` pairs lets you add or remove patches without recompiling the
routine: you only change the JSON.

## Step 7. Validate without hardware

Three checks, in this order, and all automatic:

1. **Integrity:** recompute `sum16` and the IPL SHA-1. Without this the loader rejects the image.
2. **Bounded diff:** compare the prefix byte by byte against the original. Only the trampoline
   pointer and your routine may change. Any other byte is an offsets error.
3. **Containers intact:** `Z_2`, all the decompressed `CROM`s, the kernel and the SquashFS must
   keep their SHA-256. If the design is good, you have not touched any of them.

`tools/verificar.py` implements all three. If you publish a new version, the hash of your build
must be reproducible: two runs on different machines have to give the same SHA-256.

## How to know whether the patch is active

Without opening the printer: the ink indicators on the printer's web page turn to permanently full
and stop responding to the cartridges. If they are still measuring, the hook did not run: check the
trampoline pointer and that the routine is at the address you believe.

## Mistakes we have already made

- **Confusing coordinates.** The data block has an 8 KiB header in front of it; an offset that is
  valid in flash coordinates is not valid in block coordinates, and vice versa. This particular
  mistake cost a whole round of debugging: the builder was reading the trampoline 8 KiB before
  where it was.
- **Assuming opcodes.** Filling the table with "reasonable" values (`0xEB000000`) makes validation
  pass by chance and the patch do nothing. Opcodes are taken from the binary.
- **Recompressing the block.** It was attempted the "elegant" way and it does not fit: 498 272 B
  decompressed against 307 200 B of physical free space. The patch in RAM is not a shortcut, it is
  the only viable option without an exact LZ77 compressor.
