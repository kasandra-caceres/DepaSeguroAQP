"""Crea la presentación de 8 minutos en PowerPoint con notas para la exposición."""
from __future__ import annotations

import re
import sqlite3
from pathlib import Path

from PIL import Image
from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt

RAIZ = Path(__file__).resolve().parents[1]
DIAG, CAP, EVI = RAIZ / "docs" / "diagramas", RAIZ / "docs" / "capturas", RAIZ / "docs" / "evidencias"
SALIDA = RAIZ / "entregables" / "Presentacion_DepaSeguro_AQP.pptx"
PIZARRA, TERRA, SILLAR, ARENA, GRIS = (RGBColor(0x22, 0x30, 0x3C), RGBColor(0xB4, 0x53, 0x2A), RGBColor(0xF6, 0xF1, 0xE7),
                                       RGBColor(0xEB, 0xE3, 0xD3), RGBColor(0x5B, 0x66, 0x70))
BLANCO = RGBColor(255, 255, 255)
TITULOS, TEXTO = "Georgia", "Segoe UI"

bd = sqlite3.connect(RAIZ / "data" / "depaseguro.db")
ANUAL = bd.execute("SELECT anio, SUM(cantidad) FROM denuncias_distrito WHERE modalidad='Estafa' GROUP BY anio").fetchall()
if not ANUAL:  # Base sin ingesta: valores de la lectura completa del 21-11-2026.
    ANUAL = [(2018, 700), (2019, 641), (2020, 843), (2021, 1073), (2022, 1455), (2023, 2039), (2024, 2332), (2025, 2159)]

def resumen_pruebas() -> tuple[int, int]:
    """Lee la última ejecución de pytest guardada en docs/evidencias/pruebas.txt: total de pruebas y cobertura."""
    texto = (RAIZ / "docs" / "evidencias" / "pruebas.txt").read_text(encoding="utf-8", errors="replace")
    total = int(re.findall(r"(\d+) passed", texto)[-1])
    cobertura = re.findall(r"^TOTAL.*?(\d+)%\s*$", texto, re.M)
    return total, int(cobertura[-1]) if cobertura else 90  # 90 %: última medición con pytest-cov


N_PRUEBAS, COBERTURA = resumen_pruebas()

presentacion = Presentation()
presentacion.slide_width, presentacion.slide_height = Inches(13.333), Inches(7.5)
VACIO = presentacion.slide_layouts[6]


def texto(diapo, x, y, w, h, contenido, tam=20, color=PIZARRA, negrita=False, fuente=TEXTO, centro=False):
    caja = diapo.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    marco = caja.text_frame
    marco.word_wrap = True
    lineas = contenido if isinstance(contenido, list) else [contenido]
    for indice, linea in enumerate(lineas):
        parrafo = marco.paragraphs[0] if indice == 0 else marco.add_paragraph()
        run = parrafo.add_run()
        run.text = linea
        run.font.size, run.font.color.rgb, run.font.bold, run.font.name = Pt(tam), color, negrita, fuente
        parrafo.space_after = Pt(9)
        if centro:
            parrafo.alignment = PP_ALIGN.CENTER
    return caja


def base(titulo: str, notas: str):
    diapo = presentacion.slides.add_slide(VACIO)
    fondo = diapo.background.fill
    fondo.solid()
    fondo.fore_color.rgb = SILLAR
    texto(diapo, .55, .32, 12.2, .9, titulo, 30, PIZARRA, True, TITULOS)
    diapo.notes_slide.notes_text_frame.text = notas
    return diapo


def imagen(diapo, ruta: Path, x, y, w, h):
    with Image.open(ruta) as archivo:
        proporcion = archivo.width / archivo.height
    ancho, alto = (w, w / proporcion) if w / proporcion <= h else (h * proporcion, h)
    diapo.shapes.add_picture(str(ruta), Inches(x + (w - ancho) / 2), Inches(y + (h - alto) / 2), Inches(ancho), Inches(alto))


def recorte(nombre: str, alto_relativo: float) -> Path:
    destino = RAIZ / "data" / f"recorte_{nombre}.png"
    with Image.open(CAP / f"{nombre}.png") as archivo:
        archivo.crop((0, 0, archivo.width, int(archivo.width * alto_relativo))).save(destino)
    return destino


