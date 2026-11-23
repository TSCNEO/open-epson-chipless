# Open Epson Chipless

Build a patched firmware **from your own official Epson package**, so an Epson XP-243 / XP-245 /
XP-247 keeps printing when the ink cartridge chips are missing, empty, or unreadable. No paid keys,
no activation servers, no vendor code, no firmware redistributed here.

[Leer en español](README.es.md) · [Protocol for LLM agents](AGENTS.md) · [Legal framework](LEGAL_AND_ETHICS.md)

> **Status: verified on real hardware, with the chip physically covered.**
> An Epson XP-247 running `20.25.EF20J9` was flashed with the image this repo builds. A colour
> cartridge the printer had counted down to **2 %**, with its chip covered in adhesive tape, printed
> a full page — yellow included — with no "cartridge not recognised" warning, and the print job
> completed successfully in the queue. Ink counters never move. Full log:
> [docs/en/verificado.md](docs/en/verificado.md).

---

## What this does (and what it does not)

**Does:** patches, at boot, the firmware routines that read and validate the cartridge chip. The
printer stops asking, so a cartridge without a working chip is accepted and printing continues.
Ink levels are reported as full and never decrease.

**Does not:** repair a dry printhead, bypass physical ink limits, or unlock any commercial software.
No keys, no activation, no third-party binaries. You supply your own official firmware package.

**The honest trade-off:** the counter is neutralised, so the printer will **not warn you** when a
cartridge genuinely runs dry. Watch the printed pages, not the level indicator.

## Requirements

- Python 3.10+ (standard library only).
- `capstone` for the discovery tool (`pip install capstone`). The builder, verifier, inspectors and
  test-page generator need nothing else.
- Your own official Epson update package for this family (`.efu` or `.rcx`).

## Quick start

```bash
# 1. Look at your package: zones, components, hashes
python3 tools/inspeccionar.py FWF731TL.efu --resumen

# 2. Build the patched image (uses the table shipped for 20.25.EF20J9)
python3 tools/construir.py FWF731TL.efu --out-dir build

# 3. Verify the result independently
python3 tools/verificar.py FWF731TL.efu build/FWF731TL.efu
# must print {"correcto": true, "problemas": []}
```

If your package is a different version or model, step 2 fails on purpose: build the patch table
first with the discovery tool. That is the part designed to survive a firmware update.

```bash
python3 tools/descubrir.py FW.efu                                  # fingerprints only
python3 tools/descubrir.py FW.efu --trampolin <va> --flush <va> \
    --emitir-spec spec.json                                        # full draft spec
python3 tools/construir.py FW.efu --spec spec.json --out-dir build
```

Two decisions stay human: which boot trampoline and which cache-flush routine are live. There are
dozens of structurally identical candidates and choosing wrong produces no error — the printer
simply boots unpatched. Everything else is mechanical and documented step by step in
[docs/en/metodologia.md](docs/en/metodologia.md).

## Proof, not claims

| Evidence | Where |
|---|---|
| Build is byte-identical on two independent runs | `bc25ac2e…476f7`, `docs/en/verificado.md` |
| Patched firmware boots and reports `20.25.EF20J9` | `docs/en/verificado.md` |
| All four ink indicators go to full after flashing | same |
| Printer prints with the chip covered in tape (cartridge at 2 %) | same |
| Job accepted and completed by the driver queue (~48 s) | same |
| Patch points re-discovered with the same opcodes from the binary alone | `docs/en/metodologia.md` |
| Discovery works on another family (XP-342/345, `FWG016TL`) | `docs/en/verificado.md` |
| Two independent inspectors produce the same structure hashes | `tools/inspect_firmware.py` vs `tools/inspeccionar.py` |

What is **not** proven: flashing on other models, and behaviour on versions other than
`20.25.EF20J9`. Those are marked UNVERIFIED wherever they appear.

## Two independent inspectors

`tools/inspeccionar.py` (part of the pipeline) and `tools/inspect_firmware.py` (a separate,
standard-library-only implementation with its own reference report) both parse the same packaging
format and emit comparable JSON. They were written independently and agree on the official package:

```bash
python3 tools/inspect_firmware.py FWF731TL.rcx > observed.json
diff -u docs/ef20j9-reference.json observed.json   # no structural differences
```

The same structure hashes from two implementations is stronger evidence than one tool agreeing
with itself.

## Safety

- The recovery path is untouched: neither the boot area nor the recovery area is modified, so a bad
  image can be recovered with the vendor updater.
- Flashing over the network works: `EPFWUPD.exe /NU /SU:I:<printer-ip>`. The official updater stops
  at ~83 % waiting for a version it expects; the printer reboots and comes up patched.
- Read [docs/en/flasheo.md](docs/en/flasheo.md) before flashing anything, and keep the official
  package on disk.
- Flashing firmware always carries risk. If you are not comfortable recovering a bricked printer,
  do not start.

## Contributing a result for your model

The most useful thing you can send is a **filled-in result report**: model, official version, RCX
hash, baseline levels, what printed, and what you did not test. Template and instructions:
[docs/en/result-template.md](docs/en/result-template.md).

Do not attach firmware binaries. Hashes only.

## Legal

Independent research on interoperability and the right to repair a device the author owns.
Modifying hardware you own to use third-party consumables is private use with room in many
jurisdictions; **public distribution of circumvention technology** is restricted in some of them
(US DMCA §1201, EU Directive 2001/29/EC Art. 6, Spain LPI arts. 160-161). This repository contains
no Epson code, no binaries and no activator. Read [LEGAL_AND_ETHICS.md](LEGAL_AND_ETHICS.md).
Not legal advice.

## Repository layout

```
tools/        inspector, reference inspector, builder, verifier, discovery tool, test-page generator
data/         firmware manifest (hashes only) and patch tables per version
docs/         architecture, cartridge subsystem, flashing, methodology, evidence, empirical test (ES)
docs/en/      the same documents in English
AGENTS.md     step-by-step protocol so an LLM agent can reproduce this without guessing
```

## Licence

Code under **0BSD**. Documentation under **CC BY-SA 4.0**. No warranty of any kind.
