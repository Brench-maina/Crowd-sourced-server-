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

# GET user's followed paths (FIXED)
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

# Admin Review Learning Paths - FIXED VERSION
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
            
            # Award points to creator - FIX: Check if creator exists
            if path.creator:
                try:
                    PointsService.award_points(path.creator, 'learning_path_approved')
                except Exception as points_error:
                    # Log the error but don't fail the approval
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
        print(f"Error reviewing learning path: {str(e)}")  # Server-side logging
        import traceback
        traceback.print_exc()  # Print full traceback for debugging
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