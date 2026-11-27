"""DAOs concretos: cada clase concentra las consultas propias de una entidad."""
from __future__ import annotations

from .base import BaseDAO


class UsuarioDAO(BaseDAO):
    tabla = "usuarios"

    def por_email(self, email: str) -> dict | None:
        fila = self.db.execute("SELECT * FROM usuarios WHERE email = ?", (email.strip().lower(),)).fetchone()
        return dict(fila) if fila else None


class DistritoDAO(BaseDAO):
    tabla = "distritos"
    clave = "ubigeo"

    def todos(self) -> list[dict]:
        return [dict(f) for f in self.db.execute("SELECT * FROM distritos ORDER BY nombre")]


class CampusDAO(BaseDAO):
    tabla = "campus"

    def todos(self) -> list[dict]:
        return [dict(f) for f in self.db.execute("SELECT * FROM campus ORDER BY universidad, codigo_local")]


class InmuebleDAO(BaseDAO):
    tabla = "inmuebles"

    def detalle(self, inmueble_id: int) -> dict | None:
        fila = self.db.execute("SELECT * FROM v_inmuebles WHERE id = ?", (inmueble_id,)).fetchone()
        return dict(fila) if fila else None

    def publicados(self) -> list[dict]:
        filas = self.db.execute(
            "SELECT * FROM v_inmuebles WHERE estado IN ('publicado','observado') ORDER BY trust_score DESC, id DESC"
        )
        return [dict(f) for f in filas]

    def todos_detalle(self) -> list[dict]:
        return [dict(f) for f in self.db.execute("SELECT * FROM v_inmuebles ORDER BY id DESC")]

    def de_arrendador(self, arrendador_id: int) -> list[dict]:
        filas = self.db.execute(
            "SELECT * FROM v_inmuebles WHERE arrendador_id = ? ORDER BY id DESC", (arrendador_id,)
        )
        return [dict(f) for f in filas]

    def servicios(self, inmueble_id: int) -> list[str]:
        filas = self.db.execute(
            """SELECT s.nombre FROM servicios s
               JOIN inmueble_servicios x ON x.servicio_id = s.id
               WHERE x.inmueble_id = ? ORDER BY s.nombre""",
            (inmueble_id,),
        )
        return [f["nombre"] for f in filas]

    def fijar_servicios(self, inmueble_id: int, nombres: list[str]) -> None:
        self.db.execute("DELETE FROM inmueble_servicios WHERE inmueble_id = ?", (inmueble_id,))
        for nombre in nombres:
            self.db.execute("INSERT OR IGNORE INTO servicios(nombre) VALUES (?)", (nombre,))
            self.db.execute(
                """INSERT OR IGNORE INTO inmueble_servicios(inmueble_id, servicio_id)
                   SELECT ?, id FROM servicios WHERE nombre = ?""",
                (inmueble_id, nombre),
            )
        self.db.commit()

    def precios_comparables(self, inmueble_id: int, tipo: str, ubigeo: str | None = None) -> list[float]:
        """Precios por m² de avisos del mismo tipo, excluyendo el aviso evaluado."""
        sql = """SELECT precio_m2_pen FROM inmuebles
                 WHERE tipo = ? AND id != ? AND precio_m2_pen IS NOT NULL
                   AND estado IN ('publicado','observado','pendiente')"""
        parametros: tuple = (tipo, inmueble_id)
        if ubigeo:
            sql += " AND ubigeo = ?"
            parametros += (ubigeo,)
        return [f[0] for f in self.db.execute(sql, parametros)]


class ImagenDAO(BaseDAO):
    tabla = "imagenes"

    def de_inmueble(self, inmueble_id: int) -> list[dict]:
        return [dict(f) for f in self.db.execute(
            "SELECT * FROM imagenes WHERE inmueble_id = ? ORDER BY id", (inmueble_id,))]

    def de_otros_arrendadores(self, inmueble_id: int, arrendador_id: int) -> list[dict]:
        filas = self.db.execute(
            """SELECT g.*, i.titulo, i.arrendador_id FROM imagenes g
               JOIN inmuebles i ON i.id = g.inmueble_id
               WHERE g.inmueble_id != ? AND i.arrendador_id != ?""",
            (inmueble_id, arrendador_id),
        )
        return [dict(f) for f in filas]

    def todas(self) -> list[dict]:
        filas = self.db.execute(
            """SELECT g.*, i.arrendador_id, i.titulo FROM imagenes g
               JOIN inmuebles i ON i.id = g.inmueble_id"""
        )
        return [dict(f) for f in filas]


