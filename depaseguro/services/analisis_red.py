"""Análisis de zonas (datos oficiales) y de redes de cuentas relacionadas."""
from __future__ import annotations

from collections import defaultdict
from itertools import combinations

import pandas as pd

from ..config import Config
from .analitica import hamming, tendencia_y_proyeccion

MODALIDADES_PATRIMONIO = ("Estafa", "Robo", "Hurto", "Extorsión")


class ConjuntosDisjuntos:
    """Estructura Union-Find: agrupa avisos conectados por teléfono, foto o documento."""

    def __init__(self) -> None:
        self.padre: dict = {}

    def buscar(self, elemento):
        self.padre.setdefault(elemento, elemento)
        while self.padre[elemento] != elemento:
            self.padre[elemento] = self.padre[self.padre[elemento]]
            elemento = self.padre[elemento]
        return elemento

    def unir(self, a, b) -> None:
        self.padre[self.buscar(a)] = self.buscar(b)


def detectar_redes(conexion) -> list[dict]:
    """Encuentra grupos de avisos de distintas cuentas unidos por un mismo dato."""
    avisos = {f["id"]: dict(f) for f in conexion.execute(
        """SELECT i.id, i.titulo, i.telefono_contacto, i.arrendador_id, i.trust_score, u.nombre AS arrendador
           FROM inmuebles i JOIN usuarios u ON u.id = i.arrendador_id WHERE i.estado != 'retirado'""")}
    grupos = ConjuntosDisjuntos()
    motivos: dict = defaultdict(set)

    por_telefono = defaultdict(list)
    for aviso in avisos.values():
        por_telefono[aviso["telefono_contacto"]].append(aviso["id"])
    for telefono, ids in por_telefono.items():
        if len({avisos[i]["arrendador_id"] for i in ids}) > 1:
            for a, b in zip(ids, ids[1:]):
                grupos.unir(a, b)
            motivos[grupos.buscar(ids[0])].add("mismo teléfono")

    imagenes = [dict(f) for f in conexion.execute("SELECT inmueble_id, sha256, dhash FROM imagenes")]
    for a, b in combinations(imagenes, 2):
        ia, ib = a["inmueble_id"], b["inmueble_id"]
        if ia == ib or ia not in avisos or ib not in avisos:
            continue
        if avisos[ia]["arrendador_id"] == avisos[ib]["arrendador_id"]:
            continue
        if a["sha256"] == b["sha256"] or hamming(a["dhash"], b["dhash"]) <= Config.HAMMING_IMAGEN_DUPLICADA:
            grupos.unir(ia, ib)
            motivos[grupos.buscar(ia)].add("misma fotografía")

    documentos = defaultdict(list)
    for fila in conexion.execute("SELECT inmueble_id, sha256 FROM documentos"):
        documentos[fila["sha256"]].append(fila["inmueble_id"])
    for ids in documentos.values():
        vinculados = [i for i in ids if i in avisos]
        if len({avisos[i]["arrendador_id"] for i in vinculados}) > 1:
            for a, b in zip(vinculados, vinculados[1:]):
                grupos.unir(a, b)
            motivos[grupos.buscar(vinculados[0])].add("mismo documento")

    componentes = defaultdict(list)
    for identificador in list(grupos.padre):
        componentes[grupos.buscar(identificador)].append(identificador)

    motivos_por_raiz: dict = defaultdict(set)
    for raiz, textos in motivos.items():
        motivos_por_raiz[grupos.buscar(raiz)] |= textos

    redes = []
    for raiz, ids in componentes.items():
        cuentas = {avisos[i]["arrendador"] for i in ids}
        if len(ids) >= 2 and len(cuentas) >= 2:
            redes.append({
                "avisos": [avisos[i] for i in sorted(ids)],
                "cuentas": sorted(cuentas),
                "motivos": sorted(motivos_por_raiz[raiz]),
            })
    return sorted(redes, key=lambda red: len(red["avisos"]), reverse=True)


