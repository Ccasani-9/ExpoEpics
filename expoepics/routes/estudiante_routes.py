import bcrypt
import os
import uuid
from datetime import date
from flask import Blueprint, render_template, request, session, redirect, url_for, flash, current_app
from auth import role_required
from database import query

ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg'}
MAX_FILE_BYTES = 5 * 1024 * 1024  # 5 MB
MAX_DOCS_PER_PROJECT = 5

def _allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def _save_file(file):
    """Guarda un archivo en disco. Devuelve (ruta_relativa, error)."""
    if not file or file.filename == '':
        return None, None
    if not _allowed_file(file.filename):
        return None, f'"{file.filename}": solo se permiten PDF, PNG o JPG.'
    file.seek(0, 2)
    size = file.tell()
    file.seek(0)
    if size > MAX_FILE_BYTES:
        return None, f'"{file.filename}" supera el límite de 5 MB.'
    ext = file.filename.rsplit('.', 1)[1].lower()
    fname = f"{uuid.uuid4().hex}.{ext}"
    upload_dir = os.path.join(current_app.static_folder, 'uploads', 'proyectos')
    os.makedirs(upload_dir, exist_ok=True)
    file.save(os.path.join(upload_dir, fname))
    return 'uploads/proyectos/' + fname, None

estudiante_bp = Blueprint('estudiante', __name__, url_prefix='/estudiante')


def _get_grupo_y_evento(id_estudiante):
    id_vista = session.get('id_evento_vista')
    if id_vista:
        eg = query(
            "SELECT eg.id_grupo, g.id_evento, g.id_lider, g.estado AS estado_grupo "
            "FROM estudiante_grupo eg JOIN grupo g ON eg.id_grupo=g.id_grupo "
            "WHERE eg.id_estudiante=%s AND g.id_evento=%s LIMIT 1",
            (id_estudiante, id_vista), fetch_one=True)
        if eg:
            evento = query("SELECT * FROM evento WHERE id_evento=%s", (eg['id_evento'],), fetch_one=True)
            return eg, evento
    eg = query(
        "SELECT eg.id_grupo, g.id_evento, g.id_lider, g.estado AS estado_grupo "
        "FROM estudiante_grupo eg JOIN grupo g ON eg.id_grupo=g.id_grupo "
        "WHERE eg.id_estudiante=%s ORDER BY g.id_evento DESC LIMIT 1",
        (id_estudiante,), fetch_one=True)
    if not eg:
        return None, None
    evento = query("SELECT * FROM evento WHERE id_evento=%s", (eg['id_evento'],), fetch_one=True)
    return eg, evento


