import json
import bcrypt
from datetime import date
from flask import Blueprint, render_template, request, session, redirect, url_for, flash, jsonify
from auth import role_required
from database import query

secretaria_bp = Blueprint('secretaria', __name__, url_prefix='/secretaria')


def _get_evento(id_secretaria):
    return query(
        "SELECT * FROM evento WHERE id_secretaria=%s ORDER BY fecha DESC LIMIT 1",
        (id_secretaria,), fetch_one=True)


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
    pct_row = query(
        "SELECT ROUND(SUM(CASE WHEN estado='Completado' THEN 1 ELSE 0 END)*100.0/COUNT(*),0) AS pct FROM tarea WHERE id_evento=%s",
        (id_evento,), fetch_one=True)
    pct_tareas = int(pct_row['pct'] or 0) if pct_row and pct_row['pct'] is not None else 0
    return {
        'participantes':   participantes,
        'grupos':          grupos,
        'proyectos':       proyectos,
        'pct_inscripcion': int(round(participantes * 100.0 / max(grupos * 4, 1), 0)) if grupos else 0,
        'pct_tareas':      pct_tareas,
    }


@secretaria_bp.route('/dashboard')
@role_required('secretaria')
def dashboard():
    evento = _get_evento(session['role_id'])
    if not evento:
        return render_template('secretaria/dashboard.html',
                               evento=None, metricas={},
                               proyectos_recientes=[], tareas_resumen=[],
                               chart_cursos='[]', chart_estados='[]')

    id_evento = evento['id_evento']
    metricas  = _get_metricas(id_evento)

    chart_cursos = query(
        "SELECT c.nombre, COUNT(p.id_proyecto) AS total, c.color "
        "FROM curso c LEFT JOIN grupo g ON c.id_curso=g.id_curso AND g.id_evento=%s "
        "LEFT JOIN proyecto p ON g.id_grupo=p.id_grupo "
        "GROUP BY c.id_curso, c.nombre, c.color ORDER BY total DESC",
        (id_evento,))
    chart_estados = query(
        "SELECT p.estado, COUNT(*) AS total FROM proyecto p "
        "JOIN grupo g ON p.id_grupo=g.id_grupo WHERE g.id_evento=%s GROUP BY p.estado",
        (id_evento,))
    proyectos_recientes = query(
        "SELECT p.id_proyecto, p.nombre AS nombre_proyecto, p.estado, "
        "c.nombre AS nombre_curso, g.id_grupo, e.num_mesa "
        "FROM proyecto p JOIN grupo g ON p.id_grupo=g.id_grupo "
        "JOIN curso c ON g.id_curso=c.id_curso "
        "JOIN espacio e ON g.id_espacio=e.id_espacio "
        "WHERE g.id_evento=%s ORDER BY p.id_proyecto DESC LIMIT 5",
        (id_evento,))
    tareas_resumen = query(
        "SELECT estado, COUNT(*) AS cnt FROM tarea WHERE id_evento=%s GROUP BY estado",
        (id_evento,))

    return render_template('secretaria/dashboard.html',
                           evento=evento, metricas=metricas,
                           proyectos_recientes=proyectos_recientes,
                           tareas_resumen=tareas_resumen,
                           chart_cursos=json.dumps(chart_cursos, default=str),
                           chart_estados=json.dumps(chart_estados, default=str))


@secretaria_bp.route('/api/estudiantes')
@role_required('secretaria')
def api_estudiantes():
    evento = _get_evento(session['role_id'])
    if not evento:
        return jsonify([])
    rows = query(
        "SELECT pe.nombre, pe.apellido, pe.correo, pe.dni, es.codigo, es.ciclo "
        "FROM participacion pa "
        "JOIN estudiante es ON pa.id_estudiante = es.id_estudiante "
        "JOIN persona pe ON es.id_persona = pe.id_persona "
        "WHERE pa.id_evento = %s "
        "ORDER BY pe.apellido, pe.nombre",
        (evento['id_evento'],))
    return jsonify(rows)


