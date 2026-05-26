import json
import bcrypt
from flask import Blueprint, render_template, request, session, redirect, url_for, flash
from auth import role_required
from database import query

docente_bp = Blueprint('docente', __name__, url_prefix='/docente')


def _get_evento():
    return query("SELECT * FROM evento ORDER BY fecha DESC LIMIT 1", fetch_one=True)


def _get_metricas(id_evento):
    participantes = query(
        "SELECT COUNT(*) AS cnt FROM participacion WHERE id_evento=%s",
        (id_evento,), fetch_one=True)['cnt']

    grupos = query(
        "SELECT COUNT(*) AS cnt FROM grupo WHERE id_evento=%s",
        (id_evento,), fetch_one=True)['cnt']

    proyectos = query(
        "SELECT COUNT(*) AS cnt FROM proyecto p JOIN grupo g ON p.id_grupo=g.id_grupo WHERE g.id_evento=%s",
        (id_evento,), fetch_one=True)['cnt']

    pct_tarea_row = query(
        "SELECT ROUND(SUM(CASE WHEN estado='Completado' THEN 1 ELSE 0 END)*100.0/COUNT(*),0) AS pct FROM tarea WHERE id_evento=%s",
        (id_evento,), fetch_one=True)
    pct_tareas = int(pct_tarea_row['pct'] or 0) if pct_tarea_row and pct_tarea_row['pct'] is not None else 0

    pct_inscripcion = round(participantes * 100.0 / max(grupos * 4, 1), 0) if grupos else 0

    return {
        'participantes':   participantes,
        'grupos':          grupos,
        'proyectos':       proyectos,
        'pct_inscripcion': int(pct_inscripcion),
        'pct_tareas':      pct_tareas,
    }


@docente_bp.route('/dashboard')
@role_required('docente')
def dashboard():
    evento = _get_evento()
    if not evento:
        return render_template('docente/dashboard.html',
                               evento=None, metricas={},
                               proyectos_recientes=[], chart_cursos='[]', chart_estados='[]')

    id_evento = evento['id_evento']
    metricas  = _get_metricas(id_evento)

    id_docente = session['role_id']

    chart_cursos = query(
        "SELECT c.nombre, COUNT(p.id_proyecto) AS total, c.color "
        "FROM curso c "
        "LEFT JOIN grupo g ON c.id_curso=g.id_curso AND g.id_evento=%s "
        "LEFT JOIN proyecto p ON g.id_grupo=p.id_grupo "
        "WHERE c.id_docente=%s "
        "GROUP BY c.id_curso, c.nombre, c.color ORDER BY total DESC",
        (id_evento, id_docente))

    chart_estados = query(
        "SELECT p.estado, COUNT(*) AS total "
        "FROM proyecto p JOIN grupo g ON p.id_grupo=g.id_grupo "
        "JOIN curso c ON g.id_curso=c.id_curso "
        "WHERE g.id_evento=%s AND c.id_docente=%s GROUP BY p.estado",
        (id_evento, id_docente))

    proyectos_recientes = query(
        "SELECT p.id_proyecto, p.nombre AS nombre_proyecto, p.estado, "
        "c.nombre AS nombre_curso, g.id_grupo, e.num_mesa "
        "FROM proyecto p JOIN grupo g ON p.id_grupo=g.id_grupo "
        "JOIN curso c ON g.id_curso=c.id_curso "
        "JOIN espacio e ON g.id_espacio=e.id_espacio "
        "WHERE g.id_evento=%s AND c.id_docente=%s ORDER BY p.id_proyecto DESC LIMIT 5",
        (id_evento, id_docente))

    return render_template('docente/dashboard.html',
                           evento=evento,
                           metricas=metricas,
                           proyectos_recientes=proyectos_recientes,
                           chart_cursos=json.dumps(chart_cursos, default=str),
                           chart_estados=json.dumps(chart_estados, default=str))


@docente_bp.route('/proyectos')
@role_required('docente')
def proyectos():
    evento = _get_evento()
    if not evento:
        return render_template('docente/proyectos.html', proyectos=[], evento=None)

    lista = query(
        "SELECT p.id_proyecto, p.nombre AS nombre_proyecto, p.estado AS estado_proyecto, "
        "g.id_grupo, g.estado AS estado_grupo, "
        "c.nombre AS nombre_curso, c.color, "
        "e.num_mesa, e.ubicacion, "
        "COUNT(DISTINCT eg.id_estudiante) AS num_integrantes "
        "FROM proyecto p "
        "JOIN grupo g ON p.id_grupo=g.id_grupo "
        "JOIN curso c ON g.id_curso=c.id_curso "
        "JOIN espacio e ON g.id_espacio=e.id_espacio "
        "LEFT JOIN estudiante_grupo eg ON g.id_grupo=eg.id_grupo "
        "WHERE g.id_evento=%s AND c.id_docente=%s "
        "GROUP BY p.id_proyecto,p.nombre,p.estado,g.id_grupo,g.estado,c.nombre,c.color,e.num_mesa,e.ubicacion "
        "ORDER BY g.id_grupo",
        (evento['id_evento'], session['role_id']))

    return render_template('docente/proyectos.html', proyectos=lista, evento=evento)


