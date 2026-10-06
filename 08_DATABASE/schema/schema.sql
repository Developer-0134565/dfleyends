-- =====================================================================
-- DF-Chronicles :: Esquema de la base de conocimiento
-- Documenta la integración de legends.xml + legends_plus.xml
--
-- CONVENCIONES
--   * Todo id marcado `df_id` es un ID REAL de Dwarf Fortress. Nunca se
--     genera un ID aleatorio. Los registros sin <id> en el XML (p.ej.
--     `rivers`) reciben un `record_id` determinista derivado del contenido
--     y se marcan como DERIVED.
--   * `certainty` IN {FACT, DERIVED, INTERPRETATION, UNKNOWN}
--       FACT           -> valor presente literalmente en el XML
--       DERIVED        -> calculado a partir del XML (índices, hashes)
--       INTERPRETATION -> lectura narrativa; NO se genera en esta fase
--       UNKNOWN        -> no determinado
--   * `source` IN {'legends.xml','legends_plus.xml'} identifica el export.
--   * `source_section` es la etiqueta de sección dentro de ese export.
-- =====================================================================

-- 1. PROCEDENCIA (un registro por export de Legends)
CREATE TABLE source_file (
    id               SERIAL PRIMARY KEY,
    source           TEXT NOT NULL UNIQUE,  -- 'legends.xml'|'legends_plus.xml'
    original_path    TEXT NOT NULL,         -- ruta real verificada en disco
    archived_path    TEXT NOT NULL,         -- 00_SOURCE/original_data/<source>
    sha256           TEXT NOT NULL,
    bytes            BIGINT NOT NULL,
    codificacion     TEXT NOT NULL,         -- autodetectada, no hardcodeada
    metodo_deteccion TEXT,
    bytes_control    JSONB,                 -- p.ej. {"0x10":12,"0x11":12}
    raiz_xml         TEXT,                  -- 'df_world'
    parsea           BOOLEAN,
    readonly         BOOLEAN NOT NULL DEFAULT TRUE
);

-- 2. SECCIONES (inventario de qué contiene cada export)
CREATE TABLE source_section (
    id             SERIAL PRIMARY KEY,
    source         TEXT NOT NULL REFERENCES source_file(source),
    section        TEXT NOT NULL,           -- etiqueta de <df_world>
    n_entradas     INTEGER NOT NULL,
    total_entradas BIGINT,
    UNIQUE (source, section)
);

-- 3. IDENTIDAD
--    Una fila por (source, section, df_id). La misma entidad presente en
--    ambos exports tiene DOS filas: la procedencia se conserva íntegra.
CREATE TABLE entity (
    id                BIGSERIAL PRIMARY KEY,
    record_id         TEXT NOT NULL UNIQUE, -- 'section:df_id' o derivado
    df_id             TEXT,                 -- ID real de DF; NULL si no lo tiene
    kind              TEXT NOT NULL,        -- 'historical_figure','site',...
    source            TEXT NOT NULL REFERENCES source_file(source),
    source_section    TEXT NOT NULL,
    certainty         TEXT NOT NULL CHECK (certainty IN
                        ('FACT','DERIVED','INTERPRETATION','UNKNOWN')),
    en_legends_xml    BOOLEAN,
    en_legends_plus   BOOLEAN,
    UNIQUE (source, source_section, df_id)
);
CREATE INDEX idx_entity_dfid ON entity (kind, df_id);
CREATE INDEX idx_entity_kind ON entity (kind);