@secretaria_bp.route('/api/grupos')
@role_required('secretaria')
def api_grupos():
    evento = _get_evento(session['role_id'])
    if not evento:
        return jsonify([])
    rows = query(
        "SELECT g.id_grupo, c.nombre AS nombre_curso, c.color, e.num_mesa, e.ubicacion, "
        "       p.nombre AS nombre_proyecto, p.estado AS estado_proyecto, "
        "       pe.nombre, pe.apellido, pe.correo, pe.dni, es.codigo, es.ciclo, "
        "       CASE WHEN g.id_lider = es.id_estudiante THEN 1 ELSE 0 END AS es_lider "
        "FROM grupo g "
        "JOIN curso c ON g.id_curso = c.id_curso "
        "JOIN espacio e ON g.id_espacio = e.id_espacio "
        "LEFT JOIN proyecto p ON g.id_grupo = p.id_grupo "
        "JOIN estudiante_grupo eg ON g.id_grupo = eg.id_grupo "
        "JOIN estudiante es ON eg.id_estudiante = es.id_estudiante "
        "JOIN persona pe ON es.id_persona = pe.id_persona "
        "WHERE g.id_evento = %s "
        "ORDER BY g.id_grupo, es_lider DESC, pe.apellido",
        (evento['id_evento'],))
    grupos = {}
    for r in rows:
        gid = r['id_grupo']
        if gid not in grupos:
            grupos[gid] = {
                'id_grupo': gid,
                'nombre_curso': r['nombre_curso'],
                'color': r['color'],
                'num_mesa': r['num_mesa'],
                'ubicacion': r['ubicacion'],
                'nombre_proyecto': r['nombre_proyecto'],
                'estado_proyecto': r['estado_proyecto'],
                'miembros': []
            }
        grupos[gid]['miembros'].append({
            'nombre': r['nombre'],
            'apellido': r['apellido'],
            'correo': r['correo'],
            'dni': r['dni'],
            'codigo': r['codigo'],
            'ciclo': r['ciclo'],
            'es_lider': bool(r['es_lider'])
        })
    return jsonify(list(grupos.values()))


@secretaria_bp.route('/api/proyectos')
@role_required('secretaria')
def api_proyectos():
    evento = _get_evento(session['role_id'])
    if not evento:
        return jsonify([])
    rows = query(
        "SELECT c.id_curso, c.nombre AS nombre_curso, c.color, "
        "       p.id_proyecto, p.nombre AS nombre_proyecto, p.estado, "
        "       p.descripcion, p.tecnologias_usadas, "
        "       g.id_grupo, e.num_mesa, e.ubicacion "
        "FROM proyecto p "
        "JOIN grupo g ON p.id_grupo = g.id_grupo "
        "JOIN curso c ON g.id_curso = c.id_curso "
        "JOIN espacio e ON g.id_espacio = e.id_espacio "
        "WHERE g.id_evento = %s "
        "ORDER BY c.nombre, p.nombre",
        (evento['id_evento'],))
    cursos = {}
    for r in rows:
        cid = r['id_curso']
        if cid not in cursos:
            cursos[cid] = {
                'id_curso': cid,
                'nombre_curso': r['nombre_curso'],
                'color': r['color'],
                'proyectos': []
            }
        cursos[cid]['proyectos'].append({
            'id_proyecto': r['id_proyecto'],
            'nombre_proyecto': r['nombre_proyecto'],
            'estado': r['estado'],
            'descripcion': r['descripcion'],
            'tecnologias_usadas': r['tecnologias_usadas'],
            'num_mesa': r['num_mesa'],
            'ubicacion': r['ubicacion'],
        })
    return jsonify(list(cursos.values()))


