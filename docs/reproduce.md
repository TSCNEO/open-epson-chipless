# Reproducing the firmware inspection

The normal entry point is `python3 inspect_firmware.py PACKAGE`. A reimplementation in another language or by another coding assistant should preserve the checks below and emit equivalent JSON. Use synthesized fixtures and firmware packages supplied locally by the reader.

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
python3 inspect_firmware.py path/to/EF20J9.efu > observed.json
diff -u docs/ef20j9-reference.json observed.json
```

The reference contains two IPL zones. The first contains a Linux ARM uImage and two SquashFS 4.0 filesystems. Check component hashes independently to tell a relocated component from a changed one. An unfamiliar layout is an unsupported input until its format can be established independently.

### What was observed on hardware

One Epson XP-247 was tested with `20.25.EF20J9` as the official starting point. After a locally built test image was installed over Wi-Fi, the printer restarted and its web interface responded. The version display still read `20.25.EF20J9`. The four displayed ink levels changed from varying readings to 100%. These are display readings. The record contains no completed print job with a physically chip-free cartridge.

For subsequent evaluations, record the exact model and starting version, input SHA-256, whether the printer restarted and responded, the four reported ink levels, and whether a page actually printed. Specify whether a chip was present and record a separate result after another power cycle. Keep the package inspection, the hardware observations, and any inference about compatibility distinct in the resulting report. This case covers one printer and one firmware build.
