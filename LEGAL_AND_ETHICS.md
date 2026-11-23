# Legal and ethical framework

[Leer en español](MARCO_LEGAL_Y_ETICO.md)

This document accompanies the firmware inspection project in [README.md](README.md) and the
reproduction guide in [docs/reproduce.md](docs/reproduce.md). It states what this release is,
what it is not, and what publishing or redistributing it involves.

## 1. Purpose

Independent technical research on **interoperability and the right to repair** a device the
author owns: understanding how the official firmware of the Epson XP-243/XP-245/XP-247 is
packaged and verified, and documenting a reproducible method to patch it locally.

This release contains two things: a set of **inspection tools** that parse and hash official
update packages, and a set of **build tools** that produce a patched image from the reader's
own official package, offline, on the reader's machine. Nothing is downloaded and nothing is
signed: the build only rewrites bytes inside the official image.

## 2. What this release is not

- It does **not** sign firmware, and it cannot: no vendor key is involved anywhere.
- It does **not** flash anything for you. Flashing is a manual step with the official updater,
  on hardware the reader owns.
- It does **not** ship a ready-made image: the reader builds it from their own official package.
- It does **not** include, crack, or run any vendor activator or licence tool.
- It does **not** redistribute Epson firmware or any third-party binary; readers supply
  their own official packages.
- It is **not** a commercial circumvention product or a ready-to-copy "kit".

## 3. Legal landscape (general orientation; not legal advice)

Modifying hardware you own to use third-party consumables is a **right-to-repair and
interoperability** matter, and private use has room in many jurisdictions. The sensitive
point is the **public distribution** of circumvention technology, and some jurisdictions
restrict even research tools.

- **United States.** Section 1201 of the DMCA (17 U.S.C.) prohibits, among other things,
  trafficking in technology designed to circumvent a technical protection measure.
  Exemptions exist (good-faith security research, repair, interoperability of certain
  devices, jailbreaking), but they are narrow, and a general-purpose tool to defeat a
  cartridge check may fall outside them.
- **European Union.** Article 6 of Directive 2001/29/EC prohibits circumventing technical
  measures and manufacturing, importing, distributing, selling, advertising, or possessing
  for commercial purposes circumvention devices or services. Article 6(4) exceptions are
  optional and set by each member state.
- **Spain.** Articles 160-161 of the consolidated Copyright Act (RDL 1/1996) regulate
  technical protection measures and their circumvention; Article 31 covers private copying
  and Article 100 decompilation for interoperability.
- **Other jurisdictions** may be stricter and may criminalise distribution.

This release produces a patched image on the reader's own machine, so it is closer to a
circumvention tool than to a pure analysis paper. Publishing or extending it may fall under
anti-circumvention rules in your country. The absence of binaries, keys and vendor code lowers
the practical exposure but does not eliminate it.

## 4. Responsible use

- Personal, educational, or repair use on devices you own.
- Do not sell or package the method as a product.
- Respect the law of your jurisdiction; if in doubt, do not distribute.
- Consider coordinated disclosure with the community and, where appropriate, the
  manufacturer, before wide distribution.
- Present the work as **technical and repair research**, not a "ready-to-copy bypass".

## 5. Licence and redistribution

- The code is licensed under **AGPL-3.0-only** ([LICENSE](LICENSE)).
- No Epson binaries are included; readers obtain official firmware from official sources or
  public archives.
- Anyone redistributing this material is responsible for complying with applicable law.

## 6. Risks

- The inspectors are read-only and never write to hardware.
- Flashing a modified image can **permanently brick** a printer and voids the warranty. Take a full, verified physical dump of the SPI flash chip
  (e.g. CH341A + SOIC-8 clip) before any flashing.

## 7. Disclaimer

This material is provided **as is**, without warranty of any kind. The author disclaims
liability to the extent permitted by applicable law. Nothing here is legal advice.
