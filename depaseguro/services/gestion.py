"""Casos de uso que modifican datos: cuentas, avisos, reseñas, reportes y moderación."""
from __future__ import annotations

import re
import secrets
import threading
import uuid
from datetime import datetime
from pathlib import Path

from flask import current_app
from werkzeug.security import check_password_hash, generate_password_hash

from ..dao.base import conectar
from ..dao.repositorios import (AlertaDAO, AuditoriaDAO, CodigoVisitaDAO, DescargoDAO, DocumentoDAO, ImagenDAO,
                                InmuebleDAO, ListaContactosDAO, ReporteDAO, ResenaDAO, UsuarioDAO)
from .analitica import (analizar_imagen, dni_valido, normalizar_telefono, ruc_valido, sha256_bytes,
                        telefono_valido)
from .evaluador import EvaluadorInmueble

SERVICIOS = ("Agua", "Luz", "Internet", "Gas", "Lavandería", "Cocina compartida", "Baño privado", "Amoblado")
TIPOS = {"cuarto": "Cuarto", "minidepartamento": "Minidepartamento", "departamento": "Departamento",
         "pension": "Pensión con alimentos"}
MOTIVOS = {"inexistente": "El inmueble no existe", "fotos_falsas": "Fotos falsas o copiadas",
           "cobro_indebido": "Cobro indebido", "suplantacion": "Suplantación del dueño",
           "condiciones_abusivas": "Condiciones abusivas", "otro": "Otro motivo"}
EXTENSIONES_DOCUMENTO = {".pdf", ".jpg", ".jpeg", ".png"}


class ErrorNegocio(ValueError):
    """Error de validación que se muestra tal cual al usuario."""


def _exigir(condicion: bool, mensaje: str) -> None:
    if not condicion:
        raise ErrorNegocio(mensaje)


def _numero(valor, campo: str, minimo: float = 0) -> float:
    try:
        numero = float(str(valor).replace(",", "."))
    except (TypeError, ValueError):
        raise ErrorNegocio(f"{campo} debe ser un número.") from None
    _exigir(numero >= minimo, f"{campo} debe ser mayor o igual a {minimo:g}.")
    return numero


# --- Cuentas -------------------------------------------------------------------
def registrar_usuario(db, datos: dict) -> int:
    email = datos.get("email", "").strip().lower()
    clave = datos.get("password", "")
    rol = datos.get("rol", "estudiante")
    _exigir(len(datos.get("nombre", "").strip()) >= 3, "Escribe tu nombre completo.")
    _exigir(bool(re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email)), "El correo no es válido.")
    _exigir(len(clave) >= 8 and re.search(r"\d", clave) and re.search(r"[A-Za-z]", clave),
            "La contraseña debe tener al menos 8 caracteres, con letras y números.")
    _exigir(rol in ("estudiante", "arrendador"), "Rol no permitido.")
    usuarios = UsuarioDAO(db)
    _exigir(usuarios.por_email(email) is None, "Ya existe una cuenta con ese correo.")
    tipo_doc, num_doc = datos.get("tipo_doc") or None, (datos.get("num_doc") or "").strip() or None
    if rol == "arrendador":
        _exigir(tipo_doc in ("DNI", "RUC"), "Indica tu DNI o RUC.")
        valido = dni_valido(num_doc) if tipo_doc == "DNI" else ruc_valido(num_doc)
        _exigir(valido, f"El {tipo_doc} no tiene un formato válido.")
    telefono = normalizar_telefono(datos.get("telefono", ""))
    if telefono:
        _exigir(telefono_valido(telefono), "Escribe un celular de 9 dígitos.")
    identificador = usuarios.insertar({
        "nombre": datos["nombre"].strip(), "email": email, "password_hash": generate_password_hash(clave),
        "rol": rol, "telefono": telefono or None, "tipo_doc": tipo_doc, "num_doc": num_doc})
    AuditoriaDAO(db).registrar(identificador, "registro", "usuario", identificador)
    return identificador


def autenticar(db, email: str, clave: str) -> dict | None:
    usuario = UsuarioDAO(db).por_email(email or "")
    if usuario and usuario["activo"] and check_password_hash(usuario["password_hash"], clave or ""):
        return usuario
    return None


