from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from models import db, Module, LearningResource
from utils.role_required import role_required

modules_bp = Blueprint("modules_bp", __name__)

@modules_bp.route("/<int:module_id>/resources", methods=["GET"])
@jwt_required()
def get_module_resources(module_id):
    """Fetch all learning resources under a specific module."""
    module = Module.query.get(module_id)
    if not module:
        return jsonify({"error": "Module not found"}), 404

    resources = LearningResource.query.filter_by(module_id=module_id).all()
    return jsonify([r.to_dict() for r in resources]), 200

@modules_bp.route("/<int:module_id>/resources", methods=["POST"])
@jwt_required()
@role_required("contributor")
def create_resource(module_id):
    """Add a new learning resource to a module."""
    data = request.get_json() or {}
    title = data.get("title")
    resource_type = data.get("type", "video")
    url = data.get("url", "")
    content = data.get("content", "")
    duration = data.get("duration", "")

    if not title:
        return jsonify({"error": "Title is required"}), 400

    if resource_type == "video" and not url:
        return jsonify({"error": "URL is required for video resources"}), 400

    module = Module.query.get(module_id)
    if not module:
        return jsonify({"error": "Module not found"}), 404

    new_resource = LearningResource(
        title=title,
        type=resource_type,
        url=url if url else "",
        content=content,
        duration=duration,
        description="",
        module_id=module_id
    )
    db.session.add(new_resource)
    db.session.commit()

    return jsonify(new_resource.to_dict()), 201

