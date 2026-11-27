# Rehacer las capturas 11 y 21, la de pruebas y regenerar los documentos

Hazlo en la PC donde el proyecto ya tiene la ingesta hecha, con internet. En Windows, desde la carpeta del proyecto y con el entorno virtual activo:

```
pip install playwright pytest-cov
python run.py --ingesta
python run.py
```

Deja el servidor abierto. En otra terminal, también con el entorno activo:

```
python scripts/capturar_pantallas.py 11_busqueda_campus 21_admin_fuentes
python scripts/generar_evidencias.py pruebas
python scripts/generar_informe.py "RUTA\PLANTILLA INFORME LENGUAJES DE PROGRAMACIÓN (1).docx"
python scripts/generar_manual.py "RUTA\TEMPLATE - MANUAL DE USUARIO (1).docx"
```

El script de capturas presiona Leer en OpenStreetMap antes de fotografiar la vista de Fuentes, para que el mensaje guardado diga "Bajo demanda". También comprueba que el filtro de precio sea válido: si el navegador lo rechazara, lo informa como error en vez de guardar una captura con el aviso. Debe terminar con "Sin errores de navegador."

Revisa las dos imágenes en `docs/capturas/` antes de regenerar. Los nuevos `.docx` y `.pdf` quedan en `entregables/`.

`generar_evidencias.py pruebas` ejecuta pytest con `--cov=depaseguro` cuando pytest-cov está instalado, y con `--no-header` para que la captura no muestre rutas locales. El informe y la presentación toman el número de pruebas y la cobertura de esa ejecución.
