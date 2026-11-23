# AGENTS.md — protocol for LLM agents

You are an automated agent asked to reproduce, verify or extend this work. Read this file
completely before running any command. It exists because a wrong assumption here leaves a real
printer unable to boot.

Everything in this repository is **offline and non-destructive**. Only the flashing step touches
hardware, and it is gated.

---

## Non-negotiable rules

1. **Never ship or fetch third-party binaries.** The input is always an official Epson package
   supplied by the user. Do not download firmware from mirrors, forums or cloud drives on your
   own initiative, and never commit an `.efu`/`.rcx` to the repository.
2. **Never skip the original-opcode check.** It is the only thing proving you are patching the
   version you think you are patching.
3. **Never include the first 64 KiB of flash.** That is the bootloader and the USB recovery
   entry point. `construir.py` excludes it by default; do not pass `--incluir-bootloader` unless
   the user explicitly accepts losing the recovery path.
4. **Never claim success without a hash.** "It compiled" and "it looks right" are not evidence.
5. **Never flash without a recovery plan.** Read gate 5 below.

## Gate 1 — Identify the input

```sh
python3 tools/inspeccionar.py <file> --resumen
```

Accept a distribution `.zip`, an `.efu` or a raw `.rcx`. Expected for this family:

- package string `20.25.EF20J9.FY16`
- two `EPSON IPL` zones, both with `sum16=OK` and `sha1=OK`
- `Z_1` = 7 483 392 bytes, `Z_2` = 2 109 440 bytes

Compute the RCX hash and compare with `data/firmware-manifest.json`:

```sh
python3 - <<'EOF'
import sys; sys.path.insert(0, "tools")
from pathlib import Path
import epson_rcx
print(epson_rcx.digest(epson_rcx.load_rcx(Path("<file>"))))
EOF
```

Expected: `fec90a9fdfd0374dd1b2b0235a669b4bc04d7aec446ddfe4280fb17566e1220b`.
**If it differs, stop.** A different version means different offsets; see "Extending to another
version" at the end.

Cross-check the structure with the **second, independent inspector** (standard library only). Two
implementations agreeing is stronger evidence than one agreeing with itself:

```sh
python3 tools/inspect_firmware.py <file>.rcx > observed.json
diff -u docs/ef20j9-reference.json observed.json
```

No differences means you are holding the exact build this repo was validated against. Differences
in the zone or component hashes with the same structure mean another version — go to "Extending to
another version". A different *structure* (no uImage, no SquashFS, unknown markers) means an
unsupported input: report it, do not guess the format.

## Gate 2 — Validate the patch targets

`construir.py` does this automatically before writing anything, but understand what it checks:

- the trampoline at `0x0001633C` is `ldr pc, [pc, #-4]` (`0xE51FF004`) and points to
  `0x41EAD6E8`;
- the hook area `0x00032100..0x000321C4` is entirely `0xFF` (unused flash);
- `Z0_CROM3.p0` decompresses to SHA-256
  `b2ad8f8c7152fc8ca02c87bfaf2be5dd24f4ec914dfcdbffd404912f9f9eeb14`;
- each of the 15 words at the addresses in `data/patches/xp243-245-247/ef20j9.json` matches the
  `original` value recorded there.

If any of these fails, the JSON does not describe this firmware. Do not "fix" it by relaxing the
check.

## Gate 3 — Build

```sh
python3 tools/construir.py <official.efu> --out-dir build
```

Expected, with default options:

```
tamano_salida   9527587
sha256_salida   bc25ac2e0b77a4112f04d86a27f66420c1d0036923c44b6e8087b0472de476f7
verificado      true
```

A different hash means different options or a different base. Investigate before continuing; do
not assume the difference is harmless.

## Gate 4 — Independent verification

```sh
python3 tools/verificar.py <official.efu> build/FWF731TL.efu
```

Required result: `"correcto": true`. It proves:

- both images have valid block checksums and IPL SHA-1;
- `Z_2` is byte-identical to the original;
- every decompressed CROM part, the uImage and both SquashFS images keep their SHA-256;
- the only modified bytes in the boot area are the 4-byte trampoline pointer and the 196-byte
  hook — nothing else within the 192 KiB prefix.

