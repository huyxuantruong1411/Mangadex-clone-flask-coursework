# app/__init__.py
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

db = SQLAlchemy()
login_manager = LoginManager()

def create_app():
    app = Flask(__name__)
    app.config.from_object("config.Config")

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"

    from .auth import auth as auth_blueprint
    from .routes import main as main_blueprint, manga as manga_blueprint
    from .comment_routes import comment_bp as comment_blueprint  # new

    app.register_blueprint(auth_blueprint)
    app.register_blueprint(main_blueprint)
    app.register_blueprint(manga_blueprint, url_prefix='/manga')
    app.register_blueprint(comment_blueprint)  # register comment API blueprint

    return app

# user loader
from .models import User

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)
