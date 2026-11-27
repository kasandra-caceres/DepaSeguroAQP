"""Pruebas de integración del Trust Score, alertas y redes."""
import pytest

from depaseguro.dao.repositorios import (AlertaDAO, DocumentoDAO, FavoritoDAO, IndicadorDAO, InmuebleDAO,
                                         ListaContactosDAO)
from depaseguro.models.entidades import Administrador, Arrendador, Estudiante, NivelRiesgo, fabrica_usuario
from depaseguro.services.alertas import alertas_zona
from depaseguro.services.analisis_red import ConjuntosDisjuntos, detectar_redes, ranking_zonas, serie_estafas
from depaseguro.services.busqueda import FiltrosBusqueda, buscar
from depaseguro.services.evaluador import detalle_evaluacion, reevaluar_todos
from depaseguro.services.verificador import AvisoExterno, verificar
from .conftest import agregar_foto, crear_aviso, crear_usuario, evaluar, foto


def comparables(db, cantidad=6, precio=450):
    dueno = crear_usuario(db, "comparable@prueba.test")
    for indice in range(cantidad):
        crear_aviso(db, dueno, precio=precio + indice * 10, telefono_contacto=f"9000000{indice:02d}", ubigeo="040101")
    for fila in db.execute("SELECT id FROM inmuebles").fetchall():
        evaluar(db, fila["id"])


def hechos(resultado):
    return {h.hecho for h in resultado.hallazgos}


@pytest.mark.parametrize("puntaje,nivel", [(100, NivelRiesgo.CONFIABLE), (75, NivelRiesgo.CONFIABLE), (74, NivelRiesgo.PRECAUCION),
                                           (50, NivelRiesgo.PRECAUCION), (49, NivelRiesgo.RIESGO_ALTO), (24, NivelRiesgo.CRITICO)])
def test_niveles(puntaje, nivel):
    assert NivelRiesgo.desde_puntaje(puntaje) is nivel


def test_fabrica_crea_la_subclase_correcta():
    base = {"id": 1, "nombre": "Ana Paz", "email": "a@b.c", "verificado": 1, "activo": 1}
    assert isinstance(fabrica_usuario({**base, "rol": "estudiante"}), Estudiante)
    assert isinstance(fabrica_usuario({**base, "rol": "arrendador"}), Arrendador)
    usuario = fabrica_usuario({**base, "rol": "admin"})
    assert isinstance(usuario, Administrador) and usuario.puede("moderar") and usuario.iniciales == "AP"


def test_aviso_documentado_obtiene_puntaje_alto(db):
    dueno = crear_usuario(db, "dueno@prueba.test")
    aviso = crear_aviso(db, dueno)
    agregar_foto(db, aviso, foto(1))
    for tipo in ("titularidad", "recibo_servicio"):
        DocumentoDAO(db).insertar({"inmueble_id": aviso, "tipo": tipo, "archivo": "x.pdf", "sha256": tipo, "estado": "aprobado"})
    resultado = evaluar(db, aviso)
    assert resultado.trust_score >= 75
    assert resultado.nivel is NivelRiesgo.CONFIABLE
    assert "continuar_con_visita" in resultado.recomendaciones


def test_precio_anormal_se_detecta(db):
    comparables(db)
    dueno = crear_usuario(db, "barato@prueba.test")
    aviso = crear_aviso(db, dueno, precio=80, telefono_contacto="911111111")
    assert "precio_muy_bajo" in hechos(evaluar(db, aviso))


def test_con_pocos_comparables_no_acusa_precio(db):
    dueno = crear_usuario(db, "solo@prueba.test")
    aviso = crear_aviso(db, dueno, precio=20)
    assert "precio_muy_bajo" not in hechos(evaluar(db, aviso))


def test_foto_copiada_penaliza_al_ultimo_no_al_original(db):
    original = crear_aviso(db, crear_usuario(db, "original@prueba.test"), telefono_contacto="911111112")
    copia = crear_aviso(db, crear_usuario(db, "copia@prueba.test"), telefono_contacto="911111113")
    agregar_foto(db, original, foto(5))
    agregar_foto(db, copia, foto(5))
    assert "imagen_clonada" in hechos(evaluar(db, copia))
    assert "imagen_clonada" not in hechos(evaluar(db, original))


