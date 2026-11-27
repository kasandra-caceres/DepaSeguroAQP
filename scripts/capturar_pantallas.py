"""Recorre la aplicación en un navegador real, comprueba errores y toma capturas para la documentación.

Requiere el servidor en http://127.0.0.1:5000 y datos de demostración.
Uso:  python scripts/capturar_pantallas.py                  todas las capturas
      python scripts/capturar_pantallas.py 11_busqueda_campus 21_admin_fuentes   solo las indicadas
"""
from __future__ import annotations

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:5000"
SALIDA = Path(__file__).resolve().parents[1] / "docs" / "capturas"
CLAVE = "Demo12345"
errores: list[str] = []
SOLO = set(sys.argv[1:])


def preparar(pagina) -> None:
    pagina.on("pageerror", lambda e: errores.append(f"JS {pagina.url}: {e}"))
    pagina.on("console", lambda m: errores.append(f"consola {pagina.url}: {m.text}")
              if m.type == "error" and "tile.openstreetmap" not in m.text and "ERR_" not in m.text else None)
    pagina.on("response", lambda r: errores.append(f"HTTP {r.status} {r.url}")
              if r.status >= 400 and r.url.startswith(BASE) else None)


def captura(pagina, nombre: str, completa: bool = True) -> None:
    if SOLO and nombre not in SOLO:
        return
    pagina.mouse.move(0, 0)
    pagina.wait_for_timeout(700)
    pagina.screenshot(path=SALIDA / f"{nombre}.png", full_page=completa)


def ingresar(pagina, correo: str) -> None:
    pagina.goto(f"{BASE}/login")
    pagina.fill("input[name=email]", correo)
    pagina.fill("input[name=password]", CLAVE)
    pagina.click("main button[type=submit]")
    pagina.wait_for_load_state("networkidle")


def salir(pagina) -> None:
    pagina.click("header form button")
    pagina.wait_for_load_state("networkidle")


def main() -> int:
    SALIDA.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        navegador = p.chromium.launch(channel="chrome", headless=True)
        contexto = navegador.new_context(viewport={"width": 1280, "height": 800}, locale="es-PE")
        pagina = contexto.new_page()
        preparar(pagina)

        for ruta, nombre in [("/", "01_inicio"), ("/inmuebles", "02_catalogo"), ("/zonas", "05_zonas"), ("/fuentes", "06_fuentes"),
                             ("/contrato", "07_contrato"), ("/blog", "08_blog"), ("/contacto", "09_contacto"), ("/registro", "10_registro")]:
            pagina.goto(BASE + ruta, wait_until="networkidle")
            captura(pagina, nombre)

        pagina.goto(f"{BASE}/mapa", wait_until="networkidle")
        pagina.wait_for_timeout(1800)
        captura(pagina, "03_mapa", completa=False)

        pagina.goto(f"{BASE}/inmuebles", wait_until="networkidle")
        pagina.select_option("select[name=campus]", index=15)
        pagina.fill("input[name=radio_km]", "2")
        pagina.fill("input[name=precio_max]", "800")
        if not pagina.eval_on_selector("aside form", "f => f.checkValidity()"):
            errores.append("El filtro del catálogo rechaza valores válidos; la captura mostraría un aviso del navegador")
        pagina.click("aside button[type=submit]")
        pagina.wait_for_load_state("networkidle")
        assert "precio_max=800" in pagina.url, "El filtro no se envió"
        captura(pagina, "11_busqueda_campus")

        pagina.goto(f"{BASE}/inmuebles/3", wait_until="networkidle")
        pagina.wait_for_timeout(1200)
        captura(pagina, "04_ficha_confiable")
        pagina.goto(f"{BASE}/inmuebles/12", wait_until="networkidle")
        pagina.wait_for_timeout(1200)
        captura(pagina, "12_ficha_critica")

        pagina.goto(f"{BASE}/verificador")
        pagina.fill("textarea[name=texto]", "Urgente, solo hoy último cuarto. Estoy de viaje, separa con Yape y te envío las llaves por courier.")
        pagina.fill("input[name=precio_mensual]", "150")
        pagina.fill("input[name=area_m2]", "15")
        pagina.fill("input[name=telefono]", "900000091")
        pagina.check("input[name=pide_pago_previo]")
        pagina.check("input[name=sin_contrato]")
        pagina.click("main form button[type=submit]")
        pagina.wait_for_load_state("networkidle")
        assert "Crítico" in pagina.inner_text("aside"), "El verificador debía marcar el aviso como crítico"
        captura(pagina, "13_verificador_resultado")

        ingresar(pagina, "estudiante@depaseguro.test")
        captura(pagina, "14_panel_estudiante")
        salir(pagina)

        ingresar(pagina, "carlos@depaseguro.test")
        captura(pagina, "15_panel_arrendador")
        pagina.goto(f"{BASE}/arrendador/inmuebles/nuevo", wait_until="networkidle")
        pagina.wait_for_timeout(1000)
        captura(pagina, "16_formulario_aviso")
        pagina.goto(f"{BASE}/arrendador/inmuebles/7", wait_until="networkidle")
        captura(pagina, "17_gestionar_aviso")
        salir(pagina)

        ingresar(pagina, "admin@depaseguro.test")
        pagina.wait_for_timeout(900)
        captura(pagina, "18_panel_admin")
        pagina.goto(f"{BASE}/admin/fuentes", wait_until="networkidle")
        pagina.click("form:has(input[name=clave][value=osm_nominatim]) button")  # actualiza el mensaje de Nominatim
        pagina.wait_for_load_state("networkidle")
        for ruta, nombre in [("reportes", "19_admin_reportes"), ("redes", "20_admin_redes"), ("fuentes", "21_admin_fuentes"),
                             ("documentos", "22_admin_documentos"), ("alertas", "23_admin_alertas"), ("usuarios", "24_admin_usuarios")]:
            pagina.goto(f"{BASE}/admin/{ruta}", wait_until="networkidle")
            captura(pagina, nombre)
        salir(pagina)

        movil = navegador.new_context(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True, locale="es-PE")
        telefono = movil.new_page()
        preparar(telefono)
        telefono.goto(BASE, wait_until="networkidle")
        captura(telefono, "25_movil_inicio", completa=False)
        telefono.click("[data-menu]")
        captura(telefono, "26_movil_menu", completa=False)
        telefono.goto(f"{BASE}/inmuebles/3", wait_until="networkidle")
        ancho = telefono.evaluate("document.documentElement.scrollWidth")
        if ancho > 395:
            errores.append(f"Desborde horizontal en móvil: {ancho}px")
        captura(telefono, "27_movil_ficha")
        navegador.close()
    print("\n".join(errores) if errores else "Sin errores de navegador.")
    print(f"Capturas: {len(list(SALIDA.glob('*.png')))}")
    return 1 if errores else 0


if __name__ == "__main__":
    sys.exit(main())
