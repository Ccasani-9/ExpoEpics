# ExpoEpics — Sistema de Gestión del Evento Académico
**Universidad de San Martín de Porres (USMP) · Lima, Perú · 2026**

Trabajo final del curso "Teoría de Base de Datos" — Ingeniería de Computación y Sistemas.

---

## Requisitos previos

- Python 3.11+
- MySQL 8.0+ con MySQL Workbench
- pip

---

## Instalación y ejecución

### 1. Crear y activar el entorno virtual

```bash
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Mac / Linux
```

### 2. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 3. Configurar la base de datos

Editar `config.py` con tus credenciales de MySQL:

```python
DB_PASSWORD = 'tu_password_mysql'
```

En **MySQL Workbench**, abrir y ejecutar el script:

```
sql/01_crear_tablas.sql
```

Esto crea la base de datos `expoepics` con las 18 tablas.

### 4. Insertar datos de prueba (con bcrypt)

```bash
python seed_passwords.py
```

Este script aplica bcrypt a todas las contraseñas e inserta todos los datos de demostración.

### 5. Ejecutar el servidor

```bash
python app.py
```

Abrir el navegador en: **http://localhost:5000**

---

## Usuarios de prueba

| Portal | Correo | Contraseña | Notas |
|--------|--------|-----------|-------|
| Docente/Secr. | r.garcia@usmp.edu.pe | docente123 | Docente de Base de Datos |
| Docente/Secr. | j.mendoza@usmp.edu.pe | docente123 | Docente de POO |
| Docente/Secr. | v.huanca@usmp.edu.pe | secre123 | Secretaria |
| Estudiante | r.ccasani@usmp.edu.pe | est123 | Miembro del Grupo 1 |
| Estudiante | m.lopez@usmp.edu.pe | est123 | Líder del Grupo 2 |
| Estudiante | j.ortiz@usmp.edu.pe | est123 | Líder del Grupo 3 |
| Estudiante | p.anampa@usmp.edu.pe | est123 | **Contraseña temporal** (Líder Grupo 1) |
| Juez / Mkt | c.vega@usmp.edu.pe | juez123 | Juez 1 |
| Juez / Mkt | l.rivas@usmp.edu.pe | juez123 | Juez 2 |
| Juez / Mkt | a.torres@usmp.edu.pe | mkt123 | Encargada Marketing |

---

## Estructura del proyecto

```
expoepics/
├── app.py              # Entrada principal
├── config.py           # Configuración BD y clave secreta
├── database.py         # Conexión MySQL + función query()
├── auth.py             # Decoradores login_required, role_required
├── seed_passwords.py   # Inserta datos con contraseñas bcrypt
├── requirements.txt
├── sql/
│   ├── 01_crear_tablas.sql
│   ├── 02_datos_prueba.sql   (referencia, no ejecutar directamente)
│   └── 03_consultas_dashboard.sql
├── routes/             # Blueprints por rol
├── templates/          # Jinja2 HTML
└── static/             # CSS, JS
```

---

## Funcionalidades por rol

- **Docente**: Dashboard con métricas y gráficos, lista de proyectos, cambio de estado, ver evaluaciones de jueces.
- **Secretaria**: Mismo dashboard + gestión completa de tareas (crear, cambiar estado, comentar).
- **Estudiante**: Ver su proyecto y evaluaciones, editar proyecto (solo líder, antes del plazo de 3 días).
- **Juez**: Evaluar proyectos, guardar borradores, finalizar y bloquear evaluaciones.
- **Marketing**: Ranking de proyectos por promedio de calificación, exportar CSV.
