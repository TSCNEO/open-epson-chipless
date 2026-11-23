# The cartridge subsystem and the 15 patch points

All addresses are RAM addresses in the **decompressed** image of `Z0_CROM3` for
`20.25.EF20J9`, whose base is `0x41C2D000`. The offset within the block is `VA - 0x41C2D000`.

`SHA-256` of the decompressed block, as a check that you are looking at the same binary:

```
b2ad8f8c7152fc8ca02c87bfaf2be5dd24f4ec914dfcdbffd404912f9f9eeb14   (498 272 bytes)
```

## What the printer checks, in order

According to the decompressed block, the check is **of presence and of counter reads**. There is
no signature or challenge-response exchange in these routines: there is no cryptography to forge,
only an answer to give.

1. **Chip access (CSIC).** Two wrappers, read and write. Each retries up to three
   times; if it gets no answer, it logs the error `0x2A` and returns failure.
2. **Presence bits.** Two registers are read (`0x67` and `0x68`) and combined:
   `present = ((r67 << 2) | r68) == 1`. If the chip does not exist, this yields `0`.
3. **Aggregator.** It walks the channels and returns "all present" only if each one answered `1`.
   It has 34 calls: some block printing, others only generate warnings.
4. **Consequence.** Without a chip, the aggregator returns `0` and the flows that depend on it block or
   warn. Ink levels come from reading the chip: without a chip there is no measurement, and that is why
   the patch leaves the gauges at a fixed full.

The patch acts on the first three levels at once, which is what makes sure no
path remains that can ask again.

## Functional groups

1. **CSIC chip access wrappers** — `0x41C2E07C` (read) and `0x41C2E120` (write).
   They retry up to three times; if they fail they log the error `0x2A` and return `1`.
2. **Check of registers `0x67` / `0x68`** — `0x41C2FC80`, with exit at `0x41C2FD28`,
   which computes `(r67 << 2) | r68` and returns `1` only if the result is `1` (cartridge present).
3. **State aggregator** — `0x41C2FD34`. It walks the channels calling point 2 and returns
   `1` when all answer `1`. **It has 34 calls** inside the block; several are the ones that
   trigger a lockout or a warning.
4. **Auxiliary check in `Z1_CROM0`** — `0x41C423C8` calls `0x41F9C240`.

## Patch table

| # | VA | Offset | Original opcode | New opcode | Effect |
|---:|---|---|---|---|---|
| 1 | `0x41C2E07C` | `+0x107C` | `0xE92D47F0` (`push {r4-sl, lr}`) | `0xE3A00000` (`mov r0,#0`) | CSIC read: immediate success |
| 2 | `0x41C2E080` | `+0x1080` | `0xE1A05001` (`mov r5, r1`) | `0xE12FFF1E` (`bx lr`) | closes the previous function |
| 3 | `0x41C2E120` | `+0x1120` | `0xE92D47F0` | `0xE3A00000` | CSIC write: immediate success |
| 4 | `0x41C2E124` | `+0x1124` | `0xE1A06001` | `0xE12FFF1E` | closes the previous function |
| 5 | `0x41C2FD28` | `+0x2D28` | `0xE3A00000` (`mov r0,#0`) | `0xE3A00001` (`mov r0,#1`) | "cartridge present" always |
| 6 | `0x41C41958` | `+0x14958` | `0xEBFFB8F5` (`bl 0x41C2FD34`) | `0xE3A00000` | no error |
| 7 | `0x41C423C8` | `+0x153C8` | `0xEB0D679C` (`bl 0x41F9C240`) | `0xE3A00000` | no error |
| 8 | `0x41C42850` | `+0x15850` | `0xEBFFB537` (`bl 0x41C2FD34`) | `0xE3A00000` | no error |
| 9 | `0x41C42B20` | `+0x15B20` | `0xEBFFB483` (`bl 0x41C2FD34`) | `0xE3A00000` | no error |
| 10 | `0x41C43390` | `+0x16390` | `0xEBFFB267` (`bl 0x41C2FD34`) | `0xE3A00000` | no error |
| 11 | `0x41C43480` | `+0x16480` | `0xEBFFB22B` (`bl 0x41C2FD34`) | `0xE3A00000` | no error |
| 12 | `0x41C4610C` | `+0x1910C` | `0xEBFFA708` (`bl 0x41C2FD34`) | `0xE3A00000` | no error |
| 13 | `0x41C48F98` | `+0x1BF98` | `0xEBFF9B65` (`bl 0x41C2FD34`) | `0xE3A00000` | no error |
| 14 | `0x41C4920C` | `+0x1C20C` | `0xEBFF9AC8` (`bl 0x41C2FD34`) | `0xE3A00000` | no error |
| 15 | `0x41C497D0` | `+0x1C7D0` | `0xEBFF9957` (`bl 0x41C2FD34`) | `0xE3A00000` | no error |

Addresses 13, 14 and 15 are the sensitive ones: in other builds of this same family
they appear 4 bytes further on. Copying the table from another version overwrites `strb r0, [r4, #0x10]`
at `+0x1BF9C` and `cmp r0, #1` at `+0x1C210` and `+0x1C7D4`, and the result is a printer that does not
boot. That is why `construir.py` compares the original opcode of each point before writing.

## What this patch does NOT do

- It writes nothing to the EEPROM. The `0x00`–`0xFF` area of NVRAM is left as it is.
- It does not modify the compressed block: the 15 changes happen in RAM on every boot.
- It does not simulate the chip: it makes the printer not query it.

## Practical consequence

The ink level shown by the panel or the web UI is no longer a measurement: it becomes a fixed
full value. The printer will print with a refilled or chipless cartridge even if it is
practically dry, because it no longer has any way of knowing. That is the deal: you stop having
lockouts and you also stop having warnings.