# --- Avisos --------------------------------------------------------------------
def _validar_aviso(formulario) -> dict:
    titulo = formulario.get("titulo", "").strip()
    descripcion = formulario.get("descripcion", "").strip()
    telefono = normalizar_telefono(formulario.get("telefono_contacto", ""))
    _exigir(len(titulo) >= 8, "El título debe tener al menos 8 caracteres.")
    _exigir(len(descripcion) >= 30, "La descripción debe tener al menos 30 caracteres.")
    _exigir(formulario.get("tipo") in TIPOS, "Elige un tipo de inmueble.")
    _exigir(bool(formulario.get("ubigeo")), "Elige un distrito.")
    _exigir(len(formulario.get("direccion", "").strip()) >= 6, "Escribe la dirección.")
    _exigir(telefono_valido(telefono), "Escribe un celular de contacto de 9 dígitos.")
    _exigir(formulario.get("moneda") in ("PEN", "USD"), "Moneda no válida.")
    _exigir(formulario.get("periodo") in ("semana", "mes", "semestre", "anio"), "Periodo no válido.")
    lat, lon = formulario.get("lat") or None, formulario.get("lon") or None
    return {
        "titulo": titulo, "descripcion": descripcion, "tipo": formulario["tipo"], "ubigeo": formulario["ubigeo"],
        "direccion": formulario["direccion"].strip(), "telefono_contacto": telefono,
        "lat": float(lat) if lat else None, "lon": float(lon) if lon else None,
        "area_m2": _numero(formulario.get("area_m2"), "El área", 4),
        "precio": _numero(formulario.get("precio"), "El precio", 1),
        "moneda": formulario["moneda"], "periodo": formulario["periodo"],
        "adelanto_meses": _numero(formulario.get("adelanto_meses", 1), "El adelanto"),
        "garantia_meses": _numero(formulario.get("garantia_meses", 1), "La garantía"),
        "pago_previo_visita": 1 if formulario.get("pago_previo_visita") else 0,
        "contrato_escrito": 1 if formulario.get("contrato_escrito") else 0,
    }


def guardar_imagen(db, inmueble_id: int, contenido: bytes) -> None:
    try:
        datos = analizar_imagen(contenido)
    except ErrorNegocio:
        raise
    except Exception:
        raise ErrorNegocio("Uno de los archivos no es una imagen JPG, PNG o WEBP válida.") from None
    extension = {"JPEG": ".jpg", "PNG": ".png", "WEBP": ".webp"}[datos["formato"]]
    nombre = f"{uuid.uuid4().hex[:20]}{extension}"
    (Path(current_app.config["UPLOAD_IMAGENES"]) / nombre).write_bytes(contenido)
    ImagenDAO(db).insertar({"inmueble_id": inmueble_id, "archivo": nombre, "sha256": datos["sha256"],
                            "dhash": datos["dhash"], "ancho": datos["ancho"], "alto": datos["alto"]})


def guardar_documento(db, inmueble_id: int, tipo: str, archivo) -> None:
    _exigir(tipo in ("titularidad", "recibo_servicio", "identidad"), "Tipo de documento no válido.")
    extension = Path(archivo.filename or "").suffix.lower()
    _exigir(extension in EXTENSIONES_DOCUMENTO, "El documento debe ser PDF, JPG o PNG.")
    contenido = archivo.read()
    _exigir(bool(contenido), "El documento está vacío.")
    nombre = f"{uuid.uuid4().hex[:20]}{extension}"
    (Path(current_app.config["UPLOAD_DOCUMENTOS"]) / nombre).write_bytes(contenido)
    DocumentoDAO(db).insertar({"inmueble_id": inmueble_id, "tipo": tipo, "archivo": nombre,
                               "sha256": sha256_bytes(contenido)})


def crear_aviso(db, arrendador_id: int, formulario, servicios: list[str], imagenes: list) -> int:
    datos = _validar_aviso(formulario)
    inmuebles = InmuebleDAO(db)
    identificador = inmuebles.insertar({**datos, "arrendador_id": arrendador_id, "estado": "pendiente"})
    inmuebles.fijar_servicios(identificador, [s for s in servicios if s in SERVICIOS])
    for archivo in imagenes:
        if archivo and archivo.filename:
            guardar_imagen(db, identificador, archivo.read())
    AuditoriaDAO(db).registrar(arrendador_id, "crear", "inmueble", identificador)
    EvaluadorInmueble(db).evaluar(identificador)
    verificar_direccion_en_segundo_plano(identificador)
    return identificador


