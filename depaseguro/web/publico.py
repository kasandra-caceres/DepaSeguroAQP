"""Vistas públicas: inicio, catálogo, ficha, mapa, verificador, zonas, fuentes, blog y contacto."""
from __future__ import annotations

import io
from pathlib import Path

from flask import (Blueprint, abort, current_app, flash, g, redirect, render_template, request, send_file,
                   send_from_directory, url_for)

from ..dao.base import obtener_db
from ..dao.repositorios import (BlogDAO, CampusDAO, ContactoDAO, DistritoDAO, EvaluacionDAO, FavoritoDAO, FuenteDAO,
                                ImagenDAO, IndicadorDAO, InmuebleDAO, ResenaDAO)
from ..services import analisis_red, reportes
from ..services.analitica import analizar_clausulas
from ..services.busqueda import FiltrosBusqueda, buscar, campus_cercanos
from ..services.evaluador import detalle_evaluacion, tipo_cambio_vigente
from ..services.gestion import ErrorNegocio
from ..services.verificador import AvisoExterno, verificar

bp = Blueprint("publico", __name__)


def _decimal(nombre: str) -> float | None:
    valor = request.values.get(nombre, "").strip().replace(",", ".")
    try:
        return float(valor) if valor else None
    except ValueError:
        return None


def _campus_elegido(db) -> dict | None:
    identificador = request.args.get("campus", type=int)
    return CampusDAO(db).obtener(identificador) if identificador else None


@bp.route("/")
def inicio():
    db = obtener_db()
    avisos = InmuebleDAO(db).publicados()
    fuentes = FuenteDAO(db).todas()
    resumen = {
        "avisos": len(avisos),
        "confiables": sum(a["nivel_riesgo"] == "Confiable" for a in avisos),
        "campus": CampusDAO(db).contar(),
        "fuentes_ok": sum(f["estado"] in ("ok", "sin_cambios") for f in fuentes),
        "fuentes": len(fuentes),
    }
    destacados = [a for a in avisos if a["estado"] == "publicado"][:3]
    anual = analisis_red.resumen_anual_estafas(db)
    return render_template("publico/inicio.html", resumen=resumen, destacados=destacados,
                           posts=BlogDAO(db).listar(limite=3), anual=anual,
                           campus=CampusDAO(db).todos(), tipo_cambio=IndicadorDAO(db).ultimo("tipo_cambio_venta"))


@bp.route("/inmuebles")
def catalogo():
    db = obtener_db()
    filtros = FiltrosBusqueda(
        ubigeo=request.args.get("ubigeo") or None, tipo=request.args.get("tipo") or None,
        precio_max=_decimal("precio_max"), trust_min=request.args.get("trust_min", type=int),
        campus=_campus_elegido(db), radio_km=_decimal("radio_km"), orden=request.args.get("orden", "compatibilidad"))
    avisos = buscar(InmuebleDAO(db).publicados(), filtros)
    return render_template("publico/catalogo.html", avisos=avisos, filtros=filtros, distritos=DistritoDAO(db).todos(),
                           campus=CampusDAO(db).todos())


@bp.route("/inmuebles/<int:inmueble_id>")
def detalle(inmueble_id: int):
    db = obtener_db()
    aviso = InmuebleDAO(db).detalle(inmueble_id)
    es_dueno = g.usuario is not None and aviso is not None and g.usuario.id == aviso["arrendador_id"]
    es_admin = g.usuario is not None and g.usuario.rol == "admin"
    if aviso is None or (aviso["estado"] not in ("publicado", "observado") and not (es_dueno or es_admin)):
        abort(404)
    favorito = False
    if g.usuario is not None:
        favorito = any(f["id"] == inmueble_id for f in FavoritoDAO(db).de_usuario(g.usuario.id))
    return render_template(
        "publico/detalle.html", aviso=aviso, imagenes=ImagenDAO(db).de_inmueble(inmueble_id),
        servicios=InmuebleDAO(db).servicios(inmueble_id), evaluacion=detalle_evaluacion(db, inmueble_id),
        resenas=ResenaDAO(db).de_inmueble(inmueble_id), campus=campus_cercanos(aviso, CampusDAO(db).todos()),
        zona=analisis_red.contexto_distrito(db, aviso["ubigeo"]), historial=EvaluacionDAO(db).historial(inmueble_id),
        favorito=favorito)


