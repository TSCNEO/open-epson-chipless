# SPDX-License-Identifier: 0BSD
"""Descubre los puntos de parche en un firmware oficial de Epson cualquiera.

No lleva tablas de direcciones: las busca en el binario que le des. Sirve para
una version nueva de la misma familia o para otro modelo con la misma estructura
IPL/CROM. Genera un borrador de spec que `construir.py` puede consumir tras
revisarlo.

Uso:
    python3 descubrir.py FW.efu
    python3 descubrir.py FW.efu --emitir-spec data/patches/<familia>/<version>.json
    python3 descubrir.py FW.efu --base-crom3 0x41C2D000 --flush 0x15840

Necesita capstone (solo esta herramienta; el constructor no lo usa):
    pip install capstone
"""

import argparse
import collections
import hashlib
import json
import re
import sys
from pathlib import Path

import epson_rcx

try:
    import capstone
    from capstone import arm as cs_arm
except ImportError:  # pragma: no cover
    raise SystemExit("falta capstone: pip install capstone")

RANGO_RAM = (0x40000000, 0x4FFFFFFF)  # ventana de RAM del SoC; varia por modelo (0x41.. en XP-247, 0x45.. en XP-342)
PALABRA_MCR_DCACHE = 0xEE071F1A  # mcr p15, 0, rX, c7, c10, 0
MAX_INSTRUCCIONES = 400_000


def palabra(ins):
    """Devuelve el inmediato de una instruccion, o None."""
    if len(ins.operands) < 2:
        return None
    if ins.operands[-1].type != cs_arm.ARM_OP_IMM:
        return None
    return ins.operands[-1].imm


def es_mov_imm(ins, valor=None):
    if not ins.mnemonic.startswith("mov"):
        return False
    inm = palabra(ins)
    if inm is None:
        return False
    return True if valor is None else inm == valor


def desensamblar(datos: bytes, base: int):
    md = capstone.Cs(capstone.CS_ARCH_ARM, capstone.CS_MODE_ARM)
    md.detail = True
    md.skipdata = True
    instrucciones, siguiente = [], base
    por_direccion = {}
    for ins in md.disasm(datos, base):
        if ins.id == 0 or len(instrucciones) > MAX_INSTRUCCIONES:
            continue
        instrucciones.append(ins)
        por_direccion[ins.address] = ins
    return instrucciones, por_direccion


def funcion_de(por_direccion, direccion, limite=0x400):
    """Sube desde una instruccion hasta el `push` que abre su funcion.

    Si justo antes del `push` hay cargas de constantes (`ldr rX, [pc, ...]`), la
    entrada real es anterior: el compilador las coloca antes del prologo.
    """
    base = None
    for atras in range(0, limite, 4):
        ins = por_direccion.get(direccion - atras)
        if ins and ins.mnemonic == "push" and "lr" in ins.op_str:
            base = ins.address
            break
    if base is None:
        return None
    while True:
        anterior = por_direccion.get(base - 4)
        if anterior is None or anterior.mnemonic != "ldr" or "[pc" not in anterior.op_str:
            break
        base = anterior.address
    return base


def llamadas_a(instrucciones, destino):
    return [
        i.address
        for i in instrucciones
        if i.mnemonic == "bl" and i.operands and i.operands[0].type == cs_arm.ARM_OP_IMM
        and i.operands[0].imm == destino
    ]


# --- estructura -------------------------------------------------------------

def analizar_estructura(rcx: bytes) -> dict:
    informe = epson_rcx.inspect(rcx, decompress_crom=True, incluir_datos=True)
    cabecera_fin = rcx.index(b"\x0c") + 1
    version = informe["package"]
    z1 = rcx[cabecera_fin:cabecera_fin + informe["blocks"][0]["size"]]
    seg1 = z1[0x3000:]
    prefijo = seg1[0x10000:0x40000]
    return {
        "version": version,
        "sha256_rcx": hashlib.sha256(rcx).hexdigest(),
        "informe": informe,
        "z1": z1,
        "seg1": seg1,
        "prefijo": prefijo,
    }


