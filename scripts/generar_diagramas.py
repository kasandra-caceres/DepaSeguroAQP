"""Genera los diagramas del informe con Python (matplotlib). El modelo físico se lee de la base real."""
from __future__ import annotations

import sqlite3
import textwrap
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Circle, FancyBboxPatch, Polygon, Rectangle  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
SALIDA = RAIZ / "docs" / "diagramas"
TINTA, TERRA, VERDE, AZUL, ARENA, GRIS = "#22303c", "#b4532a", "#dbe9df", "#dfe8ef", "#f4efe6", "#66717a"
plt.rcParams["font.family"] = "DejaVu Sans"


def lienzo(ancho: float, alto: float):
    figura, ejes = plt.subplots(figsize=(ancho, alto))
    ejes.set_xlim(0, ancho)
    ejes.set_ylim(0, alto)
    ejes.axis("off")
    return figura, ejes


def guardar(figura, nombre: str) -> None:
    figura.savefig(SALIDA / f"{nombre}.png", dpi=170, bbox_inches="tight", facecolor="white")
    plt.close(figura)


def caja(e, x, y, w, h, texto="", color="white", borde=TINTA, tam=8, redondo=True, negrita=False):
    estilo = "round,pad=0,rounding_size=0.08" if redondo else "square,pad=0"
    e.add_patch(FancyBboxPatch((x, y), w, h, boxstyle=estilo, fc=color, ec=borde, lw=1.1, zorder=2))
    if texto:
        e.text(x + w / 2, y + h / 2, texto, ha="center", va="center", fontsize=tam, color=TINTA, zorder=3,
               fontweight="bold" if negrita else "normal", linespacing=1.15)


