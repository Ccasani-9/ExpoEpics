import bcrypt
from flask import Blueprint, render_template, request, session, redirect, url_for, flash
from auth import role_required
from database import query

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


def _get_evento():
    return query("SELECT * FROM evento ORDER BY fecha DESC LIMIT 1", fetch_one=True)


@admin_bp.route('/dashboard')
@role_required('administrador')
def dashboard():
    evento = _get_evento()
    if not evento:
        return render_template('admin/dashboard.html', evento=None,
                               total_mesas=0, mesas_libres=0, conteos={}, tareas_recientes=[])

    id_evento = evento['id_evento']

    total_mesas = query(
        "SELECT COUNT(*) AS cnt FROM espacio WHERE id_evento=%s",
        (id_evento,), fetch_one=True)['cnt']

    mesas_libres = query(
        "SELECT COUNT(*) AS cnt FROM espacio e WHERE e.id_evento=%s "
        "AND e.id_espacio NOT IN (SELECT id_espacio FROM grupo WHERE id_evento=%s)",
        (id_evento, id_evento), fetch_one=True)['cnt']

    tareas_raw = query(
        "SELECT estado, COUNT(*) AS cnt FROM tarea WHERE id_evento=%s GROUP BY estado",
        (id_evento,))
    conteos = {r['estado']: r['cnt'] for r in tareas_raw}
    conteos.setdefault('Pendiente', 0)
    conteos.setdefault('En proceso', 0)
    conteos.setdefault('Completado', 0)
    conteos['Total'] = sum(conteos.values())

    tareas_recientes = query(
        "SELECT t.id_tarea, t.titulo, t.estado, t.fecha_limite, "
        "CONCAT(p.nombre,' ',p.apellido) AS nombre_secretaria "
        "FROM tarea t "
        "JOIN secretaria s ON t.id_secretaria=s.id_secretaria "
        "JOIN persona p ON s.id_persona=p.id_persona "
        "WHERE t.id_evento=%s "
        "ORDER BY FIELD(t.estado,'En proceso','Pendiente','Completado'), t.fecha_limite ASC "
        "LIMIT 6",
        (id_evento,))

    return render_template('admin/dashboard.html',
                           evento=evento,
                           total_mesas=total_mesas,
                           mesas_libres=mesas_libres,
                           conteos=conteos,
                           tareas_recientes=tareas_recientes)


@admin_bp.route('/mesas')
@role_required('administrador')
def mesas():
    evento = _get_evento()
    if not evento:
        return render_template('admin/mesas.html', mesas=[], evento=None)

    lista = query(
        "SELECT e.id_espacio, e.num_mesa, e.ubicacion, "
        "COUNT(g.id_grupo) AS grupos_asignados "
        "FROM espacio e "
        "LEFT JOIN grupo g ON e.id_espacio=g.id_espacio AND g.id_evento=e.id_evento "
        "WHERE e.id_evento=%s "
        "GROUP BY e.id_espacio, e.num_mesa, e.ubicacion "
        "ORDER BY e.num_mesa",
        (evento['id_evento'],))

    return render_template('admin/mesas.html', mesas=lista, evento=evento)


@admin_bp.route('/mesas/crear', methods=['POST'])
@role_required('administrador')
def crear_mesa():
    evento = _get_evento()
    if not evento:
        flash('No hay evento activo.', 'danger')
        return redirect(url_for('admin.mesas'))

    num_mesa  = request.form.get('num_mesa', type=int)
    ubicacion = request.form.get('ubicacion', '').strip()

    if not num_mesa or not ubicacion:
        flash('Número de mesa y ubicación son obligatorios.', 'danger')
        return redirect(url_for('admin.mesas'))

    duplicada = query(
        "SELECT id_espacio FROM espacio WHERE num_mesa=%s AND id_evento=%s",
        (num_mesa, evento['id_evento']), fetch_one=True)
    if duplicada:
        flash(f'Ya existe la Mesa {num_mesa} en este evento.', 'danger')
        return redirect(url_for('admin.mesas'))

    query("INSERT INTO espacio (num_mesa, ubicacion, id_evento) VALUES (%s,%s,%s)",
          (num_mesa, ubicacion, evento['id_evento']), commit=True)
    flash(f'Mesa {num_mesa} creada correctamente.', 'success')
    return redirect(url_for('admin.mesas'))


@admin_bp.route('/mesas/<int:id_espacio>/editar', methods=['POST'])
@role_required('administrador')
def editar_mesa(id_espacio):
    evento = _get_evento()
    if not evento:
        flash('No hay evento activo.', 'danger')
        return redirect(url_for('admin.mesas'))

    espacio = query(
        "SELECT id_espacio FROM espacio WHERE id_espacio=%s AND id_evento=%s",
        (id_espacio, evento['id_evento']), fetch_one=True)
    if not espacio:
        flash('Mesa no encontrada.', 'danger')
        return redirect(url_for('admin.mesas'))

    num_mesa  = request.form.get('num_mesa', type=int)
    ubicacion = request.form.get('ubicacion', '').strip()

    if not num_mesa or not ubicacion:
        flash('Número de mesa y ubicación son obligatorios.', 'danger')
        return redirect(url_for('admin.mesas'))

    duplicada = query(
        "SELECT id_espacio FROM espacio WHERE num_mesa=%s AND id_evento=%s AND id_espacio!=%s",
        (num_mesa, evento['id_evento'], id_espacio), fetch_one=True)
    if duplicada:
        flash(f'Ya existe la Mesa {num_mesa} en este evento.', 'danger')
        return redirect(url_for('admin.mesas'))

    query("UPDATE espacio SET num_mesa=%s, ubicacion=%s WHERE id_espacio=%s",
          (num_mesa, ubicacion, id_espacio), commit=True)
    flash('Mesa actualizada correctamente.', 'success')
    return redirect(url_for('admin.mesas'))