def test_mismo_dueno_puede_repetir_foto(db):
    dueno = crear_usuario(db, "dos@prueba.test")
    a, b = crear_aviso(db, dueno), crear_aviso(db, dueno)
    agregar_foto(db, a, foto(6))
    agregar_foto(db, b, foto(6))
    assert "imagen_clonada" not in hechos(evaluar(db, b))


def test_telefono_en_lista_es_critico_y_limita_puntaje(db):
    aviso = crear_aviso(db, crear_usuario(db, "lista@prueba.test"))
    ListaContactosDAO(db).insertar({"telefono": "987654321", "motivo": "Prueba"})
    resultado = evaluar(db, aviso)
    assert resultado.es_critico and resultado.trust_score <= 24
    assert InmuebleDAO(db).obtener(aviso)["estado"] == "observado"


def test_patron_deducido_por_reglas(db):
    aviso = crear_aviso(db, crear_usuario(db, "patron@prueba.test", verificado=0), pago_previo_visita=1, contrato_escrito=0)
    resultado = evaluar(db, aviso)
    assert "adelanto_fantasma" in resultado.patrones
    assert "no_transferir" in resultado.recomendaciones


def test_lenguaje_de_estafa_se_detecta(db):
    aviso = crear_aviso(db, crear_usuario(db, "texto@prueba.test"),
                        descripcion="Urgente, reserva ya. Estoy de viaje y te envio las llaves por courier.")
    assert {"lenguaje_presion", "lenguaje_evasivo"} <= hechos(evaluar(db, aviso))


def test_alerta_no_se_duplica(db):
    aviso = crear_aviso(db, crear_usuario(db, "alerta@prueba.test"), pago_previo_visita=1)
    evaluar(db, aviso)
    evaluar(db, aviso)
    assert AlertaDAO(db).contar("clave = ?", (f"riesgo:{aviso}:pago_previo",)) == 1


def test_seguidor_recibe_alerta_si_cae_el_puntaje(db):
    aviso = crear_aviso(db, crear_usuario(db, "cae@prueba.test"))
    estudiante = crear_usuario(db, "sigue@prueba.test", "estudiante")
    FavoritoDAO(db).alternar(estudiante, aviso)
    evaluar(db, aviso)
    ListaContactosDAO(db).insertar({"telefono": "987654321", "motivo": "Prueba"})
    evaluar(db, aviso)
    assert any(a["tipo"] == "favorito_en_riesgo" for a in AlertaDAO(db).de_usuario(estudiante))


def test_busqueda_guardada_genera_alerta(db):
    db.execute("INSERT INTO campus(universidad, codigo_local, lat, lon) VALUES ('U', 'L1', -16.40, -71.53)")
    estudiante = crear_usuario(db, "busca@prueba.test", "estudiante")
    db.execute("INSERT INTO busquedas_guardadas(usuario_id, campus_id, radio_km, precio_max, trust_min) VALUES (?,1,3,800,0)", (estudiante,))
    db.commit()
    aviso = crear_aviso(db, crear_usuario(db, "nuevo@prueba.test"))
    evaluar(db, aviso)
    assert any(a["tipo"] == "busqueda_coincide" for a in AlertaDAO(db).de_usuario(estudiante))


def test_tipo_de_cambio_oficial_recalcula_precio_en_dolares(db):
    aviso = crear_aviso(db, crear_usuario(db, "dolar@prueba.test"), precio=100, moneda="USD")
    IndicadorDAO(db).guardar("tipo_cambio_venta", "2026-11-01", 4.0, "bcrp")
    db.commit()
    evaluar(db, aviso)
    assert InmuebleDAO(db).obtener(aviso)["precio_mensual_pen"] == 400
    IndicadorDAO(db).guardar("tipo_cambio_venta", "2026-11-02", 3.0, "bcrp")
    db.commit()
    reevaluar_todos(db)
    assert InmuebleDAO(db).obtener(aviso)["precio_mensual_pen"] == 300


def test_historial_no_crece_sin_cambios(db):
    aviso = crear_aviso(db, crear_usuario(db, "hist@prueba.test"))
    evaluar(db, aviso)
    evaluar(db, aviso)
    assert db.execute("SELECT COUNT(*) FROM evaluaciones WHERE inmueble_id = ?", (aviso,)).fetchone()[0] == 1


def test_detalle_traduce_recomendaciones(db):
    aviso = crear_aviso(db, crear_usuario(db, "det@prueba.test"), pago_previo_visita=1)
    evaluar(db, aviso)
    assert "No transfieras dinero por este aviso." in detalle_evaluacion(db, aviso)["recomendaciones"]


