import json
import bcrypt
from flask import Blueprint, render_template, request, session, redirect, url_for, flash, jsonify
from auth import role_required
from database import query

docente_bp = Blueprint('docente', __name__, url_prefix='/docente')


def _get_evento():
    id_vista = session.get('id_evento_vista')
    if id_vista:
        evt = query("SELECT * FROM evento WHERE id_evento=%s", (id_vista,), fetch_one=True)
        if evt:
            return evt
    return query("SELECT * FROM evento WHERE es_activo=1 LIMIT 1", fetch_one=True)


def _pct_proyectos_subidos(id_evento, id_docente=None):
    """Porcentaje de grupos que ya subieron su proyecto (nombre cambiado del default o descripción cargada)."""
    condicion_subido = (
        "p.id_proyecto IS NOT NULL AND "
        "(p.nombre NOT LIKE 'Proyecto Grupo%%' OR "
        " (p.descripcion IS NOT NULL AND TRIM(p.descripcion) != ''))"
    )
    if id_docente:
        row = query(
            "SELECT COUNT(DISTINCT g.id_grupo) AS total, "
            f"SUM(CASE WHEN {condicion_subido} THEN 1 ELSE 0 END) AS subidos "
            "FROM grupo g JOIN curso c ON g.id_curso=c.id_curso "
            "LEFT JOIN proyecto p ON p.id_grupo=g.id_grupo "
            "WHERE g.id_evento=%s AND c.id_docente=%s",
            (id_evento, id_docente), fetch_one=True)
    else:
        row = query(
            "SELECT COUNT(DISTINCT g.id_grupo) AS total, "
            f"SUM(CASE WHEN {condicion_subido} THEN 1 ELSE 0 END) AS subidos "
            "FROM grupo g LEFT JOIN proyecto p ON p.id_grupo=g.id_grupo "
            "WHERE g.id_evento=%s",
            (id_evento,), fetch_one=True)
    total   = row['total'] or 0
    subidos = int(row['subidos'] or 0)
    return int(round(subidos * 100.0 / total, 0)) if total else 0


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

    return {
        'participantes':        participantes,
        'grupos':               grupos,
        'proyectos':            proyectos,
        'pct_proyectos_global': _pct_proyectos_subidos(id_evento),
        'pct_tareas':           pct_tareas,
    }


@docente_bp.route('/dashboard')
@role_required('docente')
def dashboard():
    evento = _get_evento()
    if not evento:
        return render_template('docente/dashboard.html',
                               evento=None, metricas={},
                               proyectos_recientes=[], chart_cursos='[]', chart_estados='[]')

    id_evento  = evento['id_evento']
    metricas   = _get_metricas(id_evento)
    id_docente = session['role_id']

    # Sobreescribir las 3 métricas con datos filtrados por este docente
    est_docente = query(
        "SELECT COUNT(DISTINCT eg.id_estudiante) AS cnt "
        "FROM estudiante_grupo eg "
        "JOIN grupo g ON eg.id_grupo = g.id_grupo "
        "JOIN curso c ON g.id_curso = c.id_curso "
        "WHERE g.id_evento = %s AND c.id_docente = %s",
        (id_evento, id_docente), fetch_one=True)['cnt']

    grp_docente = query(
        "SELECT COUNT(*) AS cnt FROM grupo g "
        "JOIN curso c ON g.id_curso = c.id_curso "
        "WHERE g.id_evento = %s AND c.id_docente = %s",
        (id_evento, id_docente), fetch_one=True)['cnt']

    proy_docente = query(
        "SELECT COUNT(*) AS cnt FROM proyecto p "
        "JOIN grupo g ON p.id_grupo = g.id_grupo "
        "JOIN curso c ON g.id_curso = c.id_curso "
        "WHERE g.id_evento = %s AND c.id_docente = %s",
        (id_evento, id_docente), fetch_one=True)['cnt']

    # Total de estudiantes registrados en los cursos de este docente (evento actual)
    total_registrados = query(
        "SELECT COUNT(*) AS cnt FROM inscripcion_curso ic "
        "JOIN curso c ON ic.id_curso = c.id_curso "
        "WHERE c.id_docente = %s AND ic.id_evento = %s",
        (id_docente, id_evento), fetch_one=True)['cnt']

    metricas['participantes'] = est_docente
    metricas['grupos']        = grp_docente
    metricas['proyectos']     = proy_docente
    metricas['pct_proyectos'] = _pct_proyectos_subidos(id_evento, id_docente)
    # pct_proyectos_global ya viene de _get_metricas (todos los cursos)

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

    todas_tareas = query(
        "SELECT t.titulo, t.estado, t.descripcion, t.fecha_limite, t.comentario "
        "FROM tarea t WHERE t.id_evento=%s "
        "ORDER BY FIELD(t.estado,'En proceso','Pendiente','Completado'), t.fecha_limite ASC",
        (id_evento,))

    return render_template('docente/dashboard.html',
                           evento=evento,
                           metricas=metricas,
                           proyectos_recientes=proyectos_recientes,
                           todas_tareas=todas_tareas,
                           chart_cursos=json.dumps(chart_cursos, default=str),
                           chart_estados=json.dumps(chart_estados, default=str))