@secretaria_bp.route('/tareas')
@role_required('secretaria')
def tareas():
    evento = _get_evento(session['role_id'])
    filtro = request.args.get('estado', 'Todos')
    if not evento:
        return render_template('secretaria/tareas.html', tareas=[], evento=None,
                               filtro=filtro, conteos={})

    id_evento = evento['id_evento']
    sql = ("SELECT * FROM tarea WHERE id_evento=%s AND id_secretaria=%s")
    params = [id_evento, session['role_id']]
    if filtro != 'Todos':
        sql += " AND estado=%s"
        params.append(filtro)
    sql += " ORDER BY FIELD(estado,'En proceso','Pendiente','Completado'), fecha_limite ASC"

    lista  = query(sql, params)
    conteos_raw = query(
        "SELECT estado, COUNT(*) AS cnt FROM tarea WHERE id_evento=%s AND id_secretaria=%s GROUP BY estado",
        (id_evento, session['role_id']))
    conteos = {r['estado']: r['cnt'] for r in conteos_raw}
    conteos.setdefault('Pendiente', 0)
    conteos.setdefault('En proceso', 0)
    conteos.setdefault('Completado', 0)
    conteos['Total'] = sum(conteos.values())

    return render_template('secretaria/tareas.html', tareas=lista, evento=evento,
                           filtro=filtro, conteos=conteos)


@secretaria_bp.route('/tarea/nueva', methods=['GET', 'POST'])
@role_required('secretaria')
def tarea_nueva():
    evento = _get_evento(session['role_id'])
    error  = None
    if not evento:
        flash('No hay un evento activo.', 'warning')
        return redirect(url_for('secretaria.tareas'))

    if request.method == 'POST':
        titulo      = request.form.get('titulo', '').strip()
        descripcion = request.form.get('descripcion', '').strip()
        fecha_limite= request.form.get('fecha_limite', '') or None
        if not titulo:
            error = 'El título es obligatorio.'
        else:
            query(
                "INSERT INTO tarea (id_secretaria,id_evento,titulo,descripcion,estado,comentario,fecha_creacion,fecha_limite) "
                "VALUES(%s,%s,%s,%s,'Pendiente','', CURDATE(),%s)",
                (session['role_id'], evento['id_evento'], titulo, descripcion, fecha_limite), commit=True)
            flash('Tarea creada correctamente.', 'success')
            return redirect(url_for('secretaria.tareas'))

    return render_template('secretaria/tarea_form.html', evento=evento, error=error, tarea=None)


@secretaria_bp.route('/tarea/<int:id_tarea>/estado', methods=['POST'])
@role_required('secretaria')
def cambiar_estado_tarea(id_tarea):
    nuevo = request.form.get('estado')
    if nuevo not in ('Pendiente', 'En proceso', 'Completado'):
        flash('Estado inválido.', 'danger')
        return redirect(url_for('secretaria.tareas'))

    if nuevo == 'Completado':
        query("UPDATE tarea SET estado=%s, fecha_culminacion=CURDATE() WHERE id_tarea=%s AND id_secretaria=%s",
              (nuevo, id_tarea, session['role_id']), commit=True)
    else:
        query("UPDATE tarea SET estado=%s, fecha_culminacion=NULL WHERE id_tarea=%s AND id_secretaria=%s",
              (nuevo, id_tarea, session['role_id']), commit=True)
    return redirect(url_for('secretaria.tareas'))


@secretaria_bp.route('/tarea/<int:id_tarea>/comentario', methods=['POST'])
@role_required('secretaria')
def agregar_comentario(id_tarea):
    comentario = request.form.get('comentario', '').strip()
    query("UPDATE tarea SET comentario=%s WHERE id_tarea=%s AND id_secretaria=%s",
          (comentario, id_tarea, session['role_id']), commit=True)
    return redirect(url_for('secretaria.tareas'))


@secretaria_bp.route('/cuenta', methods=['GET', 'POST'])
@role_required('secretaria')
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
    return render_template('secretaria/cuenta.html', error=error, success=success)
