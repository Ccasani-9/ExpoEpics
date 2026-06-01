# ExpoEpics — Documentación de cambios v3.0
> Módulo: **Registro de Estudiantes y Organizar Grupos** — Portal Docente
> Universidad de San Martín de Porres (USMP) — 2026

---

## INSTRUCCIÓN PARA LA IA QUE LEA ESTO

Este documento describe con exactitud todos los cambios realizados al sistema ExpoEpics después de la versión base (documentada en el documento original del proyecto). Lee todo antes de tocar código. Cada tabla nueva, columna nueva, ruta nueva y template nuevo está especificado aquí con su SQL y lógica completa.

---

## 1. RESUMEN DE CAMBIOS

Se agregaron dos grandes funcionalidades al **Portal Docente**:

| Funcionalidad | Descripción |
|---|---|
| **Registro de Estudiantes** | El docente registra manualmente a sus estudiantes con datos personales. Crea sus cuentas en la BD. |
| **Organizar Grupos** | El docente crea grupos con nombre, color y mesa, y asigna estudiantes a ellos mediante drag & drop. |

Estas funcionalidades se acceden desde un nuevo apartado en el sidebar del docente llamado **"Registro de Estudiantes"**, que es una landing page con dos tarjetas de acceso.

---

## 2. CAMBIOS EN LA BASE DE DATOS

### 2.1 Nueva tabla: `inscripcion_curso`

**¿Por qué se creó?**
El schema original no tiene forma de vincular un estudiante directamente a un curso sin pasar por `grupo`, que requiere `id_evento` e `id_espacio` (ambos NOT NULL). Para que el docente pueda registrar estudiantes antes de que exista un evento o mesas asignadas, se necesitaba una tabla intermedia directa entre `estudiante` y `curso`.

```sql
CREATE TABLE IF NOT EXISTS inscripcion_curso (
  id_inscripcion INT AUTO_INCREMENT PRIMARY KEY,
  id_estudiante  INT NOT NULL,
  id_curso       INT NOT NULL,
  fecha_registro DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uk_est_curso (id_estudiante, id_curso),
  FOREIGN KEY (id_estudiante) REFERENCES estudiante(id_estudiante),
  FOREIGN KEY (id_curso)      REFERENCES curso(id_curso)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

**Columnas:**
- `id_inscripcion` — PK autoincremental
- `id_estudiante` — FK a `estudiante.id_estudiante`
- `id_curso` — FK a `curso.id_curso`
- `fecha_registro` — timestamp automático del momento en que el docente registró al estudiante
- `UNIQUE (id_estudiante, id_curso)` — un estudiante no puede estar dos veces en el mismo curso

**Relación en el schema:**
```
docente_expoepics → curso → inscripcion_curso → estudiante → persona
```

**Qué NO hace esta tabla:**
- No reemplaza a `estudiante_grupo` (que vincula estudiantes con grupos del evento)
- No reemplaza a `participacion` (que vincula estudiantes con el evento)
- Eliminar un registro de `inscripcion_curso` NO borra al estudiante ni su cuenta

---

### 2.2 Columnas nuevas en tabla `grupo`

Se agregaron dos columnas **nullable** a la tabla `grupo` existente:

```sql
ALTER TABLE grupo
  ADD COLUMN nombre VARCHAR(80) NULL,
  ADD COLUMN color  VARCHAR(20) NULL;
```

**Columna `nombre VARCHAR(80) NULL`:**
El docente asigna un nombre al grupo al crearlo desde "Organizar Grupos" (ej: "Equipo Alpha", "Grupo A"). En el schema original los grupos no tenían nombre; se identificaban por `id_grupo` o por su mesa.

**Columna `color VARCHAR(20) NULL`:**
El docente elige un color visual para cada grupo desde "Organizar Grupos". Se almacena en formato hexadecimal (ej: `#2563eb`). Cuando es NULL, el backend usa `curso.color` como fallback.

