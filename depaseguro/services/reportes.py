"""Generación de reportes en PDF, Excel y CSV."""
from __future__ import annotations

import io
from datetime import datetime
from xml.sax.saxutils import escape

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from ..dao.repositorios import InmuebleDAO, ReporteDAO
from .analisis_red import ranking_zonas, resumen_anual_estafas, ultimo_periodo
from .analitica import resumen_precios
from .evaluador import detalle_evaluacion
from .gestion import MOTIVOS, TIPOS

PIZARRA = colors.HexColor("#22303c")
TERRACOTA = colors.HexColor("#b4532a")
SILLAR = colors.HexColor("#f4efe6")


def _estilos() -> dict:
    base = getSampleStyleSheet()
    return {
        "titulo": ParagraphStyle("titulo", parent=base["Title"], textColor=PIZARRA, fontSize=19, alignment=0, spaceAfter=4),
        "sub": ParagraphStyle("sub", parent=base["Normal"], textColor=colors.HexColor("#5b6670"), fontSize=9, spaceAfter=12),
        "h2": ParagraphStyle("h2", parent=base["Heading2"], textColor=TERRACOTA, fontSize=12.5, spaceBefore=12, spaceAfter=5),
        "p": ParagraphStyle("p", parent=base["BodyText"], fontSize=9.5, leading=13.5, alignment=TA_JUSTIFY),
        "celda": ParagraphStyle("celda", parent=base["BodyText"], fontSize=8.5, leading=11),
    }


def _pie(lienzo, documento) -> None:
    lienzo.saveState()
    lienzo.setFont("Helvetica", 7.5)
    lienzo.setFillColor(colors.HexColor("#5b6670"))
    lienzo.drawString(2 * cm, 1.1 * cm, "DepaSeguro AQP - Documento generado automáticamente")
    lienzo.drawRightString(A4[0] - 2 * cm, 1.1 * cm, f"Página {documento.page}")
    lienzo.restoreState()


