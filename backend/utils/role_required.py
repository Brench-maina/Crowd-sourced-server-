from functools import wraps
from flask_jwt_extended import get_jwt_identity, jwt_required
from flask import jsonify
from models import User

def role_required(*roles):
    """
    Decorator to restrict access to users with specific roles.

    Usage:
        @role_required("admin")
        @role_required("admin", "contributor")
        @role_required(["admin", "contributor"])
    """
    # If a single list is passed, unpack it
    if len(roles) == 1 and isinstance(roles[0], (list, tuple)):
        roles = roles[0]

    def decorator(fn):
        @wraps(fn)
        @jwt_required()
        def wrapper(*args, **kwargs):
            current_user_id = get_jwt_identity()
            user = User.query.get(current_user_id)
            if not user:
                return jsonify({"error": "User not found"}), 404

            if user.role.value not in roles:
                return jsonify({"error": "Forbidden"}), 403

            return fn(*args, **kwargs)
        return wrapper
    return decorator