Report these four facts explicitly to the user. Never summarise as "verified".

## Gate 5 — Flashing (hardware)

Do not flash unless **all** of the following are true:

1. Gate 4 passed on the exact file that will be flashed (same hash).
2. The official package is saved and hash-checked, ready for recovery.
3. The user knows the recovery procedure and accepts the residual risk.

Two transports exist:

- **USB** (official Epson updater): preferred, because the same cable is the recovery path.
- **Network** (official updater with `/NU /SU:I:<printer-ip>`): works, but if the printer fails
  to boot it loses network access, so recovery will require a USB cable later.

Recovery: hold the documented button combination at power-on to enter IPL/USB mode (USB ID
`04b8:0007`) and reflash the official `.rcx`. Because the bootloader is untouched, this path
survives a bad application image.

## Things that are out of scope

- Any activation key, keygen, licence server or vendor tooling.
- Editing the EEPROM to fake cartridge data.
- Redistributing Epson firmware, decompressed or patched.
- Automated firmware updates from Epson: they overwrite the patch. Tell the user to disable
  automatic firmware updates.

## Extending to another version or model

Adding a model means finding its numbers, not guessing them. Start with the automated pass:

```sh
pip install capstone
python3 tools/descubrir.py <official.efu>
```

It locates the chip wrappers, the presence function, the instruction to flip, the aggregator and
all of its call sites, from fingerprints in the binary. Then emit a draft spec with
`--trampolin <va> --flush <va> --emitir-spec ...` and review it. The full manual procedure, with
the reasoning behind each fingerprint and the pitfalls, is in
[docs/metodologia.md](docs/metodologia.md). Summary of what remains human work:

1. Obtain the official package and record its RCX SHA-256 in `data/firmware-manifest.json`.
2. Choose the boot hand-off among the candidates. All of them are structurally identical veneers;
   the valid one is the one actually executed at boot. Wrong choice = printer boots without the
   patch, no error anywhere.
3. Choose the D-cache cleaning routine. Wrong choice = unstable boot.
4. Decide which of the aggregator call sites to neutralise, and justify each one.

**Beware version drift.** Between `EF23I2` and `EF20J9` the same source produced a 4-byte shift:
a literal inserted at `+0x1A138` moves the last three patch sites 4 bytes earlier. Copying
addresses across versions corrupts neighbouring instructions (`+0x1BF9C`, `+0x1C210`,
`+0x1C7D4`). Always derive addresses from the binary you have, never from a table written for
another build.

## Failure decision tree

| Symptom | Meaning | Action |
|---|---|---|
| `la entrada no es la version base esperada` | Wrong version for the shipped table | Derive a new table with `descubrir.py` |
| `trampolin inesperado` | The hook pointer no longer matches the binary | Re-derive the trampoline from the binary |
| `{"correcto": false}` with an offset outside the patch window | The build touched something it should not | Stop, report the offset, ship nothing |
| Discovery finds the wrappers but no aggregator | The subsystem was recompiled | Report what was found; do not force the old table |
| Printer boots but the ink counter still drops | The hook did not run (wrong trampoline) | Needs hardware to try the next candidate |
| Printer warns "cartridge not recognised" but still prints | One check path is not patched | Review the unpatched aggregator call sites |
| Printer blocks printing | A check bypasses the patched points | Report; compare against the factory firmware |

## Reporting template

When you finish, report exactly this:

```
input          <package string>  sha256 <hash>
cross-check    second inspector diff=<none|list>
build          <size> bytes      sha256 <hash>
gate 4         correcto=<true|false>  componentes_intactos=<true|false>
hardware       flashed=<yes|no>  transport=<usb|network>  booted=<yes|no>
observed       <ink indicators, panel state, print test with the chip covered>
not validated  <what remains unknown>
```

Anything you could not verify goes in `not validated`. Do not fill it with assumptions.

If hardware was involved, fill in [docs/en/result-template.md](docs/en/result-template.md) and add
it to the repository. If it was not, say so explicitly: half a verified result honestly labelled is
worth more than a complete story without evidence.