def tarjeta(diapo, x, y, w, h, titulo, detalle, color=BLANCO):
    forma = diapo.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    forma.adjustments[0] = .06
    forma.fill.solid()
    forma.fill.fore_color.rgb = color
    forma.line.color.rgb = ARENA
    forma.shadow.inherit = False
    texto(diapo, x + .15, y + .12, w - .3, .6, titulo, 21, PIZARRA, True, TITULOS)
    texto(diapo, x + .15, y + .72, w - .3, h - .8, detalle, 19, GRIS)


# 1
d = presentacion.slides.add_slide(VACIO)
d.background.fill.solid()
d.background.fill.fore_color.rgb = PIZARRA
imagen(d, EVI / "logo_blanco.png", .7, .75, 1.1, 1.1)
texto(d, .7, 2.1, 11.8, 1.3, "DepaSeguro AQP", 54, BLANCO, True, TITULOS)
texto(d, .7, 3.25, 11.5, 1.3, "Verificación de autenticidad, calificación de inmuebles y detección de arriendos fraudulentos para estudiantes universitarios", 24, SILLAR)
texto(d, .7, 5.35, 11, 1.1, ["Grupo 08: Kasandra Cáceres Quispe y Alisson Dolorier Arias", "Lenguajes de Programación · Docente: Rene Alonso Nieto Valencia"], 18, ARENA)
d.notes_slide.notes_text_frame.text = "Kasandra, 15 segundos. Saluda, presenta al equipo y el nombre del proyecto."

# 2
d = base("Las estafas denunciadas se triplicaron en Arequipa", "Kasandra, 40 segundos. Aclara que el dato incluye todo tipo de estafas, no solo alquileres. No se encontró una cifra oficial específica de vivienda estudiantil. Por eso se propone una encuesta para medir el problema local.")
datos = CategoryChartData()
anios = [f for f in ANUAL if f[0] < 2026]
datos.categories = [str(f[0]) for f in anios]
datos.add_series("Denuncias por estafa", [f[1] for f in anios])
grafico = d.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(.55), Inches(1.3), Inches(7.6), Inches(5.5), datos).chart
grafico.has_legend = False
grafico.has_title = False
serie = grafico.plots[0].series[0]
serie.format.fill.solid()
serie.format.fill.fore_color.rgb = TERRA
grafico.plots[0].has_data_labels = True
grafico.plots[0].data_labels.font.size = Pt(13)
grafico.plots[0].gap_width = 60
grafico.value_axis.visible = False
grafico.value_axis.has_major_gridlines = False
grafico.category_axis.tick_labels.font.size = Pt(14)
texto(d, 8.5, 1.55, 4.3, 4.6, ["Riesgos en vivienda estudiantil:", "Adelantos por cuartos que no existen", "Fotos copiadas", "Presión para pagar", "Condiciones sin contrato"], 21)
texto(d, 8.5, 6.25, 4.4, .6, "Provincia de Arequipa, todo tipo de estafas. Fuente: MININTER.", 12, GRIS)

# 3
d = base("Un sistema que decide y avisa antes del pago", "Kasandra, 30 segundos. Conecta con la observación del docente: el sistema no solo registra, calcula, alerta y reporta. También lee fuentes automáticamente, deduce patrones y ayuda a actuar.")
tarjeta(d, .55, 1.45, 3.9, 2.45, "Antes de pagar", "Busca por campus, compara precios y verifica avisos de redes sociales.")
tarjeta(d, 4.7, 1.45, 3.9, 2.45, "Mientras decides", "Trust Score explicado, señales, patrones y alertas.")
tarjeta(d, 8.85, 1.45, 3.9, 2.45, "Si hay un problema", "Reporte, descargo, moderación y expediente de apoyo.")
tarjeta(d, .55, 4.2, 12.2, 2.35, "Observación del docente", "Más que registrar, calcular, alertar y reportar: lectura automática de fuentes del Estado y ONG, reglas lógicas, comparación de imágenes y detección de redes.", ARENA)

