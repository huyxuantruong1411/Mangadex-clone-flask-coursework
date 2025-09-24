from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from config import Config
import os

db = SQLAlchemy()
login_manager = LoginManager()

from .models import User

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, user_id)

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'

    # Register blueprints
    from .auth import auth as auth_blueprint
    from .routes import main as main_blueprint, manga as manga_blueprint
    from .comment_routes import comment_bp as comment_blueprint
    from .list_routes import list_bp as list_blueprint
    from .blueprints.reader import reader as reader_blueprint

    app.register_blueprint(auth_blueprint, url_prefix='/auth')
    app.register_blueprint(main_blueprint)
    app.register_blueprint(manga_blueprint, url_prefix='/manga')
    app.register_blueprint(comment_blueprint, url_prefix='/comment')
    app.register_blueprint(list_blueprint, url_prefix='/api')
    app.register_blueprint(reader_blueprint, url_prefix='/reader')

    return app