@estudiante_bp.route('/proyecto')
@role_required('estudiante')
def proyecto():
    id_est = session['role_id']
    eg, evento = _get_grupo_y_evento(id_est)

    if not eg:
        return render_template('estudiante/proyecto.html',
                               proyecto=None, grupo=None, evento=None,
                               integrantes=[], evaluaciones=[],
                               es_lider=False, dias_restantes=None,
                               puede_editar=False, tecnologias=[])

    proy = query(
        "SELECT p.*, c.nombre AS nombre_curso, c.color, "
        "g.id_grupo, g.estado AS estado_grupo, g.id_lider, "
        "e.num_mesa, e.ubicacion "
        "FROM proyecto p JOIN grupo g ON p.id_grupo=g.id_grupo "
        "JOIN curso c ON g.id_curso=c.id_curso "
        "JOIN espacio e ON g.id_espacio=e.id_espacio "
        "WHERE g.id_grupo=%s", (eg['id_grupo'],), fetch_one=True)

    documentos = []
    if proy:
        documentos = query(
            "SELECT * FROM proyecto_documento WHERE id_proyecto=%s ORDER BY fecha_subida",
            (proy['id_proyecto'],)) or []

    integrantes = query(
        "SELECT per.nombre, per.apellido, est.id_estudiante, "
        "CASE WHEN g.id_lider=est.id_estudiante THEN 1 ELSE 0 END AS es_lider "
        "FROM estudiante_grupo eg2 JOIN estudiante est ON eg2.id_estudiante=est.id_estudiante "
        "JOIN persona per ON est.id_persona=per.id_persona "
        "JOIN grupo g ON eg2.id_grupo=g.id_grupo "
        "WHERE eg2.id_grupo=%s ORDER BY es_lider DESC, per.apellido",
        (eg['id_grupo'],))

    evaluaciones = []
    if proy:
        evaluaciones = query(
            "SELECT ev.calificacion, ev.detalle, ev.aspectos_mejora, ev.fecha_evaluacion, "
            "CONCAT(per.nombre,' ',per.apellido) AS nombre_juez "
            "FROM evaluacion ev JOIN juez j ON ev.id_juez=j.id_juez "
            "JOIN persona per ON j.id_persona=per.id_persona "
            "WHERE ev.id_proyecto=%s AND ev.finalizada=1 ORDER BY ev.fecha_evaluacion DESC",
            (proy['id_proyecto'],))

    es_lider = (eg['id_lider'] == id_est)
    dias_restantes = None
    if evento:
        dias_restantes = (evento['fecha'] - date.today()).days
    puede_editar = es_lider

    tecnologias = [t.strip() for t in (proy['tecnologias_usadas'] or '').split(',') if t.strip()] if proy else []

    return render_template('estudiante/proyecto.html',
                           proyecto=proy, grupo=eg, evento=evento,
                           integrantes=integrantes, evaluaciones=evaluaciones,
                           es_lider=es_lider, dias_restantes=dias_restantes,
                           puede_editar=puede_editar, tecnologias=tecnologias,
                           documentos=documentos)


@estudiante_bp.route('/proyecto/editar', methods=['GET', 'POST'])
@role_required('estudiante')
def editar_proyecto():
    id_est = session['role_id']
    eg, evento = _get_grupo_y_evento(id_est)

    if not eg:
        flash('No tienes un grupo asignado.', 'warning')
        return redirect(url_for('estudiante.proyecto'))

    if eg['id_lider'] != id_est:
        flash('Solo el líder del grupo puede editar el proyecto.', 'danger')
        return redirect(url_for('estudiante.proyecto'))

    dias_restantes = (evento['fecha'] - date.today()).days if evento else None

    proy = query("SELECT * FROM proyecto WHERE id_grupo=%s", (eg['id_grupo'],), fetch_one=True)
    if not proy:
        flash('No hay proyecto registrado para tu grupo.', 'warning')
        return redirect(url_for('estudiante.proyecto'))

    documentos = query(
        "SELECT * FROM proyecto_documento WHERE id_proyecto=%s ORDER BY fecha_subida",
        (proy['id_proyecto'],)) or []

    error = None
    if request.method == 'POST':
        nombre      = request.form.get('nombre', '').strip()
        descripcion = request.form.get('descripcion', '').strip()
        tecnologias = request.form.get('tecnologias_usadas', '').strip()
        desc_tec    = request.form.get('descripcion_tecnologia', '').strip()
        archivos    = request.files.getlist('documentos')

        if not nombre:
            error = 'El nombre del proyecto es obligatorio.'
        else:
            slots_libres = MAX_DOCS_PER_PROJECT - len(documentos)
            nuevos = [f for f in archivos if f and f.filename]
            if nuevos and len(nuevos) > slots_libres:
                error = f'Solo puedes subir {slots_libres} documento(s) más (máximo {MAX_DOCS_PER_PROJECT} en total).'
            else:
                subidos = 0
                for f in nuevos:
                    ruta, err = _save_file(f)
                    if err:
                        error = err
                        break
                    query(
                        "INSERT INTO proyecto_documento (id_proyecto, url_archivo, nombre_original) VALUES (%s,%s,%s)",
                        (proy['id_proyecto'], ruta, f.filename), commit=True)
                    subidos += 1

                if not error:
                    query(
                        "UPDATE proyecto SET nombre=%s, descripcion=%s, tecnologias_usadas=%s, "
                        "descripcion_tecnologia=%s WHERE id_proyecto=%s",
                        (nombre, descripcion, tecnologias, desc_tec, proy['id_proyecto']), commit=True)
                    msg = 'Proyecto actualizado correctamente.'
                    if subidos:
                        msg += f' Se subieron {subidos} documento(s).'
                    flash(msg, 'success')
                    return redirect(url_for('estudiante.proyecto'))

            documentos = query(
                "SELECT * FROM proyecto_documento WHERE id_proyecto=%s ORDER BY fecha_subida",
                (proy['id_proyecto'],)) or []

    return render_template('estudiante/proyecto_editar.html',
                           proyecto=proy, documentos=documentos,
                           error=error, dias_restantes=dias_restantes,
                           max_docs=MAX_DOCS_PER_PROJECT)


