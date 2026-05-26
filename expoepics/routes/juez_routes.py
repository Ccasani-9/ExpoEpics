import bcrypt
from datetime import date
from flask import Blueprint, render_template, request, session, redirect, url_for, flash
from auth import role_required
from database import query

juez_bp = Blueprint('juez', __name__, url_prefix='/juez')


def _get_evento():
    return query("SELECT * FROM evento ORDER BY fecha DESC LIMIT 1", fetch_one=True)


@juez_bp.route('/proyectos')
@role_required('juez')
def proyectos():
    evento = _get_evento()
    pendientes = []
    evaluados  = []
    if evento:
        id_evento = evento['id_evento']
        id_juez   = session['role_id']

        evaluados = query(
            "SELECT p.id_proyecto, p.nombre, ev.calificacion, ev.id_evaluacion, ev.finalizada, "
            "c.nombre AS nombre_curso, g.id_grupo, e.num_mesa "
            "FROM evaluacion ev JOIN proyecto p ON ev.id_proyecto=p.id_proyecto "
            "JOIN grupo g ON p.id_grupo=g.id_grupo "
            "JOIN curso c ON g.id_curso=c.id_curso "
            "JOIN espacio e ON g.id_espacio=e.id_espacio "
            "WHERE ev.id_juez=%s AND g.id_evento=%s ORDER BY ev.fecha_evaluacion DESC",
            (id_juez, id_evento))

        ids_evaluados = [r['id_proyecto'] for r in evaluados]
        if ids_evaluados:
            fmt = ','.join(['%s'] * len(ids_evaluados))
            pendientes = query(
                f"SELECT p.id_proyecto, p.nombre, p.descripcion, "
                f"c.nombre AS nombre_curso, g.id_grupo, e.num_mesa "
                f"FROM proyecto p JOIN grupo g ON p.id_grupo=g.id_grupo "
                f"JOIN curso c ON g.id_curso=c.id_curso "
                f"JOIN espacio e ON g.id_espacio=e.id_espacio "
                f"WHERE g.id_evento=%s AND p.id_proyecto NOT IN ({fmt})",
                [id_evento] + ids_evaluados)
        else:
            pendientes = query(
                "SELECT p.id_proyecto, p.nombre, p.descripcion, "
                "c.nombre AS nombre_curso, g.id_grupo, e.num_mesa "
                "FROM proyecto p JOIN grupo g ON p.id_grupo=g.id_grupo "
                "JOIN curso c ON g.id_curso=c.id_curso "
                "JOIN espacio e ON g.id_espacio=e.id_espacio "
                "WHERE g.id_evento=%s",
                (id_evento,))

    return render_template('juez/proyectos.html',
                           pendientes=pendientes, evaluados=evaluados, evento=evento)


@juez_bp.route('/evaluar/<int:id_proyecto>', methods=['GET', 'POST'])
@role_required('juez')
def evaluar(id_proyecto):
    id_juez = session['role_id']

    proyecto = query(
        "SELECT p.*, c.nombre AS nombre_curso, g.id_grupo, e.num_mesa "
        "FROM proyecto p JOIN grupo g ON p.id_grupo=g.id_grupo "
        "JOIN curso c ON g.id_curso=c.id_curso "
        "JOIN espacio e ON g.id_espacio=e.id_espacio "
        "WHERE p.id_proyecto=%s", (id_proyecto,), fetch_one=True)

    if not proyecto:
        flash('Proyecto no encontrado.', 'danger')
        return redirect(url_for('juez.proyectos'))

    evaluacion = query(
        "SELECT * FROM evaluacion WHERE id_proyecto=%s AND id_juez=%s",
        (id_proyecto, id_juez), fetch_one=True)

    error = None
    if request.method == 'POST':
        if evaluacion and evaluacion['finalizada']:
            flash('Esta evaluación ya está finalizada y no puede modificarse.', 'warning')
            return redirect(url_for('juez.proyectos'))

        calificacion    = request.form.get('calificacion', '')
        detalle         = request.form.get('detalle', '').strip()
        aspectos_mejora = request.form.get('aspectos_mejora', '').strip()
        accion          = request.form.get('accion', 'borrador')

        opciones_val = ('Excelente','Muy buena','Buena','Regular','Mala','Muy mala','Revisado')
        if calificacion not in opciones_val:
            error = 'Debes seleccionar una calificación válida.'
        else:
            finalizada = 1 if accion == 'finalizar' else 0
            if evaluacion:
                query(
                    "UPDATE evaluacion SET calificacion=%s, detalle=%s, aspectos_mejora=%s, "
                    "fecha_evaluacion=CURDATE(), finalizada=%s WHERE id_evaluacion=%s",
                    (calificacion, detalle, aspectos_mejora, finalizada, evaluacion['id_evaluacion']), commit=True)
            else:
                query(
                    "INSERT INTO evaluacion (id_proyecto,id_juez,calificacion,detalle,aspectos_mejora,fecha_evaluacion,finalizada) "
                    "VALUES(%s,%s,%s,%s,%s,CURDATE(),%s)",
                    (id_proyecto, id_juez, calificacion, detalle, aspectos_mejora, finalizada), commit=True)
            msg = 'Evaluación finalizada y bloqueada.' if finalizada else 'Borrador guardado correctamente.'
            flash(msg, 'success')
            return redirect(url_for('juez.proyectos'))

    tecnologias = [t.strip() for t in (proyecto['tecnologias_usadas'] or '').split(',') if t.strip()]
    return render_template('juez/evaluar.html',
                           proyecto=proyecto, evaluacion=evaluacion,
                           tecnologias=tecnologias, error=error)


@juez_bp.route('/evaluacion/<int:id_evaluacion>/finalizar', methods=['POST'])
@role_required('juez')
def finalizar(id_evaluacion):
    ev = query("SELECT * FROM evaluacion WHERE id_evaluacion=%s AND id_juez=%s",
               (id_evaluacion, session['role_id']), fetch_one=True)
    if not ev:
        flash('Evaluación no encontrada.', 'danger')
    elif ev['finalizada']:
        flash('La evaluación ya estaba finalizada.', 'warning')
    else:
        query("UPDATE evaluacion SET finalizada=1 WHERE id_evaluacion=%s", (id_evaluacion,), commit=True)
        flash('Evaluación finalizada y bloqueada.', 'success')
    return redirect(url_for('juez.historial'))


@juez_bp.route('/historial')
@role_required('juez')
def historial():
    evento = _get_evento()
    lista = []
    if evento:
        lista = query(
            "SELECT ev.id_evaluacion, ev.calificacion, ev.detalle, ev.aspectos_mejora, "
            "ev.fecha_evaluacion, ev.finalizada, "
            "p.nombre AS nombre_proyecto, p.id_proyecto, "
            "c.nombre AS nombre_curso, g.id_grupo, e.num_mesa "
            "FROM evaluacion ev JOIN proyecto p ON ev.id_proyecto=p.id_proyecto "
            "JOIN grupo g ON p.id_grupo=g.id_grupo "
            "JOIN curso c ON g.id_curso=c.id_curso "
            "JOIN espacio e ON g.id_espacio=e.id_espacio "
            "WHERE ev.id_juez=%s AND g.id_evento=%s ORDER BY ev.fecha_evaluacion DESC",
            (session['role_id'], evento['id_evento']))
    return render_template('juez/historial.html', evaluaciones=lista, evento=evento)


@juez_bp.route('/cuenta', methods=['GET', 'POST'])
@role_required('juez')
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
    return render_template('juez/cuenta.html', error=error, success=success)