@docente_bp.route('/proyecto/<int:id_proyecto>')
@role_required('docente')
def proyecto_detalle(id_proyecto):
    proyecto = query(
        "SELECT p.*, c.nombre AS nombre_curso, c.id_docente, c.color, "
        "g.id_grupo, g.estado AS estado_grupo, g.id_lider, "
        "e.num_mesa, e.ubicacion "
        "FROM proyecto p "
        "JOIN grupo g ON p.id_grupo=g.id_grupo "
        "JOIN curso c ON g.id_curso=c.id_curso "
        "JOIN espacio e ON g.id_espacio=e.id_espacio "
        "WHERE p.id_proyecto=%s",
        (id_proyecto,), fetch_one=True)

    if not proyecto:
        flash('Proyecto no encontrado.', 'danger')
        return redirect(url_for('docente.proyectos'))

    integrantes = query(
        "SELECT per.nombre, per.apellido, est.id_estudiante, est.codigo, "
        "CASE WHEN g.id_lider=est.id_estudiante THEN 1 ELSE 0 END AS es_lider "
        "FROM estudiante_grupo eg "
        "JOIN estudiante est ON eg.id_estudiante=est.id_estudiante "
        "JOIN persona per ON est.id_persona=per.id_persona "
        "JOIN grupo g ON eg.id_grupo=g.id_grupo "
        "WHERE eg.id_grupo=%s ORDER BY es_lider DESC, per.apellido",
        (proyecto['id_grupo'],))

    evaluaciones = query(
        "SELECT ev.id_evaluacion, ev.calificacion, ev.detalle, ev.aspectos_mejora, "
        "ev.fecha_evaluacion, ev.finalizada, "
        "CONCAT(per.nombre,' ',per.apellido) AS nombre_juez "
        "FROM evaluacion ev "
        "JOIN juez j ON ev.id_juez=j.id_juez "
        "JOIN persona per ON j.id_persona=per.id_persona "
        "WHERE ev.id_proyecto=%s ORDER BY ev.fecha_evaluacion DESC",
        (id_proyecto,))

    es_docente_del_curso = (proyecto['id_docente'] == session['role_id'])

    tecnologias = [t.strip() for t in (proyecto['tecnologias_usadas'] or '').split(',') if t.strip()]

    return render_template('docente/proyecto_detalle.html',
                           proyecto=proyecto,
                           integrantes=integrantes,
                           evaluaciones=evaluaciones,
                           es_docente_del_curso=es_docente_del_curso,
                           tecnologias=tecnologias)


@docente_bp.route('/proyecto/<int:id>/estado', methods=['POST'])
@role_required('docente')
def cambiar_estado(id):
    proyecto = query(
        "SELECT p.id_proyecto, c.id_docente FROM proyecto p "
        "JOIN grupo g ON p.id_grupo=g.id_grupo "
        "JOIN curso c ON g.id_curso=c.id_curso "
        "WHERE p.id_proyecto=%s",
        (id,), fetch_one=True)

    if not proyecto:
        flash('Proyecto no encontrado.', 'danger')
        return redirect(url_for('docente.proyectos'))

    if proyecto['id_docente'] != session['role_id']:
        flash('Solo el docente del curso puede cambiar este estado.', 'danger')
        return redirect(url_for('docente.proyecto_detalle', id_proyecto=id))

    nuevo_estado = request.form.get('estado')
    if nuevo_estado not in ('En revisión', 'Aprobado', 'Rechazado'):
        flash('Estado no válido.', 'danger')
        return redirect(url_for('docente.proyecto_detalle', id_proyecto=id))

    query("UPDATE proyecto SET estado=%s WHERE id_proyecto=%s", (nuevo_estado, id), commit=True)
    flash(f'Estado actualizado a "{nuevo_estado}".', 'success')
    return redirect(url_for('docente.proyecto_detalle', id_proyecto=id))


@docente_bp.route('/evaluaciones')
@role_required('docente')
def evaluaciones():
    evento = _get_evento()
    lista = []
    if evento:
        lista = query(
            "SELECT ev.id_evaluacion, ev.calificacion, ev.detalle, ev.aspectos_mejora, "
            "ev.fecha_evaluacion, ev.finalizada, "
            "p.nombre AS nombre_proyecto, p.id_proyecto, "
            "c.nombre AS nombre_curso, "
            "CONCAT(per.nombre,' ',per.apellido) AS nombre_juez "
            "FROM evaluacion ev "
            "JOIN proyecto p ON ev.id_proyecto=p.id_proyecto "
            "JOIN grupo g ON p.id_grupo=g.id_grupo "
            "JOIN curso c ON g.id_curso=c.id_curso "
            "JOIN juez j ON ev.id_juez=j.id_juez "
            "JOIN persona per ON j.id_persona=per.id_persona "
            "WHERE g.id_evento=%s ORDER BY ev.fecha_evaluacion DESC, p.nombre",
            (evento['id_evento'],))

    return render_template('docente/evaluaciones.html', evaluaciones=lista, evento=evento)


@docente_bp.route('/cuenta', methods=['GET', 'POST'])
@role_required('docente')
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

    return render_template('docente/cuenta.html', error=error, success=success)
