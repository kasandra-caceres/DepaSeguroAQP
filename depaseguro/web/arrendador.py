"""Panel del arrendador: gestión de avisos, documentos, códigos de visita y descargos."""
from __future__ import annotations

from flask import Blueprint, abort, flash, g, redirect, render_template, request, url_for

from ..dao.base import obtener_db
from ..dao.repositorios import DistritoDAO, DocumentoDAO, InmuebleDAO, ReporteDAO
from ..services.evaluador import EvaluadorInmueble, detalle_evaluacion
from ..services.gestion import (SERVICIOS, crear_aviso, editar_aviso, eliminar_aviso, generar_codigo_visita,
                                guardar_documento, responder_reporte)
from .utilidades import requiere_rol

bp = Blueprint("arrendador", __name__, url_prefix="/arrendador")


def _aviso_propio(inmueble_id: int) -> dict:
    aviso = InmuebleDAO(obtener_db()).detalle(inmueble_id)
    if aviso is None or aviso["arrendador_id"] != g.usuario.id:
        abort(403)
    return aviso


@bp.route("/")
@requiere_rol("arrendador")
def panel():
    db = obtener_db()
    avisos = [a for a in InmuebleDAO(db).de_arrendador(g.usuario.id) if a["estado"] != "retirado"]
    reportes = ReporteDAO(db).con_detalle("i.arrendador_id = ? AND r.estado IN ('abierto','en_revision')", (g.usuario.id,))
    return render_template("arrendador/panel.html", avisos=avisos, reportes=reportes)


@bp.route("/inmuebles/nuevo", methods=["GET", "POST"])
@requiere_rol("arrendador")
def nuevo():
    db = obtener_db()
    if request.method == "POST":
        identificador = crear_aviso(db, g.usuario.id, request.form, request.form.getlist("servicios"),
                                    request.files.getlist("imagenes"))
        flash("Aviso registrado. Sube tus documentos para mejorar el Trust Score.", "ok")
        return redirect(url_for("arrendador.gestionar", inmueble_id=identificador))
    return render_template("arrendador/formulario.html", aviso=None, servicios_aviso=[], SERVICIOS=SERVICIOS,
                           distritos=DistritoDAO(db).todos())


@bp.route("/inmuebles/<int:inmueble_id>", methods=["GET"])
@requiere_rol("arrendador")
def gestionar(inmueble_id: int):
    db = obtener_db()
    aviso = _aviso_propio(inmueble_id)
    return render_template("arrendador/gestionar.html", aviso=aviso, documentos=DocumentoDAO(db).de_inmueble(inmueble_id),
                           evaluacion=detalle_evaluacion(db, inmueble_id))


@bp.route("/inmuebles/<int:inmueble_id>/editar", methods=["GET", "POST"])
@requiere_rol("arrendador")
def editar(inmueble_id: int):
    db = obtener_db()
    aviso = _aviso_propio(inmueble_id)
    if request.method == "POST":
        editar_aviso(db, inmueble_id, g.usuario.id, request.form, request.form.getlist("servicios"),
                     request.files.getlist("imagenes"))
        flash("Aviso actualizado y evaluado otra vez.", "ok")
        return redirect(url_for("arrendador.gestionar", inmueble_id=inmueble_id))
    return render_template("arrendador/formulario.html", aviso=aviso, SERVICIOS=SERVICIOS,
                           servicios_aviso=InmuebleDAO(db).servicios(inmueble_id), distritos=DistritoDAO(db).todos())


@bp.route("/inmuebles/<int:inmueble_id>/eliminar", methods=["POST"])
@requiere_rol("arrendador")
def eliminar(inmueble_id: int):
    eliminar_aviso(obtener_db(), inmueble_id, g.usuario.id)
    flash("Aviso retirado.", "ok")
    return redirect(url_for("arrendador.panel"))


@bp.route("/inmuebles/<int:inmueble_id>/documentos", methods=["POST"])
@requiere_rol("arrendador")
def documento(inmueble_id: int):
    db = obtener_db()
    _aviso_propio(inmueble_id)
    guardar_documento(db, inmueble_id, request.form.get("tipo", ""), request.files["archivo"])
    EvaluadorInmueble(db).evaluar(inmueble_id)
    flash("Documento enviado a revisión.", "ok")
    return redirect(url_for("arrendador.gestionar", inmueble_id=inmueble_id))


@bp.route("/inmuebles/<int:inmueble_id>/codigo", methods=["POST"])
@requiere_rol("arrendador")
def codigo(inmueble_id: int):
    nuevo_codigo = generar_codigo_visita(obtener_db(), inmueble_id, g.usuario.id)
    flash(f"Código de visita: {nuevo_codigo}. Entrégalo al estudiante después de la visita.", "ok")
    return redirect(url_for("arrendador.gestionar", inmueble_id=inmueble_id))


@bp.route("/reportes/<int:reporte_id>/descargo", methods=["POST"])
@requiere_rol("arrendador")
def descargo(reporte_id: int):
    responder_reporte(obtener_db(), reporte_id, g.usuario.id, request.form.get("texto", ""))
    flash("Tu descargo fue enviado a moderación.", "ok")
    return redirect(url_for("arrendador.panel"))