@docente_bp.route('/api/estudiantes')
@role_required('docente')
def api_estudiantes():
    evento = _get_evento()
    if not evento:
        return jsonify([])
    rows = query(
        "SELECT DISTINCT pe.nombre, pe.apellido, pe.correo, pe.dni, es.ciclo "
        "FROM estudiante_grupo eg "
        "JOIN grupo g ON eg.id_grupo = g.id_grupo "
        "JOIN estudiante es ON eg.id_estudiante = es.id_estudiante "
        "JOIN persona pe ON es.id_persona = pe.id_persona "
        "JOIN curso c ON g.id_curso = c.id_curso "
        "WHERE g.id_evento = %s AND c.id_docente = %s "
        "ORDER BY pe.apellido, pe.nombre",
        (evento['id_evento'], session['role_id']))
    return jsonify(rows)


@docente_bp.route('/api/grupos')
@role_required('docente')
def api_grupos():
    evento = _get_evento()
    if not evento:
        return jsonify([])
    rows = query(
        "SELECT g.id_grupo, c.nombre AS nombre_curso, c.color, e.num_mesa, e.ubicacion, "
        "       p.nombre AS nombre_proyecto, p.estado AS estado_proyecto, "
        "       pe.nombre, pe.apellido, pe.correo, pe.dni, es.ciclo, "
        "       CASE WHEN g.id_lider = es.id_estudiante THEN 1 ELSE 0 END AS es_lider "
        "FROM grupo g "
        "JOIN curso c ON g.id_curso = c.id_curso "
        "JOIN espacio e ON g.id_espacio = e.id_espacio "
        "LEFT JOIN proyecto p ON g.id_grupo = p.id_grupo "
        "JOIN estudiante_grupo eg ON g.id_grupo = eg.id_grupo "
        "JOIN estudiante es ON eg.id_estudiante = es.id_estudiante "
        "JOIN persona pe ON es.id_persona = pe.id_persona "
        "WHERE g.id_evento = %s AND c.id_docente = %s "
        "ORDER BY g.id_grupo, es_lider DESC, pe.apellido",
        (evento['id_evento'], session['role_id']))
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
            'ciclo': r['ciclo'],
            'es_lider': bool(r['es_lider'])
        })
    return jsonify(list(grupos.values()))


@docente_bp.route('/api/proyectos')
@role_required('docente')
def api_proyectos():
    evento = _get_evento()
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
        "WHERE g.id_evento = %s AND c.id_docente = %s "
        "ORDER BY c.nombre, p.nombre",
        (evento['id_evento'], session['role_id']))
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


def _grupos_sin_proy_data(id_evento, id_docente=None):
    sql = (
        "SELECT g.id_grupo, g.nombre AS nombre_grupo, c.nombre AS nombre_curso, c.color, "
        "e.num_mesa, e.ubicacion, "
        "per.nombre AS est_nombre, per.apellido AS est_apellido, "
        "CASE WHEN g.id_lider=es.id_estudiante THEN 1 ELSE 0 END AS es_lider "
        "FROM grupo g "
        "JOIN curso c ON g.id_curso=c.id_curso "
        "JOIN espacio e ON g.id_espacio=e.id_espacio "
        "LEFT JOIN proyecto p ON p.id_grupo=g.id_grupo "
        "LEFT JOIN estudiante_grupo eg ON eg.id_grupo=g.id_grupo "
        "LEFT JOIN estudiante es ON eg.id_estudiante=es.id_estudiante "
        "LEFT JOIN persona per ON es.id_persona=per.id_persona "
        "WHERE g.id_evento=%s "
        "AND (p.id_proyecto IS NULL OR "
        "     (p.nombre LIKE 'Proyecto Grupo%%' AND "
        "      (p.descripcion IS NULL OR TRIM(p.descripcion)=''))) "
    )
    params = [id_evento]
    if id_docente:
        sql += "AND c.id_docente=%s "
        params.append(id_docente)
    sql += "ORDER BY c.nombre, g.id_grupo, es_lider DESC, per.apellido"
    rows = query(sql, tuple(params))
    cursos = {}
    for row in rows:
        cn = row['nombre_curso']
        if cn not in cursos:
            cursos[cn] = {'nombre_curso': cn, 'color': row['color'], 'grupos': {}}
        gi = row['id_grupo']
        if gi not in cursos[cn]['grupos']:
            cursos[cn]['grupos'][gi] = {
                'id_grupo': gi, 'nombre': row['nombre_grupo'],
                'num_mesa': row['num_mesa'], 'ubicacion': row['ubicacion'],
                'integrantes': []
            }
        if row['est_nombre']:
            cursos[cn]['grupos'][gi]['integrantes'].append({
                'nombre': row['est_nombre'], 'apellido': row['est_apellido'],
                'es_lider': bool(row['es_lider'])
            })
    return [{'nombre_curso': v['nombre_curso'], 'color': v['color'],
             'grupos': list(v['grupos'].values())} for v in cursos.values()]


@docente_bp.route('/api/grupos-sin-proyecto')
@role_required('docente')
def api_grupos_sin_proyecto():
    evento = _get_evento()
    if not evento:
        return jsonify([])
    return jsonify(_grupos_sin_proy_data(evento['id_evento'], session['role_id']))


