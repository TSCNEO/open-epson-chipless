# Prueba empírica: imprimir con el chip tapado

Todo lo que hay en `docs/verificado.md` demuestra que el firmware parcheado se instala y que
declara los cuatro cartuchos al 100 %. Lo que **no** demuestra por sí solo es lo único que
importa de verdad: que la impresora imprime cuando el chip no puede leerse.

> **Resultado: superada el 2026-11-23.** Registro completo en `docs/verificado.md`: cartucho al
> 2 % con el chip tapado, trabajo aceptado y completado en 48 s, página impresa con las cuatro
> barras sólidas y sin avisos.

Esa prueba es física y hay que hacerla con la impresora delante. Este documento es el protocolo
completo, pensado para que la evidencia no deje lugar a dudas.

## Material

- Un cartucho cualquiera (vale el negro).
- Un trozo de cinta adhesiva transparente.
- La página de prueba: `python3 tools/pagina_prueba.py --out pagina-prueba.pdf --version <version> --hash <sha256 de la imagen flasheada>`
- Móvil para fotografiar, o cámara.

## Antes de tocar nada

1. Comprueba en la web de la impresora (`http://<ip>/PRESENTATION/HTML/TOP/PRTINFO.HTML`) que los
   cuatro niveles salen al 100 %. Anota la versión que declara.
2. Imprime **una** página con los chips puestos. Es el control: si esa página sale bien y la
   siguiente con el chip tapado también, la diferencia es solo la cinta.

## Tapar el chip

El chip es la pastilla con contactos dorados de la parte inferior del cartucho. La cinta va
**encima de los contactos**, no en la salida de tinta.

- Un solo trozo, que cubra todos los contactos de una vez. Si queda un contacto al aire, la
  impresora puede leer el chip a medias y el resultado no vale.
- No toques los contactos con los dedos: la grasa también impide el contacto y luego no se sabe
  qué ha fallado.
- Al sacar la cinta, hazlo despacio y sin dejar resto de adhesivo.

## La impresión

1. Mete el cartucho con la cinta puesta y cierra la tapa.
2. **Fotografía la pantalla de la impresora** en ese momento, antes de mandar nada. Lo que diga ahí
   es la mitad de la prueba: si avisa de que no reconoce el cartucho, sale en la foto.
3. Manda la página de prueba.
4. Fotografía la página **con la cinta todavía puesta** y el cartucho aún dentro.
5. Rellena a mano las casillas de la propia página antes de la foto final.

## Qué hay que capturar

| Prueba | Dónde se ve | Qué demuestra |
|---|---|---|
| Aviso del panel al insertar | Foto de la pantalla | Si la impresora detecta o no la ausencia de chip |
| Página impresa completa | Foto del papel | Que imprime de verdad, no que dice que imprimiría |
| Cuatro barras sólidas | La propia página | Que los cuatro canales tienen tinta y no hay uno seco |
| Nivel declarado tras imprimir | Web de la impresora | Que el nivel no baja de 100 % (consecuencia esperada del parche) |
| Versión declarada | Web de la impresora | Que es la imagen parcheada y no la de fábrica |
| Hash de la imagen | Cabecera de la página | Que el firmware que imprimió es el que está en el repo |

## Resultados posibles y qué significa cada uno

- **Imprime sin avisar.** Es el caso esperado: el parche neutraliza la lectura y la escritura del
  chip, y fuerza la presencia de los cuatro cartuchos. La prueba queda cerrada.
- **Avisa de que no reconoce el cartucho pero deja imprimir.** El parche cubre el camino principal
  y falta otro. Habría que revisar las 34 llamadas al agregador que lista `tools/descubrir.py` y
  localizar la que decide el aviso. Es un fallo localizable, no un callejón.
- **Avisa y bloquea la impresión.** Hay una comprobación que no pasa por los puntos ya parcheados,
  o el chequeo ocurre antes de que el hook de arranque esté activo. Se depura con la traza del
  panel y comparando con el firmware de fábrica.

En los tres casos el resultado es información útil: o cierra la prueba, o dice exactamente dónde
mirar.

## Si sale mal

No hay riesgo para la impresora: el chip tapado es un cartucho sin chip, y el modo recuperación del
firmware sigue intacto (no se ha tocado la zona de arranque ni la de recuperación). Para volver
atrás, quita la cinta y, si hace falta, vuelve a flashear el firmware de fábrica con
`docs/flasheo.md`.
