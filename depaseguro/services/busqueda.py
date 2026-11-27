"""Búsqueda y recomendación por cercanía a campus, construida con funciones de orden superior."""
from __future__ import annotations

from dataclasses import dataclass

from ..functional.pipeline import filtrar, mapear, ordenar_por, todos, tubo
from .analitica import distancia_km


@dataclass(frozen=True)
class FiltrosBusqueda:
    ubigeo: str | None = None
    tipo: str | None = None
    precio_max: float | None = None
    trust_min: int | None = None
    campus: dict | None = None
    radio_km: float | None = None
    orden: str = "compatibilidad"


def por_distrito(ubigeo):
    return lambda aviso: not ubigeo or aviso["ubigeo"] == ubigeo


def por_tipo(tipo):
    return lambda aviso: not tipo or aviso["tipo"] == tipo


def por_precio(maximo):
    return lambda aviso: maximo is None or (aviso["precio_mensual_pen"] or 0) <= maximo


def por_confianza(minimo):
    return lambda aviso: minimo is None or (aviso["trust_score"] or 0) >= minimo


def por_radio(radio):
    return lambda aviso: radio is None or aviso.get("distancia_km") is None or aviso["distancia_km"] <= radio


def agregar_distancia(campus):
    """Devuelve una función que añade la distancia sin modificar el aviso original."""

    def transformar(aviso: dict) -> dict:
        if not campus or aviso.get("lat") is None:
            return {**aviso, "distancia_km": None}
        return {**aviso, "distancia_km": distancia_km(aviso["lat"], aviso["lon"], campus["lat"], campus["lon"])}

    return transformar


def agregar_compatibilidad(filtros: FiltrosBusqueda):
    """Puntaje 0-100: confianza 50 %, cercanía 30 % y precio 20 %."""

    def transformar(aviso: dict) -> dict:
        confianza = (aviso["trust_score"] or 0) / 100
        distancia = aviso.get("distancia_km")
        cercania = 0.5 if distancia is None else max(0.0, 1 - distancia / max(filtros.radio_km or 5, 0.5))
        precio = 0.5
        if filtros.precio_max:
            precio = max(0.0, 1 - (aviso["precio_mensual_pen"] or 0) / filtros.precio_max)
        return {**aviso, "compatibilidad": round(100 * (0.5 * confianza + 0.3 * cercania + 0.2 * precio))}

    return transformar


ORDENES = {
    "compatibilidad": (lambda a: a["compatibilidad"], True),
    "confianza": (lambda a: a["trust_score"] or 0, True),
    "precio": (lambda a: a["precio_mensual_pen"] or 0, False),
    "cercania": (lambda a: a["distancia_km"] if a["distancia_km"] is not None else 9999, False),
}


def buscar(avisos: list[dict], filtros: FiltrosBusqueda) -> list[dict]:
    clave, descendente = ORDENES.get(filtros.orden, ORDENES["compatibilidad"])
    condicion = todos(por_distrito(filtros.ubigeo), por_tipo(filtros.tipo), por_precio(filtros.precio_max),
                      por_confianza(filtros.trust_min), por_radio(filtros.radio_km))
    return tubo(
        avisos,
        mapear(agregar_distancia(filtros.campus)),
        filtrar(condicion),
        mapear(agregar_compatibilidad(filtros)),
        ordenar_por(clave, descendente),
    )


def campus_cercanos(aviso: dict, campus: list[dict], limite: int = 3) -> list[dict]:
    if aviso.get("lat") is None:
        return []
    return tubo(
        campus,
        mapear(lambda c: {**c, "distancia_km": distancia_km(aviso["lat"], aviso["lon"], c["lat"], c["lon"])}),
        ordenar_por(lambda c: c["distancia_km"]),
    )[:limite]
