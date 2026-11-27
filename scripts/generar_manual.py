"""Llena la plantilla oficial del manual de usuario, instalación y configuración.

Uso:  python scripts/generar_manual.py RUTA_PLANTILLA.docx
"""
from __future__ import annotations

import copy

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from docx.shared import Pt  # noqa: E402
from docx.table import Table  # noqa: E402

from docx_util import Cursor, Plantilla, fijar_anchos, fijar_celda, fijar_parrafo, finalizar_con_word  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
CAP = RAIZ / "docs" / "capturas"
SALIDA = RAIZ / "entregables" / "Manual_Usuario_Instalacion_DepaSeguro_AQP.docx"


def codigo(c: Cursor, *lineas: str) -> None:
    for linea in lineas:
        p = c.p(linea, despues=1)
        p.alignment = 0
        for run in p.runs:
            run.font.name = "Consolas"
            run.font.size = Pt(10)
    c.p("", despues=2)


def figura(c: Cursor, nombre: str, leyenda: str, ancho: float = 15, alto: float = 13) -> None:
    c.imagen(CAP / f"{nombre}.png", leyenda, ancho, alto_max=alto)


def presentacion(pl: Plantilla) -> None:
    c = pl.en(28, 31, estilo="Normal")
    c.p("DepaSeguro AQP ayuda a estudiantes universitarios de Arequipa a revisar avisos de vivienda antes de pagar. Calcula un Trust Score, muestra señales de riesgo, permite buscar por campus y lee datos oficiales de forma automática. Los puntajes son estimaciones y no acusan a ninguna persona.")
    c = pl.en(31, 34, estilo="Normal")
    c.tabla([["Elemento", "Mínimo recomendado"], ["Sistema operativo", "Windows 10 o superior, Linux o macOS"], ["Python", "3.12 o superior"],
             ["Memoria", "4 GB de RAM"], ["Disco", "1 GB libre"], ["Navegador", "Chrome o Edge actualizado"], ["Internet", "Necesario para leer fuentes y ver el mapa"]], [5, 10.5])
    c = pl.en(34, 37, estilo="Normal")
    c.p("Copia la carpeta DepaSeguroAQP en una ruta corta, por ejemplo C:\\Proyectos\\DepaSeguroAQP. En Windows, las rutas muy largas pueden impedir la instalación de librerías o la carga de archivos.")
    c.p("Abre una terminal dentro de esa carpeta antes de continuar.")
    c = pl.en(37, 40, estilo="Normal")
    c.p("1. Crea y activa el entorno virtual. En Windows:")
    codigo(c, "python -m venv .venv", ".venv\\Scripts\\activate")
    c.p("En Linux o macOS:")
    codigo(c, "python3 -m venv .venv", "source .venv/bin/activate")
    c.p("2. Instala las dependencias:")
    codigo(c, "pip install -r requirements.txt")
    c.p("3. Lee las fuentes oficiales. La base SQLite se crea sola en data/depaseguro.db a partir de database/schema.sql. Este paso descarga los datos y puede tardar uno o dos minutos:")
    codigo(c, "python run.py --ingesta")
    c.p("4. Carga los datos ficticios de demostración:")
    codigo(c, "python scripts/poblar_demo.py")
    c.p("5. Inicia la aplicación:")
    codigo(c, "python run.py")
    c.p("6. Abre http://127.0.0.1:5000 en el navegador.")
    c = pl.en(40, 43, estilo="Normal")
    c.tabla([["Variable", "Valor por defecto", "Uso"],
             ["DEPASEGURO_DATA", "data", "Carpeta de base de datos y archivos"], ["DEPASEGURO_INGESTA", "1", "Activa la lectura automática"],
             ["DEPASEGURO_INTERVALO_H", "24", "Horas entre lecturas"], ["DEPASEGURO_GEOCODIFICAR", "1", "Verifica direcciones con OpenStreetMap"],
             ["DEPASEGURO_SECRET", "Generada", "Clave para firmar sesiones"]], [6.3, 3.2, 6.0])
    c.p("Cuentas de demostración. Las tres usan la clave de prueba Demo12345, que solo existe en los datos ficticios:")
    c.tabla([["Rol", "Correo"], ["Administración", "admin@depaseguro.test"], ["Estudiante", "estudiante@depaseguro.test"], ["Arrendador", "carlos@depaseguro.test"]], [5, 10.5])
    c = pl.en(43, 47, estilo="Normal")
    c.tabla([["Problema", "Solución"],
             ["python no se reconoce", "Instala Python y marca la opción Add to PATH."], ["El puerto 5000 está ocupado", "Cierra la otra aplicación que lo usa."],
             ["Una fuente aparece con error", "El sistema conserva los últimos datos. Vuelve a intentarlo desde Administración > Fuentes."],
             ["El mapa no carga", "Revisa la conexión a internet."], ["Quiero reiniciar la demostración", "Detén el servidor, borra la carpeta data y repite los pasos 3 y 4."],
             ["Quiero ejecutar las pruebas", "Usa python -m pytest."]], [6, 9.5])
    c.p("Para hacer una copia de seguridad, detén el servidor y copia la carpeta data.")


