# SPDX-License-Identifier: 0BSD
"""Libreria para leer y verificar paquetes EpsonNet RCX (formato .efu/.rcx).

Todos los offsets se refieren al RCX sin comprimir. No requiere hardware.
"""

import argparse
import configparser
import hashlib
import io
import json
import re
import struct
import zlib
from pathlib import Path
from zipfile import BadZipFile, ZipFile

# Limit each in-memory layer, including uncompressed members and CROM payloads.
LIMIT = 64 * 1024 * 1024
RCX = b"RCX\r\nSEIKO EPSON EpsonNet Form\r\n"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def version_mayor(version: str) -> str:
    """Devuelve una version del mismo formato que el actualizador acepta como superior.

    La etiqueta de la familia XP-243/245/247 se mantiene tal cual para no alterar
    las builds ya validadas; para el resto de familias se usa una etiqueta neutra.
    """
    partes = version.split(".")
    if len(partes) != 4:
        return version
    etiqueta = "EF99Z9" if partes[2].startswith("EF") else "ZZ99Z9"
    return f"{partes[0]}.{partes[1]}.{etiqueta}.{partes[3]}"


def load_rcx(path: Path) -> bytes:
    """Accept a distribution ZIP, an EFU (itself a ZIP), or the raw RCX."""
    if path.stat().st_size > LIMIT:
        raise ValueError("entrada mayor de 64 MiB")
    data = path.read_bytes()
    for _ in range(2):
        if data.startswith(RCX):
            return data
        with ZipFile(io.BytesIO(data)) as archive:
            members = [item for item in archive.infolist() if not item.is_dir()
                       and item.filename.lower().endswith((".efu", ".rcx"))]
            if len(members) != 1:
                raise ValueError("se esperaba un único miembro EFU o RCX")
            if members[0].file_size > LIMIT:
                raise ValueError("miembro mayor de 64 MiB")
            data = archive.read(members[0])
    if not data.startswith(RCX):
        raise ValueError("cabecera EpsonNet RCX desconocida")
    return data


def _unpack_huffman_table(dht: bytes, pos: int, index: int) -> tuple[list[tuple[int, int] | None], int]:
    """Decode one JPEG-style 0xFFC4 Huffman table (0xf0 + index)."""
    if pos >= len(dht) or dht[pos] != 0xf0 + index:
        raise ValueError(f"tabla Huffman CROM inválida en índice {index}")
    pos += 1
    if pos + 16 > len(dht):
        raise ValueError("tabla Huffman CROM truncada en conteos")
    counts = dht[pos:pos + 16]
    pos += 16
    total_syms = sum(counts)
    if pos + total_syms > len(dht):
        raise ValueError("tabla Huffman CROM truncada en símbolos")
    table: list[tuple[int, int] | None] = [None] * 0x10000
    code = 0
    for length in range(1, 17):
        for _ in range(counts[length - 1]):
            symbol = dht[pos]
            pos += 1
            start = code << (16 - length)
            span = 0x10000 >> length
            if start + span > 0x10000:
                raise ValueError("código Huffman CROM fuera de rango")
            table[start:start + span] = [(length, symbol)] * span
            code += 1
        code <<= 1
    return table, pos


def _decompress_crom_part(dht: bytes, coded: bytes, num_items: int, lit: bytes) -> bytes:
    """Decompress a single CROM part (3 JPEG-style Huffman tables + LZ77 copy/literal stream)."""
    pos = 0
    tables = []
    for idx in range(3):
        table, pos = _unpack_huffman_table(dht, pos, idx)
        tables.append(table)
    if pos != len(dht):
        raise ValueError("bytes sobrantes en marcador CROM 0xFFC4")

    t0, t1, t2 = tables
    cpos = 0
    clen = len(coded)
    buf = 0
    buf_bits = 0
    out = bytearray()
    lp = 0
    lit_len = len(lit)

    for _ in range(num_items):
        syms = []
        for table in (t0, t1, t2):
            while buf_bits < 16:
                byte = coded[cpos] if cpos < clen else 0
                cpos += 1
                buf = (buf << 8) | byte
                buf_bits += 8
            buf &= 0xffffff
            entry = table[(buf >> (buf_bits - 16)) & 0xffff]
            if entry is None:
                raise ValueError("código Huffman CROM inválido en flujo")
            length, symbol = entry
            syms.append(symbol)
            buf_bits -= length
        if cpos > clen + 2:
            raise ValueError("flujo Huffman CROM truncado")

        control, offset_lo, offset_hi = syms
        offset = offset_lo | (offset_hi << 8)
        if not offset:
            if control == 0xff:
                continue
            count = control + 1
            if lp + count > lit_len:
                raise ValueError("flujo literal CROM truncado")
            if len(out) + count > LIMIT:
                raise ValueError("salida CROM mayor de 64 MiB")
            out.extend(lit[lp:lp + count])
            lp += count
        else:
            count = control + 2
            if offset > len(out):
                raise ValueError("desplazamiento LZ77 CROM fuera de rango")
            if len(out) + count > LIMIT:
                raise ValueError("salida CROM mayor de 64 MiB")
            while count:
                chunk = offset if count > offset else count
                end = -offset + chunk
                out.extend(out[-offset:None if end == 0 else end])
                count -= chunk

    return bytes(out)


