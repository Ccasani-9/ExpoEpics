from flask import Blueprint, render_template, request, session, redirect, url_for, flash
import bcrypt
from database import query

auth_bp = Blueprint('auth', __name__)

_PRIORITY = ['secretaria', 'docente', 'marketing', 'juez', 'estudiante']

_TAB_ROLES = {
    'docente':    ['docente', 'secretaria'],
    'estudiante': ['estudiante'],
    'juez':       ['juez', 'marketing'],
}


def _detect_roles(id_persona):
    checks = [
        ('secretaria',          'secretaria',  'id_secretaria'),
        ('docente_expoepics',   'docente',     'id_docente'),
        ('encargado_marketing', 'marketing',   'id_marketing'),
        ('juez',                'juez',        'id_juez'),
        ('estudiante',          'estudiante',  'id_estudiante'),
        ('administrador',       'administrador','id_administrador'),
    ]
    roles = {}
    for table, name, col in checks:
        row = query(f"SELECT {col} FROM {table} WHERE id_persona=%s", (id_persona,), fetch_one=True)
        if row:
            roles[name] = row[col]
    return roles


def _primary_role(roles):
    for r in _PRIORITY:
        if r in roles:
            return r
    return None


def redirect_by_role(role):
    m = {
        'secretaria': 'secretaria.dashboard',
        'docente':    'docente.dashboard',
        'marketing':  'marketing.ranking',
        'juez':       'juez.proyectos',
        'estudiante': 'estudiante.proyecto',
    }
    return redirect(url_for(m.get(role, 'auth.login')))


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if 'id_persona' in session and not session.get('temp_pass'):
        return redirect_by_role(session.get('role'))

    error = None
    tab = request.args.get('tab', 'docente')

    if request.method == 'POST':
        correo    = request.form.get('correo', '').strip().lower()
        password  = request.form.get('contrasena', '')
        tab       = request.form.get('tab', 'docente')

        persona = query("SELECT * FROM persona WHERE LOWER(correo)=%s", (correo,), fetch_one=True)

        if not persona:
            error = 'Correo o contraseña incorrectos.'
            return render_template('login.html', error=error, tab=tab)

        stored = persona['contrasena']
        if isinstance(stored, str):
            stored = stored.encode()
        try:
            valid = bcrypt.checkpw(password.encode(), stored)
        except Exception:
            valid = False

        if not valid:
            error = 'Correo o contraseña incorrectos.'
            return render_template('login.html', error=error, tab=tab)

        roles = _detect_roles(persona['id_persona'])
        primary = _primary_role(roles)

        if not primary:
            error = 'Este usuario no tiene un rol asignado.'
            return render_template('login.html', error=error, tab=tab)

        if primary not in _TAB_ROLES.get(tab, []):
            error = 'Este correo no tiene acceso a este portal.'
            return render_template('login.html', error=error, tab=tab)

        session.clear()
        session['id_persona'] = persona['id_persona']
        session['nombre']     = persona['nombre']
        session['apellido']   = persona['apellido']
        session['correo']     = persona['correo']
        session['role']       = primary
        session['role_id']    = roles[primary]
        session['temp_pass']  = bool(persona['contrasena_temporal'])

        if persona['contrasena_temporal']:
            return redirect(url_for('auth.cambiar_pass'))

        return redirect_by_role(primary)

    return render_template('login.html', error=error, tab=tab)


@auth_bp.route('/cambiar-pass', methods=['GET', 'POST'])
def cambiar_pass():
    if 'id_persona' not in session:
        return redirect(url_for('auth.login'))

    forzado = session.get('temp_pass', False)
    error = None

    if request.method == 'POST':
        nueva     = request.form.get('nueva_contrasena', '')
        confirmar = request.form.get('confirmar_contrasena', '')

        if len(nueva) < 6:
            error = 'La contraseña debe tener al menos 6 caracteres.'
        elif nueva != confirmar:
            error = 'Las contraseñas no coinciden.'
        else:
            hashed = bcrypt.hashpw(nueva.encode(), bcrypt.gensalt()).decode()
            query("UPDATE persona SET contrasena=%s, contrasena_temporal=0 WHERE id_persona=%s",
                  (hashed, session['id_persona']), commit=True)
            session['temp_pass'] = False
            flash('Contraseña actualizada correctamente.', 'success')
            return redirect_by_role(session.get('role'))

    return render_template('cambiar_pass.html', forzado=forzado, error=error)


@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))