def _tabla_denuncias(conexion) -> pd.DataFrame:
    return pd.read_sql_query("SELECT * FROM denuncias_distrito", conexion)


def ultimo_periodo(conexion) -> tuple[int, int] | None:
    fila = conexion.execute("SELECT MAX(anio * 100 + mes) FROM denuncias_distrito").fetchone()
    return divmod(fila[0], 100) if fila and fila[0] else None


def ranking_zonas(conexion, meses: int = 12) -> list[dict]:
    """Resume los últimos meses por distrito, con tasa por 10 000 habitantes."""
    tabla = _tabla_denuncias(conexion)
    if tabla.empty:
        return []
    tabla["periodo"] = tabla["anio"] * 12 + tabla["mes"]
    reciente = tabla[tabla["periodo"] > tabla["periodo"].max() - meses]
    resumen = reciente[reciente["modalidad"].isin(MODALIDADES_PATRIMONIO)].pivot_table(
        index=["ubigeo", "distrito"], columns="modalidad", values="cantidad", aggfunc="sum", fill_value=0
    ).reset_index()
    for modalidad in MODALIDADES_PATRIMONIO:
        if modalidad not in resumen:
            resumen[modalidad] = 0
    poblacion = pd.read_sql_query("SELECT ubigeo, poblacion FROM distritos", conexion)
    resumen = resumen.merge(poblacion, on="ubigeo", how="left")
    resumen["patrimonio"] = resumen[list(MODALIDADES_PATRIMONIO)].sum(axis=1)
    resumen["tasa_estafa"] = (resumen["Estafa"] / resumen["poblacion"] * 10000).round(1)
    resumen["tasa_patrimonio"] = (resumen["patrimonio"] / resumen["poblacion"] * 10000).round(1)
    resumen = resumen.sort_values("Estafa", ascending=False)
    filas = resumen.astype(object).where(resumen.notna(), None).to_dict("records")
    return [{**fila, "distrito": fila["distrito"].title()} for fila in filas]


def serie_estafas(conexion, ubigeo: str | None = None) -> dict:
    """Serie mensual de estafas y proyección de los siguientes tres meses."""
    condicion, parametros = "modalidad = 'Estafa'", ()
    if ubigeo:
        condicion += " AND ubigeo = ?"
        parametros = (ubigeo,)
    filas = conexion.execute(
        f"""SELECT anio, mes, SUM(cantidad) AS total FROM denuncias_distrito
            WHERE {condicion} GROUP BY anio, mes ORDER BY anio, mes""",
        parametros,
    ).fetchall()
    ultimas = filas[-36:]
    etiquetas = [f"{f['anio']}-{f['mes']:02d}" for f in ultimas]
    valores = [f["total"] for f in ultimas]
    return {"etiquetas": etiquetas, "valores": valores, **tendencia_y_proyeccion(valores[-12:])}


def resumen_anual_estafas(conexion) -> list[dict]:
    filas = conexion.execute(
        """SELECT anio, SUM(cantidad) AS total, COUNT(DISTINCT mes) AS meses FROM denuncias_distrito
           WHERE modalidad = 'Estafa' GROUP BY anio ORDER BY anio"""
    )
    return [dict(f) for f in filas]


def contexto_distrito(conexion, ubigeo: str) -> dict | None:
    for fila in ranking_zonas(conexion):
        if fila["ubigeo"] == ubigeo:
            return fila
    return None


def resumen_ciberdelitos(conexion) -> list[dict]:
    filas = conexion.execute(
        """SELECT anio, SUM(CASE WHEN delito LIKE 'Fraude%' THEN cantidad ELSE 0 END) AS fraude,
                  SUM(CASE WHEN delito LIKE 'Suplantaci%' THEN cantidad ELSE 0 END) AS suplantacion,
                  SUM(cantidad) AS total
           FROM ciberdelitos GROUP BY anio ORDER BY anio"""
    )
    return [dict(f) for f in filas]
