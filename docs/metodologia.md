# Metodología: cómo se localizan los puntos de parche

Este documento es el que permite extender el proyecto a otra versión u otro modelo. No lista
direcciones: enseña el procedimiento con el que se obtuvieron. Las direcciones sin método caducan
en la siguiente compilación del fabricante; el método no.

Todo se hace sobre el firmware oficial, sin hardware y sin herramientas propietarias.

## Atajo: `tools/descubrir.py`

El procedimiento de este documento está automatizado. Sobre un firmware oficial cualquiera:

```sh
python3 tools/descubrir.py FW.efu                                     # informe
python3 tools/descubrir.py FW.efu --trampolin <va> --flush <va> \
        --emitir-spec data/patches/<familia>/<version>.json           # borrador de spec
```

Encuentra solo, por huellas del binario y no por tabla:

| Qué busca | Cómo lo reconoce |
|---|---|
| Envoltorio de lectura del chip | prólogo con `lr` + contador de reintentos 3 + código de error `0x2A` |
| Envoltorio de escritura | hermano con el mismo prólogo en los 1 KiB siguientes |
| Función de presencia | pide los registros `0x67` y `0x68`, los combina con desplazamiento `#2` y compara contra `1` |
| Punto a parchear de la presencia | el `mov rD, #0` de la salida falsa |
| Agregador | la función que llama a la presencia y recorre los canales con `cmp #4` |
| Llamadas al agregador | todas las `bl` a esa dirección, con su contexto |
| Hueco libre | tirada de `0xFF` más larga del prefijo, alineada a 256 |
| Enganches de arranque | `ldr pc, [pc, #-4]` cuyo puntero cae en RAM |

Validación de la herramienta: sobre `EF20J9` redescubre los 5 puntos centrales de la tabla que se
probó en hardware, con el mismo opcode original y el mismo opcode nuevo, el mismo hueco
(`0x00032100`), el mismo destino de arranque (`0x41EAD6E8`) y las mismas 34 llamadas al agregador.

**Lo que no adivina, y por qué:**

- **El enganche de arranque.** Hay 61 veneers `ldr pc, [pc, #-4]` idénticos en estructura; el
  válido es el que realmente se ejecuta al arrancar, y eso no se deduce del binario sin trazar el
  arranque. Se pasa con `--trampolin` y se confirma en hardware (si los indicadores de tinta
  siguen midiendo, el hook no se ejecutó).
- **La función de limpieza de D-cache.** La herramienta lista los candidatos (primitiva `mcr` y
  envoltorios), pero elegir la firma correcta afecta a la estabilidad: se pasa con `--flush`.
- **Qué llamadas al agregador neutralizar.** Lista las 34 con contexto; la selección es criterio
  humano y hay que justificarla.

Lo demás — que es la parte difícil — sale automático.

---

## Paso 0. Antes de buscar nada: entender el arranque

Un parche en RAM solo funciona si sabes **cuándo** se ejecuta el código que quieres tocar y
**desde dónde** se ejecuta. Dos preguntas:

1. ¿Qué regiones están comprimidas y a qué dirección se expanden?
2. ¿Existe un punto de entrada en el que ya todo esté expandido, la RAM sea escribible y todavía
   no se haya ejecutado la lógica de negocio?

Se contesta leyendo la cabecera IPL y los descriptores de sus segmentos (`docs/arquitectura.md`,
secciones 2 y 4). En esta familia la respuesta es un trampolín de dos instrucciones al final del
prefijo:

```
0x0001633C   E51FF004   ldr pc, [pc, #-4]
0x00016340   <puntero>  -> destino
```

**Cómo encontrarlo sin conocerlo de antemano:** busca el patrón `04 F0 1F E5` (little endian) en
la parte de flash que *no* está comprimida. Un `ldr pc,[pc,#-4]` es raro en código normal: casi
siempre es un salto por tabla o un punto de enganche. Confirma que el puntero que le sigue cae
dentro de una región que el arranque descomprime, y ya tienes el sitio.

