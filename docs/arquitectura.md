# Arquitectura del firmware y de este parche

Todo lo que sigue se ha obtenido del firmware oficial `20.25.EF20J9` de la familia
`FWF731TL` (XP-243 / XP-245 / XP-247). No requiere hardware para comprobarlo.

## 1. El contenedor `.rcx`

Un `.efu` es un ZIP con un único miembro `.rcx`. El `.rcx`, a su vez:

1. **Manifiesto ASCII** terminado en `0x0C`, precedido de la cabecera
   `RCX\r\nSEIKO EPSON EpsonNet Form\r\n`. Campos relevantes:
   - `[D] 3="20.25.EF20J9.FY16"` — versión que lee el actualizador. Si no es mayor que la
     instalada, el actualizador se niega.
   - `[Z_1] 5="7483392"` y `[Z_2] 5="2109440"` — tamaños exactos de las dos zonas.
2. **Dos bloques `EPSON IPL` contiguos**, `Z_1` y `Z_2`.

## 2. Cabecera IPL y su integridad

Cada zona empieza por una cabecera:

| Offset | Contenido |
|---|---|
| `0x00` | firma `EPSON IPL` |
| `0x0E` | `<H` longitud de la tabla de descriptores (`0x6C` = 3 ranuras de `0x24`) |
| `0x10` | descriptor de `seg0`: `<HHIII` = type, sum16, bank, flash_offset, length |
| `0x34` | descriptor de `seg1`: igual, y en `0x44..0x58` el SHA-1 de `seg1` |
| `0x1000` | `seg0`, 8 192 B: cargador IPL. Idéntico entre versiones |
| `0x3000` | `seg1`, la imagen que se escribe en flash |

No hay firma asimétrica. La integridad son dos comprobaciones:

```
sum16 = (suma de todos los bytes de seg1) mod 65536        -> descriptor + 0x02
sha1  = SHA1( seg1 || SHA1( cabecera[0:0x0E] ) )          -> 0x44..0x58
```

Cualquier reempaquetado propio debe recalcular ambas. Eso hace que una imagen modificada sea
**aceptada por el cargador sin ninguna clave**.

## 3. El bloque comprimido `Z0_CROM3`

Dentro de `seg1` hay contenedores `CROM`. El que interesa empieza en el offset de flash
`0x210000` y tiene dos partes. Cada parte:

```
"CROM"            (solo antes de la parte 0)
FF D8  <u32 BE longitud del bloque>
FF C4  <u16 len>  3 tablas Huffman estilo JPEG DHT (ids 0xF0, 0xF1, 0xF2)
FF B1  <u16 len>  1 byte de versión + coded_bytes(u32) + num_items(u32) + flujo Huffman
FF B2  <u16 len>  lit_len(u32) + literales sin comprimir
```

El flujo Huffman emite tripletas `(control, offset_lo, offset_hi)`. Con `offset = 0` es un
literal de `control + 1` bytes; con `offset != 0` es una copia LZ77 de `control + 2` bytes desde
la ventana. **No es cifrado**: es un compresor. `tools/epson_rcx.py` lo decodifica sin claves.

## 4. Mapa de flash y de RAM

| Región | Flash (`seg1`) | Tamaño | Destino en RAM |
|---|---|---:|---|
| Bootloader (`BooSt`) | `0x000000`–`0x010000` | 64 KiB | no se copia |
| Prefijo / RTOS base | `0x010000`–`0x040000` | 192 KiB | XIP en VA `0x00010000` |
| `Z0_CROM1` | `0x040000`–`0x0D0000` | 576 KiB | `0x41DEB180` |
| `Z0_CROM2` (recursos) | `0x0D0000`–`0x210000` | 1,25 MiB | `0x41CA6A60` |
| `Z0_CROM3` (cartuchos) | `0x210000`–`0x24AA9D` | 240 KiB comprimidos | `0x41C2D000` |
| Tabla MMU L1 | `0x25B000` | 21 KiB | — |
| uImage Linux | `0x260400` | 1,06 MiB | núcleo ARM |
| SquashFS raíz | `0x370000` | 910 KiB | sistema raíz |
| SquashFS red | `0x470000` | 2,2 MiB | `nwsoc`, Wi-Fi |
| `Z_2`: `Z1_CROM0` | banco 1, desde `0x10` | 1,7 MiB comprimidos | `0x41E46ADC` |

El bloque `Z0_CROM3` se descomprime a `0x41C2D000`. Ahí viven las rutinas que hablan con el chip
del cartucho.

## 5. Secuencia de arranque

1. El prefijo copia 1 MiB de flash a `0x43F00000` y remapea VA `0x00000000` a esa dirección.
2. Descomprime los cuatro bloques CROM a sus bases de RAM.
3. Limpia e invalida cachés.
4. Salta al trampolín `VA 0x0001633C`, que es `ldr pc, [pc, #-4]`: lee el puntero guardado en
   `0x00016340` y salta allí. En el firmware de fábrica ese puntero vale `0x41EAD6E8`, un punto
   de entrada vacío: a esa altura ya está todo descomprimido y la región `0x41C2D000` es
   escribible y ejecutable.

## 6. El parche

Se aprovechan **57 320 bytes libres en `0xFF`** al final del prefijo (`0x00032018` en adelante):

1. Rutina de 196 B en `VA 0x00032100`, código propio:
   guarda `{r0-r4, lr}`, recorre una tabla de 15 pares `(dirección, opcode)`, escribe cada palabra
   en `0x41C2D000+`, llama a `0x00015840` (clean + invalidate de D-cache), invalida I-cache, BTB y
   hace prefetch flush (`mcr p15, 0, r0, c7, c5, 0/6/4`), restaura registros y salta a
   `0x41EAD6E8`.
2. Se cambia **una sola palabra** en `0x00016340`: de `0x41EAD6E8` a `0x00032100`.

En cada arranque, el parche se reaplica. Nada queda escrito en el bloque comprimido.

## 7. Por qué parchear en RAM y no recomprimir

Recomprimir exige un compresor CROM real: `Z0_CROM3` ocupa 498 272 B descomprimidos y el hueco
físico antes de la tabla MMU es de solo 307 200 B entre ambas partes. Un compresor de solo
literales no cabe; haría falta LZ77 con ventana de 65 535 B y Huffman canónica, y cualquier
error de tasa de compresión rompe el arranque.

El parche en RAM evita ese riesgo entero: no toca ni un byte del bloque comprimido, y la
verificación puede demostrar que todos los contenedores conservan su SHA-256 original.

## 8. Qué queda fuera

- `Z_2` no se toca (se verifica byte a byte).
- El bootloader no se incluye nunca: así el modo de recuperación USB sobrevive a una imagen mala.
- Kernel, SquashFS y recursos no se tocan.

## 9. Límites conocidos

Los parches anulan las rutinas de comprobación y el agregador de estado, pero el agregador tiene
34 llamadas en el bloque y aquí solo se neutralizan las 9 que activan bloqueos o avisos. Las
restantes podrían disparar mensajes secundarios en calibración o limpieza. En la unidad probada
no aparecieron, pero el firmware no se ha ejercitado a fondo (ciclos largos, cambio de cartucho
en caliente, limpieza profunda). Ver [verificado.md](verificado.md).
