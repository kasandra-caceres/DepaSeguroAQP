"""Punto de entrada de DepaSeguro AQP.

    python run.py            inicia el servidor en http://127.0.0.1:5000
    python run.py --ingesta  lee las fuentes oficiales una vez y termina
"""
from __future__ import annotations

import sys

from depaseguro import create_app
from depaseguro.dao.base import conectar
from depaseguro.ingestion.planificador import ejecutar_ingesta


def main() -> None:
    if "--ingesta" in sys.argv:
        app = create_app({"INGESTA_AUTOMATICA": False})
        conexion = conectar(app.config["DB_PATH"])
        for resultado in ejecutar_ingesta(conexion):
            print(f"{resultado['fuente']:<22} {resultado['estado']:<12} {resultado['registros']:>7}  {resultado['mensaje']}")
        conexion.close()
        return
    create_app().run(host="127.0.0.1", port=5000, debug=False)


if __name__ == "__main__":
    main()
