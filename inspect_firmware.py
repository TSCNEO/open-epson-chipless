# SPDX-License-Identifier: AGPL-3.0-only
"""Inspect EpsonNet RCX packages offline. All offsets refer to the uncompressed RCX."""

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

# Limit each in-memory layer, including uncompressed members.
LIMIT = 64 * 1024 * 1024
RCX = b"RCX\r\nSEIKO EPSON EpsonNet Form\r\n"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_rcx(path: Path) -> bytes:
    """Accept a distribution ZIP, an EFU (itself a ZIP), or the raw RCX."""
    if path.stat().st_size > LIMIT:
        raise ValueError("input exceeds 64 MiB")
    data = path.read_bytes()
    for _ in range(2):
        if data.startswith(RCX):
            return data
        with ZipFile(io.BytesIO(data)) as archive:
            members = [item for item in archive.infolist() if not item.is_dir()
                       and item.filename.lower().endswith((".efu", ".rcx"))]
            if len(members) != 1:
                raise ValueError("expected exactly one EFU or RCX member")
            if members[0].file_size > LIMIT:
                raise ValueError("archive member exceeds 64 MiB")
            data = archive.read(members[0])
    if not data.startswith(RCX):
        raise ValueError("unrecognized EpsonNet RCX header")
    return data


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


def inspect(data: bytes) -> dict:
    """Validate declared block lengths and account for every RCX byte."""
    end = data.find(b"\x0c", len(RCX), 65536)
    if end < 0:
        raise ValueError("missing RCX manifest terminator")
    manifest = configparser.ConfigParser(interpolation=None)
    manifest.read_string(data[len(RCX):end].decode("ascii"))
    zones = [s for s in manifest.sections() if s.startswith("Z_")]
    if not zones or zones != [f"Z_{i}" for i in range(1, len(zones) + 1)]:
        raise ValueError("unexpected IPL zone numbering")
    pos = end + 1
    blocks = []
    for zone in zones:
        size = int(manifest[zone]["5"].strip('"'))
        if size < 9 or size > len(data) - pos or not data.startswith(b"EPSON IPL", pos):
            raise ValueError(f"invalid IPL zone {zone}")
        block = data[pos:pos + size]
        markers = [{"offset": pos + m.start(), "value": m[0].decode()}
                   for m in re.finditer(rb"EF[0-9]{2}[A-Z][0-9]", block)]
        blocks.append(dict(zone=zone, offset=pos, size=size, sha256=digest(block),
                           ef_markers=markers, components=components(block, pos)))
        pos += size
    if pos != len(data):
        raise ValueError("unexpected bytes after the declared IPL zones")
    return dict(rcx_sha256=digest(data), rcx_size=len(data),
                package=manifest["D"]["3"].strip('"'), blocks=blocks)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package", type=Path, help="distribution ZIP, EFU, or RCX")
    args = parser.parse_args()
    try:
        result = inspect(load_rcx(args.package))
    except (OSError, ValueError, KeyError, configparser.Error, BadZipFile, RuntimeError,
            NotImplementedError, EOFError, zlib.error) as exc:
        parser.exit(1, f"Error reading {args.package}: {exc}\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
