import csv
import io
import bcrypt
from flask import Blueprint, render_template, request, session, redirect, url_for, make_response
from auth import role_required
from database import query

marketing_bp = Blueprint('marketing', __name__, url_prefix='/marketing')

_PESO = {'Excelente': 5, 'Muy buena': 4, 'Buena': 3,
         'Regular': 2, 'Mala': 1, 'Revisado': 0}


def _get_evento():
    id_vista = session.get('id_evento_vista')
    if id_vista:
        evt = query("SELECT * FROM evento WHERE id_evento=%s", (id_vista,), fetch_one=True)
        if evt:
            return evt
    return query("SELECT * FROM evento WHERE es_activo=1 LIMIT 1", fetch_one=True)


def _get_ranking(id_evento):
    return query(
        "SELECT p.id_proyecto, p.nombre, p.descripcion, p.tecnologias_usadas, "
        "c.nombre AS nombre_curso, c.color, g.id_grupo, e.num_mesa, e.ubicacion, "
        "COUNT(ev.id_evaluacion) AS num_evaluaciones, "
        "AVG(CASE ev.calificacion "
        "    WHEN 'Excelente' THEN 5 WHEN 'Muy buena' THEN 4 WHEN 'Buena' THEN 3 "
        "    WHEN 'Regular'   THEN 2 WHEN 'Mala'      THEN 1 "
        "    WHEN 'Revisado'  THEN 0 ELSE NULL END) AS promedio "
        "FROM proyecto p "
        "JOIN grupo g ON p.id_grupo=g.id_grupo "
        "JOIN curso c ON g.id_curso=c.id_curso "
        "JOIN espacio e ON g.id_espacio=e.id_espacio "
        "LEFT JOIN evaluacion ev ON p.id_proyecto=ev.id_proyecto "
        "WHERE g.id_evento=%s "
        "GROUP BY p.id_proyecto,p.nombre,p.descripcion,p.tecnologias_usadas,"
        "c.nombre,c.color,g.id_grupo,e.num_mesa,e.ubicacion "
        "ORDER BY promedio DESC, p.nombre ASC",
        (id_evento,))


def _stars(promedio):
    if promedio is None:
        return 0
    return round(promedio, 1)


def _evaluaciones_proyecto(id_proyecto):
    rows = query(
        "SELECT ev.calificacion, ev.detalle, ev.aspectos_mejora, ev.fecha_evaluacion, ev.finalizada, "
        "CONCAT(per.nombre,' ',per.apellido) AS nombre_juez "
        "FROM evaluacion ev JOIN juez j ON ev.id_juez=j.id_juez "
        "JOIN persona per ON j.id_persona=per.id_persona "
        "WHERE ev.id_proyecto=%s ORDER BY ev.fecha_evaluacion DESC",
        (id_proyecto,)) or []
    out = []
    for r in rows:
        d = dict(r)
        if d.get('fecha_evaluacion') is not None:
            d['fecha_evaluacion'] = str(d['fecha_evaluacion'])
        d['finalizada'] = bool(d['finalizada'])
        out.append(d)
    return out


def _documentos_proyecto(id_proyecto):
    rows = query(
        "SELECT id_documento, nombre_original, url_archivo, fecha_subida "
        "FROM proyecto_documento WHERE id_proyecto=%s ORDER BY fecha_subida",
        (id_proyecto,)) or []
    out = []
    for r in rows:
        d = dict(r)
        if d.get('fecha_subida') is not None:
            d['fecha_subida'] = str(d['fecha_subida'])
        out.append(d)
    return out


@marketing_bp.route('/ranking')
@role_required('marketing')
def ranking():
    evento = _get_evento()
    proyectos = []
    cursos_set = {}
    if evento:
        raw = _get_ranking(evento['id_evento'])
        for r in raw:
            p = dict(r)
            p['promedio']      = float(p['promedio']) if p['promedio'] is not None else None
            p['estrellas']     = _stars(p['promedio'])
            p['evaluaciones']  = _evaluaciones_proyecto(p['id_proyecto'])
            p['documentos']    = _documentos_proyecto(p['id_proyecto'])
            proyectos.append(p)
            cursos_set[p['nombre_curso']] = p['color']

    cursos = [{'nombre': k, 'color': v} for k, v in sorted(cursos_set.items())]

    # Podio: top 3 valores de promedio distintos (empates comparten el mismo puesto)
    grupos = []
    for p in proyectos:
        if p['promedio'] is None:
            continue
        val = round(p['promedio'], 2)
        if grupos and grupos[-1]['valor'] == val:
            grupos[-1]['proyectos'].append(p)
        else:
            grupos.append({'valor': val, 'proyectos': [p]})
    podio = grupos[:3]
    for i, g in enumerate(podio, 1):
        g['posicion'] = i
        g['empate'] = len(g['proyectos']) > 1

    return render_template('marketing/ranking.html',
                           proyectos=proyectos, podio=podio, cursos=cursos,
                           evento=evento, stars=_stars)


@marketing_bp.route('/proyectos')
@role_required('marketing')
def proyectos():
    evento = _get_evento()
    lista  = []
    if evento:
        raw = _get_ranking(evento['id_evento'])
        for p in raw:
            p['estrellas'] = _stars(p['promedio'])
            p['evaluaciones'] = query(
                "SELECT ev.calificacion, ev.detalle, ev.aspectos_mejora, ev.fecha_evaluacion, "
                "CONCAT(per.nombre,' ',per.apellido) AS nombre_juez "
                "FROM evaluacion ev JOIN juez j ON ev.id_juez=j.id_juez "
                "JOIN persona per ON j.id_persona=per.id_persona "
                "WHERE ev.id_proyecto=%s ORDER BY ev.fecha_evaluacion DESC",
                (p['id_proyecto'],))
        lista = raw
    return render_template('marketing/proyectos.html', proyectos=lista, evento=evento)


@marketing_bp.route('/exportar')
@role_required('marketing')
def exportar():
    evento = _get_evento()
    filas  = []
    if evento:
        filas = _get_ranking(evento['id_evento'])

    buf = io.StringIO()
    w   = csv.writer(buf)
    w.writerow(['Posición', 'Proyecto', 'Curso', 'Mesa', 'Promedio (0-5)', 'Estrellas (0-5)', 'Evaluaciones'])
    for i, p in enumerate(filas, 1):
        prom  = f"{p['promedio']:.2f}" if p['promedio'] is not None else 'Sin calificar'
        stars = f"{_stars(p['promedio']):.1f}" if p['promedio'] is not None else '-'
        w.writerow([i, p['nombre'], p['nombre_curso'], p['num_mesa'], prom, stars, p['num_evaluaciones']])

    resp = make_response(buf.getvalue().encode('utf-8-sig'))
    resp.headers['Content-Type'] = 'text/csv; charset=utf-8'
    resp.headers['Content-Disposition'] = 'attachment; filename=ranking_expoepics.csv'
    return resp


@marketing_bp.route('/cuenta', methods=['GET', 'POST'])
@role_required('marketing')
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
    return render_template('marketing/cuenta.html', error=error, success=success)
