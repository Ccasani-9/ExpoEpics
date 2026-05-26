-- ============================================================
-- ExpoEpics — Consultas utilizadas en el dashboard
-- ============================================================
USE expoepics;

-- 1. Total de estudiantes inscritos en un evento
SELECT COUNT(*) AS total_participantes
FROM participacion
WHERE id_evento = 1;

-- 2. Total de grupos participantes en un evento
SELECT COUNT(*) AS total_grupos
FROM grupo
WHERE id_evento = 1;

-- 3. Total de proyectos registrados en un evento
SELECT COUNT(*) AS total_proyectos
FROM proyecto p
JOIN grupo g ON p.id_grupo = g.id_grupo
WHERE g.id_evento = 1;

-- 4. Porcentaje de tareas completadas de un evento
SELECT
  ROUND(SUM(CASE WHEN estado = 'Completado' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 0) AS pct_completado
FROM tarea
WHERE id_evento = 1;

-- 5. Proyectos por curso (para gráfico de barras)
SELECT c.nombre AS curso, COUNT(p.id_proyecto) AS total, c.color
FROM curso c
LEFT JOIN grupo g    ON c.id_curso  = g.id_curso  AND g.id_evento = 1
LEFT JOIN proyecto p ON g.id_grupo  = p.id_grupo
GROUP BY c.id_curso, c.nombre, c.color
ORDER BY total DESC;

-- 6. Distribución de estados de proyectos (para gráfico de dona)
SELECT p.estado, COUNT(*) AS total
FROM proyecto p
JOIN grupo g ON p.id_grupo = g.id_grupo
WHERE g.id_evento = 1
GROUP BY p.estado;

-- 7. Últimos 5 proyectos registrados
SELECT
  p.id_proyecto, p.nombre AS nombre_proyecto, p.estado,
  c.nombre AS nombre_curso, g.id_grupo, e.num_mesa
FROM proyecto p
JOIN grupo g  ON p.id_grupo  = g.id_grupo
JOIN curso c  ON g.id_curso  = c.id_curso
JOIN espacio e ON g.id_espacio = e.id_espacio
WHERE g.id_evento = 1
ORDER BY p.id_proyecto DESC
LIMIT 5;

-- 8. Ranking de proyectos por promedio de calificación
SELECT
  p.id_proyecto, p.nombre, p.descripcion,
  c.nombre AS curso,
  g.id_grupo, e.num_mesa, e.ubicacion,
  COUNT(ev.id_evaluacion) AS num_evaluaciones,
  AVG(CASE ev.calificacion
        WHEN 'Excelente' THEN 6 WHEN 'Muy buena' THEN 5
        WHEN 'Buena'     THEN 4 WHEN 'Regular'   THEN 3
        WHEN 'Mala'      THEN 2 WHEN 'Muy mala'  THEN 1
        WHEN 'Revisado'  THEN 0 ELSE NULL END) AS promedio
FROM proyecto p
JOIN grupo g    ON p.id_grupo  = g.id_grupo
JOIN curso c    ON g.id_curso  = c.id_curso
JOIN espacio e  ON g.id_espacio = e.id_espacio
LEFT JOIN evaluacion ev ON p.id_proyecto = ev.id_proyecto
WHERE g.id_evento = 1
GROUP BY p.id_proyecto, p.nombre, p.descripcion, c.nombre, g.id_grupo, e.num_mesa, e.ubicacion
ORDER BY promedio DESC, p.nombre ASC;

-- 9. Integrantes de un grupo
SELECT
  per.nombre, per.apellido, est.id_estudiante, est.codigo,
  CASE WHEN g.id_lider = est.id_estudiante THEN 1 ELSE 0 END AS es_lider
FROM estudiante_grupo eg
JOIN estudiante est ON eg.id_estudiante = est.id_estudiante
JOIN persona    per ON est.id_persona   = per.id_persona
JOIN grupo      g   ON eg.id_grupo      = g.id_grupo
WHERE eg.id_grupo = 1
ORDER BY es_lider DESC, per.apellido;

-- 10. Evaluaciones recibidas por un proyecto
SELECT
  ev.id_evaluacion, ev.calificacion, ev.detalle, ev.aspectos_mejora,
  ev.fecha_evaluacion, ev.finalizada,
  CONCAT(per.nombre, ' ', per.apellido) AS nombre_juez
FROM evaluacion ev
JOIN juez    j   ON ev.id_juez    = j.id_juez
JOIN persona per ON j.id_persona  = per.id_persona
WHERE ev.id_proyecto = 1
ORDER BY ev.fecha_evaluacion DESC;