**Por qué NULL y no NOT NULL:**
Los 4 grupos del seed data ya existían antes de este cambio. Al ser nullable, esos registros siguen funcionando sin necesitar migración de datos. El código hace fallback automático cuando son NULL.

**Impacto en código existente:**
- Ninguna ruta anterior selecciona ni escribe `nombre`/`color` de grupo → cero ruptura
- Los INSERT existentes de grupos (sin estas columnas) siguen funcionando, ponen NULL por defecto

---

### 2.3 Archivo de migraciones: `sql/03_migraciones.sql`

Para máquinas que ya tienen la BD con datos y necesitan aplicar solo los cambios nuevos (sin recrear toda la BD), se creó este archivo. Es **seguro de ejecutar múltiples veces** porque:
- `CREATE TABLE IF NOT EXISTS` no falla si ya existe
- Las columnas de `grupo` se agregan solo si no existen (verificado con `information_schema`)

```
sql/
├── 01_crear_tablas.sql    ← schema completo actualizado (para BD nueva)
├── 02_datos_prueba.sql    ← seed data (sin cambios)
└── 03_migraciones.sql     ← solo los cambios nuevos (para BD existente)
```

---

## 3. CAMBIOS EN EL BACKEND — `routes/docente_routes.py`

Se agregaron **9 nuevas rutas** al blueprint `docente_bp`. Las rutas originales no fueron modificadas.

### 3.1 Landing page — Registro de Estudiantes

```python
GET /docente/registro-estudiantes
Función: registro_estudiantes()
```

Renderiza la landing page con las dos tarjetas de acceso. Pasa al template la lista de cursos del docente para mostrar la información de cada tarjeta.

**Query:**
```sql
SELECT id_curso, nombre, ciclo, color FROM curso WHERE id_docente=%s ORDER BY nombre
```

---

### 3.2 Página principal — Ingresar Estudiantes

```python
GET /docente/registro-estudiantes/ingresar?curso=<id>
Función: ingresar_estudiantes()
```

Muestra la lista de estudiantes registrados en el curso seleccionado. Si no se pasa `?curso=`, usa el primer curso del docente. Valida que el curso pertenezca al docente.

**Query principal (lista de estudiantes del curso):**
```sql
SELECT ic.id_inscripcion, p.dni, p.nombre, p.apellido, p.correo,
       es.codigo, es.ciclo, es.id_estudiante
FROM inscripcion_curso ic
JOIN estudiante es ON ic.id_estudiante = es.id_estudiante
JOIN persona p ON es.id_persona = p.id_persona
WHERE ic.id_curso = %s
ORDER BY p.apellido, p.nombre
```

**Variables pasadas al template:**
- `cursos` — lista de todos los cursos del docente (para el selector)
- `curso_actual` — dict con el curso seleccionado
- `estudiantes` — lista de estudiantes registrados en ese curso

---

### 3.3 Agregar estudiante al curso

```python
POST /docente/registro-estudiantes/agregar
Función: agregar_estudiante()
Form data: id_curso, dni, nombre, apellido, correo, codigo, ciclo
```

Lógica completa de registro. Flujo:

```
1. Validar que id_curso pertenece al docente
2. Validar que todos los campos estén presentes
3. Validar que DNI tenga exactamente 8 dígitos numéricos
4. Verificar que el código universitario no esté duplicado en estudiante
5. Buscar si ya existe en persona (por dni OR correo):
   5a. Si existe → buscar si ya tiene registro en estudiante
       5a.i.  Si tiene estudiante → usar ese id_estudiante
       5a.ii. Si no tiene estudiante → INSERT en estudiante
   5b. Si no existe → INSERT en persona + INSERT en estudiante
       (contraseña temporal = bcrypt(dni), contrasena_temporal = TRUE)
6. Verificar si ya está en inscripcion_curso para ese curso
7. Si no está → INSERT en inscripcion_curso
8. Redirect con flash de éxito o advertencia
```

