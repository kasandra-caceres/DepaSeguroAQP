"""Crea datos de demostración claramente marcados. No representan personas ni inmuebles reales.

Uso:  python scripts/poblar_demo.py
"""
from __future__ import annotations

import io
import random
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PIL import Image, ImageDraw, ImageFilter  # noqa: E402
from werkzeug.security import generate_password_hash  # noqa: E402

from depaseguro import create_app  # noqa: E402
from depaseguro.dao.base import conectar  # noqa: E402
from depaseguro.dao.repositorios import ImagenDAO, InmuebleDAO, ListaContactosDAO  # noqa: E402
from depaseguro.services.analitica import analizar_imagen, sha256_bytes  # noqa: E402
from depaseguro.services.evaluador import EvaluadorInmueble, reevaluar_todos  # noqa: E402

CLAVE_DEMO = "Demo12345"  # credencial de prueba para sustentar el proyecto
PALETAS = [("#d9cdb8", "#8c6f56", "#4c6a7d"), ("#e6dfd2", "#6f7f6a", "#b9825a"), ("#cfd6d9", "#7a6a5d", "#c9a24b"),
           ("#e3d6c4", "#5d6f7e", "#a65a3a"), ("#dcd9cf", "#8a7b5e", "#577a64"), ("#e8dcc9", "#6e6459", "#3f6b8a")]

USUARIOS = [
    ("Administración DepaSeguro", "admin@depaseguro.test", "admin", None, None, None, 1),
    ("Lucía Demo Estudiante", "estudiante@depaseguro.test", "estudiante", "900000001", None, None, 1),
    ("Mateo Demo Estudiante", "estudiante2@depaseguro.test", "estudiante", "900000002", None, None, 1),
    ("Rosa Demo Propietaria", "rosa@depaseguro.test", "arrendador", "900000011", "DNI", "00000011", 1),
    ("Inmobiliaria Demo Sillar", "sillar@depaseguro.test", "arrendador", "900000012", "RUC", "20000000001", 1),
    ("Carlos Demo Arrendador", "carlos@depaseguro.test", "arrendador", "900000013", "DNI", "00000013", 1),
    ("Cuenta Demo Sospechosa A", "sospecha1@depaseguro.test", "arrendador", "900000091", "DNI", "00000091", 0),
    ("Cuenta Demo Sospechosa B", "sospecha2@depaseguro.test", "arrendador", "900000091", "DNI", "00000092", 0),
]