def buscar_trampolin(seg1: bytes):
    candidatos = []
    for offset in range(0x10000, min(len(seg1), 0x40000) - 8, 4):
        palabra_ins = int.from_bytes(seg1[offset:offset + 4], "little")
        if palabra_ins != 0xE51FF004:
            continue
        destino = int.from_bytes(seg1[offset + 4:offset + 8], "little")
        if RANGO_RAM[0] <= destino < RANGO_RAM[1]:
            candidatos.append(
                {"va": offset, "offset_prefijo": offset - 0x10000,
                 "instr": palabra_ins, "destino": destino, "verificado": None}
            )
    return candidatos


def huecos_libres(prefijo: bytes, minimo=300):
    huecos, inicio = [], None
    for i, byte in enumerate(prefijo):
        if byte == 0xFF:
            if inicio is None:
                inicio = i
        else:
            if inicio is not None and i - inicio >= minimo:
                huecos.append({"offset_prefijo": inicio, "va": inicio + 0x10000, "tamano": i - inicio})
            inicio = None
    if inicio is not None and len(prefijo) - inicio >= minimo:
        huecos.append({"offset_prefijo": inicio, "va": inicio + 0x10000,
                       "tamano": len(prefijo) - inicio})
    huecos.sort(key=lambda h: -h["tamano"])
    return huecos


def alinear_hueco(hueco: dict) -> dict:
    """Coloca la rutina en la primera direccion alineada a 256 bytes del hueco."""
    inicio = (hueco["va"] + 0xFF) & ~0xFF
    return {"va": inicio, "offset_prefijo": inicio - 0x10000,
            "tamano": hueco["tamano"] - (inicio - hueco["va"])}


def funcion_flush(seg1: bytes):
    """Devuelve las funciones relacionadas con la limpieza de D-cache (primitivas y envoltorios)."""
    prefijo = seg1[0x10000:0x40000]
    mcr = [0x10000 + i for i in range(0, len(prefijo) - 4, 4)
           if int.from_bytes(prefijo[i:i + 4], "little") == PALABRA_MCR_DCACHE]
    instrucciones, por_direccion = desensamblar(prefijo, 0x10000)
    primitivas = set()
    for direccion in mcr:
        base = funcion_de(por_direccion, direccion)
        if base:
            primitivas.add(base)
    candidatos = set(primitivas)
    nivel = set(primitivas)
    for _ in range(2):  # envoltorios por encima de la primitiva
        siguiente = set()
        for base in nivel:
            for llamada in llamadas_a(instrucciones, base):
                envoltorio = funcion_de(por_direccion, llamada, limite=0x40)
                if envoltorio and envoltorio not in candidatos:
                    siguiente.add(envoltorio)
        candidatos |= siguiente
        nivel = siguiente
        if not nivel:
            break
    return sorted(candidatos), mcr


# --- subsistema de cartuchos -------------------------------------------------

