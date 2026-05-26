-- ============================================================
-- ExpoEpics — Datos de prueba (referencia, contraseñas en texto plano)
-- IMPORTANTE: Ejecutar seed_passwords.py en lugar de este archivo
--             para que las contraseñas se inserten con hash bcrypt.
-- ============================================================
USE ExpoEpics;

-- PERSONAS (14 usuarios)
INSERT INTO persona (dni, nombre, apellido, correo, contrasena, contrasena_temporal) VALUES
('12345678', 'Rubén',          'García Farje',     'r.garcia@usmp.edu.pe',    'docente123', 0),
('23456789', 'Juan',            'Mendoza Torres',   'j.mendoza@usmp.edu.pe',   'docente123', 0),
('34567890', 'Valdy',           'Huanca Quispe',    'v.huanca@usmp.edu.pe',    'secre123',   0),
('45678901', 'Paul David',      'Anampa Ramirez',   'p.anampa@usmp.edu.pe',    'est123',     1),
('56789012', 'Renzo Gustavo',   'Ccasani Correa',   'r.ccasani@usmp.edu.pe',   'est123',     0),
('67890123', 'Anthony',         'Mondalgo Perez',   'a.mondalgo@usmp.edu.pe',  'est123',     0),
('78901234', 'Jorge Alejandro', 'Ortiz Jo',         'j.ortiz@usmp.edu.pe',     'est123',     0),
('89012345', 'María',           'López Soto',       'm.lopez@usmp.edu.pe',     'est123',     0),
('90123456', 'Carlos',          'Vega Castillo',    'c.vega@usmp.edu.pe',      'juez123',    0),
('01234567', 'Laura',           'Rivas Mendez',     'l.rivas@usmp.edu.pe',     'juez123',    0),
('11223344', 'Ana',              'Torres Flores',    'a.torres@usmp.edu.pe',    'mkt123',     0),
('22334455', 'Luis',             'Castro Paredes',   'l.castro@usmp.edu.pe',    'est123',     0),
('33445566', 'Sofia',            'Rios Gutierrez',   's.rios@usmp.edu.pe',      'est123',     0),
('44556677', 'Diego',            'Meza Huanca',      'd.meza@usmp.edu.pe',      'est123',     0);

-- ROLES
INSERT INTO docente_expoepics (id_persona) VALUES (1), (2);
INSERT INTO secretaria (id_persona) VALUES (3);
INSERT INTO juez (id_persona) VALUES (9), (10);
INSERT INTO encargado_marketing (id_persona, area) VALUES (11, 'Fotografía y Redes Sociales');

INSERT INTO estudiante (id_persona, codigo, ciclo) VALUES
(4,  '2021001', 6),
(5,  '2021002', 6),
(6,  '2021003', 6),
(7,  '2021004', 6),
(8,  '2021005', 5),
(12, '2021006', 5),
(13, '2021007', 5),
(14, '2021008', 5);

-- CURSOS
INSERT INTO curso (nombre, ciclo, color, id_docente) VALUES
('Base de Datos',              6, '#2563eb', 1),
('Prog. Orientada a Objetos',  5, '#16a34a', 2),
('Matemática Discreta',        5, '#d97706', 1);

-- EVENTO Y ESPACIOS
INSERT INTO evento (fecha, hora_inicio, hora_fin, ciclo, anio, id_secretaria) VALUES
('2026-06-15', '09:00:00', '13:00:00', 1, 2026, 1);

INSERT INTO espacio (num_mesa, ubicacion, id_evento) VALUES
(1, 'Patio principal', 1),
(2, 'Patio principal', 1),
(3, 'Auditorio',       1),
(4, 'Auditorio',       1);

-- GRUPOS
INSERT INTO grupo (id_curso, id_evento, id_espacio, estado, id_lider) VALUES
(1, 1, 1, 'Seleccionado', 1),
(2, 1, 2, 'Seleccionado', 5),
(3, 1, 3, 'Seleccionado', 4),
(1, 1, 4, 'Postulado',    3);