def usuario(pl: Plantilla) -> None:
    c = pl.en(49, 50, estilo="Normal")
    c.p("El sitio tiene encabezado con menú, contenido principal, barras laterales y pie de página.")
    figura(c, "01_inicio", "Pantalla de inicio.", 10.5, 14)
    c = pl.en(50, 51, estilo="Normal")
    c.p("En la ficha de un aviso, el panel derecho muestra Trust Score, composición del puntaje, señales, recomendaciones y contexto de zona.")
    figura(c, "04_ficha_confiable", "Ficha de un aviso.", 10, 15)
    c = pl.en(51, 52, estilo="Normal")
    c.p("En el catálogo, el panel izquierdo contiene los filtros: campus, radio, distrito, tipo, precio y puntaje.")
    c = pl.en(52, 55, estilo="Normal")
    c.p("El pie de página incluye enlaces de la plataforma, entidades oficiales, contacto y botones para compartir.")

    fijar_parrafo(pl.parrafo(56), "BUSCAR INMUEBLES.")
    c = pl.en(56, 57, estilo="Normal")
    c.vinetas(["Entra en Inmuebles.", "Elige tu campus y el radio.", "Indica presupuesto y puntaje mínimo.", "Presiona Aplicar y abre un aviso."])
    figura(c, "11_busqueda_campus", "Búsqueda por campus.", 9.5, 13)
    fijar_parrafo(pl.parrafo(57), "AGREGAR, MODIFICAR, ELIMINAR AVISOS (ARRENDADOR).")
    c = pl.en(57, 58, estilo="Normal")
    c.vinetas(["Crea una cuenta como arrendador e ingresa.", "Presiona Publicar inmueble y completa el formulario.", "Marca la ubicación en el mapa y sube fotos reales.",
               "En Gestionar, sube tus documentos.", "Usa Editar para cambiar datos o Retirar aviso para quitarlo.", "Genera un código de visita para que el estudiante publique una reseña verificada."])
    figura(c, "17_gestionar_aviso", "Gestión de un aviso.", 11, 12)
    fijar_parrafo(pl.parrafo(58), "GUARDADOS, ALERTAS Y RESEÑAS.")
    c = pl.en(58, 59, estilo="Normal")
    c.p("Como estudiante, usa Guardar y vigilar en una ficha. Si el puntaje baja, recibirás una alerta. También puedes guardar una búsqueda desde tu panel.")
    figura(c, "14_panel_estudiante", "Panel del estudiante.", 11, 12)
    fijar_parrafo(pl.parrafo(59), "VERIFICAR ANTES DE PAGAR.")
    c = pl.en(59, 60, estilo="Normal")
    c.p("La plataforma no procesa pagos. Antes de transferir dinero, abre Verificar aviso, pega el texto y marca lo ocurrido. Revisa el resultado y visita el inmueble.")
    figura(c, "13_verificador_resultado", "Resultado del verificador.", 11, 12)
    c.p("Si fuiste víctima, abre la ficha, usa Reportar este aviso y descarga el expediente desde tu panel.")
    fijar_parrafo(pl.parrafo(60), "MAPA, ZONAS, CONTRATOS Y GUÍAS.")
    c = pl.en(60, 63, estilo="Normal")
    c.vinetas(["Mapa: muestra avisos por nivel y campus.", "Zonas: muestra denuncias por distrito y tendencia.", "Contratos: revisa cláusulas y genera un modelo PDF.", "Guías: explica cómo prevenir estafas."])
    figura(c, "05_zonas", "Observatorio de zonas.", 9, 12)