**Contraseña temporal:** se genera como `bcrypt.hashpw(dni.encode(), bcrypt.gensalt())`. El estudiante al hacer login verá que `contrasena_temporal = TRUE` y será redirigido a `/cambiar-pass` antes de poder entrar.

---

### 3.4 Eliminar estudiante del curso

```python
POST /docente/registro-estudiantes/eliminar/<id_inscripcion>
Función: eliminar_estudiante()
```

Elimina solo la fila de `inscripcion_curso`. **No elimina** el registro de `persona` ni de `estudiante`. El usuario mantiene su cuenta. Valida que la inscripción pertenezca a un curso del docente autenticado.

---

### 3.5 Página Organizar Grupos

```python
GET /docente/organizar-grupos?curso=<id>
Función: organizar_grupos()
```

Renderiza la página de organización. Misma lógica de selector de curso que `ingresar_estudiantes`. Pasa el evento actual para mostrarlo o mostrar alerta si no hay evento.

---

### 3.6 API — Datos para Organizar Grupos

```python
GET /docente/api/organizar-grupos?curso=<id>
Función: api_organizar_grupos()
Retorna: JSON
```

Endpoint consumido por el JavaScript de la página. Retorna tres colecciones:

**`pool`** — estudiantes registrados en el curso que NO están en ningún grupo del evento actual:
```sql
-- Todos los del curso
SELECT es.id_estudiante, p.nombre, p.apellido
FROM inscripcion_curso ic
JOIN estudiante es ON ic.id_estudiante = es.id_estudiante
JOIN persona p ON es.id_persona = p.id_persona
WHERE ic.id_curso = %s ORDER BY p.apellido, p.nombre

-- Ya asignados a algún grupo
SELECT eg.id_estudiante FROM estudiante_grupo eg
JOIN grupo g ON eg.id_grupo = g.id_grupo
WHERE g.id_curso = %s AND g.id_evento = %s
```
Python hace la diferencia: `pool = todos - asignados`

**`grupos`** — grupos creados para este curso y evento, con sus miembros:
```sql
SELECT g.id_grupo, g.nombre, g.color, e.num_mesa, e.ubicacion, e.id_espacio
FROM grupo g JOIN espacio e ON g.id_espacio = e.id_espacio
WHERE g.id_curso = %s AND g.id_evento = %s ORDER BY g.id_grupo
-- + subquery de miembros por cada grupo
```
Fallback: si `g.nombre IS NULL` → `"Grupo {id}"`. Si `g.color IS NULL` → `curso.color`.

**`espacios`** — mesas libres del evento (no ocupadas por ningún grupo):
```sql
SELECT e.id_espacio, e.num_mesa, e.ubicacion FROM espacio e
WHERE e.id_evento = %s
AND e.id_espacio NOT IN (SELECT id_espacio FROM grupo WHERE id_evento = %s)
ORDER BY e.num_mesa
```

---

### 3.7 Crear grupo

```python
POST /docente/organizar-grupos/crear
Función: crear_grupo()
Body JSON: { id_curso, nombre, color, id_espacio }
Retorna: JSON con el grupo creado
```

Validaciones antes de insertar:
1. El curso pertenece al docente
2. `nombre` y `id_espacio` no están vacíos
3. Existe un evento activo
4. El espacio no está ya tomado por otro grupo en este evento
5. El espacio pertenece al evento activo

```sql
INSERT INTO grupo (id_curso, id_evento, id_espacio, estado, nombre, color)
VALUES (%s, %s, %s, 'Postulado', %s, %s)
```

Retorna el objeto grupo completo (incluyendo `id_grupo` autoincremental) para que el JS lo renderice inmediatamente sin recargar la página.

---

### 3.8 Eliminar grupo

```python
POST /docente/organizar-grupos/eliminar
Función: eliminar_grupo()
Body JSON: { id_grupo }
Retorna: JSON { ok: true, espacio_liberado: {...} }
```

Elimina en cascada en este orden (respetando FK constraints):
```
1. DELETE evaluacion  → proyectos del grupo
2. DELETE proyecto    → del grupo
3. DELETE estudiante_grupo → del grupo
4. DELETE grupo
```

