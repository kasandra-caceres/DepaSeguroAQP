"""Sesión, permisos, protección CSRF y filtros compartidos por las vistas."""
from __future__ import annotations

import hmac
import secrets
import time
from collections import defaultdict
from functools import wraps

from flask import abort, flash, g, redirect, request, session, url_for

from ..dao.base import obtener_db
from ..dao.repositorios import AlertaDAO, UsuarioDAO
from ..models.entidades import fabrica_usuario
from ..services.gestion import MOTIVOS, TIPOS

_intentos: dict[str, list[float]] = defaultdict(list)
MAX_INTENTOS, VENTANA_SEGUNDOS = 6, 300


def preparar_peticion() -> None:
    """Carga al usuario actual y valida el token CSRF en cada envío de formulario."""
    g.usuario = None
    identificador = session.get("usuario_id")
    if identificador:
        fila = UsuarioDAO(obtener_db()).obtener(identificador)
        if fila and fila["activo"]:
            g.usuario = fabrica_usuario(fila)
        else:
            session.clear()
    if request.method == "POST":
        enviado = request.form.get("csrf_token", "") or request.headers.get("X-CSRF-Token", "")
        if not hmac.compare_digest(enviado, session.get("csrf_token", "-")):
            abort(403)


def token_csrf() -> str:
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_hex(24)
    return session["csrf_token"]


def requiere_rol(*roles: str):
    """Decorador de acceso. Es una función de orden superior que envuelve la vista."""

    def decorador(vista):
        @wraps(vista)
        def envuelta(*args, **kwargs):
            if g.usuario is None:
                flash("Inicia sesión para continuar.", "info")
                return redirect(url_for("auth.login", siguiente=request.path))
            if g.usuario.rol not in roles:
                abort(403)
            return vista(*args, **kwargs)

        return envuelta

    return decorador


def demasiados_intentos(clave: str) -> bool:
    """Limita intentos de acceso por dirección IP en una ventana de tiempo."""
    ahora = time.time()
    _intentos[clave] = [t for t in _intentos[clave] if ahora - t < VENTANA_SEGUNDOS]
    return len(_intentos[clave]) >= MAX_INTENTOS


def registrar_intento(clave: str) -> None:
    _intentos[clave].append(time.time())


def limpiar_intentos(clave: str) -> None:
    _intentos.pop(clave, None)


def clase_nivel(nivel: str | None) -> str:
    return {"Confiable": "n-ok", "Precaución": "n-medio", "Riesgo alto": "n-alto", "Crítico": "n-critico"}.get(nivel or "", "n-nd")


def registrar_filtros(app) -> None:
    app.jinja_env.globals.update(TIPOS=TIPOS, MOTIVOS=MOTIVOS)
    app.jinja_env.filters["nivel"] = clase_nivel
    app.jinja_env.filters["soles"] = lambda v: "S/ -" if v is None else f"S/ {v:,.0f}"
    app.jinja_env.filters["soles2"] = lambda v: "S/ -" if v is None else f"S/ {v:,.2f}"
    app.jinja_env.filters["titulo"] = lambda v: (v or "").title().replace(" Y ", " y ").replace(" De ", " de ")
    app.jinja_env.filters["fecha"] = lambda v: (v or "")[:16]

    @app.context_processor
    def globales():
        sin_leer = 0
        if g.get("usuario") is not None:
            sin_leer = AlertaDAO(obtener_db()).sin_leer(g.usuario.id)
        return {"usuario": g.get("usuario"), "csrf_token": token_csrf, "alertas_sin_leer": sin_leer}
