"""Ayudas para llenar las plantillas Word conservando estilos, numeración y campos."""
from __future__ import annotations

import copy
import shutil
import subprocess
import tempfile
from pathlib import Path

from docx import Document
from PIL import Image
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_COLOR_INDEX
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor
from docx.table import Table
from docx.text.paragraph import Paragraph

PENDIENTE = "[COMPLETAR"


def fijar_celda(celda, texto: str, tam: float | None = None) -> None:
    """Reemplaza el texto de una celda y conserva el formato de su primer run."""
    parrafo = celda.paragraphs[0]
    for extra in celda.paragraphs[1:]:
        extra._p.getparent().remove(extra._p)
    if parrafo.runs:
        parrafo.runs[0].text = str(texto)
        for run in parrafo.runs[1:]:
            run._r.getparent().remove(run._r)
    else:
        parrafo.add_run(str(texto))
    parrafo.runs[0].font.color.rgb = RGBColor(0, 0, 0)
    if tam:
        parrafo.runs[0].font.size = Pt(tam)


def fijar_parrafo(parrafo: Paragraph, texto: str) -> None:
    if parrafo.runs:
        parrafo.runs[0].text = texto
        for run in parrafo.runs[1:]:
            run._r.getparent().remove(run._r)
    else:
        parrafo.add_run(texto)


def agregar_campo(parrafo: Paragraph, instruccion: str, resultado: str = "1") -> None:
    """Inserta un campo de Word; se actualiza al abrir o con la automatización final."""
    for tipo, contenido in (("begin", None), (None, instruccion), ("separate", None), ("texto", resultado), ("end", None)):
        run = parrafo.add_run()
        if tipo in ("begin", "separate", "end"):
            marca = OxmlElement("w:fldChar")
            marca.set(qn("w:fldCharType"), tipo)
            run._r.append(marca)
        elif tipo == "texto":
            run.text = contenido
        else:
            orden = OxmlElement("w:instrText")
            orden.set(qn("xml:space"), "preserve")
            orden.text = contenido
            run._r.append(orden)


def run_con_pendientes(parrafo: Paragraph, texto: str, negrita: bool = False) -> None:
    """Resalta en amarillo los datos que debe completar el equipo."""
    resto = texto
    while PENDIENTE in resto:
        inicio = resto.index(PENDIENTE)
        fin = resto.index("]", inicio) + 1
        if inicio:
            parrafo.add_run(resto[:inicio]).bold = negrita or None
        marcado = parrafo.add_run(resto[inicio:fin])
        marcado.font.highlight_color = WD_COLOR_INDEX.YELLOW
        marcado.bold = True
        resto = resto[fin:]
    if resto:
        parrafo.add_run(resto).bold = negrita or None


def fijar_anchos(tabla, anchos: list[float]) -> None:
    """Fija el ancho de cada columna en la grilla y en las celdas. LibreOffice y Word respetan la grilla con diseño fijo."""
    tbl = tabla._tbl
    propiedades = tbl.tblPr
    for viejo in propiedades.findall(qn("w:tblLayout")):
        propiedades.remove(viejo)
    diseno = OxmlElement("w:tblLayout")
    diseno.set(qn("w:type"), "fixed")
    propiedades.append(diseno)
    grilla = tbl.tblGrid
    for columna, ancho in zip(grilla.findall(qn("w:gridCol")), anchos):
        columna.set(qn("w:w"), str(int(Cm(ancho).twips)))
    for fila in tabla.rows:
        for celda, ancho in zip(fila.cells, anchos):
            celda.width = Cm(ancho)


def poner_bordes(tabla) -> None:
    """Dibuja bordes directamente, porque no todas las plantillas incluyen el estilo Table Grid."""
    propiedades = tabla._tbl.tblPr
    bordes = OxmlElement("w:tblBorders")
    for lado in ("top", "left", "bottom", "right", "insideH", "insideV"):
        borde = OxmlElement(f"w:{lado}")
        borde.set(qn("w:val"), "single")
        borde.set(qn("w:sz"), "4")
        borde.set(qn("w:color"), "808080")
        bordes.append(borde)
    propiedades.append(bordes)


def ajustar_filas(tabla_xml) -> None:
    """Quita alturas fijas de la plantilla y evita que una fila se parta entre páginas."""
    for altura in tabla_xml.xpath(".//w:trHeight"):
        altura.getparent().remove(altura)
    filas = tabla_xml.xpath("./w:tr")
    for numero, fila in enumerate(filas):
        propiedades = fila.get_or_add_trPr()
        propiedades.append(OxmlElement("w:cantSplit"))
        if numero < len(filas) - 1:
            for parrafo in fila.xpath(".//w:p"):
                Paragraph(parrafo, None).paragraph_format.keep_with_next = True