@docente_bp.route('/api/grupos-sin-proyecto-global')
@role_required('docente')
def api_grupos_sin_proyecto_global():
    if not session.get('es_director'):
        return jsonify({'error': 'No autorizado'}), 403
    evento = _get_evento()
    if not evento:
        return jsonify([])
    return jsonify(_grupos_sin_proy_data(evento['id_evento']))


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
        "SELECT per.nombre, per.apellido, est.id_estudiante, "
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

    documentos = query(
        "SELECT * FROM proyecto_documento WHERE id_proyecto=%s ORDER BY fecha_subida",
        (id_proyecto,)) or []

    return render_template('docente/proyecto_detalle.html',
                           proyecto=proyecto,
                           integrantes=integrantes,
                           evaluaciones=evaluaciones,
                           es_docente_del_curso=es_docente_del_curso,
                           tecnologias=tecnologias,
                           documentos=documentos)


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
    es_director = bool(session.get('es_director'))
    lista = []
    proyectos_sin_evaluar = []

    if evento:
        _base_ev = (
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
        )
        if es_director:
            lista = query(
                _base_ev + "WHERE g.id_evento=%s ORDER BY ev.fecha_evaluacion DESC, p.nombre",
                (evento['id_evento'],))
        else:
            lista = query(
                _base_ev + "WHERE g.id_evento=%s AND c.id_docente=%s "
                "ORDER BY ev.fecha_evaluacion DESC, p.nombre",
                (evento['id_evento'], session['role_id']))

        _base_sin = (
            "SELECT p.nombre AS nombre_proyecto, p.id_proyecto, c.nombre AS nombre_curso "
            "FROM proyecto p "
            "JOIN grupo g ON p.id_grupo=g.id_grupo "
            "JOIN curso c ON g.id_curso=c.id_curso "
            "WHERE g.id_evento=%s "
            "AND p.id_proyecto NOT IN (SELECT DISTINCT id_proyecto FROM evaluacion) "
            "ORDER BY c.nombre, p.nombre"
        )
        if es_director:
            proyectos_sin_evaluar = query(_base_sin, (evento['id_evento'],)) or []
        else:
            proyectos_sin_evaluar = query(
                _base_sin.replace("WHERE g.id_evento=%s", "WHERE g.id_evento=%s AND c.id_docente=%s"),
                (evento['id_evento'], session['role_id'])) or []

    return render_template('docente/evaluaciones.html',
                           evaluaciones=lista or [],
                           evento=evento,
                           sin_evaluar=len(proyectos_sin_evaluar),
                           proyectos_sin_evaluar=proyectos_sin_evaluar,
                           es_director=es_director)


@docente_bp.route('/organizar-grupos')
@role_required('docente')
def organizar_grupos():
    id_curso = request.args.get('curso', type=int)
    cursos = query(
        "SELECT id_curso, nombre, ciclo, color FROM curso WHERE id_docente=%s ORDER BY nombre",
        (session['role_id'],))
    if not cursos:
        flash('No tienes cursos asignados.', 'warning')
        return redirect(url_for('docente.registro_estudiantes'))
    if not id_curso:
        id_curso = cursos[0]['id_curso']
    curso_actual = next((c for c in cursos if c['id_curso'] == id_curso), None)
    if not curso_actual:
        flash('Curso no válido.', 'danger')
        return redirect(url_for('docente.registro_estudiantes'))
    evento = _get_evento()
    return render_template('docente/organizar_grupos.html',
                           cursos=cursos, curso_actual=curso_actual, evento=evento)


@docente_bp.route('/api/organizar-grupos')
@role_required('docente')
def api_organizar_grupos():
    id_curso = request.args.get('curso', type=int)
    curso = query(
        "SELECT id_curso, color FROM curso WHERE id_curso=%s AND id_docente=%s",
        (id_curso, session['role_id']), fetch_one=True)
    if not curso:
        return jsonify({'error': 'Curso no válido'}), 403
    evento = _get_evento()
    if not evento:
        return jsonify({'pool': [], 'grupos': [], 'espacios': []})
    id_evento = evento['id_evento']

    todos = query(
        "SELECT es.id_estudiante, p.nombre, p.apellido "
        "FROM inscripcion_curso ic "
        "JOIN estudiante es ON ic.id_estudiante = es.id_estudiante "
        "JOIN persona p ON es.id_persona = p.id_persona "
        "WHERE ic.id_curso = %s AND ic.id_evento = %s ORDER BY p.apellido, p.nombre",
        (id_curso, id_evento))

    en_grupo = query(
        "SELECT eg.id_estudiante FROM estudiante_grupo eg "
        "JOIN grupo g ON eg.id_grupo = g.id_grupo "
        "WHERE g.id_curso = %s AND g.id_evento = %s",
        (id_curso, id_evento))
    ids_asignados = {r['id_estudiante'] for r in en_grupo}

    pool = [{'id_estudiante': e['id_estudiante'],
             'nombre': e['nombre'], 'apellido': e['apellido']}
            for e in todos if e['id_estudiante'] not in ids_asignados]

    grupos_rows = query(
        "SELECT g.id_grupo, g.nombre, g.color, g.id_lider, e.num_mesa, e.ubicacion, e.id_espacio "
        "FROM grupo g JOIN espacio e ON g.id_espacio = e.id_espacio "
        "WHERE g.id_curso = %s AND g.id_evento = %s ORDER BY g.id_grupo",
        (id_curso, id_evento))

    grupos = []
    for g in grupos_rows:
        miembros = query(
            "SELECT es.id_estudiante, p.nombre, p.apellido "
            "FROM estudiante_grupo eg "
            "JOIN estudiante es ON eg.id_estudiante = es.id_estudiante "
            "JOIN persona p ON es.id_persona = p.id_persona "
            "WHERE eg.id_grupo = %s ORDER BY p.apellido",
            (g['id_grupo'],))
        grupos.append({
            'id_grupo':   g['id_grupo'],
            'nombre':     g['nombre'] or ('Grupo ' + str(g['id_grupo'])),
            'color':      g['color']  or curso['color'],
            'id_lider':   g['id_lider'],
            'num_mesa':   g['num_mesa'],
            'ubicacion':  g['ubicacion'],
            'id_espacio': g['id_espacio'],
            'miembros':   [{'id_estudiante': m['id_estudiante'],
                            'nombre': m['nombre'], 'apellido': m['apellido'],
                            'es_lider': m['id_estudiante'] == g['id_lider']}
                           for m in miembros]
        })

    espacios = query(
        "SELECT e.id_espacio, e.num_mesa, e.ubicacion FROM espacio e "
        "WHERE e.id_evento = %s "
        "AND e.id_espacio NOT IN (SELECT id_espacio FROM grupo WHERE id_evento = %s) "
        "ORDER BY e.num_mesa",
        (id_evento, id_evento))

    return jsonify({
        'pool':    pool,
        'grupos':  grupos,
        'espacios': [{'id_espacio': e['id_espacio'],
                      'num_mesa':   e['num_mesa'],
                      'ubicacion':  e['ubicacion']} for e in espacios]
    })