Retorna `espacio_liberado` con `{id_espacio, num_mesa, ubicacion}` para que el JS lo devuelva al dropdown de espacios disponibles sin recargar.

---

### 3.9 Mover estudiante

```python
POST /docente/organizar-grupos/mover
Función: mover_estudiante()
Body JSON: { id_estudiante, id_grupo (nullable), id_curso }
```

Maneja tres casos con la misma lógica:
- Pool → Grupo: quita de ningún grupo, agrega al destino
- Grupo → Otro grupo: quita del grupo actual, agrega al destino
- Grupo → Pool: quita del grupo actual, no agrega a ninguno

```sql
-- Siempre quitar de cualquier grupo del curso+evento
DELETE FROM estudiante_grupo WHERE id_estudiante=%s
AND id_grupo IN (SELECT id_grupo FROM grupo WHERE id_curso=%s AND id_evento=%s)

-- Si hay destino, agregar
INSERT IGNORE INTO estudiante_grupo (id_estudiante, id_grupo) VALUES (%s, %s)
```

Validaciones de seguridad:
- El estudiante debe estar en `inscripcion_curso` para ese curso
- El grupo destino debe pertenecer a un curso del docente autenticado

---

## 4. CAMBIOS EN TEMPLATES

### 4.1 `templates/base.html` — Sidebar

Se agregó un ítem de navegación en el bloque del rol `docente`:

```html
<a href="{{ url_for('docente.registro_estudiantes') }}"
   class="nav-item {% if 'registro' in (request.endpoint or '') or
   'estudiante' in (request.endpoint or '') and 'docente' in (request.endpoint or '') %}active{% endif %}">
  <i class="ti ti-users-plus"></i> Registro de Estudiantes
</a>
```

Aparece entre "Evaluaciones" y "Mi Cuenta". El ícono usado es `ti-users-plus` de Tabler Icons.

---

### 4.2 `templates/docente/registro_estudiantes.html` — NUEVO

Landing page con dos tarjetas de acceso apiladas en columna izquierda + panel informativo derecha.

**Layout:**
```
grid: [columna-acciones (1fr)] [panel-info (300px)]
columna-acciones: flex-column con gap:16px
```

**Tarjeta 1 — Ingresar Estudiantes (azul):**
- Ícono: `ti-user-plus`, fondo azul claro
- Link: `url_for('docente.ingresar_estudiantes')`
- Meta: nombre del curso (si tiene 1) o "N cursos disponibles"
- Hover: borde azul, sombra, translateY(-2px)

**Tarjeta 2 — Organizar Grupos (verde):**
- Ícono: `ti-layout-kanban`, fondo verde claro
- Link: `url_for('docente.organizar_grupos')`
- Meta: "Arrastrar y soltar"
- Hover: borde verde, sombra, translateY(-2px)

**Si el docente no tiene cursos:** ambas tarjetas se muestran deshabilitadas (`.reg-card-disabled`, opacidad 55%, cursor not-allowed).

**Panel informativo derecho:**
- Lista de 5 pasos del flujo
- Lista de cursos del docente con punto de color y badge de ciclo

---

### 4.3 `templates/docente/ingresar_estudiantes.html` — NUEVO

Página de gestión de estudiantes por curso. Dos vistas (toggle) con paginación en tabla.

**Componentes del header:**
- Breadcrumb: `Registro de Estudiantes > Ingresar Estudiantes`
- Selector de curso: aparece solo si el docente tiene 2+ cursos (tabs con color de cada curso)
- Encabezado de sección con nombre del curso, badge de ciclo, conteo y dos botones de acción

**Botón "Eliminar Estudiantes":**
- Alterna un modo de eliminación (`.modo-eliminar` en el grid)
- En tarjetas: aparece una X roja circular en esquina superior derecha de cada tarjeta
- En tabla: aparece el botón "Eliminar" en la columna de acciones de cada fila
- Cuando está activo, el botón cambia a "Cancelar" y su estilo a `.btn-outline`

