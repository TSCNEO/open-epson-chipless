# Result template for your model

This is what turns a repository into something that grows: someone with a different printer tests it
and leaves the result in a format that is actually worth reading. Copy the block, fill it in, send it
as a pull request or an issue.

One rule: **anything you did not test stays as `not tested`**. Never fill it with assumptions.

## Before you start

1. Note the exact model and the version the printer reports (web UI or panel).
2. Run the inspector on your official package and save the RCX hash.
3. Note the four levels the printer shows and run a nozzle check from the maintenance menu. That is
   your baseline.

## Block to fill in

```text
Printer model:
Official starting version:
Official RCX SHA-256:
Cartridges installed and whether each one has a chip:
  Baseline (before any change):
    Reported levels:        K=__  Y=__  M=__  C=__
    Nozzle check:           (full pattern / which colour failed)

Built image:
  Tool and spec used:     (a table under data/patches/... or a generated spec)
  Image SHA-256:
  tools/verificar.py output:  correcto=____  problemas=____

Flashing:
  Transport:              USB / network
  Version reported after:
  Panel and web respond:  yes / no
  Full power cycle after: yes / no

Test with the chip covered:
  Tape over the contacts:    yes / no
  Panel warning on insert:
  Reported levels before printing:
  Job sent and queue status:
  Reported levels after printing:
  Did the page come out? Were all four colours visible?

Not tested:
  (be specific: other versions, other models, duplex printing, etc.)
```

## What makes a report useful

- The **RCX hash**, not just the version string. Two different builds can share a label.
- The **literal output** of `verificar.py`, not the word "verified".
- A **photo or description** of the printed page: the paper is the evidence, not the indicator.
- The **failures**, with the exact panel text. One well-described negative report is worth more than
  ten positives without data.

## What is not accepted

- Firmware binaries, packed or unpacked.
- Names of commercial firmware sellers or activators.
- Reports containing "should work".
