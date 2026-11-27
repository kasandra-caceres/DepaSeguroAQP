"""Panel de administración: moderación, usuarios, fuentes y reportes."""
from __future__ import annotations

import io
from pathlib import Path

from flask import (Blueprint, current_app, flash, g, redirect, render_template, request, send_file,
                   send_from_directory, url_for)

from ..dao.base import obtener_db
from ..dao.repositorios import (AlertaDAO, AuditoriaDAO, ContactoDAO, DescargoDAO, DocumentoDAO, FuenteDAO,
                                InmuebleDAO, ListaContactosDAO, ReporteDAO, UsuarioDAO)
from ..ingestion.planificador import ejecutar_ingesta
from ..services import reportes
from ..services.analisis_red import detectar_redes
from ..services.analitica import normalizar_telefono, telefono_valido
from ..services.evaluador import reevaluar_todos
from ..services.gestion import (ErrorNegocio, cambiar_estado_aviso, cambiar_usuario, resolver_reporte,
                                revisar_documento)
from .utilidades import requiere_rol

bp = Blueprint("admin", __name__, url_prefix="/admin")


@bp.route("/")
@requiere_rol("admin")
def panel():
    db = obtener_db()
    return render_template("admin/panel.html", indicadores=reportes.indicadores_panel(db),
                           alertas=AlertaDAO(db).globales(12), fuentes=FuenteDAO(db).todas())


@bp.route("/avisos")
@requiere_rol("admin")
def avisos():
    return render_template("admin/avisos.html", avisos=InmuebleDAO(obtener_db()).todos_detalle())


@bp.route("/avisos/<int:inmueble_id>/estado", methods=["POST"])
@requiere_rol("admin")
def estado_aviso(inmueble_id: int):
    cambiar_estado_aviso(obtener_db(), inmueble_id, g.usuario.id, request.form.get("estado", ""))
    flash("Estado actualizado.", "ok")
    return redirect(request.referrer or url_for("admin.avisos"))


@bp.route("/documentos")
@requiere_rol("admin")
def documentos():
    return render_template("admin/documentos.html", documentos=DocumentoDAO(obtener_db()).pendientes())


@bp.route("/documentos/<int:documento_id>", methods=["POST"])
@requiere_rol("admin")
def revisar(documento_id: int):
    revisar_documento(obtener_db(), documento_id, g.usuario.id, request.form.get("estado", ""),
                      request.form.get("observacion", ""))
    flash("Documento revisado y aviso recalculado.", "ok")
    return redirect(url_for("admin.documentos"))


@bp.route("/documentos/archivo/<path:archivo>")
@requiere_rol("admin")
def archivo_documento(archivo: str):
    return send_from_directory(Path(current_app.config["UPLOAD_DOCUMENTOS"]), archivo)


@bp.route("/reportes")
@requiere_rol("admin")
def lista_reportes():
    db = obtener_db()
    casos = ReporteDAO(db).con_detalle()
    for caso in casos:
        caso["descargos"] = DescargoDAO(db).de_reporte(caso["id"])
    return render_template("admin/reportes.html", reportes=casos)


@bp.route("/reportes/<int:reporte_id>", methods=["POST"])
@requiere_rol("admin")
def resolver(reporte_id: int):
    resolver_reporte(obtener_db(), reporte_id, g.usuario.id, request.form.get("estado", ""),
                     request.form.get("resolucion", ""))
    flash("Reporte actualizado.", "ok")
    return redirect(url_for("admin.lista_reportes"))


@bp.route("/usuarios")
@requiere_rol("admin")
def usuarios():
    return render_template("admin/usuarios.html", usuarios=UsuarioDAO(obtener_db()).listar())


@bp.route("/usuarios/<int:usuario_id>", methods=["POST"])
@requiere_rol("admin")
def actualizar_usuario(usuario_id: int):
    cambiar_usuario(obtener_db(), usuario_id, g.usuario.id, {request.form["campo"]: request.form["valor"]})
    flash("Usuario actualizado.", "ok")
    return redirect(url_for("admin.usuarios"))


@bp.route("/contactos-riesgo", methods=["GET", "POST"])
@requiere_rol("admin")
def lista():
    db = obtener_db()
    dao = ListaContactosDAO(db)
    if request.method == "POST":
        telefono = normalizar_telefono(request.form.get("telefono", ""))
        if not telefono_valido(telefono):
            raise ErrorNegocio("Escribe un celular de 9 dígitos.")
        if not dao.contiene(telefono):
            dao.insertar({"telefono": telefono, "motivo": request.form.get("motivo", "").strip() or "Registro manual"})
            AuditoriaDAO(db).registrar(g.usuario.id, "agregar_contacto", "lista_contactos", detalle=telefono)
            reevaluar_todos(db, notificar=True)
        return redirect(url_for("admin.lista"))
    return render_template("admin/lista.html", contactos=dao.listar())


@bp.route("/contactos-riesgo/<int:contacto_id>/eliminar", methods=["POST"])
@requiere_rol("admin")
def quitar_contacto(contacto_id: int):
    db = obtener_db()
    ListaContactosDAO(db).eliminar(contacto_id)
    AuditoriaDAO(db).registrar(g.usuario.id, "quitar_contacto", "lista_contactos", contacto_id)
    reevaluar_todos(db)
    return redirect(url_for("admin.lista"))


@bp.route("/redes")
@requiere_rol("admin")
def redes():
    return render_template("admin/redes.html", redes=detectar_redes(obtener_db()))


@bp.route("/alertas")
@requiere_rol("admin")
def alertas():
    return render_template("admin/alertas.html", alertas=AlertaDAO(obtener_db()).globales(300))


@bp.route("/fuentes", methods=["GET", "POST"])
@requiere_rol("admin")
def fuentes():
    db = obtener_db()
    if request.method == "POST":
        resultados = ejecutar_ingesta(db, request.form.get("clave") or None)
        AuditoriaDAO(db).registrar(g.usuario.id, "ejecutar_ingesta", "fuentes_datos")
        fallidas = [r["fuente"] for r in resultados if r["estado"] == "error"]
        flash(f"Lectura terminada con errores en: {', '.join(fallidas)}." if fallidas
              else "Lectura de fuentes terminada.", "error" if fallidas else "ok")
        return redirect(url_for("admin.fuentes"))
    historial = [dict(f) for f in db.execute("SELECT * FROM ingestas ORDER BY id DESC LIMIT 30")]
    return render_template("admin/fuentes.html", fuentes=FuenteDAO(db).todas(), historial=historial)


@bp.route("/auditoria")
@requiere_rol("admin")
def auditoria():
    db = obtener_db()
    return render_template("admin/auditoria.html", eventos=AuditoriaDAO(db).recientes(),
                           contactos=ContactoDAO(db).listar(limite=30))


@bp.route("/exportar/<formato>")
@requiere_rol("admin")
def exportar(formato: str):
    db = obtener_db()
    salidas = {
        "distritos.pdf": (reportes.pdf_riesgo_distritos, "application/pdf"),
        "catalogo.xlsx": (reportes.excel_catalogo,
                          "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
        "alertas.csv": (reportes.csv_alertas, "text/csv; charset=utf-8"),
    }
    if formato not in salidas:
        return redirect(url_for("admin.panel"))
    funcion, tipo = salidas[formato]
    return send_file(io.BytesIO(funcion(db)), mimetype=tipo, as_attachment=True, download_name=f"depaseguro-{formato}")
