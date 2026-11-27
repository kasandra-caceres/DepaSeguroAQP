"""Lectura automática de fuentes del Estado y de organizaciones sin fines de lucro.

``FuenteDatos`` aplica el patrón Template Method: ``ejecutar`` fija el proceso
(descargar, transformar, cargar y registrar) y cada subclase resuelve solo lo
propio de su fuente. Si una fuente falla, el sistema sigue usando lo último leído.
"""
from __future__ import annotations

import hashlib
import io
import re
import time
from abc import ABC, abstractmethod
from datetime import date, datetime, timedelta

import pandas as pd
import requests

from ..config import Config
from ..dao.repositorios import FuenteDAO, IndicadorDAO, IngestaDAO
from ..services.analitica import sin_acentos

PORTAL = "https://www.datosabiertos.gob.pe"
BCRP = "https://estadisticas.bcrp.gob.pe/estadisticas/series/api"
MESES = {"Ene": 1, "Feb": 2, "Mar": 3, "Abr": 4, "May": 5, "Jun": 6, "Jul": 7, "Ago": 8,
         "Set": 9, "Sep": 9, "Oct": 10, "Nov": 11, "Dic": 12}
PROVINCIA_DISTRITOS_UBIGEO = "0401"


def ahora() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def decodificar(contenido: bytes) -> str:
    """Los portales mezclan codificaciones: intenta UTF-8 y luego Windows-1252."""
    try:
        return contenido.decode("utf-8-sig")
    except UnicodeDecodeError:
        return contenido.decode("cp1252", errors="replace")


class FuenteDatos(ABC):
    clave = ""
    nombre = ""
    entidad = ""
    categoria = "estado"
    url = ""
    uso = ""

    def __init__(self, conexion, sesion: requests.Session | None = None) -> None:
        self.db = conexion
        self.http = sesion or requests.Session()
        self.http.headers.update({"User-Agent": Config.USER_AGENT})

    def descargar(self, url: str, **opciones) -> requests.Response:
        respuesta = self.http.get(url, timeout=Config.HTTP_TIMEOUT, **opciones)
        respuesta.raise_for_status()
        return respuesta

    def recursos_portal(self, dataset: str) -> list[dict]:
        """Consulta el catálogo del portal; así se encuentra el archivo más reciente aunque cambie de nombre."""
        respuesta = self.descargar(f"{PORTAL}/api/3/action/package_show", params={"id": dataset})
        resultado = respuesta.json()["result"]
        return resultado[0]["resources"]

    @abstractmethod
    def obtener(self) -> object:
        """Descarga los datos crudos."""

    @abstractmethod
    def cargar(self, crudo: object) -> int:
        """Transforma y guarda. Devuelve la cantidad de registros procesados."""

    def mensaje_exito(self, registros: int) -> str:
        return f"{registros} registro(s) actualizados."

    def huella(self, crudo: object) -> str:
        return hashlib.sha256(repr(crudo).encode("utf-8", "replace")).hexdigest()

    def ejecutar(self) -> dict:
        fuentes = FuenteDAO(self.db)
        inicio = ahora()
        ingesta = IngestaDAO(self.db).insertar(
            {"fuente": self.clave, "inicio": inicio, "estado": "en_proceso"})
        try:
            crudo = self.obtener()
            huella = self.huella(crudo)
            previa = fuentes.obtener(self.clave) or {}
            if previa.get("huella") == huella and previa.get("registros"):
                registros, estado, mensaje = previa["registros"], "sin_cambios", "La fuente no publicó datos nuevos."
            else:
                registros = self.cargar(crudo)
                self.db.commit()
                estado, mensaje = "ok", self.mensaje_exito(registros)
            fuentes.actualizar(self.clave, {"ultima_ejecucion": ahora(), "ultimo_exito": ahora(), "estado": estado,
                                            "registros": registros, "mensaje": mensaje, "huella": huella})
        except Exception as error:  # una fuente caída no debe detener a las demás
            self.db.rollback()
            registros, estado = 0, "error"
            mensaje = f"{type(error).__name__}: {str(error)[:200]}"
            fuentes.actualizar(self.clave, {"ultima_ejecucion": ahora(), "estado": estado, "mensaje": mensaje})
        IngestaDAO(self.db).actualizar(ingesta, {"fin": ahora(), "estado": estado,
                                                 "registros": registros, "mensaje": mensaje})
        return {"fuente": self.clave, "estado": estado, "registros": registros, "mensaje": mensaje}


