from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity, verify_jwt_in_request
from datetime import datetime
from models import db, LearningPath, ContentStatusEnum, User, UserProgress, Module
from utils.role_required import role_required
from services.core_services import PointsService

learning_paths_bp = Blueprint('learning_paths_bp', __name__)

@learning_paths_bp.route('/test')
def test_learning():
    return jsonify({"message": "Learning route working!"})

# CREATE Learning Path (Contributor)
@learning_paths_bp.route('/paths', methods=['POST'])
@jwt_required()
def create_learning_path():
    try:
        current_user_identity = get_jwt_identity()
        user_id = current_user_identity["id"] if isinstance(current_user_identity, dict) else current_user_identity
        
        user = User.query.get(user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        title = data.get('title', '').strip()
        description = data.get('description', '').strip()
        
        # Validation
        if not title or len(title) < 5:
            return jsonify({"error": "Title must be at least 5 characters long"}), 400
        
        if not description:
            return jsonify({"error": "Description is required"}), 400
        
        # Create new learning path
        new_path = LearningPath(
            title=title,
            description=description,
            creator_id=user_id,
            status=ContentStatusEnum.pending,
            is_published=False,
            created_at=datetime.utcnow()
        )
        
        db.session.add(new_path)
        db.session.commit()
        
        return jsonify({
            "message": "Learning path created successfully",
            "path": {
                "id": new_path.id,
                "title": new_path.title,
                "description": new_path.description,
                "status": new_path.status.value,
                "is_published": new_path.is_published
            }
        }), 201
        
    except Exception as e:
        db.session.rollback()
        print(f"Error creating learning path: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Failed to create learning path: {str(e)}"}), 500

# GET All Published Learning Paths
@learning_paths_bp.route("/paths", methods=["GET"])
def get_learning_paths():
    # Pagination
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 10, type=int)
    status_filter = request.args.get("status")

    # Check if user is authenticated
    current_user = None
    try:
        verify_jwt_in_request(optional=True)
        current_user_identity = get_jwt_identity()
        if current_user_identity:
            user_id = current_user_identity["id"] if isinstance(current_user_identity, dict) else current_user_identity
            current_user = User.query.get(user_id)
    except:
        current_user = None

    query = LearningPath.query

    # Only admins can see unpublished paths
    if not (current_user and current_user.role == "admin"):
        query = query.filter(LearningPath.is_published == True)

    # Admin can filter by status
    if current_user and current_user.role == "admin":
        if status_filter == "published":
            query = query.filter(LearningPath.is_published == True)
        elif status_filter == "pending":
            query = query.filter(LearningPath.is_published == False)

    # Pagination
    paths_paginated = query.paginate(page=page, per_page=per_page, error_out=False)
    
    # Build paths list with follow status
    paths_list = []
    for lp in paths_paginated.items:
        path_dict = {
            "id": lp.id,
            "title": lp.title,
            "description": lp.description,
            "is_published": lp.is_published
        }
        
        # Add follow status if user is authenticated
        if current_user:
            path_dict["is_following"] = lp in current_user.followed_paths
        else:
            path_dict["is_following"] = False
            
        paths_list.append(path_dict)

    return jsonify({
        "page": page,
        "per_page": per_page,
        "total": paths_paginated.total,
        "paths": paths_list
    })

# GET Modules for a Learning Path
@learning_paths_bp.route('/<int:path_id>/modules', methods=['GET'])
@jwt_required()
def get_path_modules(path_id):
    """Get all modules for a specific learning path"""
    try:
        path = LearningPath.query.get(path_id)
        if not path:
            return jsonify({"error": "Learning path not found"}), 404
        
        # Get current user to check permissions
        current_user_identity = get_jwt_identity()
        user_id = current_user_identity["id"] if isinstance(current_user_identity, dict) else current_user_identity
        user = User.query.get(user_id)
        
        # Check if user is the creator or admin
        if int(path.creator_id) != int(user_id) and user.role != "admin":
            # If not creator/admin, only show modules for published paths
            if not path.is_published:
                return jsonify({"error": "Access denied"}), 403
        
        modules = Module.query.filter_by(learning_path_id=path_id).order_by(Module.id).all()
        
        modules_list = [{
            "id": module.id,
            "title": module.title,
            "description": module.description
        } for module in modules]
        
        return jsonify(modules_list), 200
        
    except Exception as e:
        print(f"Error fetching modules: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Failed to fetch modules: {str(e)}"}), 500

