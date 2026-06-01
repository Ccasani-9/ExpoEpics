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
-- FIN DE MIGRACIONES
-- ────────────────────────────────────────────────────────────
-- Para futuras modificaciones al schema, agregar aquí un nuevo
-- bloque con el mismo patrón: IF NOT EXISTS o verificación con
-- information_schema para que sea seguro correrlo varias veces.
-- ────────────────────────────────────────────────────────────
