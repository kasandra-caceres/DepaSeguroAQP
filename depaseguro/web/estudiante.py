"""Panel y acciones del estudiante."""
from __future__ import annotations

import io

from flask import Blueprint, abort, flash, g, redirect, render_template, request, send_file, url_for

from ..dao.base import obtener_db
from ..dao.repositorios import AlertaDAO, BusquedaGuardadaDAO, CampusDAO, FavoritoDAO, InmuebleDAO, ReporteDAO
from ..services import reportes
from ..services.gestion import registrar_reporte, registrar_resena
from .utilidades import requiere_rol

bp = Blueprint("estudiante", __name__, url_prefix="/estudiante")


@bp.route("/")
@requiere_rol("estudiante")
def panel():
    db = obtener_db()
    alertas = AlertaDAO(db).de_usuario(g.usuario.id)
    db.execute("UPDATE alertas SET leida = 1 WHERE usuario_id = ?", (g.usuario.id,))
    db.commit()
    return render_template(
        "estudiante/panel.html", favoritos=FavoritoDAO(db).de_usuario(g.usuario.id), alertas=alertas,
        busquedas=BusquedaGuardadaDAO(db).de_usuario(g.usuario.id), campus=CampusDAO(db).todos(),
        reportes=ReporteDAO(db).con_detalle("r.reportante_id = ?", (g.usuario.id,)))


@bp.route("/favorito/<int:inmueble_id>", methods=["POST"])
@requiere_rol("estudiante")
def favorito(inmueble_id: int):
    agregado = FavoritoDAO(obtener_db()).alternar(g.usuario.id, inmueble_id)
    flash("Aviso guardado. Te alertaremos si su puntaje baja." if agregado else "Aviso quitado de tus guardados.", "ok")
    return redirect(url_for("publico.detalle", inmueble_id=inmueble_id))


@bp.route("/resena/<int:inmueble_id>", methods=["POST"])
@requiere_rol("estudiante")
def resena(inmueble_id: int):
    verificada = registrar_resena(obtener_db(), inmueble_id, g.usuario.id, request.form.get("puntaje"),
                                  request.form.get("comentario", ""), request.form.get("codigo", ""))
    flash("Reseña verificada publicada." if verificada else "Reseña publicada sin código de visita.", "ok")
    return redirect(url_for("publico.detalle", inmueble_id=inmueble_id) + "#resenas")


@bp.route("/reportar/<int:inmueble_id>", methods=["POST"])
@requiere_rol("estudiante")
def reportar(inmueble_id: int):
    identificador = registrar_reporte(obtener_db(), inmueble_id, g.usuario.id, request.form.to_dict())
    flash(f"Registramos tu reporte N.º {identificador}. Puedes descargar tu expediente en tu panel.", "ok")
    return redirect(url_for("publico.detalle", inmueble_id=inmueble_id))


@bp.route("/busquedas", methods=["POST"])
@requiere_rol("estudiante")
def guardar_busqueda():
    BusquedaGuardadaDAO(obtener_db()).insertar({
        "usuario_id": g.usuario.id, "campus_id": request.form.get("campus_id", type=int),
        "radio_km": request.form.get("radio_km", 2, type=float), "precio_max": request.form.get("precio_max", 800, type=float),
        "trust_min": request.form.get("trust_min", 60, type=int)})
    flash("Búsqueda guardada. Te avisaremos cuando aparezca una opción compatible.", "ok")
    return redirect(url_for("estudiante.panel"))


@bp.route("/busquedas/<int:busqueda_id>/eliminar", methods=["POST"])
@requiere_rol("estudiante")
def eliminar_busqueda(busqueda_id: int):
    dao = BusquedaGuardadaDAO(obtener_db())
    busqueda = dao.obtener(busqueda_id)
    if busqueda is None or busqueda["usuario_id"] != g.usuario.id:
        abort(403)
    dao.eliminar(busqueda_id)
    return redirect(url_for("estudiante.panel"))


@bp.route("/reportes/<int:reporte_id>/expediente.pdf")
@requiere_rol("estudiante", "admin")
def expediente(reporte_id: int):
    db = obtener_db()
    reporte = ReporteDAO(db).obtener(reporte_id)
    if reporte is None or (g.usuario.rol != "admin" and reporte["reportante_id"] != g.usuario.id):
        abort(403)
    return send_file(io.BytesIO(reportes.pdf_expediente(db, reporte_id)), mimetype="application/pdf",
                     as_attachment=True, download_name=f"expediente-{reporte_id}.pdf")