@bp.route("/inmuebles/<int:inmueble_id>/ficha.pdf")
def ficha_pdf(inmueble_id: int):
    db = obtener_db()
    aviso = InmuebleDAO(db).detalle(inmueble_id)
    if aviso is None or aviso["estado"] not in ("publicado", "observado"):
        abort(404)
    return send_file(io.BytesIO(reportes.pdf_ficha_inmueble(db, inmueble_id)), mimetype="application/pdf",
                     download_name=f"ficha-inmueble-{inmueble_id}.pdf")


@bp.route("/media/<path:archivo>")
def media(archivo: str):
    return send_from_directory(Path(current_app.config["UPLOAD_IMAGENES"]), archivo)


@bp.route("/mapa")
def mapa():
    return render_template("publico/mapa.html")


@bp.route("/verificador", methods=["GET", "POST"])
def verificador():
    db = obtener_db()
    resultado = None
    if request.method == "POST":
        imagen = request.files.get("imagen")
        aviso = AvisoExterno(
            texto=request.form.get("texto", ""), precio_mensual=_decimal("precio_mensual"), area_m2=_decimal("area_m2"),
            tipo=request.form.get("tipo", "cuarto"), ubigeo=request.form.get("ubigeo") or None,
            telefono=request.form.get("telefono", ""), pide_pago_previo=bool(request.form.get("pide_pago_previo")),
            tiene_contrato=not request.form.get("sin_contrato"), permite_visita=not request.form.get("sin_visita"),
            imagen=imagen.read() if imagen and imagen.filename else None)
        try:
            resultado = verificar(db, aviso, g.usuario.id if g.usuario else None)
        except Exception:
            flash("No pudimos leer la imagen. Usa un archivo JPG, PNG o WEBP.", "error")
    return render_template("publico/verificador.html", resultado=resultado, distritos=DistritoDAO(db).todos())


@bp.route("/zonas")
def zonas():
    db = obtener_db()
    return render_template(
        "publico/zonas.html", zonas=analisis_red.ranking_zonas(db), periodo=analisis_red.ultimo_periodo(db),
        anual=analisis_red.resumen_anual_estafas(db), ciber=analisis_red.resumen_ciberdelitos(db),
        cpi=IndicadorDAO(db).serie("cpi_peru")[-6:])


@bp.route("/fuentes")
def fuentes():
    db = obtener_db()
    return render_template("publico/fuentes.html", fuentes=FuenteDAO(db).todas(), tipo_cambio=tipo_cambio_vigente(db),
                           ipc=IndicadorDAO(db).ultimo("ipc_lima"))


@bp.route("/contrato", methods=["GET", "POST"])
def contrato():
    analisis = None
    if request.method == "POST" and request.form.get("accion") == "analizar":
        texto = request.form.get("texto", "")
        if len(texto.strip()) < 40:
            flash("Pega el texto del contrato para analizarlo.", "error")
        else:
            analisis = analizar_clausulas(texto)
    elif request.method == "POST":
        pdf = reportes.pdf_contrato(request.form.to_dict())
        return send_file(io.BytesIO(pdf), mimetype="application/pdf", as_attachment=True,
                         download_name="contrato-modelo-depaseguro.pdf")
    return render_template("publico/contrato.html", analisis=analisis)


@bp.route("/blog")
def blog():
    return render_template("publico/blog.html", posts=BlogDAO(obtener_db()).listar())


@bp.route("/blog/<slug>")
def articulo(slug: str):
    post = BlogDAO(obtener_db()).por_slug(slug)
    if post is None:
        abort(404)
    return render_template("publico/articulo.html", post=post)


@bp.route("/nosotros")
def nosotros():
    return render_template("publico/nosotros.html")


@bp.route("/terminos")
def terminos():
    return render_template("publico/terminos.html")


@bp.route("/contacto", methods=["GET", "POST"])
def contacto():
    if request.method == "POST":
        nombre, correo = request.form.get("nombre", "").strip(), request.form.get("email", "").strip()
        mensaje = request.form.get("mensaje", "").strip()
        if len(nombre) < 3 or "@" not in correo or len(mensaje) < 10:
            flash("Completa tu nombre, correo y mensaje.", "error")
        else:
            ContactoDAO(obtener_db()).insertar({"nombre": nombre, "email": correo, "mensaje": mensaje})
            flash("Recibimos tu mensaje. Gracias por escribirnos.", "ok")
            return redirect(url_for("publico.contacto"))
    return render_template("publico/contacto.html")


@bp.app_errorhandler(ErrorNegocio)
def error_negocio(error: ErrorNegocio):
    flash(str(error), "error")
    return redirect(request.referrer or url_for("publico.inicio"))
