# Legal

## What this repository contains

Only original code and documentation:

- `tools/` — both inspectors, builder, verifier, discovery tool and test-page generator, written for this project (0BSD).
- `docs/`, `README*`, `AGENTS.md` — our own reverse-engineering notes (CC BY-SA 4.0).
- `data/patches/` — offset tables and instruction words, i.e. facts about a binary, plus one
  hand-written ARM routine of our own.
- `data/firmware-manifest.json` — hashes and download locations for official firmware, so you can
  verify the file you obtained yourself.

## What it does NOT contain

- No Epson firmware, whole or in part, compressed or decompressed.
- No firmware from any reseller, and no code from any commercial activation product.
- No licence key, keygen, activation blob or signature forger.
- No EEPROM dumps from third parties.

That is deliberate. Firmware distributed by Seiko Epson is copyrighted; bundling it — modified or
not — would be redistribution of their code and would put the project at risk of a takedown. The
design avoids the problem instead of fighting it: **you supply your own official copy, the tool
patches it locally.**

## How you are expected to use it

You must own the printer and the firmware you feed it. Obtaining the official firmware from
Epson's support site is free and requires nothing but a model name.

## Jurisdiction and risk

Modifying firmware of a device you own, for interoperability and repair, is permitted in many
jurisdictions, but rules about circumventing technical protection measures differ by country and
this project does change how a printer treats cartridge authentication. Nothing here is legal
advice. If you redistribute builds, you do it on your own responsibility.

## Trademarks

Epson, XP-243, XP-245, XP-247 and related marks belong to Seiko Epson Corporation. This project
is not affiliated with, endorsed by, or supported by Seiko Epson. Model names are used only to
describe compatibility.

## Warranty

None. Flashing firmware can render a printer unusable. The build excludes the bootloader to keep
the recovery path alive, but that is a mitigation, not a guarantee. See `docs/flasheo.md`.
