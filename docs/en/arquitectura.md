# Firmware architecture and this patch

Everything below was obtained from the official firmware `20.25.EF20J9` of the `FWF731TL` family
(XP-243 / XP-245 / XP-247). No hardware is required to check it.

## 1. The `.rcx` container

An `.efu` is a ZIP with a single `.rcx` member. The `.rcx`, in turn:

1. **ASCII manifest** terminated by `0x0C`, preceded by the header
   `RCX\r\nSEIKO EPSON EpsonNet Form\r\n`. Relevant fields:
   - `[D] 3="20.25.EF20J9.FY16"` — version read by the updater. If it is not greater than the
     installed one, the updater refuses.
   - `[Z_1] 5="7483392"` and `[Z_2] 5="2109440"` — exact sizes of the two zones.
2. **Two contiguous `EPSON IPL` blocks**, `Z_1` and `Z_2`.

## 2. IPL header and its integrity

Each zone begins with a header:

| Offset | Content |
|---|---|
| `0x00` | signature `EPSON IPL` |
| `0x0E` | `<H` length of the descriptor table (`0x6C` = 3 slots of `0x24`) |
| `0x10` | descriptor of `seg0`: `<HHIII` = type, sum16, bank, flash_offset, length |
| `0x34` | descriptor of `seg1`: same, and at `0x44..0x58` the SHA-1 of `seg1` |
| `0x1000` | `seg0`, 8,192 B: IPL loader. Identical across versions |
| `0x3000` | `seg1`, the image written to flash |

There is no asymmetric signature. Integrity is two checks:

```
sum16 = (sum of all bytes of seg1) mod 65536        -> descriptor + 0x02
sha1  = SHA1( seg1 || SHA1( header[0:0x0E] ) )      -> 0x44..0x58
```

Any repackaging of our own must recompute both. That means a modified image is
**accepted by the loader without any key**.

## 3. The compressed block `Z0_CROM3`

Inside `seg1` there are `CROM` containers. The one of interest starts at flash offset
`0x210000` and has two parts. Each part:

```
"CROM"            (only before part 0)
FF D8  <u32 BE block length>
FF C4  <u16 len>  3 Huffman tables, JPEG DHT style (ids 0xF0, 0xF1, 0xF2)
FF B1  <u16 len>  1 version byte + coded_bytes(u32) + num_items(u32) + Huffman stream
FF B2  <u16 len>  lit_len(u32) + uncompressed literals
```

The Huffman stream emits triples `(control, offset_lo, offset_hi)`. With `offset = 0` it is a
literal of `control + 1` bytes; with `offset != 0` it is an LZ77 copy of `control + 2` bytes from
the window. **It is not encryption**: it is a compressor. `tools/epson_rcx.py` decodes it without
keys.

## 4. Flash and RAM map

| Region | Flash (`seg1`) | Size | RAM destination |
|---|---|---:|---|
| Bootloader (`BooSt`) | `0x000000`–`0x010000` | 64 KiB | not copied |
| Prefix / RTOS base | `0x010000`–`0x040000` | 192 KiB | XIP at VA `0x00010000` |
| `Z0_CROM1` | `0x040000`–`0x0D0000` | 576 KiB | `0x41DEB180` |
| `Z0_CROM2` (resources) | `0x0D0000`–`0x210000` | 1.25 MiB | `0x41CA6A60` |
| `Z0_CROM3` (cartridges) | `0x210000`–`0x24AA9D` | 240 KiB compressed | `0x41C2D000` |
| MMU L1 table | `0x25B000` | 21 KiB | — |
| Linux uImage | `0x260400` | 1.06 MiB | ARM kernel |
| Root SquashFS | `0x370000` | 910 KiB | root filesystem |
| Network SquashFS | `0x470000` | 2.2 MiB | `nwsoc`, Wi-Fi |
| `Z_2`: `Z1_CROM0` | bank 1, from `0x10` | 1.7 MiB compressed | `0x41E46ADC` |

The `Z0_CROM3` block is decompressed to `0x41C2D000`. The routines that talk to the cartridge
chip live there.

## 5. Boot sequence

1. The prefix copies 1 MiB of flash to `0x43F00000` and remaps VA `0x00000000` to that address.
2. It decompresses the four CROM blocks to their RAM bases.
3. It cleans and invalidates caches.
4. It jumps to the trampoline `VA 0x0001633C`, which is `ldr pc, [pc, #-4]`: it reads the pointer
   stored at `0x00016340` and jumps there. In the factory firmware that pointer is `0x41EAD6E8`, an
   empty entry point: at that stage everything is already decompressed and the region `0x41C2D000`
   is writable and executable.

## 6. The patch

It uses **57,320 bytes of free space in `0xFF`** at the end of the prefix (`0x00032018` onwards):

1. A 196 B routine at `VA 0x00032100`, our own code:
   it saves `{r0-r4, lr}`, walks a table of 15 `(address, opcode)` pairs, writes each word
   at `0x41C2D000+`, calls `0x00015840` (clean + invalidate of D-cache), invalidates I-cache, BTB and
   does a prefetch flush (`mcr p15, 0, r0, c7, c5, 0/6/4`), restores the registers and jumps to
   `0x41EAD6E8`.
2. **A single word** is changed at `0x00016340`: from `0x41EAD6E8` to `0x00032100`.

On every boot the patch is reapplied. Nothing is written into the compressed block.

## 7. Why patch in RAM instead of recompressing

Recompressing requires a real CROM compressor: `Z0_CROM3` occupies 498,272 B decompressed and the
physical free space before the MMU table is only 307,200 B between both parts. A literals-only
compressor does not fit; LZ77 with a 65,535 B window and canonical Huffman would be needed, and any
compression-rate error breaks the boot.

The RAM patch avoids that risk entirely: it does not touch a single byte of the compressed block, and
verification can prove that all containers keep their original SHA-256.

## 8. What is out of scope

- `Z_2` is not touched (it is verified byte by byte).
- The bootloader is never included: this way the USB recovery mode survives a bad image.
- Kernel, SquashFS and resources are not touched.

## 9. Known limits

The patches neutralise the check routines and the state aggregator, but the aggregator has
34 calls in the block and here only the 9 that trigger lockouts or warnings are neutralised. The
remaining ones could raise secondary messages during calibration or cleaning. They did not appear on
the tested unit, but the firmware has not been exercised in depth (long cycles, hot cartridge swap,
deep cleaning). See [verificado.md](./verificado.md).
