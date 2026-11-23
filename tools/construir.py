# SPDX-License-Identifier: 0BSD
"""Construye un RCX modificado a partir del firmware oficial de Epson.

No incluye ni redistribuye binarios de Epson: el usuario aporta su propia copia
oficial y este script la parchea en memoria.

Uso:
    python3 construir.py EF20J9.efu --out-dir build
    python3 construir.py EF20J9.rcx --out-dir build --rcx-version 20.25.EF99Z9.FY16
"""

import argparse
import hashlib
import json
import re
import struct
import zipfile
from pathlib import Path

import epson_rcx

SPEC_POR_DEFECTO = Path(__file__).resolve().parent.parent / "data" / "patches" / "xp243-245-247" / "ef20j9.json"
VERSION_RE = re.compile(r"^[0-9A-Z]{1,3}\.[0-9A-Z]{1,3}\.[A-Z0-9]{4,8}\.FY16$")

# Bloque fijo del hook: 17 palabras, tabla de pares a continuacion.
HOOK_CODIGO = [
    0xE92D401F,  # push {r0, r1, r2, r3, r4, lr}
    0xE28F0038,  # add  r0, pc, #0x38      -> inicio de la tabla
    0xE8B00006,  # ldmia r0!, {r1, r2}      r1 = destino, r2 = opcode
    0xE3510000,  # cmp  r1, #0
    0x0A000001,  # beq  flush
    0xE5812000,  # str  r2, [r1]
    0xEAFFFFFA,  # b    loop
    0xE59F301C,  # ldr  r3, [pc, #0x1c]     -> funcion de flush
    0xE12FFF33,  # blx  r3
    0xE3A00000,  # mov  r0, #0
    0xEE070F15,  # mcr  p15, 0, r0, c7, c5, 0   invalidar I-cache
    0xEE070FD5,  # mcr  p15, 0, r0, c7, c5, 6   vaciar BTB
    0xEE070F95,  # mcr  p15, 0, r0, c7, c5, 4   prefetch flush
    0xE8BD401F,  # pop  {r0, r1, r2, r3, r4, lr}
    0xE51FF004,  # ldr  pc, [pc, #-4]
]
TAMANO_CABECERA_HOOK = (len(HOOK_CODIGO) + 4) * 4  # +2 palabras fijas +2 terminador


def palabra(valor) -> int:
    return int(valor, 0) if isinstance(valor, str) else int(valor)


def construir_hook(spec: dict) -> bytes:
    """Ensambla la rutina que parchea la RAM en el arranque (codigo propio, no de Epson)."""
    palabras = list(HOOK_CODIGO)
    palabras.append(palabra(spec["hook"]["destino_original"]))
    palabras.append(palabra(spec["hook"]["funcion_flush_dcache"]))
    for parche in spec["parches"]:
        palabras.append(palabra(parche["va"]))
        palabras.append(palabra(parche["nuevo"]))
    palabras.append(0)  # terminador
    palabras.append(0)
    return b"".join(struct.pack("<I", p) for p in palabras)


def crom3_parte0(z1: bytes, layout: dict) -> bytes:
    """Extrae y descomprime la primera parte del contenedor CROM de Z0_CROM3."""
    base = layout["crom3_offset_flash"]  # coordenada de seg1 == offset de flash
    if not z1.startswith(b"CROM\xff\xd8", base):
        raise ValueError(f"cabecera CROM ausente en 0x{base:x}")
    pos = base + 10  # "CROM" + 0xFFD8 + longitud big-endian
    marca, mlen = struct.unpack_from(">HH", z1, pos)
    if marca != 0xFFC4:
        raise ValueError(f"marcador CROM inesperado: 0x{marca:04x}")
    dht = z1[pos + 4:pos + 2 + mlen]
    pos += 2 + mlen

    marca, mlen = struct.unpack_from(">HH", z1, pos)
    if marca != 0xFFB1:
        raise ValueError(f"marcador CROM inesperado: 0x{marca:04x}")
    coded_bytes, num_items = struct.unpack_from(">LL", z1, pos + 5)
    pos += 2 + mlen
    coded = z1[pos:pos + coded_bytes]
    pos += coded_bytes

    marca, mlen = struct.unpack_from(">HH", z1, pos)
    if marca != 0xFFB2:
        raise ValueError(f"marcador CROM inesperado: 0x{marca:04x}")
    lit_len, = struct.unpack_from(">L", z1, pos + 4)
    pos += 2 + mlen
    return epson_rcx._decompress_crom_part(dht, coded, num_items, z1[pos:pos + lit_len])