class DocumentoDAO(BaseDAO):
    tabla = "documentos"

    def de_inmueble(self, inmueble_id: int) -> list[dict]:
        return [dict(f) for f in self.db.execute(
            "SELECT * FROM documentos WHERE inmueble_id = ? ORDER BY id", (inmueble_id,))]

    def pendientes(self) -> list[dict]:
        filas = self.db.execute(
            """SELECT d.*, i.titulo, u.nombre AS arrendador FROM documentos d
               JOIN inmuebles i ON i.id = d.inmueble_id
               JOIN usuarios u ON u.id = i.arrendador_id
               WHERE d.estado = 'pendiente' ORDER BY d.id"""
        )
        return [dict(f) for f in filas]


class ResenaDAO(BaseDAO):
    tabla = "resenas"

    def de_inmueble(self, inmueble_id: int) -> list[dict]:
        filas = self.db.execute(
            """SELECT r.*, u.nombre AS autor FROM resenas r
               JOIN usuarios u ON u.id = r.estudiante_id
               WHERE r.inmueble_id = ? ORDER BY r.verificada DESC, r.id DESC""",
            (inmueble_id,),
        )
        return [dict(f) for f in filas]


class ReporteDAO(BaseDAO):
    tabla = "reportes"

    def de_inmueble(self, inmueble_id: int) -> list[dict]:
        return [dict(f) for f in self.db.execute(
            "SELECT * FROM reportes WHERE inmueble_id = ? ORDER BY id DESC", (inmueble_id,))]

    def con_detalle(self, condicion: str = "1=1", parametros: tuple = ()) -> list[dict]:
        filas = self.db.execute(
            f"""SELECT r.*, i.titulo, i.telefono_contacto, i.arrendador_id, i.direccion,
                       u.nombre AS reportante, u.email AS reportante_email
                FROM reportes r
                LEFT JOIN inmuebles i ON i.id = r.inmueble_id
                JOIN usuarios u ON u.id = r.reportante_id
                WHERE {condicion} ORDER BY r.id DESC""",
            parametros,
        )
        return [dict(f) for f in filas]


class DescargoDAO(BaseDAO):
    tabla = "descargos"

    def de_reporte(self, reporte_id: int) -> list[dict]:
        return [dict(f) for f in self.db.execute(
            "SELECT * FROM descargos WHERE reporte_id = ? ORDER BY id", (reporte_id,))]


class ListaContactosDAO(BaseDAO):
    tabla = "lista_contactos"

    def contiene(self, telefono: str) -> bool:
        return self.contar("telefono = ?", (telefono,)) > 0


class EvaluacionDAO(BaseDAO):
    tabla = "evaluaciones"

    def ultima(self, inmueble_id: int) -> dict | None:
        fila = self.db.execute(
            "SELECT * FROM evaluaciones WHERE inmueble_id = ? ORDER BY id DESC LIMIT 1", (inmueble_id,)
        ).fetchone()
        return dict(fila) if fila else None

    def historial(self, inmueble_id: int) -> list[dict]:
        return [dict(f) for f in self.db.execute(
            "SELECT id, trust_score, nivel, creado_en FROM evaluaciones WHERE inmueble_id = ? ORDER BY id",
            (inmueble_id,))]


class AlertaDAO(BaseDAO):
    tabla = "alertas"

    def registrar(self, tipo: str, severidad: str, mensaje: str, inmueble_id: int | None = None,
                  usuario_id: int | None = None, clave: str | None = None) -> bool:
        """Guarda una alerta. Una ``clave`` repetida se ignora para no duplicar avisos."""
        cursor = self.db.execute(
            """INSERT OR IGNORE INTO alertas(usuario_id, inmueble_id, tipo, severidad, mensaje, clave)
               VALUES (?,?,?,?,?,?)""",
            (usuario_id, inmueble_id, tipo, severidad, mensaje, clave),
        )
        self.db.commit()
        return cursor.rowcount > 0

    def de_usuario(self, usuario_id: int, limite: int = 50) -> list[dict]:
        return [dict(f) for f in self.db.execute(
            "SELECT * FROM alertas WHERE usuario_id = ? ORDER BY id DESC LIMIT ?", (usuario_id, limite))]

    def globales(self, limite: int = 100) -> list[dict]:
        filas = self.db.execute(
            """SELECT a.*, i.titulo FROM alertas a LEFT JOIN inmuebles i ON i.id = a.inmueble_id
               WHERE a.usuario_id IS NULL ORDER BY a.id DESC LIMIT ?""",
            (limite,),
        )
        return [dict(f) for f in filas]

    def sin_leer(self, usuario_id: int) -> int:
        return self.contar("usuario_id = ? AND leida = 0", (usuario_id,))


