"""Endpoints JSON que alimentan mapas y gráficos del frontend."""
from __future__ import annotations

from flask import Blueprint, jsonify, request, url_for

from ..dao.base import obtener_db
from ..dao.repositorios import CampusDAO, InmuebleDAO
from ..services import analisis_red, reportes
from .utilidades import requiere_rol

bp = Blueprint("api", __name__, url_prefix="/api")


@bp.route("/mapa")
def mapa():
    db = obtener_db()
    avisos = [
        {"id": a["id"], "titulo": a["titulo"], "lat": a["lat"], "lon": a["lon"], "nivel": a["nivel_riesgo"],
         "trust": a["trust_score"], "precio": a["precio_mensual_pen"], "distrito": a["distrito"].title(),
         "url": url_for("publico.detalle", inmueble_id=a["id"])}
        for a in InmuebleDAO(db).publicados() if a["lat"] is not None
    ]
    campus = [{"universidad": c["universidad"].title(), "lat": c["lat"], "lon": c["lon"], "local": c["codigo_local"],
               "licencia": c["licencia"]} for c in CampusDAO(db).todos()]
    return jsonify({"avisos": avisos, "campus": campus})


@bp.route("/zonas/serie")
def serie():
    return jsonify(analisis_red.serie_estafas(obtener_db(), request.args.get("ubigeo") or None))


@bp.route("/admin/indicadores")
@requiere_rol("admin")
def indicadores():
    return jsonify(reportes.indicadores_panel(obtener_db()))
