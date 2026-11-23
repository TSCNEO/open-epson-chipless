# Open Epson Chipless

Proyecto experimental de análisis de firmware de solo lectura para la Epson XP-247.

[Read in English](README.md)

> **Aviso.** Proyecto experimental. Solo dispongo de una Epson XP-247 para pruebas. Se proporciona tal cual, sin soporte ni garantía. El uso corre por tu cuenta. El autor declina toda responsabilidad en la medida permitida por la ley aplicable.

## Inspeccionar una actualización

Requiere Python 3.9 o posterior. El inspector analiza un ZIP de distribución, un EFU o un RCX y devuelve un informe JSON con la versión, los tamaños, los hashes SHA-256 y la comprobación CRC de los datos uImage reconocidos.

```sh
python3 inspect_firmware.py ruta/a/actualizacion.efu
```

Esta publicación contiene el inspector. La construcción y validación de una imagen instalable quedan fuera del alcance de esta versión. Los archivos de firmware se leen de forma local. [Guía de reproducción en inglés](docs/reproduce.md)

## Licencia

El proyecto usa [AGPL-3.0-only](LICENSE). Permite el uso comercial y la redistribución. Exige ofrecer el código fuente correspondiente al distribuir modificaciones cubiertas o al ofrecer una versión modificada con la que se pueda interactuar por red.
