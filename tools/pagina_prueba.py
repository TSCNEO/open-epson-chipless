#!/usr/bin/env python3
"""Genera una pagina de prueba imprimible para verificar la impresion sin chip.

La pagina lleva lo que hace falta para que la foto sea prueba:
  - los cuatro colores en barras solidas (si falta uno, se ve)
  - modelo, version de firmware y hash de la imagen flasheada
  - casillas para marcar a mano si el chip estaba cubierto y con que

No usa dependencias: escribe el PDF a mano.

Uso:
    python3 tools/pagina_prueba.py --out pagina-prueba.pdf \
        --modelo "XP-247" --version 20.25.EF20J9 --hash bc25ac2e...
"""

from __future__ import annotations

import argparse
import datetime as dt
from pathlib import Path

ANCHO, ALTO = 595, 842  # A4 en puntos


def _escapar(texto: str) -> str:
    return texto.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")


class Pagina:
    """Mini constructor de PDF: solo texto y rectangulos."""

    def __init__(self) -> None:
        self.ops: list[str] = []

    def texto(self, x: float, y: float, txt: str, fuente: str = "F1", tam: float = 12,
              gris: float = 0.0) -> None:
        self.ops.append(
            f"BT /{fuente} {tam} Tf {gris} {gris} {gris} rg "
            f"1 0 0 1 {x:.1f} {y:.1f} Tm ({_escapar(txt)}) Tj ET"
        )

    def rect(self, x: float, y: float, w: float, h: float, rgb: tuple[float, float, float]) -> None:
        r, g, b = rgb
        self.ops.append(f"{r:.3f} {g:.3f} {b:.3f} rg {x:.1f} {y:.1f} {w:.1f} {h:.1f} re f")

    def marco(self, x: float, y: float, w: float, h: float, gris: float = 0.0) -> None:
        self.ops.append(f"{gris:.3f} {gris:.3f} {gris:.3f} RG 0.8 w {x:.1f} {y:.1f} {w:.1f} {h:.1f} re S")

    def linea(self, x1: float, y1: float, x2: float, y2: float, gris: float = 0.0) -> None:
        self.ops.append(f"{gris:.3f} {gris:.3f} {gris:.3f} RG 0.6 w {x1:.1f} {y1:.1f} m {x2:.1f} {y2:.1f} l S")


def construir_pdf(pag: Pagina, titulo: str, meta: list[tuple[str, str]],
                  hash_imagen: str, fecha: str) -> bytes:
    contenido = "\n".join(pag.ops).encode("latin-1", "replace")

    objetos: list[bytes] = []
    objetos.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    objetos.append(b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>")
    objetos.append(
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
        b"/Resources << /Font << /F1 5 0 R /F2 6 0 R >> >> /Contents 4 0 R >>"
    )
    objetos.append(
        b"<< /Length " + str(len(contenido)).encode() + b" >>\nstream\n" + contenido + b"\nendstream"
    )
    objetos.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>")
    objetos.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Courier /Encoding /WinAnsiEncoding >>")

    salida = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    posiciones: list[int] = []
    for i, obj in enumerate(objetos, start=1):
        posiciones.append(len(salida))
        salida += f"{i} 0 obj\n".encode() + obj + b"\nendobj\n"

    inicio_xref = len(salida)
    salida += f"xref\n0 {len(objetos) + 1}\n".encode()
    salida += b"0000000000 65535 f \n"
    for pos in posiciones:
        salida += f"{pos:010d} 00000 n \n".encode()
    salida += (
        f"trailer\n<< /Size {len(objetos) + 1} /Root 1 0 R >>\n"
        f"startxref\n{inicio_xref}\n%%EOF\n"
    ).encode()
    return bytes(salida)


def principal() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default="pagina-prueba.pdf", help="fichero PDF de salida")
    ap.add_argument("--modelo", default="XP-243 / 245 / 247")
    ap.add_argument("--version", default="(sin declarar)")
    ap.add_argument("--hash", dest="hash_imagen", default="(sin declarar)")
    ap.add_argument("--fecha", default="")
    args = ap.parse_args()

    fecha = args.fecha or dt.date.today().isoformat()
    pag = Pagina()

    pag.texto(50, 790, "PRINTER WITHOUT CARTRIDGE CHIP", "F1", 22)
    pag.texto(50, 768, "Test page generated from open firmware - no chips, no keys", "F1", 11, 0.35)
    pag.linea(50, 758, 545, 758, 0.6)

    y = 730
    for clave, valor in (("Model", args.modelo), ("Firmware version", args.version),
                         ("Date", fecha)):
        pag.texto(50, y, f"{clave}:", "F1", 11, 0.45)
        pag.texto(170, y, valor, "F2", 11)
        y -= 18

    pag.texto(50, y, "Flashed image sha256:", "F1", 11, 0.45)
    resto = args.hash_imagen
    yy = y - 16
    while resto:
        pag.texto(50, yy, resto[:64], "F2", 9.5)
        resto = resto[64:]
        yy -= 13

    # Barras de color: si un canal no imprime, se ve a simple vista.
    pag.texto(50, yy - 14, "Colour check (all four must be solid):", "F1", 11, 0.45)
    barras = [((0.05, 0.05, 0.05), "K"), ((0.98, 0.85, 0.05), "Y"),
              ((0.85, 0.05, 0.45), "M"), ((0.05, 0.45, 0.9), "C")]
    x = 50
    alto_barra = 70
    y_barra = yy - 30 - alto_barra
    for rgb, nombre in barras:
        pag.rect(x, y_barra, 105, alto_barra, rgb)
        pag.texto(x + 46, y_barra - 14, nombre, "F1", 12)
        x += 123

    # Casillas para rellenar a mano: esto es lo que convierte la foto en prueba.
    y_caja = y_barra - 60
    pag.texto(50, y_caja, "Fill in by hand before photographing the result:", "F1", 11, 0.45)
    marcas = [
        ("Cartridge chip covered (tape)", "YES  /  NO"),
        ("Printer did not complain about the cartridge", "YES  /  NO"),
        ("Ink level reported by the printer web UI", "______ %"),
        ("Pages printed before this one", "______"),
    ]
    y_caja -= 24
    for etiqueta, valor in marcas:
        pag.marco(50, y_caja - 3, 11, 11, 0.2)
        pag.texto(70, y_caja, etiqueta, "F1", 10.5)
        pag.texto(400, y_caja, valor, "F2", 10)
        y_caja -= 24

    pag.linea(50, y_caja - 10, 545, y_caja - 10, 0.75)
    pag.texto(50, y_caja - 30, "Signature / date:", "F1", 10, 0.45)
    pag.linea(160, y_caja - 32, 380, y_caja - 32, 0.4)

    datos = construir_pdf(pag, "Test page", [], args.hash_imagen, fecha)
    ruta = Path(args.out)
    ruta.write_bytes(datos)
    print(f"escrito {ruta} ({len(datos)} B)")
    return 0


if __name__ == "__main__":
    raise SystemExit(principal())
