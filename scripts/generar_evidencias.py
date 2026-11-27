"""Crea evidencias para el informe: Pydoc, imágenes de código, Git, pruebas y reportes reales."""
from __future__ import annotations

import pkgutil
import subprocess
import sys
from pathlib import Path

import pypdfium2
from PIL import Image, ImageDraw, ImageFont

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
EVIDENCIAS = RAIZ / "docs" / "evidencias"
PYDOC = RAIZ / "docs" / "pydoc"


def terminal(nombre: str, texto: str, ancho_max: int = 108) -> None:
    """Dibuja texto real de consola como imagen."""
    fuente = None
    for nombre_fuente in ("consola.ttf", "DejaVuSansMono.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", "Menlo.ttc"):
        try:
            fuente = ImageFont.truetype(nombre_fuente, 19)
            break
        except OSError:
            continue
    fuente = fuente or ImageFont.load_default()
    lineas = [linea[:ancho_max] for linea in texto.rstrip().splitlines()]
    ancho = int(max(fuente.getlength("M" * 40), max(fuente.getlength(l) for l in lineas))) + 40
    imagen = Image.new("RGB", (ancho, len(lineas) * 26 + 34), "#1f2a33")
    dibujo = ImageDraw.Draw(imagen)
    for i, linea in enumerate(lineas):
        dibujo.text((20, 16 + i * 26), linea, font=fuente, fill="#e8e3d8")
    imagen.save(EVIDENCIAS / f"{nombre}.png")


def ejecutar(*comando: str) -> str:
    resultado = subprocess.run(comando, cwd=RAIZ, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return resultado.stdout + resultado.stderr


def codigo(nombre: str, ruta: str, inicio: str, lineas: int) -> None:
    contenido = (RAIZ / ruta).read_text(encoding="utf-8").splitlines()
    desde = next(i for i, linea in enumerate(contenido) if inicio in linea)
    terminal(nombre, "\n".join(f"{desde + i + 1:>4}  {linea}" for i, linea in enumerate(contenido[desde:desde + lineas])), 100)


def pydoc() -> int:
    PYDOC.mkdir(parents=True, exist_ok=True)
    import depaseguro

    modulos = ["depaseguro"] + [m.name for m in pkgutil.walk_packages(depaseguro.__path__, "depaseguro.")]
    subprocess.run([sys.executable, "-m", "pydoc", "-w", *modulos], cwd=PYDOC, capture_output=True,
                   env={**__import__("os").environ, "PYTHONPATH": str(RAIZ)})
    return len(list(PYDOC.glob("*.html")))


def reportes() -> None:
    from depaseguro import create_app
    from depaseguro.dao.base import conectar
    from depaseguro.services import reportes as modulo

    app = create_app({"TESTING": True, "INGESTA_AUTOMATICA": False})
    db = conectar(app.config["DB_PATH"])
    archivos = {
        "reporte_distritos": modulo.pdf_riesgo_distritos(db),
        "reporte_ficha": modulo.pdf_ficha_inmueble(db, 13),
        "reporte_expediente": modulo.pdf_expediente(db, 1),
    }
    db.close()
    for nombre, contenido in archivos.items():
        (EVIDENCIAS / f"{nombre}.pdf").write_bytes(contenido)
        pagina = pypdfium2.PdfDocument(contenido)[0]
        pagina.render(scale=1.5).to_pil().save(EVIDENCIAS / f"{nombre}.png")


def main() -> None:
    EVIDENCIAS.mkdir(parents=True, exist_ok=True)
    print("Pydoc:", pydoc())
    reportes()
    codigo("codigo_dao", "depaseguro/dao/base.py", "def insertar(self", 11)
    codigo("codigo_motor", "depaseguro/logic/motor.py", "def unificar(a, b", 18)
    codigo("codigo_score", "depaseguro/services/evaluador.py", "def calcular_score", 9)
    codigo("codigo_fuente", "depaseguro/ingestion/fuentes.py", "def ejecutar(self)", 26)
    codigo("codigo_busqueda", "depaseguro/services/busqueda.py", "def buscar(avisos", 11)
    codigo("codigo_hash", "depaseguro/services/analitica.py", "def dhash(imagen", 16)
    print("Evidencias listas.")


def git() -> None:
    EVIDENCIAS.mkdir(parents=True, exist_ok=True)
    terminal("git_ramas", "$ git branch -a\n" + ejecutar("git", "branch", "-a"))
    terminal("git_grafo", "$ git log --oneline --graph --all\n" + ejecutar("git", "log", "--oneline", "--graph", "--all", "-n", "24"))
    terminal("git_commit", "$ git log --no-merges -1 --stat --format=short develop\n"
             + "\n".join(ejecutar("git", "log", "--no-merges", "-1", "--stat", "--format=short", "develop").splitlines()[:16]))


def pruebas() -> None:
    EVIDENCIAS.mkdir(parents=True, exist_ok=True)
    import importlib.util
    cobertura = importlib.util.find_spec("pytest_cov") is not None
    opciones = ["--cov=depaseguro", "--cov-report=term"] if cobertura else []
    salida = ejecutar(sys.executable, "-m", "pytest", *opciones, "-p", "no:cacheprovider", "-o", "addopts=")
    (EVIDENCIAS / "pruebas.txt").write_text(salida, encoding="utf-8")
    orden = "$ python -m pytest" + (" --cov=depaseguro" if cobertura else "")
    terminal("pruebas", orden + "\n" + "\n".join(salida.splitlines()[-44:]))
    print(salida.splitlines()[-1])


if __name__ == "__main__":
    {"git": git, "pruebas": pruebas}.get(sys.argv[1] if len(sys.argv) > 1 else "", main)()