@estudiante_bp.route('/proyecto/documento/<int:id_doc>/eliminar', methods=['POST'])
@role_required('estudiante')
def eliminar_documento(id_doc):
    id_est = session['role_id']
    eg, _ = _get_grupo_y_evento(id_est)
    if not eg or eg['id_lider'] != id_est:
        flash('No tienes permiso para realizar esta acción.', 'danger')
        return redirect(url_for('estudiante.proyecto'))
    proy = query("SELECT id_proyecto FROM proyecto WHERE id_grupo=%s", (eg['id_grupo'],), fetch_one=True)
    doc = query(
        "SELECT * FROM proyecto_documento WHERE id_documento=%s AND id_proyecto=%s",
        (id_doc, proy['id_proyecto']), fetch_one=True) if proy else None
    if doc:
        ruta_full = os.path.join(current_app.static_folder, doc['url_archivo'])
        if os.path.exists(ruta_full):
            os.remove(ruta_full)
        query("DELETE FROM proyecto_documento WHERE id_documento=%s", (id_doc,), commit=True)
        flash('Documento eliminado.', 'success')
    return redirect(url_for('estudiante.proyecto'))


@estudiante_bp.route('/grupo/agregar-integrante', methods=['POST'])
@role_required('estudiante')
def agregar_integrante():
    id_est = session['role_id']
    eg, evento = _get_grupo_y_evento(id_est)

    if not eg:
        flash('No tienes un grupo asignado.', 'warning')
        return redirect(url_for('estudiante.proyecto'))

    if eg['id_lider'] != id_est:
        flash('Solo el líder puede agregar integrantes.', 'danger')
        return redirect(url_for('estudiante.proyecto'))

    dni      = request.form.get('dni', '').strip()
    nombre   = request.form.get('nombre', '').strip()
    apellido = request.form.get('apellido', '').strip()
    correo   = request.form.get('correo', '').strip().lower()
    ciclo    = request.form.get('ciclo', '').strip()

    if not all([dni, nombre, apellido, correo, ciclo]):
        flash('Todos los campos son obligatorios.', 'danger')
        return redirect(url_for('estudiante.proyecto'))

    if len(dni) != 8 or not dni.isdigit():
        flash('El DNI debe tener exactamente 8 dígitos numéricos.', 'danger')
        return redirect(url_for('estudiante.proyecto'))

    if query("SELECT id_persona FROM persona WHERE dni=%s", (dni,), fetch_one=True):
        flash(f'Ya existe un usuario con DNI {dni}.', 'danger')
        return redirect(url_for('estudiante.proyecto'))

    if query("SELECT id_persona FROM persona WHERE LOWER(correo)=%s", (correo,), fetch_one=True):
        flash(f'El correo {correo} ya está registrado.', 'danger')
        return redirect(url_for('estudiante.proyecto'))

    hashed = bcrypt.hashpw(dni.encode(), bcrypt.gensalt()).decode()
    id_persona = query(
        "INSERT INTO persona (dni, nombre, apellido, correo, contrasena, contrasena_temporal) "
        "VALUES (%s, %s, %s, %s, %s, 1)",
        (dni, nombre, apellido, correo, hashed), commit=True)

    id_estudiante = query(
        "INSERT INTO estudiante (id_persona, ciclo) VALUES (%s, %s)",
        (id_persona, int(ciclo)), commit=True)

    query("INSERT INTO estudiante_grupo (id_estudiante, id_grupo) VALUES (%s, %s)",
          (id_estudiante, eg['id_grupo']), commit=True)

    if evento:
        query("INSERT IGNORE INTO participacion (id_evento, id_estudiante) VALUES (%s, %s)",
              (evento['id_evento'], id_estudiante), commit=True)

    flash(f'✓ {nombre} {apellido} fue agregado al grupo. Contraseña temporal: su DNI ({dni}).', 'success')
    return redirect(url_for('estudiante.proyecto'))


