# Evidence: what has been tested and what has not

## Input

Official Epson firmware for XP-243/245/247, version `20.25.EF20J9.FY16`, obtained from Epson's
support site:

```
EFU   sha256  3e9ae697fadece00618217da9737866ff8f0a1c38030edd4ac8eb24848ab4074   7 536 294 B
RCX   sha256  fec90a9fdfd0374dd1b2b0235a669b4bc04d7aec446ddfe4280fb17566e1220b   9 593 123 B
```

Both IPL zones with valid `sum16` and `SHA-1` before touching anything.

## Built image

With the default options (no bootloader, declared version `20.25.EF99Z9.FY16`):

```
RCX   sha256  bc25ac2e0b77a4112f04d86a27f66420c1d0036923c44b6e8087b0472de476f7   9 527 587 B
```

Checks this image passes:

| Check | Result |
|---|---|
| `sum16` and `SHA-1` of both zones | correct |
| `Z_2` byte for byte against the original | identical (2 109 440 B) |
| Decompressed CROM parts (5) | SHA-256 identical to the original |
| uImage and both SquashFS | SHA-256 identical to the original |
| Diff inside the prefix | 4 B (pointer) + 196 B (hook), nothing else |
| Decompressed block `Z0_CROM3.p0` | `b2ad8f8c…eeb14`, 498 272 B, original opcodes confirmed |

The equivalence of the builder is strongly proven: two independent implementations of the same
patch produce **the same SHA-256 byte for byte**, not only the same size.

## Hardware test

Unit: Epson XP-247 (identified by SNMP/ENPC as `XP-243 245 247 Series`), with
`20.25.EF20J9` from the factory.

- **Transport:** network, with the official Epson updater (`/NU /SU:I:<ip>`).
- **Progress observed:** `Update,Done,0` (50) → `WaitUpdating,Done,0` (66) →
  `Reboot,Start,0` (83), where it stops because it is waiting to read `EF99Z9`.
- **Boot:** correct. The printer's web page answers 200 and reports `20.25.EF20J9`.
- **ENPC (UDP 3289):** answers and returns the correct model.
- **Ink indicators** (bar height on the web page, 50 = full):

| | Before | After |
|---|---:|---:|
| Black | 37 | 50 |
| Yellow | 50 | 50 |
| Magenta | 48 | 50 |
| Cyan | 42 | 50 |

All four go to full, which is exactly the expected behaviour: the printer no longer queries the
chip.

### Live state (2026-11-23)

Read straight from the printer, with no reboot and no reflash:

```
GET http://<printer-ip>/PRESENTATION/HTML/TOP/INDEX.HTML
  Device Name: EPSONRM4EVER
  Current Version:20.25.EF20J9
  XP-243 245 247 Series
GET http://<printer-ip>/PRESENTATION/HTML/TOP/PRTINFO.HTML
  Ink_K height=50   Ink_Y height=50   Ink_M height=50   Ink_C height=50   (50 = full)
  Connection Status: Wi-Fi-72Mbps   Signal Strength: Excellent
```

Still on the patched version with all four levels at 100 %. Note: nothing has been **printed** on
this unit yet, so the 100 % is the value the firmware reports, not the result of ink having been
used. The test that separates one from the other is `prueba-empirica.md`.

## Empirical test: printing with the chip covered (2026-11-23)

The test that separates "the firmware says there is ink" from "the printer prints without a chip".

**Conditions:** a colour cartridge the printer had counted down to **2 %**, with the chip contacts
covered by adhesive tape. Flashed image: build `bc25ac2e…476f7` (`20.25.EF20J9`).

```
GET /PRESENTATION/HTML/TOP/PRTINFO.HTML    before:    K=50  Y=50  M=50  C=50
lp -d EpsonXP247 -o media=A4 pagina-prueba.pdf
  request id EpsonXP247-14, sent 17:25:46 CET
lpstat -W completed                         17:26:52 CET  Alerts: job-completed-successfully
GET /PRESENTATION/HTML/TOP/PRTINFO.HTML    after:     K=50  Y=50  M=50  C=50
```

**Result:** the printer accepted the job and completed it in 48 seconds. The page came out with all
four bars solid — yellow included — and with no "cartridge not recognised" warning, neither on the
panel nor in the web UI. After printing, all four levels still report 100 %.

**What this closes:** the patch does not merely stop the printer from querying the chip; it prints
with the chip physically unreachable, and it does so on the channel whose counter stood at 2 %.

**What it does not close:** the reported level not dropping is the expected behaviour (the counter
is neutralised), so the printer will not warn when the cartridge genuinely runs dry. And it is still
proven on one version and one model: portability is demonstrated as patch-point location, not as
flashing on other hardware.

## Portability test on another family

To check that the method does not depend on these addresses, the tool was run on an official
firmware of **another model**: `FWG016TL`, version `1E.26.MJ01O7.FY16` (XP-342/345), a recovery
package published by Epson. Same container, different code.

```
EFU   sha256 1416eda96307fd1c2f05dc6a5871458a163e47d1e2be250aa067d56637366e2d   9 706 502 B
RCX   sha256 f4b774262f6b16170190c364e08cec1825517a089fb84a7a45404259eb909f3c  15 884 579 B
```

`tools/descubrir.py` found, without touching anything, the same subsystem:

| Element | XP-247 (`FWF731TL`) | XP-342/345 (`FWG016TL`) |
|---|---|---|
| Read wrapper | +0x107C | +0x1094 |
| Write wrapper | +0x1120 | +0x1138 |
| Presence function | +0x2C80 | +0x2CA0 |
| Output to invert | +0x2D28 | +0x2D48 |
| Aggregator | +0x2D34 | +0x2D54 |
| Calls to the aggregator | 34 | 34 |

Uniform shift of +0x18 and +0x20: it is **the same code**, compiled in another version. The
shape of the functions matches instruction by instruction (`push {r4, r5, lr}` +
`sub sp, sp, #0xc` in the presence; `mov rN, #3` as retry counter in both wrappers;
`ldr r0, [pc, #-0x358]` at the start of the aggregator).

The full pipeline also worked: spec draft → build (15 819 043 B) →
verification with `"correcto": true` and all containers intact.

**What this test does not prove:**

- That image has not been flashed: there is no XP-342/345 hardware here.
- The block load base in that family is not confirmed (`0x45B26000` is a hypothesis
  deduced from the address cluster of the veneers), so the absolute addresses of the
  draft are provisional; the *offsets* are correct.
- The boot hook chosen for that image is arbitrary among the 63 candidates, and the
  flush routine was assumed to be the same. Without confirmation on hardware, that image is not flashable.

What it does prove: the points are located by code structure, not by a table, and the
same reasoning works on a binary we had never seen.

## What has NOT been validated

No overselling here: this is what remains open.

1. **Long runs.** No sustained printing has been done, nor with genuinely dry cartridges.
2. **Hot cartridge change** with the patched firmware.
3. **Deep cleaning and calibrations**, where aggregator calls that have not
   been neutralised (9 of 34) could be triggered.
4. **Extended power-off/on cycles.** The patch is reapplied on every boot, but it has only
   been checked across occasional reboots.
5. **Real USB recovery.** IPL mode exists and the bootloader is not touched, but a
   full recovery from a broken boot has not been exercised.
6. **Other units and other versions.** All of the above is a single printer and a single
   firmware version.

If you test any of these points, open an issue with the exact version, the image hash and the
observable result. That is the data that is missing.