**Botón "Agregar Estudiante":**
- Abre un modal con formulario de 2 columnas
- Campos: DNI (8 dígitos, input numérico), Código universitario, Nombre(s), Apellido(s), Correo (span 2 columnas), Ciclo (select 1-10, pre-selecciona el ciclo del curso)
- Nota informativa sobre contraseña temporal
- Al enviar: POST a `/docente/registro-estudiantes/agregar`

**Toggle de vistas:**
Dos botones en el encabezado:
- `⊞` → Vista tarjetas (`.view-btn.active`)
- `≡` → Vista tabla

**Vista Tarjetas:**
- Grid responsivo: `repeat(auto-fill, minmax(200px, 1fr))`
- Sin paginación — scroll libre para ver todos los estudiantes
- Cada tarjeta: avatar circular con iniciales (color del curso), nombre, DNI, correo, código, ciclo

**Vista Tabla:**
- Columnas: #, Estudiante (avatar + nombre), DNI, Correo, Código, Ciclo, Acción
- Paginación de 10 en 10 con botones numerados y texto "Mostrando X–Y de Z"
- Paginador con lógica de compresión con `…` para muchas páginas

**Gestión del estado (JavaScript):**
Todos los estudiantes se incrustan en el HTML como JSON dentro de `<script type="application/json">` al cargar la página. El JS pagina en cliente. No hay peticiones adicionales al servidor para cambiar de página o vista.

```json
[{"id":"1","nombre":"Juan","apellido":"García","dni":"12345678",
  "correo":"j.garcia@usmp.pe","codigo":"2024001","ciclo":5,
  "color":"#2563eb","del_url":"/docente/registro-estudiantes/eliminar/1"}]
```

---

### 4.4 `templates/docente/organizar_grupos.html` — NUEVO

Página de organización visual de grupos mediante drag & drop. Toda la interactividad es JavaScript puro (HTML5 Drag and Drop API). El estado se persiste en MySQL mediante llamadas `fetch()` (AJAX).

**Estructura de la página:**
```
[Breadcrumb]
[Selector de curso — solo si tiene 2+ cursos]
[Alerta si no hay evento]
[Barra: nombre curso + badge + resumen + botón "Crear nuevo grupo"]
[Sección Grupos]
  └── Si vacío: estado vacío con mensaje guía
  └── Si hay grupos: .grupos-grid con .grupo-box por cada grupo
[Sección Pool de estudiantes]
  └── Header con título + badge de conteo
  └── .pool-zona (droppable) con .student-chip por cada estudiante
[Modal: Crear nuevo grupo]
```

**Contenedor de grupo (`.grupo-box`):**
- Header con fondo del color del grupo: nombre, mesa, ubicación, conteo de integrantes, botón eliminar (papelera)
- Drop zone (`.grupo-drop-zone`): área droppable, altura mínima 110px
- Si vacío: hint "Arrastra estudiantes aquí" (no droppable por sí mismo, es decorativo dentro de la zona)
- Si tiene miembros: chips de cada estudiante

**Chip de estudiante (`.student-chip`):**
- `draggable="true"`, cursor grab
- Avatar circular 24px con iniciales (color del grupo si está asignado, gris si está en pool)
- Nombre completo
- En hover: borde azul, sombra
- Al arrastrar: clase `.dragging` (opacidad 45%, scale 96%)

**Modal Crear Grupo:**
- Input texto: nombre del grupo
- Swatches de color: 8 colores predefinidos (`#2563eb`, `#16a34a`, `#d97706`, `#dc2626`, `#7c3aed`, `#0891b2`, `#db2777`, `#334155`) + botón de color personalizado (`<input type="color">` invisible detrás de un ícono)
- Preview del color seleccionado (punto + código hex)
- Select de mesa: solo espacios `NOT IN (SELECT id_espacio FROM grupo WHERE id_evento=?)` — las mesas tomadas no aparecen
- Si no hay espacios libres: mensaje de error, select deshabilitado