def verificar_base(z1: bytes, hook: bytes, spec: dict) -> None:
    """Comprueba trampolin, espacio libre y los opcodes originales antes de tocar nada."""
    layout = spec["layout"]
    prefijo = layout["prefijo_flash_inicio"]

    off_insn = prefijo + spec["hook"]["offset_instr_trampolin"]
    off_ptr = prefijo + spec["hook"]["offset_puntero_trampolin"]
    insn, ptr = struct.unpack_from("<II", z1, off_insn)
    if insn != palabra(spec["hook"]["instr_trampolin"]):
        raise ValueError(f"trampolin inesperado: instruccion 0x{insn:08x}")
    if ptr != palabra(spec["hook"]["destino_original"]):
        raise ValueError(f"trampolin inesperado: destino 0x{ptr:08x}")

    inicio_hook = palabra(spec["hook"]["va"])  # coordenada de seg1 == offset de flash
    tramo = z1[inicio_hook:inicio_hook + len(hook)]
    if len(tramo) != len(hook) or any(b != 0xFF for b in tramo):
        raise ValueError(
            f"el rango 0x{palabra(spec['hook']['va']):x} no esta libre (se esperaba 0xFF)"
        )

    p0 = crom3_parte0(z1, layout)
    esperado = spec.get("crom3_p0_sha256")
    if esperado and hashlib.sha256(p0).hexdigest() != esperado:
        raise ValueError("Z0_CROM3.p0 no coincide con el hash esperado para esta version")

    base_ram = palabra(spec["crom3_base_ram"])
    for parche in spec["parches"]:
        va = palabra(parche["va"])
        off = va - base_ram
        if not 0 <= off <= len(p0) - 4:
            raise ValueError(f"direccion 0x{va:x} fuera de Z0_CROM3.p0")
        actual, = struct.unpack_from("<I", p0, off)
        if actual != palabra(parche["original"]):
            raise ValueError(
                f"opcode original inesperado en 0x{va:x}: "
                f"esperado 0x{palabra(parche['original']):08x}, encontrado 0x{actual:08x}"
            )


def actualizar_manifiesto(cabecera: bytes, version: str, tamano_z1: int, spec: dict) -> bytes:
    """Reescribe [D] 3 (version declarada) y [Z_1] 5 (tamano de la zona)."""
    texto = cabecera.decode("ascii")
    version_base = spec["version_base"]
    texto, n = re.subn(
        rf'^3="{re.escape(version_base)}"(?=\r?$)',
        f'3="{version}"',
        texto,
        count=1,
        flags=re.MULTILINE,
    )
    if n != 1:
        raise ValueError(f'no se encontro [D] 3="{version_base}" en el manifiesto')
    tamano_original = spec["layout"]["tamano_z1"]
    if tamano_z1 != tamano_original:
        texto, n = re.subn(
            rf'(\[Z_1\]\r?\n5="){tamano_original}(")',
            rf"\g<1>{tamano_z1}\2",
            texto,
            count=1,
        )
        if n != 1:
            raise ValueError(f'no se encontro [Z_1] 5="{tamano_original}" en el manifiesto')
    return texto.encode("ascii")