@docente_bp.route('/organizar-grupos/crear', methods=['POST'])
@role_required('docente')
def crear_grupo():
    data       = request.get_json()
    id_curso   = data.get('id_curso')
    nombre     = (data.get('nombre') or '').strip()
    color      = data.get('color', '#2563eb')
    id_espacio = data.get('id_espacio')

    curso = query("SELECT id_curso FROM curso WHERE id_curso=%s AND id_docente=%s",
                  (id_curso, session['role_id']), fetch_one=True)
    if not curso:
        return jsonify({'error': 'Curso no válido'}), 403
    if not nombre or not id_espacio:
        return jsonify({'error': 'Nombre y espacio son obligatorios'}), 400

    evento = _get_evento()
    if not evento:
        return jsonify({'error': 'No hay evento activo'}), 400

    tomado = query("SELECT id_grupo FROM grupo WHERE id_espacio=%s AND id_evento=%s",
                   (id_espacio, evento['id_evento']), fetch_one=True)
    if tomado:
        return jsonify({'error': 'Ese espacio ya está ocupado por otro grupo'}), 400

    espacio = query("SELECT id_espacio, num_mesa, ubicacion FROM espacio "
                    "WHERE id_espacio=%s AND id_evento=%s",
                    (id_espacio, evento['id_evento']), fetch_one=True)
    if not espacio:
        return jsonify({'error': 'Espacio no válido'}), 400

    id_grupo = query(
        "INSERT INTO grupo (id_curso, id_evento, id_espacio, estado, nombre, color) "
        "VALUES (%s,%s,%s,'Postulado',%s,%s)",
        (id_curso, evento['id_evento'], id_espacio, nombre, color), commit=True)

    # Crear proyecto vacío para que el líder pueda completarlo desde su portal
    query(
        "INSERT INTO proyecto (id_grupo, nombre, estado) VALUES (%s,%s,'Registrado')",
        (id_grupo, f"Proyecto Grupo {nombre}"), commit=True)

    return jsonify({
        'id_grupo':   id_grupo,
        'nombre':     nombre,
        'color':      color,
        'num_mesa':   espacio['num_mesa'],
        'ubicacion':  espacio['ubicacion'],
        'id_espacio': id_espacio,
        'miembros':   []
    })


@docente_bp.route('/organizar-grupos/eliminar', methods=['POST'])
@role_required('docente')
def eliminar_grupo():
    data     = request.get_json()
    id_grupo = data.get('id_grupo')

    grupo = query(
        "SELECT g.id_grupo, g.id_espacio, e.num_mesa, e.ubicacion "
        "FROM grupo g "
        "JOIN curso c  ON g.id_curso  = c.id_curso "
        "JOIN espacio e ON g.id_espacio = e.id_espacio "
        "WHERE g.id_grupo=%s AND c.id_docente=%s",
        (id_grupo, session['role_id']), fetch_one=True)
    if not grupo:
        return jsonify({'error': 'Grupo no encontrado'}), 404

    query("DELETE FROM evaluacion WHERE id_proyecto IN "
          "(SELECT id_proyecto FROM proyecto WHERE id_grupo=%s)",
          (id_grupo,), commit=True)
    query("DELETE FROM proyecto WHERE id_grupo=%s", (id_grupo,), commit=True)
    query("DELETE FROM estudiante_grupo WHERE id_grupo=%s", (id_grupo,), commit=True)
    query("DELETE FROM grupo WHERE id_grupo=%s", (id_grupo,), commit=True)

    return jsonify({
        'ok': True,
        'espacio_liberado': {
            'id_espacio': grupo['id_espacio'],
            'num_mesa':   grupo['num_mesa'],
            'ubicacion':  grupo['ubicacion']
        }
    })