@admin_bp.route('/mesas/<int:id_espacio>/eliminar', methods=['POST'])
@role_required('administrador')
def eliminar_mesa(id_espacio):
    evento = _get_evento()
    if not evento:
        flash('No hay evento activo.', 'danger')
        return redirect(url_for('admin.mesas'))

    ocupada = query(
        "SELECT id_grupo FROM grupo WHERE id_espacio=%s AND id_evento=%s",
        (id_espacio, evento['id_evento']), fetch_one=True)
    if ocupada:
        flash('No se puede eliminar una mesa con un grupo asignado.', 'danger')
        return redirect(url_for('admin.mesas'))

    espacio = query(
        "SELECT num_mesa FROM espacio WHERE id_espacio=%s AND id_evento=%s",
        (id_espacio, evento['id_evento']), fetch_one=True)
    if not espacio:
        flash('Mesa no encontrada.', 'danger')
        return redirect(url_for('admin.mesas'))

    query("DELETE FROM espacio WHERE id_espacio=%s", (id_espacio,), commit=True)
    flash(f'Mesa {espacio["num_mesa"]} eliminada.', 'success')
    return redirect(url_for('admin.mesas'))


@admin_bp.route('/tareas')
@role_required('administrador')
def tareas():
    evento = _get_evento()
    filtro = request.args.get('estado', 'Todos')
    if not evento:
        return render_template('admin/tareas.html', tareas=[], evento=None,
                               filtro=filtro, conteos={})

    id_evento = evento['id_evento']
    sql = (
        "SELECT t.*, CONCAT(p.nombre,' ',p.apellido) AS nombre_secretaria "
        "FROM tarea t "
        "JOIN secretaria s ON t.id_secretaria=s.id_secretaria "
        "JOIN persona p ON s.id_persona=p.id_persona "
        "WHERE t.id_evento=%s"
    )
    params = [id_evento]
    if filtro != 'Todos':
        sql += " AND t.estado=%s"
        params.append(filtro)
    sql += " ORDER BY FIELD(t.estado,'En proceso','Pendiente','Completado'), t.fecha_limite ASC"

    lista = query(sql, params)
    conteos_raw = query(
        "SELECT estado, COUNT(*) AS cnt FROM tarea WHERE id_evento=%s GROUP BY estado",
        (id_evento,))
    conteos = {r['estado']: r['cnt'] for r in conteos_raw}
    conteos.setdefault('Pendiente', 0)
    conteos.setdefault('En proceso', 0)
    conteos.setdefault('Completado', 0)
    conteos['Total'] = sum(conteos.values())

    return render_template('admin/tareas.html', tareas=lista, evento=evento,
                           filtro=filtro, conteos=conteos)


@admin_bp.route('/tarea/<int:id_tarea>/estado', methods=['POST'])
@role_required('administrador')
def cambiar_estado_tarea(id_tarea):
    nuevo = request.form.get('estado')
    if nuevo not in ('Pendiente', 'En proceso', 'Completado'):
        flash('Estado inválido.', 'danger')
        return redirect(url_for('admin.tareas'))
    if nuevo == 'Completado':
        query("UPDATE tarea SET estado=%s, fecha_culminacion=CURDATE() WHERE id_tarea=%s",
              (nuevo, id_tarea), commit=True)
    else:
        query("UPDATE tarea SET estado=%s, fecha_culminacion=NULL WHERE id_tarea=%s",
              (nuevo, id_tarea), commit=True)
    return redirect(url_for('admin.tareas'))


@admin_bp.route('/tarea/<int:id_tarea>/comentario', methods=['POST'])
@role_required('administrador')
def agregar_comentario(id_tarea):
    comentario = request.form.get('comentario', '').strip()
    query("UPDATE tarea SET comentario=%s WHERE id_tarea=%s",
          (comentario, id_tarea), commit=True)
    return redirect(url_for('admin.tareas'))


@admin_bp.route('/cuenta', methods=['GET', 'POST'])
@role_required('administrador')
def cuenta():
    error = success = None
    if request.method == 'POST':
        actual    = request.form.get('contrasena_actual', '')
        nueva     = request.form.get('nueva_contrasena', '')
        confirmar = request.form.get('confirmar_contrasena', '')
        persona = query("SELECT contrasena FROM persona WHERE id_persona=%s",
                        (session['id_persona'],), fetch_one=True)
        stored = persona['contrasena'].encode() if isinstance(persona['contrasena'], str) else persona['contrasena']
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
    return render_template('admin/cuenta.html', error=error, success=success)
