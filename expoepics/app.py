from flask import Flask, redirect, url_for, session
from config import Config
from database import close_db, query

_MESES_ES = {
    'January': 'Enero', 'February': 'Febrero', 'March': 'Marzo',
    'April': 'Abril', 'May': 'Mayo', 'June': 'Junio',
    'July': 'Julio', 'August': 'Agosto', 'September': 'Septiembre',
    'October': 'Octubre', 'November': 'Noviembre', 'December': 'Diciembre',
}
_DIAS_ES = {
    'Monday': 'Lunes', 'Tuesday': 'Martes', 'Wednesday': 'Miércoles',
    'Thursday': 'Jueves', 'Friday': 'Viernes', 'Saturday': 'Sábado', 'Sunday': 'Domingo',
}


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    app.teardown_appcontext(close_db)

    @app.template_filter('fecha_es')
    def fecha_es_filter(fecha, fmt='%d de %B de %Y'):
        if not fecha:
            return ''
        s = fecha.strftime(fmt)
        for en, es in _MESES_ES.items():
            s = s.replace(en, es)
        for en, es in _DIAS_ES.items():
            s = s.replace(en, es)
        return s

    @app.template_filter('hora_fmt')
    def hora_fmt_filter(t):
        if t is None:
            return '—'
        if hasattr(t, 'strftime'):
            return t.strftime('%H:%M')
        total = int(t.total_seconds())
        return f"{total // 3600:02d}:{(total % 3600) // 60:02d}"

    @app.context_processor
    def inject_evento_activo():
        todos = query("SELECT * FROM evento ORDER BY fecha DESC")
        id_vista = session.get('id_evento_vista')
        evt = None
        if id_vista:
            evt = query("SELECT * FROM evento WHERE id_evento=%s", (id_vista,), fetch_one=True)
        if not evt:
            evt = query("SELECT * FROM evento WHERE es_activo=1 LIMIT 1", fetch_one=True)
        return {'g_evento': evt, 'g_todos_eventos': todos or []}

    from routes.auth_routes           import auth_bp
    from routes.docente_routes        import docente_bp
    from routes.secretaria_routes     import secretaria_bp
    from routes.estudiante_routes     import estudiante_bp
    from routes.juez_routes           import juez_bp
    from routes.marketing_routes      import marketing_bp
    from routes.administrador_routes  import admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(docente_bp)
    app.register_blueprint(secretaria_bp)
    app.register_blueprint(estudiante_bp)
    app.register_blueprint(juez_bp)
    app.register_blueprint(marketing_bp)
    app.register_blueprint(admin_bp)

    @app.route('/')
    def index():
        if 'id_persona' not in session:
            return redirect(url_for('auth.login'))
        _map = {
            'secretaria':    'secretaria.dashboard',
            'docente':       'docente.dashboard',
            'marketing':     'marketing.ranking',
            'juez':          'juez.proyectos',
            'estudiante':    'estudiante.proyecto',
            'administrador': 'admin.dashboard',
        }
        return redirect(url_for(_map.get(session.get('role'), 'auth.login')))

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=5000)