def editar_aviso(db, inmueble_id: int, usuario_id: int, formulario, servicios: list[str], imagenes: list) -> None:
    inmuebles = InmuebleDAO(db)
    actual = inmuebles.obtener(inmueble_id)
    _exigir(actual is not None and actual["arrendador_id"] == usuario_id, "No puedes editar este aviso.")
    datos = _validar_aviso(formulario)
    if datos["direccion"] != actual["direccion"] or datos["ubigeo"] != actual["ubigeo"]:
        datos["direccion_estado"] = "sin_verificar"
    datos["actualizado_en"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    inmuebles.actualizar(inmueble_id, datos)
    inmuebles.fijar_servicios(inmueble_id, [s for s in servicios if s in SERVICIOS])
    for archivo in imagenes:
        if archivo and archivo.filename:
            guardar_imagen(db, inmueble_id, archivo.read())
    AuditoriaDAO(db).registrar(usuario_id, "editar", "inmueble", inmueble_id)
    EvaluadorInmueble(db).evaluar(inmueble_id)
    if datos.get("direccion_estado") == "sin_verificar":
        verificar_direccion_en_segundo_plano(inmueble_id)


def eliminar_aviso(db, inmueble_id: int, usuario_id: int) -> None:
    inmuebles = InmuebleDAO(db)
    actual = inmuebles.obtener(inmueble_id)
    _exigir(actual is not None and actual["arrendador_id"] == usuario_id, "No puedes eliminar este aviso.")
    inmuebles.actualizar(inmueble_id, {"estado": "retirado"})
    AuditoriaDAO(db).registrar(usuario_id, "retirar", "inmueble", inmueble_id)


def verificar_direccion_en_segundo_plano(inmueble_id: int) -> None:
    """Consulta OpenStreetMap sin hacer esperar al usuario."""
    if not current_app.config.get("GEOCODIFICAR", True) or current_app.config.get("TESTING"):
        return
    ruta = current_app.config["DB_PATH"]

    def tarea() -> None:
        from ..ingestion.fuentes import FuenteOpenStreetMap

        conexion = conectar(ruta)
        try:
            FuenteOpenStreetMap(conexion).ejecutar()
            EvaluadorInmueble(conexion).evaluar(inmueble_id)
        finally:
            conexion.close()

    threading.Thread(target=tarea, daemon=True).start()


def generar_codigo_visita(db, inmueble_id: int, usuario_id: int) -> str:
    aviso = InmuebleDAO(db).obtener(inmueble_id)
    _exigir(aviso is not None and aviso["arrendador_id"] == usuario_id, "No puedes generar este código.")
    codigo = secrets.token_hex(3).upper()
    CodigoVisitaDAO(db).insertar({"inmueble_id": inmueble_id, "codigo": codigo})
    return codigo


# --- Comunidad -----------------------------------------------------------------
def registrar_resena(db, inmueble_id: int, estudiante_id: int, puntaje, comentario: str, codigo: str = "") -> bool:
    valor = int(_numero(puntaje, "El puntaje", 1))
    _exigir(1 <= valor <= 5, "El puntaje va de 1 a 5.")
    _exigir(len(comentario.strip()) >= 15, "Cuenta tu experiencia en al menos 15 caracteres.")
    resenas = ResenaDAO(db)
    _exigir(resenas.contar("inmueble_id = ? AND estudiante_id = ?", (inmueble_id, estudiante_id)) == 0,
            "Ya dejaste una reseña en este aviso.")
    verificada = False
    if codigo.strip():
        codigos = CodigoVisitaDAO(db)
        registro = codigos.por_codigo(codigo)
        _exigir(registro is not None and registro["inmueble_id"] == inmueble_id and registro["usado_por"] is None,
                "El código de visita no es válido o ya fue usado.")
        codigos.actualizar(registro["id"], {"usado_por": estudiante_id,
                                            "usado_en": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
        verificada = True
    resenas.insertar({"inmueble_id": inmueble_id, "estudiante_id": estudiante_id, "puntaje": valor,
                      "comentario": comentario.strip(), "verificada": int(verificada)})
    EvaluadorInmueble(db).evaluar(inmueble_id)
    return verificada


def registrar_reporte(db, inmueble_id: int, usuario_id: int, datos: dict) -> int:
    _exigir(datos.get("motivo") in MOTIVOS, "Elige un motivo.")
    _exigir(len(datos.get("detalle", "").strip()) >= 20, "Describe lo ocurrido en al menos 20 caracteres.")
    reportes = ReporteDAO(db)
    identificador = reportes.insertar({
        "inmueble_id": inmueble_id, "reportante_id": usuario_id, "motivo": datos["motivo"],
        "detalle": datos["detalle"].strip(),
        "telefono_reportado": normalizar_telefono(datos.get("telefono_reportado", "")) or None,
        "monto_perdido": _numero(datos.get("monto_perdido") or 0, "El monto")})
    AlertaDAO(db).registrar("reporte_nuevo", "alta", f"Nuevo reporte #{identificador}: {MOTIVOS[datos['motivo']]}.",
                            inmueble_id=inmueble_id, clave=f"reporte:{identificador}")
    AuditoriaDAO(db).registrar(usuario_id, "reportar", "reporte", identificador)
    EvaluadorInmueble(db).evaluar(inmueble_id)
    return identificador


def responder_reporte(db, reporte_id: int, arrendador_id: int, texto: str) -> None:
    reporte = ReporteDAO(db).con_detalle("r.id = ?", (reporte_id,))
    _exigir(bool(reporte) and reporte[0]["arrendador_id"] == arrendador_id, "No puedes responder este reporte.")
    _exigir(len(texto.strip()) >= 15, "Escribe tu descargo con más detalle.")
    DescargoDAO(db).insertar({"reporte_id": reporte_id, "arrendador_id": arrendador_id, "texto": texto.strip()})
    AlertaDAO(db).registrar("descargo", "media", f"El arrendador respondió el reporte #{reporte_id}.",
                            inmueble_id=reporte[0]["inmueble_id"], clave=f"descargo:{reporte_id}")


# --- Moderación ----------------------------------------------------------------
def resolver_reporte(db, reporte_id: int, admin_id: int, estado: str, resolucion: str) -> None:
    _exigir(estado in ("en_revision", "confirmado", "descartado"), "Estado no válido.")
    reportes = ReporteDAO(db)
    reporte = reportes.obtener(reporte_id)
    _exigir(reporte is not None, "El reporte no existe.")
    reportes.actualizar(reporte_id, {"estado": estado, "resolucion": resolucion.strip() or None,
                                     "resuelto_en": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
    if estado == "confirmado":
        aviso = InmuebleDAO(db).obtener(reporte["inmueble_id"]) if reporte["inmueble_id"] else None
        telefono = reporte["telefono_reportado"] or (aviso["telefono_contacto"] if aviso else None)
        if telefono and not ListaContactosDAO(db).contiene(telefono):
            ListaContactosDAO(db).insertar({"telefono": telefono, "reporte_id": reporte_id,
                                            "motivo": MOTIVOS[reporte["motivo"]]})
        _reevaluar_mismo_telefono(db, telefono)
    AuditoriaDAO(db).registrar(admin_id, f"reporte_{estado}", "reporte", reporte_id, resolucion)
    if reporte["inmueble_id"]:
        EvaluadorInmueble(db).evaluar(reporte["inmueble_id"])


def _reevaluar_mismo_telefono(db, telefono: str | None) -> None:
    if not telefono:
        return
    evaluador = EvaluadorInmueble(db)
    for fila in db.execute("SELECT id FROM inmuebles WHERE telefono_contacto = ?", (telefono,)).fetchall():
        evaluador.evaluar(fila["id"])


def revisar_documento(db, documento_id: int, admin_id: int, estado: str, observacion: str = "") -> None:
    _exigir(estado in ("aprobado", "rechazado"), "Estado no válido.")
    documentos = DocumentoDAO(db)
    documento = documentos.obtener(documento_id)
    _exigir(documento is not None, "El documento no existe.")
    documentos.actualizar(documento_id, {
        "estado": estado, "observacion": observacion.strip() or None, "revisado_por": admin_id,
        "revisado_en": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
    AuditoriaDAO(db).registrar(admin_id, f"documento_{estado}", "documento", documento_id, observacion)
    EvaluadorInmueble(db).evaluar(documento["inmueble_id"])


def cambiar_estado_aviso(db, inmueble_id: int, admin_id: int, estado: str) -> None:
    _exigir(estado in ("publicado", "observado", "rechazado", "pendiente"), "Estado no válido.")
    InmuebleDAO(db).actualizar(inmueble_id, {"estado": estado})
    AuditoriaDAO(db).registrar(admin_id, f"aviso_{estado}", "inmueble", inmueble_id)
    EvaluadorInmueble(db).evaluar(inmueble_id)


def cambiar_usuario(db, usuario_id: int, admin_id: int, cambios: dict) -> None:
    permitidos = {clave: int(valor) for clave, valor in cambios.items() if clave in ("verificado", "activo")}
    _exigir(bool(permitidos), "Sin cambios.")
    _exigir(not (usuario_id == admin_id and permitidos.get("activo") == 0), "No puedes desactivar tu propia cuenta.")
    UsuarioDAO(db).actualizar(usuario_id, permitidos)
    AuditoriaDAO(db).registrar(admin_id, "actualizar_usuario", "usuario", usuario_id, str(permitidos))
    evaluador = EvaluadorInmueble(db)
    for fila in db.execute("SELECT id FROM inmuebles WHERE arrendador_id = ?", (usuario_id,)).fetchall():
        evaluador.evaluar(fila["id"])
