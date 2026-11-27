"""Motor de inferencia lógica estilo Prolog escrito en Python puro.

Aplica lo visto en las sesiones de programación lógica: hechos, reglas,
variables, unificación, backtracking y negación por fallo. Las reglas del
negocio viven en ``reglas_fraude.pl`` y pueden cambiarse sin tocar Python.

Representación de términos:
    * Átomo o número -> ``str`` / ``int`` / ``float``
    * Variable       -> ``Var("X")``
    * Compuesto      -> ``Compuesto("patron", ("i1", Var("P")))``
"""
from __future__ import annotations

import itertools
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator


@dataclass(frozen=True)
class Var:
    nombre: str


@dataclass(frozen=True)
class Compuesto:
    functor: str
    args: tuple = ()

    def __str__(self) -> str:
        if not self.args:
            return self.functor
        return f"{self.functor}({', '.join(str(a) for a in self.args)})"


@dataclass(frozen=True)
class Negacion:
    """Objetivo ``\\+ meta``: se cumple si la meta no puede demostrarse."""

    meta: Compuesto


@dataclass(frozen=True)
class Diferente:
    """Objetivo ``A \\= B``: se cumple si A y B no unifican."""

    izquierda: object
    derecha: object


@dataclass(frozen=True)
class Regla:
    cabeza: Compuesto
    cuerpo: tuple = ()


Sustitucion = dict


def resolver_variable(termino, sustitucion: Sustitucion):
    """Sigue la cadena de enlaces de una variable hasta su valor actual."""
    while isinstance(termino, Var) and termino in sustitucion:
        termino = sustitucion[termino]
    return termino


def unificar(a, b, sustitucion: Sustitucion) -> Sustitucion | None:
    """Algoritmo de unificación; devuelve una sustitución nueva o ``None``."""
    a, b = resolver_variable(a, sustitucion), resolver_variable(b, sustitucion)
    if a == b:
        return sustitucion
    if isinstance(a, Var):
        return {**sustitucion, a: b}
    if isinstance(b, Var):
        return {**sustitucion, b: a}
    if isinstance(a, Compuesto) and isinstance(b, Compuesto):
        if a.functor != b.functor or len(a.args) != len(b.args):
            return None
        for x, y in zip(a.args, b.args):
            sustitucion = unificar(x, y, sustitucion)
            if sustitucion is None:
                return None
        return sustitucion
    return None


def aplicar(termino, sustitucion: Sustitucion):
    """Reemplaza las variables enlazadas de un término."""
    termino = resolver_variable(termino, sustitucion)
    if isinstance(termino, Compuesto):
        return Compuesto(termino.functor, tuple(aplicar(a, sustitucion) for a in termino.args))
    return termino


class BaseConocimiento:
    """Almacena hechos y reglas y responde consultas por encadenamiento hacia atrás."""

    PROFUNDIDAD_MAXIMA = 64

    def __init__(self, reglas: list[Regla] | None = None) -> None:
        self._clausulas: dict[tuple[str, int], list[Regla]] = {}
        self._contador = itertools.count()
        for regla in reglas or []:
            self.agregar(regla)

    def agregar(self, regla: Regla) -> None:
        clave = (regla.cabeza.functor, len(regla.cabeza.args))
        self._clausulas.setdefault(clave, []).append(regla)

    def agregar_hecho(self, functor: str, *args) -> None:
        self.agregar(Regla(Compuesto(functor, tuple(args))))

    def _renombrar(self, termino, sufijo: int):
        if isinstance(termino, Var):
            return Var(f"{termino.nombre}#{sufijo}")
        if isinstance(termino, Compuesto):
            return Compuesto(termino.functor, tuple(self._renombrar(a, sufijo) for a in termino.args))
        if isinstance(termino, Negacion):
            return Negacion(self._renombrar(termino.meta, sufijo))
        if isinstance(termino, Diferente):
            return Diferente(self._renombrar(termino.izquierda, sufijo), self._renombrar(termino.derecha, sufijo))
        return termino

    def _demostrar(self, metas: tuple, sustitucion: Sustitucion, profundidad: int) -> Iterator[Sustitucion]:
        if not metas:
            yield sustitucion
            return
        if profundidad > self.PROFUNDIDAD_MAXIMA:
            return
        meta, resto = metas[0], metas[1:]
        if isinstance(meta, Negacion):
            if next(self._demostrar((meta.meta,), sustitucion, profundidad + 1), None) is None:
                yield from self._demostrar(resto, sustitucion, profundidad + 1)
            return
        if isinstance(meta, Diferente):
            if unificar(meta.izquierda, meta.derecha, sustitucion) is None:
                yield from self._demostrar(resto, sustitucion, profundidad + 1)
            return
        for regla in self._clausulas.get((meta.functor, len(meta.args)), ()):
            sufijo = next(self._contador)
            cabeza = self._renombrar(regla.cabeza, sufijo)
            nueva = unificar(meta, cabeza, sustitucion)
            if nueva is None:
                continue
            cuerpo = tuple(self._renombrar(g, sufijo) for g in regla.cuerpo)
            yield from self._demostrar(cuerpo + resto, nueva, profundidad + 1)

    def consultar(self, consulta: str | Compuesto) -> list[dict]:
        """Devuelve todas las soluciones como ``{variable: valor}`` sin repetir."""
        meta = parsear_termino(consulta) if isinstance(consulta, str) else consulta
        variables = sorted(_variables(meta), key=lambda v: v.nombre)
        soluciones: list[dict] = []
        for sustitucion in self._demostrar((meta,), {}, 0):
            fila = {v.nombre: aplicar(v, sustitucion) for v in variables}
            if fila not in soluciones:
                soluciones.append(fila)
        return soluciones

    def cumple(self, consulta: str | Compuesto) -> bool:
        meta = parsear_termino(consulta) if isinstance(consulta, str) else consulta
        return next(self._demostrar((meta,), {}, 0), None) is not None


