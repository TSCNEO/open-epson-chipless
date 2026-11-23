# Reproducing the firmware inspection

The normal entry point is `python3 tools/inspect_firmware.py PACKAGE`. A reimplementation in another language or by another coding assistant should preserve the checks below and emit equivalent JSON. Use synthesized fixtures and firmware packages supplied locally by the reader.

1. Accept a raw RCX or unwrap up to two ZIP layers. At each layer require exactly one non-directory member with an EFU or RCX suffix. Enforce the 64 MiB limit for the input and for each declared uncompressed member.
2. Parse the EpsonNet text manifest through its form-feed terminator. Read the declared package version and enumerate the numbered IPL zones in order. Require each zone to begin with the IPL marker and verify that the declared lengths account for the remaining RCX bytes.
3. For each zone, emit its start, length, SHA-256 and observed version strings. Record offsets relative to the uncompressed RCX.
4. Identify uImage and SquashFS 4.0 candidates within each zone. Verify the uImage header CRC and report the payload CRC result. Bound each component by its declared size and the enclosing zone. Hash the component's bytes including its header.
5. For a comparison, inspect each input independently and compare the type and hash of each corresponding component. Matching hashes identify matching bytes even when a component moves. Different hashes identify different bytes. Matching version labels alone provide weaker evidence than matching hashes.

Verify that equivalent RCX, EFU, and outer ZIP inputs yield identical reports. Verify that truncated zones and ZIP layers with multiple candidate members exit with a nonzero status. A mutated uImage payload with an otherwise intact header should report a failed data CRC.

The report describes file structure and byte identity. Verification of on-device operation requires separate hardware evidence.

## Case study for coding assistants

Use the [EF20J9 reference report](ef20j9-reference.json) as the expected output for the official Epson XP-247 package. Its manifest declares `20.25.EF20J9.FY16` and the printer reports `20.25.EF20J9`. Confirm the RCX SHA-256 against the report before treating another file as the same build.

```sh
python3 tools/inspect_firmware.py path/to/EF20J9.efu > observed.json
diff -u docs/ef20j9-reference.json observed.json
```

The reference contains two IPL zones. The first contains a Linux ARM uImage and two SquashFS 4.0 filesystems. Check component hashes independently to tell a relocated component from a changed one. An unfamiliar layout is an unsupported input until its format can be established independently.

### What was observed on hardware

One Epson XP-247 was tested with `20.25.EF20J9` as the official starting point. After a locally built image was installed over Wi-Fi, the printer restarted and its web interface responded. The version display still read `20.25.EF20J9`.

The web status page reported black at 74%, cyan at 84%, magenta at 96%, and yellow at 100% before the update. After the restart it reported 100% for all four colors.

That only described the display. The physical test came later: a colour cartridge the printer had counted down to **2 %**, with its chip contacts covered in adhesive tape, was installed. The printer raised no warning, accepted a print job from the driver queue and completed it in 48 seconds, and the page came out with all four colour bars solid. The four levels still reported 100 % afterwards. Full log in [verificado.md](en/verificado.md).

This case covers one printer and one firmware build. Flashing on other models and versions remains unverified.

### Report a result for another printer

The most useful contribution is a filled-in result report. Use the template in
[result-template.md](en/result-template.md): model, official version, RCX SHA-256, baseline levels
and nozzle check, what printed with the chip covered, and every check you did **not** perform.

The pipeline that builds and verifies an image is documented in [../README.md](../README.md) and,
step by step for an automated agent, in [../AGENTS.md](../AGENTS.md).
