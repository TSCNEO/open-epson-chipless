# Evidencia: qué se ha probado y qué no

## Entrada

Firmware oficial de Epson para XP-243/245/247, versión `20.25.EF20J9.FY16`, obtenido del sitio de
soporte de Epson:

```
EFU   sha256  3e9ae697fadece00618217da9737866ff8f0a1c38030edd4ac8eb24848ab4074   7 536 294 B
RCX   sha256  fec90a9fdfd0374dd1b2b0235a669b4bc04d7aec446ddfe4280fb17566e1220b   9 593 123 B
```

Ambas zonas IPL con `sum16` y `SHA-1` válidos antes de tocar nada.

## Imagen construida

Con las opciones por defecto (sin bootloader, versión declarada `20.25.EF99Z9.FY16`):

```
RCX   sha256  bc25ac2e0b77a4112f04d86a27f66420c1d0036923c44b6e8087b0472de476f7   9 527 587 B
```

Comprobaciones que pasa esta imagen:

| Comprobación | Resultado |
|---|---|
| `sum16` y `SHA-1` de ambas zonas | correctos |
| `Z_2` byte a byte frente al original | idéntica (2 109 440 B) |
| Partes CROM descomprimidas (5) | SHA-256 idénticos al original |
| uImage y los dos SquashFS | SHA-256 idénticos al original |
| Diff dentro del prefijo | 4 B (puntero) + 196 B (hook), nada más |
| Bloque descomprimido `Z0_CROM3.p0` | `b2ad8f8c…eeb14`, 498 272 B, opcodes originales confirmados |

La equivalencia del constructor está probada de forma fuerte: dos implementaciones independientes
del mismo parche producen **el mismo SHA-256 byte a byte**, no solo el mismo tamaño.

## Prueba en hardware

Unidad: Epson XP-247 (identificada por SNMP/ENPC como `XP-243 245 247 Series`), con
`20.25.EF20J9` de fábrica.

- **Transporte:** red, con el actualizador oficial de Epson (`/NU /SU:I:<ip>`).
- **Progreso observado:** `Update,Done,0` (50) → `WaitUpdating,Done,0` (66) →
  `Reboot,Start,0` (83), donde se detiene porque espera leer `EF99Z9`.
- **Arranque:** correcto. Web de la impresora responde 200 y reporta `20.25.EF20J9`.
- **ENPC (UDP 3289):** responde y devuelve el modelo correcto.
- **Indicadores de tinta** (altura de barra en la web, 50 = lleno):

| | Antes | Después |
|---|---:|---:|
| Negro | 37 | 50 |
| Amarillo | 50 | 50 |
| Magenta | 48 | 50 |
| Cian | 42 | 50 |

Los cuatro pasan a lleno, que es precisamente el comportamiento esperado: la impresora ya no
consulta el chip.

### Estado en vivo (2026-11-23)

Lectura directa de la impresora, sin reiniciar ni flashear nada:

```
GET http://<ip-de-la-impresora>/PRESENTATION/HTML/TOP/INDEX.HTML
  Device Name: EPSONRM4EVER
  Current Version:20.25.EF20J9
  XP-243 245 247 Series
GET http://<ip-de-la-impresora>/PRESENTATION/HTML/TOP/PRTINFO.HTML
  Ink_K height=50   Ink_Y height=50   Ink_M height=50   Ink_C height=50   (50 = lleno)
  Connection Status: Wi-Fi-72Mbps   Signal Strength: Excellent
```

Sigue en la versión parcheada y con los cuatro niveles al 100 %. Nota: hasta ahora **no se ha
impreso nada** con esta unidad, así que el 100 % es el valor que declara el firmware, no el
resultado de haber gastado tinta. La prueba que separa una cosa de la otra es
`docs/prueba-empirica.md`.

## Prueba empírica: impresión con el chip tapado (2026-11-23)

La prueba que separa "el firmware declara que hay tinta" de "la impresora imprime sin chip".

**Condiciones:** cartucho de color que la impresora tenía contado al **2 %**, con los contactos del
chip cubiertos con cinta adhesiva. Imagen flasheada: build `bc25ac2e…476f7` (`20.25.EF20J9`).

```
GET /PRESENTATION/HTML/TOP/PRTINFO.HTML    antes:     K=50  Y=50  M=50  C=50
lp -d EpsonXP247 -o media=A4 pagina-prueba.pdf
  request id EpsonXP247-14, enviado 17:25:46 CET
lpstat -W completed                         17:26:52 CET  Alerts: job-completed-successfully
GET /PRESENTATION/HTML/TOP/PRTINFO.HTML    despues:   K=50  Y=50  M=50  C=50
```