def parse_ipl_segments(block: bytes) -> dict:
    """Parse EPSON IPL header descriptors and verify 16-bit checksums and SHA-1."""
    if not block.startswith(b"EPSON IPL") or len(block) < 0x3000:
        raise ValueError("cabecera EPSON IPL inválida o truncada")
    header_item_bytes, = struct.unpack_from("<H", block, 0x0e)
    if header_item_bytes < 0x48 or header_item_bytes % 0x24 != 0 or 0x10 + header_item_bytes > 0x1000:
        raise ValueError("tamaño de tabla de descriptores IPL inválido")

    header_sha1 = hashlib.sha1(block[:0x0e]).digest()
    segments = []
    for idx, body_off in enumerate((0x1000, 0x3000)):
        desc_off = 0x10 + 0x24 * idx
        seg_type, csum16_decl, bank, flash_offset, length = struct.unpack_from("<HHIII", block, desc_off)
        if body_off + length > len(block):
            raise ValueError(f"segmento IPL {idx} excede el tamaño del bloque")
        body = block[body_off:body_off + length]
        csum16_calc = sum(body) & 0xffff
        seg_info = {
            "index": idx,
            "type": seg_type,
            "bank": bank,
            "flash_offset": flash_offset,
            "offset": body_off,
            "size": length,
            "checksum16_declared": f"0x{csum16_decl:04x}",
            "checksum16_calculated": f"0x{csum16_calc:04x}",
            "checksum16_ok": csum16_calc == csum16_decl,
        }
        if idx > 0:
            sha1_decl = block[desc_off + 0x10:desc_off + 0x24].hex()
            sha1_calc = hashlib.sha1(body + header_sha1).hexdigest()
            seg_info["sha1_declared"] = sha1_decl
            seg_info["sha1_calculated"] = sha1_calc
            seg_info["sha1_ok"] = sha1_calc == sha1_decl
        segments.append(seg_info)

    return {
        "ipl_header": {
            "header_item_bytes": header_item_bytes,
            "header_prefix_sha1": header_sha1.hex(),
        },
        "segments": segments,
    }


def parse_crom_containers(block: bytes, base: int, decompress: bool = False,
                          incluir_datos: bool = False) -> list[dict]:
    """Locate CROM containers inside an IPL block and optionally decompress their parts."""
    containers = []
    for match in re.finditer(rb"CROM\xff\xd8", block):
        start = match.start()
        pos = start + 4
        parts = []
        part_idx = 0
        while pos + 6 <= len(block) and block[pos:pos + 2] == b"\xff\xd8":
            soi_mark, block_len = struct.unpack_from(">HL", block, pos)
            if soi_mark != 0xffd8:
                break
            pos += 6
            if pos + 4 > len(block):
                raise ValueError("marcador CROM 0xFFC4 truncado")
            mark, mlen = struct.unpack_from(">HH", block, pos)
            if mark != 0xffc4 or mlen < 2 or pos + 2 + mlen > len(block):
                raise ValueError(f"se esperaba marcador CROM 0xFFC4 válido, recibido 0x{mark:04x}")
            dht = block[pos + 4:pos + 2 + mlen]
            pos += 2 + mlen

            if pos + 4 > len(block):
                raise ValueError("marcador CROM 0xFFB1 truncado")
            mark, mlen = struct.unpack_from(">HH", block, pos)
            if mark != 0xffb1 or mlen < 11 or pos + 2 + mlen > len(block):
                raise ValueError(f"se esperaba marcador CROM 0xFFB1 válido, recibido 0x{mark:04x}")
            coded_bytes, num_items = struct.unpack_from(">LL", block, pos + 5)
            pos += 2 + mlen
            if pos + coded_bytes > len(block):
                raise ValueError("flujo comprimido CROM excede el bloque")
            coded = block[pos:pos + coded_bytes]
            pos += coded_bytes

            if pos + 4 > len(block):
                raise ValueError("marcador CROM 0xFFB2 truncado")
            mark, mlen = struct.unpack_from(">HH", block, pos)
            if mark != 0xffb2 or mlen < 6 or pos + 2 + mlen > len(block):
                raise ValueError(f"se esperaba marcador CROM 0xFFB2 válido, recibido 0x{mark:04x}")
            lit_len, = struct.unpack_from(">L", block, pos + 4)
            pos += 2 + mlen
            if pos + lit_len > len(block):
                raise ValueError("flujo literal CROM excede el bloque")
            lit = block[pos:pos + lit_len]
            pos += lit_len

            part_info = {
                "index": part_idx,
                "block_len": block_len,
                "copy_bytes": coded_bytes,
                "copy_items": num_items,
                "literal_bytes": lit_len,
            }
            if decompress:
                raw = _decompress_crom_part(dht, coded, num_items, lit)
                part_info["uncompressed_size"] = len(raw)
                part_info["uncompressed_sha256"] = digest(raw)
                if incluir_datos:
                    part_info["data"] = raw
            parts.append(part_info)
            part_idx += 1

        containers.append({
            "offset": base + start,
            "zone_offset": start,
            "compressed_size": pos - start,
            "parts": parts,
        })
    return containers


