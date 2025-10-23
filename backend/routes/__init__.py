from flask import Blueprint
from .auth import auth_bp
from .user import user_bp
from .community import community_bp
from .learning_paths import learning_paths_bp



def register_blueprints(app):
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(user_bp, url_prefix="/user")
    app.register_blueprint(community_bp, url_prefix="/community")
    app.register_blueprint(learning_paths_bp, url_prefix="/learning-paths")
    