class FuenteBCRP(FuenteDatos):
    """Tipo de cambio e índice de precios desde la API del Banco Central de Reserva."""

    clave = "bcrp"
    nombre = "BCRPData: tipo de cambio e IPC"
    entidad = "Banco Central de Reserva del Perú"
    url = "https://estadisticas.bcrp.gob.pe/estadisticas/series/"
    uso = "Convierte avisos en dólares a soles y actualiza precios antiguos."

    def obtener(self) -> dict:
        hoy = date.today()
        inicio_tc = (hoy - timedelta(days=45)).isoformat()
        tipo_cambio = self.descargar(f"{BCRP}/PD04640PD/json/{inicio_tc}/{hoy.isoformat()}").json()
        ipc = self.descargar(f"{BCRP}/PN38705PM/json/{hoy.year - 3}-1/{hoy.year}-12").json()
        return {"tc": tipo_cambio["periods"], "ipc": ipc["periods"]}

    @staticmethod
    def _periodo_diario(nombre: str) -> str:
        dia, mes, anio = nombre.split(".")
        return f"20{anio}-{MESES[mes]:02d}-{int(dia):02d}"

    @staticmethod
    def _periodo_mensual(nombre: str) -> str:
        mes, anio = nombre.split(".")
        return f"{anio}-{MESES[mes]:02d}"

    def cargar(self, crudo: dict) -> int:
        indicadores = IndicadorDAO(self.db)
        total = 0
        for fila in crudo["tc"]:
            valor = fila["values"][0]
            if valor not in ("n.d.", ""):
                indicadores.guardar("tipo_cambio_venta", self._periodo_diario(fila["name"]), float(valor), self.clave)
                total += 1
        for fila in crudo["ipc"]:
            valor = fila["values"][0]
            if valor not in ("n.d.", ""):
                indicadores.guardar("ipc_lima", self._periodo_mensual(fila["name"]), float(valor), self.clave)
                total += 1
        return total


class FuenteDenuncias(FuenteDatos):
    """Denuncias policiales por distrito (SIDPOL) publicadas por el MININTER."""

    clave = "mininter_denuncias"
    nombre = "Denuncias policiales registradas a nivel nacional"
    entidad = "Ministerio del Interior (MININTER)"
    url = f"{PORTAL}/dataset/denuncias-policiales-registradas-nivel-nacional-mininter"
    uso = "Calcula estafas y delitos patrimoniales por distrito y genera alertas de zona."
    dataset = "denuncias-policiales-registradas-nivel-nacional-mininter"

    def obtener(self) -> dict:
        recursos = [r for r in self.recursos_portal(self.dataset) if str(r.get("format", "")).lower() == "csv"]
        historicos = [r for r in recursos if re.search(r"Enero\s+2018\s+a", r.get("name", ""))]
        if not historicos:
            raise ValueError("No se encontró el archivo histórico en el catálogo.")
        recurso = historicos[-1]
        return {"url": recurso["url"], "nombre": recurso["name"]}

    def huella(self, crudo: dict) -> str:
        return hashlib.sha256(crudo["url"].encode()).hexdigest()

    def cargar(self, crudo: dict) -> int:
        contenido = self.descargar(crudo["url"]).content
        tabla = pd.read_csv(io.StringIO(decodificar(contenido)), dtype=str)
        return self.guardar(tabla)

    def guardar(self, tabla: pd.DataFrame) -> int:
        tabla["UBIGEO_HECHO"] = tabla["UBIGEO_HECHO"].str.zfill(6)
        arequipa = tabla[tabla["UBIGEO_HECHO"].str.startswith(PROVINCIA_DISTRITOS_UBIGEO)].copy()
        arequipa["cantidad"] = pd.to_numeric(arequipa["cantidad"], errors="coerce").fillna(0).astype(int)
        agrupado = arequipa.groupby(
            ["UBIGEO_HECHO", "DIST_HECHO", "ANIO", "MES", "P_MODALIDADES"], as_index=False)["cantidad"].sum()
        self.db.execute("DELETE FROM denuncias_distrito")
        self.db.executemany(
            """INSERT OR REPLACE INTO denuncias_distrito(ubigeo, distrito, anio, mes, modalidad, cantidad)
               VALUES (?,?,?,?,?,?)""",
            [(f.UBIGEO_HECHO, f.DIST_HECHO, int(f.ANIO), int(f.MES), f.P_MODALIDADES, int(f.cantidad))
             for f in agrupado.itertuples()],
        )
        return len(agrupado)


