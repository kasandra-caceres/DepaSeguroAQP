"""Configuración central de DepaSeguro AQP (rutas, límites y parámetros)."""
from __future__ import annotations

import os
import secrets
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def _clave_secreta(data_dir: Path) -> str:
    """Devuelve una clave persistente para firmar sesiones sin guardarla en Git."""
    if os.environ.get("DEPASEGURO_SECRET"):
        return os.environ["DEPASEGURO_SECRET"]
    archivo = data_dir / ".secret_key"
    if archivo.exists():
        return archivo.read_text(encoding="utf-8").strip()
    data_dir.mkdir(parents=True, exist_ok=True)
    clave = secrets.token_hex(32)
    archivo.write_text(clave, encoding="utf-8")
    return clave


class Config:
    """Valores por defecto; varios pueden sobrescribirse con variables de entorno."""

    DATA_DIR = Path(os.environ.get("DEPASEGURO_DATA", BASE_DIR / "data"))
    MAX_CONTENT_LENGTH = 12 * 1024 * 1024  # 12 MB por petición
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    TESTING = False

    # Lectura automática de fuentes
    INGESTA_AUTOMATICA = os.environ.get("DEPASEGURO_INGESTA", "1") == "1"
    INGESTA_INTERVALO_HORAS = int(os.environ.get("DEPASEGURO_INTERVALO_H", "24"))
    HTTP_TIMEOUT = 90
    # Cliente genérico: las APIs abiertas piden identificar la aplicación, no a una persona.
    USER_AGENT = "DepaSeguroAQP/1.0 (proyecto academico UTP Arequipa)"
    GEOCODIFICAR = os.environ.get("DEPASEGURO_GEOCODIFICAR", "1") == "1"

    # Umbrales del motor de riesgo
    MUESTRA_MINIMA_PRECIOS = 5
    Z_PRECIO_BAJO = -1.5
    Z_PRECIO_MUY_BAJO = -2.5
    HAMMING_IMAGEN_DUPLICADA = 6
    ADELANTO_MAXIMO_MESES = 2
    TIPO_CAMBIO_RESPALDO = 3.45  # solo si BCRP nunca pudo leerse

    @classmethod
    def preparar(cls, app) -> None:
        """Crea carpetas de trabajo y completa la configuración dependiente de DATA_DIR."""
        data = Path(app.config.get("DATA_DIR", cls.DATA_DIR))
        rutas = {
            "DB_PATH": data / "depaseguro.db",
            "UPLOAD_IMAGENES": data / "uploads" / "imagenes",
            "UPLOAD_DOCUMENTOS": data / "uploads" / "documentos",
            "CACHE_DIR": data / "cache",
            "EXPORT_DIR": data / "exports",
        }
        for clave, ruta in rutas.items():
            app.config.setdefault(clave, ruta)
        for clave in ("UPLOAD_IMAGENES", "UPLOAD_DOCUMENTOS", "CACHE_DIR", "EXPORT_DIR"):
            Path(app.config[clave]).mkdir(parents=True, exist_ok=True)
        if not app.config.get("SECRET_KEY"):
            app.config["SECRET_KEY"] = _clave_secreta(data)