def components(block: bytes, base: int) -> list[dict]:
    """Identify length-bounded structures. Hash the meaningful bytes, excluding padding."""
    found = []
    for match in re.finditer(rb"hsqs|\x27\x05\x19\x56", block):
        i = match.start()
        header = block[i:i + 96]
        if match[0] == b"hsqs" and len(header) == 96:
            major, minor = struct.unpack_from("<HH", header, 28)
            size, = struct.unpack_from("<Q", header, 40)
            if (major, minor) != (4, 0) or not 96 <= size <= len(block) - i:
                continue
            inodes, = struct.unpack_from("<I", header, 4)
            codec, = struct.unpack_from("<H", header, 20)
            info = dict(type="SquashFS 4.0", inodes=inodes, compression_id=codec)
        elif match[0] == b"\x27\x05\x19\x56" and len(header) >= 64:
            header = header[:64]
            hcrc, _, payload_size, _, _, dcrc = struct.unpack_from(">6I", header, 4)
            size = payload_size + 64
            if size > len(block) - i or zlib.crc32(header[:4] + bytes(4) + header[8:]) != hcrc:
                continue
            info = dict(type="uImage", name=header[32:].rstrip(b"\0").decode("ascii", "replace"),
                        data_crc32_ok=zlib.crc32(block[i + 64:i + size]) == dcrc)
        else:
            continue
        found.append(dict(offset=base + i, size=size, sha256=digest(block[i:i + size]), **info))
    return found


def inspect(data: bytes, decompress_crom: bool = False, incluir_datos: bool = False) -> dict:
    """Validate declared block lengths and account for every RCX byte."""
    end = data.find(b"\x0c", len(RCX), 65536)
    if end < 0:
        raise ValueError("falta el fin de la cabecera RCX")
    manifest = configparser.ConfigParser(interpolation=None)
    manifest.read_string(data[len(RCX):end].decode("ascii"))
    zones = [s for s in manifest.sections() if s.startswith("Z_")]
    if not zones or zones != [f"Z_{i}" for i in range(1, len(zones) + 1)]:
        raise ValueError("numeración de zonas desconocida")
    pos = end + 1
    blocks = []
    for zone in zones:
        size = int(manifest[zone]["5"].strip('"'))
        if size < 9 or size > len(data) - pos or not data.startswith(b"EPSON IPL", pos):
            raise ValueError(f"zona IPL inválida {zone}")
        block = data[pos:pos + size]
        markers = [{"offset": pos + m.start(), "value": m[0].decode()}
                   for m in re.finditer(rb"EF[0-9]{2}[A-Z][0-9]", block)]
        ipl_info = parse_ipl_segments(block)
        croms = parse_crom_containers(block, pos, decompress=decompress_crom,
                                      incluir_datos=incluir_datos)
        blocks.append(dict(
            zone=zone,
            offset=pos,
            size=size,
            sha256=digest(block),
            ef_markers=markers,
            components=components(block, pos),
            ipl_header=ipl_info["ipl_header"],
            segments=ipl_info["segments"],
            crom_containers=croms,
        ))
        pos += size
    if pos != len(data):
        raise ValueError("hay bytes fuera de las zonas declaradas")
    return dict(rcx_sha256=digest(data), rcx_size=len(data),
                package=manifest["D"]["3"].strip('"'), blocks=blocks)
