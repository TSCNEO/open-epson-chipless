# Contributing

*(En español: [CONTRIBUTING.es.md](CONTRIBUTING.es.md))*

## Adding a model or a version

You need the official firmware and analysis work. There are no shortcuts: the addresses of one
version are not valid for another (between `EF23I2` and `EF20J9` there is a 4-byte offset that
corrupts neighbouring instructions if the table is copied).

Start with the automated pass, which finds the fingerprint candidates for you:

```sh
pip install capstone
python3 tools/descubrir.py <official.efu>
```

Then:

1. Get the official firmware and record its `sha256_rcx` in `data/firmware-manifest.json`.
2. Confirm the structure with **both** inspectors (`tools/inspeccionar.py` and
   `tools/inspect_firmware.py`) — they are independent implementations and must agree.
3. Choose the boot trampoline and the cache-flush routine (they need hardware to confirm).
4. Decompress `Z0_CROM3`, identify the cartridge/CSIC routines and **the original opcode** of
   each address you want to patch.
5. Create `data/patches/<familia>/<version>.json`.
6. Pass gates 2 to 4 of [AGENTS.md](AGENTS.md).

A PR that only changes numbers without evidence that the original opcode matches is rejected.

## Reporting a result without writing code

The most useful contribution for most people is a filled-in test report: your model, the official
version, the RCX hash, what printed with the chip covered, and what you did not test. Use
[docs/en/result-template.md](docs/en/result-template.md) (Spanish:
[docs/plantilla-resultados.md](docs/plantilla-resultados.md)). No binaries — hashes only.

## What is NOT accepted

- Firmware binaries, your own or from third parties.
- Keys, activators, licence server emulators.
- EEPROM dumps from other people's machines.
- "Tested on my printer, trust me" patches without hashes.

## Translations

Welcome. Documentation exists in Spanish (`docs/`) and English (`docs/en/`), and `AGENTS.md` is in
English on purpose: LLM agents consume it better that way. If you translate a document, add it to
the matching directory and link it from the README.