**Lógica de drag & drop (JavaScript):**

```
onDragStart:
  - Guarda id_estudiante y grupoActual en variables
  - Resalta todas las zonas droppables con outline punteado

onDragOver:
  - e.preventDefault() (necesario para permitir drop)
  - Agrega clase .drag-over a la zona

onDragLeave:
  - Solo remueve .drag-over si realmente salió de la zona
    (verifica con e.relatedTarget && this.contains(e.relatedTarget))

onDrop:
  - Si mismo grupo origen === destino: no hace nada
  - Busca al estudiante en el estado JS (gruposData o poolData)
  - Lo remueve del origen y lo agrega al destino
  - Re-renderiza todo (renderTodo())
  - Hace fetch POST a /docente/organizar-grupos/mover
  - Si fetch falla: recarga datos desde servidor (cargar())
```

**Actualización optimista:**
El DOM se actualiza inmediatamente al soltar el drag, sin esperar la respuesta del servidor. Esto hace la experiencia fluida. Si hay error de red, se recarga desde el servidor para sincronizar.

**Función `renderTodo()`:**
Reconstruye desde cero tanto los grupos como el pool desde el estado JS (`gruposData`, `poolData`). Actualiza también el resumen de texto ("X estudiantes · Y en grupo · Z sin grupo").

**Eliminar grupo:**
1. `confirm()` con nombre del grupo y cantidad de afectados
2. `fetch POST /docente/organizar-grupos/eliminar`
3. En éxito: devuelve miembros al array `poolData`, agrega espacio al array `espaciosLibres`, filtra el grupo de `gruposData`, llama `renderTodo()`

---

## 5. FLUJO COMPLETO DE USO

### Flujo 1: Registrar estudiantes

```
Docente hace login
  → Sidebar: clic en "Registro de Estudiantes"
  → Landing page con dos tarjetas
  → Clic en "Ingresar Estudiantes"
  → Selector de curso (si tiene >1)
  → Página con grid de tarjetas (vacío inicialmente)
  → Clic en "Agregar Estudiante"
  → Modal: completar DNI, nombre, apellido, correo, código, ciclo
  → Submit POST /docente/registro-estudiantes/agregar
  → Flask: crea persona + estudiante + inscripcion_curso en MySQL
  → Redirect con flash "Juan García registrado exitosamente."
  → La página recarga y aparece la tarjeta del nuevo estudiante
  → Repetir para cada estudiante
```

### Flujo 2: Organizar grupos

```
Desde landing page → clic en "Organizar Grupos"
  → Página carga → fetch GET /docente/api/organizar-grupos
  → Se renderizan: pool con todos los estudiantes + grupos existentes
  → Docente hace clic en "Crear nuevo grupo"
    → Modal: escribe nombre, elige color, selecciona mesa disponible
    → fetch POST /docente/organizar-grupos/crear
    → Flask: INSERT en grupo con nombre, color, id_espacio
    → JS: agrega el grupo al estado y re-renderiza
  → Docente arrastra chip de estudiante desde pool al grupo
    → JS: actualiza estado + fetch POST /docente/organizar-grupos/mover
    → Flask: DELETE + INSERT en estudiante_grupo
  → Docente puede arrastrar entre grupos o de vuelta al pool
  → Para eliminar grupo: clic en papelera del header del grupo
    → confirm() → fetch POST /docente/organizar-grupos/eliminar
    → Flask: DELETE cascade evaluacion → proyecto → estudiante_grupo → grupo
    → JS: miembros regresan al pool, espacio queda disponible
```

---

## 6. RUTAS NUEVAS — TABLA RESUMEN

