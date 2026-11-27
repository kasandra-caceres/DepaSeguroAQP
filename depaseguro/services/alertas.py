"""Generación de alertas automáticas a partir de evaluaciones y datos oficiales."""
from __future__ import annotations

from ..dao.repositorios import AlertaDAO, BusquedaGuardadaDAO, FavoritoDAO
from ..models.entidades import ResultadoEvaluacion, Severidad
from .analitica import distancia_km
from .eventos import suscribir


@suscribir("inmueble_evaluado")
def alertar_riesgo(conexion, resultado: ResultadoEvaluacion, anterior: dict, inmueble: dict) -> None:
    """Crea una alerta para moderación cuando aparece una señal alta o crítica."""
    alertas = AlertaDAO(conexion)
    for hallazgo in resultado.hallazgos:
        if hallazgo.severidad in (Severidad.ALTA, Severidad.CRITICA):
            alertas.registrar(
                hallazgo.hecho, hallazgo.severidad.value,
                f"{inmueble['titulo']}: {hallazgo.titulo}. {hallazgo.detalle}",
                inmueble_id=resultado.inmueble_id,
                clave=f"riesgo:{resultado.inmueble_id}:{hallazgo.hecho}",
            )


@suscribir("inmueble_evaluado")
def alertar_seguidores(conexion, resultado: ResultadoEvaluacion, anterior: dict, inmueble: dict) -> None:
    """Avisa a quienes guardaron el inmueble si su puntaje cae de forma importante."""
    previo = anterior.get("trust_score")
    if previo is None or previo - resultado.trust_score < 15:
        return
    alertas = AlertaDAO(conexion)
    for usuario_id in FavoritoDAO(conexion).seguidores(resultado.inmueble_id):
        alertas.registrar(
            "favorito_en_riesgo", "alta",
            f"El aviso «{inmueble['titulo']}» bajó de {previo} a {resultado.trust_score} puntos.",
            inmueble_id=resultado.inmueble_id, usuario_id=usuario_id,
            clave=f"favorito:{usuario_id}:{resultado.inmueble_id}:{resultado.trust_score}",
        )


@suscribir("inmueble_evaluado")
def alertar_busquedas(conexion, resultado: ResultadoEvaluacion, anterior: dict, inmueble: dict) -> None:
    """Avisa a estudiantes con una búsqueda guardada que coincide con el aviso."""
    if inmueble["estado"] != "publicado" or inmueble.get("lat") is None:
        return
    alertas = AlertaDAO(conexion)
    for busqueda in BusquedaGuardadaDAO(conexion).todas():
        if busqueda["lat"] is None or resultado.trust_score < busqueda["trust_min"]:
            continue
        if inmueble["precio_mensual_pen"] > busqueda["precio_max"]:
            continue
        distancia = distancia_km(inmueble["lat"], inmueble["lon"], busqueda["lat"], busqueda["lon"])
        if distancia <= busqueda["radio_km"]:
            alertas.registrar(
                "busqueda_coincide", "info",
                f"Nueva opción a {distancia} km de {busqueda['universidad']}: {inmueble['titulo']} "
                f"(S/ {inmueble['precio_mensual_pen']:.0f}, {resultado.trust_score} puntos).",
                inmueble_id=resultado.inmueble_id, usuario_id=busqueda["usuario_id"],
                clave=f"busqueda:{busqueda['id']}:{resultado.inmueble_id}",
            )


def alertas_zona(conexion) -> int:
    """Compara estafas denunciadas en los últimos 3 meses contra el mismo periodo del año anterior."""
    ultimo = conexion.execute("SELECT MAX(anio * 100 + mes) FROM denuncias_distrito").fetchone()[0]
    if not ultimo:
        return 0
    anio, mes = divmod(ultimo, 100)
    meses = [((anio * 12 + mes - 1 - k) // 12, (anio * 12 + mes - 1 - k) % 12 + 1) for k in range(3)]
    claves_actual = [a * 100 + m for a, m in meses]
    claves_previo = [(a - 1) * 100 + m for a, m in meses]

    def suma(claves: list[int]) -> dict:
        marcas = ",".join("?" for _ in claves)
        filas = conexion.execute(
            f"""SELECT ubigeo, distrito, SUM(cantidad) AS total FROM denuncias_distrito
                WHERE modalidad = 'Estafa' AND (anio * 100 + mes) IN ({marcas})
                GROUP BY ubigeo""",
            claves,
        )
        return {f["ubigeo"]: dict(f) for f in filas}

    actual, previo = suma(claves_actual), suma(claves_previo)
    creadas = 0
    alertas = AlertaDAO(conexion)
    for ubigeo, fila in actual.items():
        base = previo.get(ubigeo, {}).get("total", 0)
        if base >= 10 and fila["total"] >= base * 1.2:
            variacion = round((fila["total"] / base - 1) * 100)
            creadas += alertas.registrar(
                "zona_estafas", "media",
                f"Las denuncias por estafa en {fila['distrito'].title()} subieron {variacion}% "
                f"({base} a {fila['total']}) en el trimestre a {mes:02d}/{anio} frente al año anterior (MININTER).",
                clave=f"zona:{ubigeo}:{ultimo}",
            )
    return creadas
