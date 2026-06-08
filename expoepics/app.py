from flask import Flask, redirect, url_for, session
from config import Config
from database import close_db, query


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    app.teardown_appcontext(close_db)

    @app.context_processor
    def inject_evento_activo():
        evt = query("SELECT * FROM evento ORDER BY fecha DESC LIMIT 1", fetch_one=True)
        return {'g_evento': evt}

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
    def index():1
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