@estudiante_bp.route('/evento')
@role_required('estudiante')
def evento():
    id_est = session['role_id']
    eg, ev = _get_grupo_y_evento(id_est)

    espacio = None
    dias_restantes = None
    if eg and ev:
        espacio = query(
            "SELECT e.* FROM espacio e JOIN grupo g ON e.id_espacio=g.id_espacio "
            "WHERE g.id_grupo=%s", (eg['id_grupo'],), fetch_one=True)
        dias_restantes = (ev['fecha'] - date.today()).days

    return render_template('estudiante/evento.html',
                           evento=ev, espacio=espacio, dias_restantes=dias_restantes)


@estudiante_bp.route('/evaluaciones')
@role_required('estudiante')
def evaluaciones():
    id_est = session['role_id']
    eg, _ = _get_grupo_y_evento(id_est)
    lista = []
    if eg:
        proy = query("SELECT id_proyecto FROM proyecto WHERE id_grupo=%s",
                     (eg['id_grupo'],), fetch_one=True)
        if proy:
            lista = query(
                "SELECT ev.calificacion, ev.detalle, ev.aspectos_mejora, ev.fecha_evaluacion, "
                "CONCAT(per.nombre,' ',per.apellido) AS nombre_juez "
                "FROM evaluacion ev JOIN juez j ON ev.id_juez=j.id_juez "
                "JOIN persona per ON j.id_persona=per.id_persona "
                "WHERE ev.id_proyecto=%s AND ev.finalizada=1 ORDER BY ev.fecha_evaluacion DESC",
                (proy['id_proyecto'],))
    return render_template('estudiante/evaluaciones.html', evaluaciones=lista)


@estudiante_bp.route('/cuenta', methods=['GET', 'POST'])
@role_required('estudiante')
def cuenta():
    error = success = None
    if request.method == 'POST':
        actual    = request.form.get('contrasena_actual', '')
        nueva     = request.form.get('nueva_contrasena', '')
        confirmar = request.form.get('confirmar_contrasena', '')
        persona = query("SELECT contrasena FROM persona WHERE id_persona=%s",
                        (session['id_persona'],), fetch_one=True)
        stored  = persona['contrasena'].encode() if isinstance(persona['contrasena'], str) else persona['contrasena']
        if not bcrypt.checkpw(actual.encode(), stored):
            error = 'La contraseña actual es incorrecta.'
        elif len(nueva) < 6:
            error = 'La nueva contraseña debe tener al menos 6 caracteres.'
        elif nueva != confirmar:
            error = 'Las contraseñas no coinciden.'
        else:
            hashed = bcrypt.hashpw(nueva.encode(), bcrypt.gensalt()).decode()
            query("UPDATE persona SET contrasena=%s WHERE id_persona=%s",
                  (hashed, session['id_persona']), commit=True)
            success = 'Contraseña actualizada correctamente.'
    return render_template('estudiante/cuenta.html', error=error, success=success)
