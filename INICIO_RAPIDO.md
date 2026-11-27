# Inicio rapido de la entrega

El respaldo SQLite con datos ficticios esta en data/depaseguro.db.
Las imagenes y los documentos de demostracion estan en data/uploads.
Conserva estas carpetas al descomprimir el ZIP.

En PowerShell, desde la carpeta DepaSeguroAQP, ejecuta:

    py -3 -m venv .venv
    .\.venv\Scripts\python.exe -m pip install -r requirements.txt
    $env:DEPASEGURO_INGESTA = '0'
    $env:DEPASEGURO_GEOCODIFICAR = '0'
    .\.venv\Scripts\python.exe run.py

Usa Python 3.12 o superior. Abre http://127.0.0.1:5000.
El respaldo permite abrir el catalogo y las fichas sin cargar datos de nuevo.
Los mosaicos del mapa necesitan internet.

Para la sustentacion, abre el catalogo y selecciona el aviso
"Minidepartamento de lujo a precio de remate". Muestra su Trust Score y explica
las senales con depaseguro/services/evaluador.py y depaseguro/logic/reglas_fraude.pl.
Consulta docs/GUIA_SUSTENTACION.md y la presentacion en entregables/.
