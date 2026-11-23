# Open Epson Chipless

Genera un firmware parcheado **a partir de tu propio paquete oficial de Epson**, para que una Epson
XP-243 / XP-245 / XP-247 siga imprimiendo cuando los chips de los cartuchos no están, están vacíos o
no se pueden leer. Sin claves de pago, sin servidores de activación, sin código del vendedor y sin
redistribuir firmware.

[Read in English](README.md) · [Protocolo para agentes LLM](AGENTS.md) · [Marco legal](MARCO_LEGAL_Y_ETICO.md)

> **Estado: verificado en hardware real y con el chip tapado físicamente.**
> Una Epson XP-247 con `20.25.EF20J9` se flasheó con la imagen que construye este repo. Un cartucho
> de color que la impresora tenía contado al **2 %**, con el chip cubierto con cinta adhesiva,
> imprimió una página completa —amarillo incluido— sin ningún aviso de cartucho no reconocido, y el
> trabajo se completó correctamente en la cola de impresión. Los contadores no se mueven nunca.
> Registro completo: [docs/verificado.md](docs/verificado.md).

---

## Qué hace y qué no hace

**Hace:** parchea, en el arranque, las rutinas del firmware que leen y validan el chip del cartucho.
La impresora deja de preguntar, así que un cartucho sin chip operativo se acepta y la impresión
continúa. El nivel de tinta se declara lleno y no baja.

**No hace:** arreglar un cabezal seco, saltarse límites físicos de tinta ni desbloquear software
comercial. Sin claves, sin activación, sin binarios de terceros. Tú aportas tu paquete oficial.

**La contrapartida honesta:** el contador está neutralizado, así que la impresora **no te avisará**
cuando un cartucho se seque de verdad. Fíjate en las páginas que salen, no en el indicador.

## Requisitos

- Python 3.10 o superior (solo biblioteca estándar).
- `capstone` para el descubridor (`pip install capstone`). El constructor, el verificador, los dos
  inspectores y el generador de página de prueba no necesitan nada más.
- Tu propio paquete oficial de Epson para esta familia (`.efu` o `.rcx`).

## Empezar en tres comandos

```bash
# 1. Mira tu paquete: zonas, componentes, hashes
python3 tools/inspeccionar.py FWF731TL.efu --resumen

# 2. Construye la imagen parcheada (usa la tabla incluida para 20.25.EF20J9)
python3 tools/construir.py FWF731TL.efu --out-dir build

# 3. Verifica el resultado de forma independiente
python3 tools/verificar.py FWF731TL.efu build/FWF731TL.efu
# debe imprimir {"correcto": true, "problemas": []}
```

Si tu paquete es otra versión u otro modelo, el paso 2 falla a propósito: primero hay que levantar la
tabla de parches con el descubridor. Esa es la parte diseñada para sobrevivir a una actualización de
firmware.

```bash
python3 tools/descubrir.py FW.efu                                  # solo huellas
python3 tools/descubrir.py FW.efu --trampolin <va> --flush <va> \
    --emitir-spec spec.json                                        # borrador de spec
python3 tools/construir.py FW.efu --spec spec.json --out-dir build
```

Dos decisiones siguen siendo humanas: qué trampolín de arranque y qué rutina de flush de caché son
los que se ejecutan de verdad. Hay decenas de candidatos estructuralmente idénticos y elegir mal no
da error: la impresora arranca sin parchear. Todo lo demás es mecánico y está en
[docs/metodologia.md](docs/metodologia.md).

## Pruebas, no promesas

| Evidencia | Dónde |
|---|---|
| La build es idéntica byte a byte en dos ejecuciones | `bc25ac2e…476f7`, `docs/verificado.md` |
| El firmware parcheado arranca y declara `20.25.EF20J9` | `docs/verificado.md` |
| Los cuatro indicadores pasan a lleno tras flashear | ídem |
| Imprime con el chip tapado con cinta (cartucho al 2 %) | ídem |
| Trabajo aceptado y completado por la cola (~48 s) | ídem |
| Los puntos se redescubren con los mismos opcodes solo desde el binario | `docs/metodologia.md` |
| El descubrimiento funciona en otra familia (XP-342/345, `FWG016TL`) | `docs/verificado.md` |
| Dos inspectores independientes dan los mismos hashes de estructura | `tools/inspect_firmware.py` vs `tools/inspeccionar.py` |

Lo que **no** está probado: flashear en otros modelos y el comportamiento en versiones distintas de
`20.25.EF20J9`. Aparece marcado como UNVERIFIED donde corresponde.

## Dos inspectores independientes

`tools/inspeccionar.py` (parte del pipeline) y `tools/inspect_firmware.py` (implementación aparte,
solo biblioteca estándar, con su propio informe de referencia) leen el mismo formato y emiten JSON
comparable. Se escribieron por separado y coinciden sobre el paquete oficial:

```bash
python3 tools/inspect_firmware.py FWF731TL.rcx > observado.json
diff -u docs/ef20j9-reference.json observado.json   # sin diferencias de estructura
```

Los mismos hashes desde dos implementaciones valen más que una herramienta que se da la razón a sí
misma.

## Seguridad

- El modo recuperación queda intacto: no se toca la zona de arranque ni la de recuperación, así que
  una imagen mala se puede recuperar con el actualizador oficial.
- Flashear por red funciona: `EPFWUPD.exe /NU /SU:I:<ip-de-la-impresora>`. El actualizador oficial se
  detiene hacia el 83 % esperando una versión concreta; la impresora reinicia y arranca parcheada.
- Lee [docs/flasheo.md](docs/flasheo.md) antes de flashear nada y guarda el paquete oficial en disco.
- Flashear firmware siempre tiene riesgo. Si no te ves capaz de recuperar una impresora bloqueada,
  no empieces.

## Aportar el resultado de tu modelo

Lo más útil que puedes enviar es un **informe relleno**: modelo, versión oficial, hash del RCX,
niveles de partida, qué se imprimió y qué no probaste. Plantilla e instrucciones:
[docs/plantilla-resultados.md](docs/plantilla-resultados.md).

No adjuntes binarios de firmware. Solo hashes.

## Legal

Investigación independiente sobre interoperabilidad y derecho a la reparación de un dispositivo
propiedad del autor. Modificar hardware propio para usar consumibles de terceros es uso privado con
recorrido en muchas jurisdicciones; la **distribución pública de tecnología de elusión** está
restringida en algunas (DMCA §1201 de EE. UU., Directiva 2001/29/CE art. 6, LPI arts. 160-161).
Este repositorio no contiene código de Epson, ni binarios, ni activadores. Lee
[MARCO_LEGAL_Y_ETICO.md](MARCO_LEGAL_Y_ETICO.md). No es asesoría legal.

## Estructura del repositorio

```
tools/        inspector, inspector de referencia, constructor, verificador, descubridor, página de prueba
data/         manifiesto de firmware (solo hashes) y tablas de parches por versión
docs/         arquitectura, subsistema de cartuchos, flasheo, metodología, evidencia, prueba empírica
docs/en/      los mismos documentos en inglés
AGENTS.md     protocolo paso a paso para que un agente LLM lo reproduzca sin adivinar
```

## Licencia

Código bajo **0BSD**. Documentación bajo **CC BY-SA 4.0**. Sin garantía de ningún tipo.
