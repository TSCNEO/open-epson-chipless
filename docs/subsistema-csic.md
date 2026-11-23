# El subsistema de cartuchos y los 15 puntos de parche

Todas las direcciones son de RAM en la imagen **descomprimida** de `Z0_CROM3` para
`20.25.EF20J9`, cuya base es `0x41C2D000`. El offset dentro del bloque es `VA - 0x41C2D000`.

`SHA-256` del bloque descomprimido, como control de que estás mirando el mismo binario:

```
b2ad8f8c7152fc8ca02c87bfaf2be5dd24f4ec914dfcdbffd404912f9f9eeb14   (498 272 bytes)
```

## Qué revisa la impresora, en orden

Según el bloque descomprimido, la comprobación es **de presencia y de lectura de contadores**. No
hay firma ni intercambio de desafío-respuesta en estas rutinas: no hay criptografía que falsificar,
solo una respuesta que dar.

1. **Acceso al chip (CSIC).** Dos envoltorios, lectura y escritura. Cada uno reintenta hasta tres
   veces; si no obtiene respuesta, registra el error `0x2A` y devuelve fallo.
2. **Bits de presencia.** Se leen dos registros (`0x67` y `0x68`) y se combinan:
   `presente = ((r67 << 2) | r68) == 1`. Si el chip no existe, esto da `0`.
3. **Agregador.** Recorre los canales y devuelve "todo presente" solo si cada uno respondió `1`.
   Tiene 34 llamadas: algunas bloquean la impresión, otras solo generan avisos.
4. **Consecuencia.** Sin chip, el agregador devuelve `0` y los flujos que dependen de él bloquean o
   avisan. Los niveles de tinta salen de la lectura del chip: sin chip no hay medida, y por eso el
   parche deja los indicadores en lleno fijo.

El parche actúa en los tres primeros niveles a la vez, que es lo que hace que no quede ninguna
ruta que pueda volver a preguntar.

## Grupos funcionales

1. **Envoltorios de acceso al chip CSIC** — `0x41C2E07C` (lectura) y `0x41C2E120` (escritura).
   Reintentan hasta tres veces; si fallan registran el error `0x2A` y devuelven `1`.
2. **Comprobación de los registros `0x67` / `0x68`** — `0x41C2FC80`, con salida en `0x41C2FD28`,
   que calcula `(r67 << 2) | r68` y devuelve `1` solo si el resultado es `1` (cartucho presente).
3. **Agregador de estado** — `0x41C2FD34`. Recorre los canales llamando al punto 2 y devuelve
   `1` cuando todos responden `1`. **Tiene 34 llamadas** dentro del bloque; varias son las que
   disparan bloqueo o aviso.
4. **Comprobación auxiliar en `Z1_CROM0`** — `0x41C423C8` llama a `0x41F9C240`.

## Tabla de parches

| # | VA | Offset | Opcode original | Opcode nuevo | Efecto |
|---:|---|---|---|---|---|
| 1 | `0x41C2E07C` | `+0x107C` | `0xE92D47F0` (`push {r4-sl, lr}`) | `0xE3A00000` (`mov r0,#0`) | lectura CSIC: éxito inmediato |
| 2 | `0x41C2E080` | `+0x1080` | `0xE1A05001` (`mov r5, r1`) | `0xE12FFF1E` (`bx lr`) | cierra la función anterior |
| 3 | `0x41C2E120` | `+0x1120` | `0xE92D47F0` | `0xE3A00000` | escritura CSIC: éxito inmediato |
| 4 | `0x41C2E124` | `+0x1124` | `0xE1A06001` | `0xE12FFF1E` | cierra la función anterior |
| 5 | `0x41C2FD28` | `+0x2D28` | `0xE3A00000` (`mov r0,#0`) | `0xE3A00001` (`mov r0,#1`) | "cartucho presente" siempre |
| 6 | `0x41C41958` | `+0x14958` | `0xEBFFB8F5` (`bl 0x41C2FD34`) | `0xE3A00000` | sin error |
| 7 | `0x41C423C8` | `+0x153C8` | `0xEB0D679C` (`bl 0x41F9C240`) | `0xE3A00000` | sin error |
| 8 | `0x41C42850` | `+0x15850` | `0xEBFFB537` (`bl 0x41C2FD34`) | `0xE3A00000` | sin error |
| 9 | `0x41C42B20` | `+0x15B20` | `0xEBFFB483` (`bl 0x41C2FD34`) | `0xE3A00000` | sin error |
| 10 | `0x41C43390` | `+0x16390` | `0xEBFFB267` (`bl 0x41C2FD34`) | `0xE3A00000` | sin error |
| 11 | `0x41C43480` | `+0x16480` | `0xEBFFB22B` (`bl 0x41C2FD34`) | `0xE3A00000` | sin error |
| 12 | `0x41C4610C` | `+0x1910C` | `0xEBFFA708` (`bl 0x41C2FD34`) | `0xE3A00000` | sin error |
| 13 | `0x41C48F98` | `+0x1BF98` | `0xEBFF9B65` (`bl 0x41C2FD34`) | `0xE3A00000` | sin error |
| 14 | `0x41C4920C` | `+0x1C20C` | `0xEBFF9AC8` (`bl 0x41C2FD34`) | `0xE3A00000` | sin error |
| 15 | `0x41C497D0` | `+0x1C7D0` | `0xEBFF9957` (`bl 0x41C2FD34`) | `0xE3A00000` | sin error |

Las direcciones 13, 14 y 15 son las sensibles: en otras compilaciones de esta misma familia
aparecen 4 bytes más adelante. Copiar la tabla de otra versión sobrescribe `strb r0, [r4, #0x10]`
en `+0x1BF9C` y `cmp r0, #1` en `+0x1C210` y `+0x1C7D4`, y el resultado es una impresora que no
arranca. Por eso `construir.py` compara el opcode original de cada punto antes de escribir.

## Qué NO hace este parche

- No escribe nada en la EEPROM. La zona `0x00`–`0xFF` de la NVRAM queda como está.
- No modifica el bloque comprimido: los 15 cambios ocurren en RAM en cada arranque.
- No simula el chip: hace que la impresora no lo consulte.

## Consecuencia práctica

El nivel de tinta que muestra el panel o la web deja de ser una medición: pasa a ser un valor
fijo de lleno. La impresora imprimirá con un cartucho recargado o sin chip aunque esté
prácticamente seco, porque ya no tiene forma de saberlo. Ese es el trato: dejas de tener
bloqueos y también dejas de tener avisos.
