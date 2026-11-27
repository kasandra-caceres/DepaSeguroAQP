"""Ejecuta la lectura de fuentes de forma manual o programada."""
from __future__ import annotations

import logging
import threading
from datetime import datetime, timedelta

from ..dao.base import conectar
from ..services.alertas import alertas_zona
from ..services.evaluador import reevaluar_todos
from .fuentes import FUENTES, registrar_catalogo

log = logging.getLogger("depaseguro.ingesta")
_candado = threading.Lock()


def ejecutar_ingesta(conexion, solo: str | None = None) -> list[dict]:
    """Lee las fuentes, recalcula los avisos y genera alertas de zona."""
    if not _candado.acquire(blocking=False):
        return [{"fuente": "todas", "estado": "ocupado", "registros": 0,
                 "mensaje": "Ya hay una lectura en curso."}]
    try:
        registrar_catalogo(conexion)
        resultados = [clase(conexion).ejecutar() for clase in FUENTES if solo in (None, clase.clave)]
        reevaluar_todos(conexion)
        alertas_zona(conexion)
        return resultados
    finally:
        _candado.release()


def ultima_ejecucion(conexion) -> datetime | None:
    fila = conexion.execute("SELECT MAX(ultima_ejecucion) FROM fuentes_datos").fetchone()
    return datetime.fromisoformat(fila[0]) if fila and fila[0] else None


class Planificador(threading.Thread):
    """Hilo en segundo plano: revisa cada hora si ya toca actualizar las fuentes."""

    def __init__(self, ruta_db, intervalo_horas: int) -> None:
        super().__init__(daemon=True, name="planificador-fuentes")
        self.ruta_db = ruta_db
        self.intervalo = timedelta(hours=intervalo_horas)
        self.detener = threading.Event()

    def run(self) -> None:
        while not self.detener.is_set():
            conexion = conectar(self.ruta_db)
            try:
                ultima = ultima_ejecucion(conexion)
                if ultima is None or datetime.now() - ultima >= self.intervalo:
                    resultados = ejecutar_ingesta(conexion)
                    log.info("Lectura automática terminada: %s", resultados)
            except Exception:
                log.exception("Falló la lectura automática")
            finally:
                conexion.close()
            self.detener.wait(3600)
