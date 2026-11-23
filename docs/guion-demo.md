# Guion de demo (60–75 s)

Para grabar con el móvil, sin edición complicada. Objetivo: que quien lo vea entienda en 10
segundos que la impresora imprime con el chip tapado, y en 60 que el método está publicado y puede
repetirlo.

Regla de oro: **la cinta se pone en pantalla**. Si el vídeo dice que hay cinta pero no se ve
ponerla, no vale. Mismo criterio con el hash y con la versión.

## Plano a plano

**0–4 s · El gancho.** Primer plano de la impresora imprimiendo. Voz en off en seco:
> "Esta impresora tiene chip en los cartuchos. Le he tapado el chip con cinta. Y sigue imprimiendo."

Sobreimpresión: `8 años · 1 trozo de cinta`.

**4–12 s · El problema.** Gráfico simple: cartucho → chip → contador → "cartucho no reconocido".
> "El chip es un contador. Cuando la impresora decide que está vacío, para, aunque quede tinta.
> Y el firmware está cerrado a propósito."

**12–22 s · Lo que se hizo, sin humo.** Pantalla del repo: `inspeccionar.py`, `descubrir.py`,
`construir.py`.
> "Cogí el firmware oficial de Epson, el de su propia web. Localicé el subsistema que habla con el
> chip: quince puntos de parche. Construí mi propia imagen. Sin claves de pago y sin una línea de
> código de nadie más."

**22–32 s · El flasheo.** El log del actualizador: `50 → 66 → 83`.
> "Flasheada por WiFi con el actualizador oficial. Tres minutos."

**32–48 s · La prueba.** Aquí van los tres planos que importan, en este orden:
1. La web de la impresora: `Current Version:20.25.EF20J9` y las cuatro barras llenas.
2. **La cinta sobre los contactos del chip**, plano corto y claro.
3. La página de prueba saliendo impresa, con las barras de color y el hash visible.
> "Misma impresora, versión parcheada, cuatro colores llenos. Chip tapado. Y sale la página: con su
> hash, que coincide con el que está en el repositorio."

**48–60 s · El cierre.**
> "El método está publicado: las herramientas, cómo se localizan los puntos en cualquier versión y
> cómo se comprueba que la imagen es la misma. Si tienes una Epson de esta familia, puedes hacerlo
> tú. Y si tienes otro modelo, la herramienta te dice por dónde empezar."

CTA: *"Repo en el primer comentario. Cuéntame tu modelo."*

## Texto para los subtítulos (inglés, para el repo y para redes)

```
0:00  This printer requires a chip in every cartridge.
0:03  I covered the chip with tape. It still prints.
0:12  The chip is just a counter with a lock on the firmware.
0:15  I took Epson's own official firmware package.
0:19  Found the subsystem that talks to the chip: 15 patch points.
0:23  Built my own image. No paid keys. No third-party code.
0:28  Flashed over Wi-Fi with Epson's own updater.
0:34  Same printer, patched version, all four colours full.
0:40  Chip covered. Page comes out, hash matches the repo.
0:50  The whole method is published. Take your own model further.
```

## Qué NO poner en el vídeo

- Ni el nombre de un vendedor de firmware ni de un activador. No se menciona, no se compara.
- Ni "gratis para siempre" ni "tinta infinita": el nivel se queda fijo, y eso hay que decirlo.
- Ni planos de la impresora con la tapa abierta y prisa. Un plano mal hecho aquí parece un montaje.

## Material que hay que tener listo antes de grabar

- Página de prueba generada:
  `python3 tools/pagina_prueba.py --out pagina-prueba.pdf --modelo "Epson XP-247" --version 20.25.EF20J9 --hash <sha256>`
- La web de la impresora abierta en el móvil, para que el plano de la versión sea real y no una
  captura antigua.
- Cinta, cartucho y un trapo. Y la impresora con papel.
