# Flashing and recovering

## Before you start

1. Build and verify:

   ```sh
   python3 tools/construir.py EF20J9.efu --out-dir build
   python3 tools/verificar.py EF20J9.efu build/FWF731TL.efu   # debe decir "correcto": true
   ```

2. Save the official package and **note its hash**. It is your way back:

   ```sh
   sha256sum EF20J9.efu
   # 3e9ae697fadece00618217da9737866ff8f0a1c38030edd4ac8eb24848ab4074
   ```

3. Check that the file you are going to flash is exactly the verified one:

   ```sh
   sha256sum build/FWF731TL.efu
   ```

## What to expect afterwards

- The printer reports **the same version as before** (`20.25.EF20J9`). The patch does not change the
  internal version string; it only declares another one in the manifest so that the updater
  accepts the package.
- The four ink gauges permanently show full.
- Chipless or refilled cartridges stop raising an error.

## Transport 1: USB (recommended)

Use the same official Epson updater that ships with the package, with the cable connected
directly (no hub). Replace the `FWF731TL.efu` in the directory with the one you have built.

Advantage: the cable you use to flash is the same one you will need if something goes wrong.

## Transport 2: network

The official updater accepts the printer over the network:

```sh
EPFWUPD.exe /NU /SU:I:<ip-de-la-impresora>
```

On the tested unit the sequence was:

```
WaitIdle,Done,0        -> Update,Done,0        Progress:50
WaitUpdating,Done,0                            Progress:66
Reboot,Start,0                                 Progress:83
```

**It stays at 83 and does not finish.** It is not a failure: after rebooting, the updater tries to read
the version `EF99Z9` declared by the manifest, and the printer keeps reporting `EF20J9` because the
patch does not touch that datum. The process can be closed: the flash has already finished.

Warning: if the printer did not boot after a network flash, it loses connectivity and
recovery requires a USB cable, without exception.

## Recovery

The patch **never includes the first 64 KiB** (bootloader `BooSt`), so recovery mode remains
intact:

1. Turn the printer off.
2. Turn it on with the key combination documented by Epson to enter
   update/IPL mode (in this family, hold the indicated keys while
   powering on until the device appears to the PC).
3. The PC must see a USB device with ID `04b8:0007` (IPL mode).
4. Reflash the official package with the Epson updater, or with `epsflasher`
   (project `abrasive/epson-reversing`) if you prefer a command line on Linux.

If you have never tried that mode, do it **before** flashing anything modified: entering and leaving
without writing breaks nothing and confirms that your safety net exists.

## Afterwards

- **Disable automatic firmware updates.** Any official update
  overwrites the patch and you would go back to the chip lockout. On the printer's web UI, check the
  notification/update options and disable them; and do not accept new-version notices.
- Check the status on the printer's web UI: model, version and the four levels.
- Do a test print and a power-off/on cycle to confirm that the patch is
  reapplied (it must still not complain about the chip).

## If something goes wrong

| Symptom | What it means | Action |
|---|---|---|
| The updater stays at `Progress:83` | Expected behaviour: it waits for a version you are not going to report | Close the process, the printer is already flashed |
| The printer does not respond over the network after rebooting | Broken boot | USB recovery (above) |
| It boots but still asks for a chip | The hook did not execute | Check that patch point 2 is at `0x00032100` and that `0x00016340` equals `0x00032100` |
| It still asks for a chip for only one colour | A warning may remain from an aggregator call that was not neutralised | Report the case with the version and the decompressed block |