class FuenteCiberdelitos(FuenteDatos):
    """Delitos informáticos denunciados ante el Ministerio Público."""

    clave = "mpfn_ciberdelitos"
    nombre = "Delitos informáticos denunciados"
    entidad = "Ministerio Público - Fiscalía de la Nación (MPFN)"
    url = f"{PORTAL}/dataset/delitos-inform%C3%A1ticos-denunciados-ante-el-ministerio-p%C3%BAblico-mpfn"
    uso = "Muestra la evolución del fraude informático y la suplantación en Arequipa."
    dataset = "delitos-informáticos-denunciados-ante-el-ministerio-público-mpfn"

    def obtener(self) -> list[dict]:
        recursos = self.recursos_portal(self.dataset)
        archivos = [r for r in recursos if str(r.get("format", "")).lower() == "csv"]
        return [{"url": r["url"], "nombre": r["name"]} for r in archivos]

    def cargar(self, crudo: list[dict]) -> int:
        total = 0
        self.db.execute("DELETE FROM ciberdelitos")
        for recurso in crudo:
            contenido = self.descargar(recurso["url"]).content
            tabla = pd.read_csv(io.StringIO(decodificar(contenido)), dtype=str)
            total += self.guardar(tabla)
        return total

    def guardar(self, tabla: pd.DataFrame) -> int:
        tabla.columns = [c.strip().lower() for c in tabla.columns]
        # El archivo de 2020 trae todos los delitos: solo se conservan los de la Ley 30096.
        es_informatico = tabla["generico"].fillna("").str.contains("30096")
        fiscal = tabla[es_informatico & (tabla["distrito_fiscal"].str.strip().str.upper() == "AREQUIPA")].copy()
        fiscal["cantidad"] = pd.to_numeric(fiscal["cantidad"], errors="coerce").fillna(0).astype(int)
        agrupado = fiscal.groupby(["anio_denuncia", "des_articulo"], as_index=False)["cantidad"].sum()
        self.db.executemany(
            """INSERT INTO ciberdelitos(anio, distrito_fiscal, delito, cantidad) VALUES (?,?,?,?)
               ON CONFLICT(anio, distrito_fiscal, delito) DO UPDATE SET cantidad = cantidad + excluded.cantidad""",
            [(int(f.anio_denuncia), "AREQUIPA", f.des_articulo, int(f.cantidad)) for f in agrupado.itertuples()],
        )
        return len(agrupado)


class FuenteSunedu(FuenteDatos):
    """Locales universitarios licenciados, con coordenadas oficiales."""

    clave = "sunedu_campus"
    nombre = "SUNEDU - Programas académicos"
    entidad = "Superintendencia Nacional de Educación Superior Universitaria (SUNEDU)"
    url = f"{PORTAL}/dataset/sunedu-programas-acad%C3%A9micos"
    uso = "Da la ubicación y licencia de cada campus para buscar por cercanía."
    dataset = "sunedu-programas-académicos"

    def obtener(self) -> dict:
        recursos = [r for r in self.recursos_portal(self.dataset) if str(r.get("format", "")).lower() == "csv"]
        if not recursos:
            raise ValueError("El catálogo no incluye un CSV.")
        return {"url": recursos[0]["url"]}

    def huella(self, crudo: dict) -> str:
        return hashlib.sha256(crudo["url"].encode()).hexdigest()

    def cargar(self, crudo: dict) -> int:
        contenido = self.descargar(crudo["url"]).content
        tabla = pd.read_csv(io.StringIO(decodificar(contenido)), sep="|", dtype=str)
        return self.guardar(tabla)

    def guardar(self, tabla: pd.DataFrame) -> int:
        locales = tabla[(tabla["DEPARTAMENTO_LOCAL"] == "AREQUIPA") & (tabla["PROVINCIA_LOCAL"] == "AREQUIPA")]
        locales = locales.drop_duplicates(["NOMBRE", "CODIGO_LOCAL"])
        total = 0
        for fila in locales.itertuples():
            lat, lon = pd.to_numeric(fila.LATITUD_UBICACION, errors="coerce"), pd.to_numeric(
                fila.LONGITUD_UBICACION, errors="coerce")
            if pd.isna(lat) or pd.isna(lon):
                continue
            self.db.execute(
                """INSERT INTO campus(universidad, codigo_local, distrito, lat, lon, licencia, fecha_corte, actualizado_en)
                   VALUES (?,?,?,?,?,?,?,?)
                   ON CONFLICT(universidad, codigo_local) DO UPDATE SET distrito = excluded.distrito,
                     lat = excluded.lat, lon = excluded.lon, licencia = excluded.licencia,
                     fecha_corte = excluded.fecha_corte, actualizado_en = excluded.actualizado_en""",
                (fila.NOMBRE, fila.CODIGO_LOCAL, fila.DISTRITO_LOCAL, float(lat), float(lon),
                 fila.ESTADO_LICENCIAMIENTO, fila.FECHA_CORTE, ahora()),
            )
            total += 1
        return total