| Método | Ruta | Función | Descripción |
|--------|------|---------|-------------|
| GET | `/docente/registro-estudiantes` | `registro_estudiantes` | Landing page con 2 tarjetas |
| GET | `/docente/registro-estudiantes/ingresar` | `ingresar_estudiantes` | Gestión de estudiantes por curso |
| POST | `/docente/registro-estudiantes/agregar` | `agregar_estudiante` | Crea persona + estudiante + inscripcion |
| POST | `/docente/registro-estudiantes/eliminar/<id>` | `eliminar_estudiante` | Borra solo inscripcion_curso |
| GET | `/docente/organizar-grupos` | `organizar_grupos` | Página drag & drop |
| GET | `/docente/api/organizar-grupos` | `api_organizar_grupos` | JSON: pool + grupos + espacios |
| POST | `/docente/organizar-grupos/crear` | `crear_grupo` | INSERT en grupo |
| POST | `/docente/organizar-grupos/eliminar` | `eliminar_grupo` | DELETE cascade grupo |
| POST | `/docente/organizar-grupos/mover` | `mover_estudiante` | Actualiza estudiante_grupo |

---

## 7. ARCHIVOS CREADOS / MODIFICADOS

| Archivo | Tipo | Cambio |
|---------|------|--------|
| `sql/01_crear_tablas.sql` | Modificado | Agregada tabla `inscripcion_curso` (tabla 18) y columnas `nombre`/`color` a `grupo` |
| `sql/03_migraciones.sql` | **Nuevo** | Script para BD existentes con datos |
| `routes/docente_routes.py` | Modificado | +9 rutas nuevas (líneas 336–693) |
| `templates/base.html` | Modificado | +1 ítem en sidebar del docente |
| `templates/docente/registro_estudiantes.html` | **Nuevo** | Landing page |
| `templates/docente/ingresar_estudiantes.html` | **Nuevo** | Gestión de estudiantes (tarjetas + tabla paginada) |
| `templates/docente/organizar_grupos.html` | **Nuevo** | Drag & drop de grupos |

---

## 8. REGLAS DE NEGOCIO ESPECÍFICAS DE ESTE MÓDULO

1. **El docente solo opera sobre sus propios cursos.** Cada ruta valida `curso.id_docente = session['role_id']` antes de cualquier operación.

2. **Eliminar inscripcion_curso no borra la cuenta.** Solo se borra el vínculo curso-estudiante. La persona y el estudiante siguen en la BD.

3. **Eliminar un grupo borra en cascada.** Si el grupo tiene proyecto con evaluaciones, se borran primero las evaluaciones, luego el proyecto, luego estudiante_grupo, luego el grupo.

4. **Las mesas ya ocupadas no aparecen.** Al crear un grupo, el select de espacios filtra con `NOT IN (SELECT id_espacio FROM grupo WHERE id_evento=?)`.

5. **No todos los estudiantes necesitan estar en un grupo.** Los del pool quedan sin grupo hasta que el docente los asigne.

6. **Un estudiante solo puede estar en un grupo por curso+evento.** Antes de insertar en `estudiante_grupo`, se hace DELETE de cualquier asignación previa del mismo estudiante en el mismo curso+evento.

7. **La contraseña temporal es el DNI con bcrypt.** Al crear la cuenta del estudiante: `bcrypt.hashpw(dni.encode(), bcrypt.gensalt())`, `contrasena_temporal = TRUE`. Al primer login es redirigido a `/cambiar-pass`.

8. **Si no hay evento activo, no se pueden crear grupos.** La página muestra una alerta y el botón "Crear nuevo grupo" no funciona.

---

## 9. INSTRUCCIÓN PARA CONFIGURAR EN MÁQUINA NUEVA

### Caso A — BD vacía (máquina nueva):
```bash
# En MySQL Workbench ejecutar en orden:
sql/01_crear_tablas.sql   # crea las 19 tablas con todo actualizado
sql/02_datos_prueba.sql   # inserta 14 usuarios y datos de prueba
python seed_passwords.py  # aplica bcrypt a las contraseñas
python app.py             # arranca en http://localhost:5000
```

### Caso B — BD existente con datos:
```bash
# En MySQL Workbench ejecutar SOLO:
sql/03_migraciones.sql    # aplica los 2 cambios (tabla nueva + 2 columnas)
# No tocar 01 ni 02
```
