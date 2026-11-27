"""Convierte las capturas en un video corto para la página de inicio."""
from __future__ import annotations

from pathlib import Path

import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw, ImageFont

RAIZ = Path(__file__).resolve().parents[1]
CAPTURAS = RAIZ / "docs" / "capturas"
ESTATICOS = RAIZ / "depaseguro" / "static"
ANCHO, ALTO, FPS, SEGUNDOS = 1280, 720, 12, 4
ESCENAS = [
    ("01_inicio", "1. Busca vivienda con información verificable"),
    ("11_busqueda_campus", "2. Filtra por campus, distancia y presupuesto"),
    ("04_ficha_confiable", "3. Revisa el Trust Score y su explicación"),
    ("13_verificador_resultado", "4. Analiza avisos vistos en redes sociales"),
    ("05_zonas", "5. Consulta datos oficiales por distrito"),
    ("18_panel_admin", "6. La moderación recibe alertas y reportes"),
]


def fotograma(nombre: str, texto: str) -> Image.Image:
    imagen = Image.open(CAPTURAS / f"{nombre}.png").convert("RGB")
    escala = ANCHO / imagen.width
    imagen = imagen.resize((ANCHO, int(imagen.height * escala)))
    lienzo = Image.new("RGB", (ANCHO, ALTO), "#22303c")
    lienzo.paste(imagen.crop((0, 0, ANCHO, min(imagen.height, ALTO))), (0, 0))
    dibujo = ImageDraw.Draw(lienzo, "RGBA")
    dibujo.rectangle([0, ALTO - 74, ANCHO, ALTO], fill=(34, 48, 60, 235))
    fuente = ImageFont.truetype("arial.ttf", 30)
    dibujo.text((36, ALTO - 56), texto, font=fuente, fill="#ffffff")
    return lienzo


def main() -> None:
    (ESTATICOS / "video").mkdir(exist_ok=True)
    cuadros = [fotograma(*escena) for escena in ESCENAS]
    cuadros[0].save(ESTATICOS / "img" / "video-portada.png", optimize=True)
    escritor = imageio_ffmpeg.write_frames(str(ESTATICOS / "video" / "recorrido.mp4"), (ANCHO, ALTO), fps=FPS,
                                           codec="libx264", pix_fmt_out="yuv420p", quality=7, macro_block_size=8)
    escritor.send(None)
    for cuadro in cuadros:
        datos = np.ascontiguousarray(np.asarray(cuadro, dtype=np.uint8))
        for _ in range(FPS * SEGUNDOS):
            escritor.send(datos)
    escritor.close()
    print("Video creado.")


if __name__ == "__main__":
    main()
