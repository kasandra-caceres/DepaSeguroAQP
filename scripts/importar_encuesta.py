"""Convierte las respuestas del Google Form al CSV que usa el informe.

En la hoja de respuestas: Archivo > Descargar > Microsoft Excel (.xlsx) o Valores separados por comas (.csv).
También acepta el PDF que exporta Google Sheets.
Uso:  python scripts/importar_encuesta.py RUTA_DESCARGA.xlsx
      python scripts/importar_encuesta.py RUTA_DESCARGA.csv
      python scripts/importar_encuesta.py RUTA_DESCARGA.pdf
Crea data/encuesta_resultados.csv. Luego vuelve a ejecutar generar_informe.py.

El PDF corta las respuestas largas de la pregunta 9 en el ancho de la columna; el .xlsx y el .csv las traen completas.
"""
from __future__ import annotations

import re
import subprocess
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
OBLIGATORIAS = set(ORDEN) - {"universidad", "p9_confianza"}

# Una fila del PDF de Google Sheets: fecha, cinco respuestas cerradas, monto opcional, contrato, escala y texto libre.
FILA_PDF = re.compile(
    r"^\s*(\d{1,2}/\d{1,2}/\d{4} \d{1,2}:\d{2}:\d{2})\s+(Sí|No)\s+(Sí|No)\s+(Redes|WhatsApp|Carteles|Otro)\s+"
    r"(Sí|No)\s+(Sí|No)\s+(?:([\d.,]+)\s+)?(Sí|No)\s+([1-5])(?:\s+(.*?))?\s*$")


def desde_pdf(origen: Path) -> pd.DataFrame:
    texto = subprocess.run(["pdftotext", "-layout", str(origen), "-"], capture_output=True, text=True,
                           encoding="utf-8", check=True).stdout
    filas = []
    for linea in texto.splitlines():
        if not re.match(r"^\s*\d{1,2}/\d{1,2}/\d{4}", linea):
            continue
        coincidencia = FILA_PDF.match(linea)
        if not coincidencia:
            raise SystemExit(f"No se pudo leer esta fila del PDF:\n{linea}")
        fecha, p1, p2, p3, p4, p5, p6, p7, p8, p9 = coincidencia.groups()
        filas.append({"fecha": fecha, "p1_otra_region": p1, "p2_busco": p2, "p3_canal": p3, "p4_pago_previo": p4,
                      "p5_estafa": p5, "p6_monto": p6, "p7_contrato": p7, "p8_interes": int(p8), "p9_confianza": p9 or ""})
    if not filas:
        raise SystemExit("El PDF no tiene filas de respuestas.")
    return pd.DataFrame(filas)


def desde_tabla(origen: Path) -> pd.DataFrame:
    crudo = pd.read_excel(origen) if origen.suffix.lower() in (".xlsx", ".xls") else pd.read_csv(origen, encoding="utf-8-sig")
    nombres = {crudo.columns[0]: "fecha"}
    for columna in crudo.columns[1:]:
        for inicio, destino in COLUMNAS.items():
            if columna.strip().startswith(inicio):
                nombres[columna] = destino
    return crudo.rename(columns=nombres)


def convertir(origen: Path) -> pd.DataFrame:
    datos = desde_pdf(origen) if origen.suffix.lower() == ".pdf" else desde_tabla(origen)
    faltan = OBLIGATORIAS - set(datos.columns)
    if faltan:
        raise SystemExit(f"No se encontraron estas preguntas en el archivo: {', '.join(sorted(faltan))}")
    for opcional in ("universidad", "p9_confianza"):
        if opcional not in datos.columns:
            datos[opcional] = ""
    datos = datos[ORDEN].copy()
    datos["fecha"] = pd.to_datetime(datos["fecha"], dayfirst=True, errors="coerce").dt.date
    # Monto vacío: la persona no respondió esa pregunta. Se deja vacío para no contarlo como S/ 0.
    datos["p6_monto"] = pd.to_numeric(datos["p6_monto"].astype(str).str.replace(",", "."), errors="coerce")
    return datos


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    datos = convertir(Path(sys.argv[1]))
    datos.to_csv(SALIDA, index=False, encoding="utf-8")
    print(f"{len(datos)} respuestas guardadas en {SALIDA.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
