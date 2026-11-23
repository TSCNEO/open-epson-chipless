# SPDX-License-Identifier: 0BSD
"""Comprueba que un RCX generado solo se diferencia del oficial donde debe.

Pensado para CI y para que un agente valide antes de flashear:
    python3 verificar.py original.rcx build/FWF731TL.rcx --spec ../data/patches/...

No necesita hardware ni binarios de terceros.
"""

import argparse
import hashlib
import json
import struct
import sys
from pathlib import Path

import epson_rcx

SPEC_POR_DEFECTO = Path(__file__).resolve().parent.parent / "data" / "patches" / "xp243-245-247" / "ef20j9.json"


def firma_componentes(informe: dict) -> dict:
    z1, z2 = informe["blocks"]
    return {
        "z1_crom": [[p["uncompressed_sha256"] for p in c["parts"]] for c in z1["crom_containers"]],
        "z2_crom": [[p["uncompressed_sha256"] for p in c["parts"]] for c in z2["crom_containers"]],
        "componentes": [c["sha256"] for c in z1["components"]],
    }


def verifica(original: bytes, generado: bytes, spec: dict) -> dict:
    problemas = []
    inf_orig = epson_rcx.inspect(original, decompress_crom=True)
    inf_nuevo = epson_rcx.inspect(generado, decompress_crom=True)

    for etiqueta, informe in (("original", inf_orig), ("generado", inf_nuevo)):
        for bloque in informe["blocks"]:
            if not all(seg["checksum16_ok"] for seg in bloque["segments"]):
                problemas.append(f"{etiqueta}: suma de 16 bits invalida en {bloque['zone']}")
            if not all(seg.get("sha1_ok", True) for seg in bloque["segments"]):
                problemas.append(f"{etiqueta}: SHA-1 IPL invalido en {bloque['zone']}")

    if len(inf_nuevo["blocks"]) != 2:
        problemas.append("el firmware generado no tiene dos zonas")
        return {"correcto": False, "problemas": problemas}

    if firma_componentes(inf_orig) != firma_componentes(inf_nuevo):
        problemas.append("algun CROM, uImage o SquashFS cambio respecto al original")

    layout = spec["layout"]
    fin_orig = original.index(b"\x0c") + 1
    fin_nuevo = generado.index(b"\x0c") + 1
    b2_orig, b2_nuevo = inf_orig["blocks"][1], inf_nuevo["blocks"][1]
    z2_orig = original[b2_orig["offset"]:b2_orig["offset"] + b2_orig["size"]]
    z2_nuevo = generado[b2_nuevo["offset"]:b2_nuevo["offset"] + b2_nuevo["size"]]
    if hashlib.sha256(z2_orig).digest() != hashlib.sha256(z2_nuevo).digest():
        problemas.append("la zona Z_2 no es identica al original")

    # Comparar el prefijo en coordenadas de flash, usando el flash_offset declarado
    # por cada imagen (el generado suele omitir los primeros 64 KiB de bootloader).
    seg1_orig = original[fin_orig + layout["offset_seg1"]:]
    seg1_nuevo = generado[fin_nuevo + layout["offset_seg1"]:]
    fo_orig = inf_orig["blocks"][0]["segments"][1]["flash_offset"]
    fo_nuevo = inf_nuevo["blocks"][0]["segments"][1]["flash_offset"]
    ini, fin = layout["prefijo_flash_inicio"], layout["prefijo_flash_fin"]
    pref_orig = seg1_orig[ini - fo_orig:fin - fo_orig]
    pref_nuevo = seg1_nuevo[ini - fo_nuevo:fin - fo_nuevo]
    if len(pref_orig) != len(pref_nuevo) or len(pref_orig) != fin - ini:
        problemas.append("el prefijo del firmware generado tiene otro tamano")
    else:
        permitidos = set(
            range(spec["hook"]["offset_puntero_trampolin"], spec["hook"]["offset_puntero_trampolin"] + 4)
        ) | set(
            range(
                int(spec["hook"]["va"], 0) - ini,
                int(spec["hook"]["va"], 0) - ini + (len(spec["parches"]) * 8) + 76,
            )
        )
        fuera = [i for i in range(len(pref_orig)) if pref_orig[i] != pref_nuevo[i] and i not in permitidos]
        if fuera:
            problemas.append(f"hay {len(fuera)} bytes modificados fuera del hook (primer offset: 0x{fuera[0]:x})")

    return {
        "correcto": not problemas,
        "problemas": problemas,
        "original": {"sha256": inf_orig["rcx_sha256"], "version": inf_orig["package"]},
        "generado": {"sha256": inf_nuevo["rcx_sha256"], "version": inf_nuevo["package"]},
        "componentes_intactos": firma_componentes(inf_orig) == firma_componentes(inf_nuevo),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("original", type=Path, help="Firmware oficial de Epson")
    parser.add_argument("generado", type=Path, help="Firmware construido")
    parser.add_argument("--spec", type=Path, default=SPEC_POR_DEFECTO, help="JSON con la tabla de parches")
    args = parser.parse_args()

    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    try:
        resultado = verifica(
            epson_rcx.load_rcx(args.original), epson_rcx.load_rcx(args.generado), spec
        )
    except (OSError, ValueError, KeyError, struct.error) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1)

    print(json.dumps(resultado, indent=2, ensure_ascii=False))
    raise SystemExit(0 if resultado["correcto"] else 2)


if __name__ == "__main__":
    main()
