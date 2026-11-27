"""Convierte las respuestas del Google Form al CSV que usa el informe.

En la hoja de respuestas: Archivo > Descargar > Valores separados por comas (.csv).
Uso:  python scripts/importar_encuesta.py RUTA_DESCARGA.csv
Crea data/encuesta_resultados.csv. Luego vuelve a ejecutar generar_informe.py.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
SALIDA = RAIZ / "data" / "encuesta_resultados.csv"

# Inicio del título de cada pregunta en el formulario -> columna del CSV del proyecto.
COLUMNAS = {
    "Universidad": "universidad",
    "1.": "p1_otra_region", "2.": "p2_busco", "3.": "p3_canal", "4.": "p4_pago_previo", "5.": "p5_estafa",
    "6.": "p6_monto", "7.": "p7_contrato", "8.": "p8_interes", "9.": "p9_confianza",
}
ORDEN = ["fecha", "universidad", "p1_otra_region", "p2_busco", "p3_canal", "p4_pago_previo", "p5_estafa",
         "p6_monto", "p7_contrato", "p8_interes", "p9_confianza"]


def convertir(origen: Path) -> pd.DataFrame:
    crudo = pd.read_csv(origen, encoding="utf-8-sig")
    nombres = {crudo.columns[0]: "fecha"}
    for columna in crudo.columns[1:]:
        for inicio, destino in COLUMNAS.items():
            if columna.strip().startswith(inicio):
                nombres[columna] = destino
    faltan = set(ORDEN) - set(nombres.values())
    if faltan:
        raise SystemExit(f"No se encontraron estas preguntas en el archivo: {', '.join(sorted(faltan))}")
    datos = crudo.rename(columns=nombres)[ORDEN]
    datos["fecha"] = pd.to_datetime(datos["fecha"], dayfirst=True, errors="coerce").dt.date
    datos["p6_monto"] = pd.to_numeric(datos["p6_monto"].astype(str).str.replace(",", "."), errors="coerce").fillna(0)
    return datos


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    datos = convertir(Path(sys.argv[1]))
    datos.to_csv(SALIDA, index=False, encoding="utf-8")
    print(f"{len(datos)} respuestas guardadas en {SALIDA.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
