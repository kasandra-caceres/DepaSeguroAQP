"""Evaluación de avisos: reúne datos, ejecuta detectores, aplica reglas y calcula el Trust Score.

``EvaluadorInmueble`` es una fachada (patrón Facade): quien la usa pide evaluar
un aviso sin conocer detectores, reglas ni estadística.
"""
from __future__ import annotations

import json
from dataclasses import asdict
from functools import lru_cache, reduce

from ..config import Config
from ..dao.repositorios import (DocumentoDAO, EvaluacionDAO, ImagenDAO, IndicadorDAO, InmuebleDAO,
                                ListaContactosDAO, ReporteDAO, ResenaDAO)
from ..functional.pipeline import limitar
from ..logic.motor import BaseConocimiento, cargar_reglas
from ..models.entidades import (ComponenteScore, ContextoEvaluacion, Hallazgo, NivelRiesgo,
                                ResultadoEvaluacion, Severidad)
from .analitica import hamming, normalizar_precio, normalizar_telefono, z_robusto
from .detectores import DETECTORES
from .eventos import publicar

TEXTO_PATRON = {
    "adelanto_fantasma": "Adelanto por un inmueble que podría no existir",
    "ganga_irreal": "Oferta demasiado buena para ser real",
    "inmueble_clonado": "Aviso armado con fotos ajenas",
    "contacto_reincidente": "Contacto vinculado a casos anteriores",
    "ubicacion_dudosa": "Ubicación sin respaldo",
    "condiciones_abusivas": "Condiciones abusivas sin contrato",
    "documento_falso": "Documentación no aceptada",
}
TEXTO_RECOMENDACION = {
    "no_transferir": "No transfieras dinero por este aviso.",
    "visitar_antes": "Visita el lugar y conoce al arrendador antes de pagar.",
    "exigir_contrato": "Exige un contrato escrito antes de entregar dinero.",
    "buscar_alternativas": "Busca otra opción: este aviso reúne señales graves.",
    "continuar_con_visita": "Tiene buenas señales; confirma todo en una visita presencial.",
}


@lru_cache(maxsize=1)
def _reglas() -> tuple:
    return tuple(cargar_reglas())


def tipo_cambio_vigente(conexion) -> float:
    """Último tipo de cambio leído de BCRP, o el valor de respaldo si nunca se leyó."""
    ultimo = IndicadorDAO(conexion).ultimo("tipo_cambio_venta")
    return ultimo["valor"] if ultimo else Config.TIPO_CAMBIO_RESPALDO


def inferir(inmueble_id: int, hallazgos: list[Hallazgo], contexto: ContextoEvaluacion) -> dict:
    """Convierte hallazgos en hechos y consulta la base de conocimiento."""
    base = BaseConocimiento(list(_reglas()))
    atomo = f"i{inmueble_id}"
    for hallazgo in hallazgos:
        base.agregar_hecho(hallazgo.hecho, atomo)
    if any(d["estado"] == "aprobado" for d in contexto.documentos):
        base.agregar_hecho("documentos_aprobados", atomo)
    if contexto.inmueble.get("arrendador_verificado"):
        base.agregar_hecho("arrendador_verificado", atomo)
    patrones = [fila["P"] for fila in base.consultar(f"patron({atomo}, P)")]
    recomendaciones = [fila["R"] for fila in base.consultar(f"recomendacion({atomo}, R)")]
    return {"patrones": patrones, "recomendaciones": recomendaciones,
            "critico": base.cumple(f"critico({atomo})"), "confiable": base.cumple(f"confiable({atomo})")}


def puntuar_documentos(ctx: ContextoEvaluacion) -> ComponenteScore:
    aprobados = {d["tipo"] for d in ctx.documentos if d["estado"] == "aprobado"}
    pendientes = {d["tipo"] for d in ctx.documentos if d["estado"] == "pendiente"}
    puntos = 15 * ("titularidad" in aprobados) + 10 * ("recibo_servicio" in aprobados)
    puntos += 4 * ("titularidad" in pendientes) + 2 * ("recibo_servicio" in pendientes)
    return ComponenteScore("Documentos", puntos, 25, f"{len(aprobados)} tipo(s) aprobado(s) por moderación")


def puntuar_identidad(ctx: ContextoEvaluacion) -> ComponenteScore:
    verificado = bool(ctx.inmueble.get("arrendador_verificado"))
    return ComponenteScore("Identidad", 15 if verificado else 4, 15,
                           "Arrendador verificado" if verificado else "Identidad aún no verificada")


def puntuar_precio(ctx: ContextoEvaluacion) -> ComponenteScore:
    if ctx.z_precio is None or ctx.muestra_precio < Config.MUESTRA_MINIMA_PRECIOS:
        return ComponenteScore("Precio", 10, 15, "Pocos avisos comparables; puntaje neutral")
    puntos = limitar(0, 15)(15 + (ctx.z_precio + 1) * 6) if ctx.z_precio < -1 else 15
    return ComponenteScore("Precio", round(puntos, 1), 15, f"Desvío robusto z = {ctx.z_precio}")