## Paso 1. Buscar hueco físico en el prefijo

Necesitas espacio para tu rutina que no se sobrescriba, y que esté en una zona ejecutable.

- Recorre el prefijo (región XIP) buscando la tirada de `0xFF` más larga.
- Descarta cualquier zona que sea referenciada por un puntero: comprueba que la dirección de
  inicio no aparece como palabra little endian en ninguna parte del prefijo ni en las cabeceras.
- En `EF20J9` hay 57 320 B libres desde `0x00032018`; se eligen `0x00032100` (alineado a 16 y con
  margen por delante) y caben 196 B de rutina más 1 800 B de holgura.

## Paso 2. Descomprimir el bloque que contiene la lógica

Los contenedores `CROM` están dentro de `seg1`. Para cada uno:

1. Localiza la firma `CROM` y el bloque `FF D8` que da su longitud.
2. Decodifica las tablas Huffman (`FF C4`, tres tablas estilo JPEG DHT con ids `0xF0/0xF1/0xF2`).
3. Decodifica el flujo Huffman (`FF B1`): tripletas que producen literales o copias LZ77.
4. Concatena los literales de `FF B2` en su posición correspondiente.

`tools/epson_rcx.py` hace exactamente eso en `_decompress_crom_part`. Compruébalo siempre con el
SHA-256 del bloque descomprimido: si cambia, estás mirando otro binario y cualquier dirección de
una tabla anterior es veneno.

## Paso 3. Localizar el subsistema de cartuchos sin símbolos

Aquí no hay nombres. Se navega con pistas que el compilador deja y que son estables entre
versiones:

**a) El código de error.** Cuando una operación contra el chip falla, el firmware registra un
código. En esta familia es `0x2A`, y aparece en la ruta de fallo de los dos envoltorios de acceso.
Busca `mov rX, #0x2A` seguido de un `str` a una variable global: eso te da la función de acceso y,
por vecindad, su hermana (lectura y escritura suelen estar contiguas, con la misma estructura).

**b) El contador de reintentos.** Los envoltorios reintentan un número pequeño de veces (3). Ese
`cmp rX, #3` con un bucle que decrementa es otra firma reconocible.

**c) Los bits de "presente".** El firmware lee dos registros del chip y los combina:

```
presente = ((reg_67 << 2) | reg_68) == 1
```

Buscando las constantes `0x67` y `0x68` juntas y un desplazamiento a la izquierda de 2 aparecen
la función que calcula ese valor y su salida.

**d) El agregador.** Es la función que llama al cálculo anterior **una vez por canal** y devuelve
verdadero solo si todos responden verdadero. Encuéntrala contando referencias: es la función que
recibe más `bl` desde sitios distintos del bloque. En `EF20J9` tiene 34 llamadas.

## Paso 4. Elegir qué parchear (y qué no)

Regla: **parchea la decisión, no el sensor.**

| Estrategia | Efecto | Riesgo |
|---|---|---|
| Anular la lectura del chip | Ninguna lectura tiene éxito | Rutas que distinguen "error" de "ausente" quedan inconsistentes |
| Forzar el valor "presente" en la comparación | Todas las consultas responden presente | Es el punto que usa todo el bloque: mínimo impacto |
| Anular las llamadas al agregador | Esas llamadas concretas dejan de bloquear | Solo cubres las que parcheas |

Se combinan las tres, pero con criterio:

- Envoltorios de lectura y escritura: devolver éxito inmediato (`mov r0,#0` + `bx lr`). Así ninguna
  ruta de error se dispara.
- El cálculo de "presente": forzar el retorno a `1`. Es un solo punto y afecta a todos los canales.
- Las llamadas al agregador que disparan bloqueo o aviso: sustituir el `bl` por `mov r0,#0`. **No
  las sustituyas todas a ciegas**: si una de esas llamadas gobierna otra cosa (por ejemplo, una
  calibración), romperla introduce fallos difíciles de diagnosticar. En este proyecto se
  neutralizan 9 de 34 y se documenta el resto como no verificado.

