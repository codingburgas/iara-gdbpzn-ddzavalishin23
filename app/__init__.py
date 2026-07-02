from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime  # import the class, not the module

db = SQLAlchemy()


def create_app():
    app = Flask(__name__)
    app.config.from_object('config.Config')

    # Make datetime class available in all templates
    app.jinja_env.globals.update(datetime=datetime)

    db.init_app(app)

    @app.context_processor
    def inject_user():
        from flask import session
        from .models import User
        user = None
        if 'user_id' in session:
            user = User.query.get(session['user_id'])
            if user is None:
                # Invalid session – clear it
                session.pop('user_id', None)
                session.pop('username', None)
        return dict(current_user=user)

    from .routes.auth import auth_bp
    from .routes.main import main_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)

    return app