# dueño, título, tipo, ubigeo, dirección, lat, lon, área, precio, moneda, periodo, adelanto, garantía,
# pago previo, contrato, teléfono, foto, documentos aprobados, descripción
AVISOS = [
    ("rosa", "Cuarto amoblado a pasos de la UNSA", "cuarto", "040101", "Calle Demo 101", -16.4040, -71.5270, 14, 480, "PEN", "mes", 1, 1, 0, 1, "900000011", 0, 2,
     "Cuarto iluminado con escritorio, cerca de la avenida Venezuela. Se firma contrato y se muestra el recibo de luz."),
    ("rosa", "Minidepartamento en Yanahuara para estudiante", "minidepartamento", "040126", "Calle Demo 102", -16.3880, -71.5420, 28, 950, "PEN", "mes", 1, 1, 0, 1, "900000011", 1, 2,
     "Minidepartamento con cocina y baño propio. Visitas de lunes a sábado con cita previa."),
    ("rosa", "Habitación con baño privado cerca de Católica", "cuarto", "040101", "Calle Demo 103", -16.4070, -71.5460, 15, 560, "PEN", "mes", 1, 1, 0, 1, "900000011", 2, 2,
     "Habitación con baño privado y agua caliente, cerca de la Universidad Católica de Santa María."),
    ("sillar", "Pensión estudiantil con alimentos en Cercado", "pension", "040101", "Calle Demo 201", -16.4000, -71.5380, 13, 780, "PEN", "mes", 1, 1, 0, 1, "900000012", 3, 2,
     "Incluye desayuno y almuerzo de lunes a viernes. Contrato por semestre y comprobante de pago."),
    ("sillar", "Minidepartamento amoblado en Cayma", "minidepartamento", "040103", "Calle Demo 202", -16.3740, -71.5460, 32, 300, "USD", "mes", 1, 1, 0, 1, "900000012", 4, 2,
     "Unidad amoblada con lavandería común. El precio se publica en dólares y se puede pagar en soles."),
    ("sillar", "Departamento compartido en Cerro Colorado", "departamento", "040104", "Calle Demo 203", -16.3640, -71.5740, 55, 1300, "PEN", "mes", 1, 1, 0, 1, "900000012", 5, 2,
     "Departamento de dos dormitorios para estudiantes, cerca de transporte hacia el centro de la ciudad."),
    ("carlos", "Cuarto económico en Bustamante y Rivero", "cuarto", "040129", "Calle Demo 301", -16.4230, -71.5260, 12, 380, "PEN", "mes", 1, 1, 0, 1, "900000013", 6, 1,
     "Cuarto sencillo con internet incluido. Se muestra en persona y se firma contrato de seis meses."),
    ("carlos", "Cuarto con kitchenette en Sachaca", "cuarto", "040117", "Calle Demo 302", -16.4240, -71.5650, 16, 420, "PEN", "mes", 1, 1, 0, 1, "900000013", 7, 1,
     "Ambiente con kitchenette, cerca del óvalo. Servicios de agua y luz por consumo con recibo."),
    ("carlos", "Cuarto por semestre cerca de UTP", "cuarto", "040101", "Calle Demo 303", -16.4090, -71.5400, 14, 2880, "PEN", "semestre", 1, 1, 0, 1, "900000013", 8, 1,
     "Se paga por semestre académico con contrato. Muy cerca de la sede de la Universidad Tecnológica del Perú."),
    ("carlos", "Cuarto para estudiante en Paucarpata", "cuarto", "040112", "Calle Demo 304", -16.4300, -71.5050, 13, 350, "PEN", "mes", 1, 1, 0, 1, "900000013", 9, 0,
     "Cuarto con ventana al patio. Documentos en trámite, se puede visitar por la tarde."),
    ("carlos", "Cuarto luminoso en Miraflores", "cuarto", "040110", "Calle Demo 305", -16.3910, -71.5180, 13, 400, "PEN", "mes", 1, 1, 0, 1, "900000013", 10, 1,
     "Ambiente independiente con entrada propia, cerca de paraderos y mercados del distrito."),
    # Casos diseñados para demostrar la detección
    ("sospecha1", "Minidepartamento de lujo a precio de remate", "minidepartamento", "040126", "Calle Demo 901", -16.3890, -71.5440, 35, 300, "PEN", "mes", 2, 2, 1, 0, "900000091", 1, 0,
     "Solo hoy, último cuarto. Estoy de viaje, separa con Yape y te envío las llaves por courier. Hay muchos interesados."),
    ("sospecha2", "Cuarto cerca a UNSA oferta urgente", "cuarto", "040101", "Calle Demo 902", -16.4050, -71.5280, 14, 160, "PEN", "mes", 2, 1, 1, 0, "900000091", 0, 0,
     "Urgente, reserva ya con depósito. No hay visitas por ahora, el dueño no está, solo por WhatsApp."),
    ("sospecha2", "Habitación amoblada todo incluido", "cuarto", "040129", "Calle Demo 903", -16.4240, -71.5270, 15, 190, "PEN", "mes", 3, 2, 1, 0, "900000092", 11, 0,
     "Aprovecha ya esta habitación con todos los servicios. Deposita el adelanto hoy mismo para separarla."),
]


