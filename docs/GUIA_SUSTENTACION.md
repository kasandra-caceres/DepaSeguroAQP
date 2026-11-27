# Guía de estudio para la sustentación

La rúbrica califica **autoría**: el código debe ser del estudiante o, como mínimo, debe dominarlo. Usa esta guía para entender cada parte y poder modificarla frente al docente.

## Reparto sugerido de 8 minutos

| Diapositiva | Tema | Expone | Tiempo |
| --- | --- | --- | --- |
| 1-3 | Equipo, problema y solución | Kasandra | 1:50 |
| 4-6 | Proceso, arquitectura y fuentes | Alisson | 2:05 |
| 7 | Paradigmas y Trust Score | Kasandra | 0:55 |
| 8 | Demostración | Alisson | 1:20 |
| 9 | Base de datos | Kasandra | 0:35 |
| 10 | Calidad y Git | Alisson | 0:35 |
| 11 | Cierre | Kasandra | 0:40 |

## Dónde está cada concepto

| Concepto del curso | Archivo | Qué explicar |
| --- | --- | --- |
| Programación funcional | `depaseguro/functional/pipeline.py`, `services/busqueda.py` | `tubo`, closures y funciones que devuelven funciones |
| Programación lógica | `depaseguro/logic/motor.py`, `logic/reglas_fraude.pl` | Hechos, reglas, unificación y backtracking |
| Clases y herencia | `depaseguro/models/entidades.py`, `services/detectores.py` | `Usuario` y `Detector` son clases abstractas |
| Listas, tuplas y diccionarios | `services/evaluador.py`, `services/analitica.py` | Estructuras usadas en contexto y resultados |
| Pandas | `ingestion/fuentes.py`, `services/analisis_red.py` | Lectura de CSV, filtros y agrupación |
| Persistencia | `dao/base.py`, `dao/repositorios.py`, `database/schema.sql` | CRUD y consultas parametrizadas |

## Preguntas probables

**¿Por qué usar mediana y MAD?** Porque un precio falso muy bajo afecta menos a la mediana que al promedio.

**¿Qué diferencia hay entre SHA-256 y dHash?** SHA-256 detecta archivos idénticos. dHash reconoce imágenes parecidas aunque cambien tamaño o compresión.

**¿Cómo se calcula el Trust Score?** Se suman siete componentes hasta 100. Se restan reportes. Si las reglas detectan un caso crítico, el resultado no supera 24.

**¿Qué pasa si una fuente no responde?** `FuenteDatos.ejecutar` registra el error y continúa. Se conservan los últimos datos válidos.

**¿Cómo se evita acusar injustamente?** Se usa lenguaje de riesgo, se explica cada señal, el arrendador puede responder y un reporte solo se confirma por moderación.

**¿Por qué no se consulta SUNARP?** Requiere validaciones del servicio. El sistema no intenta evadirlas. Por eso se revisan documentos y se orienta al estudiante.

**¿Cuánto de esto es real?** Las fuentes son reales. Los avisos, usuarios y casos de demostración son ficticios.

## Práctica recomendada

1. Ejecuta el sistema desde cero con el manual.
2. Cambia una regla en `reglas_fraude.pl` y observa el resultado.
3. Agrega una frase en `FRASES_RIESGO` y prueba el verificador.
4. Ejecuta `python -m pytest`.
5. Explica en voz alta el recorrido de `EvaluadorInmueble.evaluar`.
