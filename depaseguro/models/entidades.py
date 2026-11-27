"""Clases de dominio (POO): herencia, polimorfismo y objetos de transferencia (DTO)."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum


class Severidad(str, Enum):
    INFO = "info"
    MEDIA = "media"
    ALTA = "alta"
    CRITICA = "critica"


class NivelRiesgo(str, Enum):
    CONFIABLE = "Confiable"
    PRECAUCION = "Precaución"
    RIESGO_ALTO = "Riesgo alto"
    CRITICO = "Crítico"

    @classmethod
    def desde_puntaje(cls, puntaje: int) -> "NivelRiesgo":
        if puntaje >= 75:
            return cls.CONFIABLE
        if puntaje >= 50:
            return cls.PRECAUCION
        if puntaje >= 25:
            return cls.RIESGO_ALTO
        return cls.CRITICO


class Usuario(ABC):
    """Clase base: define lo común y obliga a cada rol a declarar sus permisos."""

    rol = "usuario"

    def __init__(self, id: int, nombre: str, email: str, verificado: bool = False, activo: bool = True,
                 telefono: str | None = None) -> None:
        self.id = id
        self.nombre = nombre
        self.email = email
        self.verificado = bool(verificado)
        self.activo = bool(activo)
        self.telefono = telefono

    @abstractmethod
    def permisos(self) -> frozenset[str]:
        """Conjunto de acciones habilitadas para el rol."""

    @abstractmethod
    def panel_inicio(self) -> str:
        """Nombre del endpoint al que entra el usuario tras iniciar sesión."""

    def puede(self, permiso: str) -> bool:
        return self.activo and permiso in self.permisos()

    @property
    def iniciales(self) -> str:
        return "".join(parte[0] for parte in self.nombre.split()[:2]).upper()


class Estudiante(Usuario):
    rol = "estudiante"

    def permisos(self) -> frozenset[str]:
        return frozenset({"favoritos", "resenar", "reportar", "guardar_busqueda"})

    def panel_inicio(self) -> str:
        return "estudiante.panel"


class Arrendador(Usuario):
    rol = "arrendador"

    def permisos(self) -> frozenset[str]:
        return frozenset({"publicar", "subir_documentos", "generar_codigo", "responder_reporte"})

    def panel_inicio(self) -> str:
        return "arrendador.panel"


class Administrador(Usuario):
    rol = "admin"

    def permisos(self) -> frozenset[str]:
        return frozenset({"moderar", "gestionar_usuarios", "ejecutar_ingesta", "exportar", "ver_documentos"})

    def panel_inicio(self) -> str:
        return "admin.panel"


_ROLES = {clase.rol: clase for clase in (Estudiante, Arrendador, Administrador)}


def fabrica_usuario(fila) -> Usuario:
    """Patrón Factory: crea la subclase correcta a partir de una fila de la base de datos."""
    datos = dict(fila)
    clase = _ROLES[datos["rol"]]
    return clase(datos["id"], datos["nombre"], datos["email"], datos["verificado"], datos["activo"],
                 datos.get("telefono"))


@dataclass(frozen=True)
class Hallazgo:
    """Resultado inmutable de un detector."""

    hecho: str
    severidad: Severidad
    titulo: str
    detalle: str


@dataclass(frozen=True)
class ComponenteScore:
    nombre: str
    obtenido: float
    maximo: float
    explicacion: str


@dataclass(frozen=True)
class ResultadoEvaluacion:
    """DTO que viaja del servicio de evaluación hacia la vista y la persistencia."""

    inmueble_id: int
    trust_score: int
    nivel: NivelRiesgo
    componentes: tuple[ComponenteScore, ...]
    hallazgos: tuple[Hallazgo, ...]
    patrones: tuple[str, ...]
    recomendaciones: tuple[str, ...]
    es_critico: bool = False


@dataclass(frozen=True)
class PrecioNormalizado:
    mensual_pen: float
    por_m2_pen: float
    tipo_cambio: float | None = None


@dataclass
class ContextoEvaluacion:
    """Datos reunidos una sola vez y compartidos por todos los detectores."""

    inmueble: dict
    imagenes: list[dict] = field(default_factory=list)
    documentos: list[dict] = field(default_factory=list)
    duplicados_imagen: list[dict] = field(default_factory=list)
    telefono_en_lista: bool = False
    otros_arrendadores_telefono: int = 0
    reportes_abiertos: int = 0
    reportes_confirmados: int = 0
    resenas: list[dict] = field(default_factory=list)
    z_precio: float | None = None
    mediana_referencia: float | None = None
    muestra_precio: int = 0
