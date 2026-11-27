"""Conexión SQLite y patrón DAO genérico para las operaciones CRUD."""
from __future__ import annotations

import sqlite3
from pathlib import Path

from flask import current_app, g

ESQUEMA = Path(__file__).resolve().parents[2] / "database" / "schema.sql"


def conectar(ruta: str | Path) -> sqlite3.Connection:
    """Abre una conexión con claves foráneas activas y filas tipo diccionario."""
    conexion = sqlite3.connect(ruta, timeout=30)
    conexion.row_factory = sqlite3.Row
    conexion.execute("PRAGMA foreign_keys = ON")
    conexion.execute("PRAGMA journal_mode = WAL")
    return conexion


def obtener_db() -> sqlite3.Connection:
    """Una conexión por petición; se cierra al terminar el contexto de Flask."""
    if "db" not in g:
        g.db = conectar(current_app.config["DB_PATH"])
    return g.db


def cerrar_db(_error=None) -> None:
    conexion = g.pop("db", None)
    if conexion is not None:
        conexion.close()


def crear_esquema(conexion: sqlite3.Connection) -> None:
    conexion.executescript(ESQUEMA.read_text(encoding="utf-8"))
    conexion.commit()


class BaseDAO:
    """Encapsula el SQL de una tabla. Las subclases solo declaran ``tabla``."""

    tabla = ""
    clave = "id"

    def __init__(self, conexion: sqlite3.Connection | None = None) -> None:
        self.db = conexion if conexion is not None else obtener_db()

    def _columnas(self) -> set[str]:
        return {fila["name"] for fila in self.db.execute(f"PRAGMA table_info({self.tabla})")}

    def _solo_validos(self, datos: dict) -> dict:
        """Evita inyección por nombres de columna: solo pasan columnas reales."""
        validas = self._columnas()
        return {clave: valor for clave, valor in datos.items() if clave in validas}

    def obtener(self, identificador) -> dict | None:
        fila = self.db.execute(
            f"SELECT * FROM {self.tabla} WHERE {self.clave} = ?", (identificador,)
        ).fetchone()
        return dict(fila) if fila else None

    def listar(self, orden: str | None = None, limite: int = 500) -> list[dict]:
        columna = orden if orden in self._columnas() else self.clave
        filas = self.db.execute(
            f"SELECT * FROM {self.tabla} ORDER BY {columna} DESC LIMIT ?", (limite,)
        )
        return [dict(fila) for fila in filas]

    def insertar(self, datos: dict) -> int:
        limpio = self._solo_validos(datos)
        columnas = ", ".join(limpio)
        marcas = ", ".join("?" for _ in limpio)
        cursor = self.db.execute(
            f"INSERT INTO {self.tabla} ({columnas}) VALUES ({marcas})", tuple(limpio.values())
        )
        self.db.commit()
        return cursor.lastrowid

    def actualizar(self, identificador, datos: dict) -> None:
        limpio = self._solo_validos(datos)
        if not limpio:
            return
        asignaciones = ", ".join(f"{columna} = ?" for columna in limpio)
        self.db.execute(
            f"UPDATE {self.tabla} SET {asignaciones} WHERE {self.clave} = ?",
            (*limpio.values(), identificador),
        )
        self.db.commit()

    def eliminar(self, identificador) -> None:
        self.db.execute(f"DELETE FROM {self.tabla} WHERE {self.clave} = ?", (identificador,))
        self.db.commit()

    def contar(self, condicion: str = "1=1", parametros: tuple = ()) -> int:
        return self.db.execute(
            f"SELECT COUNT(*) FROM {self.tabla} WHERE {condicion}", parametros
        ).fetchone()[0]