def puntuar_imagenes(ctx: ContextoEvaluacion) -> ComponenteScore:
    if not ctx.imagenes:
        return ComponenteScore("Fotos", 3, 15, "Sin fotografías")
    if ctx.duplicados_imagen:
        return ComponenteScore("Fotos", 0, 15, "Fotos repetidas en avisos de otra persona")
    return ComponenteScore("Fotos", 15, 15, "Fotos sin coincidencias en la plataforma")


def puntuar_contacto(ctx: ContextoEvaluacion) -> ComponenteScore:
    if ctx.telefono_en_lista:
        return ComponenteScore("Contacto", 0, 10, "Número con caso confirmado")
    if ctx.otros_arrendadores_telefono:
        return ComponenteScore("Contacto", 3, 10, "Número compartido entre cuentas")
    return ComponenteScore("Contacto", 10, 10, "Sin coincidencias")


def puntuar_condiciones(ctx: ContextoEvaluacion) -> ComponenteScore:
    aviso = ctx.inmueble
    puntos = 10 - 5 * bool(aviso["pago_previo_visita"]) - 3 * (not aviso["contrato_escrito"])
    if aviso["adelanto_meses"] + aviso["garantia_meses"] > Config.ADELANTO_MAXIMO_MESES + 1:
        puntos -= 2
    return ComponenteScore("Condiciones", max(0, puntos), 10, "Contrato, adelanto y forma de pago")


def puntuar_comunidad(ctx: ContextoEvaluacion) -> ComponenteScore:
    """Promedio bayesiano: pocas reseñas no pesan tanto como muchas."""
    verificadas = [r["puntaje"] for r in ctx.resenas if r["verificada"]]
    previo, peso = 3.5, 3
    promedio = (previo * peso + sum(verificadas)) / (peso + len(verificadas))
    return ComponenteScore("Comunidad", round((promedio - 1) / 4 * 10, 1), 10,
                           f"{len(verificadas)} reseña(s) verificada(s)")


PUNTUADORES = (puntuar_documentos, puntuar_identidad, puntuar_precio, puntuar_imagenes,
               puntuar_contacto, puntuar_condiciones, puntuar_comunidad)


def calcular_score(ctx: ContextoEvaluacion, critico: bool) -> tuple[int, tuple[ComponenteScore, ...]]:
    componentes = tuple(funcion(ctx) for funcion in PUNTUADORES)
    base = reduce(lambda total, componente: total + componente.obtenido, componentes, 0)
    penalidad = 40 * min(ctx.reportes_confirmados, 1) + min(15, 5 * ctx.reportes_abiertos)
    puntaje = limitar(0, 100)(base - penalidad)
    if critico:
        puntaje = min(puntaje, 24)
    return round(puntaje), componentes