-- 4. CAMPOS: un valor por campo, con procedencia y certeza.
--    Permite conservar AMBOS valores cuando hay discrepancia.
CREATE TABLE field_value (
    id              BIGSERIAL PRIMARY KEY,
    record_id       TEXT NOT NULL REFERENCES entity(record_id) ON DELETE CASCADE,
    field           TEXT NOT NULL,          -- ruta punteada: 'structures.name'
    valor           TEXT,
    source          TEXT NOT NULL,
    source_section  TEXT NOT NULL,
    certainty       TEXT NOT NULL CHECK (certainty IN
                      ('FACT','DERIVED','INTERPRETATION','UNKNOWN')),
    conflicto        BOOLEAN NOT NULL DEFAULT FALSE,
    conflicto_tipo   TEXT,                  -- 'conflicto_real'|'notacion_equivalente'
    tambien_en_plus  BOOLEAN,
    UNIQUE (record_id, field, source)
);
CREATE INDEX idx_field_record ON field_value (record_id);
-- 5. GEOGRAFÍA
CREATE TABLE geo_region (
    id         BIGSERIAL PRIMARY KEY,
    record_id  TEXT UNIQUE NOT NULL,
    df_id      TEXT,
    name       TEXT,
    type       TEXT,
    coords     TEXT,
    source     TEXT NOT NULL,
    certainty  TEXT NOT NULL
);

CREATE TABLE geo_landmass (
    id        BIGSERIAL PRIMARY KEY,
    record_id TEXT UNIQUE NOT NULL,
    df_id     TEXT,
    name      TEXT,
    coord_1   INTEGER,
    coord_2   INTEGER,
    source    TEXT NOT NULL,   -- siempre legends_plus.xml
    certainty TEXT NOT NULL
);

CREATE TABLE geo_mountain_peak (
    id        BIGSERIAL PRIMARY KEY,
    record_id TEXT UNIQUE NOT NULL,
    df_id     TEXT,
    name      TEXT,
    height    INTEGER,
    coords    TEXT,
    source    TEXT NOT NULL,
    certainty TEXT NOT NULL
);

-- `rivers` NO tiene <id> en el XML: record_id es DERIVED (hash del contenido).
CREATE TABLE geo_river (
    id        BIGSERIAL PRIMARY KEY,
    record_id TEXT UNIQUE NOT NULL,
    df_id     TEXT,            -- siempre NULL en este export
    name      TEXT,
    path      TEXT,
    end_pos   TEXT,
    source    TEXT NOT NULL,
    certainty TEXT NOT NULL CHECK (certainty = 'DERIVED')
);

-- 6. IDENTIDADES (nombres reales, solo en legends_plus.xml)
CREATE TABLE identity (
    id           BIGSERIAL PRIMARY KEY,
    record_id    TEXT UNIQUE NOT NULL,
    df_id        TEXT,
    name         TEXT,
    histfig_id   TEXT,
    entity_id    TEXT,
    birth_year   INTEGER,
    birth_second TEXT,
    source       TEXT NOT NULL,
    certainty    TEXT NOT NULL
);
CREATE INDEX idx_identity_hf ON identity (histfig_id);

-- 7. EVENTOS
--    Regla CRÍTICA: los ids ausentes en legends.xml NO se materializan.
--    No hay filas inventadas; ver historical_event_relationship.
CREATE TABLE historical_event (
    id             BIGSERIAL PRIMARY KEY,
    record_id      TEXT UNIQUE NOT NULL,
    df_id          TEXT NOT NULL,           -- ID real de DF
    source         TEXT NOT NULL,           -- solo 'legends.xml' aporta filas
    source_section TEXT NOT NULL,
    certainty      TEXT NOT NULL
);
CREATE INDEX idx_event_dfid ON historical_event (df_id);

-- Presencia de cada id de evento en cada export (sin inventar filas).
CREATE TABLE event_presence (
    event_df_id      TEXT PRIMARY KEY,
    en_legends_xml   BOOLEAN NOT NULL,
    en_legends_plus  BOOLEAN NOT NULL
);

CREATE TABLE historical_event_collection (
    id        BIGSERIAL PRIMARY KEY,
    record_id TEXT UNIQUE NOT NULL,
    df_id     TEXT,
    name      TEXT,
    source    TEXT NOT NULL,
    certainty TEXT NOT NULL
);

