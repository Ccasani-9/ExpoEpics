from functools import wraps
from flask import session, redirect, url_for, flash


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'id_persona' not in session:
            flash('Debes iniciar sesión primero.', 'warning')
            return redirect(url_for('auth.login'))
        if session.get('temp_pass'):
            return redirect(url_for('auth.cambiar_pass'))
        return f(*args, **kwargs)
    return decorated


def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if 'id_persona' not in session:
                flash('Debes iniciar sesión primero.', 'warning')
                return redirect(url_for('auth.login'))
            if session.get('temp_pass'):
                return redirect(url_for('auth.cambiar_pass'))
            if session.get('role') not in roles:
                flash('No tienes acceso a esta sección.', 'danger')
                return redirect(url_for('auth.login'))
            return f(*args, **kwargs)
        return decorated
    return decorator