@docente_bp.route('/organizar-grupos/mover', methods=['POST'])
@role_required('docente')
def mover_estudiante():
    data          = request.get_json()
    id_estudiante = data.get('id_estudiante')
    id_grupo_dest = data.get('id_grupo')
    id_curso      = data.get('id_curso')

    evento = _get_evento()
    if not evento:
        return jsonify({'error': 'No hay evento activo'}), 400

    en_curso = query(
        "SELECT id_inscripcion FROM inscripcion_curso "
        "WHERE id_estudiante=%s AND id_curso=%s AND id_evento=%s",
        (id_estudiante, id_curso, evento['id_evento']), fetch_one=True)
    if not en_curso:
        return jsonify({'error': 'Estudiante no pertenece a este curso'}), 403

    query(
        "DELETE FROM estudiante_grupo WHERE id_estudiante=%s "
        "AND id_grupo IN (SELECT id_grupo FROM grupo WHERE id_curso=%s AND id_evento=%s)",
        (id_estudiante, id_curso, evento['id_evento']), commit=True)

    if id_grupo_dest:
        grupo_valido = query(
            "SELECT g.id_grupo FROM grupo g "
            "JOIN curso c ON g.id_curso = c.id_curso "
            "WHERE g.id_grupo=%s AND c.id_docente=%s AND g.id_evento=%s",
            (id_grupo_dest, session['role_id'], evento['id_evento']), fetch_one=True)
        if not grupo_valido:
            return jsonify({'error': 'Grupo no válido'}), 403
        query("INSERT IGNORE INTO estudiante_grupo (id_estudiante, id_grupo) VALUES (%s,%s)",
              (id_estudiante, id_grupo_dest), commit=True)

    return jsonify({'ok': True})


@docente_bp.route('/organizar-grupos/lider', methods=['POST'])
@role_required('docente')
def asignar_lider():
    data          = request.get_json()
    id_grupo      = data.get('id_grupo')
    id_estudiante = data.get('id_estudiante')  # None = quitar líder

    grupo = query(
        "SELECT g.id_grupo FROM grupo g "
        "JOIN curso c ON g.id_curso = c.id_curso "
        "WHERE g.id_grupo=%s AND c.id_docente=%s",
        (id_grupo, session['role_id']), fetch_one=True)
    if not grupo:
        return jsonify({'error': 'Grupo no válido'}), 403

    if id_estudiante:
        en_grupo = query(
            "SELECT id_estudiante FROM estudiante_grupo "
            "WHERE id_estudiante=%s AND id_grupo=%s",
            (id_estudiante, id_grupo), fetch_one=True)
        if not en_grupo:
            return jsonify({'error': 'El estudiante no pertenece a este grupo'}), 400

    query("UPDATE grupo SET id_lider=%s WHERE id_grupo=%s",
          (id_estudiante, id_grupo), commit=True)
    return jsonify({'ok': True})


@docente_bp.route('/registro-estudiantes')
@role_required('docente')
def registro_estudiantes():
    cursos = query(
        "SELECT id_curso, nombre, ciclo, color FROM curso WHERE id_docente=%s ORDER BY nombre",
        (session['role_id'],))
    return render_template('docente/registro_estudiantes.html', cursos=cursos)


@docente_bp.route('/registro-estudiantes/ingresar')
@role_required('docente')
def ingresar_estudiantes():
    id_curso = request.args.get('curso', type=int)
    cursos = query(
        "SELECT id_curso, nombre, ciclo, color FROM curso WHERE id_docente=%s ORDER BY nombre",
        (session['role_id'],))

    if not cursos:
        flash('No tienes cursos asignados.', 'warning')
        return redirect(url_for('docente.registro_estudiantes'))

    if not id_curso:
        id_curso = cursos[0]['id_curso']

    curso_actual = next((c for c in cursos if c['id_curso'] == id_curso), None)
    if not curso_actual:
        flash('Curso no válido.', 'danger')
        return redirect(url_for('docente.registro_estudiantes'))

    evento = _get_evento()
    id_evento_actual = evento['id_evento'] if evento else None

    estudiantes = query(
        "SELECT ic.id_inscripcion, p.dni, p.nombre, p.apellido, p.correo, "
        "es.ciclo, es.id_estudiante "
        "FROM inscripcion_curso ic "
        "JOIN estudiante es ON ic.id_estudiante = es.id_estudiante "
        "JOIN persona p ON es.id_persona = p.id_persona "
        "WHERE ic.id_curso = %s AND ic.id_evento = %s "
        "ORDER BY p.apellido, p.nombre",
        (id_curso, id_evento_actual))

    return render_template('docente/ingresar_estudiantes.html',
                           cursos=cursos,
                           curso_actual=curso_actual,
                           estudiantes=estudiantes)


