import bcrypt
from datetime import date
from flask import Blueprint, render_template, request, session, redirect, url_for, flash
from auth import role_required
from database import query

estudiante_bp = Blueprint('estudiante', __name__, url_prefix='/estudiante')


def _get_grupo_y_evento(id_estudiante):
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

    integrantes = query(
        "SELECT per.nombre, per.apellido, est.id_estudiante, est.codigo, "
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
    puede_editar   = False
    if evento:
        hoy = date.today()
        dias_restantes = (evento['fecha'] - hoy).days
        puede_editar   = es_lider and dias_restantes > 3

    tecnologias = [t.strip() for t in (proy['tecnologias_usadas'] if proy else '').split(',') if t.strip()] if proy else []

    return render_template('estudiante/proyecto.html',
                           proyecto=proy, grupo=eg, evento=evento,
                           integrantes=integrantes, evaluaciones=evaluaciones,
                           es_lider=es_lider, dias_restantes=dias_restantes,
                           puede_editar=puede_editar, tecnologias=tecnologias)


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

    hoy = date.today()
    dias_restantes = (evento['fecha'] - hoy).days if evento else 999
    if dias_restantes <= 3:
        flash('El plazo de edición cerró. Faltan menos de 3 días para la ExpoEpics.', 'danger')
        return redirect(url_for('estudiante.proyecto'))

    proy = query("SELECT * FROM proyecto WHERE id_grupo=%s", (eg['id_grupo'],), fetch_one=True)
    if not proy:
        flash('No hay proyecto registrado para tu grupo.', 'warning')
        return redirect(url_for('estudiante.proyecto'))

    error = None
    if request.method == 'POST':
        nombre      = request.form.get('nombre', '').strip()
        descripcion = request.form.get('descripcion', '').strip()
        tecnologias = request.form.get('tecnologias_usadas', '').strip()
        desc_tec    = request.form.get('descripcion_tecnologia', '').strip()
        url_doc     = request.form.get('url_documento', '').strip()
        if not nombre:
            error = 'El nombre del proyecto es obligatorio.'
        else:
            query(
                "UPDATE proyecto SET nombre=%s, descripcion=%s, tecnologias_usadas=%s, "
                "descripcion_tecnologia=%s, url_documento=%s WHERE id_proyecto=%s",
                (nombre, descripcion, tecnologias, desc_tec, url_doc, proy['id_proyecto']), commit=True)
            flash('Proyecto actualizado correctamente.', 'success')
            return redirect(url_for('estudiante.proyecto'))

    return render_template('estudiante/proyecto_editar.html',
                           proyecto=proy, error=error, dias_restantes=dias_restantes)


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
    codigo   = request.form.get('codigo', '').strip()
    ciclo    = request.form.get('ciclo', '').strip()

    if not all([dni, nombre, apellido, correo, codigo, ciclo]):
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

    if query("SELECT id_estudiante FROM estudiante WHERE codigo=%s", (codigo,), fetch_one=True):
        flash(f'El código {codigo} ya está registrado.', 'danger')
        return redirect(url_for('estudiante.proyecto'))

    hashed = bcrypt.hashpw(dni.encode(), bcrypt.gensalt()).decode()
    id_persona = query(
        "INSERT INTO persona (dni, nombre, apellido, correo, contrasena, contrasena_temporal) "
        "VALUES (%s, %s, %s, %s, %s, 1)",
        (dni, nombre, apellido, correo, hashed), commit=True)

    id_estudiante = query(
        "INSERT INTO estudiante (id_persona, codigo, ciclo) VALUES (%s, %s, %s)",
        (id_persona, codigo, int(ciclo)), commit=True)

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
