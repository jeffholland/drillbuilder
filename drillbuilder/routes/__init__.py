from flask import Blueprint


def register_blueprints(app):
    from .auth import bp as auth_bp
    from .quizzes import bp as quizzes_bp
    from .attempts import bp as attempts_bp
    from .users import bp as users_bp
    from .frontend import bp as frontend_bp
    from .images import bp as images_bp

    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(quizzes_bp, url_prefix="/quizzes")
    app.register_blueprint(attempts_bp, url_prefix="/attempts")
    app.register_blueprint(users_bp, url_prefix="/users")
    app.register_blueprint(frontend_bp, url_prefix="")
    app.register_blueprint(images_bp, url_prefix="/images")