def foto_demo(indice: int, tamano=(960, 640)) -> bytes:
    """Dibuja una habitación sintética; así no se usa ninguna foto real ni con derechos de autor."""
    rng = random.Random(indice * 97 + 11)
    pared, piso, acento = PALETAS[indice % len(PALETAS)]
    ancho, alto = tamano
    imagen = Image.new("RGB", tamano, pared)
    dibujo = ImageDraw.Draw(imagen)
    horizonte = int(alto * rng.uniform(.58, .7))
    dibujo.rectangle([0, horizonte, ancho, alto], fill=piso)
    x = rng.randint(70, 520)
    dibujo.rectangle([x, 90, x + rng.randint(190, 300), 90 + rng.randint(140, 200)], fill="#bfdbe8", outline="#ffffff", width=9)
    cama_x = rng.randint(40, 420)
    cama_ancho = rng.randint(330, 450)
    dibujo.rounded_rectangle([cama_x, horizonte - 50, cama_x + cama_ancho, horizonte + 95], 18, fill=acento)
    dibujo.rounded_rectangle([cama_x + 15, horizonte - 86, cama_x + 118, horizonte - 34], 12, fill="#f4efe6")
    mesa_x = min(cama_x + cama_ancho + rng.randint(30, 70), ancho - 170)
    dibujo.rectangle([mesa_x, horizonte - 42, mesa_x + 140, horizonte - 26], fill="#5a4636")
    dibujo.rectangle([mesa_x + 10, horizonte - 26, mesa_x + 22, horizonte + 80], fill="#5a4636")
    dibujo.rectangle([mesa_x + 118, horizonte - 26, mesa_x + 130, horizonte + 80], fill="#5a4636")
    for _ in range(rng.randint(3, 6)):
        cx, cy = rng.randint(0, ancho), rng.randint(0, horizonte - 40)
        dibujo.ellipse([cx, cy, cx + rng.randint(30, 90), cy + rng.randint(30, 90)], fill=acento)
    imagen = imagen.filter(ImageFilter.GaussianBlur(.5))
    salida = io.BytesIO()
    imagen.save(salida, "JPEG", quality=86)
    return salida.getvalue()


def guardar_foto(db, app, inmueble_id: int, contenido: bytes) -> None:
    datos = analizar_imagen(contenido)
    nombre = f"{uuid.uuid4().hex[:20]}.jpg"
    (Path(app.config["UPLOAD_IMAGENES"]) / nombre).write_bytes(contenido)
    ImagenDAO(db).insertar({"inmueble_id": inmueble_id, "archivo": nombre, "sha256": datos["sha256"],
                            "dhash": datos["dhash"], "ancho": datos["ancho"], "alto": datos["alto"]})


def recomprimir(contenido: bytes) -> bytes:
    """Simula una foto robada: otro tamaño y compresión, misma escena."""
    imagen = Image.open(io.BytesIO(contenido)).resize((720, 480))
    salida = io.BytesIO()
    imagen.save(salida, "JPEG", quality=62)
    return salida.getvalue()


def guardar_documento(db, app, inmueble_id: int, tipo: str, estado: str, admin_id: int) -> None:
    contenido = f"DOCUMENTO DE DEMOSTRACION {inmueble_id} {tipo}".encode()
    nombre = f"{uuid.uuid4().hex[:20]}.pdf"
    (Path(app.config["UPLOAD_DOCUMENTOS"]) / nombre).write_bytes(contenido)
    db.execute(
        """INSERT INTO documentos(inmueble_id, tipo, archivo, sha256, estado, revisado_por, revisado_en)
           VALUES (?,?,?,?,?,?,datetime('now','localtime'))""",
        (inmueble_id, tipo, nombre, sha256_bytes(contenido), estado, admin_id if estado != "pendiente" else None))


