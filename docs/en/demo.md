# Demo shot list (60–75 s)

Record it with a phone, no fancy editing. The goal: within 10 seconds the viewer understands that
the printer prints with the chip covered; within 60, that the method is published and repeatable.

Rule: **the tape goes on screen.** If the video says there is tape but never shows it being
applied, it is worthless. Same for the hash and the version string.

## Shot by shot

**0–4 s · The hook.** Close-up of the printer printing.
> "This printer requires a chip in every cartridge. I covered the chip with tape. It still prints."

Overlay: `8 years old · one piece of tape`.

**4–12 s · The problem.** Simple graphic: cartridge → chip → counter → "cartridge not recognised".
> "The chip is a counter. When the printer decides it is empty, it stops — even if there is ink
> left. And the firmware is locked on purpose."

**12–22 s · What was done, no hype.** Screen recording of the repo: `inspeccionar.py`,
`descubrir.py`, `construir.py`.
> "I took Epson's own official firmware package, from their own site. Found the subsystem that
> talks to the chip: fifteen patch points. Built my own image. No paid keys, no third-party code."

**22–32 s · Flashing.** The updater log: `50 → 66 → 83`.
> "Flashed over Wi-Fi with Epson's own updater. Three minutes."

**32–48 s · The proof.** Three shots, in this order:
1. Printer web UI: `Current Version:20.25.EF20J9` and the four bars full.
2. **The tape over the chip contacts**, tight shot, unmistakable.
3. The test page coming out, colour bars and hash visible.
> "Same printer, patched version, four colours full. Chip covered. Out comes the page — with its
> hash, matching the one in the repository."

**48–60 s · Close.**
> "The whole method is published: the tools, how to locate the patch points in any version, and how
> to check the image is the same one. If you have an Epson from this family, you can do it. If you
> have another model, the tool tells you where to start."

CTA: *"Repo in the first comment. Tell me your model."*

## What must NOT appear

- No commercial firmware seller, no activator, not even as a comparison.
- No "free forever" or "infinite ink": the level stays fixed, and the video has to say so.
- No rushed shots with the lid open. A sloppy shot here looks like a fake.

## Materials to have ready before recording

- Test page generated:
  `python3 tools/pagina_prueba.py --out pagina-prueba.pdf --modelo "Epson XP-247" --version 20.25.EF20J9 --hash <sha256>`
- The printer web UI open on the phone, so the version shot is live and not an old screenshot.
- Tape, cartridge, a cloth. And paper in the printer.