-- PROYECTOS
INSERT INTO proyecto (id_grupo, nombre, descripcion, tecnologias_usadas, descripcion_tecnologia, estado, url_documento) VALUES
(1, 'SistemaRiego IoT',
    'Sistema de riego automatizado con sensores IoT para optimizar el uso del agua en cultivos universitarios.',
    'Arduino, MySQL, Python Flask, React',
    'Arduino para sensores de humedad, MySQL para almacenamiento, Flask como API REST y React para el dashboard.',
    'Aprobado', 'https://drive.google.com/file/ejemplo1'),
(2, 'App Delivery Campus',
    'Aplicación móvil para delivery dentro del campus universitario con seguimiento en tiempo real.',
    'Flutter, Firebase, Node.js',
    'Flutter para app móvil, Firebase para datos en tiempo real, Node.js para el backend REST.',
    'En revisión', ''),
(3, 'ChatBot Académico',
    'Asistente virtual inteligente que responde consultas académicas usando procesamiento de lenguaje natural.',
    'Python, OpenAI API, PostgreSQL',
    'Python para el backend, OpenAI API para NLP y PostgreSQL para el historial.',
    'Aprobado', 'https://drive.google.com/file/ejemplo3'),
(4, 'Plataforma de Notas Online',
    'Sistema web para gestión de calificaciones académicas accesible para docentes y estudiantes.',
    'PHP, MySQL, Bootstrap',
    'PHP para el backend, MySQL para datos, Bootstrap para la UI.',
    'Registrado', '');

-- ESTUDIANTE_GRUPO
INSERT INTO estudiante_grupo (id_estudiante, id_grupo) VALUES
(1,1),(2,1),
(5,2),(6,2),
(4,3),(7,3),
(3,4),(8,4);

-- PARTICIPACIÓN
INSERT INTO participacion (id_evento, id_estudiante, asistencia, certificado, recibio_complemento) VALUES
(1, 1, 1, 1, 1),
(1, 2, 1, 1, 0),
(1, 3, 0, 0, 0),
(1, 4, 1, 1, 1),
(1, 5, 1, 1, 1),
(1, 7, 1, 0, 1);

-- EVALUACIONES
INSERT INTO evaluacion (id_proyecto, id_juez, calificacion, detalle, aspectos_mejora, fecha_evaluacion, finalizada) VALUES
(1, 1, 'Excelente',  'Proyecto muy bien desarrollado con implementación IoT impecable.',         'Mejorar documentación del código.',              '2026-06-15', 1),
(3, 1, 'Muy buena',  'El chatbot responde con precisión, NLP bien implementado.',                'Ampliar la base de conocimientos académicos.',    '2026-06-15', 1),
(2, 2, 'Buena',      'App funciona correctamente pero tiene problemas de rendimiento en horas pico.','Optimizar consultas a Firebase y mejorar UI.','2026-06-15', 0);

-- TAREAS DE LA SECRETARIA
INSERT INTO tarea (id_secretaria, id_evento, titulo, descripcion, estado, comentario, fecha_creacion, fecha_limite, fecha_culminacion) VALUES
(1, 1, 'Organizar mesas del patio',     'Distribuir 20 mesas en el patio principal.',           'Completado', 'Listo, 20 mesas organizadas.',          '2026-06-01', '2026-06-10', '2026-06-09'),
(1, 1, 'Coordinar catering',             'Contratar catering para el coffee break.',             'En proceso', 'Pendiente confirmación del proveedor.', '2026-06-01', '2026-06-12', NULL),
(1, 1, 'Instalar banners y señalización','Colocar banners de ExpoEpics en las entradas.',        'Pendiente',  '',                                      '2026-06-02', '2026-06-14', NULL),
(1, 1, 'Enviar invitaciones a jueces',   'Enviar correos de invitación a los jueces.',           'Completado', '5 invitaciones enviadas y confirmadas.', '2026-06-01', '2026-06-08', '2026-06-07'),
(1, 1, 'Preparar certificados',          'Diseñar e imprimir los certificados de participación.','En proceso', 'En proceso de diseño.',                 '2026-06-03', '2026-06-13', NULL),
(1, 1, 'Configurar sistema de sonido',   'Verificar equipos de audio para el evento.',           'Pendiente',  '',                                      '2026-06-04', '2026-06-14', NULL);

-- MARKETING_EVENTO
INSERT INTO marketing_evento (id_marketing, id_evento) VALUES (1, 1);
