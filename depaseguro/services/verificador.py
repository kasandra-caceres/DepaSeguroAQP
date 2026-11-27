"""Verificador rápido: evalúa un aviso visto fuera de la plataforma (Facebook, WhatsApp, etc.)."""
from __future__ import annotations

import json
from dataclasses import dataclass

from ..config import Config
from ..dao.repositorios import ImagenDAO, InmuebleDAO, ListaContactosDAO, VerificacionRapidaDAO
from ..logic.motor import BaseConocimiento
from ..models.entidades import NivelRiesgo
from .analitica import (analizar_imagen, analizar_texto, hamming, normalizar_telefono, telefono_valido,
                        z_robusto)
from .evaluador import TEXTO_PATRON, TEXTO_RECOMENDACION, _reglas


@dataclass(frozen=True)
class AvisoExterno:
    texto: str
    precio_mensual: float | None = None
    area_m2: float | None = None
    tipo: str = "cuarto"
    ubigeo: str | None = None
    telefono: str = ""
    pide_pago_previo: bool = False
    tiene_contrato: bool = True
    permite_visita: bool = True
    imagen: bytes | None = None


PENALIDAD = {
    "telefono_lista_negra": 60, "imagen_clonada": 35, "pago_previo": 30, "lenguaje_evasivo": 25,
    "precio_muy_bajo": 25, "precio_bajo": 10, "lenguaje_presion": 15, "sin_contrato": 15,
    "pide_pago_digital": 10, "telefono_invalido": 10, "sin_visita": 30,
}


def _revisar_precio(db, aviso: AvisoExterno) -> list[tuple]:
    if not aviso.precio_mensual:
        return []
    if aviso.area_m2:
        valor = aviso.precio_mensual / aviso.area_m2
        columna = "precio_m2_pen"
    else:
        valor = aviso.precio_mensual
        columna = "precio_mensual_pen"
    sql = f"SELECT {columna} FROM inmuebles WHERE tipo = ? AND {columna} IS NOT NULL AND estado != 'rechazado'"
    parametros: tuple = (aviso.tipo,)
    distrital = [f[0] for f in db.execute(sql + " AND ubigeo = ?", (*parametros, aviso.ubigeo))] if aviso.ubigeo else []
    muestra = distrital if len(distrital) >= Config.MUESTRA_MINIMA_PRECIOS else [f[0] for f in db.execute(sql, parametros)]
    if len(muestra) < Config.MUESTRA_MINIMA_PRECIOS:
        return []
    z, mediana = z_robusto(valor, muestra)
    if z <= Config.Z_PRECIO_MUY_BAJO:
        return [("precio_muy_bajo", "Precio muy por debajo de lo habitual",
                 f"La mediana comparable es S/ {mediana:.2f} y este aviso está en S/ {valor:.2f}.")]
    if z <= Config.Z_PRECIO_BAJO:
        return [("precio_bajo", "Precio bajo para la zona",
                 f"La mediana comparable es S/ {mediana:.2f} y este aviso está en S/ {valor:.2f}.")]
    return []


def _revisar_imagen(db, aviso: AvisoExterno) -> list[tuple]:
    if not aviso.imagen:
        return []
    datos = analizar_imagen(aviso.imagen)
    for otra in ImagenDAO(db).todas():
        if otra["sha256"] == datos["sha256"] or hamming(otra["dhash"], datos["dhash"]) <= Config.HAMMING_IMAGEN_DUPLICADA:
            return [("imagen_clonada", "La foto ya existe en otro aviso",
                     f"Coincide con «{otra['titulo']}». Pregunta por qué aparece con otro anunciante.")]
    return []


def verificar(db, aviso: AvisoExterno, usuario_id: int | None = None) -> dict:
    hallazgos: list[tuple] = []
    texto = analizar_texto(aviso.texto)
    if texto["presion"]:
        hallazgos.append(("lenguaje_presion", "Te apuran para decidir", ", ".join(texto["presion"])))
    if texto["evasion"]:
        hallazgos.append(("lenguaje_evasivo", "Evita la visita o el contrato", ", ".join(texto["evasion"])))
    if texto["pago"]:
        hallazgos.append(("pide_pago_digital", "Menciona pagos o depósitos", ", ".join(texto["pago"])))
    if aviso.pide_pago_previo:
        hallazgos.append(("pago_previo", "Pide dinero antes de la visita", "Es la señal más común de una estafa."))
    if not aviso.tiene_contrato:
        hallazgos.append(("sin_contrato", "No ofrece contrato", "Sin contrato es difícil reclamar."))
    if not aviso.permite_visita:
        hallazgos.append(("sin_visita", "No permite visitar el lugar", "No pagues por algo que no pudiste ver."))
    if aviso.telefono:
        telefono = normalizar_telefono(aviso.telefono)
        if not telefono_valido(telefono):
            hallazgos.append(("telefono_invalido", "Número con formato extraño", "No parece un celular peruano."))
        elif ListaContactosDAO(db).contiene(telefono):
            hallazgos.append(("telefono_lista_negra", "Número con caso confirmado",
                              "Está vinculado a un reporte confirmado en DepaSeguro."))
        else:
            coincidencias = InmuebleDAO(db).contar(
                "telefono_contacto = ? AND nivel_riesgo IN ('Riesgo alto','Crítico')", (telefono,))
            if coincidencias:
                hallazgos.append(("telefono_invalido", "Número usado en avisos de riesgo",
                                  f"Aparece en {coincidencias} aviso(s) con riesgo alto."))
    hallazgos += _revisar_precio(db, aviso)
    hallazgos += _revisar_imagen(db, aviso)

    base = BaseConocimiento(list(_reglas()))
    for hecho, _titulo, _detalle in hallazgos:
        base.agregar_hecho(hecho, "externo")
    if not aviso.tiene_contrato and aviso.pide_pago_previo:
        base.agregar_hecho("sin_documentos", "externo")
    patrones = [fila["P"] for fila in base.consultar("patron(externo, P)")]
    recomendaciones = [fila["R"] for fila in base.consultar("recomendacion(externo, R)")]

    puntaje = max(0, 100 - sum(PENALIDAD.get(h[0], 5) for h in hallazgos) - 10 * len(patrones))
    if base.cumple("critico(externo)"):
        puntaje = min(puntaje, 24)
    resultado = {
        "puntaje": puntaje,
        "nivel": NivelRiesgo.desde_puntaje(puntaje).value,
        "hallazgos": [{"titulo": t, "detalle": d} for _h, t, d in hallazgos],
        "patrones": [TEXTO_PATRON.get(p, p) for p in patrones],
        "recomendaciones": [TEXTO_RECOMENDACION.get(r, r) for r in recomendaciones]
        or ["No se encontraron señales fuertes, pero igual visita el lugar y pide contrato antes de pagar."],
    }
    VerificacionRapidaDAO(db).insertar({"usuario_id": usuario_id, "puntaje": puntaje, "nivel": resultado["nivel"],
                                        "resultado": json.dumps(resultado, ensure_ascii=False)})
    return resultado