class Cursor:
    """Escribe contenido nuevo justo después de un elemento de la plantilla."""

    def __init__(self, documento, ancla, estilo: str = "Body Text", vineta=None) -> None:
        self.doc = documento
        self.ancla = ancla
        self.estilo = estilo
        self.vineta = vineta

    def _colocar(self, elemento) -> None:
        self.ancla.addnext(elemento)
        self.ancla = elemento

    def _parrafo(self, estilo: str | None = None) -> Paragraph:
        nombre = estilo or self.estilo
        disponible = nombre if any(s.name == nombre for s in self.doc.styles) else "Normal"
        parrafo = self.doc.add_paragraph(style=disponible)
        self._colocar(parrafo._p)
        return parrafo

    def p(self, texto: str, negrita: bool = False, centro: bool = False, despues: float = 6) -> Paragraph:
        parrafo = self._parrafo()
        run_con_pendientes(parrafo, texto, negrita)
        parrafo.alignment = WD_ALIGN_PARAGRAPH.CENTER if centro else WD_ALIGN_PARAGRAPH.JUSTIFY
        parrafo.paragraph_format.space_after = Pt(despues)
        parrafo.paragraph_format.left_indent = Cm(0)
        parrafo.paragraph_format.first_line_indent = Cm(0)
        return parrafo

    def sub(self, texto: str) -> Paragraph:
        parrafo = self.p(texto, negrita=True, despues=3)
        parrafo.alignment = WD_ALIGN_PARAGRAPH.LEFT
        parrafo.paragraph_format.keep_with_next = True
        parrafo.paragraph_format.space_before = Pt(6)
        return parrafo

    def vinetas(self, elementos: list[str]) -> None:
        for texto in elementos:
            parrafo = self._parrafo("List Paragraph")
            if self.vineta is not None:
                propiedades = parrafo._p.get_or_add_pPr()
                propiedades.append(copy.deepcopy(self.vineta))
            else:
                texto = "• " + texto
            run_con_pendientes(parrafo, texto)
            parrafo.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            parrafo.paragraph_format.space_after = Pt(3)

    def titulo_tabla(self, tipo: str, texto: str) -> None:
        parrafo = self._parrafo("Caption")
        parrafo.add_run(f"{tipo} ")
        agregar_campo(parrafo, f" SEQ {tipo} \\* ARABIC ")
        parrafo.add_run(f". {texto}")
        parrafo.alignment = WD_ALIGN_PARAGRAPH.CENTER
        parrafo.paragraph_format.space_after = Pt(9)

    def imagen(self, ruta: Path, texto: str, ancho_cm: float = 16, tipo: str = "Ilustración", alto_max: float = 19.5) -> None:
        with Image.open(ruta) as imagen:
            proporcion = imagen.height / imagen.width
        ancho_cm = min(ancho_cm, alto_max / proporcion)
        parrafo = self._parrafo("Normal")
        parrafo.alignment = WD_ALIGN_PARAGRAPH.CENTER
        parrafo.paragraph_format.keep_with_next = True
        parrafo.add_run().add_picture(str(ruta), width=Cm(ancho_cm))
        if texto:
            self.titulo_tabla(tipo, texto)

    def tabla(self, filas: list[list], anchos: list[float] | None = None, texto: str | None = None, tam: float = 9) -> Table:
        tabla = self.doc.add_table(rows=len(filas), cols=len(filas[0]))
        poner_bordes(tabla)
        for i, fila in enumerate(filas):
            for j, valor in enumerate(fila):
                celda = tabla.cell(i, j)
                parrafo = celda.paragraphs[0]
                run_con_pendientes(parrafo, str(valor), negrita=(i == 0))
                for run in parrafo.runs:
                    run.font.size = Pt(tam)
                    run.font.name = "Arial"
                parrafo.paragraph_format.space_after = Pt(1)
                parrafo.paragraph_format.left_indent = Cm(0)
                parrafo.paragraph_format.right_indent = Cm(0)
                parrafo.paragraph_format.first_line_indent = Cm(0)
                if anchos:
                    celda.width = Cm(anchos[j])
                if i == 0:
                    sombra = OxmlElement("w:shd")
                    sombra.set(qn("w:val"), "clear")
                    sombra.set(qn("w:fill"), "EBE3D3")
                    celda._tc.get_or_add_tcPr().append(sombra)
        if anchos:
            fijar_anchos(tabla, anchos)
        encabezado = OxmlElement("w:tblHeader")
        tabla.rows[0]._tr.get_or_add_trPr().append(encabezado)
        self._colocar(tabla._tbl)
        if texto:
            self.titulo_tabla("Tabla", texto)
        else:
            self.p("", despues=4)
        return tabla

    def copiar_tabla(self, modelo: Table, valores: list[str], texto: str) -> None:
        nueva = copy.deepcopy(modelo._tbl)
        self._colocar(nueva)
        tabla = Table(nueva, self.doc)
        for fila, valor in zip(tabla.rows, valores):
            fijar_celda(fila.cells[1], valor, 10)
        self.titulo_tabla("Tabla", texto)

    def salto(self) -> None:
        parrafo = self._parrafo("Normal")
        parrafo.add_run().add_break(__import__("docx.enum.text", fromlist=["WD_BREAK"]).WD_BREAK.PAGE)