**Resultado:** la impresora aceptó el trabajo y lo completó en 48 segundos. La página salió impresa
con las cuatro barras sólidas —amarillo incluido— y sin ningún aviso de cartucho no reconocido, ni
en el panel ni en la web. Después de imprimir, los cuatro niveles siguen declarando 100 %.

**Qué cierra esto:** el parche no se limita a que la impresora deje de consultar el chip; imprime
con el chip físicamente inaccesible, y lo hace con el canal cuyo contador estaba al 2 %.

**Qué no cierra:** que el nivel declarado no baje sigue siendo el comportamiento esperado (el
contador está neutralizado), así que la impresora no avisará cuando el cartucho se agote de verdad.
Y sigue probado en una sola versión y un solo modelo: la portabilidad está demostrada como
localización de puntos, no como flasheo en otro hardware.

## Prueba de portabilidad en otra familia

Para comprobar que el método no depende de estas direcciones, se pasó la herramienta por un
firmware oficial de **otro modelo**: `FWG016TL`, versión `1E.26.MJ01O7.FY16` (XP-342/345), paquete
de recuperación publicado por Epson. Mismo contenedor, código distinto.

```
EFU   sha256 1416eda96307fd1c2f05dc6a5871458a163e47d1e2be250aa067d56637366e2d   9 706 502 B
RCX   sha256 f4b774262f6b16170190c364e08cec1825517a089fb84a7a45404259eb909f3c  15 884 579 B
```

`tools/descubrir.py` encontró, sin tocar nada, el mismo subsistema:

| Elemento | XP-247 (`FWF731TL`) | XP-342/345 (`FWG016TL`) |
|---|---|---|
| Envoltorio de lectura | +0x107C | +0x1094 |
| Envoltorio de escritura | +0x1120 | +0x1138 |
| Función de presencia | +0x2C80 | +0x2CA0 |
| Salida a invertir | +0x2D28 | +0x2D48 |
| Agregador | +0x2D34 | +0x2D54 |
| Llamadas al agregador | 34 | 34 |

Desplazamiento uniforme de +0x18 y +0x20: es **el mismo código**, compilado en otra versión. La
forma de las funciones coincide instrucción a instrucción (`push {r4, r5, lr}` + `sub sp, sp,
#0xc` en la presencia; `mov rN, #3` como contador de reintentos en los dos envoltorios;
`ldr r0, [pc, #-0x358]` al principio del agregador).

El pipeline completo también funcionó: borrador de spec → construcción (15 819 043 B) →
verificación con `"correcto": true` y todos los contenedores intactos.

**Qué no prueba esta prueba:**

- No se ha flasheado esa imagen: no hay hardware XP-342/345 aquí.
- La base de carga del bloque en esa familia no está confirmada (`0x45B26000` es una hipótesis
  deducida del clúster de direcciones de los veneers), así que las direcciones absolutas del
  borrador son provisionales; los *offsets* sí son correctos.
- El enganche de arranque elegido para esa imagen es arbitrario entre los 63 candidatos, y la
  rutina de flush se asumió igual. Sin confirmación en hardware, esa imagen no es flasheable.

Lo que sí demuestra: los puntos se localizan por estructura del código, no por una tabla, y el
mismo razonamiento funciona en un binario que nunca habíamos visto.

## Lo que NO se ha validado

Aquí no se vende humo: esto es lo que queda abierto.

1. **Tiradas largas.** No se ha imprimido de forma sostenida ni con cartuchos realmente secos.
2. **Cambio de cartucho en caliente** con el firmware parcheado.
3. **Limpieza profunda y calibraciones**, donde podrían activarse llamadas del agregador que no
   se han neutralizado (9 de 34).
4. **Ciclos de apagado/encendido prolongados.** El parche se reaplica en cada arranque, pero solo
   se ha comprobado en reinicios puntuales.
5. **Recuperación USB real.** El modo IPL existe y el bootloader no se toca, pero no se ha
   ejercitado una recuperación completa desde un arranque roto.
6. **Otras unidades y otras versiones.** Todo lo anterior es una sola impresora y una sola
   versión de firmware.

Si pruebas alguno de estos puntos, abre un issue con la versión exacta, el hash de la imagen y el
resultado observable. Ese es el dato que falta.