@docente_bp.route('/registro-estudiantes/agregar', methods=['POST'])
@role_required('docente')
def agregar_estudiante():
    id_curso = request.form.get('id_curso', type=int)
    dni      = request.form.get('dni', '').strip()
    nombre   = request.form.get('nombre', '').strip()
    apellido = request.form.get('apellido', '').strip()
    correo   = request.form.get('correo', '').strip().lower()
    ciclo    = request.form.get('ciclo', type=int)

    curso = query(
        "SELECT id_curso FROM curso WHERE id_curso=%s AND id_docente=%s",
        (id_curso, session['role_id']), fetch_one=True)
    if not curso:
        flash('Curso no válido.', 'danger')
        return redirect(url_for('docente.registro_estudiantes'))

    if not all([dni, nombre, apellido, correo, ciclo]):
        flash('Todos los campos son obligatorios.', 'danger')
        return redirect(url_for('docente.ingresar_estudiantes', curso=id_curso))

    if len(dni) != 8 or not dni.isdigit():
        flash('El DNI debe tener exactamente 8 dígitos numéricos.', 'danger')
        return redirect(url_for('docente.ingresar_estudiantes', curso=id_curso))

    persona_existente = query(
        "SELECT id_persona FROM persona WHERE dni=%s OR correo=%s",
        (dni, correo), fetch_one=True)

    if persona_existente:
        id_persona = persona_existente['id_persona']
        est_existente = query(
            "SELECT id_estudiante FROM estudiante WHERE id_persona=%s",
            (id_persona,), fetch_one=True)
        if est_existente:
            id_estudiante = est_existente['id_estudiante']
        else:
            query("INSERT INTO estudiante (id_persona, ciclo) VALUES (%s,%s)",
                  (id_persona, ciclo), commit=True)
            est = query("SELECT id_estudiante FROM estudiante WHERE id_persona=%s",
                        (id_persona,), fetch_one=True)
            id_estudiante = est['id_estudiante']
    else:
        temp_pass = bcrypt.hashpw(dni.encode(), bcrypt.gensalt()).decode()
        query(
            "INSERT INTO persona (dni, nombre, apellido, correo, contrasena, contrasena_temporal) "
            "VALUES (%s,%s,%s,%s,%s,%s)",
            (dni, nombre, apellido, correo, temp_pass, True), commit=True)
        persona_nueva = query(
            "SELECT id_persona FROM persona WHERE dni=%s", (dni,), fetch_one=True)
        id_persona = persona_nueva['id_persona']
        query("INSERT INTO estudiante (id_persona, ciclo) VALUES (%s,%s)",
              (id_persona, ciclo), commit=True)
        est = query("SELECT id_estudiante FROM estudiante WHERE id_persona=%s",
                    (id_persona,), fetch_one=True)
        id_estudiante = est['id_estudiante']

    evento = _get_evento()
    if not evento:
        flash('No hay un evento activo.', 'warning')
        return redirect(url_for('docente.ingresar_estudiantes', curso=id_curso))
    id_evento_actual = evento['id_evento']

    ya_inscrito = query(
        "SELECT id_inscripcion FROM inscripcion_curso "
        "WHERE id_estudiante=%s AND id_curso=%s AND id_evento=%s",
        (id_estudiante, id_curso, id_evento_actual), fetch_one=True)

    if ya_inscrito:
        flash('El estudiante ya está registrado en este curso.', 'warning')
    else:
        query("INSERT INTO inscripcion_curso (id_estudiante, id_curso, id_evento) VALUES (%s,%s,%s)",
              (id_estudiante, id_curso, id_evento_actual), commit=True)
        flash(f'{nombre} {apellido} registrado exitosamente.', 'success')

    return redirect(url_for('docente.ingresar_estudiantes', curso=id_curso))