class Plantilla:
    def __init__(self, ruta: Path) -> None:
        self.doc = Document(str(ruta))
        self.cuerpo = self.doc.element.body
        self.els = list(self.cuerpo)

    def parrafo(self, indice: int) -> Paragraph:
        return Paragraph(self.els[indice], self.doc)

    def limpiar(self, inicio: int, fin: int) -> None:
        for elemento in self.els[inicio + 1:fin]:
            etiqueta = elemento.tag.split("}")[1]
            if etiqueta.startswith("bookmark") or elemento.xpath(".//w:sectPr"):
                continue
            if elemento.getparent() is not None:
                self.cuerpo.remove(elemento)

    def en(self, inicio: int, fin: int | None = None, vineta=None, estilo: str = "Body Text") -> Cursor:
        if fin is not None:
            self.limpiar(inicio, fin)
        return Cursor(self.doc, self.els[inicio], estilo, vineta)

    def quitar_imagenes_sin_uso(self) -> None:
        xml = self.doc.element.xml
        parte = self.doc.part
        for clave, relacion in list(parte.rels.items()):
            if relacion.reltype.endswith("/image") and f'"{clave}"' not in xml:
                parte.drop_rel(clave)


GUION_WORD = r"""
param([string]$Docx, [string]$Pdf)
$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0
try {
  $doc = $word.Documents.Open($Docx)
  foreach ($i in 1..2) {
    $doc.Fields.Update() | Out-Null
    foreach ($toc in $doc.TablesOfContents) { $toc.Update() }
    foreach ($tof in $doc.TablesOfFigures) { $tof.Update() }
    foreach ($seccion in $doc.Sections) {
      foreach ($cabecera in $seccion.Headers) { $cabecera.Range.Fields.Update() | Out-Null }
      foreach ($pie in $seccion.Footers) { $pie.Range.Fields.Update() | Out-Null }
    }
  }
  $doc.Save()
  $doc.ExportAsFixedFormat($Pdf, 17)
  "Paginas: " + $doc.ComputeStatistics(2)
  $doc.Close()
} finally { $word.Quit() }
"""


def finalizar_con_word(destino: Path) -> str:
    """Actualiza índices y exporta a PDF. Word no admite rutas muy largas, por eso usa una carpeta temporal.

    Si no hay Word, usa LibreOffice mediante lo_finalizar.py.
    """
    if not shutil.which("powershell.exe"):
        import sys
        guion = Path(__file__).with_name("lo_finalizar.py")
        salida = subprocess.run([sys.executable, str(guion), str(destino)], capture_output=True, text=True, timeout=600)
        if salida.returncode:
            raise RuntimeError(salida.stdout + salida.stderr)
        return salida.stdout.strip()
    with tempfile.TemporaryDirectory(dir=Path.home()) as temporal:
        carpeta = Path(temporal)
        docx = carpeta / "doc.docx"
        pdf = carpeta / "doc.pdf"
        guion = carpeta / "actualizar.ps1"
        shutil.copy(destino, docx)
        guion.write_text(GUION_WORD, encoding="utf-8-sig")
        salida = subprocess.run(["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(guion),
                                 "-Docx", str(docx), "-Pdf", str(pdf)], capture_output=True, text=True, timeout=280)
        if not pdf.exists():
            raise RuntimeError(salida.stdout + salida.stderr)
        shutil.copy(docx, destino)
        shutil.copy(pdf, destino.with_suffix(".pdf"))
        return salida.stdout.strip()
