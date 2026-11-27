"""Registro, inicio y cierre de sesión."""
from __future__ import annotations

from flask import Blueprint, flash, g, redirect, render_template, request, session, url_for

from ..dao.base import obtener_db
from ..models.entidades import fabrica_usuario
from ..services.gestion import ErrorNegocio, autenticar, registrar_usuario
from .utilidades import demasiados_intentos, limpiar_intentos, registrar_intento

bp = Blueprint("auth", __name__)


def _destino_seguro(destino: str | None) -> str | None:
    """Solo acepta rutas internas para evitar redirecciones a sitios externos."""
    return destino if destino and destino.startswith("/") and not destino.startswith("//") else None


def _iniciar(fila: dict):
    token = session.get("csrf_token")
    session.clear()
    if token:
        session["csrf_token"] = token
    session["usuario_id"] = fila["id"]
    return fabrica_usuario(fila)


@bp.route("/registro", methods=["GET", "POST"])
def registro():
    if request.method == "POST":
        try:
            registrar_usuario(obtener_db(), request.form.to_dict())
        except ErrorNegocio as error:
            flash(str(error), "error")
            return render_template("auth/registro.html", datos=request.form), 400
        flash("Cuenta creada. Ya puedes iniciar sesión.", "ok")
        return redirect(url_for("auth.login"))
    return render_template("auth/registro.html", datos={"rol": request.args.get("rol", "estudiante")})


@bp.route("/login", methods=["GET", "POST"])
def login():
    if g.usuario is not None:
        return redirect(url_for(g.usuario.panel_inicio()))
    if request.method == "POST":
        clave_ip = request.remote_addr or "local"
        if demasiados_intentos(clave_ip):
            flash("Demasiados intentos. Espera unos minutos.", "error")
            return render_template("auth/login.html"), 429
        fila = autenticar(obtener_db(), request.form.get("email", ""), request.form.get("password", ""))
        if fila is None:
            registrar_intento(clave_ip)
            flash("Correo o contraseña incorrectos.", "error")
            return render_template("auth/login.html"), 401
        limpiar_intentos(clave_ip)
        usuario = _iniciar(fila)
        return redirect(_destino_seguro(request.args.get("siguiente")) or url_for(usuario.panel_inicio()))
    return render_template("auth/login.html")


@bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("Cerraste sesión.", "info")
    return redirect(url_for("publico.inicio"))
