"""Datos de prueba compartidos. Cada prueba usa una base temporal independiente."""
from __future__ import annotations

import io
import re

import pytest
from PIL import Image, ImageDraw
from werkzeug.security import generate_password_hash

from depaseguro import create_app
from depaseguro.dao.base import conectar
from depaseguro.dao.repositorios import ImagenDAO, InmuebleDAO
from depaseguro.services.analitica import analizar_imagen
from depaseguro.services.evaluador import EvaluadorInmueble
from depaseguro.web import utilidades

CLAVE = "Prueba123"


@pytest.fixture()
def app(tmp_path):
    utilidades._intentos.clear()
    aplicacion = create_app({"TESTING": True, "DATA_DIR": tmp_path, "INGESTA_AUTOMATICA": False,
                             "GEOCODIFICAR": False, "SECRET_KEY": "pruebas"})
    return aplicacion


@pytest.fixture()
def db(app):
    conexion = conectar(app.config["DB_PATH"])
    yield conexion
    conexion.close()


@pytest.fixture()
def cliente(app):
    return app.test_client()


def crear_usuario(db, correo: str, rol: str = "arrendador", verificado: int = 1) -> int:
    cursor = db.execute(
        "INSERT INTO usuarios(nombre, email, password_hash, rol, verificado) VALUES (?,?,?,?,?)",
        (correo.split("@")[0].title() + " Prueba", correo, generate_password_hash(CLAVE), rol, verificado))
    db.commit()
    return cursor.lastrowid


def crear_aviso(db, arrendador_id: int, **cambios) -> int:
    datos = {
        "arrendador_id": arrendador_id, "titulo": "Cuarto de prueba", "descripcion": "Cuarto ordenado con contrato y visita.",
        "tipo": "cuarto", "ubigeo": "040101", "direccion": "Calle Falsa 123", "lat": -16.40, "lon": -71.53, "area_m2": 15,
        "precio": 450, "moneda": "PEN", "periodo": "mes", "adelanto_meses": 1, "garantia_meses": 1,
        "pago_previo_visita": 0, "contrato_escrito": 1, "telefono_contacto": "987654321", "estado": "publicado",
        "direccion_estado": "verificada",
    }
    datos.update(cambios)
    return InmuebleDAO(db).insertar(datos)


def foto(semilla: int = 1, tamano=(320, 240)) -> bytes:
    imagen = Image.new("RGB", tamano, (240, 230, 210))
    dibujo = ImageDraw.Draw(imagen)
    for indice in range(8):
        x = (semilla * 53 + indice * 37) % tamano[0]
        y = (semilla * 29 + indice * 61) % tamano[1]
        color = (semilla * 40 % 255, indice * 30 % 255, (semilla + indice) * 20 % 255)
        dibujo.ellipse([x, y, x + 70, y + 70], fill=color)
    salida = io.BytesIO()
    imagen.save(salida, "JPEG", quality=92)
    return salida.getvalue()


def agregar_foto(db, inmueble_id: int, contenido: bytes) -> None:
    datos = analizar_imagen(contenido)
    ImagenDAO(db).insertar({"inmueble_id": inmueble_id, "archivo": f"f{inmueble_id}.jpg", "sha256": datos["sha256"],
                            "dhash": datos["dhash"], "ancho": datos["ancho"], "alto": datos["alto"]})


def evaluar(db, inmueble_id: int):
    return EvaluadorInmueble(db).evaluar(inmueble_id)


def token(cliente, ruta: str = "/login") -> str:
    html = cliente.get(ruta).get_data(as_text=True)
    return re.search(r'name="csrf_token" value="([^"]+)"', html).group(1)


def ingresar(cliente, correo: str) -> None:
    respuesta = cliente.post("/login", data={"email": correo, "password": CLAVE, "csrf_token": token(cliente)})
    assert respuesta.status_code == 302
