"""Funciones puras de cálculo: normalización, estadística, hashes, validación y geografía."""
from __future__ import annotations

import hashlib
import io
import math
import re
import unicodedata

import numpy as np
import pandas as pd
from PIL import Image

from ..models.entidades import PrecioNormalizado

FACTOR_PERIODO = {"semana": 52 / 12, "mes": 1, "semestre": 1 / 6, "anio": 1 / 12}


def normalizar_precio(precio: float, moneda: str, periodo: str, area_m2: float,
                      tipo_cambio: float) -> PrecioNormalizado:
    """Convierte cualquier precio publicado a soles por mes y soles por m²."""
    if precio <= 0 or area_m2 <= 0:
        raise ValueError("El precio y el área deben ser mayores que cero.")
    if periodo not in FACTOR_PERIODO:
        raise ValueError(f"Periodo no reconocido: {periodo}")
    en_soles = precio * tipo_cambio if moneda == "USD" else precio
    mensual = en_soles * FACTOR_PERIODO[periodo]
    return PrecioNormalizado(round(mensual, 2), round(mensual / area_m2, 2),
                             tipo_cambio if moneda == "USD" else None)


def deflactar(monto: float, ipc_origen: float, ipc_actual: float) -> float:
    """Expresa un monto antiguo en soles de hoy usando el índice de precios."""
    return round(monto * ipc_actual / ipc_origen, 2)


def z_robusto(valor: float, muestra: list[float]) -> tuple[float | None, float | None]:
    """Puntaje z robusto (mediana y MAD). Resiste mejor los precios falsos que media y desviación."""
    if not muestra:
        return None, None
    serie = pd.Series(muestra, dtype="float64")
    mediana = float(serie.median())
    mad = float((serie - mediana).abs().median())
    escala = 1.4826 * mad
    if escala < 1e-9:
        escala = max(float(serie.std(ddof=0)), 0.10 * mediana, 1e-9)
    return round((valor - mediana) / escala, 2), round(mediana, 2)


def resumen_precios(filas: list[dict]) -> list[dict]:
    """Agrupa precios por distrito con pandas para reportes y panel de control."""
    if not filas:
        return []
    tabla = pd.DataFrame(filas)
    agrupado = tabla.groupby("distrito").agg(
        avisos=("id", "count"),
        mediana_mensual=("precio_mensual_pen", "median"),
        mediana_m2=("precio_m2_pen", "median"),
        trust_medio=("trust_score", "mean"),
    ).reset_index().sort_values("avisos", ascending=False)
    return agrupado.round(2).to_dict("records")


def tendencia_y_proyeccion(valores: list[float], pasos: int = 3) -> dict:
    """Ajusta una recta por mínimos cuadrados y proyecta los siguientes periodos."""
    if len(valores) < 3:
        return {"pendiente": 0.0, "proyeccion": []}
    eje = np.arange(len(valores))
    pendiente, intercepto = np.polyfit(eje, np.array(valores, dtype=float), 1)
    futuro = np.arange(len(valores), len(valores) + pasos)
    proyeccion = [max(0.0, round(float(pendiente * x + intercepto), 1)) for x in futuro]
    return {"pendiente": round(float(pendiente), 3), "proyeccion": proyeccion}


def sha256_bytes(contenido: bytes) -> str:
    return hashlib.sha256(contenido).hexdigest()


def dhash(imagen: Image.Image, tamano: int = 8) -> str:
    """Hash perceptual por diferencias: compara brillo entre píxeles vecinos.

    Dos fotos iguales con distinto tamaño o compresión producen hashes casi
    idénticos, algo que un SHA-256 no detecta.
    """
    gris = imagen.convert("L").resize((tamano + 1, tamano), Image.Resampling.LANCZOS)
    pixeles = gris.tobytes()
    bits = 0
    for fila in range(tamano):
        for columna in range(tamano):
            izquierda = pixeles[fila * (tamano + 1) + columna]
            derecha = pixeles[fila * (tamano + 1) + columna + 1]
            bits = (bits << 1) | int(izquierda > derecha)
    return f"{bits:0{tamano * tamano // 4}x}"


def hamming(hash_a: str, hash_b: str) -> int:
    return bin(int(hash_a, 16) ^ int(hash_b, 16)).count("1")


def analizar_imagen(contenido: bytes) -> dict:
    """Valida que los bytes sean una imagen real y calcula sus huellas."""
    with Image.open(io.BytesIO(contenido)) as prueba:
        prueba.verify()
    with Image.open(io.BytesIO(contenido)) as imagen:
        if imagen.format not in {"JPEG", "PNG", "WEBP"}:
            raise ValueError("Formato de imagen no permitido.")
        return {"sha256": sha256_bytes(contenido), "dhash": dhash(imagen),
                "ancho": imagen.width, "alto": imagen.height, "formato": imagen.format}


def normalizar_telefono(telefono: str) -> str:
    """Deja solo los 9 dígitos de un celular peruano para poder compararlo."""
    digitos = re.sub(r"\D", "", telefono or "")
    if digitos.startswith("51") and len(digitos) == 11:
        digitos = digitos[2:]
    return digitos