def analizar_codigo(datos: bytes, base: int) -> dict:
    instrucciones, por_direccion = desensamblar(datos, base)

    # 1. Envoltorio de lectura: prologo con reintento 3 que registra el codigo de error 0x2A.
    lectura = None
    for ins in instrucciones:
        if es_mov_imm(ins, 0x2A):
            inicio = funcion_de(por_direccion, ins.address)
            if inicio and any(es_mov_imm(por_direccion.get(inicio + 4 * k), 3) for k in range(1, 10)
                              if por_direccion.get(inicio + 4 * k)):
                lectura = inicio
                break

    # 2. Envoltorio de escritura: hermano con el mismo prologo, cerca del anterior.
    escritura = None
    if lectura:
        for ins in instrucciones:
            if ins.address <= lectura or ins.address > lectura + 0x400:
                continue
            if ins.mnemonic == "push" and "lr" in ins.op_str and any(
                es_mov_imm(por_direccion.get(ins.address + 4 * k), 3) for k in range(1, 10)
                if por_direccion.get(ins.address + 4 * k)
            ):
                escritura = ins.address
                break

    # 3. Presencia: funcion que pide los registros 0x67 y 0x68, los combina con lsl #2 / orr
    #    y compara contra 1. Puede haber varias parecidas: gana la que use un agregador con 4 canales.
    candidatas = []
    for ins in instrucciones:
        if not es_mov_imm(ins, 0x67):
            continue
        cercanos = [por_direccion.get(ins.address + 4 * k) for k in range(0, 16)]
        if not any(x is not None and es_mov_imm(x, 0x68) for x in cercanos):
            continue
        inicio_funcion = funcion_de(por_direccion, ins.address)
        if not inicio_funcion:
            continue
        cuerpo = [x for a, x in por_direccion.items() if inicio_funcion <= a < inicio_funcion + 0x200]
        if not any(x.mnemonic in ("orr", "and") and "lsl #2" in x.op_str for x in cuerpo):
            continue
        if not any(x.mnemonic == "cmp" and palabra(x) == 1 for x in cuerpo):
            continue
        if inicio_funcion not in candidatas:
            candidatas.append(inicio_funcion)

    presencia, parche_presencia, agregador, llamadas = None, None, None, []
    mejor = -1
    for inicio_funcion in candidatas:
        llamadas_funcion = llamadas_a(instrucciones, inicio_funcion)
        agregador_candidato, canales = None, 0
        for llamada in llamadas_funcion:
            inicio_llamante = funcion_de(por_direccion, llamada)
            if not inicio_llamante:
                continue
            cuerpo = [x for a, x in por_direccion.items()
                      if inicio_llamante <= a < inicio_llamante + 0x200]
            canal = next((palabra(x) for x in cuerpo
                          if x.mnemonic == "cmp" and palabra(x) in (3, 4)), None)
            if canal and startswith_ok(canal):
                agregador_candidato, canales = inicio_llamante, canal
                break
        puntuacion = canales * 100 + len(llamadas_funcion)
        if agregador_candidato and puntuacion > mejor:
            mejor = puntuacion
            presencia, agregador = inicio_funcion, agregador_candidato
    if presencia:
        cuerpo = [x for a, x in por_direccion.items() if presencia <= a < presencia + 0x200]
        for x in sorted(cuerpo, key=lambda y: y.address):
            if not x.mnemonic.startswith("b") or x.mnemonic == "bl":
                continue
            if not x.operands or x.operands[0].type != cs_arm.ARM_OP_IMM:
                continue
            anterior = por_direccion.get(x.operands[0].imm - 4)
            if anterior is not None and es_mov_imm(anterior, 0) and anterior.address >= presencia:
                parche_presencia = anterior.address
                break
        llamadas = llamadas_a(instrucciones, agregador) if agregador else []

    return {
        "instrucciones": len(instrucciones),
        "envoltorio_lectura": lectura,
        "envoltorio_escritura": escritura,
        "presencia": presencia,
        "parche_presencia": parche_presencia,
        "agregador": agregador,
        "llamadas_agregador": sorted(llamadas),
        "por_direccion": por_direccion,
    }


def startswith_ok(canal):
    """Los canales de tinta son 3 o 4; cualquier otro valor indica que no es el agregador."""
    return canal in (3, 4)


def contexto(por_direccion, direccion, n=3):
    trozos = []
    for k in range(1, n + 1):
        ins = por_direccion.get(direccion + 4 * k)
        if ins:
            trozos.append(f"{ins.mnemonic} {ins.op_str}")
    return " ; ".join(trozos)


# --- informe y spec ----------------------------------------------------------