def _variables(termino) -> set[Var]:
    if isinstance(termino, Var):
        return {termino}
    if isinstance(termino, Compuesto):
        return set().union(*(_variables(a) for a in termino.args)) if termino.args else set()
    return set()


# ---------------------------------------------------------------------------
# Lector del subconjunto de Prolog usado en reglas_fraude.pl
# ---------------------------------------------------------------------------
_TOKEN = re.compile(r"\s*(:-|\\\+|\\=|[(),.]|[A-Za-z_][A-Za-z0-9_]*|-?\d+(?:\.\d+)?)")


def _tokenizar(texto: str) -> list[str]:
    tokens, posicion = [], 0
    texto = texto.rstrip()
    while posicion < len(texto):
        coincidencia = _TOKEN.match(texto, posicion)
        if not coincidencia:
            raise ValueError(f"Símbolo no válido cerca de: {texto[posicion:posicion + 20]!r}")
        tokens.append(coincidencia.group(1))
        posicion = coincidencia.end()
    return tokens


class _Lector:
    def __init__(self, tokens: list[str]) -> None:
        self.tokens, self.i = tokens, 0

    def ver(self) -> str | None:
        return self.tokens[self.i] if self.i < len(self.tokens) else None

    def tomar(self, esperado: str | None = None) -> str:
        token = self.ver()
        if token is None or (esperado and token != esperado):
            raise ValueError(f"Se esperaba {esperado!r} y se encontró {token!r}")
        self.i += 1
        return token

    def termino(self):
        token = self.tomar()
        if re.fullmatch(r"-?\d+", token):
            return int(token)
        if re.fullmatch(r"-?\d+\.\d+", token):
            return float(token)
        if token[0].isupper() or token[0] == "_":
            return Var(token if token != "_" else f"_anon{self.i}")
        if self.ver() == "(":
            self.tomar("(")
            argumentos = [self.termino()]
            while self.ver() == ",":
                self.tomar(",")
                argumentos.append(self.termino())
            self.tomar(")")
            return Compuesto(token, tuple(argumentos))
        return token

    def objetivo(self):
        if self.ver() == "\\+":
            self.tomar()
            return Negacion(_como_compuesto(self.termino()))
        izquierda = self.termino()
        if self.ver() == "\\=":
            self.tomar()
            return Diferente(izquierda, self.termino())
        return _como_compuesto(izquierda)

    def clausula(self) -> Regla:
        cabeza = _como_compuesto(self.termino())
        cuerpo = []
        if self.ver() == ":-":
            self.tomar()
            cuerpo.append(self.objetivo())
            while self.ver() == ",":
                self.tomar(",")
                cuerpo.append(self.objetivo())
        self.tomar(".")
        return Regla(cabeza, tuple(cuerpo))


def _como_compuesto(termino) -> Compuesto:
    return termino if isinstance(termino, Compuesto) else Compuesto(str(termino))


def parsear_termino(texto: str) -> Compuesto:
    return _como_compuesto(_Lector(_tokenizar(texto)).termino())


def parsear_programa(texto: str) -> list[Regla]:
    sin_comentarios = "\n".join(linea.split("%", 1)[0] for linea in texto.splitlines())
    lector = _Lector(_tokenizar(sin_comentarios))
    reglas = []
    while lector.ver() is not None:
        reglas.append(lector.clausula())
    return reglas


def cargar_reglas(ruta: Path | None = None) -> list[Regla]:
    ruta = ruta or Path(__file__).with_name("reglas_fraude.pl")
    return parsear_programa(ruta.read_text(encoding="utf-8"))
