# Contribuir

*(In English: [CONTRIBUTING.md](CONTRIBUTING.md))*

## Añadir un modelo o una versión

Hace falta el firmware oficial y trabajo de análisis. No hay atajos: las direcciones de una
versión no valen para otra (entre `EF23I2` y `EF20J9` hay un desfase de 4 bytes que corrompe
instrucciones vecinas si se copia la tabla).

1. Consigue el firmware oficial y anota su `sha256_rcx` en `data/firmware-manifest.json`.
2. Localiza el trampolín de arranque y el hueco libre del prefijo.
3. Descomprime `Z0_CROM3`, identifica las rutinas de cartucho/CSIC y **el opcode original** de
   cada dirección que quieras parchear.
4. Crea `data/patches/<familia>/<version>.json`.
5. Pasa las puertas 2 a 4 de [AGENTS.md](AGENTS.md).

Un PR que solo cambie números sin la evidencia de que el opcode original coincide se rechaza.

## Qué NO se acepta

- Binarios de firmware, propios o de terceros.
- Claves, activadores, emuladores de servidor de licencias.
- Volcados de EEPROM de máquinas ajenas.
- Parches "probados en mi impresora, confía" sin hashes.

## Traducciones

Bienvenidas. La documentación está en español y `AGENTS.md` en inglés a propósito: los agentes
LLM lo consumen mejor así. Si traduces los documentos, mantenlos enlazados desde el README.
