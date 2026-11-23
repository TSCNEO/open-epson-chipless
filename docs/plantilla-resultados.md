# Plantilla de resultados para tu modelo

Esto es lo que convierte un repo en algo que crece: alguien con otra impresora prueba y deja el
resultado en un formato que vale. Copia el bloque, rellénalo y mándalo como pull request o issue.

Regla única: **lo que no hayas probado se queda como `no probado`**. No se rellena con suposiciones.

## Antes de empezar

1. Anota modelo exacto y versión que declara la impresora (web o panel).
2. Pasa el inspector sobre tu paquete oficial y guarda el hash del RCX.
3. Anota los cuatro niveles que muestra la impresora y haz una comprobación de inyectores con el
   menú de mantenimiento. Eso es la línea base.

## Bloque para rellenar

```text
Modelo de impresora:
Versión oficial de partida:
SHA-256 del RCX oficial:
Cartuchos instalados y si cada uno tiene chip:
  Línea base (antes de cualquier cambio):
    Niveles declarados:      K=__  Y=__  M=__  C=__
    Comprobación de inyectores:  (patrón completo / fallos en qué color)

Imagen construida:
  Herramienta y spec usados:   (tabla de data/patches/... o spec generado)
  SHA-256 de la imagen:
  Salida de tools/verificar.py:  correcto=____  problemas=____

Flasheo:
  Transporte:              USB / red
  Versión declarada después:
  Panel y web responden:   sí / no
  Reinicio completo posterior: sí / no

Prueba con el chip tapado:
  Cinta sobre los contactos:   sí / no
  Aviso del panel al insertar:
  Niveles declarados antes de imprimir:
  Trabajo enviado y estado en la cola:
  Niveles declarados después de imprimir:
  ¿Salió la página? ¿Se veían los cuatro colores?

No probado:
  (sé específico: otras versiones, otro modelo, impresión a doble cara, etc.)
```

## Qué hace útil un informe

- El **hash del RCX**, no la versión a secas. Dos builds distintas comparten etiqueta.
- La **salida literal** de `verificar.py`, no "verificado".
- La **foto o descripción** de la página impresa: la prueba es el papel, no el indicador.
- Los **fallos**, con el texto exacto del panel. Un informe negativa bien descrito vale más que
  diez positivos sin datos.

## Lo que no se acepta

- Binarios de firmware, empaquetados o descomprimidos.
- Nombres de vendedores de firmware o activadores comerciales.
- Informes con secciones "debería funcionar".
