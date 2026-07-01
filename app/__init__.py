from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate  # Add this import
import datetime

db = SQLAlchemy()


def create_app():
    app = Flask(__name__)
    app.config.from_object('config.Config')
    app.jinja_env.globals.update(datetime=datetime)

    db.init_app(app)
    migrate = Migrate(app, db)  # Add this line

    @app.context_processor
    def inject_user():
        from flask import session
        from .models import User
        user = None
        if 'user_id' in session:
            user = User.query.get(session['user_id'])
        return dict(current_user=user)

    from .routes.auth import auth_bp
    from .routes.main import main_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)

    return app