# CREATE Module for a Learning Path
@learning_paths_bp.route('/<int:path_id>/modules', methods=['POST'])
@jwt_required()
def create_module(path_id):
    """Create a new module for a learning path"""
    try:
        current_user_identity = get_jwt_identity()
        user_id = current_user_identity["id"] if isinstance(current_user_identity, dict) else current_user_identity
        
        path = LearningPath.query.get(path_id)
        if not path:
            return jsonify({"error": "Learning path not found"}), 404
        
        # Debug logging
        print(f"DEBUG - User ID: {user_id} (type: {type(user_id)})")
        print(f"DEBUG - Path Creator ID: {path.creator_id} (type: {type(path.creator_id)})")
        
        # Check if user is the creator - ensure both are same type
        if int(path.creator_id) != int(user_id):
            user = User.query.get(user_id)
            # Allow admins too
            if not (user and user.role == "admin"):
                return jsonify({"error": "Only the path creator can add modules"}), 403
        
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        title = data.get('title', '').strip()
        description = data.get('description', '').strip()
        
        if not title or len(title) < 3:
            return jsonify({"error": "Module title must be at least 3 characters"}), 400
        
        new_module = Module(
            title=title,
            description=description,
            learning_path_id=path_id
        )
        
        db.session.add(new_module)
        db.session.commit()
        
        return jsonify({
            "message": "Module created successfully",
            "module": {
                "id": new_module.id,
                "title": new_module.title,
                "description": new_module.description
            }
        }), 201
        
    except Exception as e:
        db.session.rollback()
        print(f"Error creating module: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Failed to create module: {str(e)}"}), 500

# Unfollow Learning Path
@learning_paths_bp.route('/paths/<int:path_id>/unfollow', methods=['POST'])
@jwt_required()
def unfollow_path(path_id):
    try:
        current_user_identity = get_jwt_identity()
        user_id = current_user_identity["id"] if isinstance(current_user_identity, dict) else current_user_identity
        
        path = LearningPath.query.get_or_404(path_id)
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({"error": "User not found"}), 404

        if path not in user.followed_paths:
            return jsonify({"error": "Not following this path"}), 400

        user.followed_paths.remove(path)
        db.session.commit()
        return jsonify({
            "message": "Unfollowed learning path",
            "path": {"id": path.id, "title": path.title}
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Failed to unfollow learning path"}), 500

# GET user's followed paths 
@learning_paths_bp.route("/my-paths", methods=["GET"])
@jwt_required()
def get_my_learning_paths():
    try:
        current_user_identity = get_jwt_identity()
        user_id = current_user_identity["id"] if isinstance(current_user_identity, dict) else current_user_identity
        
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({"error": "User not found"}), 404

        followed_paths = []

        for path in user.followed_paths:
            # Only include published paths
            if path.is_published:
                completed_modules = sum(
                    1 for module in path.modules if module in user.completed_modules
                )
                total_modules = len(path.modules)
                completion_percentage = (
                    int((completed_modules / total_modules) * 100) if total_modules > 0 else 0
                )

                followed_paths.append({
                    "id": path.id,
                    "title": path.title,
                    "description": path.description,
                    "completion_percentage": completion_percentage
                })

        return jsonify(followed_paths), 200
    
    except Exception as e:
        return jsonify({"error": "Failed to retrieve followed paths", "details": str(e)}), 500

# Admin Review Learning Paths
@learning_paths_bp.route('/admin/paths/<int:path_id>/review', methods=['PUT'])
@jwt_required()
@role_required("admin")
def review_learning_path(path_id):
    try:
        current_user_identity = get_jwt_identity()
        user_id = current_user_identity["id"] if isinstance(current_user_identity, dict) else current_user_identity
        
        path = LearningPath.query.get_or_404(path_id)
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No data provided"}), 400
            
        action = data.get("action")
        reason = data.get("reason", "")

        if not action:
            return jsonify({"error": "Action is required"}), 400

        if action == "approve":
            path.status = ContentStatusEnum.approved
            path.is_published = True
            path.reviewed_by = user_id
            path.rejection_reason = None
            
            # Award points to creator
            if path.creator:
                try:
                    PointsService.award_points(path.creator, 'learning_path_approved')
                except Exception as points_error:
                    print(f"Failed to award points: {points_error}")
            
        elif action == "reject":
            if not reason or reason.strip() == "":
                return jsonify({"error": "Rejection reason is required"}), 400
                
            path.status = ContentStatusEnum.rejected
            path.is_published = False
            path.rejection_reason = reason
            path.reviewed_by = user_id
        else:
            return jsonify({"error": "Invalid action. Use 'approve' or 'reject'"}), 400

        db.session.commit()
        
        return jsonify({
            "message": f"Learning path {action}d successfully",
            "path": {
                "id": path.id,
                "title": path.title,
                "status": path.status.value,
                "is_published": path.is_published
            }
        }), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"Error reviewing learning path: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Failed to review learning path: {str(e)}"}), 500

# Admin Get pending paths
@learning_paths_bp.route('/admin/paths/pending', methods=['GET'])
@jwt_required()
@role_required("admin")
def get_pending_paths():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get("per_page", 10, type=int)
    pending_paths = LearningPath.query.filter_by(status=ContentStatusEnum.pending).paginate(page=page, per_page=per_page, error_out=False)

    data = [
        {
            "id": path.id,
            "title": path.title,
            "description": path.description,
            "creator": path.creator.username if path.creator else "Unknown",
            "module_count": path.modules.count(),
            "created_at": path.created_at.isoformat()
        } for path in pending_paths.items
    ]

    return jsonify({
        "pending_paths": data,
        "page": page,
        "total_pages": pending_paths.pages,
        "total_items": pending_paths.total
    }), 200