def test_union_find():
    grupos = ConjuntosDisjuntos()
    grupos.unir(1, 2)
    grupos.unir(2, 3)
    assert grupos.buscar(1) == grupos.buscar(3)


def test_redes_unen_cuentas_por_telefono(db):
    crear_aviso(db, crear_usuario(db, "a@prueba.test"), telefono_contacto="933333333")
    crear_aviso(db, crear_usuario(db, "b@prueba.test"), telefono_contacto="933333333")
    redes = detectar_redes(db)
    assert len(redes) == 1 and "mismo teléfono" in redes[0]["motivos"]


def poblar_denuncias(db):
    filas = [("040101", "AREQUIPA", 2025, mes, "Estafa", 10) for mes in range(1, 13)]
    filas += [("040101", "AREQUIPA", 2026, mes, "Estafa", 20) for mes in range(1, 4)]
    filas += [("040101", "AREQUIPA", 2026, 3, "Robo", 5)]
    db.executemany("INSERT INTO denuncias_distrito VALUES (?,?,?,?,?,?)", filas)
    db.execute("UPDATE distritos SET poblacion = 50000 WHERE ubigeo = '040101'")
    db.commit()


def test_ranking_zonas_calcula_tasa(db):
    poblar_denuncias(db)
    zona = ranking_zonas(db)[0]
    assert zona["Estafa"] == 150 and zona["Robo"] == 5
    assert zona["tasa_estafa"] == 30


def test_alerta_de_zona_por_aumento(db):
    poblar_denuncias(db)
    assert alertas_zona(db) == 1
    assert alertas_zona(db) == 0


def test_serie_estafas_proyecta(db):
    poblar_denuncias(db)
    serie = serie_estafas(db)
    assert len(serie["valores"]) == 15 and len(serie["proyeccion"]) == 3


def test_busqueda_filtra_y_ordena():
    avisos = [
        {"id": 1, "ubigeo": "1", "tipo": "cuarto", "precio_mensual_pen": 400, "trust_score": 90, "lat": -16.4, "lon": -71.5},
        {"id": 2, "ubigeo": "1", "tipo": "cuarto", "precio_mensual_pen": 900, "trust_score": 95, "lat": -16.4, "lon": -71.5},
        {"id": 3, "ubigeo": "2", "tipo": "cuarto", "precio_mensual_pen": 300, "trust_score": 40, "lat": -16.4, "lon": -71.5},
    ]
    resultado = buscar(avisos, FiltrosBusqueda(precio_max=500, trust_min=50))
    assert [a["id"] for a in resultado] == [1]
    assert "distancia_km" not in avisos[0]  # la lista original no cambia


def test_busqueda_por_radio():
    avisos = [{"id": 1, "ubigeo": "1", "tipo": "cuarto", "precio_mensual_pen": 400, "trust_score": 90, "lat": -16.40, "lon": -71.53},
              {"id": 2, "ubigeo": "1", "tipo": "cuarto", "precio_mensual_pen": 400, "trust_score": 90, "lat": -16.50, "lon": -71.53}]
    resultado = buscar(avisos, FiltrosBusqueda(campus={"lat": -16.40, "lon": -71.53}, radio_km=2))
    assert [a["id"] for a in resultado] == [1]


def test_verificador_detecta_aviso_peligroso(db):
    resultado = verificar(db, AvisoExterno("Urgente, solo hoy. Yapea para separar, estoy de viaje.", pide_pago_previo=True,
                                           tiene_contrato=False, permite_visita=False))
    assert resultado["puntaje"] < 25
    assert resultado["patrones"]


def test_verificador_acepta_aviso_normal(db):
    resultado = verificar(db, AvisoExterno("Cuarto con visita y contrato en Cayma.", telefono="987654321"))
    assert resultado["puntaje"] == 100


def test_verificador_reconoce_telefono_listado(db):
    ListaContactosDAO(db).insertar({"telefono": "987654321", "motivo": "Prueba"})
    assert verificar(db, AvisoExterno("Cuarto", telefono="987 654 321"))["nivel"] == "Crítico"


def test_verificador_reconoce_foto_repetida(db):
    aviso = crear_aviso(db, crear_usuario(db, "fotov@prueba.test"))
    agregar_foto(db, aviso, foto(7))
    resultado = verificar(db, AvisoExterno("Cuarto en oferta", imagen=foto(7)))
    assert any("foto" in h["titulo"].lower() for h in resultado["hallazgos"])