@docente_bp.route('/registro-estudiantes/importar', methods=['POST'])
@role_required('docente')
def importar_estudiantes():
    import openpyxl, io

    id_curso = request.form.get('id_curso', type=int)
    ciclo    = request.form.get('ciclo', type=int)
    archivo  = request.files.get('archivo_excel')

    curso = query(
        "SELECT id_curso FROM curso WHERE id_curso=%s AND id_docente=%s",
        (id_curso, session['role_id']), fetch_one=True)
    if not curso:
        flash('Curso no válido.', 'danger')
        return redirect(url_for('docente.registro_estudiantes'))

    if not archivo or not archivo.filename:
        flash('Debes seleccionar un archivo Excel (.xlsx).', 'danger')
        return redirect(url_for('docente.ingresar_estudiantes', curso=id_curso, modal='importar'))

    if not ciclo or not (1 <= ciclo <= 10):
        flash('Selecciona un ciclo válido (1 al 10).', 'danger')
        return redirect(url_for('docente.ingresar_estudiantes', curso=id_curso, modal='importar'))

    try:
        wb = openpyxl.load_workbook(io.BytesIO(archivo.read()))
        ws = wb.active
    except Exception:
        flash('El archivo no es un Excel válido (.xlsx).', 'danger')
        return redirect(url_for('docente.ingresar_estudiantes', curso=id_curso, modal='importar'))

    importados   = 0
    ya_inscritos = 0
    errores      = []

    for fila, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
        if not any(row):
            continue

        # Columnas: A=DNI  B=APELLIDOS  C=NOMBRES  D=CORREO INSTITUCIONAL
        raw_dni      = row[0]
        raw_apellido = row[1]
        raw_nombre   = row[2]
        raw_correo   = row[3] if len(row) > 3 else None

        if isinstance(raw_dni, float):
            raw_dni = int(raw_dni)
        dni      = str(raw_dni or '').strip().zfill(8) if isinstance(raw_dni, int) else str(raw_dni or '').strip()
        apellido = str(raw_apellido or '').strip().upper()
        nombre   = str(raw_nombre or '').strip().upper()
        correo   = str(raw_correo or '').strip().lower()

        if not all([dni, apellido, nombre, correo]):
            errores.append(f'Fila {fila}: datos incompletos (se requieren DNI, apellidos, nombres y correo).')
            continue

        if len(dni) != 8 or not dni.isdigit():
            errores.append(f'Fila {fila}: DNI "{dni}" inválido (debe tener exactamente 8 dígitos).')
            continue

        try:
            persona_existente = query(
                "SELECT id_persona FROM persona WHERE dni=%s OR correo=%s",
                (dni, correo), fetch_one=True)

            if persona_existente:
                id_persona = persona_existente['id_persona']
                est_existente = query(
                    "SELECT id_estudiante FROM estudiante WHERE id_persona=%s",
                    (id_persona,), fetch_one=True)
                if est_existente:
                    id_estudiante = est_existente['id_estudiante']
                else:
                    query("INSERT INTO estudiante (id_persona, ciclo) VALUES (%s,%s)",
                          (id_persona, ciclo), commit=True)
                    est = query("SELECT id_estudiante FROM estudiante WHERE id_persona=%s",
                                (id_persona,), fetch_one=True)
                    id_estudiante = est['id_estudiante']
            else:
                temp_pass = bcrypt.hashpw(dni.encode(), bcrypt.gensalt()).decode()
                query(
                    "INSERT INTO persona (dni, nombre, apellido, correo, contrasena, contrasena_temporal) "
                    "VALUES (%s,%s,%s,%s,%s,%s)",
                    (dni, nombre, apellido, correo, temp_pass, True), commit=True)
                persona_nueva = query(
                    "SELECT id_persona FROM persona WHERE dni=%s", (dni,), fetch_one=True)
                id_persona = persona_nueva['id_persona']
                query("INSERT INTO estudiante (id_persona, ciclo) VALUES (%s,%s)",
                      (id_persona, ciclo), commit=True)
                est = query("SELECT id_estudiante FROM estudiante WHERE id_persona=%s",
                            (id_persona,), fetch_one=True)
                id_estudiante = est['id_estudiante']

            evento_imp = _get_evento()
            id_evento_imp = evento_imp['id_evento'] if evento_imp else None

            ya_inscrito = query(
                "SELECT id_inscripcion FROM inscripcion_curso "
                "WHERE id_estudiante=%s AND id_curso=%s AND id_evento=%s",
                (id_estudiante, id_curso, id_evento_imp), fetch_one=True)

            if ya_inscrito:
                ya_inscritos += 1
            else:
                query("INSERT INTO inscripcion_curso (id_estudiante, id_curso, id_evento) VALUES (%s,%s,%s)",
                      (id_estudiante, id_curso, id_evento_imp), commit=True)
                importados += 1

        except Exception:
            errores.append(f'Fila {fila} ({apellido}, {nombre}): error inesperado al procesar.')

    partes = []
    if importados:
        s = 's' if importados != 1 else ''
        partes.append(f'{importados} estudiante{s} importado{s}')
    if ya_inscritos:
        partes.append(f'{ya_inscritos} ya estaban inscritos')
    if errores:
        partes.append(f'{len(errores)} fila{"s" if len(errores) != 1 else ""} con error')

    resumen = ', '.join(partes) + '.' if partes else 'No se procesó ningún estudiante.'
    cat = 'success' if importados and not errores else ('warning' if importados else 'danger')
    flash(resumen, cat)
    for err in errores[:5]:
        flash(err, 'warning')

    return redirect(url_for('docente.ingresar_estudiantes', curso=id_curso))


@docente_bp.route('/registro-estudiantes/eliminar/<int:id_inscripcion>', methods=['POST'])
@role_required('docente')
def eliminar_estudiante(id_inscripcion):
    inscripcion = query(
        "SELECT ic.id_inscripcion, ic.id_curso, ic.id_estudiante, ic.id_evento "
        "FROM inscripcion_curso ic "
        "JOIN curso c ON ic.id_curso = c.id_curso "
        "WHERE ic.id_inscripcion=%s AND c.id_docente=%s",
        (id_inscripcion, session['role_id']), fetch_one=True)

    if not inscripcion:
        flash('Registro no encontrado.', 'danger')
        return redirect(url_for('docente.registro_estudiantes'))

    id_curso      = inscripcion['id_curso']
    id_estudiante = inscripcion['id_estudiante']
    id_evento     = inscripcion['id_evento']

    # Quitar del grupo en este evento y curso
    query(
        "DELETE FROM estudiante_grupo WHERE id_estudiante=%s "
        "AND id_grupo IN (SELECT id_grupo FROM grupo WHERE id_curso=%s AND id_evento=%s)",
        (id_estudiante, id_curso, id_evento), commit=True)

    query("DELETE FROM inscripcion_curso WHERE id_inscripcion=%s",
          (id_inscripcion,), commit=True)
    flash('Estudiante eliminado del registro del curso.', 'success')
    return redirect(url_for('docente.ingresar_estudiantes', curso=id_curso))