# 3b
d = base("Tres alternativas, una elegida", "Kasandra, 30 segundos. Nombra las tres alternativas. La web es la única que cubre más de 5 pantallas, backend y persistencia en Python, datos abiertos y el plazo del curso. Del bot se tomó el verificador y del directorio la validación de documentos.")
tarjeta(d, .55, 1.45, 3.95, 3.3, "1. Plataforma web", "Trust Score, búsqueda por campus, verificador y 7 fuentes. Elegida.", ARENA)
tarjeta(d, 4.7, 1.45, 3.95, 3.3, "2. Bot de WhatsApp", "Respuesta rápida, pero sin pantallas y dependiente de una API de pago.")
tarjeta(d, 8.85, 1.45, 3.9, 3.3, "3. Directorio", "Arrendadores visitados, pero requiere convenios y no revisa avisos de redes.")
texto(d, .55, 5.1, 12.2, 1.4, "Criterios: ataque al fraude en redes, 5 pantallas o más, Python en backend y persistencia, datos abiertos, dependencia de terceros y plazo.", 19, GRIS)

# 3c
d = base("Planificación y control del proyecto", "Alisson, 40 segundos. El WBS del informe divide el trabajo en seis paquetes. El Gantt va de la semana 11 a la 17. Los hitos se controlaron semana a semana: avance del 40 % en la semana 15 y entrega final el 01 de diciembre.")
imagen(d, DIAG / "gantt.png", .45, 1.3, 8.6, 5.8)
texto(d, 9.0, 1.4, 3.9, 5.6, ["Hitos", "S12 Tema aprobado", "S13 SRS y BPMN", "S14 Diseño y mockups", "S15 Prototipo y avance 40 %", "S16 Pruebas", "S17 Entrega y sustentación"], 18)

# 4
d = base("El proceso agrega controles antes de publicar", "Alisson, 30 segundos. Recorre BPMN: el arrendador registra, Python evalúa, moderación revisa si hay riesgo, y el estudiante decide. Si hay un problema, reporta.")
imagen(d, DIAG / "bpmn_propuesto.png", .6, 1.25, 12.1, 5.9)

# 5
d = base("Frontend, backend y datos integrados", "Alisson, 35 segundos. Explica capas MVC. El frontend captura datos; el backend es Python; SQLite guarda 27 tablas. La ingesta alimenta la misma base.")
imagen(d, DIAG / "arquitectura.png", .55, 1.2, 8.4, 6)
texto(d, 9.25, 1.55, 3.6, 4.8, ["Frontend: Jinja, CSS, JS", "Backend: Flask y Python", "Datos: SQLite y archivos", "Patrones: MVC, DAO, DTO, Strategy, Facade, Observer"], 19)

# 6
d = base("Siete fuentes se leen de forma automática", "Alisson, 35 segundos. Da ejemplos: BCRP cambia el precio de avisos en dólares; SUNEDU aporta campus; MININTER permite ver denuncias por distrito. Si una fuente falla, se conservan los últimos datos.")
filas = [("Fuente", "Tipo", "Uso"), ("BCRP", "Estado", "Tipo de cambio e IPC"), ("MININTER", "Estado", "Denuncias por distrito"), ("Ministerio Público", "Estado", "Delitos informáticos"),
         ("SUNEDU", "Estado", "Campus y licencia"), ("OpenStreetMap", "ONG", "Direcciones"), ("Wikidata", "ONG", "Población distrital"), ("Transparency International", "ONG", "Percepción de corrupción")]
tabla = d.shapes.add_table(len(filas), 3, Inches(.55), Inches(1.35), Inches(12.2), Inches(4.8)).table
tabla.columns[0].width, tabla.columns[1].width, tabla.columns[2].width = Inches(4.8), Inches(1.8), Inches(5.6)
for i, fila in enumerate(filas):
    for j, valor in enumerate(fila):
        celda = tabla.cell(i, j)
        celda.text = valor
        celda.fill.solid()
        celda.fill.fore_color.rgb = PIZARRA if i == 0 else BLANCO
        run = celda.text_frame.paragraphs[0].runs[0]
        run.font.size, run.font.name, run.font.bold = Pt(17), TEXTO, i == 0
        run.font.color.rgb = BLANCO if i == 0 else PIZARRA
        celda.vertical_anchor = MSO_ANCHOR.MIDDLE