class FavoritoDAO(BaseDAO):
    tabla = "favoritos"

    def alternar(self, usuario_id: int, inmueble_id: int) -> bool:
        existente = self.db.execute(
            "SELECT 1 FROM favoritos WHERE usuario_id = ? AND inmueble_id = ?", (usuario_id, inmueble_id)
        ).fetchone()
        if existente:
            self.db.execute("DELETE FROM favoritos WHERE usuario_id = ? AND inmueble_id = ?",
                            (usuario_id, inmueble_id))
        else:
            self.db.execute("INSERT INTO favoritos(usuario_id, inmueble_id) VALUES (?,?)",
                            (usuario_id, inmueble_id))
        self.db.commit()
        return not existente

    def de_usuario(self, usuario_id: int) -> list[dict]:
        filas = self.db.execute(
            """SELECT v.* FROM v_inmuebles v JOIN favoritos f ON f.inmueble_id = v.id
               WHERE f.usuario_id = ? ORDER BY f.creado_en DESC""",
            (usuario_id,),
        )
        return [dict(f) for f in filas]

    def seguidores(self, inmueble_id: int) -> list[int]:
        return [f[0] for f in self.db.execute(
            "SELECT usuario_id FROM favoritos WHERE inmueble_id = ?", (inmueble_id,))]


class BusquedaGuardadaDAO(BaseDAO):
    tabla = "busquedas_guardadas"

    def de_usuario(self, usuario_id: int) -> list[dict]:
        filas = self.db.execute(
            """SELECT b.*, c.universidad, c.codigo_local FROM busquedas_guardadas b
               LEFT JOIN campus c ON c.id = b.campus_id WHERE b.usuario_id = ? ORDER BY b.id DESC""",
            (usuario_id,),
        )
        return [dict(f) for f in filas]

    def todas(self) -> list[dict]:
        filas = self.db.execute(
            """SELECT b.*, c.lat, c.lon, c.universidad FROM busquedas_guardadas b
               LEFT JOIN campus c ON c.id = b.campus_id"""
        )
        return [dict(f) for f in filas]


class FuenteDAO(BaseDAO):
    tabla = "fuentes_datos"
    clave = "clave"

    def todas(self) -> list[dict]:
        return [dict(f) for f in self.db.execute(
            "SELECT * FROM fuentes_datos ORDER BY categoria, nombre")]


class IngestaDAO(BaseDAO):
    tabla = "ingestas"


class IndicadorDAO(BaseDAO):
    tabla = "indicadores"

    def guardar(self, clave: str, periodo: str, valor: float, fuente: str) -> None:
        self.db.execute(
            "INSERT OR REPLACE INTO indicadores(clave, periodo, valor, fuente) VALUES (?,?,?,?)",
            (clave, periodo, valor, fuente),
        )

    def ultimo(self, clave: str) -> dict | None:
        filas = self.serie(clave)
        return filas[-1] if filas else None

    def serie(self, clave: str) -> list[dict]:
        filas = [dict(f) for f in self.db.execute("SELECT * FROM indicadores WHERE clave = ?", (clave,))]
        return sorted(filas, key=lambda fila: fila["periodo"])


class BlogDAO(BaseDAO):
    tabla = "blog_posts"

    def por_slug(self, slug: str) -> dict | None:
        fila = self.db.execute("SELECT * FROM blog_posts WHERE slug = ?", (slug,)).fetchone()
        return dict(fila) if fila else None


class ContactoDAO(BaseDAO):
    tabla = "contactos"


class CodigoVisitaDAO(BaseDAO):
    tabla = "codigos_visita"

    def por_codigo(self, codigo: str) -> dict | None:
        fila = self.db.execute("SELECT * FROM codigos_visita WHERE codigo = ?", (codigo.strip().upper(),)).fetchone()
        return dict(fila) if fila else None


class VerificacionRapidaDAO(BaseDAO):
    tabla = "verificaciones_rapidas"


class AuditoriaDAO(BaseDAO):
    tabla = "auditoria"

    def registrar(self, usuario_id, accion: str, entidad: str, entidad_id=None, detalle: str | None = None) -> None:
        self.insertar({"usuario_id": usuario_id, "accion": accion, "entidad": entidad,
                       "entidad_id": entidad_id, "detalle": detalle})

    def recientes(self, limite: int = 100) -> list[dict]:
        filas = self.db.execute(
            """SELECT a.*, u.nombre AS usuario FROM auditoria a
               LEFT JOIN usuarios u ON u.id = a.usuario_id ORDER BY a.id DESC LIMIT ?""",
            (limite,),
        )
        return [dict(f) for f in filas]
