# Flashear y recuperar

## Antes de empezar

1. Construye y verifica:

   ```sh
   python3 tools/construir.py EF20J9.efu --out-dir build
   python3 tools/verificar.py EF20J9.efu build/FWF731TL.efu   # debe decir "correcto": true
   ```

2. Guarda el paquete oficial y **anota su hash**. Es tu vía de vuelta:

   ```sh
   sha256sum EF20J9.efu
   # 3e9ae697fadece00618217da9737866ff8f0a1c38030edd4ac8eb24848ab4074
   ```

3. Comprueba que el fichero que vas a flashear es exactamente el verificado:

   ```sh
   sha256sum build/FWF731TL.efu
   ```

## Qué esperar después

- La impresora reporta **la misma versión que antes** (`20.25.EF20J9`). El parche no cambia la
  cadena de versión interna; solo se declara otra en el manifiesto para que el actualizador
  acepte el paquete.
- Los cuatro indicadores de tinta pasan a marcar lleno de forma permanente.
- Los cartuchos sin chip o recargados dejan de dar error.

## Transporte 1: USB (recomendado)

Usa el mismo actualizador oficial de Epson que trae el paquete, con el cable conectado
directamente (sin hub). Sustituye el `FWF731TL.efu` del directorio por el que has construido.

Ventaja: el cable que usas para flashear es el mismo que necesitarás si algo sale mal.

## Transporte 2: red

El actualizador oficial acepta la impresora por red:

```sh
EPFWUPD.exe /NU /SU:I:<ip-de-la-impresora>
```

En la unidad probada la secuencia fue:

```
WaitIdle,Done,0        -> Update,Done,0        Progress:50
WaitUpdating,Done,0                            Progress:66
Reboot,Start,0                                 Progress:83
```

**Se queda en 83 y no termina.** No es un fallo: tras reiniciar, el actualizador intenta leer la
versión `EF99Z9` que declara el manifiesto, y la impresora sigue reportando `EF20J9` porque el
parche no toca ese dato. Se puede cerrar el proceso: el flasheo ya ha terminado.

Advertencia: si la impresora no arrancase tras un flasheo por red, pierde la conectividad y la
recuperación exige sí o sí un cable USB.

## Recuperación

El parche **nunca incluye los primeros 64 KiB** (bootloader `BooSt`), así que el modo de
recuperación sigue intacto:

1. Apaga la impresora.
2. Enciéndela con la combinación de teclas documentada por Epson para entrar en modo
   actualización/IPL (en esta familia, mantener pulsadas las teclas indicadas mientras se
   enciende hasta que el equipo aparezca al PC).
3. El PC debe ver un dispositivo USB con ID `04b8:0007` (modo IPL).
4. Reflashea el paquete oficial con el actualizador de Epson, o con `epsflasher`
   (proyecto `abrasive/epson-reversing`) si prefieres línea de comandos en Linux.

Si nunca has probado ese modo, hazlo **antes** de flashear nada modificado: entrar y salir sin
escribir no rompe nada y confirma que tu red de seguridad existe.

## Después

- **Desactiva las actualizaciones automáticas de firmware.** Cualquier actualización oficial
  sobrescribe el parche y volverías al bloqueo por chip. En la web de la impresora, revisa las
  opciones de notificación/actualización y desactívalas; y no aceptes avisos de nueva versión.
- Comprueba el estado en la web de la impresora: modelo, versión y los cuatro niveles.
- Haz una impresión de prueba y un ciclo de apagado/encendido para confirmar que el parche se
  reaplica (debe seguir sin quejarse del chip).

## Si algo va mal

| Síntoma | Qué significa | Acción |
|---|---|---|
| El actualizador se queda en `Progress:83` | Comportamiento esperado: espera una versión que no vas a reportar | Cierra el proceso, la impresora ya está flasheada |
| La impresora no responde por red tras reiniciar | Arranque roto | Recuperación por USB (arriba) |
| Arranca pero sigue pidiendo chip | El hook no se ejecutó | Revisa que el punto 2 del parche esté en `0x00032100` y que `0x00016340` valga `0x00032100` |
| Sigue pidiendo chip solo en un color | Puede quedar un aviso por una llamada del agregador no neutralizada | Reporta el caso con la versión y el bloque descomprimido |
