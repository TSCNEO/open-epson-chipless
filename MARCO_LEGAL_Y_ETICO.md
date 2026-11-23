# Marco legal y ético

[Read in English](LEGAL_AND_ETHICS.md)

Este documento acompaña al proyecto de inspección de firmware de [README.es.md](README.es.md)
y a la guía de reproducción de [docs/reproduce.md](docs/reproduce.md). Deja claro qué es esta
publicación, qué no es, y qué implica publicarla o redistribuirla.

## 1. Propósito

Investigación técnica independiente sobre **interoperabilidad y derecho a la reparación** de
un equipo propio: entender cómo se empaqueta y verifica el firmware oficial de la Epson
XP-243/XP-245/XP-247, y documentar una inspección reproducible de **solo lectura**.

Esta publicación es un **inspector de solo lectura**. Analiza paquetes oficiales de
actualización que el lector obtiene localmente y describe su estructura y sus hashes.

## 2. Qué no es esta publicación

- **No** construye, modifica, firma ni flashea firmware. La construcción y validación de una
  imagen instalable quedan fuera del alcance de esta versión.
- **No** incluye, crackea ni ejecuta ningún activador o herramienta de licencia de terceros.
- **No** redistribuye firmware de Epson ni binarios de terceros; cada lector aporta su propio
  paquete oficial.
- **No** es un producto comercial de elusión ni un "kit" listo para copiar.

## 3. Marco legal (orientativo; no es asesoría legal)

Modificar hardware propio para usar consumibles de terceros es un tema de **derecho a la
reparación e interoperabilidad**, y el uso privado tiene margen en muchas jurisdicciones. El
punto sensible es la **distribución pública** de tecnología de elusión, y algunas
jurisdicciones restringen incluso las herramientas de investigación.

- **Estados Unidos.** La §1201 del DMCA (17 U.S.C.) prohíbe, entre otras cosas, *traficar*
  con tecnología diseñada para eludir una medida de protección técnica. Existen exenciones
  (investigación de seguridad de buena fe, reparación, interoperabilidad de ciertos
  dispositivos, *jailbreak*), pero son estrechas, y una herramienta genérica para anular la
  comprobación de un cartucho puede quedar fuera de ellas.
- **Unión Europea.** El art. 6 de la Directiva 2001/29/CE prohíbe eludir medidas técnicas y
  **fabricar, importar, distribuir, vender, anunciar o poseer con fines comerciales**
  dispositivos o servicios de elusión. Las excepciones del art. 6(4) son opcionales y las fija
  cada Estado miembro.
- **España.** Los arts. 160-161 del texto refundido de la LPI (RDL 1/1996) regulan las
  medidas de protección técnica y su elusión; el art. 31 cubre la copia privada y el art. 100
  la descompilación para interoperabilidad.
- **Otras jurisdicciones** pueden ser más estrictas e incluso criminalizar la distribución.

Como esta publicación es análisis de solo lectura, su exposición legal propia es menor que la
de una herramienta de elusión. Publicar o ampliar el proyecto en torno a ella puede seguir
cayendo bajo las normas anti-elusión de tu país.

## 4. Uso responsable

- Uso personal, educativo o de reparación sobre equipos propios.
- No vender ni empaquetar el método como producto.
- Respetar la ley de tu jurisdicción; si dudas, no lo distribuyas.
- Valorar una **divulgación coordinada** con la comunidad y, si procede, con el fabricante,
  antes de una difusión amplia.
- Presentar el trabajo como **investigación técnica y de reparación**, no como "bypass listo
  para copiar".

## 5. Licencia y redistribución

- El código se distribuye bajo **AGPL-3.0-only** ([LICENSE](LICENSE)).
- **No** se incluyen binarios de Epson; el lector obtiene el firmware oficial de fuentes
  oficiales o de archivos públicos.
- Quien redistribuya este material es responsable de cumplir la ley aplicable.

## 6. Riesgos

- El inspector es de solo lectura y no escribe en el hardware.
- Cualquier modificación de firmware (fuera del alcance de esta publicación) puede
  **inutilizar permanentemente** la impresora y anula la garantía. Realiza un volcado físico
  completo y verificado del chip flash SPI (p. ej. CH341A + pinza SOIC-8) antes de cualquier
  flasheo.

## 7. Descargo

Este material se ofrece **tal cual**, sin garantía de ningún tipo. El autor declina toda
responsabilidad en la medida permitida por la ley aplicable. Nada de lo aquí escrito
constituye asesoría legal.