def construye(rcx_base: bytes, spec: dict, version: str, incluir_bootloader: bool) -> tuple[bytes, dict]:
    if hashlib.sha256(rcx_base).hexdigest() != spec["sha256_rcx_base"]:
        raise ValueError(f"la entrada no es la version base esperada ({spec['sha256_rcx_base']})")
    if not VERSION_RE.match(version):
        raise ValueError(f"version RCX invalida: {version}")

    layout = spec["layout"]
    informe = epson_rcx.inspect(rcx_base, decompress_crom=True)
    for bloque in informe["blocks"]:
        if not all(seg["checksum16_ok"] for seg in bloque["segments"]):
            raise ValueError(f"suma de 16 bits invalida en la entrada ({bloque['zone']})")
        if not all(seg.get("sha1_ok", True) for seg in bloque["segments"]):
            raise ValueError(f"SHA-1 IPL invalido en la entrada ({bloque['zone']})")

    fin_cabecera = rcx_base.index(b"\x0c") + 1
    if len(rcx_base) != fin_cabecera + layout["tamano_z1"] + layout["tamano_z2"]:
        raise ValueError("longitud inesperada del RCX base")

    z1 = rcx_base[fin_cabecera:fin_cabecera + layout["tamano_z1"]]
    z2 = rcx_base[fin_cabecera + layout["tamano_z1"]:]

    esperado_z2 = spec.get("z2_sha256_base")
    if esperado_z2 and hashlib.sha256(z2).hexdigest() != esperado_z2:
        raise ValueError("la zona Z_2 no coincide con el hash esperado")

    hook = construir_hook(spec)
    verificar_base(z1[layout["offset_seg1"]:], hook, spec)

    cabecera_y_seg0 = bytearray(z1[:layout["offset_seg1"]])
    seg1 = bytearray(z1[layout["offset_seg1"]:])

    prefijo_ref = bytes(seg1[layout["prefijo_flash_inicio"]:layout["prefijo_flash_fin"]])
    struct.pack_into(
        "<I",
        seg1,
        layout["prefijo_flash_inicio"] + spec["hook"]["offset_puntero_trampolin"],
        palabra(spec["hook"]["va"]),
    )
    inicio_hook = palabra(spec["hook"]["va"])
    seg1[inicio_hook:inicio_hook + len(hook)] = hook
    prefijo_nuevo = bytes(seg1[layout["prefijo_flash_inicio"]:layout["prefijo_flash_fin"]])

    if incluir_bootloader:
        offset_flash = 0
    else:
        seg1 = seg1[layout["tamano_bootloader"]:]
        offset_flash = layout["tamano_bootloader"]

    seg1_bytes = bytes(seg1)
    suma16 = sum(seg1_bytes) & 0xFFFF
    struct.pack_into("<HHIII", cabecera_y_seg0, 0x34, 2, suma16, 0, offset_flash, len(seg1_bytes))
    sha1_cabecera = hashlib.sha1(bytes(cabecera_y_seg0[:0x0E])).digest()
    cabecera_y_seg0[0x44:0x58] = hashlib.sha1(seg1_bytes + sha1_cabecera).digest()

    z1_nueva = bytes(cabecera_y_seg0) + seg1_bytes
    cabecera = actualizar_manifiesto(rcx_base[:fin_cabecera], version, len(z1_nueva), spec)
    rcx_nuevo = cabecera + z1_nueva + z2

    # Verificacion posterior: la imagen debe cumplir exactamente lo declarado.
    nuevo = epson_rcx.inspect(rcx_nuevo, decompress_crom=True)
    for bloque in nuevo["blocks"]:
        if not all(seg["checksum16_ok"] for seg in bloque["segments"]):
            raise AssertionError(f"suma de 16 bits incorrecta tras parchear ({bloque['zone']})")
        if not all(seg.get("sha1_ok", True) for seg in bloque["segments"]):
            raise AssertionError(f"SHA-1 IPL incorrecto tras parchear ({bloque['zone']})")
    def firma_componentes(inf: dict) -> dict:
        z1b, z2b = inf["blocks"]
        return {
            "z1_crom": [[p["uncompressed_sha256"] for p in c["parts"]] for c in z1b["crom_containers"]],
            "z2_crom": [[p["uncompressed_sha256"] for p in c["parts"]] for c in z2b["crom_containers"]],
            "componentes": [c["sha256"] for c in z1b["components"]],
        }

    if firma_componentes(nuevo) != firma_componentes(informe):
        raise AssertionError("algun contenedor CROM, uImage o SquashFS cambio respecto al oficial")
    bloque_z2_nuevo = rcx_nuevo[len(cabecera) + len(z1_nueva):]
    if hashlib.sha256(bloque_z2_nuevo).digest() != hashlib.sha256(z2).digest():
        raise AssertionError("Z_2 fue alterado inesperadamente")

    permitidos = set(
        range(spec["hook"]["offset_puntero_trampolin"],
              spec["hook"]["offset_puntero_trampolin"] + 4)
    ) | set(range(inicio_hook - layout["prefijo_flash_inicio"],
              inicio_hook - layout["prefijo_flash_inicio"] + len(hook)))
    if any(
        prefijo_ref[i] != prefijo_nuevo[i]
        for i in range(len(prefijo_ref))
        if i not in permitidos
    ):
        raise AssertionError("el diff del prefijo excede las direcciones esperadas")

    resumen = {
        "sha256_entrada": spec["sha256_rcx_base"],
        "version_declarada": version,
        "bootloader_incluido": incluir_bootloader,
        "offset_flash_z1": f"0x{offset_flash:08x}",
        "hook_va": f"0x{palabra(spec['hook']['va']):08x}",
        "hook_bytes": len(hook),
        "puntos_parcheados": len(spec["parches"]),
        "tamano_salida": len(rcx_nuevo),
        "sha256_salida": hashlib.sha256(rcx_nuevo).hexdigest(),
        "verificado": True,
    }
    return rcx_nuevo, resumen


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("entrada", type=Path, help="Firmware oficial de Epson (.efu, .rcx o .zip)")
    parser.add_argument("--spec", type=Path, default=SPEC_POR_DEFECTO, help="JSON con la tabla de parches")
    parser.add_argument("--out-dir", type=Path, default=Path("build"), help="Directorio de salida")
    parser.add_argument("--rcx-version", default=None, help="Cadena [D] 3 (por defecto, la base con 99Z9)")
    parser.add_argument(
        "--incluir-bootloader",
        action="store_true",
        help="Incluye los primeros 64 KiB (BooSt). NO recomendado: ahi vive el modo recuperacion",
    )
    args = parser.parse_args()

    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    version = (args.rcx_version or spec.get("version_declarada")
               or epson_rcx.version_mayor(spec["version_base"]))
    try:
        rcx_base = epson_rcx.load_rcx(args.entrada)
        rcx_nuevo, resumen = construye(rcx_base, spec, version, args.incluir_bootloader)
    except (OSError, ValueError, KeyError, struct.error, zipfile.BadZipFile, AssertionError) as exc:
        parser.exit(1, f"Error: {exc}\n")

    args.out_dir.mkdir(parents=True, exist_ok=True)
    # El nombre de salida sigue al del firmware de entrada (no esta fijado a una familia).
    nombre = args.entrada.stem
    ruta_rcx = args.out_dir / f"{nombre}.rcx"
    ruta_efu = args.out_dir / f"{nombre}.efu"
    ruta_rcx.write_bytes(rcx_nuevo)
    # ZIP determinista: fecha fija y orden fijo, para que el hash sea reproducible.
    with zipfile.ZipFile(ruta_efu, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        info = zipfile.ZipInfo(f"{nombre}.rcx", date_time=(1980, 1, 1, 0, 0, 0))
        info.compress_type = zipfile.ZIP_DEFLATED
        info.external_attr = 0o644 << 16
        zf.writestr(info, rcx_nuevo)

    resumen["rcx"] = str(ruta_rcx)
    resumen["efu"] = str(ruta_efu)
    resumen["sha256_efu"] = hashlib.sha256(ruta_efu.read_bytes()).hexdigest()
    print(json.dumps(resumen, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