class FuenteWikidata(FuenteDatos):
    """Población por distrito desde Wikidata (Wikimedia Foundation, sin fines de lucro)."""

    clave = "wikidata_poblacion"
    nombre = "Wikidata: población distrital"
    entidad = "Wikimedia Foundation (ONG)"
    categoria = "ong"
    url = "https://query.wikidata.org/"
    uso = "Permite expresar las denuncias por cada 10 000 habitantes."
    consulta = """SELECT ?dLabel ?pop WHERE {
      ?d wdt:P131 wd:Q601118; wdt:P1082 ?pop.
      SERVICE wikibase:label { bd:serviceParam wikibase:language "es". }
    }"""

    def obtener(self) -> list[dict]:
        respuesta = self.descargar("https://query.wikidata.org/sparql", params={"query": self.consulta},
                                   headers={"Accept": "application/sparql-results+json"})
        return [{"distrito": fila["dLabel"]["value"], "poblacion": int(float(fila["pop"]["value"]))}
                for fila in respuesta.json()["results"]["bindings"]]

    def cargar(self, crudo: list[dict]) -> int:
        por_nombre = {}
        for fila in crudo:
            if fila["distrito"].startswith("Distrito de "):
                nombre = sin_acentos(fila["distrito"].removeprefix("Distrito de ")).upper()
                por_nombre[nombre] = fila["poblacion"]
        total = 0
        for distrito in self.db.execute("SELECT ubigeo, nombre FROM distritos").fetchall():
            poblacion = por_nombre.get(sin_acentos(distrito["nombre"]).upper())
            if poblacion:
                self.db.execute(
                    "UPDATE distritos SET poblacion = ?, poblacion_fuente = 'Wikidata' WHERE ubigeo = ?",
                    (poblacion, distrito["ubigeo"]))
                total += 1
        return total


class FuenteTransparencia(FuenteDatos):
    """Índice de Percepción de la Corrupción de Transparency International, vía Our World in Data."""

    clave = "ti_cpi"
    nombre = "Índice de Percepción de la Corrupción (Perú)"
    entidad = "Transparency International y Our World in Data (ONG)"
    categoria = "ong"
    url = "https://ourworldindata.org/grapher/ti-corruption-perception-index"
    uso = "Da contexto institucional al observatorio de zonas."

    def obtener(self) -> str:
        return self.descargar(f"{self.url}.csv", params={"country": "PER"}).text

    def cargar(self, crudo: str) -> int:
        tabla = pd.read_csv(io.StringIO(crudo))
        peru = tabla[tabla["Code"] == "PER"]
        indicadores = IndicadorDAO(self.db)
        columna = "Corruption Perceptions Index"
        for fila in peru.to_dict("records"):
            indicadores.guardar("cpi_peru", str(fila["Year"]), float(fila[columna]), self.clave)
        return len(peru)


