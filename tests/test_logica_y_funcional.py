"""Pruebas del motor lógico tipo Prolog y de las utilidades funcionales."""
import pytest

from depaseguro.functional.pipeline import agrupar_por, componer, filtrar, limitar, mapear, todos, tubo
from depaseguro.logic.motor import BaseConocimiento, Compuesto, Var, cargar_reglas, parsear_programa, unificar


def test_unificacion_enlaza_variable():
    resultado = unificar(Compuesto("p", (Var("X"), "b")), Compuesto("p", ("a", "b")), {})
    assert resultado == {Var("X"): "a"}


def test_unificacion_falla_con_atomos_distintos():
    assert unificar(Compuesto("p", ("a",)), Compuesto("p", ("b",)), {}) is None


def test_reglas_con_varias_soluciones_y_transitividad():
    base = BaseConocimiento(parsear_programa("""
        padre(ana, luis). padre(luis, eva).
        ancestro(X, Y) :- padre(X, Y).
        ancestro(X, Y) :- padre(X, Z), ancestro(Z, Y).
    """))
    assert {fila["Y"] for fila in base.consultar("ancestro(ana, Y)")} == {"luis", "eva"}


def test_negacion_por_fallo_y_diferencia():
    base = BaseConocimiento(parsear_programa("""
        ave(tweety). ave(pingu). no_vuela(pingu).
        vuela(X) :- ave(X), \\+ no_vuela(X).
        distinto(X, Y) :- ave(X), ave(Y), X \\= Y.
    """))
    assert base.cumple("vuela(tweety)")
    assert not base.cumple("vuela(pingu)")
    assert base.cumple("distinto(tweety, pingu)")
    assert not base.cumple("distinto(pingu, pingu)")


def _base_fraude(*hechos):
    base = BaseConocimiento(cargar_reglas())
    for hecho in hechos:
        base.agregar_hecho(hecho, "i1")
    return base


def test_regla_adelanto_fantasma():
    base = _base_fraude("pago_previo", "sin_contrato", "sin_documentos")
    assert {"P": "adelanto_fantasma"} in base.consultar("patron(i1, P)")
    assert base.cumple("recomendacion(i1, no_transferir)")


def test_dos_patrones_distintos_son_criticos():
    base = _base_fraude("precio_muy_bajo", "imagen_clonada", "pago_previo", "lenguaje_presion")
    assert base.cumple("critico(i1)")


def test_aviso_limpio_es_confiable():
    base = _base_fraude("documentos_aprobados", "arrendador_verificado")
    assert base.cumple("confiable(i1)")
    assert not base.cumple("critico(i1)")


def test_programa_invalido_lanza_error():
    with pytest.raises(ValueError):
        parsear_programa("regla(a :- b.")


def test_tubo_y_componer():
    assert tubo([1, 2, 3], mapear(lambda x: x * 2), filtrar(lambda x: x > 2)) == [4, 6]
    assert componer(lambda x: x + 1, lambda x: x * 3)(2) == 7


def test_todos_y_limitar():
    regla = todos(lambda x: x > 0, lambda x: x % 2 == 0)
    assert regla(4) and not regla(3)
    assert limitar(0, 100)(140) == 100


def test_agrupar_no_modifica_entrada():
    datos = ({"d": "a"}, {"d": "b"}, {"d": "a"})
    grupos = agrupar_por(lambda x: x["d"], datos)
    assert len(grupos["a"]) == 2 and len(datos) == 3
