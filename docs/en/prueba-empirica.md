# Empirical test: printing with the chip covered

Everything in `verified.md` proves that the patched firmware installs and that it reports all four
cartridges at 100 %. What it does **not** prove on its own is the only thing that actually matters:
that the printer prints when the chip cannot be read.

> **Result: passed on 2026-11-23.** Full log in `verificado.md`: cartridge at 2 % with the chip
> covered, job accepted and completed in 48 s, page printed with all four bars solid, no warnings.

That test is physical and has to be done with the printer in front of you. This document is the
full protocol, written so that the evidence leaves no room for doubt.

## What you need

- Any cartridge (black is fine).
- A piece of clear adhesive tape.
- The test page: `python3 tools/pagina_prueba.py --out pagina-prueba.pdf --version <version> --hash <sha256 of the flashed image>`
- A phone or camera.

## Before touching anything

1. Check the printer web UI (`http://<ip>/PRESENTATION/HTML/TOP/PRTINFO.HTML`) and confirm all four
   levels show 100 %. Note the version it reports.
2. Print **one** page with the chips in place. That is the control: if that page comes out fine and
   the next one with the chip covered also comes out fine, the only difference is the tape.

## Covering the chip

The chip is the small board with gold contacts on the underside of the cartridge. The tape goes
**over the contacts**, not over the ink outlet.

- One single piece, covering every contact at once. If one contact is left exposed the printer may
  read the chip partially and the result is worthless.
- Do not touch the contacts with your fingers: grease also breaks the contact and then you cannot
  tell what failed.
- Peel the tape off slowly and leave no adhesive residue.

## The print

1. Insert the cartridge with the tape on and close the lid.
2. **Photograph the printer screen** at that moment, before sending anything. What it says there is
   half the proof: if it warns about an unrecognised cartridge, it shows in the photo.
3. Send the test page.
4. Photograph the page **with the tape still on** and the cartridge still inside.
5. Fill in the boxes on the page itself by hand before the final photo.

## What to capture

| Evidence | Where it shows | What it proves |
|---|---|---|
| Panel warning on insert | Photo of the screen | Whether the printer detects the missing chip |
| Complete printed page | Photo of the paper | That it prints, not that it says it would |
| Four solid bars | The page itself | That all four channels have ink and none is dry |
| Reported level after printing | Printer web UI | That the level does not drop below 100 % (expected consequence) |
| Reported version | Printer web UI | That this is the patched image and not the factory one |
| Image hash | Page header | That the firmware that printed is the one in the repo |

## Possible outcomes and what each one means

- **Prints with no warning.** The expected case: the patch neutralises chip reads and writes and
  forces all four cartridges present. Test closed.
- **Warns about an unrecognised cartridge but still prints.** The patch covers the main path and one
  more is missing. Check the 34 aggregator call sites listed by `tools/descubrir.py` and find the one
  that raises the warning. That is a locatable bug, not a dead end.
- **Warns and blocks printing.** Either a check that does not go through the patched points, or the
  check happens before the boot hook is active. Debug with the panel trace and compare against the
  factory firmware.

All three outcomes are useful information: either they close the test or they say exactly where to
look.

## If it goes wrong

There is no risk to the printer: a covered chip is just a cartridge without a chip, and the firmware
recovery path is untouched (neither the boot area nor the recovery area has been modified). To go
back, remove the tape and, if needed, flash the factory firmware again following `flasheo.md`.
