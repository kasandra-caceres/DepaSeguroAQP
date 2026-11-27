-- DepaSeguro AQP - Modelo físico (SQLite 3)
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS usuarios (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre        TEXT NOT NULL,
    email         TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    rol           TEXT NOT NULL CHECK (rol IN ('estudiante','arrendador','admin')),
    telefono      TEXT,
    tipo_doc      TEXT CHECK (tipo_doc IN ('DNI','RUC','CE') OR tipo_doc IS NULL),
    num_doc       TEXT,
    verificado    INTEGER NOT NULL DEFAULT 0,
    activo        INTEGER NOT NULL DEFAULT 1,
    es_demo       INTEGER NOT NULL DEFAULT 0,
    creado_en     TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS distritos (
    ubigeo            TEXT PRIMARY KEY,
    nombre            TEXT NOT NULL UNIQUE,
    lat               REAL,
    lon               REAL,
    poblacion         INTEGER,
    poblacion_fuente  TEXT
);

CREATE TABLE IF NOT EXISTS campus (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    universidad   TEXT NOT NULL,
    codigo_local  TEXT NOT NULL,
    distrito      TEXT,
    lat           REAL NOT NULL,
    lon           REAL NOT NULL,
    licencia      TEXT,
    fecha_corte   TEXT,
    actualizado_en TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    UNIQUE (universidad, codigo_local)
);

CREATE TABLE IF NOT EXISTS inmuebles (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    arrendador_id       INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    titulo              TEXT NOT NULL,
    descripcion         TEXT NOT NULL,
    tipo                TEXT NOT NULL CHECK (tipo IN ('cuarto','minidepartamento','departamento','pension')),
    ubigeo              TEXT NOT NULL REFERENCES distritos(ubigeo),
    direccion           TEXT NOT NULL,
    lat                 REAL,
    lon                 REAL,
    area_m2             REAL NOT NULL CHECK (area_m2 > 0),
    precio              REAL NOT NULL CHECK (precio > 0),
    moneda              TEXT NOT NULL DEFAULT 'PEN' CHECK (moneda IN ('PEN','USD')),
    periodo             TEXT NOT NULL DEFAULT 'mes' CHECK (periodo IN ('semana','mes','semestre','anio')),
    precio_mensual_pen  REAL,
    precio_m2_pen       REAL,
    adelanto_meses      REAL NOT NULL DEFAULT 1,
    garantia_meses      REAL NOT NULL DEFAULT 1,
    pago_previo_visita  INTEGER NOT NULL DEFAULT 0,
    contrato_escrito    INTEGER NOT NULL DEFAULT 1,
    telefono_contacto   TEXT NOT NULL,
    estado              TEXT NOT NULL DEFAULT 'pendiente'
                        CHECK (estado IN ('pendiente','publicado','observado','rechazado','retirado')),
    trust_score         INTEGER,
    nivel_riesgo        TEXT,
    direccion_estado    TEXT NOT NULL DEFAULT 'sin_verificar',
    es_demo             INTEGER NOT NULL DEFAULT 0,
    creado_en           TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    actualizado_en      TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);
CREATE INDEX IF NOT EXISTS ix_inmuebles_distrito ON inmuebles(ubigeo, tipo);
CREATE INDEX IF NOT EXISTS ix_inmuebles_estado ON inmuebles(estado, trust_score);
CREATE INDEX IF NOT EXISTS ix_inmuebles_telefono ON inmuebles(telefono_contacto);

CREATE TABLE IF NOT EXISTS servicios (
    id     INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS inmueble_servicios (
    inmueble_id INTEGER NOT NULL REFERENCES inmuebles(id) ON DELETE CASCADE,
    servicio_id INTEGER NOT NULL REFERENCES servicios(id) ON DELETE CASCADE,
    PRIMARY KEY (inmueble_id, servicio_id)
);

CREATE TABLE IF NOT EXISTS imagenes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    inmueble_id INTEGER NOT NULL REFERENCES inmuebles(id) ON DELETE CASCADE,
    archivo     TEXT NOT NULL,
    sha256      TEXT NOT NULL,
    dhash       TEXT NOT NULL,
    ancho       INTEGER,
    alto        INTEGER,
    creado_en   TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);
CREATE INDEX IF NOT EXISTS ix_imagenes_sha ON imagenes(sha256);

CREATE TABLE IF NOT EXISTS documentos (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    inmueble_id   INTEGER NOT NULL REFERENCES inmuebles(id) ON DELETE CASCADE,
    tipo          TEXT NOT NULL CHECK (tipo IN ('titularidad','recibo_servicio','identidad')),
    archivo       TEXT NOT NULL,
    sha256        TEXT NOT NULL,
    estado        TEXT NOT NULL DEFAULT 'pendiente' CHECK (estado IN ('pendiente','aprobado','rechazado')),
    observacion   TEXT,
    revisado_por  INTEGER REFERENCES usuarios(id),
    revisado_en   TEXT,
    creado_en     TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS codigos_visita (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    inmueble_id INTEGER NOT NULL REFERENCES inmuebles(id) ON DELETE CASCADE,
    codigo      TEXT NOT NULL UNIQUE,
    usado_por   INTEGER REFERENCES usuarios(id),
    usado_en    TEXT,
    creado_en   TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS resenas (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    inmueble_id  INTEGER NOT NULL REFERENCES inmuebles(id) ON DELETE CASCADE,
    estudiante_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    puntaje      INTEGER NOT NULL CHECK (puntaje BETWEEN 1 AND 5),
    comentario   TEXT NOT NULL,
    verificada   INTEGER NOT NULL DEFAULT 0,
    creado_en    TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    UNIQUE (inmueble_id, estudiante_id)
);

CREATE TABLE IF NOT EXISTS reportes (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    inmueble_id   INTEGER REFERENCES inmuebles(id) ON DELETE SET NULL,
    reportante_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    motivo        TEXT NOT NULL CHECK (motivo IN ('inexistente','fotos_falsas','cobro_indebido','suplantacion','condiciones_abusivas','otro')),
    detalle       TEXT NOT NULL,
    telefono_reportado TEXT,
    monto_perdido REAL NOT NULL DEFAULT 0,
    estado        TEXT NOT NULL DEFAULT 'abierto' CHECK (estado IN ('abierto','en_revision','confirmado','descartado')),
    resolucion    TEXT,
    creado_en     TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    resuelto_en   TEXT
);

CREATE TABLE IF NOT EXISTS descargos (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    reporte_id    INTEGER NOT NULL REFERENCES reportes(id) ON DELETE CASCADE,
    arrendador_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    texto         TEXT NOT NULL,
    creado_en     TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS lista_contactos (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    telefono   TEXT NOT NULL UNIQUE,
    motivo     TEXT NOT NULL,
    reporte_id INTEGER REFERENCES reportes(id) ON DELETE SET NULL,
    creado_en  TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS evaluaciones (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    inmueble_id  INTEGER NOT NULL REFERENCES inmuebles(id) ON DELETE CASCADE,
    trust_score  INTEGER NOT NULL,
    nivel        TEXT NOT NULL,
    componentes  TEXT NOT NULL,
    hallazgos    TEXT NOT NULL,
    patrones     TEXT NOT NULL,
    creado_en    TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);
CREATE INDEX IF NOT EXISTS ix_evaluaciones_inmueble ON evaluaciones(inmueble_id, id);

CREATE TABLE IF NOT EXISTS alertas (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id  INTEGER REFERENCES usuarios(id) ON DELETE CASCADE,
    inmueble_id INTEGER REFERENCES inmuebles(id) ON DELETE CASCADE,
    tipo        TEXT NOT NULL,
    severidad   TEXT NOT NULL CHECK (severidad IN ('info','media','alta','critica')),
    mensaje     TEXT NOT NULL,
    clave       TEXT UNIQUE,
    leida       INTEGER NOT NULL DEFAULT 0,
    creado_en   TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS favoritos (
    usuario_id  INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    inmueble_id INTEGER NOT NULL REFERENCES inmuebles(id) ON DELETE CASCADE,
    creado_en   TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    PRIMARY KEY (usuario_id, inmueble_id)
);

CREATE TABLE IF NOT EXISTS busquedas_guardadas (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    campus_id  INTEGER REFERENCES campus(id) ON DELETE SET NULL,
    radio_km   REAL NOT NULL DEFAULT 2,
    precio_max REAL NOT NULL,
    trust_min  INTEGER NOT NULL DEFAULT 60,
    creado_en  TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS verificaciones_rapidas (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    puntaje    INTEGER NOT NULL,
    nivel      TEXT NOT NULL,
    resultado  TEXT NOT NULL,
    creado_en  TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

-- Fuentes externas y datos leídos automáticamente
CREATE TABLE IF NOT EXISTS fuentes_datos (
    clave             TEXT PRIMARY KEY,
    nombre            TEXT NOT NULL,
    entidad           TEXT NOT NULL,
    categoria         TEXT NOT NULL CHECK (categoria IN ('estado','ong')),
    url               TEXT NOT NULL,
    uso               TEXT NOT NULL,
    ultima_ejecucion  TEXT,
    ultimo_exito      TEXT,
    estado            TEXT NOT NULL DEFAULT 'pendiente',
    registros         INTEGER NOT NULL DEFAULT 0,
    mensaje           TEXT,
    huella            TEXT
);

CREATE TABLE IF NOT EXISTS ingestas (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    fuente    TEXT NOT NULL REFERENCES fuentes_datos(clave) ON DELETE CASCADE,
    inicio    TEXT NOT NULL,
    fin       TEXT,
    estado    TEXT NOT NULL,
    registros INTEGER NOT NULL DEFAULT 0,
    mensaje   TEXT
);

CREATE TABLE IF NOT EXISTS indicadores (
    clave   TEXT NOT NULL,
    periodo TEXT NOT NULL,
    valor   REAL NOT NULL,
    fuente  TEXT NOT NULL,
    PRIMARY KEY (clave, periodo)
);

CREATE TABLE IF NOT EXISTS denuncias_distrito (
    ubigeo    TEXT NOT NULL,
    distrito  TEXT NOT NULL,
    anio      INTEGER NOT NULL,
    mes       INTEGER NOT NULL,
    modalidad TEXT NOT NULL,
    cantidad  INTEGER NOT NULL,
    PRIMARY KEY (ubigeo, anio, mes, modalidad)
);

CREATE TABLE IF NOT EXISTS ciberdelitos (
    anio             INTEGER NOT NULL,
    distrito_fiscal  TEXT NOT NULL,
    delito           TEXT NOT NULL,
    cantidad         INTEGER NOT NULL,
    PRIMARY KEY (anio, distrito_fiscal, delito)
);

CREATE TABLE IF NOT EXISTS geocache (
    consulta  TEXT PRIMARY KEY,
    lat       REAL,
    lon       REAL,
    nombre    TEXT,
    creado_en TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

-- Contenido y trazabilidad
CREATE TABLE IF NOT EXISTS blog_posts (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    slug      TEXT NOT NULL UNIQUE,
    titulo    TEXT NOT NULL,
    resumen   TEXT NOT NULL,
    contenido TEXT NOT NULL,
    creado_en TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS contactos (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre    TEXT NOT NULL,
    email     TEXT NOT NULL,
    mensaje   TEXT NOT NULL,
    atendido  INTEGER NOT NULL DEFAULT 0,
    creado_en TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS auditoria (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    accion     TEXT NOT NULL,
    entidad    TEXT NOT NULL,
    entidad_id INTEGER,
    detalle    TEXT,
    creado_en  TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE VIEW IF NOT EXISTS v_inmuebles AS
SELECT i.*, d.nombre AS distrito, u.nombre AS arrendador, u.verificado AS arrendador_verificado,
       (SELECT archivo FROM imagenes g WHERE g.inmueble_id = i.id ORDER BY g.id LIMIT 1) AS portada,
       (SELECT COUNT(*) FROM resenas r WHERE r.inmueble_id = i.id AND r.verificada = 1) AS resenas_verificadas,
       (SELECT ROUND(AVG(r.puntaje),1) FROM resenas r WHERE r.inmueble_id = i.id) AS puntaje_medio
FROM inmuebles i
JOIN distritos d ON d.ubigeo = i.ubigeo
JOIN usuarios u ON u.id = i.arrendador_id;