@docente_bp.route('/asistencia')
@role_required('docente')
def asistencia():
    if not session.get('es_director'):
        flash('Solo el director puede acceder a esta sección.', 'danger')
        return redirect(url_for('docente.dashboard'))
    evento = _get_evento()
    if not evento:
        flash('No hay un evento activo.', 'warning')
        return redirect(url_for('docente.dashboard'))

    id_evento = evento['id_evento']

    rows = query(
        "SELECT c.id_curso, c.nombre AS nombre_curso, c.color, "
        "       per.nombre, per.apellido, per.dni, per.correo, "
        "       es.id_estudiante, "
        "       COALESCE(pa.asistencia, 0) AS asistencia, "
        "       pa.firma "
        "FROM ( "
        "    SELECT DISTINCT ic.id_estudiante, ic.id_curso "
        "    FROM inscripcion_curso ic "
        "    WHERE ic.id_evento = %s "
        "      AND ic.id_curso IN (SELECT DISTINCT id_curso FROM grupo WHERE id_evento = %s) "
        "    UNION "
        "    SELECT DISTINCT eg.id_estudiante, g.id_curso "
        "    FROM estudiante_grupo eg "
        "    JOIN grupo g ON eg.id_grupo = g.id_grupo "
        "    WHERE g.id_evento = %s "
        ") fuente "
        "JOIN curso c       ON fuente.id_curso      = c.id_curso "
        "JOIN estudiante es ON fuente.id_estudiante = es.id_estudiante "
        "JOIN persona per   ON es.id_persona        = per.id_persona "
        "LEFT JOIN participacion pa "
        "       ON pa.id_estudiante = es.id_estudiante AND pa.id_evento = %s "
        "ORDER BY c.nombre, per.apellido, per.nombre",
        (id_evento, id_evento, id_evento, id_evento))

    cursos = {}
    for r in rows:
        cid = r['id_curso']
        if cid not in cursos:
            cursos[cid] = {
                'id_curso':     cid,
                'nombre_curso': r['nombre_curso'],
                'color':        r['color'],
                'estudiantes':  [],
            }
        cursos[cid]['estudiantes'].append({
            'id_estudiante': r['id_estudiante'],
            'dni':           r['dni'],
            'nombre':        r['nombre'],
            'apellido':      r['apellido'],
            'correo':        r['correo'],
            'asistencia':    bool(r['asistencia']),
            'firma':         r['firma'],
        })

    return render_template('docente/asistencia.html',
                           evento=evento,
                           cursos=list(cursos.values()))


@docente_bp.route('/asistencia/guardar', methods=['POST'])
@role_required('docente')
def asistencia_guardar():
    data          = request.get_json()
    id_estudiante = data.get('id_estudiante')
    id_evento     = data.get('id_evento')
    asistio       = bool(data.get('asistio', False))
    firma         = data.get('firma') or None
    if not asistio:
        firma = None

    query(
        "INSERT INTO participacion (id_evento, id_estudiante, asistencia, firma) "
        "VALUES (%s, %s, %s, %s) "
        "ON DUPLICATE KEY UPDATE asistencia=%s, firma=%s",
        (id_evento, id_estudiante, asistio, firma, asistio, firma),
        commit=True)
    return jsonify({'ok': True})


@docente_bp.route('/ajustes', methods=['GET', 'POST'])
@role_required('docente')
def ajustes():
    if not session.get('es_director'):
        flash('Solo el director puede acceder a esta sección.', 'danger')
        return redirect(url_for('docente.dashboard'))
    evento = _get_evento()

    if request.method == 'POST':
        if not evento:
            flash('No hay evento activo. La secretaria debe configurarlo primero.', 'warning')
            return redirect(url_for('docente.ajustes'))

        edicion     = request.form.get('edicion',     type=int)
        fecha       = request.form.get('fecha',       '').strip()
        hora_inicio = request.form.get('hora_inicio', '').strip()
        hora_fin    = request.form.get('hora_fin',    '').strip()
        semestre    = request.form.get('semestre',    type=int)
        anio        = request.form.get('anio',        type=int)

        if not all([edicion, fecha, hora_inicio, hora_fin, semestre, anio]):
            flash('Todos los campos son obligatorios.', 'danger')
            return redirect(url_for('docente.ajustes'))

        query(
            "UPDATE evento SET edicion=%s, fecha=%s, hora_inicio=%s, hora_fin=%s, "
            "semestre=%s, anio=%s WHERE id_evento=%s",
            (edicion, fecha, hora_inicio, hora_fin, semestre, anio, evento['id_evento']),
            commit=True)
        flash('Ajustes de ExpoEpics guardados correctamente.', 'success')
        return redirect(url_for('docente.ajustes'))

    doc = query("SELECT firma FROM docente_expoepics WHERE id_docente=%s",
                (session['role_id'],), fetch_one=True)
    firma = doc['firma'] if doc else None
    return render_template('docente/ajustes.html', evento=evento, firma=firma)


@docente_bp.route('/ajustes/firma', methods=['POST'])
@role_required('docente')
def guardar_firma():
    if not session.get('es_director'):
        return jsonify({'ok': False}), 403
    data = request.get_json(silent=True) or {}
    firma_data = data.get('firma', '')
    if not firma_data.startswith('data:image/png;base64,'):
        return jsonify({'ok': False, 'error': 'Formato inválido'}), 400
    query("UPDATE docente_expoepics SET firma=%s WHERE id_docente=%s",
          (firma_data, session['role_id']), commit=True)
    return jsonify({'ok': True})


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
