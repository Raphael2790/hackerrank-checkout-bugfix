from flask import Flask

from app.repository import Repository
from app.routes import api, register_error_handlers


def create_app() -> Flask:
    app = Flask(__name__)
    repo = Repository()
    repo.seed()
    app.extensions["repo"] = repo

    app.register_blueprint(api)
    register_error_handlers(app)
    return app
