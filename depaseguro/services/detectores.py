"""Detectores de fraude (patrón Strategy): cada clase revisa un solo aspecto del aviso."""
from __future__ import annotations

from abc import ABC, abstractmethod

from ..config import Config
from ..models.entidades import ContextoEvaluacion, Hallazgo, Severidad
from .analitica import analizar_texto


class Detector(ABC):
    """Interfaz común. Agregar un detector nuevo no obliga a modificar los demás."""

    @abstractmethod
    def evaluar(self, ctx: ContextoEvaluacion) -> list[Hallazgo]:
        ...


class DetectorPrecio(Detector):
    def evaluar(self, ctx):
        z = ctx.z_precio
        if z is None or ctx.muestra_precio < Config.MUESTRA_MINIMA_PRECIOS:
            return []
        referencia = f"S/ {ctx.mediana_referencia:.2f} por m² en {ctx.muestra_precio} avisos comparables"
        if z <= Config.Z_PRECIO_MUY_BAJO:
            return [Hallazgo("precio_muy_bajo", Severidad.ALTA, "Precio anormalmente bajo",
                             f"Está muy por debajo de la mediana ({referencia}; z = {z}).")]
        if z <= Config.Z_PRECIO_BAJO:
            return [Hallazgo("precio_bajo", Severidad.MEDIA, "Precio bajo para la zona",
                             f"Está por debajo de lo habitual ({referencia}; z = {z}).")]
        return []


class DetectorImagenes(Detector):
    def evaluar(self, ctx):
        if not ctx.imagenes:
            return [Hallazgo("sin_fotos", Severidad.MEDIA, "Aviso sin fotografías",
                             "No se puede comprobar visualmente el inmueble.")]
        if ctx.duplicados_imagen:
            titulos = ", ".join(sorted({d["titulo"] for d in ctx.duplicados_imagen})[:3])
            return [Hallazgo("imagen_clonada", Severidad.ALTA, "Fotografía repetida en otro aviso",
                             f"Coincide con fotos de otro arrendador: {titulos}.")]
        return []


class DetectorContacto(Detector):
    def evaluar(self, ctx):
        hallazgos = []
        if ctx.telefono_en_lista:
            hallazgos.append(Hallazgo("telefono_lista_negra", Severidad.CRITICA, "Teléfono con reporte confirmado",
                                      "Este número está vinculado a un caso confirmado por la moderación."))
        if ctx.otros_arrendadores_telefono:
            hallazgos.append(Hallazgo("telefono_compartido", Severidad.ALTA, "Teléfono usado por varias cuentas",
                                      f"El número aparece en {ctx.otros_arrendadores_telefono} cuenta(s) más."))
        return hallazgos


class DetectorDocumentos(Detector):
    def evaluar(self, ctx):
        estados = [d["estado"] for d in ctx.documentos]
        if "rechazado" in estados:
            return [Hallazgo("documento_rechazado", Severidad.ALTA, "Documento rechazado",
                             "La moderación no aceptó uno de los comprobantes presentados.")]
        if "aprobado" in estados:
            return []
        if estados:
            return [Hallazgo("documentos_pendientes", Severidad.INFO, "Documentos en revisión",
                             "Los comprobantes aún no han sido validados.")]
        return [Hallazgo("sin_documentos", Severidad.MEDIA, "Sin comprobante de titularidad",
                         "El arrendador no presentó título, partida ni recibo de servicios.")]


class DetectorCondiciones(Detector):
    def evaluar(self, ctx):
        aviso = ctx.inmueble
        hallazgos = []
        if aviso["pago_previo_visita"]:
            hallazgos.append(Hallazgo("pago_previo", Severidad.ALTA, "Pide pago antes de la visita",
                                      "Nunca transfieras dinero sin haber visto el inmueble."))
        if not aviso["contrato_escrito"]:
            hallazgos.append(Hallazgo("sin_contrato", Severidad.MEDIA, "No ofrece contrato escrito",
                                      "Sin contrato es más difícil recuperar adelantos o garantías."))
        if aviso["adelanto_meses"] + aviso["garantia_meses"] > Config.ADELANTO_MAXIMO_MESES + 1:
            hallazgos.append(Hallazgo("adelanto_excesivo", Severidad.MEDIA, "Adelanto y garantía elevados",
                                      f"Pide {aviso['adelanto_meses']:g} mes(es) de adelanto y "
                                      f"{aviso['garantia_meses']:g} de garantía."))
        return hallazgos


class DetectorTexto(Detector):
    def evaluar(self, ctx):
        aviso = ctx.inmueble
        encontrado = analizar_texto(f"{aviso['titulo']} {aviso['descripcion']}")
        hallazgos = []
        if encontrado["presion"]:
            hallazgos.append(Hallazgo("lenguaje_presion", Severidad.MEDIA, "Lenguaje de urgencia",
                                      "Frases detectadas: " + ", ".join(encontrado["presion"]) + "."))
        if encontrado["evasion"]:
            hallazgos.append(Hallazgo("lenguaje_evasivo", Severidad.ALTA, "Evita la visita o el contrato",
                                      "Frases detectadas: " + ", ".join(encontrado["evasion"]) + "."))
        return hallazgos


class DetectorUbicacion(Detector):
    def evaluar(self, ctx):
        estado = ctx.inmueble["direccion_estado"]
        if estado == "fuera_distrito":
            return [Hallazgo("direccion_fuera_distrito", Severidad.ALTA, "Ubicación no coincide con el distrito",
                             "El punto del mapa está lejos del distrito declarado.")]
        if estado == "no_encontrada":
            return [Hallazgo("direccion_no_encontrada", Severidad.MEDIA, "Dirección no encontrada",
                             "OpenStreetMap no localizó la dirección declarada.")]
        return []


class DetectorReportes(Detector):
    def evaluar(self, ctx):
        hallazgos = []
        if ctx.reportes_confirmados:
            hallazgos.append(Hallazgo("reporte_confirmado", Severidad.CRITICA, "Reporte confirmado",
                                      "La moderación confirmó al menos un reporte sobre este aviso."))
        if ctx.reportes_abiertos >= 2:
            hallazgos.append(Hallazgo("reportes_multiples", Severidad.ALTA, "Varios reportes abiertos",
                                      f"Tiene {ctx.reportes_abiertos} reportes en revisión."))
        elif ctx.reportes_abiertos == 1:
            hallazgos.append(Hallazgo("reporte_abierto", Severidad.MEDIA, "Reporte en revisión",
                                      "Un estudiante reportó este aviso y aún no hay resolución."))
        return hallazgos


DETECTORES: tuple[Detector, ...] = (
    DetectorPrecio(), DetectorImagenes(), DetectorContacto(), DetectorDocumentos(),
    DetectorCondiciones(), DetectorTexto(), DetectorUbicacion(), DetectorReportes(),
)
