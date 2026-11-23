# Reproducing the firmware inspection

The normal entry point is `python3 inspect_firmware.py PACKAGE`. A reimplementation in another language or by another coding assistant should preserve the checks below and emit equivalent JSON. Use synthesized fixtures and firmware packages supplied locally by the reader.

1. Accept a raw RCX or unwrap up to two ZIP layers. At each layer require exactly one non-directory member with an EFU or RCX suffix. Enforce the 64 MiB limit for the input and for each declared uncompressed member.
2. Parse the EpsonNet text manifest through its form-feed terminator. Read the declared package version and enumerate the numbered IPL zones in order. Require each zone to begin with the IPL marker and verify that the declared lengths account for the remaining RCX bytes.
3. For each zone, emit its start, length, SHA-256 and observed version strings. Record offsets relative to the uncompressed RCX.
4. Identify uImage and SquashFS 4.0 candidates within each zone. Verify the uImage header CRC and report the payload CRC result. Bound each component by its declared size and the enclosing zone. Hash the component's bytes including its header.
5. For a comparison, inspect each input independently and compare the type and hash of each corresponding component. Matching hashes identify matching bytes even when a component moves. Different hashes identify different bytes. Matching version labels alone provide weaker evidence than matching hashes.

Verify that equivalent RCX, EFU, and outer ZIP inputs yield identical reports. Verify that truncated zones and ZIP layers with multiple candidate members exit with a nonzero status. A mutated uImage payload with an otherwise intact header should report a failed data CRC.

The report describes file structure and byte identity. Verification of on-device operation requires separate hardware evidence.
