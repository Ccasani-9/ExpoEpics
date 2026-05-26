-- ============================================================
-- ExpoEpics — Script de creación de base de datos
-- Universidad de San Martín de Porres (USMP) · 2026
-- ============================================================

CREATE DATABASE IF NOT EXISTS ExpoEpics
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE ExpoEpics;

-- 1. PERSONA (entidad base)
CREATE TABLE IF NOT EXISTS persona (
  id_persona        INT AUTO_INCREMENT PRIMARY KEY,
  dni               VARCHAR(8)   UNIQUE NOT NULL,
  nombre            VARCHAR(60)  NOT NULL,
  apellido          VARCHAR(60)  NOT NULL,
  correo            VARCHAR(100) UNIQUE NOT NULL,
  contrasena        VARCHAR(255) NOT NULL,
  contrasena_temporal BOOLEAN    NOT NULL DEFAULT TRUE
);

-- 2. ESTUDIANTE
CREATE TABLE IF NOT EXISTS estudiante (
  id_estudiante INT AUTO_INCREMENT PRIMARY KEY,
  id_persona    INT NOT NULL,
  codigo        VARCHAR(15) UNIQUE NOT NULL,
  ciclo         INT NOT NULL,
  FOREIGN KEY (id_persona) REFERENCES persona(id_persona)
);

-- 3. DOCENTE_EXPOEPICS
CREATE TABLE IF NOT EXISTS docente_expoepics (
  id_docente INT AUTO_INCREMENT PRIMARY KEY,
  id_persona INT NOT NULL,
  FOREIGN KEY (id_persona) REFERENCES persona(id_persona)
);

-- 4. JUEZ
CREATE TABLE IF NOT EXISTS juez (
  id_juez    INT AUTO_INCREMENT PRIMARY KEY,
  id_persona INT NOT NULL,
  FOREIGN KEY (id_persona) REFERENCES persona(id_persona)
);

-- 5. ADMINISTRADOR
CREATE TABLE IF NOT EXISTS administrador (
  id_administrador INT AUTO_INCREMENT PRIMARY KEY,
  id_persona       INT NOT NULL,
  FOREIGN KEY (id_persona) REFERENCES persona(id_persona)
);

-- 6. SECRETARIA
CREATE TABLE IF NOT EXISTS secretaria (
  id_secretaria INT AUTO_INCREMENT PRIMARY KEY,
  id_persona    INT NOT NULL,
  FOREIGN KEY (id_persona) REFERENCES persona(id_persona)
);

-- 7. ENCARGADO_MARKETING
CREATE TABLE IF NOT EXISTS encargado_marketing (
  id_marketing INT AUTO_INCREMENT PRIMARY KEY,
  id_persona   INT NOT NULL,
  area         VARCHAR(50) NOT NULL,
  FOREIGN KEY (id_persona) REFERENCES persona(id_persona)
);

-- 8. CURSO
CREATE TABLE IF NOT EXISTS curso (
  id_curso   INT AUTO_INCREMENT PRIMARY KEY,
  nombre     VARCHAR(80) NOT NULL,
  ciclo      INT NOT NULL,
  color      VARCHAR(20) NOT NULL,
  id_docente INT NOT NULL,
  FOREIGN KEY (id_docente) REFERENCES docente_expoepics(id_docente)
);

-- 9. EVENTO
CREATE TABLE IF NOT EXISTS evento (
  id_evento     INT AUTO_INCREMENT PRIMARY KEY,
  fecha         DATE NOT NULL,
  hora_inicio   TIME NOT NULL,
  hora_fin      TIME NOT NULL,
  ciclo         INT NOT NULL,
  anio          INT NOT NULL,
  id_secretaria INT NOT NULL,
  FOREIGN KEY (id_secretaria) REFERENCES secretaria(id_secretaria)
);

-- 10. ESPACIO
CREATE TABLE IF NOT EXISTS espacio (
  id_espacio INT AUTO_INCREMENT PRIMARY KEY,
  num_mesa   INT NOT NULL,
  ubicacion  VARCHAR(80) NOT NULL,
  id_evento  INT NOT NULL,
  FOREIGN KEY (id_evento) REFERENCES evento(id_evento)
);

-- 11. GRUPO
CREATE TABLE IF NOT EXISTS grupo (
  id_grupo   INT AUTO_INCREMENT PRIMARY KEY,
  id_curso   INT NOT NULL,
  id_evento  INT NOT NULL,
  id_espacio INT NOT NULL,
  estado     VARCHAR(20) NOT NULL,
  id_lider   INT NULL,
  FOREIGN KEY (id_curso)   REFERENCES curso(id_curso),
  FOREIGN KEY (id_evento)  REFERENCES evento(id_evento),
  FOREIGN KEY (id_espacio) REFERENCES espacio(id_espacio),
  FOREIGN KEY (id_lider)   REFERENCES estudiante(id_estudiante),
  CHECK (estado IN ('Postulado','Seleccionado','Presentó','No asistió'))
);