CREATE TABLE historical_era (
    id         BIGSERIAL PRIMARY KEY,
    record_id  TEXT UNIQUE NOT NULL,
    name       TEXT,
    start_year INTEGER,
    source     TEXT NOT NULL,
    certainty  TEXT NOT NULL
);
-- 8. RELACIONES
--    Representan los 13.192 eventos que legends.xml NO incluye. Sus
--    <event> apuntan a ids que están documentados como AUSENTES en
--    historical_events; por eso event_df_id NO tiene FK de integridad:
--    la referencia es válida pero el evento no se materializa.
CREATE TABLE historical_event_relationship (
    id           BIGSERIAL PRIMARY KEY,
    record_id    TEXT UNIQUE NOT NULL,
    event_df_id  TEXT NOT NULL,
    relationship TEXT,                       -- 'lover','mother',...
    source_hf    TEXT,
    target_hf    TEXT,
    year         TEXT,
    source       TEXT NOT NULL,              -- siempre legends_plus.xml
    source_section TEXT NOT NULL,
    certainty    TEXT NOT NULL
);
CREATE INDEX idx_rel_event  ON historical_event_relationship (event_df_id);
CREATE INDEX idx_rel_source ON historical_event_relationship (source_hf);
CREATE INDEX idx_rel_target ON historical_event_relationship (target_hf);

CREATE TABLE historical_event_relationship_supplement (
    id            BIGSERIAL PRIMARY KEY,
    record_id     TEXT UNIQUE NOT NULL,
    event_df_id   TEXT NOT NULL,
    occasion_type TEXT,
    reason        TEXT,
    site          TEXT,
    source        TEXT NOT NULL,
    source_section TEXT NOT NULL,
    certainty     TEXT NOT NULL
);
CREATE INDEX idx_supp_event ON historical_event_relationship_supplement (event_df_id);

-- 9. ÍNDICE DERIVED: evento -> relaciones -> figuras implicadas.
--    Permite consultar la cadena pedida en el punto 8 del encargo.
CREATE VIEW v_evento_relaciones AS
SELECT r.event_df_id,
       e.df_id            AS evento_presente_en_historical_events,
       r.relationship     AS tipo_relacion,
       r.source_hf        AS figura_origen,
       r.target_hf        AS figura_destino,
       r.year,
       r.source,
       r.source_section
FROM historical_event_relationship r
LEFT JOIN historical_event e ON e.df_id = r.event_df_id;

-- audited_entities: qué entidades aparecen en cada export (trazabilidad)
CREATE VIEW v_entidades_por_fuente AS
SELECT kind, df_id,
       bool_or(en_legends_xml)  AS en_legends_xml,
       bool_or(en_legends_plus) AS en_legends_plus,
       count(*)                 AS filas
FROM entity
GROUP BY kind, df_id;

-- campo en conflicto: ambos valores se conservan en field_value
CREATE VIEW v_campos_en_conflicto AS
SELECT f.record_id, f.field, f.valor, f.source, f.source_section,
       f.conflicto_tipo
FROM field_value f
WHERE f.conflicto;

-- Sólo divergencias REALES (descarta notaciones equivalentes del mismo dato)
CREATE VIEW v_conflictos_reales AS
SELECT f.record_id, f.field, f.valor, f.source
FROM field_value f
WHERE f.conflicto AND f.conflicto_tipo = 'conflicto_real';

-- ---------------------------------------------------------------------
-- 10. REGLAS DE MERGE APLICADAS (documentadas, no aplicadas por el DDL)
-- ---------------------------------------------------------------------
--  a) legends.xml es la fuente PRIMARIA: sus campos nunca se pierden.
--  b) Un valor vacío en legends_plus.xml NUNCA pisa un valor de legends.xml.
--  c) Un valor de legends.xml NUNCA se descarta por no existir en plus.
--  d) Divergencia con ambos valores no vacíos -> se conservan AMBOS en
--     field_value (una fila por source) y se marca conflicto = TRUE.
--     No se elige ningún valor en silencio.
--  e) Los ids ausentes de historical_events no se crean filas de evento;
--     se registran solo como filas de relación, con event_existe = FALSE.
--  f) Todo campo lleva `source` y `source_section` para trazabilidad.
--  g) Registros sin <id> en el XML reciben record_id determinista (DERIVED);
--     nunca un ID aleatorio.