def poblar_blog(db) -> None:
    articulos = [
        ("senales-de-una-estafa-de-alquiler", "7 señales de una estafa de alquiler",
         "Reconoce los patrones más comunes antes de transferir un adelanto.",
         "## Precio demasiado bajo\n\nCompara el aviso con otros del mismo distrito. Una gran diferencia merece más preguntas.\n\n"
         "## Te piden pagar antes de visitar\n\nNo envíes dinero por Yape, Plin o transferencia si no viste el lugar ni conociste a quien alquila.\n\n"
         "## Excusas para no mostrar el cuarto\n\nFrases como «estoy de viaje» o «te envío las llaves» son una alerta.\n\n"
         "## Presión para decidir\n\nDesconfía si te dicen que hay muchos interesados y debes pagar hoy.\n\n"
         "## Fotos que aparecen en varios avisos\n\nUsa el verificador para comparar la imagen con los avisos registrados.\n\n"
         "## No hay contrato\n\nSin un documento escrito es más difícil demostrar lo que acordaste.\n\n"
         "## Datos que no coinciden\n\nRevisa que nombre, dirección y número de cuenta sean coherentes."),
        ("antes-de-pagar-un-adelanto", "Qué revisar antes de pagar un adelanto",
         "Una lista práctica para tu primera visita.",
         "## Visita con alguien de confianza\n\nConoce el lugar en persona y prueba el agua, la luz y las cerraduras.\n\n"
         "## Pide un sustento\n\nSolicita un recibo de servicios o un documento que relacione a la persona con el inmueble. "
         "También puedes consultar la publicidad registral en SUNARP.\n\n"
         "## Deja todo por escrito\n\nAcuerda monto, plazo, garantía, servicios y forma de devolución.\n\n"
         "## Conserva comprobantes\n\nGuarda el contrato, los recibos y las conversaciones."),
        ("si-fuiste-victima", "Qué hacer si fuiste víctima de una estafa",
         "Actúa rápido para aumentar las posibilidades de recuperar tu dinero.",
         "## Reúne la evidencia\n\nGuarda capturas del aviso, chats, números de cuenta y comprobantes.\n\n"
         "## Avisa a tu banco o billetera\n\nComunícate cuanto antes con tu entidad para reportar la operación.\n\n"
         "## Presenta la denuncia\n\nAcude a una comisaría o al Ministerio Público con la evidencia. "
         "En DepaSeguro puedes descargar un expediente que ordena la información.\n\n"
         "## Reporta el aviso\n\nTu reporte ayuda a alertar a otros estudiantes."),
    ]
    db.executemany("INSERT OR IGNORE INTO blog_posts(slug, titulo, resumen, contenido) VALUES (?,?,?,?)", articulos)


