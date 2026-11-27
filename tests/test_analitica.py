"""Pruebas de cálculo: precios, hashes, validadores, texto y distancia."""
import io

import pytest
from PIL import Image

from depaseguro.services.analitica import (analizar_clausulas, analizar_imagen, analizar_texto, deflactar,
                                           distancia_km, dni_valido, hamming, normalizar_precio,
                                           normalizar_telefono, resumen_precios, ruc_valido, telefono_valido,
                                           tendencia_y_proyeccion, z_robusto)
from .conftest import foto


@pytest.mark.parametrize("precio,moneda,periodo,esperado", [
    (500, "PEN", "mes", 500), (100, "USD", "mes", 350), (120, "PEN", "semana", 520),
    (3000, "PEN", "semestre", 500), (6000, "PEN", "anio", 500),
])
def test_normalizar_precio(precio, moneda, periodo, esperado):
    resultado = normalizar_precio(precio, moneda, periodo, 10, 3.5)
    assert resultado.mensual_pen == pytest.approx(esperado)
    assert resultado.por_m2_pen == pytest.approx(esperado / 10)


def test_normalizar_precio_rechaza_cero():
    with pytest.raises(ValueError):
        normalizar_precio(0, "PEN", "mes", 10, 3.5)


def test_deflactar_actualiza_a_soles_de_hoy():
    assert deflactar(100, 100, 110) == 110


def test_z_robusto_detecta_precio_bajo():
    z, mediana = z_robusto(10, [30, 31, 32, 33, 34, 35])
    assert mediana == pytest.approx(32.5)
    assert z < -2.5


def test_z_robusto_resiste_un_valor_extremo():
    z_con_extremo, _ = z_robusto(30, [29, 30, 31, 32, 900])
    assert abs(z_con_extremo) < 1


def test_z_robusto_muestra_vacia():
    assert z_robusto(10, []) == (None, None)


def test_z_robusto_muestra_sin_variacion_no_divide_entre_cero():
    z, _ = z_robusto(20, [30, 30, 30])
    assert z < 0


def test_dhash_reconoce_foto_redimensionada():
    original = foto(3, (640, 480))
    imagen = Image.open(io.BytesIO(original)).resize((320, 240))
    salida = io.BytesIO()
    imagen.save(salida, "JPEG", quality=60)
    a, b = analizar_imagen(original), analizar_imagen(salida.getvalue())
    assert a["sha256"] != b["sha256"]
    assert hamming(a["dhash"], b["dhash"]) <= 6


def test_dhash_separa_fotos_diferentes():
    a, b = analizar_imagen(foto(2)), analizar_imagen(foto(9))
    assert hamming(a["dhash"], b["dhash"]) > 6


def test_archivo_falso_no_pasa_como_imagen():
    with pytest.raises(Exception):
        analizar_imagen(b"esto no es una imagen")


def test_telefonos():
    assert normalizar_telefono("+51 987-654-321") == "987654321"
    assert telefono_valido("987654321")
    assert not telefono_valido("12345")


def test_documentos():
    assert dni_valido("12345678") and not dni_valido("1234")
    assert ruc_valido("20000000001")
    assert not ruc_valido("20000000002")
    assert not ruc_valido("99000000001")


def test_distancia_entre_plaza_y_unsa():
    assert distancia_km(-16.3989, -71.5369, -16.4033, -71.5249) == pytest.approx(1.37, abs=.1)


def test_analizar_texto_ignora_tildes_y_mayusculas():
    resultado = analizar_texto("ÚLTIMO CUARTO, deposita hoy. Estoy de viaje.")
    assert "ultimo cuarto" in resultado["presion"]
    assert "deposita" in resultado["pago"]
    assert "estoy de viaje" in resultado["evasion"]


def test_clausulas_abusivas():
    texto = "La garantía no será devuelta. El arrendador podrá ingresar en cualquier momento sin aviso."
    titulos = {c["titulo"] for c in analizar_clausulas(texto)}
    assert {"La garantía no se devuelve", "Ingreso al cuarto sin aviso"} <= titulos


def test_contrato_equilibrado_no_genera_alertas():
    assert analizar_clausulas("La garantía será devuelta al terminar. Las partes acuerdan el ingreso con aviso previo.") == []


def test_tendencia_proyecta_crecimiento():
    resultado = tendencia_y_proyeccion([10, 20, 30, 40], 2)
    assert resultado["pendiente"] == pytest.approx(10)
    assert resultado["proyeccion"] == [50, 60]


def test_resumen_precios_agrupa_por_distrito():
    filas = [{"id": 1, "distrito": "CAYMA", "precio_mensual_pen": 400, "precio_m2_pen": 30, "trust_score": 80},
             {"id": 2, "distrito": "CAYMA", "precio_mensual_pen": 600, "precio_m2_pen": 40, "trust_score": 60}]
    assert resumen_precios(filas)[0]["mediana_mensual"] == 500