-- 12. PROYECTO
CREATE TABLE IF NOT EXISTS proyecto (
  id_proyecto             INT AUTO_INCREMENT PRIMARY KEY,
  id_grupo                INT NOT NULL,
  nombre                  VARCHAR(100) NOT NULL,
  descripcion             VARCHAR(500),
  tecnologias_usadas      VARCHAR(200),
  descripcion_tecnologia  VARCHAR(500),
  estado                  VARCHAR(20) NOT NULL DEFAULT 'Registrado',
  url_documento           VARCHAR(500),
  FOREIGN KEY (id_grupo) REFERENCES grupo(id_grupo),
  CHECK (estado IN ('Registrado','En revisión','Aprobado','Rechazado','Presentado'))
);

-- 13. PARTICIPACION
CREATE TABLE IF NOT EXISTS participacion (
  id_participacion    INT AUTO_INCREMENT PRIMARY KEY,
  id_evento           INT NOT NULL,
  id_estudiante       INT NOT NULL,
  asistencia          BOOLEAN DEFAULT FALSE,
  certificado         BOOLEAN DEFAULT FALSE,
  recibio_complemento BOOLEAN DEFAULT FALSE,
  UNIQUE KEY uk_evento_estudiante (id_evento, id_estudiante),
  FOREIGN KEY (id_evento)    REFERENCES evento(id_evento),
  FOREIGN KEY (id_estudiante) REFERENCES estudiante(id_estudiante)
);

-- 14. EVALUACION
CREATE TABLE IF NOT EXISTS evaluacion (
  id_evaluacion   INT AUTO_INCREMENT PRIMARY KEY,
  id_proyecto     INT NOT NULL,
  id_juez         INT NOT NULL,
  calificacion    VARCHAR(20) NOT NULL,
  detalle         VARCHAR(500),
  aspectos_mejora VARCHAR(500),
  fecha_evaluacion DATE NOT NULL,
  finalizada      BOOLEAN NOT NULL DEFAULT FALSE,
  FOREIGN KEY (id_proyecto) REFERENCES proyecto(id_proyecto),
  FOREIGN KEY (id_juez)     REFERENCES juez(id_juez),
  CHECK (calificacion IN ('Excelente','Muy buena','Buena','Regular','Mala','Muy mala','Revisado'))
);

-- 15. ESTUDIANTE_GRUPO
CREATE TABLE IF NOT EXISTS estudiante_grupo (
  id_estudiante INT NOT NULL,
  id_grupo      INT NOT NULL,
  PRIMARY KEY (id_estudiante, id_grupo),
  FOREIGN KEY (id_estudiante) REFERENCES estudiante(id_estudiante),
  FOREIGN KEY (id_grupo)      REFERENCES grupo(id_grupo)
);

-- 16. MARKETING_EVENTO
CREATE TABLE IF NOT EXISTS marketing_evento (
  id_marketing INT NOT NULL,
  id_evento    INT NOT NULL,
  PRIMARY KEY (id_marketing, id_evento),
  FOREIGN KEY (id_marketing) REFERENCES encargado_marketing(id_marketing),
  FOREIGN KEY (id_evento)    REFERENCES evento(id_evento)
);

-- 17. ADMINISTRADOR_EVENTO
CREATE TABLE IF NOT EXISTS administrador_evento (
  id_administrador INT NOT NULL,
  id_evento        INT NOT NULL,
  PRIMARY KEY (id_administrador, id_evento),
  FOREIGN KEY (id_administrador) REFERENCES administrador(id_administrador),
  FOREIGN KEY (id_evento)        REFERENCES evento(id_evento)
);

-- 18. TAREA
CREATE TABLE IF NOT EXISTS tarea (
  id_tarea          INT AUTO_INCREMENT PRIMARY KEY,
  id_secretaria     INT NOT NULL,
  id_evento         INT NOT NULL,
  titulo            VARCHAR(120) NOT NULL,
  descripcion       VARCHAR(500),
  estado            VARCHAR(20) NOT NULL DEFAULT 'Pendiente',
  comentario        VARCHAR(500),
  fecha_creacion    DATE NOT NULL,
  fecha_limite      DATE,
  fecha_culminacion DATE NULL,
  FOREIGN KEY (id_secretaria) REFERENCES secretaria(id_secretaria),
  FOREIGN KEY (id_evento)     REFERENCES evento(id_evento),
  CHECK (estado IN ('Pendiente','En proceso','Completado'))
);