def _tabla(filas: list[list], anchos: list[float] | None = None) -> Table:
    estilos = _estilos()
    contenido = [[Paragraph(escape(str(c)), estilos["celda"]) for c in fila] for fila in filas]
    tabla = Table(contenido, colWidths=anchos, repeatRows=1)
    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), SILLAR),
        ("LINEBELOW", (0, 0), (-1, 0), 0.8, PIZARRA),
        ("LINEBELOW", (0, 1), (-1, -1), 0.25, colors.HexColor("#c9c2b6")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return tabla


def _construir(titulo: str, subtitulo: str, elementos: list) -> bytes:
    salida = io.BytesIO()
    estilos = _estilos()
    documento = SimpleDocTemplate(salida, pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm,
                                  topMargin=1.8 * cm, bottomMargin=1.8 * cm, title=titulo, author="DepaSeguro AQP")
    historia = [Paragraph(escape(titulo), estilos["titulo"]), Paragraph(escape(subtitulo), estilos["sub"]), *elementos]
    documento.build(historia, onFirstPage=_pie, onLaterPages=_pie)
    return salida.getvalue()


def _fecha() -> str:
    return datetime.now().strftime("%d/%m/%Y %H:%M")


def pdf_riesgo_distritos(db) -> bytes:
    """Reporte gerencial: oferta evaluada por distrito y contexto oficial de denuncias."""
    e = _estilos()
    avisos = InmuebleDAO(db).publicados()
    oferta = resumen_precios(avisos)
    elementos = [Paragraph("Oferta evaluada en la plataforma", e["h2"])]
    if oferta:
        filas = [["Distrito", "Avisos", "Mediana mensual", "Mediana por m²", "Trust Score medio"]]
        filas += [[f["distrito"].title(), f["avisos"], f"S/ {f['mediana_mensual']:.2f}", f"S/ {f['mediana_m2']:.2f}",
                   f"{f['trust_medio']:.0f}"] for f in oferta]
        elementos.append(_tabla(filas))
    else:
        elementos.append(Paragraph("Aún no hay avisos publicados.", e["p"]))

    elementos.append(Paragraph("Denuncias de los últimos 12 meses (MININTER)", e["h2"]))
    zonas = ranking_zonas(db)
    periodo = ultimo_periodo(db)
    if zonas:
        filas = [["Distrito", "Estafa", "Robo", "Hurto", "Estafas por 10 000 hab."]]
        filas += [[z["distrito"], z["Estafa"], z["Robo"], z["Hurto"],
                   z["tasa_estafa"] if z["tasa_estafa"] is not None else "s/d"] for z in zonas[:15]]
        elementos.append(_tabla(filas))
        elementos.append(Spacer(1, 6))
        elementos.append(Paragraph(f"Datos hasta {periodo[1]:02d}/{periodo[0]}. Una denuncia registrada no equivale "
                                   "a un delito comprobado, y los distritos con más población o comercio suelen "
                                   "concentrar más denuncias.", e["p"]))
        anual = resumen_anual_estafas(db)
        filas = [["Año", "Estafas denunciadas", "Meses con datos"]] + [[a["anio"], a["total"], a["meses"]] for a in anual]
        elementos += [Paragraph("Evolución anual en la provincia de Arequipa", e["h2"]), _tabla(filas)]
    else:
        elementos.append(Paragraph("Todavía no se han leído datos del MININTER.", e["p"]))
    return _construir("Reporte de riesgo por distrito", f"Generado el {_fecha()}", elementos)


def pdf_ficha_inmueble(db, inmueble_id: int) -> bytes:
    """Ficha de confiabilidad que el estudiante puede guardar o compartir."""
    e = _estilos()
    aviso = InmuebleDAO(db).detalle(inmueble_id)
    evaluacion = detalle_evaluacion(db, inmueble_id)
    elementos = [_tabla([
        ["Dato", "Valor"],
        ["Tipo", TIPOS.get(aviso["tipo"], aviso["tipo"])],
        ["Distrito", aviso["distrito"].title()],
        ["Dirección", aviso["direccion"]],
        ["Precio normalizado", f"S/ {aviso['precio_mensual_pen']:.2f} al mes (S/ {aviso['precio_m2_pen']:.2f} por m²)"],
        ["Trust Score", f"{aviso['trust_score']} / 100 ({aviso['nivel_riesgo']})"],
    ], [5 * cm, 12 * cm])]
    if evaluacion:
        elementos.append(Paragraph("Composición del puntaje", e["h2"]))
        filas = [["Componente", "Puntos", "Explicación"]]
        filas += [[c["nombre"], f"{c['obtenido']:g} / {c['maximo']:g}", c["explicacion"]] for c in evaluacion["componentes"]]
        elementos.append(_tabla(filas, [4 * cm, 2.5 * cm, 10.5 * cm]))
        elementos.append(Paragraph("Señales encontradas", e["h2"]))
        if evaluacion["hallazgos"]:
            filas = [["Señal", "Detalle"]] + [[h["titulo"], h["detalle"]] for h in evaluacion["hallazgos"]]
            elementos.append(_tabla(filas, [6 * cm, 11 * cm]))
        else:
            elementos.append(Paragraph("No se encontraron señales de riesgo.", e["p"]))
        if evaluacion["recomendaciones"]:
            elementos.append(Paragraph("Recomendaciones", e["h2"]))
            elementos += [Paragraph(f"• {escape(r)}", e["p"]) for r in evaluacion["recomendaciones"]]
    elementos += [Spacer(1, 10), Paragraph(
        "El Trust Score es una estimación automática basada en los datos disponibles. No afirma que una persona haya "
        "cometido un delito ni reemplaza la visita al inmueble, el contrato o la consulta en registros públicos.", e["p"])]
    return _construir(f"Ficha de confiabilidad: {aviso['titulo']}", f"Generado el {_fecha()}", elementos)


def pdf_expediente(db, reporte_id: int) -> bytes:
    """Ordena la evidencia de un caso para presentarla ante la autoridad."""
    e = _estilos()
    reporte = ReporteDAO(db).con_detalle("r.id = ?", (reporte_id,))[0]
    aviso = InmuebleDAO(db).detalle(reporte["inmueble_id"]) if reporte["inmueble_id"] else None
    hechos = [
        ["Campo", "Información"],
        ["Número de reporte", reporte["id"]],
        ["Fecha de registro", reporte["creado_en"]],
        ["Persona que reporta", reporte["reportante"]],
        ["Motivo", MOTIVOS.get(reporte["motivo"], reporte["motivo"])],
        ["Monto perdido", f"S/ {reporte['monto_perdido']:.2f}"],
        ["Teléfono reportado", reporte["telefono_reportado"] or (aviso["telefono_contacto"] if aviso else "No indicado")],
        ["Estado en la plataforma", reporte["estado"].replace("_", " ")],
    ]
    elementos = [Paragraph("1. Datos del caso", e["h2"]), _tabla(hechos, [5 * cm, 12 * cm]),
                 Paragraph("2. Relato de los hechos", e["h2"]), Paragraph(escape(reporte["detalle"]), e["p"])]
    if aviso:
        elementos += [Paragraph("3. Aviso publicado", e["h2"]), _tabla([
            ["Campo", "Información"], ["Título", aviso["titulo"]], ["Dirección declarada", aviso["direccion"]],
            ["Distrito", aviso["distrito"].title()], ["Anunciante", aviso["arrendador"]],
            ["Publicado el", aviso["creado_en"]], ["Precio publicado", f"{aviso['moneda']} {aviso['precio']:.2f} por {aviso['periodo']}"],
        ], [5 * cm, 12 * cm])]
        imagenes = db.execute("SELECT sha256, creado_en FROM imagenes WHERE inmueble_id = ?", (aviso["id"],)).fetchall()
        if imagenes:
            filas = [["Huella SHA-256 de la imagen", "Registrada el"]] + [[f["sha256"], f["creado_en"]] for f in imagenes]
            elementos += [Paragraph("4. Huellas digitales de las fotografías", e["h2"]), _tabla(filas, [13 * cm, 4 * cm])]
    elementos.append(Paragraph("Qué adjuntar y dónde acudir", e["h2"]))
    pasos = (
        "Adjunta capturas del aviso y de los chats, comprobantes de Yape, Plin o transferencia, número de cuenta "
        "y datos del destinatario.",
        "Si hubo engaño para obtener dinero, presenta la denuncia en una comisaría o ante el Ministerio Público; "
        "el Código Penal regula la estafa en su artículo 196.",
        "Si el caso se cometió usando medios informáticos, menciona la Ley 30096 de Delitos Informáticos.",
        "Avisa de inmediato a tu banco o billetera digital para intentar bloquear la operación.",
    )
    elementos += [Paragraph(f"• {escape(paso)}", e["p"]) for paso in pasos]
    elementos += [Spacer(1, 8), Paragraph(
        "Este expediente organiza la información registrada por el usuario. No constituye una denuncia ni "
        "asesoría legal, y su contenido debe ser verificado por la autoridad competente.", e["p"])]
    return _construir(f"Expediente de apoyo para denuncia N.º {reporte['id']}", f"Generado el {_fecha()}", elementos)


def pdf_contrato(datos: dict) -> bytes:
    """Modelo referencial de contrato de arrendamiento para vivienda estudiantil."""
    e = _estilos()
    limpio = {clave: escape(str(valor or "__________")) for clave, valor in datos.items()}
    clausulas = [
        ("PRIMERA - Partes", f"Conste por el presente documento el contrato de arrendamiento que celebran "
         f"{limpio['arrendador']}, identificado(a) con documento {limpio['doc_arrendador']}, como ARRENDADOR(A); y "
         f"{limpio['estudiante']}, identificado(a) con documento {limpio['doc_estudiante']}, como ARRENDATARIO(A)."),
        ("SEGUNDA - Inmueble", f"El ARRENDADOR(A) declara ser propietario(a) o estar autorizado(a) para arrendar el "
         f"inmueble ubicado en {limpio['direccion']}, Arequipa, y entrega el ambiente descrito como: {limpio['ambiente']}."),
        ("TERCERA - Plazo", f"El plazo es de {limpio['plazo_meses']} mes(es), desde {limpio['inicio']}."),
        ("CUARTA - Renta y forma de pago", f"La renta mensual es de S/ {limpio['renta']}, pagadera hasta el día "
         f"{limpio['dia_pago']} de cada mes. Cada pago será respaldado con un recibo o constancia."),
        ("QUINTA - Garantía", f"El ARRENDATARIO(A) entrega S/ {limpio['garantia']} como garantía, que será devuelta "
         f"al concluir el contrato dentro de {limpio['dias_devolucion']} días, descontando únicamente daños "
         "comprobados o deudas por servicios."),
        ("SEXTA - Servicios", f"La renta incluye: {limpio['servicios']}. Los demás servicios se pagarán según consumo acreditado."),
        ("SÉPTIMA - Ingreso al ambiente", "El ARRENDADOR(A) solo ingresará al ambiente con aviso previo y acuerdo "
         "del ARRENDATARIO(A), salvo una emergencia que ponga en riesgo a personas o al inmueble."),
        ("OCTAVA - Fin anticipado", f"Cualquiera de las partes podrá terminar el contrato avisando con "
         f"{limpio['aviso_dias']} días de anticipación."),
        ("NOVENA - Inventario", "Las partes firman un inventario del estado del ambiente y sus bienes al inicio y al final."),
    ]
    elementos = []
    for titulo, texto in clausulas:
        elementos += [Paragraph(titulo, e["h2"]), Paragraph(texto, e["p"])]
    elementos += [Spacer(1, 34), _tabla([["ARRENDADOR(A)", "ARRENDATARIO(A)"], ["Firma y documento", "Firma y documento"]]),
                  Spacer(1, 10), Paragraph(
        "Modelo referencial de apoyo. Revísalo según tu caso y, si tienes dudas, consulta con un abogado o con "
        "los servicios de orientación legal de tu universidad.", e["p"])]
    return _construir("Contrato de arrendamiento de vivienda estudiantil", "Modelo referencial - DepaSeguro AQP", elementos)


def excel_catalogo(db) -> bytes:
    """Libro Excel con varias hojas para análisis fuera de la plataforma."""
    avisos = pd.DataFrame(InmuebleDAO(db).todos_detalle())
    columnas = ["id", "titulo", "tipo", "distrito", "precio", "moneda", "periodo", "precio_mensual_pen", "precio_m2_pen",
                "trust_score", "nivel_riesgo", "estado", "direccion_estado", "arrendador", "creado_en"]
    salida = io.BytesIO()
    with pd.ExcelWriter(salida, engine="openpyxl") as libro:
        (avisos[columnas] if not avisos.empty else pd.DataFrame(columns=columnas)).to_excel(
            libro, sheet_name="Avisos", index=False)
        pd.DataFrame(resumen_precios(InmuebleDAO(db).publicados())).to_excel(libro, sheet_name="Por distrito", index=False)
        pd.DataFrame(ranking_zonas(db)).to_excel(libro, sheet_name="Denuncias 12 meses", index=False)
        pd.read_sql_query("SELECT id, motivo, estado, monto_perdido, creado_en, resuelto_en FROM reportes", db).to_excel(
            libro, sheet_name="Reportes", index=False)
        for hoja in libro.sheets.values():
            for columna in hoja.columns:
                ancho = max((len(str(celda.value)) for celda in columna if celda.value is not None), default=8)
                hoja.column_dimensions[columna[0].column_letter].width = min(ancho + 2, 45)
    return salida.getvalue()


def csv_alertas(db) -> bytes:
    tabla = pd.read_sql_query(
        "SELECT id, tipo, severidad, mensaje, inmueble_id, creado_en FROM alertas ORDER BY id DESC", db)
    return tabla.to_csv(index=False).encode("utf-8-sig")


def indicadores_panel(db) -> dict:
    """Valores agregados para el panel de administración."""
    uno = lambda sql: db.execute(sql).fetchone()[0]
    niveles = {f["nivel_riesgo"]: f["total"] for f in db.execute(
        "SELECT nivel_riesgo, COUNT(*) AS total FROM inmuebles WHERE nivel_riesgo IS NOT NULL AND estado != 'retirado' GROUP BY 1")}
    motivos = [dict(f) for f in db.execute("SELECT motivo, COUNT(*) AS total FROM reportes GROUP BY motivo")]
    return {
        "avisos": uno("SELECT COUNT(*) FROM inmuebles WHERE estado != 'retirado'"),
        "pendientes": uno("SELECT COUNT(*) FROM inmuebles WHERE estado = 'pendiente'"),
        "reportes_abiertos": uno("SELECT COUNT(*) FROM reportes WHERE estado IN ('abierto','en_revision')"),
        "confirmados": uno("SELECT COUNT(*) FROM reportes WHERE estado = 'confirmado'"),
        "documentos": uno("SELECT COUNT(*) FROM documentos WHERE estado = 'pendiente'"),
        "monto": uno("SELECT COALESCE(SUM(monto_perdido), 0) FROM reportes WHERE estado = 'confirmado'"),
        "alertas": uno("SELECT COUNT(*) FROM alertas WHERE usuario_id IS NULL AND leida = 0"),
        "usuarios": uno("SELECT COUNT(*) FROM usuarios"),
        "niveles": niveles,
        "motivos": motivos,
    }
