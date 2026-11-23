# SPDX-License-Identifier: 0BSD
"""Inventario y verificacion de un paquete EpsonNet RCX (.zip, .efu o .rcx).

Solo lectura: no modifica nada ni necesita impresora.
"""

import argparse
import configparser
import json
import struct
import zlib
from pathlib import Path
from zipfile import BadZipFile

import epson_rcx


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archivo", type=Path, help="ZIP de distribucion, EFU o RCX")
    parser.add_argument(
        "--decompress-crom",
        action="store_true",
        help="Descomprime cada parte CROM en memoria y calcula tamano y SHA-256",
    )
    parser.add_argument("--resumen", action="store_true", help="Salida corta legible")
    args = parser.parse_args()

    try:
        result = epson_rcx.inspect(
            epson_rcx.load_rcx(args.archivo), decompress_crom=args.decompress_crom
        )
    except (
        OSError,
        ValueError,
        KeyError,
        configparser.Error,
        BadZipFile,
        RuntimeError,
        NotImplementedError,
        EOFError,
        zlib.error,
        struct.error,
    ) as exc:
        parser.exit(1, f"Error al leer {args.archivo}: {exc}\n")

    if not args.resumen:
        print(json.dumps(result, indent=2))
        return

    print(f"paquete   : {result['package']}")
    print(f"rcx       : {result['rcx_size']:,} B  sha256 {result['rcx_sha256']}")
    for block in result["blocks"]:
        print(f"\n{block['zone']}: {block['size']:,} B  sha256 {block['sha256'][:16]}...")
        for seg in block["segments"]:
            estado = "OK" if seg["checksum16_ok"] else "FALLA"
            print(
                f"  seg{seg['index']}  type={seg['type']} bank={seg['bank']} "
                f"flash=0x{seg['flash_offset']:08x} len={seg['size']:,} sum16={estado}"
                + (f" sha1={'OK' if seg.get('sha1_ok') else 'FALLA'}" if seg["index"] else "")
            )
        for comp in block["components"]:
            print(f"  {comp['type']:<14} {comp['size']:>10,} B  {comp.get('name', '')}")
        for crom in block["crom_containers"]:
            partes = len(crom["parts"])
            print(f"  CROM           {crom['compressed_size']:>10,} B  {partes} parte(s)")


if __name__ == "__main__":
    main()
