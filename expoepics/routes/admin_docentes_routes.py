import bcrypt
import mysql.connector
from flask import Blueprint, render_template, request, session, redirect, url_for, flash
from config import Config
from database import query

admin_docentes_bp = Blueprint('admin_docentes', __name__, url_prefix='/admin-docentes')


def _guard():
    if session.get('role') != 'admin_docentes':
        return redirect(url_for('auth.login', tab='admin_docentes'))
    return None


@admin_docentes_bp.route('/login', methods=['POST'])
def login():
    usuario  = request.form.get('usuario', '').strip()
    password = request.form.get('contrasena', '')

    try:
        test = mysql.connector.connect(
            host=Config.DB_HOST,
            port=int(Config.DB_PORT),
            user=usuario,
            password=password,
            database=Config.DB_NAME,
        )
        test.close()
    except Exception:
        return render_template('login.html',
                               error='Usuario o contraseña MySQL incorrectos.',
                               tab='admin_docentes')

    session.clear()
    session['role']     = 'admin_docentes'
    session['nombre']   = 'Admin'
    session['apellido'] = 'Docentes'
    session['usuario']  = usuario
    return redirect(url_for('admin_docentes.dashboard'))


@admin_docentes_bp.route('/dashboard')
def dashboard():
    guard = _guard()
    if guard:
        return guard

    personas = query(
        "SELECT * FROM vista_personas ORDER BY apellido, nombre"
    )
    docentes = query(
        "SELECT * FROM vista_docentes ORDER BY apellido, nombre"
    )
    personas_disponibles = query(
        "SELECT * FROM vista_personas "
        "WHERE id_persona NOT IN (SELECT id_persona FROM docente_expoepics) "
        "ORDER BY apellido, nombre"
    )
    return render_template('admin_docentes/dashboard.html',
                           personas=personas,
                           docentes=docentes,
                           personas_disponibles=personas_disponibles)


@admin_docentes_bp.route('/persona/agregar', methods=['POST'])
def agregar_persona():
    guard = _guard()
    if guard:
        return guard

    dni        = request.form.get('dni', '').strip()
    nombre     = request.form.get('nombre', '').strip()
    apellido   = request.form.get('apellido', '').strip()
    correo     = request.form.get('correo', '').strip().lower()
    contrasena = request.form.get('contrasena', '').strip()

    if not all([dni, nombre, apellido, correo, contrasena]):
        flash('Todos los campos son obligatorios.', 'danger')
        return redirect(url_for('admin_docentes.dashboard'))

    if len(dni) != 8 or not dni.isdigit():
        flash('El DNI debe tener exactamente 8 dígitos numéricos.', 'danger')
        return redirect(url_for('admin_docentes.dashboard'))

    existente = query(
        "SELECT id_persona FROM persona WHERE dni=%s OR correo=%s",
        (dni, correo), fetch_one=True
    )
    if existente:
        flash('Ya existe una persona con ese DNI o correo.', 'danger')
        return redirect(url_for('admin_docentes.dashboard'))

    hashed = bcrypt.hashpw(contrasena.encode(), bcrypt.gensalt()).decode()
    query(
        "INSERT INTO persona (dni, nombre, apellido, correo, contrasena, contrasena_temporal) "
        "VALUES (%s, %s, %s, %s, %s, 0)",
        (dni, nombre, apellido, correo, hashed), commit=True
    )
    flash(f'{nombre} {apellido} agregado correctamente.', 'success')
    return redirect(url_for('admin_docentes.dashboard'))


@admin_docentes_bp.route('/persona/eliminar/<int:id_persona>', methods=['POST'])
def eliminar_persona(id_persona):
    guard = _guard()
    if guard:
        return guard

    persona = query(
        "SELECT nombre, apellido FROM persona WHERE id_persona=%s",
        (id_persona,), fetch_one=True
    )
    if not persona:
        flash('Persona no encontrada.', 'danger')
        return redirect(url_for('admin_docentes.dashboard'))

    query("DELETE FROM docente_expoepics WHERE id_persona=%s", (id_persona,), commit=True)
    query("DELETE FROM persona WHERE id_persona=%s", (id_persona,), commit=True)
    flash(f'{persona["nombre"]} {persona["apellido"]} eliminado.', 'success')
    return redirect(url_for('admin_docentes.dashboard'))


@admin_docentes_bp.route('/docente/agregar', methods=['POST'])
def agregar_docente():
    guard = _guard()
    if guard:
        return guard

    id_persona  = request.form.get('id_persona', type=int)
    es_director = 1 if request.form.get('es_director') else 0

    if not id_persona:
        flash('Selecciona una persona.', 'danger')
        return redirect(url_for('admin_docentes.dashboard'))

    existente = query(
        "SELECT id_docente FROM docente_expoepics WHERE id_persona=%s",
        (id_persona,), fetch_one=True
    )
    if existente:
        flash('Esa persona ya es docente.', 'warning')
        return redirect(url_for('admin_docentes.dashboard'))

    query(
        "INSERT INTO docente_expoepics (id_persona, es_director) VALUES (%s, %s)",
        (id_persona, es_director), commit=True
    )
    flash('Docente agregado correctamente.', 'success')
    return redirect(url_for('admin_docentes.dashboard'))


@admin_docentes_bp.route('/docente/eliminar/<int:id_docente>', methods=['POST'])
def eliminar_docente(id_docente):
    guard = _guard()
    if guard:
        return guard

    docente = query(
        "SELECT d.id_docente, p.nombre, p.apellido "
        "FROM docente_expoepics d "
        "JOIN persona p ON d.id_persona = p.id_persona "
        "WHERE d.id_docente=%s",
        (id_docente,), fetch_one=True
    )
    if not docente:
        flash('Docente no encontrado.', 'danger')
        return redirect(url_for('admin_docentes.dashboard'))

    query("DELETE FROM docente_expoepics WHERE id_docente=%s", (id_docente,), commit=True)
    flash(f'{docente["nombre"]} {docente["apellido"]} eliminado de docentes.', 'success')
    return redirect(url_for('admin_docentes.dashboard'))


@admin_docentes_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))
