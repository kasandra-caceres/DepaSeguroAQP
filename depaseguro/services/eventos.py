"""Bus de eventos en memoria (patrón Observer).

El evaluador solo avisa que terminó; las alertas se suscriben sin que el
evaluador las conozca. Así las responsabilidades quedan desacopladas.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Callable

_suscriptores: dict[str, list[Callable]] = defaultdict(list)


def suscribir(evento: str) -> Callable:
    """Decorador que registra una función como oyente de un evento."""

    def registrar(funcion: Callable) -> Callable:
        if funcion not in _suscriptores[evento]:
            _suscriptores[evento].append(funcion)
        return funcion

    return registrar


def publicar(evento: str, **datos) -> None:
    for funcion in _suscriptores[evento]:
        funcion(**datos)
