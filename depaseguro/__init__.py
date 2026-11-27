"""Fábrica de la aplicación Flask de DepaSeguro AQP."""
from __future__ import annotations

import logging
import os

from flask import Flask, render_template

from .config import Config
from .dao.base import cerrar_db, conectar, crear_esquema
from .ingestion.fuentes import registrar_catalogo
from .ingestion.planificador import Planificador
from .services import alertas as _alertas  # noqa: F401  registra los oyentes de eventos
from .web import admin, api, arrendador, auth, estudiante, publico
from .web.utilidades import preparar_peticion, registrar_filtros

DISTRITOS_BASE = (
    ("040101", "AREQUIPA", -16.3989, -71.5369), ("040102", "ALTO SELVA ALEGRE", -16.3770, -71.5230),
    ("040103", "CAYMA", -16.3700, -71.5450), ("040104", "CERRO COLORADO", -16.3610, -71.5760),
    ("040105", "CHARACATO", -16.4680, -71.4910), ("040107", "JACOBO HUNTER", -16.4380, -71.5620),
    ("040108", "LA JOYA", -16.4240, -71.8190), ("040109", "MARIANO MELGAR", -16.4040, -71.5060),
    ("040110", "MIRAFLORES", -16.3910, -71.5170), ("040112", "PAUCARPATA", -16.4300, -71.5040),
    ("040116", "SABANDIA", -16.4560, -71.4940), ("040117", "SACHACA", -16.4250, -71.5660),
    ("040122", "SOCABAYA", -16.4680, -71.5280), ("040123", "TIABAYA", -16.4470, -71.5900),
    ("040124", "UCHUMAYO", -16.4250, -71.6700), ("040126", "YANAHUARA", -16.3880, -71.5430),
    ("040128", "YURA", -16.2520, -71.6800), ("040129", "JOSE LUIS BUSTAMANTE Y RIVERO", -16.4240, -71.5250),
)


def asegurar_catalogos(conexion) -> None:
    conexion.executemany("INSERT OR IGNORE INTO distritos(ubigeo, nombre, lat, lon) VALUES (?,?,?,?)", DISTRITOS_BASE)
    conexion.commit()
    registrar_catalogo(conexion)


def create_app(configuracion: dict | None = None) -> Flask:
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config.from_object(Config)
    app.config.update(configuracion or {})
    Config.preparar(app)

    conexion = conectar(app.config["DB_PATH"])
    crear_esquema(conexion)
    asegurar_catalogos(conexion)
    conexion.close()

    app.teardown_appcontext(cerrar_db)
    app.before_request(preparar_peticion)
    registrar_filtros(app)
    for modulo in (publico, auth, estudiante, arrendador, admin, api):
        app.register_blueprint(modulo.bp)

    @app.errorhandler(403)
    def prohibido(_error):
        return render_template("publico/error.html", codigo=403, mensaje="No tienes permiso para ver esta página."), 403

    @app.errorhandler(404)
    def no_encontrado(_error):
        return render_template("publico/error.html", codigo=404, mensaje="No encontramos esa página."), 404

    @app.errorhandler(413)
    def muy_grande(_error):
        return render_template("publico/error.html", codigo=413, mensaje="Los archivos superan el límite de 12 MB."), 413

    @app.after_request
    def cabeceras_seguridad(respuesta):
        respuesta.headers.setdefault("X-Content-Type-Options", "nosniff")
        respuesta.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        respuesta.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        return respuesta

    es_proceso_recargado = os.environ.get("WERKZEUG_RUN_MAIN") == "true" or not app.debug
    if app.config["INGESTA_AUTOMATICA"] and not app.config["TESTING"] and es_proceso_recargado:
        logging.basicConfig(level=logging.INFO)
        Planificador(app.config["DB_PATH"], app.config["INGESTA_INTERVALO_HORAS"]).start()
    return app
