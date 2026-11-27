"""Utilidades de programación funcional: composición, orden superior y reducción.

Aplica las sesiones de programación funcional: funciones como parámetros,
funciones anónimas, funciones que devuelven funciones y valores inmutables.
"""
from __future__ import annotations

from functools import reduce
from typing import Callable, Iterable, TypeVar

T = TypeVar("T")
K = TypeVar("K")


def tubo(valor, *funciones: Callable):
    """Pasa ``valor`` por cada función, de izquierda a derecha."""
    return reduce(lambda acumulado, funcion: funcion(acumulado), funciones, valor)


def componer(*funciones: Callable) -> Callable:
    """Crea una función nueva equivalente a ``f(g(h(x)))``."""
    return lambda valor: reduce(lambda acumulado, funcion: funcion(acumulado), reversed(funciones), valor)


def filtrar(predicado: Callable[[T], bool]) -> Callable[[Iterable[T]], list[T]]:
    return lambda elementos: list(filter(predicado, elementos))


def mapear(transformacion: Callable) -> Callable[[Iterable], list]:
    return lambda elementos: list(map(transformacion, elementos))


def ordenar_por(clave: Callable, descendente: bool = False) -> Callable[[Iterable[T]], list[T]]:
    return lambda elementos: sorted(elementos, key=clave, reverse=descendente)


def todos(*predicados: Callable[[T], bool]) -> Callable[[T], bool]:
    """Combina predicados: el resultado es verdadero si todos se cumplen."""
    return lambda elemento: all(predicado(elemento) for predicado in predicados)


def agrupar_por(clave: Callable[[T], K], elementos: Iterable[T]) -> dict[K, tuple[T, ...]]:
    """Agrupa sin modificar estado externo; cada paso crea un diccionario nuevo."""
    return reduce(
        lambda grupos, elemento: {
            **grupos,
            clave(elemento): (*grupos.get(clave(elemento), ()), elemento),
        },
        elementos,
        {},
    )


def limitar(minimo: float, maximo: float) -> Callable[[float], float]:
    """Crea una función que acota un número al rango indicado."""
    return lambda valor: max(minimo, min(maximo, valor))