def telefono_valido(telefono: str) -> bool:
    return bool(re.fullmatch(r"9\d{8}", normalizar_telefono(telefono)))


def dni_valido(dni: str) -> bool:
    return bool(re.fullmatch(r"\d{8}", dni or ""))


def ruc_valido(ruc: str) -> bool:
    """Valida longitud, prefijo y dígito verificador (módulo 11) del RUC."""
    if not re.fullmatch(r"(10|15|17|20)\d{9}", ruc or ""):
        return False
    pesos = (5, 4, 3, 2, 7, 6, 5, 4, 3, 2)
    suma = sum(int(digito) * peso for digito, peso in zip(ruc[:10], pesos))
    verificador = 11 - suma % 11
    if verificador >= 10:
        verificador -= 10
    return verificador == int(ruc[10])


def distancia_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distancia sobre la superficie terrestre con la fórmula de Haversine."""
    radio = 6371.0
    fi1, fi2 = math.radians(lat1), math.radians(lat2)
    delta_fi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = math.sin(delta_fi / 2) ** 2 + math.cos(fi1) * math.cos(fi2) * math.sin(delta_lambda / 2) ** 2
    return round(radio * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)), 2)


def sin_acentos(texto: str) -> str:
    base = unicodedata.normalize("NFD", texto or "")
    return "".join(c for c in base if unicodedata.category(c) != "Mn")


FRASES_RIESGO = {
    "presion": ("solo hoy", "ultimo cuarto", "ultima habitacion", "urgente", "muchos interesados",
                "se va rapido", "reserva ya", "reserva ahora", "aprovecha ya", "hoy mismo", "no pierdas"),
    "pago": ("yape", "plin", "deposita", "deposito", "transferencia", "adelanta", "adelanto antes",
             "separa con", "separar con", "reserva con", "pago por adelantado", "paga antes"),
    "evasion": ("sin visita", "no hay visitas", "estoy de viaje", "fuera de la ciudad", "fuera del pais",
                "te envio las llaves", "por courier", "sin contrato", "no necesitas contrato",
                "el dueno no esta", "solo por whatsapp"),
}


def analizar_texto(texto: str) -> dict[str, list[str]]:
    """Busca expresiones típicas de estafa, sin distinguir mayúsculas ni tildes."""
    limpio = sin_acentos(texto).lower()
    return {
        categoria: [frase for frase in frases if frase in limpio]
        for categoria, frases in FRASES_RIESGO.items()
    }


CLAUSULAS_ABUSIVAS = (
    (r"(no|sin) (se )?(devuelve|devolvera|reembols)\w*.{0,30}(garantia|deposito)|garantia.{0,40}no (es|sera) (reembolsable|devuelta)",
     "alta", "La garantía no se devuelve",
     "La garantía debe devolverse al terminar el contrato, descontando solo daños comprobados."),
    (r"(ingres\w+|entrar|acceder).{0,50}(cualquier momento|sin aviso|sin previo aviso)",
     "alta", "Ingreso al cuarto sin aviso",
     "El arrendador no debería entrar sin acuerdo previo con quien ocupa el cuarto."),
    (r"(aument\w+|subir|increment\w+).{0,40}(cuando|en cualquier|libremente|sin aviso|a su criterio)",
     "alta", "Aumento de renta unilateral",
     "El monto y la forma de reajuste deben estar pactados en el contrato."),
    (r"(desaloj\w+|retirar\w*|cambiar\w* (la )?chapa|corte\w*.{0,20}(agua|luz)).{0,60}(sin aviso|inmediat\w+|de inmediato|cualquier momento)",
     "alta", "Desalojo o corte de servicios inmediato",
     "Cortar servicios o cambiar la chapa por cuenta propia puede ser ilegal; exige un procedimiento claro."),
    (r"renuncia\w*.{0,40}(reclam\w+|derecho\w*|demand\w+|denuncia\w*)",
     "alta", "Renuncia a reclamar",
     "Una cláusula no debería impedirte acudir a las autoridades."),
    (r"(penalidad|multa).{0,40}(\d+ (meses|mes)|total del contrato|todos los meses)",
     "media", "Penalidad desproporcionada",
     "Revisa que la penalidad guarde proporción con el daño real."),
    (r"visitas? (prohibid\w+|no permitid\w+)|prohibid\w+.{0,20}visitas?",
     "media", "Prohibición total de visitas",
     "Conviene pactar reglas de convivencia razonables en lugar de una prohibición absoluta."),
)


def analizar_clausulas(texto: str) -> list[dict]:
    """Detecta cláusulas potencialmente abusivas en un contrato pegado por el usuario."""
    limpio = sin_acentos(texto).lower()
    return [
        {"severidad": severidad, "titulo": titulo, "consejo": consejo}
        for patron, severidad, titulo, consejo in CLAUSULAS_ABUSIVAS
        if re.search(patron, limpio)
    ]
