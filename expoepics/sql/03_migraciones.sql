-- ============================================================
-- ExpoEpics — Script de migraciones incrementales
-- Ejecutar SOLO en bases de datos que ya tienen datos.
-- Para bases de datos nuevas usar 01_crear_tablas.sql.
-- Cada bloque es seguro de correr más de una vez.
-- ============================================================
USE ExpoEpics;

-- ────────────────────────────────────────────────────────────
-- MIGRACIÓN 1: Nueva tabla inscripcion_curso
-- Registra estudiantes directamente en un curso (sin grupo ni evento).
-- Necesaria para el apartado "Registro de Estudiantes" del docente.
-- ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS inscripcion_curso (
  id_inscripcion INT AUTO_INCREMENT PRIMARY KEY,
  id_estudiante  INT NOT NULL,
  id_curso       INT NOT NULL,
  fecha_registro DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uk_est_curso (id_estudiante, id_curso),
  FOREIGN KEY (id_estudiante) REFERENCES estudiante(id_estudiante),
  FOREIGN KEY (id_curso)      REFERENCES curso(id_curso)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ────────────────────────────────────────────────────────────
-- MIGRACIÓN 2: Columnas nombre y color en tabla grupo
-- Permiten que el docente asigne nombre propio y color visual
-- a cada grupo desde el apartado "Organizar Grupos".
-- ────────────────────────────────────────────────────────────

-- Agregar columna 'nombre' solo si no existe
SET @col_nombre = (
  SELECT COUNT(*) FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = 'ExpoEpics'
    AND TABLE_NAME   = 'grupo'
    AND COLUMN_NAME  = 'nombre'
);
SET @sql_nombre = IF(@col_nombre = 0,
  'ALTER TABLE grupo ADD COLUMN nombre VARCHAR(80) NULL',
  'SELECT "columna nombre ya existe" AS info'
);
PREPARE stmt FROM @sql_nombre;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Agregar columna 'color' solo si no existe
SET @col_color = (
  SELECT COUNT(*) FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = 'ExpoEpics'
    AND TABLE_NAME   = 'grupo'
    AND COLUMN_NAME  = 'color'
);
SET @sql_color = IF(@col_color = 0,
  'ALTER TABLE grupo ADD COLUMN color VARCHAR(20) NULL',
  'SELECT "columna color ya existe" AS info'
);
PREPARE stmt FROM @sql_color;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- ────────────────────────────────────────────────────────────
-- MIGRACIÓN 3: Columna area_involucrada en tabla tarea
-- Permite que la secretaria indique qué área es responsable
-- de cada tarea (Marketing, Administración, Admisión, Logística
-- u otro valor libre).
-- ────────────────────────────────────────────────────────────
SET @col_area = (
  SELECT COUNT(*) FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = 'ExpoEpics'
    AND TABLE_NAME   = 'tarea'
    AND COLUMN_NAME  = 'area_involucrada'
);
SET @sql_area = IF(@col_area = 0,
  'ALTER TABLE tarea ADD COLUMN area_involucrada VARCHAR(80) NULL AFTER titulo',
  'SELECT "columna area_involucrada ya existe" AS info'
);
PREPARE stmt FROM @sql_area;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- ────────────────────────────────────────────────────────────
-- MIGRACIÓN 4: Columna edicion en tabla evento
-- Almacena el número de edición del evento (ej. 23.ª edición).
-- Independiente del id_evento (PK autoincremental).
-- ────────────────────────────────────────────────────────────
SET @col_edicion = (
  SELECT COUNT(*) FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = 'ExpoEpics'
    AND TABLE_NAME   = 'evento'
    AND COLUMN_NAME  = 'edicion'
);
SET @sql_edicion = IF(@col_edicion = 0,
  'ALTER TABLE evento ADD COLUMN edicion SMALLINT NULL AFTER id_evento',
  'SELECT "columna edicion ya existe" AS info'
);
PREPARE stmt FROM @sql_edicion;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- ────────────────────────────────────────────────────────────
-- MIGRACIÓN 5: Renombrar evento.ciclo → evento.semestre
-- Un año universitario tiene 2 semestres académicos, no ciclos.
-- ────────────────────────────────────────────────────────────
SET @col_ciclo = (
  SELECT COUNT(*) FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = 'ExpoEpics'
    AND TABLE_NAME   = 'evento'
    AND COLUMN_NAME  = 'ciclo'
);
SET @sql_rename = IF(@col_ciclo > 0,
  'ALTER TABLE evento RENAME COLUMN ciclo TO semestre',
  'SELECT "columna semestre ya existe" AS info'
);
PREPARE stmt FROM @sql_rename;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- ────────────────────────────────────────────────────────────
-- MIGRACIÓN 6: Eliminar id_secretaria de la tabla evento
-- El evento puede ser configurado por cualquier organizador
-- (docente o secretaria), no necesita estar atado a una secretaria específica.
-- ────────────────────────────────────────────────────────────

-- Primero eliminar la FK constraint si existe
SET @fk_ev_sec = (
  SELECT CONSTRAINT_NAME FROM information_schema.KEY_COLUMN_USAGE
  WHERE TABLE_SCHEMA = 'ExpoEpics'
    AND TABLE_NAME   = 'evento'
    AND COLUMN_NAME  = 'id_secretaria'
    AND REFERENCED_TABLE_NAME IS NOT NULL
  LIMIT 1
);
SET @sql_fk = IF(@fk_ev_sec IS NOT NULL,
  CONCAT('ALTER TABLE evento DROP FOREIGN KEY ', @fk_ev_sec),
  'SELECT "FK ya eliminada" AS info'
);
PREPARE stmt FROM @sql_fk;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Luego eliminar la columna si existe
SET @col_ev_sec = (
  SELECT COUNT(*) FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = 'ExpoEpics'
    AND TABLE_NAME   = 'evento'
    AND COLUMN_NAME  = 'id_secretaria'
);
SET @sql_col = IF(@col_ev_sec > 0,
  'ALTER TABLE evento DROP COLUMN id_secretaria',
  'SELECT "columna ya eliminada" AS info'
);
PREPARE stmt FROM @sql_col;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- ────────────────────────────────────────────────────────────
-- MIGRACIÓN 7: Eliminar columna codigo de tabla estudiante
-- El código universitario no aporta valor: el seguimiento entre
-- ediciones se hace con id_estudiante, y la identidad con el DNI.
-- ────────────────────────────────────────────────────────────
SET @col_cod = (
  SELECT COUNT(*) FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = 'ExpoEpics'
    AND TABLE_NAME   = 'estudiante'
    AND COLUMN_NAME  = 'codigo'
);
SET @sql_cod = IF(@col_cod > 0,
  'ALTER TABLE estudiante DROP COLUMN codigo',
  'SELECT "columna codigo ya eliminada" AS info'
);
PREPARE stmt FROM @sql_cod;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- ────────────────────────────────────────────────────────────
-- MIGRACIÓN 8: Columna es_director en tabla docente_expoepics
-- Diferencia al director (Rubén García Farje) de los docentes
-- regulares. Solo el director ve Asistencia y Ajustes ExpoEpics.
-- ────────────────────────────────────────────────────────────
SET @col_dir = (
  SELECT COUNT(*) FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = 'ExpoEpics'
    AND TABLE_NAME   = 'docente_expoepics'
    AND COLUMN_NAME  = 'es_director'
);
SET @sql_dir = IF(@col_dir = 0,
  'ALTER TABLE docente_expoepics ADD COLUMN es_director TINYINT(1) NOT NULL DEFAULT 0',
  'SELECT "columna es_director ya existe" AS info'
);
PREPARE stmt FROM @sql_dir;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Marcar a Rubén García Farje como director (id_docente = 1)
UPDATE docente_expoepics SET es_director = 1 WHERE id_docente = 1;

-- ────────────────────────────────────────────────────────────
-- MIGRACIÓN 9: Columna firma en docente_expoepics
-- Almacena la firma del director como imagen base64 PNG.
-- Se usa en los diplomas de participación.
-- ────────────────────────────────────────────────────────────
SET @col_firma = (
  SELECT COUNT(*) FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = 'ExpoEpics'
    AND TABLE_NAME   = 'docente_expoepics'
    AND COLUMN_NAME  = 'firma'
);
SET @sql_firma = IF(@col_firma = 0,
  'ALTER TABLE docente_expoepics ADD COLUMN firma LONGTEXT NULL',
  'SELECT "columna firma ya existe" AS info'
);
PREPARE stmt FROM @sql_firma;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- ────────────────────────────────────────────────────────────
-- MIGRACIÓN 10: Columna es_activo en tabla evento
-- Marca cuál evento es el activo globalmente. Cuando se crea una
-- nueva ExpoEpics, esta columna se actualiza para que todos los
-- portales apunten al nuevo evento por defecto.
-- ────────────────────────────────────────────────────────────
SET @col_activo = (
  SELECT COUNT(*) FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = 'ExpoEpics'
    AND TABLE_NAME   = 'evento'
    AND COLUMN_NAME  = 'es_activo'
);
SET @sql_activo = IF(@col_activo = 0,
  'ALTER TABLE evento ADD COLUMN es_activo TINYINT(1) NOT NULL DEFAULT 0',
  'SELECT "columna es_activo ya existe" AS info'
);
PREPARE stmt FROM @sql_activo;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Marcar el evento más reciente como activo (solo si ninguno lo está)
UPDATE evento SET es_activo = 1
WHERE id_evento = (SELECT id_evento FROM (SELECT id_evento FROM evento ORDER BY fecha DESC LIMIT 1) t)
  AND NOT EXISTS (SELECT 1 FROM (SELECT id_evento FROM evento WHERE es_activo = 1 LIMIT 1) a);

-- ────────────────────────────────────────────────────────────
-- MIGRACIÓN 11: Columna id_evento en inscripcion_curso
-- Sin este campo los alumnos de ediciones anteriores aparecen
-- en la nueva ExpoEpics automáticamente. Con id_evento cada
-- inscripción queda ligada a una edición específica.
-- ────────────────────────────────────────────────────────────
SET @col_ic_ev = (
  SELECT COUNT(*) FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = 'ExpoEpics'
    AND TABLE_NAME   = 'inscripcion_curso'
    AND COLUMN_NAME  = 'id_evento'
);
SET @sql_ic_ev = IF(@col_ic_ev = 0,
  'ALTER TABLE inscripcion_curso ADD COLUMN id_evento INT NULL AFTER id_curso',
  'SELECT "columna id_evento ya existe en inscripcion_curso" AS info'
);
PREPARE stmt FROM @sql_ic_ev; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- Poblar filas existentes con el evento activo
UPDATE inscripcion_curso
SET id_evento = (SELECT id_evento FROM evento WHERE es_activo = 1 LIMIT 1)
WHERE id_evento IS NULL;

-- Hacer NOT NULL
SET @col_ic_ev2 = (
  SELECT IS_NULLABLE FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = 'ExpoEpics'
    AND TABLE_NAME   = 'inscripcion_curso'
    AND COLUMN_NAME  = 'id_evento'
);
SET @sql_ic_nn = IF(@col_ic_ev2 = 'YES',
  'ALTER TABLE inscripcion_curso MODIFY id_evento INT NOT NULL',
  'SELECT "id_evento ya es NOT NULL" AS info'
);
PREPARE stmt FROM @sql_ic_nn; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- Reemplazar unique constraint (id_estudiante, id_curso) por (id_estudiante, id_curso, id_evento)
SET @idx_old = (
  SELECT COUNT(*) FROM information_schema.STATISTICS
  WHERE TABLE_SCHEMA = 'ExpoEpics'
    AND TABLE_NAME   = 'inscripcion_curso'
    AND INDEX_NAME   = 'uq_est_curso'
);
SET @sql_drop_idx = IF(@idx_old > 0,
  'ALTER TABLE inscripcion_curso DROP INDEX uq_est_curso',
  'SELECT "indice uq_est_curso no existe" AS info'
);
PREPARE stmt FROM @sql_drop_idx; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @idx_new = (
  SELECT COUNT(*) FROM information_schema.STATISTICS
  WHERE TABLE_SCHEMA = 'ExpoEpics'
    AND TABLE_NAME   = 'inscripcion_curso'
    AND INDEX_NAME   = 'uq_est_curso_evento'
);
SET @sql_add_idx = IF(@idx_new = 0,
  'ALTER TABLE inscripcion_curso ADD UNIQUE KEY uq_est_curso_evento (id_estudiante, id_curso, id_evento)',
  'SELECT "indice uq_est_curso_evento ya existe" AS info'
);
PREPARE stmt FROM @sql_add_idx; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- ────────────────────────────────────────────────────────────
-- MIGRACIÓN 11: Sincronizar inscripcion_curso desde estudiante_grupo
-- Inserta en inscripcion_curso los estudiantes que están en un grupo
-- del evento activo pero no tienen fila de inscripción para ese curso.
-- Es seguro correrlo varias veces (INSERT IGNORE).
-- ────────────────────────────────────────────────────────────
INSERT IGNORE INTO inscripcion_curso (id_estudiante, id_curso, id_evento)
SELECT DISTINCT eg.id_estudiante, g.id_curso, g.id_evento
FROM estudiante_grupo eg
JOIN grupo g ON eg.id_grupo = g.id_grupo;

-- ────────────────────────────────────────────────────────────
-- FIN DE MIGRACIONES
-- ────────────────────────────────────────────────────────────
-- Para futuras modificaciones al schema, agregar aquí un nuevo
-- bloque con el mismo patrón: IF NOT EXISTS o verificación con
-- information_schema para que sea seguro correrlo varias veces.
-- ────────────────────────────────────────────────────────────