class EvaluadorInmueble:
    def __init__(self, conexion) -> None:
        self.db = conexion
        self.inmuebles = InmuebleDAO(conexion)

    def _normalizar(self, aviso: dict) -> dict:
        precio = normalizar_precio(aviso["precio"], aviso["moneda"], aviso["periodo"], aviso["area_m2"],
                                   tipo_cambio_vigente(self.db))
        self.inmuebles.actualizar(aviso["id"], {"precio_mensual_pen": precio.mensual_pen,
                                                "precio_m2_pen": precio.por_m2_pen})
        return {**aviso, "precio_mensual_pen": precio.mensual_pen, "precio_m2_pen": precio.por_m2_pen}

    def _muestra_precios(self, aviso: dict) -> list[float]:
        """Primero compara dentro del distrito; si hay pocos avisos usa toda la ciudad."""
        distrital = self.inmuebles.precios_comparables(aviso["id"], aviso["tipo"], aviso["ubigeo"])
        if len(distrital) >= Config.MUESTRA_MINIMA_PRECIOS:
            return distrital
        return self.inmuebles.precios_comparables(aviso["id"], aviso["tipo"])

    def _duplicados(self, aviso: dict, imagenes: list[dict]) -> list[dict]:
        """Busca copias de fotos subidas antes: quien publicó primero no se penaliza por ser copiado."""
        otras = ImagenDAO(self.db).de_otros_arrendadores(aviso["id"], aviso["arrendador_id"])
        return [
            otra for otra in otras for propia in imagenes
            if otra["id"] < propia["id"] and (
                otra["sha256"] == propia["sha256"]
                or hamming(otra["dhash"], propia["dhash"]) <= Config.HAMMING_IMAGEN_DUPLICADA)
        ]

    def construir_contexto(self, inmueble_id: int) -> ContextoEvaluacion:
        aviso = self.inmuebles.detalle(inmueble_id)
        if aviso is None:
            raise LookupError(f"No existe el inmueble {inmueble_id}")
        aviso = self._normalizar(aviso)
        imagenes = ImagenDAO(self.db).de_inmueble(inmueble_id)
        telefono = normalizar_telefono(aviso["telefono_contacto"])
        otros = self.db.execute(
            """SELECT COUNT(DISTINCT arrendador_id) FROM inmuebles
               WHERE telefono_contacto = ? AND arrendador_id != ?""",
            (telefono, aviso["arrendador_id"]),
        ).fetchone()[0]
        reportes = ReporteDAO(self.db).de_inmueble(inmueble_id)
        muestra = self._muestra_precios(aviso)
        z, mediana = z_robusto(aviso["precio_m2_pen"], muestra)
        return ContextoEvaluacion(
            inmueble=aviso,
            imagenes=imagenes,
            documentos=DocumentoDAO(self.db).de_inmueble(inmueble_id),
            duplicados_imagen=self._duplicados(aviso, imagenes),
            telefono_en_lista=ListaContactosDAO(self.db).contiene(telefono),
            otros_arrendadores_telefono=otros,
            reportes_abiertos=sum(r["estado"] in ("abierto", "en_revision") for r in reportes),
            reportes_confirmados=sum(r["estado"] == "confirmado" for r in reportes),
            resenas=ResenaDAO(self.db).de_inmueble(inmueble_id),
            z_precio=z,
            mediana_referencia=mediana,
            muestra_precio=len(muestra),
        )

    def evaluar(self, inmueble_id: int, notificar: bool = True) -> ResultadoEvaluacion:
        anterior = self.inmuebles.obtener(inmueble_id)
        contexto = self.construir_contexto(inmueble_id)
        hallazgos = [h for detector in DETECTORES for h in detector.evaluar(contexto)]
        deduccion = inferir(inmueble_id, hallazgos, contexto)
        puntaje, componentes = calcular_score(contexto, deduccion["critico"])
        resultado = ResultadoEvaluacion(
            inmueble_id=inmueble_id,
            trust_score=puntaje,
            nivel=NivelRiesgo.desde_puntaje(puntaje),
            componentes=componentes,
            hallazgos=tuple(sorted(hallazgos, key=lambda h: list(Severidad).index(h.severidad), reverse=True)),
            patrones=tuple(deduccion["patrones"]),
            recomendaciones=tuple(deduccion["recomendaciones"]),
            es_critico=deduccion["critico"],
        )
        self._guardar(resultado, anterior, contexto)
        if notificar:
            publicar("inmueble_evaluado", conexion=self.db, resultado=resultado,
                     anterior=anterior, inmueble=contexto.inmueble)
        return resultado

    def _guardar(self, resultado: ResultadoEvaluacion, anterior: dict, contexto: ContextoEvaluacion) -> None:
        estado = anterior["estado"]
        if resultado.es_critico and estado == "publicado":
            estado = "observado"
        self.inmuebles.actualizar(resultado.inmueble_id, {
            "trust_score": resultado.trust_score, "nivel_riesgo": resultado.nivel.value, "estado": estado})
        previa = EvaluacionDAO(self.db).ultima(resultado.inmueble_id)
        hallazgos = json.dumps([{**asdict(h), "severidad": h.severidad.value} for h in resultado.hallazgos],
                               ensure_ascii=False)
        componentes = json.dumps([asdict(c) for c in resultado.componentes], ensure_ascii=False)
        patrones = json.dumps({"patrones": resultado.patrones, "recomendaciones": resultado.recomendaciones},
                              ensure_ascii=False)
        if previa and previa["trust_score"] == resultado.trust_score and previa["hallazgos"] == hallazgos:
            return  # sin cambios: no se llena el historial
        EvaluacionDAO(self.db).insertar({
            "inmueble_id": resultado.inmueble_id, "trust_score": resultado.trust_score,
            "nivel": resultado.nivel.value, "componentes": componentes,
            "hallazgos": hallazgos, "patrones": patrones})


def reevaluar_todos(conexion, notificar: bool = False) -> int:
    """Recalcula todos los avisos activos; se usa tras leer nuevas fuentes o moderar."""
    evaluador = EvaluadorInmueble(conexion)
    filas = conexion.execute("SELECT id FROM inmuebles WHERE estado != 'retirado'").fetchall()
    for fila in filas:
        evaluador.evaluar(fila["id"], notificar=notificar)
    return len(filas)


def detalle_evaluacion(conexion, inmueble_id: int) -> dict | None:
    """Prepara la última evaluación guardada para mostrarla en pantalla."""
    fila = EvaluacionDAO(conexion).ultima(inmueble_id)
    if not fila:
        return None
    extra = json.loads(fila["patrones"])
    return {
        **fila,
        "componentes": json.loads(fila["componentes"]),
        "hallazgos": json.loads(fila["hallazgos"]),
        "patrones": [TEXTO_PATRON.get(p, p) for p in extra["patrones"]],
        "recomendaciones": [TEXTO_RECOMENDACION.get(r, r) for r in extra["recomendaciones"]],
    }