class FuenteOpenStreetMap(FuenteDatos):
    """Verifica direcciones pendientes con Nominatim (OpenStreetMap Foundation, sin fines de lucro)."""

    clave = "osm_nominatim"
    nombre = "OpenStreetMap Nominatim"
    entidad = "OpenStreetMap Foundation (ONG)"
    categoria = "ong"
    url = "https://nominatim.openstreetmap.org/"
    uso = "Comprueba que la dirección exista y corresponda al distrito declarado."
    LOTE = 15

    def obtener(self) -> list[dict]:
        filas = self.db.execute(
            """SELECT i.id, i.direccion, i.lat, i.lon, d.nombre AS distrito, d.lat AS dlat, d.lon AS dlon
               FROM inmuebles i JOIN distritos d ON d.ubigeo = i.ubigeo
               WHERE i.direccion_estado = 'sin_verificar' AND i.estado != 'retirado' LIMIT ?""",
            (self.LOTE,),
        ).fetchall()
        return [dict(f) for f in filas]

    def huella(self, crudo: list[dict]) -> str:
        return f"{ahora()}-{len(crudo)}"  # siempre procesa el lote pendiente

    def mensaje_exito(self, registros: int) -> str:
        """Nominatim se consulta bajo demanda: solo procesa direcciones nuevas, por eso 0 no es una falla."""
        cache = self.db.execute("SELECT COUNT(*) FROM geocache WHERE lat IS NOT NULL").fetchone()[0]
        verificadas = self.db.execute("SELECT COUNT(*) FROM inmuebles WHERE direccion_estado = 'verificada'").fetchone()[0]
        nuevas = f"{registros} dirección(es) nuevas revisadas" if registros else "Sin direcciones nuevas por revisar"
        detalle = f"{verificadas} avisos con dirección verificada" + (f" y {cache} direcciones en caché" if cache else "")
        return f"Bajo demanda. {nuevas}; {detalle}."

    def geocodificar(self, consulta: str) -> dict | None:
        guardado = self.db.execute("SELECT * FROM geocache WHERE consulta = ?", (consulta,)).fetchone()
        if guardado:
            return dict(guardado) if guardado["lat"] is not None else None
        time.sleep(1.1)  # política de uso: máximo una consulta por segundo
        respuesta = self.descargar(f"{self.url}search", params={
            "q": consulta, "format": "jsonv2", "limit": 1, "countrycodes": "pe"})
        datos = respuesta.json()
        punto = ({"lat": float(datos[0]["lat"]), "lon": float(datos[0]["lon"]), "nombre": datos[0]["display_name"]}
                 if datos else None)
        self.db.execute("INSERT OR REPLACE INTO geocache(consulta, lat, lon, nombre) VALUES (?,?,?,?)",
                        (consulta, *(punto.values() if punto else (None, None, None))))
        return punto

    def cargar(self, crudo: list[dict]) -> int:
        from ..services.analitica import distancia_km

        for aviso in crudo:
            punto = self.geocodificar(f"{aviso['direccion']}, {aviso['distrito'].title()}, Arequipa, Perú")
            if punto is None:
                self.db.execute("UPDATE inmuebles SET direccion_estado = 'no_encontrada' WHERE id = ?", (aviso["id"],))
                continue
            lat, lon = aviso["lat"] or punto["lat"], aviso["lon"] or punto["lon"]
            lejos = aviso["dlat"] is not None and distancia_km(lat, lon, aviso["dlat"], aviso["dlon"]) > 8
            self.db.execute(
                "UPDATE inmuebles SET lat = ?, lon = ?, direccion_estado = ? WHERE id = ?",
                (lat, lon, "fuera_distrito" if lejos else "verificada", aviso["id"]))
        return len(crudo)


FUENTES = (FuenteBCRP, FuenteSunedu, FuenteDenuncias, FuenteCiberdelitos,
           FuenteWikidata, FuenteTransparencia, FuenteOpenStreetMap)


def registrar_catalogo(conexion) -> None:
    """Inserta o actualiza la descripción de cada fuente sin borrar su historial."""
    for clase in FUENTES:
        conexion.execute(
            """INSERT INTO fuentes_datos(clave, nombre, entidad, categoria, url, uso) VALUES (?,?,?,?,?,?)
               ON CONFLICT(clave) DO UPDATE SET nombre = excluded.nombre, entidad = excluded.entidad,
                 categoria = excluded.categoria, url = excluded.url, uso = excluded.uso""",
            (clase.clave, clase.nombre, clase.entidad, clase.categoria, clase.url, clase.uso),
        )
    conexion.commit()