def flecha(e, puntos, texto=None, tam=7, color=TINTA, punteada=False):
    for inicio, fin in zip(puntos[:-2], puntos[1:-1]):
        e.plot([inicio[0], fin[0]], [inicio[1], fin[1]], color=color, lw=1, zorder=1, ls="--" if punteada else "-")
    e.annotate("", xy=puntos[-1], xytext=puntos[-2], zorder=1,
               arrowprops=dict(arrowstyle="-|>", color=color, lw=1, ls="--" if punteada else "-", shrinkA=0, shrinkB=0))
    if texto:
        a, b = puntos[(len(puntos) - 1) // 2], puntos[(len(puntos) - 1) // 2 + 1]
        e.text((a[0] + b[0]) / 2 + .06, (a[1] + b[1]) / 2 + .06, texto, fontsize=tam, color=color, zorder=4,
               bbox=dict(fc="white", ec="none", pad=.6, alpha=.85))


def evento(e, x, y, fin=False):
    e.add_patch(Circle((x, y), .17, fc="white", ec=TINTA, lw=2.4 if fin else 1.1, zorder=2))


def compuerta(e, x, y, texto="", abajo=False):
    e.add_patch(Polygon([(x - .26, y), (x, y + .26), (x + .26, y), (x, y - .26)], fc="#fff3d6", ec=TINTA, lw=1.1, zorder=2))
    e.text(x, y, "×", ha="center", va="center", fontsize=10, zorder=3)
    if texto:
        e.text(x, y - .42 if abajo else y + .33, texto, ha="center", fontsize=7, zorder=3)


def carriles(e, ancho, nombres, alto):
    for indice, nombre in enumerate(nombres):
        y = alto * (len(nombres) - indice - 1)
        e.add_patch(Rectangle((0, y), ancho, alto, fc="white" if indice % 2 else "#fbf8f2", ec=TINTA, lw=1, zorder=0))
        e.add_patch(Rectangle((0, y), .42, alto, fc=ARENA, ec=TINTA, lw=1, zorder=0))
        e.text(.21, y + alto / 2, nombre, rotation=90, ha="center", va="center", fontsize=8, fontweight="bold")


def bpmn_actual():
    f, e = lienzo(12, 5.2)
    carriles(e, 12, ["Estudiante", "Anunciante"], 2.6)
    evento(e, .8, 3.9)
    caja(e, 1.2, 3.5, 1.5, .8, "Busca cuarto en\nredes o carteles", AZUL)
    caja(e, 3.1, 3.5, 1.5, .8, "Contacta por\nWhatsApp", AZUL)
    caja(e, 3.1, .9, 1.5, .8, "Envía fotos y pide\nadelanto", ARENA)
    compuerta(e, 5.4, 3.9, "¿Puede visitar?")
    caja(e, 6.3, 3.5, 1.4, .8, "Transfiere\nsin verificar", "#f6d9cf")
    caja(e, 8, .9, 1.6, .8, "Deja de responder o\nimpone condiciones", ARENA)
    caja(e, 8, 3.5, 1.7, .8, "Descubre el engaño\ny pierde dinero", "#f6d9cf")
    caja(e, 10, 3.5, 1.3, .8, "Busca de nuevo\nsin evidencia", AZUL)
    evento(e, 11.65, 3.9, True)
    flecha(e, [(.97, 3.9), (1.2, 3.9)])
    flecha(e, [(2.7, 3.9), (3.1, 3.9)])
    flecha(e, [(3.85, 3.5), (3.85, 1.7)])
    flecha(e, [(4.6, 1.3), (5.4, 1.3), (5.4, 3.64)])
    flecha(e, [(5.66, 3.9), (6.3, 3.9)], "no")
    flecha(e, [(7.7, 3.7), (7.85, 3.7), (7.85, 1.3), (8, 1.3)])
    flecha(e, [(8.8, 1.7), (8.8, 3.5)])
    flecha(e, [(9.7, 3.9), (10, 3.9)])
    flecha(e, [(11.3, 3.9), (11.48, 3.9)])
    guardar(f, "bpmn_actual")


def bpmn_propuesto():
    f, e = lienzo(14, 8)
    carriles(e, 14, ["Arrendador", "Backend Python", "Moderación", "Estudiante"], 2)
    y1, y2, y3, y4 = 7, 5, 3, 1
    evento(e, .8, y1)
    caja(e, 1.2, y1 - .4, 1.6, .8, "Registra aviso,\nfotos y documentos", AZUL)
    caja(e, 3.2, y2 - .4, 1.6, .8, "Normaliza precio\ny huellas de fotos", VERDE)
    caja(e, 5.2, y2 - .4, 1.7, .8, "Ejecuta detectores\ny reglas lógicas", VERDE)
    caja(e, 7.3, y2 - .4, 1.6, .8, "Calcula\nTrust Score", VERDE)
    compuerta(e, 9.5, y2, "¿Riesgo alto?")
    caja(e, 8.7, y3 - .4, 1.6, .8, "Revisa documentos\ny alertas", ARENA)
    compuerta(e, 11, y3, "¿Aprueba?", abajo=True)
    caja(e, 11.7, y2 - .4, 1.6, .8, "Publica aviso\ny notifica", VERDE)
    caja(e, 11.7, y1 - .4, 1.6, .8, "Corrige o presenta\ndescargo", AZUL)
    caja(e, 11.7, y4 - .4, 1.6, .8, "Busca, compara\ny decide", "#f6e3c8")
    caja(e, 9.2, y4 - .4, 1.7, .8, "Reporta y obtiene\nexpediente", "#f6e3c8")
    evento(e, 13.65, y4, True)
    flecha(e, [(.97, y1), (1.2, y1)])
    flecha(e, [(2.8, y1), (4, y1), (4, y2 + .4)])
    flecha(e, [(4.8, y2), (5.2, y2)])
    flecha(e, [(6.9, y2), (7.3, y2)])
    flecha(e, [(8.9, y2), (9.24, y2)])
    flecha(e, [(9.5, y2 - .26), (9.5, y3 + .4)], "sí")
    flecha(e, [(9.76, y2), (11.7, y2)], "no")
    flecha(e, [(10.3, y3), (10.74, y3)])
    flecha(e, [(11.26, y3), (12.1, y3), (12.1, y2 - .4)], "sí")
    flecha(e, [(11, y3 + .26), (11, y1), (11.7, y1)], "no")
    flecha(e, [(12.9, y2 - .4), (12.9, y4 + .4)])
    flecha(e, [(13.3, y4), (13.48, y4)])
    flecha(e, [(11.7, y4), (10.9, y4)])
    e.text(11.3, y4 - .62, "si hay problema", ha="center", fontsize=7)
    flecha(e, [(9.5, y4 + .4), (9.5, y3 - .4)])
    guardar(f, "bpmn_propuesto")


def bpmn_ingesta():
    f, e = lienzo(12.5, 4)
    carriles(e, 12.5, ["Planificador Python", "Fuentes externas"], 2)
    y1, y2 = 3, 1
    evento(e, .8, y1)
    caja(e, 1.2, y1 - .4, 1.5, .8, "Revisa si pasaron\n24 horas", VERDE)
    caja(e, 3, y2 - .4, 1.7, .8, "BCRP, MININTER, MPFN,\nSUNEDU, Wikidata,\nTI, OSM", AZUL, tam=7)
    caja(e, 3, y1 - .4, 1.7, .8, "Consulta catálogo\ny descarga datos", VERDE)
    compuerta(e, 5.3, y1, "¿Hay cambios?")
    caja(e, 6, y1 - .4, 1.5, .8, "Transforma con\npandas y guarda", VERDE)
    caja(e, 7.9, y1 - .4, 1.5, .8, "Recalcula precios\ny Trust Score", VERDE)
    caja(e, 9.8, y1 - .4, 1.5, .8, "Genera alertas\nde zona", VERDE)
    evento(e, 11.8, y1, True)
    flecha(e, [(.97, y1), (1.2, y1)])
    flecha(e, [(2.7, y1), (3, y1)])
    flecha(e, [(3.85, y1 - .4), (3.85, y2 + .4)], "HTTP")
    flecha(e, [(4.7, y1), (5.04, y1)])
    flecha(e, [(5.56, y1), (6, y1)], "sí")
    flecha(e, [(7.5, y1), (7.9, y1)])
    flecha(e, [(9.4, y1), (9.8, y1)])
    flecha(e, [(11.3, y1), (11.63, y1)])
    flecha(e, [(5.3, y1 - .26), (5.3, 2.1), (8.65, 2.1), (8.65, y1 - .4)], "no: registra sin cambios")
    guardar(f, "bpmn_ingesta")


def actor(e, x, y, nombre):
    e.add_patch(Circle((x, y + .32), .12, fc="white", ec=TINTA, lw=1.1))
    e.plot([x, x], [y + .2, y - .1], color=TINTA, lw=1.1)
    e.plot([x - .18, x + .18], [y + .1, y + .1], color=TINTA, lw=1.1)
    e.plot([x, x - .15], [y - .1, y - .35], color=TINTA, lw=1.1)
    e.plot([x, x + .15], [y - .1, y - .35], color=TINTA, lw=1.1)
    e.text(x, y - .5, nombre, ha="center", fontsize=8, fontweight="bold")


def casos_uso():
    from matplotlib.patches import Ellipse

    f, e = lienzo(13, 9)
    e.add_patch(Rectangle((2.2, .2), 8.6, 8.6, fc="#fbf8f2", ec=TINTA, lw=1.1))
    e.text(6.5, 8.55, "DepaSeguro AQP", ha="center", fontsize=10, fontweight="bold")
    actores = {"Estudiante": (1, 6.8), "Arrendador": (1, 2.4), "Moderador": (12, 6.4), "Planificador": (12, 1.8)}
    for nombre, (x, y) in actores.items():
        actor(e, x, y, nombre)
    casos = [
        ("CU01 Buscar por campus", 3.9, 7.9, "Estudiante"), ("CU02 Consultar Trust Score", 3.9, 7.1, "Estudiante"),
        ("CU03 Verificar aviso externo", 3.9, 6.3, "Estudiante"), ("CU04 Registrar reseña", 3.9, 5.5, "Estudiante"),
        ("CU05 Reportar y descargar\nexpediente", 3.9, 4.7, "Estudiante"), ("CU06 Publicar aviso", 3.9, 3.6, "Arrendador"),
        ("CU07 Cargar documentos", 3.9, 2.8, "Arrendador"), ("CU08 Generar código de visita", 3.9, 2.0, "Arrendador"),
        ("CU09 Presentar descargo", 3.9, 1.2, "Arrendador"), ("CU10 Moderar avisos\ny documentos", 8.9, 7.6, "Moderador"),
        ("CU11 Resolver reportes", 8.9, 6.7, "Moderador"), ("CU12 Revisar redes de cuentas", 8.9, 5.8, "Moderador"),
        ("CU13 Exportar reportes", 8.9, 4.9, "Moderador"), ("CU14 Leer fuentes oficiales", 8.9, 2.9, "Planificador"),
        ("CU15 Generar alertas", 8.9, 1.8, "Planificador"),
    ]
    for texto, x, y, nombre in casos:
        e.add_patch(Ellipse((x, y), 2.7, .68, fc="white", ec=TINTA, lw=1, zorder=2))
        e.text(x, y, texto, ha="center", va="center", fontsize=7.2, zorder=3)
        ax, ay = actores[nombre]
        desde = (ax + .25, ay + .1) if ax < 6 else (ax - .25, ay + .1)
        hasta = (x - 1.35, y) if ax < 6 else (x + 1.35, y)
        e.plot([desde[0], hasta[0]], [desde[1], hasta[1]], color=GRIS, lw=.8, zorder=1)
    e.add_patch(Ellipse((6.4, 4), 2.1, .7, fc=VERDE, ec=TINTA, lw=1, zorder=2))
    e.text(6.4, 4, "Calcular Trust Score", ha="center", va="center", fontsize=7.2, zorder=3)
    for x, y in ((5.2, 3.6), (7.6, 2.9), (7.55, 6.7)):
        flecha(e, [(x, y), (6.4 + (-1 if x < 6.4 else 1), 4.05)], color=GRIS, punteada=True)
    e.text(6.4, 3.4, "«include»", ha="center", fontsize=7, color=GRIS)
    guardar(f, "casos_uso")


def clase(e, x, y, w, nombre, atributos, metodos, color=AZUL, tam=6.8):
    linea = .17
    alto_a, alto_m = linea * len(atributos) + .08, linea * len(metodos) + .08
    alto_n = .3
    total = alto_n + alto_a + alto_m
    caja(e, x, y - alto_n, w, alto_n, nombre, color, redondo=False, tam=tam + .7, negrita=True)
    caja(e, x, y - alto_n - alto_a, w, alto_a, "", "white", redondo=False)
    caja(e, x, y - total, w, alto_m, "", "white", redondo=False)
    for i, texto in enumerate(atributos):
        e.text(x + .06, y - alto_n - .13 - i * linea, texto, fontsize=tam, va="center", zorder=4)
    for i, texto in enumerate(metodos):
        e.text(x + .06, y - alto_n - alto_a - .13 - i * linea, texto, fontsize=tam, va="center", zorder=4)
    return {"x": x, "y": y, "w": w, "h": total}


def herencia(e, hija, padre):
    x1, y1 = hija["x"] + hija["w"] / 2, hija["y"]
    x2, y2 = padre["x"] + padre["w"] / 2, padre["y"] - padre["h"]
    medio = y2 - .22
    e.plot([x1, x1, x2, x2], [y1, medio, medio, y2 - .14], color=TINTA, lw=1, zorder=1)
    e.add_patch(Polygon([(x2 - .1, y2 - .14), (x2 + .1, y2 - .14), (x2, y2)], fc="white", ec=TINTA, lw=1, zorder=2))


def clases():
    f, e = lienzo(15, 10.2)
    usuario = clase(e, 1.7, 10, 2.5, "«abstract» Usuario", ["id, nombre, email", "verificado, activo"], ["permisos()", "panel_inicio()", "puede(permiso)"])
    hijas = [clase(e, x, 8.2, 1.75, n, ["rol"], ["permisos()", "panel_inicio()"]) for x, n in ((.1, "Estudiante"), (2.05, "Arrendador"), (4, "Administrador"))]
    for hija in hijas:
        herencia(e, hija, usuario)
    detector = clase(e, 8, 10, 2.6, "«abstract» Detector", [], ["evaluar(contexto): list[Hallazgo]"], VERDE)
    nombres = ["DetectorPrecio", "DetectorImagenes", "DetectorContacto", "DetectorDocumentos", "DetectorCondiciones", "DetectorTexto", "DetectorUbicacion", "DetectorReportes"]
    x = 6.3
    for i, nombre in enumerate(nombres[:4]):
        h = clase(e, x + i * 2.17, 8.75, 2.05, nombre, [], ["evaluar(contexto)"], VERDE)
        herencia(e, h, detector)
    for i, nombre in enumerate(nombres[4:]):
        clase(e, x + i * 2.17, 7.75, 2.05, nombre, [], ["evaluar(contexto)"], VERDE)
    fuente = clase(e, .1, 6.2, 3.1, "«abstract» FuenteDatos", ["clave, nombre, entidad, categoria"], ["ejecutar(): dict", "obtener()", "cargar(crudo): int", "huella(crudo): str"], "#f6e3c8")
    nombres = ["FuenteBCRP", "FuenteDenuncias", "FuenteCiberdelitos", "FuenteSunedu", "FuenteWikidata", "FuenteTransparencia", "FuenteOpenStreetMap"]
    for i, nombre in enumerate(nombres):
        fila, columna = divmod(i, 2)
        clase(e, .1 + columna * 1.75, 4.2 - fila * .78, 1.65, nombre, [], ["obtener()", "cargar()"], "#f6e3c8", tam=6.2)
    e.plot([1.65, 1.65], [4.2, 4.42], color=TINTA, lw=1)
    e.add_patch(Polygon([(1.55, 4.42), (1.75, 4.42), (1.65, 4.56)], fc="white", ec=TINTA, lw=1))
    evaluador = clase(e, 4.3, 6.2, 3.1, "EvaluadorInmueble «Facade»", ["db, inmuebles"], ["construir_contexto(id)", "evaluar(id): ResultadoEvaluacion"], "#efe0ea")
    base = clase(e, 8, 6.2, 3, "BaseConocimiento", ["_clausulas"], ["agregar_hecho(functor, args)", "consultar(meta): list", "cumple(meta): bool"], "#efe0ea")
    dao = clase(e, 11.5, 6.2, 3.2, "BaseDAO «DAO»", ["tabla, clave, db"], ["obtener(id)", "listar()", "insertar(datos)", "actualizar(id, datos)", "eliminar(id)"], "#e5e3f2")
    nombres = ["UsuarioDAO", "InmuebleDAO", "ReporteDAO", "AlertaDAO", "FuenteDAO"]
    for i, nombre in enumerate(nombres):
        clase(e, 11.5 + (i % 2) * 1.65, 3.85 - (i // 2) * .55, 1.55, nombre, [], [], "#e5e3f2", tam=6)
    e.plot([13.1, 13.1], [3.85, 4.1], color=TINTA, lw=1)
    e.add_patch(Polygon([(13, 4.1), (13.2, 4.1), (13.1, 4.24)], fc="white", ec=TINTA, lw=1))
    resultado = clase(e, 4.3, 3.9, 3.1, "ResultadoEvaluacion «DTO»", ["trust_score, nivel", "componentes, hallazgos", "patrones, recomendaciones"], [], "#efe0ea")
    contexto = clase(e, 8, 3.9, 3, "ContextoEvaluacion", ["inmueble, imagenes, documentos", "duplicados_imagen, z_precio", "reportes_abiertos, resenas"], [], "#efe0ea")
    hallazgo = clase(e, 4.3, 2.1, 3.1, "Hallazgo «frozen»", ["hecho, severidad", "titulo, detalle"], [], "#efe0ea")
    flecha(e, [(7.4, 5.6), (8, 5.6)], "usa")
    flecha(e, [(5.85, evaluador["y"] - evaluador["h"]), (5.85, 3.9)], "crea")
    flecha(e, [(7.4, 4.75), (7.7, 4.75), (7.7, 3.6), (8, 3.6)], "usa")
    flecha(e, [(5.85, resultado["y"] - resultado["h"]), (5.85, 2.1)], "1..*")
    flecha(e, [(6.6, 6.2), (6.6, 6.72), (7.2, 6.72), (7.2, 7.25)], "ejecuta", color=GRIS, punteada=True)
    e.text(10.6, 6.75, "Los ocho detectores heredan de Detector", ha="center", fontsize=7, color=GRIS)
    guardar(f, "clases")


def entidad_relacion():
    f, e = lienzo(14, 9.4)
    entidades = {
        "USUARIOS": (6, 8.3), "DISTRITOS": (1, 5.7), "INMUEBLES": (6, 5.7), "IMAGENES": (10.8, 8.3), "DOCUMENTOS": (11.2, 6.9),
        "SERVICIOS": (11.2, 5.5), "RESENAS": (11.2, 4.1), "CODIGOS_VISITA": (11.2, 2.7), "REPORTES": (6, 3.2), "DESCARGOS": (2.6, 3.2),
        "LISTA_CONTACTOS": (6, 1.1), "ALERTAS": (9.1, 1), "EVALUACIONES": (2.6, 1.1), "CAMPUS": (.3, 8.3),
        "BUSQUEDAS_GUARDADAS": (2.9, 8.3), "DENUNCIAS_DISTRITO": (.5, 3.2), "FAVORITOS": (8.8, 7.2),
    }
    ancho, alto = 2.05, .62
    centro = {n: (x + ancho / 2, y + alto / 2) for n, (x, y) in entidades.items()}
    relaciones = [("USUARIOS", "INMUEBLES", "1", "N"), ("DISTRITOS", "INMUEBLES", "1", "N"), ("INMUEBLES", "IMAGENES", "1", "N"),
                  ("INMUEBLES", "DOCUMENTOS", "1", "N"), ("INMUEBLES", "SERVICIOS", "N", "M"), ("INMUEBLES", "RESENAS", "1", "N"),
                  ("INMUEBLES", "CODIGOS_VISITA", "1", "N"), ("INMUEBLES", "REPORTES", "1", "N"), ("REPORTES", "DESCARGOS", "1", "N"),
                  ("REPORTES", "LISTA_CONTACTOS", "1", "0..1"), ("INMUEBLES", "ALERTAS", "1", "N"), ("INMUEBLES", "EVALUACIONES", "1", "N"),
                  ("CAMPUS", "BUSQUEDAS_GUARDADAS", "1", "N"), ("USUARIOS", "BUSQUEDAS_GUARDADAS", "1", "N"),
                  ("DISTRITOS", "DENUNCIAS_DISTRITO", "1", "N"), ("USUARIOS", "FAVORITOS", "1", "N"), ("INMUEBLES", "FAVORITOS", "1", "N")]
    for a, b, ca, cb in relaciones:
        (x1, y1), (x2, y2) = centro[a], centro[b]
        e.plot([x1, x2], [y1, y2], color=GRIS, lw=1, zorder=1)
        distancia = abs(x2 - x1)
        t = .24 if y1 != y2 or distancia > 3.2 else (ancho / 2 + .12) / distancia
        e.text(x1 + (x2 - x1) * t, y1 + (y2 - y1) * t, ca, fontsize=7.5, color=TERRA, zorder=4, backgroundcolor="white")
        e.text(x1 + (x2 - x1) * (1 - t), y1 + (y2 - y1) * (1 - t), cb, fontsize=7.5, color=TERRA, zorder=4, backgroundcolor="white")
    for nombre, (x, y) in entidades.items():
        caja(e, x, y, ancho, alto, nombre, AZUL if nombre in ("USUARIOS", "INMUEBLES", "REPORTES") else "white", tam=7.2, negrita=True)
    guardar(f, "entidad_relacion")


def modelo_fisico():
    """Dibuja las tablas reales de la base en tres láminas legibles."""
    bd = sqlite3.connect(RAIZ / "data" / "depaseguro.db")
    tablas = [f[0] for f in bd.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
    columnas_por_fila, ancho_caja, linea = 3, 2.75, .17
    datos = []
    for tabla in tablas:
        foraneas = {f[3] for f in bd.execute(f"PRAGMA foreign_key_list({tabla})")}
        filas = []
        for columna in bd.execute(f"PRAGMA table_info({tabla})"):
            marca = "PK " if columna[5] else ("FK " if columna[1] in foraneas else "   ")
            filas.append(f"{marca}{columna[1]} {columna[2] or ''}"[:36])
        datos.append((tabla, filas))
    datos.sort(key=lambda d: len(d[1]))
    laminas = [datos[0::3], datos[1::3], datos[2::3]]
    for numero, lamina in enumerate(laminas, 1):
        grupos = [lamina[i:i + columnas_por_fila] for i in range(0, len(lamina), columnas_por_fila)]
        altos = [max(len(f) for _t, f in g) * linea + .6 for g in grupos]
        total = sum(altos) + .1
        figura, e = lienzo(columnas_por_fila * (ancho_caja + .15), total)
        y = total
        for grupo, alto in zip(grupos, altos):
            for i, (tabla, filas) in enumerate(grupo):
                x = i * (ancho_caja + .15)
                caja(e, x, y - .3, ancho_caja, .27, tabla, AZUL, redondo=False, tam=8, negrita=True)
                caja(e, x, y - .3 - len(filas) * linea - .06, ancho_caja, len(filas) * linea + .06, "", "white", redondo=False)
                for j, texto in enumerate(filas):
                    e.text(x + .05, y - .4 - j * linea, texto, fontsize=7, family="DejaVu Sans Mono", va="center", zorder=4)
            y -= alto
        guardar(figura, f"modelo_fisico_{numero}")


def arquitectura():
    f, e = lienzo(13, 8)
    capas = [
        (6.55, 1.25, "#f6e3c8", "PRESENTACIÓN (Vista)", ["Plantillas Jinja2", "CSS / JavaScript", "Leaflet + OpenStreetMap", "Chart.js"]),
        (5.0, 1.25, AZUL, "CONTROLADORES (Flask Blueprints)", ["publico", "auth", "estudiante", "arrendador", "admin", "api"]),
        (3.45, 1.25, VERDE, "LÓGICA DE NEGOCIO (100 % Python)", ["Evaluador (Facade)", "Detectores (Strategy)", "Motor lógico", "Eventos (Observer)", "Reportes"]),
        (1.9, 1.25, "#efe0ea", "ACCESO A DATOS (DAO / DTO)", ["BaseDAO", "DAOs por entidad", "Entidades POO", "DTO inmutables"]),
    ]
    for y, alto, color, titulo, partes in capas:
        caja(e, .2, y, 9.3, alto, "", color)
        e.text(.4, y + alto - .22, titulo, fontsize=8.5, fontweight="bold", zorder=4)
        ancho = 8.9 / len(partes)
        for i, parte in enumerate(partes):
            caja(e, .4 + i * ancho, y + .15, ancho - .12, .65, parte, "white", tam=7.5)
    caja(e, .2, .35, 4.5, 1.25, "SQLite\n27 tablas, una vista e índices", "#e5e3f2", tam=9)
    caja(e, 5, .35, 4.5, 1.25, "Archivos\nimágenes, documentos,\nPDF, Excel y CSV", "#e5e3f2", tam=9)
    caja(e, 10, 3.45, 2.8, 4.35, "", ARENA)
    e.text(11.4, 7.5, "INGESTA AUTOMÁTICA", ha="center", fontsize=8.5, fontweight="bold", zorder=4)
    fuentes = ["BCRP (Estado)", "MININTER (Estado)", "Ministerio Público (Estado)", "SUNEDU (Estado)", "OpenStreetMap (ONG)", "Wikidata (ONG)", "Transparency Int. (ONG)"]
    for i, fuente in enumerate(fuentes):
        caja(e, 10.2, 6.85 - i * .5, 2.4, .4, fuente, "white", tam=7)
    caja(e, 10, 1.9, 2.8, 1.25, "Planificador\ncada 24 horas\n(Template Method)", VERDE, tam=8)
    flecha(e, [(11.4, 3.45), (11.4, 3.15)])
    flecha(e, [(10, 2.5), (9.5, 2.5)])
    for x in (2.4, 7.2):
        flecha(e, [(x, 1.9), (x, 1.6)])
    for y in (6.55, 5, 3.45):
        flecha(e, [(4.8, y), (4.8, y - .3)])
    guardar(f, "arquitectura")


def paquetes():
    arbol = """DepaSeguroAQP/
├── run.py                     Punto de entrada
├── requirements.txt           Dependencias
├── database/schema.sql        Modelo físico
├── depaseguro/
│   ├── __init__.py            Fábrica de la aplicación
│   ├── config.py              Parámetros
│   ├── models/entidades.py    Clases y DTO
│   ├── dao/                   Conexión y repositorios
│   ├── functional/            Programación funcional
│   ├── logic/                 Motor y reglas Prolog
│   ├── services/              Reglas de negocio y reportes
│   ├── ingestion/             Fuentes y planificador
│   ├── web/                   Controladores Flask
│   ├── templates/             Vistas HTML
│   └── static/                CSS, JS, imágenes y video
├── scripts/                   Demo, diagramas y documentos
├── tests/                     Pruebas pytest
└── docs/                      Capturas, diagramas y Pydoc"""
    f, e = lienzo(8.2, 4.75)
    e.add_patch(Rectangle((0, 0), 8.2, 4.75, fc="#fbf8f2", ec=TINTA, lw=1))
    e.text(.2, 4.6, arbol, family="DejaVu Sans Mono", fontsize=9.2, va="top", linespacing=1.32)
    guardar(f, "paquetes")


def wbs():
    f, e = lienzo(14, 5.4)
    caja(e, 5, 4.6, 4, .6, "1. DepaSeguro AQP", "#f6e3c8", tam=10, negrita=True)
    ramas = [
        ("1.1 Inicio", ["Selección del problema", "Aprobación docente", "Alcance"]),
        ("1.2 Análisis", ["Contexto y BPMN", "Requisitos SRS", "Fuentes de datos"]),
        ("1.3 Diseño", ["Casos de uso", "Clases y BD", "Mockups UX/UI"]),
        ("1.4 Construcción", ["Backend Python", "Frontend web", "Persistencia", "Ingesta automática"]),
        ("1.5 Pruebas", ["Unitarias", "Integración", "Navegador real"]),
        ("1.6 Cierre", ["Informe y manual", "Presentación", "Sustentación"]),
    ]
    ancho = 14 / len(ramas)
    for i, (nombre, hijos) in enumerate(ramas):
        x = i * ancho + .12
        caja(e, x, 3.3, ancho - .24, .6, nombre, AZUL, tam=8.5, negrita=True)
        e.plot([7, 7, x + (ancho - .24) / 2, x + (ancho - .24) / 2], [4.6, 4.2, 4.2, 3.9], color=TINTA, lw=1, zorder=1)
        for j, hijo in enumerate(hijos):
            caja(e, x + .12, 2.45 - j * .66, ancho - .48, .52, hijo, "white", tam=7.5)
    guardar(f, "wbs")


def gantt():
    tareas = [("Selección y aprobación del tema", 11, 12), ("Análisis del contexto y BPMN", 12, 13), ("Requisitos SRS y casos de uso", 12, 13),
              ("Diseño de clases y base de datos", 13, 14), ("Mockups UX/UI", 13, 14), ("Backend y persistencia", 13, 15),
              ("Lectura automática de fuentes", 14, 15), ("Frontend web", 14, 16), ("Reportes y alertas", 15, 16),
              ("Avance del 40 % en GitHub", 15, 15.5), ("Pruebas y correcciones", 15, 17), ("Informe, manual y presentación", 16, 17), ("Entrega y sustentación final", 17, 17.6)]
    figura, ejes = plt.subplots(figsize=(11, 4.8))
    for i, (nombre, inicio, fin) in enumerate(reversed(tareas)):
        ejes.barh(i, fin - inicio, left=inicio, color=TERRA if "Sustentación" in nombre or "Avance" in nombre else TINTA, height=.55)
    ejes.set_yticks(range(len(tareas)), [t[0] for t in reversed(tareas)], fontsize=8.5)
    ejes.set_xticks(range(11, 19), [f"S{n}" for n in range(11, 19)], fontsize=8.5)
    ejes.set_xlim(11, 18)
    ejes.grid(axis="x", color="#ddd")
    ejes.set_axisbelow(True)
    ejes.spines[["top", "right"]].set_visible(False)
    ejes.set_xlabel("Semana del curso", fontsize=9)
    guardar(figura, "gantt")


def organigrama():
    f, e = lienzo(8, 3)
    caja(e, 2.7, 2.2, 2.6, .65, "Docente asesor\nRene Alonso Nieto Valencia", ARENA, tam=8)
    caja(e, .5, .6, 3.1, .85, "Kasandra Cáceres Quispe\nLíder del proyecto", AZUL, tam=8)
    caja(e, 4.4, .6, 3.1, .85, "Alisson Dolorier Arias\nResponsable de versiones", VERDE, tam=8)
    e.plot([4, 4], [2.2, 1.8], color=TINTA, lw=1)
    e.plot([2.05, 5.95], [1.8, 1.8], color=TINTA, lw=1)
    e.plot([2.05, 2.05], [1.8, 1.45], color=TINTA, lw=1)
    e.plot([5.95, 5.95], [1.8, 1.45], color=TINTA, lw=1)
    guardar(f, "organigrama")


def ramas():
    f, e = lienzo(12, 4.4)
    filas = {"main": 3.8, "develop": 2.8, "feature/*": 1.6, "fix/*": .6}
    colores = {"main": TERRA, "develop": TINTA, "feature/*": "#2c7a4b", "fix/*": "#a87406"}
    for nombre, y in filas.items():
        e.text(.1, y, nombre, fontsize=9, va="center", fontweight="bold", color=colores[nombre])
        e.plot([1.4, 11.7], [y, y], color=colores[nombre], lw=2, zorder=1)
    def punto(x, nombre):
        e.add_patch(Circle((x, filas[nombre]), .1, fc=colores[nombre], ec="white", lw=1, zorder=3))
    for x, nombre in [(1.8, "main"), (2.4, "develop"), (3.2, "feature/*"), (4, "feature/*"), (4.8, "develop"), (5.6, "feature/*"), (6.4, "feature/*"),
                      (7.2, "develop"), (8, "fix/*"), (8.8, "develop"), (10, "develop"), (10.8, "main")]:
        punto(x, nombre)
    for (x1, n1), (x2, n2) in [(("1.8", "main"), ("2.4", "develop")), (("2.4", "develop"), ("3.2", "feature/*")), (("4", "feature/*"), ("4.8", "develop")),
                               (("4.8", "develop"), ("5.6", "feature/*")), (("6.4", "feature/*"), ("7.2", "develop")), (("7.2", "develop"), ("8", "fix/*")),
                               (("8", "fix/*"), ("8.8", "develop")), (("10", "develop"), ("10.8", "main"))]:
        e.plot([float(x1), float(x2)], [filas[n1], filas[n2]], color=GRIS, lw=1.2, zorder=2)
    e.text(10.8, 4.05, "v1.0.0", ha="center", fontsize=8)
    guardar(f, "ramas_flujo")


def wire(e, x, y, w, h, texto="", relleno="white", tam=7, negrita=False):
    e.add_patch(Rectangle((x, y), w, h, fc=relleno, ec="#555", lw=.9, zorder=2))
    if texto:
        e.text(x + w / 2, y + h / 2, texto, ha="center", va="center", fontsize=tam, color="#333", zorder=3, fontweight="bold" if negrita else "normal")


def imagen_wire(e, x, y, w, h):
    wire(e, x, y, w, h, relleno="#e8e8e8")
    e.plot([x, x + w], [y, y + h], color="#999", lw=.7, zorder=3)
    e.plot([x, x + w], [y + h, y], color="#999", lw=.7, zorder=3)


def mock_web():
    f, e = lienzo(11, 7)
    wire(e, 0, 0, 11, 7)
    wire(e, 0, 6.45, 11, .55)
    wire(e, .2, 6.55, 1.8, .35, "LOGO DepaSeguro", negrita=True)
    for i, t in enumerate(["Inmuebles", "Mapa", "Verificar", "Zonas", "Contratos", "Guías"]):
        wire(e, 3.2 + i * 1.05, 6.55, .95, .35, t)
    wire(e, 9.7, 6.55, 1.1, .35, "Ingresar", "#ddd")
    wire(e, .2, .4, 2.5, 5.8, relleno="#f6f6f6")
    e.text(.35, 6, "Filtros", fontsize=9, fontweight="bold", zorder=4)
    for i, t in enumerate(["Campus ▼", "Radio (km)", "Distrito ▼", "Tipo ▼", "Precio máximo", "Trust Score mínimo", "Ordenar por ▼"]):
        wire(e, .35, 5.3 - i * .62, 2.2, .42, t)
    wire(e, .35, .65, 2.2, .42, "APLICAR", "#ccc", negrita=True)
    e.text(3, 6.05, "Inmuebles evaluados", fontsize=11, fontweight="bold", zorder=4)
    for i in range(6):
        x, y = 3 + (i % 3) * 2.65, 3.4 - (i // 3) * 2.9
        wire(e, x, y, 2.5, 2.55)
        imagen_wire(e, x + .1, y + 1.2, 2.3, 1.25)
        wire(e, x + .15, y + 2.1, .95, .25, "85 Confiable", "#ccc", 6)
        wire(e, x + .1, y + .75, 2.3, .35, "Título del aviso", negrita=True)
        wire(e, x + .1, y + .1, 2.3, .55, "S/ 480 al mes · 1.2 km")
    guardar(f, "mockup_web_catalogo")


def mock_ficha():
    f, e = lienzo(11, 7)
    wire(e, 0, 0, 11, 7)
    wire(e, 0, 6.45, 11, .55, "ENCABEZADO Y MENÚ")
    wire(e, .2, 5.75, 7, .5, "Título del aviso", negrita=True, tam=10)
    imagen_wire(e, .2, 3.2, 3.4, 2.4)
    imagen_wire(e, 3.8, 3.2, 3.4, 2.4)
    wire(e, .2, 2.05, 7, 1, "Precio normalizado, descripción, condiciones y servicios")
    wire(e, .2, .25, 3.4, 1.65, "Mapa OpenStreetMap", "#eee")
    wire(e, 3.8, .25, 3.4, 1.65, "Campus cercanos y reseñas")
    wire(e, 7.4, 4.1, 3.4, 2.15)
    e.text(7.6, 5.75, "85", fontsize=22, fontweight="bold", zorder=4)
    e.text(8.5, 5.85, "Trust Score", fontsize=8, zorder=4)
    for i, t in enumerate(["Documentos", "Identidad", "Precio", "Fotos"]):
        wire(e, 7.55, 5.2 - i * .28, 3.1, .2, t, "#eee", 6)
    wire(e, 7.4, 1.75, 3.4, 2.2, "Señales, patrones\ny recomendaciones")
    wire(e, 7.4, .25, 3.4, 1.35, "Guardar · Reportar · Ficha PDF", "#ddd")
    guardar(f, "mockup_web_ficha")


def mock_movil():
    f, e = lienzo(3.5, 7)
    wire(e, 0, 0, 3.5, 7)
    wire(e, 0, 6.4, 3.5, .6, "LOGO              Menú")
    e.text(.2, 6.1, "Verifica un aviso", fontsize=11, fontweight="bold", zorder=4)
    wire(e, .2, 4.65, 3.1, 1.2, "Pega el texto del aviso")
    wire(e, .2, 4.1, 1.5, .42, "Precio")
    wire(e, 1.8, 4.1, 1.5, .42, "Área")
    wire(e, .2, 3.55, 3.1, .42, "Teléfono")
    wire(e, .2, 3, 3.1, .42, "Subir foto")
    for i, t in enumerate(["☐ Piden dinero antes de visitar", "☐ No ofrecen contrato", "☐ No dejan visitar"]):
        e.text(.25, 2.75 - i * .27, t, fontsize=7.5, zorder=4)
    wire(e, .2, 1.65, 3.1, .42, "ANALIZAR AVISO", "#ccc", negrita=True)
    wire(e, .2, .2, 3.1, 1.3, "Resultado: 20 Crítico\nNo transfieras dinero", "#eee", 8)
    guardar(f, "mockup_movil_verificador")


def mock_reporte():
    f, e = lienzo(6.5, 8)
    wire(e, 0, 0, 6.5, 8)
    wire(e, .4, 7.2, 5.7, .5, "Reporte de riesgo por distrito", negrita=True, tam=11)
    e.text(.45, 6.95, "Fecha y hora de generación", fontsize=7, zorder=4)
    e.text(.45, 6.55, "Oferta evaluada en la plataforma", fontsize=9, fontweight="bold", zorder=4)
    for fila in range(5):
        for columna, texto in enumerate(["Distrito", "Avisos", "Mediana mes", "Mediana m²", "Trust medio"]):
            wire(e, .4 + columna * 1.14, 6.05 - fila * .34, 1.14, .34, texto if fila == 0 else "", "#ddd" if fila == 0 else "white", 6.5)
    e.text(.45, 4.2, "Denuncias de los últimos 12 meses (MININTER)", fontsize=9, fontweight="bold", zorder=4)
    for fila in range(6):
        for columna, texto in enumerate(["Distrito", "Estafa", "Robo", "Hurto", "Tasa"]):
            wire(e, .4 + columna * 1.14, 3.7 - fila * .34, 1.14, .34, texto if fila == 0 else "", "#ddd" if fila == 0 else "white", 6.5)
    wire(e, .4, .9, 5.7, .75, "Notas de interpretación y fuente de los datos", tam=7.5)
    wire(e, .4, .3, 5.7, .35, "Pie: sistema y número de página", tam=7)
    guardar(f, "mockup_reporte")


def main() -> None:
    SALIDA.mkdir(parents=True, exist_ok=True)
    for funcion in (bpmn_actual, bpmn_propuesto, bpmn_ingesta, casos_uso, clases, entidad_relacion, modelo_fisico, arquitectura,
                    paquetes, wbs, gantt, organigrama, ramas, mock_web, mock_ficha, mock_movil, mock_reporte):
        funcion()
    print(f"{len(list(SALIDA.glob('*.png')))} diagramas generados.")


if __name__ == "__main__":
    main()