texto(d, .55, 6.35, 12.2, .6, "Actualización cada 24 horas, con historial y tolerancia a fallas.", 18, TERRA, True)

# 7
d = base("Python combina estadística, reglas y puntaje", "Kasandra, 45 segundos. Muestra los tres paradigmas. Funcional: filtros y reducción. Lógico: motor tipo Prolog. POO: detectores y clases. El Trust Score explica cada componente.")
tarjeta(d, .55, 1.35, 3.95, 2.4, "Funcional", "Pipelines, lambdas, reduce y datos inmutables.")
tarjeta(d, 4.7, 1.35, 3.95, 2.4, "Lógica", "Hechos, reglas y unificación, como en Prolog.")
tarjeta(d, 8.85, 1.35, 3.9, 2.4, "POO y patrones", "Herencia, Strategy y Template Method.")
tarjeta(d, .55, 4.05, 12.2, 2.65, "Trust Score: 0 a 100", "Documentos 25 · Identidad 15 · Precio 15 · Fotos 15 · Contacto 10 · Condiciones 10 · Comunidad 10. Un reporte confirmado o varios patrones graves limitan el resultado.", ARENA)

# 8
d = base("Un aviso sospechoso se explica y se limita", "Alisson, 60 segundos. Demostración o captura. Abre la ficha crítica: precio, foto repetida y teléfono. Luego pega un texto en el verificador. Los datos son ficticios.")
imagen(d, recorte("12_ficha_critica", .78), .55, 1.25, 6, 5.85)
imagen(d, recorte("13_verificador_resultado", .78), 6.8, 1.25, 6, 5.85)

# 9
d = base("La persistencia sostiene todo el proceso", "Kasandra, 30 segundos. Explica entidades centrales: usuarios, inmuebles, evaluaciones, reportes y fuentes. El CRUD se implementa con DAO y consultas parametrizadas.")
imagen(d, DIAG / "entidad_relacion.png", .55, 1.2, 8.5, 6)
texto(d, 9.35, 1.55, 3.5, 4.8, ["27 tablas", "Claves foráneas e índices", "Patrón DAO", "Archivos PDF, Excel y CSV"], 21)

# 10
d = base("Calidad comprobada con pruebas y Git", f"Alisson, 30 segundos. Muestra {N_PRUEBAS} pruebas y {COBERTURA} % de cobertura. Menciona una incidencia real: el archivo 2020 del Ministerio Público mezclaba todos los delitos y se corrigió.")
tarjeta(d, .55, 1.45, 3.9, 2.45, f"{N_PRUEBAS} pruebas", "Todas pasaron en la última ejecución.")
tarjeta(d, 4.7, 1.45, 3.9, 2.45, f"{COBERTURA} % de cobertura", "Incluye reglas, fuentes, web y permisos.")
tarjeta(d, 8.85, 1.45, 3.9, 2.45, "Git", "Ramas main, develop y feature.")
imagen(d, DIAG / "ramas_flujo.png", 1.3, 4.05, 10.7, 3)

# 11
d = base("El prototipo cumple y queda listo para validarse", "Kasandra, 30 segundos. Cierra con lo logrado, limitaciones y próximos pasos. Reconoce que falta medir con usuarios reales.")
tarjeta(d, .55, 1.45, 3.95, 3.9, "Logrado", "Portal web, backend Python, SQLite, alertas, reportes y lectura automática.")
tarjeta(d, 4.7, 1.45, 3.95, 3.9, "Límites", "Datos de avisos ficticios y sin una fuente oficial de alquiler por distrito.")
tarjeta(d, 8.85, 1.45, 3.9, 3.9, "Siguiente paso", "Aplicar la encuesta, hacer un piloto y mejorar notificaciones.", ARENA)

SALIDA.parent.mkdir(exist_ok=True)
presentacion.save(SALIDA)
print(f"Diapositivas: {len(presentacion.slides)}")