## Paso 5. Verificar cada opcode antes de escribir

Para cada dirección candidata:

1. Decodifica la instrucción y compruébala a mano: ¿es un prólogo de función, un `bl`, un `mov`?
   Si esperas un `bl` y hay un `strb`, has llegado 4 bytes tarde.
2. Comprueba el contexto: las 2 instrucciones anteriores y las 2 siguientes deben tener sentido
   con lo que crees que hace la función.
3. Guarda el opcode **original** en la tabla de parches. No como documentación: como control. El
   constructor lo compara antes de escribir y aborta si no coincide.

Ese control es lo que evita el fallo clásico: reutilizar una tabla de otra compilación. Entre dos
versiones de esta misma familia, insertar un literal desplaza el código y tres de los quince
puntos quedan 4 bytes más adelante; parchear ahí corrompe instrucciones vecinas y la impresora no
arranca.

## Paso 6. Diseñar la rutina de enganche

Requisitos que debe cumplir, en este orden:

1. **Preservar registros.** Guarda y restaura todo lo que toques, incluido `lr`. El destino
   original espera el estado de la CPU tal cual.
2. **Escribir las palabras en RAM, no en flash.** El bloque ya está descomprimido en este punto.
3. **Vaciar cachés.** Los procesadores ARM926 con cachés Harvard necesitan, tras escribir código:
   - `mcr p15,0,r0,c7,c10,0` — clean + invalidate D-cache
   - `mcr p15,0,r0,c7,c5,0` — invalidate I-cache
   - `mcr p15,0,r0,c7,c5,6` — flush BTB
   - `mcr p15,0,r0,c7,c5,4` — prefetch flush
   Sin esto, la CPU ejecuta instrucciones viejas de la caché y el parche "no hace nada" de forma
   intermitente, que es el peor fallo posible de diagnosticar.
4. **Saltar al destino original**, no hacer un `bx lr`: el trampolín sustituye un salto, no una
   llamada.

La tabla de pares `(dirección, opcode)` permite añadir o quitar parches sin recompilar la rutina:
solo cambia el JSON.

## Paso 7. Validar sin hardware

Tres comprobaciones, en este orden, y todas automáticas:

1. **Integridad:** recalcular `sum16` y el SHA-1 IPL. Sin esto el cargador rechaza la imagen.
2. **Diff acotado:** comparar el prefijo byte a byte contra el original. Solo pueden cambiar el
   puntero del trampolín y tu rutina. Cualquier otro byte es un error de offsets.
3. **Contenedores intactos:** `Z_2`, todos los `CROM` descomprimidos, el kernel y los SquashFS
   deben conservar su SHA-256. Si el diseño es bueno, no has tocado ninguno.

`tools/verificar.py` implementa las tres. Si publicas una versión nueva, el hash de tu build debe
ser reproducible: dos ejecuciones en máquinas distintas tienen que dar el mismo SHA-256.

## Cómo saber si el parche está activo

Sin abrir la impresora: los indicadores de tinta de la web de la impresora pasan a marcar lleno de
forma permanente y dejan de responder a los cartuchos. Si siguen midiendo, el hook no se ejecutó:
revisa el puntero del trampolín y que la rutina esté en la dirección que crees.

## Errores que ya hemos cometido

- **Confundir coordenadas.** El bloque de datos tiene una cabecera de 8 KiB delante; un offset
  válido en coordenadas de flash no lo es en coordenadas del bloque, y al revés. Este error
  concreto costó una tanda entera de depuración: el constructor leía el trampolín 8 KiB antes de
  donde estaba.
- **Suponer opcodes.** Rellenar la tabla con valores "razonables" (`0xEB000000`) hace que la
  validación pase por casualidad y el parche no haga nada. Los opcodes se extraen del binario.
- **Recomprimir el bloque.** Se intentó por la vía "elegante" y no cabe: 498 272 B descomprimidos
  contra 307 200 B de hueco físico. El parche en RAM no es un atajo, es la única opción viable sin
  un compresor LZ77 exacto.
