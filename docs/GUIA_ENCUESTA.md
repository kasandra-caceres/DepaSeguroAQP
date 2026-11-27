# Evidencia en la sociedad: encuesta a estudiantes

Los lineamientos piden evidencia del trabajo en la sociedad. El anexo C del informe se llena solo con las respuestas reales.

1. Crea el formulario con `scripts/crear_formulario_google.gs`: entra a https://script.google.com, crea un proyecto, pega el archivo, ejecuta `crearEncuesta` y copia el enlace para responder que aparece en los registros. Compártelo con estudiantes de UTP y otras universidades de Arequipa. Apunta a 20 respuestas o más.
2. Toma fotos o capturas de la aplicación, sin mostrar rostros ni nombres sin permiso, y guárdalas en `docs/evidencias/sociedad/` como `.jpg` o `.png`. El nombre del archivo se usa como leyenda, por ejemplo `aplicacion_campus_utp.jpg`.
3. En la hoja de respuestas usa Archivo > Descargar > CSV y conviértelo:

```
python scripts/importar_encuesta.py "RUTA\Respuestas - Encuesta DepaSeguro AQP.csv"
```

Esto crea `data/encuesta_resultados.csv`. Si aplicas encuestas en papel, agrega esas filas al mismo archivo con los valores de `data/encuesta_plantilla.csv`: Sí o No; Redes, WhatsApp, Carteles u Otro; monto en soles; interés de 1 a 5.

4. Vuelve a generar el informe: `python scripts/generar_informe.py "RUTA\PLANTILLA INFORME.docx"`. Python calcula los porcentajes y los inserta en el anexo C, y quita el aviso amarillo.
