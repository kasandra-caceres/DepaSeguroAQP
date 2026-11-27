"""Actualiza índices y campos de un .docx con LibreOffice y lo exporta a PDF.

Alternativa a Word para Linux o macOS.
Uso:  python3 scripts/lo_finalizar.py ARCHIVO.docx
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
import time
from pathlib import Path

import uno
from com.sun.star.beans import PropertyValue


def prop(nombre, valor):
    p = PropertyValue()
    p.Name, p.Value = nombre, valor
    return p


def conectar(puerto: int):
    local = uno.getComponentContext()
    resolver = local.ServiceManager.createInstanceWithContext("com.sun.star.bridge.UnoUrlResolver", local)
    for _ in range(60):
        try:
            return resolver.resolve(f"uno:socket,host=127.0.0.1,port={puerto};urp;StarOffice.ComponentContext")
        except Exception:
            time.sleep(0.5)
    raise RuntimeError("No se pudo conectar con LibreOffice")


def main() -> None:
    docx = Path(sys.argv[1]).resolve()
    pdf = docx.with_suffix(".pdf")
    puerto = 2002
    perfil = tempfile.mkdtemp()
    proceso = subprocess.Popen(["soffice", "--headless", "--invisible", "--norestore", f"-env:UserInstallation=file://{perfil}",
                                f"--accept=socket,host=127.0.0.1,port={puerto};urp;"])
    try:
        ctx = conectar(puerto)
        escritorio = ctx.ServiceManager.createInstanceWithContext("com.sun.star.frame.Desktop", ctx)
        doc = escritorio.loadComponentFromURL(docx.as_uri(), "_blank", 0, (prop("Hidden", True),))
        for _ in range(2):
            doc.getTextFields().refresh()
            indices = doc.getDocumentIndexes()
            for i in range(indices.getCount()):
                indices.getByIndex(i).update()
            doc.refresh()
        doc.storeToURL(docx.as_uri(), (prop("FilterName", "MS Word 2007 XML"),))
        doc.storeToURL(pdf.as_uri(), (prop("FilterName", "writer_pdf_Export"),))
        paginas = doc.getCurrentController().getPropertyValue("PageCount")
        doc.close(True)
        print(f"Paginas: {paginas}")
    finally:
        proceso.terminate()
        proceso.wait(timeout=30)


if __name__ == "__main__":
    main()
