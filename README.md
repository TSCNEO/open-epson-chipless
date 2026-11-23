# Open Epson Chipless

Experimental, read-only firmware research for the Epson XP-247.

[Leer en español](README.es.md)

> **Disclaimer.** This is an experimental project. I have one Epson XP-247 available for testing. The project is provided as is, without support or warranty. Use it at your own risk. The author disclaims liability to the extent permitted by applicable law.

## Inspect an update package

The inspector runs locally with Python 3.9 or newer and the standard library. Supply a distribution ZIP, EFU, or RCX. It reports the package version, firmware markers, region sizes, SHA-256 hashes, and CRC status for recognized uImage data. The output uses JSON and offsets are measured from the start of the uncompressed RCX.

```sh
python3 inspect_firmware.py path/to/update.efu
python3 inspect_firmware.py path/to/reference.efu > reference.json
python3 inspect_firmware.py path/to/candidate.efu > candidate.json
diff -u reference.json candidate.json
```

The repository ships an inspector. Building and validating an installable firmware image is outside the scope of this release. Firmware inputs stay local. [Reproducing the inspector and its results](docs/reproduce.md)

## License

The project uses [AGPL-3.0-only](LICENSE). The license permits commercial use and redistribution. It requires corresponding source when distributing covered modifications and when users interact over a network with a modified version of the program.