def informa(estructura: dict, trampolin: list, huecos: list, flush: list,
            mcr: list, codigo: dict, base_crom3: int) -> None:
    inf = estructura["informe"]
    print(f"version            {estructura['version']}")
    print(f"rcx sha256         {estructura['sha256_rcx']}")
    for bloque in inf["blocks"]:
        estados = [("sum16 OK" if s["checksum16_ok"] else "sum16 MAL") for s in bloque["segments"]]
        print(f"  {bloque['zone']:<6} {bloque['size']:>9} B  {' '.join(estados)}")
    print(f"trampolin          {len(trampolin)} candidato(s)")
    for t in trampolin:
        print(f"  va {t['va']:#08x}  destino {t['destino']:#010x}")
    if huecos:
        h = huecos[0]
        print(f"hueco libre        {h['tamano']} B en va {h['va']:#08x} (prefijo +{h['offset_prefijo']:#x})")
    print(f"flush D-cache      {len(mcr)} instruccion(es) mcr; envoltorios: "
          + ", ".join(f"{c:#08x}" for c in flush[:5]))
    print()
    print(f"instrucciones CROM3 {codigo['instrucciones']}")
    for etiqueta, clave in (("envoltorio lectura", "envoltorio_lectura"),
                            ("envoltorio escritura", "envoltorio_escritura"),
                            ("funcion presencia", "presencia"),
                            ("  salida a parchear", "parche_presencia"),
                            ("agregador", "agregador")):
        valor = codigo[clave]
        texto = f"{valor:#010x} (offset +{valor - base_crom3:#x})" if valor else "NO ENCONTRADO"
        print(f"  {etiqueta:<20} {texto}")
    print(f"  llamadas al agregador {len(codigo['llamadas_agregador'])}")
    print()
    print("Primeras 8 llamadas al agregador y su contexto:")
    for direccion in codigo["llamadas_agregador"][:8]:
        print(f"  {direccion:#010x}  ->  {contexto(codigo['por_direccion'], direccion)}")