def main() -> None:
    app = create_app({"TESTING": True, "GEOCODIFICAR": False})
    db = conectar(app.config["DB_PATH"])
    if db.execute("SELECT COUNT(*) FROM usuarios").fetchone()[0]:
        print("La base ya tiene datos. Borra data/depaseguro.db para volver a poblarla.")
        return
    ids = {}
    clave = generate_password_hash(CLAVE_DEMO)
    for nombre, correo, rol, telefono, tipo_doc, num_doc, verificado in USUARIOS:
        cursor = db.execute(
            """INSERT INTO usuarios(nombre, email, password_hash, rol, telefono, tipo_doc, num_doc, verificado, es_demo)
               VALUES (?,?,?,?,?,?,?,?,1)""",
            (nombre, correo, clave, rol, telefono, tipo_doc, num_doc, verificado))
        ids[correo.split("@")[0]] = cursor.lastrowid
    db.commit()
    alias = {"rosa": ids["rosa"], "sillar": ids["sillar"], "carlos": ids["carlos"],
             "sospecha1": ids["sospecha1"], "sospecha2": ids["sospecha2"]}
    admin_id = ids["admin"]
    fotos = {indice: foto_demo(indice) for indice in range(12)}
    inmuebles = InmuebleDAO(db)
    identificadores = []
    for (dueno, titulo, tipo, ubigeo, direccion, lat, lon, area, precio, moneda, periodo, adelanto, garantia,
         pago_previo, contrato, telefono, foto, documentos, descripcion) in AVISOS:
        nuevo = inmuebles.insertar({
            "arrendador_id": alias[dueno], "titulo": titulo, "descripcion": descripcion, "tipo": tipo, "ubigeo": ubigeo,
            "direccion": direccion, "lat": lat, "lon": lon, "area_m2": area, "precio": precio, "moneda": moneda,
            "periodo": periodo, "adelanto_meses": adelanto, "garantia_meses": garantia, "pago_previo_visita": pago_previo,
            "contrato_escrito": contrato, "telefono_contacto": telefono, "estado": "publicado", "es_demo": 1,
            "direccion_estado": "verificada"})
        identificadores.append(nuevo)
        robada = dueno.startswith("sospecha") and foto in (0, 1)
        guardar_foto(db, app, nuevo, recomprimir(fotos[foto]) if robada else fotos[foto])
        if not robada:
            guardar_foto(db, app, nuevo, foto_demo(foto + 40))
        if documentos >= 1:
            guardar_documento(db, app, nuevo, "titularidad", "aprobado", admin_id)
        if documentos >= 2:
            guardar_documento(db, app, nuevo, "recibo_servicio", "aprobado", admin_id)
        inmuebles.fijar_servicios(nuevo, random.Random(nuevo).sample(["Agua", "Luz", "Internet", "Amoblado", "Baño privado"], 3))
    db.commit()

    # Un aviso nuevo espera moderación y otro tiene un documento por revisar
    inmuebles.actualizar(identificadores[9], {"estado": "pendiente"})
    guardar_documento(db, app, identificadores[9], "recibo_servicio", "pendiente", admin_id)

    resenas = [(0, "estudiante", 5, "La dueña mostró el recibo y firmamos contrato. El cuarto es como en las fotos.", 1),
               (0, "estudiante2", 4, "Buena ubicación y trato claro. El agua caliente funciona bien.", 1),
               (3, "estudiante", 5, "Cumplen con los alimentos y entregan comprobante cada mes.", 1),
               (1, "estudiante2", 4, "Visité el minidepartamento y coincide con el aviso publicado.", 1)]
    for indice, autor, puntaje, comentario, verificada in resenas:
        db.execute("INSERT INTO resenas(inmueble_id, estudiante_id, puntaje, comentario, verificada) VALUES (?,?,?,?,?)",
                   (identificadores[indice], ids[autor], puntaje, comentario, verificada))
    reporte = db.execute(
        """INSERT INTO reportes(inmueble_id, reportante_id, motivo, detalle, telefono_reportado, monto_perdido, estado, resolucion, resuelto_en)
           VALUES (?,?,?,?,?,?,?,?,datetime('now','localtime'))""",
        (identificadores[12], ids["estudiante"], "cobro_indebido",
         "Caso de demostración: se pidió un depósito para separar el cuarto y luego la cuenta dejó de responder.",
         "900000091", 300, "confirmado", "Caso ficticio usado para demostrar el flujo de moderación.")).lastrowid
    ListaContactosDAO(db).insertar({"telefono": "900000091", "motivo": "Caso ficticio de demostración", "reporte_id": reporte})
    db.execute(
        """INSERT INTO reportes(inmueble_id, reportante_id, motivo, detalle, monto_perdido) VALUES (?,?,?,?,?)""",
        (identificadores[13], ids["estudiante2"], "fotos_falsas",
         "Caso de demostración: las fotos del aviso no coinciden con el lugar que me describieron.", 0))
    campus = db.execute("SELECT id FROM campus LIMIT 1").fetchone()
    if campus:
        db.execute("INSERT INTO busquedas_guardadas(usuario_id, campus_id, radio_km, precio_max, trust_min) VALUES (?,?,?,?,?)",
                   (ids["estudiante"], campus["id"], 2, 800, 60))
    db.execute("INSERT INTO favoritos(usuario_id, inmueble_id) VALUES (?,?)", (ids["estudiante"], identificadores[0]))
    poblar_blog(db)
    db.commit()

    reevaluar_todos(db)
    evaluador = EvaluadorInmueble(db)
    for identificador in identificadores:
        evaluador.evaluar(identificador)
    print(f"Listo: {len(identificadores)} avisos de demostración. Clave de prueba en scripts/poblar_demo.py.")
    db.close()


if __name__ == "__main__":
    main()