def administracion(pl: Plantilla) -> None:
    c = pl.en(66, 67, estilo="Normal")
    c.p("El panel de administración reúne indicadores, gráficos, alertas y exportaciones.")
    figura(c, "18_panel_admin", "Panel de administración.", 10, 13)
    c = pl.en(67, 68, estilo="Normal")
    c.p("El área derecha muestra el contenido de la opción elegida.")
    c = pl.en(68, 69, estilo="Normal")
    c.p("El menú izquierdo permite abrir Resumen, Avisos, Documentos, Reportes, Alertas, Redes, Contactos de riesgo, Usuarios, Fuentes y Auditoría.")
    c = pl.en(69, 71, estilo="Normal")
    c.p("El panel inferior contiene los enlaces generales del sitio.")
    c = pl.en(72, 73, estilo="Normal")
    c.p("En Usuarios, presiona Sí o No para cambiar verificación o estado. No puedes desactivar tu propia cuenta.")
    figura(c, "24_admin_usuarios", "Mantenimiento de usuarios.", 12, 9)
    fijar_parrafo(pl.parrafo(73), "MANTENIMIENTO DE AVISOS Y DOCUMENTOS.")
    c = pl.en(73, 74, estilo="Normal")
    c.p("En Avisos, cambia el estado a pendiente, publicado, observado o rechazado. En Documentos, abre cada archivo, aprueba o rechaza, y el puntaje se recalcula.")
    fijar_parrafo(pl.parrafo(74), "MANTENIMIENTO DE CONTACTOS DE RIESGO.")
    c = pl.en(74, 75, estilo="Normal")
    c.p("Agrega o quita teléfonos solo con sustento. Cada cambio queda en Auditoría y recalcula los avisos.")
    fijar_parrafo(pl.parrafo(75), "MANTENIMIENTO DE REPORTES.")
    c = pl.en(75, 76, estilo="Normal")
    c.p("Lee el relato y el descargo. Marca En revisión, Confirmar o Descartar. Confirmar agrega el teléfono a contactos de riesgo.")
    figura(c, "19_admin_reportes", "Moderación de reportes.", 11, 9)
    fijar_parrafo(pl.parrafo(76), "FUENTES, ALERTAS, REDES Y REPORTES.")
    c = pl.en(76, 79, estilo="Normal")
    c.vinetas(["Fuentes: revisa el estado y usa Actualizar todas ahora.", "Alertas: consulta señales automáticas.", "Redes: revisa cuentas relacionadas antes de tomar una decisión.",
               "Resumen: exporta riesgo por distrito en PDF, catálogo en Excel y alertas en CSV."])
    figura(c, "21_admin_fuentes", "Lectura automática de fuentes.", 12, 10)


def main() -> None:
    pl = Plantilla(Path(sys.argv[1]))
    tabla = Table(pl.els[14], pl.doc)
    filas = [["06/11/2026", "1.0", "Grupo 08", "Primera versión del manual.", "Cáceres Quispe, K.", "06/11/2026"],
             ["27/11/2026", "1.1", "Grupo 08", "Comandos para Linux y macOS, creación de la base y claves de demostración.", "Cáceres Quispe, K.", "27/11/2026"]]
    while len(tabla.rows) - 1 < len(filas):
        tabla._tbl.append(copy.deepcopy(tabla.rows[-1]._tr))
    for fila, valores in zip(tabla.rows[1:], filas):
        for celda, valor in zip(fila.cells, valores):
            fijar_celda(celda, valor)
    for fila in list(tabla.rows[1 + len(filas):]):
        fila._tr.getparent().remove(fila._tr)
    fijar_anchos(tabla, [2.5, 1.75, 2.2, 3.85, 2.4, 2.6])
    fijar_parrafo(pl.parrafo(6), "DepaSeguro AQP - Versión 1.1")
    presentacion(pl)
    usuario(pl)
    administracion(pl)
    pl.quitar_imagenes_sin_uso()
    SALIDA.parent.mkdir(exist_ok=True)
    pl.doc.save(SALIDA)
    print(finalizar_con_word(SALIDA))


if __name__ == "__main__":
    main()