def construir_spec(estructura: dict, trampolin: dict, hueco: dict, codigo: dict,
                   base_crom3: int, flush: int, version_declarada: str,
                   offset_contenedor: int) -> dict:
    inf = estructura["informe"]
    por_direccion = codigo["por_direccion"]
    parches = []

    def añade(va, nuevo, nota):
        ins = por_direccion.get(va)
        if not ins:
            return
        parches.append({
            "va": f"0x{va:08X}",
            "original": f"0x{int.from_bytes(ins.bytes, 'little'):08X}",
            "nuevo": f"0x{nuevo:08X}",
            "nota": nota,
        })

    if codigo["envoltorio_lectura"]:
        añade(codigo["envoltorio_lectura"], 0xE3A00000, "lectura CSIC: devuelve exito")
        añade(codigo["envoltorio_lectura"] + 4, 0xE12FFF1E, "lectura CSIC: retorno inmediato")
    if codigo["envoltorio_escritura"]:
        añade(codigo["envoltorio_escritura"], 0xE3A00000, "escritura CSIC: devuelve exito")
        añade(codigo["envoltorio_escritura"] + 4, 0xE12FFF1E, "escritura CSIC: retorno inmediato")
    if codigo["parche_presencia"]:
        añade(codigo["parche_presencia"], 0xE3A00001, "presencia: devuelve 1 siempre")

    return {
        "version_base": estructura["version"],
        "version_declarada": version_declarada,
        "sha256_rcx_base": estructura["sha256_rcx"],
        "crom3_base_ram": f"0x{base_crom3:08X}",
        "layout": {
            "tamano_z1": inf["blocks"][0]["size"],
            "tamano_z2": inf["blocks"][1]["size"],
            "tamano_cabecera_ipl": inf["blocks"][0]["segments"][0]["offset"],
            "tamano_seg0": inf["blocks"][0]["segments"][0]["size"],
            "offset_seg1": inf["blocks"][0]["segments"][1]["offset"],
            "tamano_bootloader": 65536,
            "prefijo_flash_inicio": 65536,
            "prefijo_flash_fin": 262144,
            "crom3_offset_flash": offset_contenedor,
        },
        "hook": {
            "va": f"0x{hueco['va']:08X}",
            "offset_instr_trampolin": trampolin["offset_prefijo"],
            "offset_puntero_trampolin": trampolin["offset_prefijo"] + 4,
            "instr_trampolin": "0xE51FF004",
            "destino_original": f"0x{trampolin['destino']:08X}",
            "funcion_flush_dcache": f"0x{flush:08X}",
        },
        "parches": parches,
        "candidatos_pendientes_revision": [
            {"va": f"0x{d:08X}", "contexto": contexto(por_direccion, d)}
            for d in codigo["llamadas_agregador"]
        ],
        "_procedencia": "generado por tools/descubrir.py a partir del firmware oficial; revisar antes de flashear",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("firmware", type=Path, help="Firmware oficial (.zip, .efu o .rcx)")
    parser.add_argument("--base-crom3", default="0x41C2D000",
                        help="Direccion de carga del bloque de cartuchos (por defecto 0x41C2D000)")
    parser.add_argument("--flush", default=None, help="Direccion de la funcion de limpieza de D-cache")
    parser.add_argument("--trampolin", default=None,
                        help="VA del enganche de arranque (obligatorio para emitir spec; ver candidatos)")
    parser.add_argument("--emitir-spec", type=Path, default=None, help="Guardar borrador de spec JSON")
    args = parser.parse_args()

    rcx = epson_rcx.load_rcx(args.firmware)
    estructura = analizar_estructura(rcx)
    cabecera_fin = rcx.index(b"\x0c") + 1
    base_crom3 = int(args.base_crom3, 0)

    trampolines = buscar_trampolin(estructura["seg1"])
    huecos = huecos_libres(estructura["prefijo"])
    flush_candidatos, mcr = funcion_flush(estructura["seg1"])

    # El bloque que contiene la logica de cartuchos: se busca el que tenga las huellas.
    mejor, mejor_bloque, mejor_offset = None, None, None
    for contenedor in estructura["informe"]["blocks"][0]["crom_containers"]:
        for parte in contenedor["parts"]:
            datos = parte.get("data")
            if not datos:
                continue
            analisis = analizar_codigo(datos, base_crom3)
            puntuacion = sum(bool(analisis[k]) for k in
                             ("envoltorio_lectura", "envoltorio_escritura", "presencia", "agregador"))
            if mejor is None or puntuacion > mejor:
                mejor, mejor_bloque = puntuacion, analisis
                mejor_offset = contenedor["offset"] - cabecera_fin - 0x3000

    if not mejor_bloque:
        raise SystemExit("no se ha podido descomprimir ningun bloque CROM; revisa el fichero")

    informa(estructura, trampolines, huecos, flush_candidatos, mcr, mejor_bloque, base_crom3)

    if not args.emitir_spec:
        return
    if not huecos:
        raise SystemExit("no hay hueco libre en el prefijo: no se puede emitir spec")
    if not args.trampolin:
        print("\nNo se emite spec: hay que fijar el enganche de arranque con --trampolin.")
        print("Los veneers de llamada son indistinguibles por estructura; el valido es el que se")
        print("ejecuta al arrancar. Candidatos:")
        for t in trampolines[:12]:
            print(f"  --trampolin 0x{t['va']:08x}   destino {t['destino']:#010x}")
        raise SystemExit(2)
    elegido = next((t for t in trampolines if t["va"] == int(args.trampolin, 0)), None)
    if elegido is None:
        raise SystemExit(f"0x{int(args.trampolin, 0):08x} no es un candidato valido")
    flush = int(args.flush, 0) if args.flush else (flush_candidatos[-1] if flush_candidatos else 0x15840)
    version_declarada = epson_rcx.version_mayor(estructura["version"])
    spec = construir_spec(estructura, elegido, alinear_hueco(huecos[0]), mejor_bloque, base_crom3,
                          flush, version_declarada, mejor_offset)
    args.emitir_spec.parent.mkdir(parents=True, exist_ok=True)
    args.emitir_spec.write_text(json.dumps(spec, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"\nborrador escrito en {args.emitir_spec}")
    print("revisa los parches y completa candidatos_pendientes_revision antes de construir")


if __name__ == "__main__":
    main()
